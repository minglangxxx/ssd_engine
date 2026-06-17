from __future__ import annotations

import json
import threading
import time

from flask import current_app

from app.extensions import db
from app.models.device import Device
from app.models.snia_task import SniaTask
from app.models.task import Task, TaskStatus
from app.services.task_service import TaskService
from app.utils.db import db_released
from app.utils.helpers import ApiError
from app.utils.logger import get_logger
from app.workloads.fio_workload import FioConfigValidator

logger = get_logger(__name__)


def is_steady_state(iops_history: list[float], window: int = 5, threshold: float = 0.1) -> bool:
    """简化版稳态判定：最近 window 轮的 IOPS 最大偏差 < threshold。

    SNIA PTS 正式规范要求基于 slope（线性回归斜率）的 pass/fail 判定，
    当前实现为简化版，适用于工程验证场景。如需符合 PTS 正式认证，
    需实现 OLS 线性回归 + 置信区间判定。
    """
    if len(iops_history) < window:
        return False
    recent = iops_history[-window:]
    avg = sum(recent) / window
    if avg == 0:
        return False
    max_dev = max(abs(v - avg) / avg for v in recent)
    return max_dev < threshold


class SniaService:
    @staticmethod
    def _default_config() -> dict:
        return {
            'precondition': {'rw': 'write', 'bs': '128k', 'iodepth': 32, 'size': '100%', 'loops': 2},
            'iops_test': {
                'block_sizes': ['128k', '32k', '16k', '8k', '4k', '512'],
                'patterns': ['randwrite', 'randread', 'write', 'read'],
                'iodepth': 32, 'runtime': 60,
            },
            'steady_state': {
                'rw': 'randwrite', 'bs': '4k', 'iodepth': 32,
                'rounds': 25, 'runtime': 60,
                'window': 5, 'threshold': 0.10,
            },
        }

    @staticmethod
    def create(data: dict) -> SniaTask:
        device = Device.query.get(data['device_id'])
        if not device or device.agent_status != 'online':
            raise ApiError('VALIDATION_ERROR', '设备不在线', 400)
        default_config = SniaService._default_config()
        if 'config' in data and data['config']:
            for section in ('precondition', 'iops_test', 'steady_state'):
                if section in data['config']:
                    default_config[section].update(data['config'][section])
        task = SniaTask(
            name=data['name'],
            device_id=device.id,
            device_ip=device.ip,
            device_path=data['device_path'],
            status='pending',
            config=default_config,
            iops_history='[]',
            total_rounds=default_config['steady_state']['rounds'],
        )
        db.session.add(task)
        db.session.flush()
        db.session.commit()

        app = current_app._get_current_object()
        threading.Thread(
            target=SniaService._run_pipeline,
            args=(task.id, app),
            daemon=True,
        ).start()
        logger.info('SniaTask %d created', task.id)
        return task

    @staticmethod
    def get(snia_task_id: int) -> SniaTask:
        task = SniaTask.query.get(snia_task_id)
        if not task:
            raise ApiError('NOT_FOUND', 'SNIA 任务不存在', 404)
        return task

    @staticmethod
    def list(status: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        query = SniaTask.query
        if status:
            query = query.filter_by(status=status)
        pagination = query.order_by(SniaTask.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )
        return {
            'items': [t.to_dict() for t in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def abort(snia_task_id: int) -> SniaTask:
        task = SniaService.get(snia_task_id)
        if task.status in ('done', 'failed', 'aborted'):
            raise ApiError('VALIDATION_ERROR', '任务已终态，无法终止', 400)
        task.status = 'aborted'
        db.session.commit()
        logger.info('SniaTask %d aborted', task.id)
        return task

    @staticmethod
    def report(snia_task_id: int) -> dict:
        task = SniaService.get(snia_task_id)
        return {
            'task': task.to_dict(),
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        }

    @staticmethod
    def _run_pipeline(snia_task_id: int, app):
        with app.app_context():
            task = SniaTask.query.get(snia_task_id)
            device = Device.query.get(task.device_id)
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                # Phase 1: Precondition
                task.status = 'preconditioning'
                task.current_phase = 'precondition'
                db.session.commit()

                pre_cfg = task.config['precondition']
                for loop_i in range(pre_cfg['loops']):
                    task = SniaTask.query.get(snia_task_id)
                    if task.status == 'aborted':
                        return

                    fio_cfg = {
                        'rw': pre_cfg['rw'], 'bs': pre_cfg['bs'],
                        'iodepth': pre_cfg['iodepth'],
                        'size': pre_cfg.get('size', '100%'),
                        'runtime': 0, 'time_based': False,
                        'loops': 1, 'ioengine': pre_cfg.get('ioengine', 'libaio'),
                        'direct': pre_cfg.get('direct', True),
                    }
                    sub_task = Task(
                        name=f'snia_pc_{snia_task_id}_{loop_i}',
                        device_id=device.id,
                        device_ip=device.ip,
                        device_path=task.device_path,
                        config=FioConfigValidator.apply_defaults(fio_cfg),
                        fault_type='none',
                        group_task_id=None,
                        is_sub_task=True,
                    )
                    db.session.add(sub_task)
                    db.session.flush()

                    with db_released():
                        resp = agent.fio_start(str(sub_task.id), fio_cfg, task.device_path)
                        if not resp.get('success'):
                            raise Exception('Agent 启动 Precondition FIO 失败')

                    result = SniaService._wait_sub_task(
                        sub_task.id, parent_snia_task_id=snia_task_id
                    )
                    if result is None:
                        task = SniaTask.query.get(snia_task_id)
                        if task.status == 'aborted':
                            return
                        raise Exception(f'Precondition round {loop_i} 超时')

                # Phase 2: IOPS Test
                task = SniaTask.query.get(snia_task_id)
                if task.status == 'aborted':
                    return
                task.status = 'iops_test'
                task.current_phase = 'iops_test'
                db.session.commit()

                iops_cfg = task.config['iops_test']
                iops_results = []
                for bs in iops_cfg['block_sizes']:
                    for pattern in iops_cfg['patterns']:
                        task = SniaTask.query.get(snia_task_id)
                        if task.status == 'aborted':
                            return

                        fio_cfg = {
                            'rw': pattern, 'bs': bs,
                            'iodepth': iops_cfg['iodepth'],
                            'runtime': iops_cfg['runtime'],
                            'time_based': True, 'ioengine': 'libaio', 'direct': True,
                        }
                        sub_name = f'snia_iops_{snia_task_id}_{bs}_{pattern}'
                        sub_task = Task(
                            name=sub_name,
                            device_id=device.id,
                            device_ip=device.ip,
                            device_path=task.device_path,
                            config=FioConfigValidator.apply_defaults(fio_cfg),
                            fault_type='none',
                            is_sub_task=True,
                        )
                        db.session.add(sub_task)
                        db.session.flush()

                        with db_released():
                            resp = agent.fio_start(str(sub_task.id), fio_cfg, task.device_path)
                            if not resp.get('success'):
                                raise Exception(f'Agent 启动 IOPS Test 失败: {bs}/{pattern}')

                        result = SniaService._wait_sub_task(
                            sub_task.id, parent_snia_task_id=snia_task_id
                        )
                        if result is None:
                            task = SniaTask.query.get(snia_task_id)
                            if task.status == 'aborted':
                                return
                            continue
                        iops_results.append({
                            'bs': bs, 'pattern': pattern,
                            'iops': result.get('iops'),
                            'bw': result.get('bandwidth'),
                        })

                # Phase 3: Steady State
                task = SniaTask.query.get(snia_task_id)
                if task.status == 'aborted':
                    return
                task.status = 'steady_state'
                task.current_phase = 'steady_state'
                task.total_rounds = task.config['steady_state']['rounds']
                db.session.commit()

                ss_cfg = task.config['steady_state']
                iops_list = json.loads(task.iops_history) if task.iops_history else []
                for round_i in range(task.total_rounds):
                    task = SniaTask.query.get(snia_task_id)
                    if task.status == 'aborted':
                        return

                    task.current_round = round_i + 1
                    db.session.commit()

                    fio_cfg = {
                        'rw': ss_cfg['rw'], 'bs': ss_cfg['bs'],
                        'iodepth': ss_cfg['iodepth'],
                        'runtime': ss_cfg['runtime'],
                        'time_based': True, 'ioengine': 'libaio', 'direct': True,
                    }
                    sub_name = f'snia_ss_{snia_task_id}_{round_i}'
                    sub_task = Task(
                        name=sub_name,
                        device_id=device.id,
                        device_ip=device.ip,
                        device_path=task.device_path,
                        config=FioConfigValidator.apply_defaults(fio_cfg),
                        fault_type='none',
                        is_sub_task=True,
                    )
                    db.session.add(sub_task)
                    db.session.flush()

                    with db_released():
                        resp = agent.fio_start(str(sub_task.id), fio_cfg, task.device_path)
                        if not resp.get('success'):
                            raise Exception(f'Agent 启动 Steady State round {round_i} 失败')

                    result = SniaService._wait_sub_task(
                        sub_task.id, parent_snia_task_id=snia_task_id
                    )
                    if result:
                        iops_list.append(result.get('iops', 0))
                    elif result is None:
                        task = SniaTask.query.get(snia_task_id)
                        if task.status == 'aborted':
                            return

                    task.iops_history = json.dumps(iops_list)
                    db.session.commit()

                    if is_steady_state(iops_list, window=ss_cfg['window'], threshold=ss_cfg['threshold']):
                        task.is_steady = True
                        break

                # Done
                task.status = 'done'
                task.result = {
                    'iops_test_results': iops_results,
                    'steady_state_achieved': task.is_steady,
                    'steady_state_round': task.current_round if task.is_steady else None,
                    'iops_history': iops_list,
                }
                db.session.commit()
                logger.info('SniaTask %d completed: steady=%s', task.id, task.is_steady)

            except Exception as e:
                task = SniaTask.query.get(snia_task_id)
                if task and task.status not in ('aborted', 'done'):
                    task.status = 'failed'
                    task.error = str(e)
                    db.session.commit()
                logger.exception('SniaTask %d failed: %s', snia_task_id, e)
            finally:
                agent.close()

    @staticmethod
    def _wait_sub_task(task_id: int, parent_snia_task_id: int = 0, timeout: int = 7200) -> dict | None:
        start = time.time()
        while time.time() - start < timeout:
            sub = Task.query.get(task_id)
            if sub and sub.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
                return sub.result
            if parent_snia_task_id:
                parent = SniaTask.query.get(parent_snia_task_id)
                if parent and parent.status == 'aborted':
                    return None
            time.sleep(3)
        return None


from app.executors.agent_executor import AgentExecutor  # noqa: E402
