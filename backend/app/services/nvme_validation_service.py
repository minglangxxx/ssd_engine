from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

import yaml
from flask import current_app

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.models.nvme_test import NvmeTest
from app.services.nvme_service import NvmeService
from app.utils.db import db_released
from app.utils.helpers import ApiError
from app.utils.logger import get_logger

logger = get_logger(__name__)

RULES_DIR = os.path.join(os.path.dirname(__file__), '..', 'rules')

VALID_TEST_TYPES = {'identify', 'namespace', 'smart', 'error_log', 'feature', 'fw_slot'}


class CheckOp(Enum):
    NOT_EMPTY = "not_empty"
    NOT_ZERO = "not_zero"
    GTE = "gte"
    LTE = "lte"
    RANGE = "range"
    REGEX = "regex"
    IN_SET = "in_set"
    LEN_LTE = "len_lte"
    LEN_GTE = "len_gte"
    INCREASED = "increased"
    FORMAT = "format"


@dataclass
class CheckRule:
    field: str
    check: CheckOp
    label: str
    params: dict | None = None
    level: str = "fail"


@dataclass
class CheckResult:
    field: str
    value: Any
    check: str
    pass_: bool
    reason: str
    level: str

    def to_dict(self) -> dict:
        return {
            'field': self.field,
            'value': self.value,
            'check': self.check,
            'pass': self.pass_,
            'reason': self.reason,
            'level': self.level,
        }


def _resolve_nested(data: dict, key_path: str) -> Any:
    if key_path in data:
        return data[key_path]

    parts = key_path.split('.')
    obj = data
    for part in parts:
        sub_parts = part.replace(']', '').split('[')
        for sp in sub_parts:
            if sp == '':
                continue
            if isinstance(obj, dict):
                obj = obj.get(sp)
            elif isinstance(obj, list):
                try:
                    idx = int(sp)
                    obj = obj[idx] if idx < len(obj) else None
                except (ValueError, TypeError):
                    obj = None
            else:
                return None
            if obj is None:
                return None
    return obj


def _resolve_dynamic_params(params: dict, raw_data: dict) -> dict:
    if not params:
        return params
    resolved = {}
    for k, v in params.items():
        if isinstance(v, str) and v in raw_data:
            resolved[k] = raw_data[v]
        elif k == 'hi' and isinstance(v, str):
            special_map = {
                'nsze': raw_data.get('nsze', 0),
                'ncap': raw_data.get('ncap', 0),
                'lbafs_len': len(raw_data.get('lbaf', [])) - 1 if isinstance(raw_data.get('lbaf'), list) else 0,
            }
            if v in special_map:
                resolved[k] = special_map[v]
            else:
                resolved[k] = raw_data.get(v, v)
        else:
            resolved[k] = v
    return resolved


def evaluate_rule(value: Any, rule: CheckRule) -> CheckResult:
    passed = True
    reason = "通过"

    if rule.check == CheckOp.NOT_EMPTY:
        if value is None or value == "":
            passed = False
            reason = f"{rule.label}为空"
    elif rule.check == CheckOp.NOT_ZERO:
        try:
            if value is None or int(value) == 0:
                passed = False
                reason = f"{rule.label}为0"
        except (ValueError, TypeError):
            passed = False
            reason = f"{rule.label}值无效"
    elif rule.check == CheckOp.GTE:
        threshold = (rule.params or {}).get("threshold", 1)
        try:
            if value is None or int(value) < threshold:
                passed = False
                reason = f"{rule.label}={value}，要求≥{threshold}"
        except (ValueError, TypeError):
            passed = False
            reason = f"{rule.label}值无效"
    elif rule.check == CheckOp.LTE:
        threshold = (rule.params or {}).get("threshold", 70)
        try:
            if value is not None and int(value) > threshold:
                passed = False
                reason = f"{rule.label}={value}，要求≤{threshold}"
        except (ValueError, TypeError):
            passed = False
            reason = f"{rule.label}值无效"
    elif rule.check == CheckOp.RANGE:
        lo = (rule.params or {}).get("lo", 0)
        hi = (rule.params or {}).get("hi", 100)
        try:
            iv = int(value) if value is not None else None
            if iv is None or not (lo <= iv <= hi):
                passed = False
                reason = f"{rule.label}={value}，要求在[{lo},{hi}]范围"
        except (ValueError, TypeError):
            passed = False
            reason = f"{rule.label}值无效"
    elif rule.check == CheckOp.REGEX:
        pattern = (rule.params or {}).get("regex", "")
        if not re.match(pattern, str(value or "")):
            passed = False
            reason = f"{rule.label}格式不匹配"
    elif rule.check == CheckOp.IN_SET:
        allowed = [str(v) for v in (rule.params or {}).get("set", [])]
        if str(value) not in allowed:
            passed = False
            reason = f"{rule.label}={value}，不在允许集合内"
    elif rule.check == CheckOp.LEN_LTE:
        max_len = (rule.params or {}).get("max", 20)
        if value and len(str(value)) > max_len:
            passed = False
            reason = f"{rule.label}长度{len(str(value))}，超过{max_len}"
    elif rule.check == CheckOp.LEN_GTE:
        min_len = (rule.params or {}).get("min", 1)
        if not value or len(str(value)) < min_len:
            passed = False
            reason = f"{rule.label}长度不足{min_len}"
    elif rule.check == CheckOp.FORMAT:
        if (rule.params or {}).get("fmt") == "hex4":
            if not re.match(r"^0x[0-9a-fA-F]{4}$", str(value or "")):
                passed = False
                reason = f"{rule.label}格式需为0x+4位十六进制"
    elif rule.check == CheckOp.INCREASED:
        before = (rule.params or {}).get("before", 0)
        after = (rule.params or {}).get("after", 0)
        if after <= before:
            passed = False
            reason = f"错误日志条数未增加（{before}→{after}）"
        else:
            reason = f"错误日志正确增加（{before}→{after}）"

    return CheckResult(
        field=rule.field,
        value=value,
        check=rule.label,
        pass_=passed,
        reason=reason,
        level=rule.level,
    )


def aggregate_verdict(results: list[CheckResult]) -> str:
    has_fail = any(not r.pass_ and r.level == "fail" for r in results)
    has_warn = any(not r.pass_ and r.level == "warn" for r in results)
    if has_fail:
        return "FAIL"
    if has_warn:
        return "PARTIAL"
    return "PASS"


def verify_error_log_result(verify_data: dict) -> list[CheckResult]:
    """适配 Agent error_log_verify 增量比对返回结构

    校验项：
    1. SMART 计数器应单调递增（count2 >= count1）
    2. error-log 缓冲区条目数 ≤ SMART 计数器最新值
    3. error-log 缓冲区是否有条目（信息性告警）
    """
    results = []

    if verify_data.get('skipped', False):
        results.append(CheckResult(
            field='error_log_verify', value='skipped',
            check='错误日志交叉验证', pass_=True,
            reason=f'跳过验证（{verify_data.get("skip_reason", "")}）',
            level='warn',
        ))
        return results

    err_count = verify_data.get('error_log_count', 0)
    count1 = verify_data.get('smart_count_first', 0)
    count2 = verify_data.get('smart_count_second', 0)
    consistent = verify_data.get('consistent', False)
    delta = verify_data.get('counter_delta', 0)

    counter_not_decreased = (count2 >= count1)
    results.append(CheckResult(
        field='smart_counter_monotonic',
        value=f'first={count1}, second={count2}, delta={delta}',
        check='SMART num_err_log_entries 单调递增',
        pass_=counter_not_decreased,
        reason='计数器单调递增' if counter_not_decreased
               else f'计数器异常减少（{count1}→{count2}）',
        level='fail',
    ))

    buffer_ok = (err_count <= count2)
    results.append(CheckResult(
        field='error_log_buffer_vs_counter',
        value=f'buffer={err_count}, counter={count2}',
        check='Error Log 缓冲区条目数 ≤ SMART 计数器',
        pass_=buffer_ok,
        reason='缓冲区条目数在合理范围' if buffer_ok
               else f'缓冲区条目数({err_count})超过计数器({count2})',
        level='fail',
    ))

    if err_count > 0:
        results.append(CheckResult(
            field='error_log_entries', value=err_count,
            check='Error Log 条目数', pass_=False,
            reason=f'存在 {err_count} 条错误日志条目',
            level='warn',
        ))
    else:
        results.append(CheckResult(
            field='error_log_entries', value=0,
            check='Error Log 条目数', pass_=True,
            reason='无错误日志条目',
            level='warn',
        ))

    return results


class NvmeValidationService:
    @staticmethod
    def load_rules(test_type: str) -> list[CheckRule]:
        if test_type == 'error_log':
            return []
        filename = {
            'identify': 'identify_rules.yaml',
            'namespace': 'namespace_rules.yaml',
            'smart': 'smart_rules.yaml',
            'feature': 'feature_rules.yaml',
            'fw_slot': 'fw_slot_rules.yaml',
        }.get(test_type)
        if not filename:
            raise ApiError('INVALID_PARAM', f'不支持的 test_type: {test_type}', 400)

        filepath = os.path.join(RULES_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning('Rule file not found: %s, using empty rules', filepath)
            return []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.warning('YAML parse error in %s: %s', filepath, e)
            return []

        if not data or 'rules' not in data:
            return []

        rules = []
        for item in data['rules']:
            try:
                rules.append(CheckRule(
                    field=item['field'],
                    check=CheckOp(item['check']),
                    label=item['label'],
                    params=item.get('params'),
                    level=item.get('level', 'fail'),
                ))
            except (KeyError, ValueError) as e:
                logger.warning('Invalid rule entry in %s: %s (%s)', filepath, item, e)
        return rules

    @staticmethod
    def apply_rules(raw_data: dict, rules: list[CheckRule]) -> list[CheckResult]:
        results = []
        for rule in rules:
            value = _resolve_nested(raw_data, rule.field)
            resolved_params = _resolve_dynamic_params(rule.params or {}, raw_data)
            effective_rule = CheckRule(
                field=rule.field,
                check=rule.check,
                label=rule.label,
                params=resolved_params,
                level=rule.level,
            )
            results.append(evaluate_rule(value, effective_rule))
        return results

    @staticmethod
    def run_validation(device_id: int, disk_name: str, test_type: str) -> dict:
        if test_type not in VALID_TEST_TYPES:
            raise ApiError('INVALID_PARAM', f'不支持的 test_type: {test_type}', 400)

        device = Device.query.get(device_id)
        if device is None:
            raise ApiError('NOT_FOUND', '设备不存在', 404)

        existing = NvmeTest.query.filter_by(
            device_id=device.id,
            disk_name=disk_name,
            test_type=test_type,
        ).filter(
            NvmeTest.status.in_(['pending', 'running'])
        ).first()
        if existing is not None:
            return {'test_id': existing.id, 'status': existing.status}

        test = NvmeTest(
            device_id=device.id,
            disk_name=disk_name,
            test_type=test_type,
            status='pending',
        )
        db.session.add(test)
        db.session.commit()

        thread = threading.Thread(
            target=NvmeValidationService._run_in_background,
            args=(test.id, device, disk_name, test_type),
            daemon=True,
        )
        thread.start()

        return {'test_id': test.id, 'status': 'pending'}

    @staticmethod
    def get_validation_result(test_id: int) -> dict:
        test = NvmeTest.query.get(test_id)
        if test is None:
            raise ApiError('NOT_FOUND', '校验记录不存在', 404)
        return test.to_dict()

    @staticmethod
    def list_validations(device_id: int, disk_name: str | None = None,
                         test_type: str | None = None,
                         page: int = 1, page_size: int = 10) -> dict:
        device = Device.query.get(device_id)
        if device is None:
            raise ApiError('NOT_FOUND', '设备不存在', 404)

        query = NvmeTest.query.filter_by(device_id=device_id)
        if disk_name:
            query = query.filter_by(disk_name=disk_name)
        if test_type:
            query = query.filter_by(test_type=test_type)

        total = query.count()
        items = (query.order_by(NvmeTest.created_at.desc())
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all())

        return {
            'items': [t.to_dict() for t in items],
            'total': total,
        }

    @staticmethod
    def _run_in_background(test_id: int, device: Device, disk_name: str, test_type: str):
        app = current_app._get_current_object()
        with app.app_context():
            try:
                test = NvmeTest.query.get(test_id)
                test.status = 'running'
                db.session.commit()

                with db_released():
                    agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
                    try:
                        raw_data = NvmeValidationService._fetch_data(agent, disk_name, test_type)
                    finally:
                        agent.close()

                if test_type == 'error_log':
                    results = verify_error_log_result(raw_data)
                else:
                    rules = NvmeValidationService.load_rules(test_type)
                    results = NvmeValidationService.apply_rules(raw_data, rules)

                verdict = aggregate_verdict(results)

                test = NvmeTest.query.get(test_id)
                test.result = [r.to_dict() for r in results]
                test.verdict = verdict
                test.status = 'done'
                db.session.commit()

            except Exception as e:
                logger.error('Validation failed for test_id=%s: %s', test_id, e, exc_info=True)
                try:
                    db.session.rollback()
                    test = NvmeTest.query.get(test_id)
                    if test:
                        test.status = 'failed'
                        test.error = str(e)
                        db.session.commit()
                except Exception:
                    db.session.rollback()
                    try:
                        db.session.execute(
                            db.text("UPDATE nvme_tests SET status='failed', error=:err WHERE id=:id"),
                            {'err': str(e)[:500], 'id': test_id}
                        )
                        db.session.commit()
                    except Exception:
                        logger.critical('Cannot mark test_id=%s as failed, stuck in running', test_id)
            finally:
                db.session.remove()

    @staticmethod
    def _fetch_data(agent: AgentExecutor, disk_name: str, test_type: str) -> dict:
        controller = NvmeService._extract_nvme_controller(disk_name)
        if test_type == 'identify':
            return agent.get_nvme_id_ctrl(f'/dev/{controller}')
        elif test_type == 'namespace':
            return agent.get_nvme_id_ns(f'/dev/{disk_name}')
        elif test_type == 'smart':
            return agent.get_smart(f'/dev/{disk_name}')
        elif test_type == 'error_log':
            return agent.verify_nvme_error_log(f'/dev/{controller}')
        elif test_type == 'feature':
            data = {}
            for fid, label in [('0x06', 'fid_0x06'), ('0x02', 'fid_0x02'), ('0x0c', 'fid_0x0c')]:
                try:
                    data[label] = agent.get_nvme_feature(f'/dev/{controller}', fid=fid)
                except Exception:
                    data[label] = None
            return data
        elif test_type == 'fw_slot':
            return agent.get_nvme_fw_log(f'/dev/{controller}')
        raise ApiError('INVALID_PARAM', f'不支持的 test_type: {test_type}', 400)
