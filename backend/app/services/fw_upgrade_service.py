from __future__ import annotations

import threading
import time

from flask import current_app

from app.extensions import db
from app.models.baseline import Baseline
from app.models.device import Device
from app.models.fw_upgrade_test import FwUpgradeTest
from app.models.regression_result import RegressionResult
from app.models.task import Task, TaskStatus
from app.services.baseline_service import BaselineService
from app.services.regression_service import RegressionService
from app.services.task_service import TaskService
from app.utils.db import db_released
from app.utils.helpers import ApiError
from app.utils.logger import get_logger
from app.workloads.fio_workload import FioConfigValidator

logger = get_logger(__name__)


def _extract_active_fw(fw_log_data: dict) -> str:
    afi = fw_log_data.get('afi', {})
    active_slot = afi.get('active', 0)
    if active_slot == 0:
        return ''
    frs = fw_log_data.get('frs', [])
    slot_idx = active_slot - 1
    if 0 <= slot_idx < len(frs):
        return frs[slot_idx] or ''
    return ''


class FwUpgradeService:
    @staticmethod
    def create(data: dict) -> FwUpgradeTest:
        device = Device.query.get(data['device_id'])
        if not device or device.agent_status != 'online':
            raise ApiError('VALIDATION_ERROR', '设备不在线', 400)
        fio_config = FioConfigValidator.apply_defaults(data['fio_config'])
        fw_test = FwUpgradeTest(
            name=data['name'],
            device_id=device.id,
            device_ip=device.ip,
            device_path=data['device_path'],
            fio_config=fio_config,
            status='pending',
        )
        db.session.add(fw_test)
        db.session.flush()
        db.session.commit()

        app = current_app._get_current_object()
        threading.Thread(
            target=FwUpgradeService._collect_baseline,
            args=(fw_test.id, device.id, app),
            daemon=True,
        ).start()
        logger.info('FwUpgradeTest %d created', fw_test.id)
        return fw_test

    @staticmethod
    def _collect_baseline(fw_test_id: int, device_id: int, app):
        with app.app_context():
            fw_test = FwUpgradeTest.query.get(fw_test_id)
            device = Device.query.get(device_id)
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                with db_released():
                    fw_info = agent.get_nvme_fw_log(fw_test.device_path)
                fw_test.fw_before = _extract_active_fw(fw_info)
                fw_test.status = 'collecting_baseline'
                db.session.commit()

                fw_test = FwUpgradeTest.query.get(fw_test_id)
                if fw_test.status == 'failed' and fw_test.error == '用户终止':
                    return

                config = fw_test.fio_config
                sub_task = Task(
                    name=f'fw_baseline_{fw_test_id}',
                    device_id=device.id,
                    device_ip=device.ip,
                    device_path=fw_test.device_path,
                    config=config,
                    fault_type='none',
                    is_sub_task=True,
                )
                db.session.add(sub_task)
                db.session.flush()
                fw_test.task_before_id = sub_task.id
                db.session.commit()

                with db_released():
                    resp = agent.fio_start(str(sub_task.id), config, fw_test.device_path)
                    if not resp.get('success'):
                        raise Exception('Agent 启动基线 FIO 失败')

                result = FwUpgradeService._wait_sub_task(
                    sub_task.id, parent_fw_test_id=fw_test_id
                )
                if result is None:
                    fw_test = FwUpgradeTest.query.get(fw_test_id)
                    if fw_test.status == 'failed' and fw_test.error == '用户终止':
                        return
                    raise Exception('基线 FIO 执行超时')

                fw_test.result_before = result
                fw_test.status = 'waiting_upgrade'
                db.session.commit()

            except Exception as e:
                fw_test = FwUpgradeTest.query.get(fw_test_id)
                if fw_test and not (fw_test.status == 'failed' and fw_test.error == '用户终止'):
                    fw_test.status = 'failed'
                    fw_test.error = str(e)
                    db.session.commit()
                logger.exception('FwUpgradeTest %d baseline failed: %s', fw_test_id, e)
            finally:
                agent.close()

    @staticmethod
    def confirm_upgrade(fw_test_id: int) -> FwUpgradeTest:
        fw_test = FwUpgradeTest.query.get(fw_test_id)
        if not fw_test:
            raise ApiError('NOT_FOUND', '固件测试不存在', 404)
        if fw_test.status != 'waiting_upgrade':
            raise ApiError('VALIDATION_ERROR', '当前状态不支持确认升级', 400)
        device = Device.query.get(fw_test.device_id)
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            with db_released():
                fw_info = agent.get_nvme_fw_log(fw_test.device_path)
            fw_test.fw_after = _extract_active_fw(fw_info)
        finally:
            agent.close()

        fw_test.status = 'testing_after'
        db.session.commit()

        app = current_app._get_current_object()
        threading.Thread(
            target=FwUpgradeService._run_after_test,
            args=(fw_test.id, device.id, app),
            daemon=True,
        ).start()
        return fw_test

    @staticmethod
    def _run_after_test(fw_test_id: int, device_id: int, app):
        with app.app_context():
            fw_test = FwUpgradeTest.query.get(fw_test_id)
            device = Device.query.get(device_id)
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                fw_test = FwUpgradeTest.query.get(fw_test_id)
                if fw_test.status == 'failed' and fw_test.error == '用户终止':
                    return

                config = fw_test.fio_config
                sub_task = Task(
                    name=f'fw_after_{fw_test_id}',
                    device_id=device.id,
                    device_ip=device.ip,
                    device_path=fw_test.device_path,
                    config=config,
                    fault_type='none',
                    is_sub_task=True,
                )
                db.session.add(sub_task)
                db.session.flush()
                fw_test.task_after_id = sub_task.id
                db.session.commit()

                with db_released():
                    resp = agent.fio_start(str(sub_task.id), config, fw_test.device_path)
                    if not resp.get('success'):
                        raise Exception('Agent 启动升级后 FIO 失败')

                result = FwUpgradeService._wait_sub_task(
                    sub_task.id, parent_fw_test_id=fw_test_id
                )
                if result is None:
                    fw_test = FwUpgradeTest.query.get(fw_test_id)
                    if fw_test.status == 'failed' and fw_test.error == '用户终止':
                        return
                    raise Exception('升级后 FIO 执行超时')

                fw_test.result_after = result
                db.session.commit()

                sub_task = Task.query.get(sub_task.id)
                if sub_task.status != TaskStatus.SUCCESS:
                    raise Exception('升级后 FIO 执行失败')

                baseline = BaselineService.create({
                    'task_id': fw_test.task_before_id,
                    'name': f'FW升级前基线 - {fw_test.fw_before}',
                    'device_model': '',
                    'firmware': fw_test.fw_before or '',
                })

                reg = RegressionService.run({
                    'task_id': sub_task.id,
                    'baseline_id': baseline.id,
                })
                fw_test.regression_id = reg.id
                fw_test.status = 'done'
                db.session.commit()
                logger.info('FwUpgradeTest %d completed', fw_test_id)

            except Exception as e:
                fw_test = FwUpgradeTest.query.get(fw_test_id)
                if fw_test and not (fw_test.status == 'failed' and fw_test.error == '用户终止'):
                    fw_test.status = 'failed'
                    fw_test.error = str(e)
                    db.session.commit()
                logger.exception('FwUpgradeTest %d after-test failed: %s', fw_test_id, e)
            finally:
                agent.close()

    @staticmethod
    def _wait_sub_task(task_id: int, parent_fw_test_id: int = 0, timeout: int = 7200) -> dict | None:
        start = time.time()
        while time.time() - start < timeout:
            sub = Task.query.get(task_id)
            if sub and sub.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
                return sub.result
            if parent_fw_test_id:
                parent = FwUpgradeTest.query.get(parent_fw_test_id)
                if parent and parent.status == 'failed' and parent.error == '用户终止':
                    return None
            time.sleep(3)
        return None

    @staticmethod
    def get(fw_test_id: int) -> FwUpgradeTest:
        fw_test = FwUpgradeTest.query.get(fw_test_id)
        if not fw_test:
            raise ApiError('NOT_FOUND', '固件测试不存在', 404)
        return fw_test

    @staticmethod
    def list(status: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        query = FwUpgradeTest.query
        if status:
            query = query.filter_by(status=status)
        pagination = query.order_by(FwUpgradeTest.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )
        return {
            'items': [t.to_dict() for t in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def abort(fw_test_id: int) -> FwUpgradeTest:
        fw_test = FwUpgradeService.get(fw_test_id)
        if fw_test.status in ('done', 'failed'):
            raise ApiError('VALIDATION_ERROR', '任务已终态，无法终止', 400)
        fw_test.status = 'failed'
        fw_test.error = '用户终止'
        db.session.commit()
        return fw_test

    @staticmethod
    def report(fw_test_id: int) -> dict:
        fw_test = FwUpgradeService.get(fw_test_id)
        reg = RegressionResult.query.get(fw_test.regression_id) if fw_test.regression_id else None
        report_data = {
            'task': fw_test.to_dict(),
            'regression': reg.to_dict() if reg else None,
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        }
        return report_data


from app.executors.agent_executor import AgentExecutor  # noqa: E402
