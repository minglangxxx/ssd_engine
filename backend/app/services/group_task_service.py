from __future__ import annotations

import threading

from flask import current_app

from app.extensions import db
from app.models.device import Device
from app.models.group_task import GroupTask
from app.models.task import Task, TaskStatus
from app.services.task_service import TaskService
from app.utils.db import db_released
from app.utils.helpers import ApiError
from app.utils.logger import get_logger
from app.workloads.fio_workload import FioConfigValidator

logger = get_logger(__name__)


class GroupTaskService:
    @staticmethod
    def create(data: dict) -> GroupTask:
        device_ids = data['device_ids']
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        if len(devices) != len(device_ids):
            missing = set(device_ids) - {d.id for d in devices}
            raise ApiError('NOT_FOUND', f'设备不存在: {missing}', 404)
        offline = [d.ip for d in devices if d.agent_status != 'online']
        if offline:
            raise ApiError('VALIDATION_ERROR', f'设备离线: {offline}', 400)

        fio_config = FioConfigValidator.apply_defaults(data['fio_config'])
        default_path = data.get('device_path') or '/dev/nvme0n1'
        per_device_paths = data.get('device_paths') or {}

        group = GroupTask(
            name=data['name'],
            fio_config=fio_config,
            total_count=len(devices),
        )
        db.session.add(group)
        db.session.flush()

        task_ids = []
        for device in devices:
            path = per_device_paths.get(str(device.id), default_path)
            task = Task(
                name=f"{data['name']} - {device.ip}",
                device_id=device.id,
                device_ip=device.ip,
                device_path=path,
                config=fio_config,
                fault_type='none',
                group_task_id=group.id,
                is_sub_task=True,
            )
            db.session.add(task)
            db.session.flush()
            task_ids.append((task.id, device.id))

        group.status = 'running'
        db.session.commit()

        app = current_app._get_current_object()
        for task_id, device_id in task_ids:
            threading.Thread(
                target=GroupTaskService._start_sub_task,
                args=(task_id, device_id, app),
                daemon=True,
            ).start()

        logger.info('GroupTask %d created with %d sub-tasks', group.id, len(devices))
        return group

    @staticmethod
    def _start_sub_task(task_id: int, device_id: int, app):
        with app.app_context():
            try:
                TaskService.start_task_by_id(task_id, device_id)
                db.session.commit()
            except Exception:
                task = Task.query.get(task_id)
                if task and task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                    task.status = TaskStatus.FAILED
                    task.result = task.result or {}
                    task.result['error'] = 'Agent 启动失败'
                    db.session.commit()

    @staticmethod
    def list(status: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        query = GroupTask.query
        if status:
            query = query.filter_by(status=status)
        pagination = query.order_by(GroupTask.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )
        return {
            'items': [g.to_dict() for g in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def get(group_task_id: int) -> GroupTask:
        group = GroupTask.query.get(group_task_id)
        if not group:
            raise ApiError('NOT_FOUND', '组任务不存在', 404)
        return group

    @staticmethod
    def delete(group_task_id: int) -> None:
        group = GroupTaskService.get(group_task_id)
        for sub_task in group.sub_tasks:
            from app.models.fio_trend import FioTrendData
            FioTrendData.query.filter_by(task_id=sub_task.id).delete()
            from app.models.data_record import DataRecord
            DataRecord.query.filter_by(task_id=sub_task.id).delete()
            from app.models.baseline import Baseline
            from app.models.regression_result import RegressionResult
            for b in Baseline.query.filter_by(source_task_id=sub_task.id).all():
                if RegressionResult.query.filter_by(baseline_id=b.id).first():
                    raise ApiError('CONFLICT', f'基线 #{b.id} 存在回归引用，需先删除回归结果', 409)
                db.session.delete(b)
            from app.models.monitor_data import DiskMonitorSample
            DiskMonitorSample.query.filter_by(task_id=sub_task.id).update({DiskMonitorSample.task_id: None})
        Task.query.filter_by(group_task_id=group_task_id).delete()
        db.session.delete(group)
        db.session.commit()
        logger.info('GroupTask %d and sub-tasks deleted', group_task_id)

    @staticmethod
    def try_aggregate(group_task_id: int):
        group = GroupTask.query.get(group_task_id)
        if group is None:
            return
        sub_tasks = Task.query.filter_by(group_task_id=group_task_id).all()
        done_count = sum(
            1 for t in sub_tasks
            if t.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}
        )
        group.done_count = done_count

        if done_count < group.total_count:
            db.session.commit()
            return

        success_tasks = [t for t in sub_tasks if t.status == TaskStatus.SUCCESS]
        if not success_tasks:
            group.status = 'failed'
            db.session.commit()
            return

        iops_list = [t.result['iops'] for t in success_tasks if t.result and 'iops' in t.result]
        bw_list = [t.result['bandwidth'] for t in success_tasks if t.result and 'bandwidth' in t.result]
        lat_list = [
            t.result['latency']['mean'] for t in success_tasks
            if t.result and t.result.get('latency', {}).get('mean')
        ]
        lat_p99_list = [
            t.result['latency']['p99'] for t in success_tasks
            if t.result and t.result.get('latency', {}).get('p99')
        ]

        group.summary = {
            'iops_max': max(iops_list) if iops_list else None,
            'iops_min': min(iops_list) if iops_list else None,
            'iops_avg': round(sum(iops_list) / len(iops_list), 1) if iops_list else None,
            'bw_max': max(bw_list) if bw_list else None,
            'bw_min': min(bw_list) if bw_list else None,
            'bw_avg': round(sum(bw_list) / len(bw_list), 1) if bw_list else None,
            'lat_mean_max': max(lat_list) if lat_list else None,
            'lat_mean_min': min(lat_list) if lat_list else None,
            'lat_mean_avg': round(sum(lat_list) / len(lat_list), 1) if lat_list else None,
            'lat_p99_max': max(lat_p99_list) if lat_p99_list else None,
            'lat_p99_min': min(lat_p99_list) if lat_p99_list else None,
            'lat_p99_avg': round(sum(lat_p99_list) / len(lat_p99_list), 1) if lat_p99_list else None,
        }
        group.status = 'partial' if len(success_tasks) < group.total_count else 'done'
        db.session.commit()
        logger.info('GroupTask %d aggregated: status=%s', group.id, group.status)
