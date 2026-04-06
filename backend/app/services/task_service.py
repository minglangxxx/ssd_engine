from __future__ import annotations

from datetime import datetime
from typing import Any

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.models.fio_trend import FioTrendData
from app.models.task import Task, TaskStatus
from app.utils.helpers import ApiError
from app.workloads.fio_workload import FioConfigError, FioConfigValidator


class TaskService:
    @staticmethod
    def create(data: dict) -> Task:
        config = data.get('config', {})
        errors = FioConfigValidator.validate(config)
        if errors:
            raise FioConfigError(errors)

        device = Device.query.filter_by(ip=data['device_ip']).first()
        if device is None:
            device = Device(
                ip=data['device_ip'],
                name=data.get('name') or data['device_ip'],
                ssh_user=data.get('device_user'),
                ssh_password=data.get('device_password'),
            )
            db.session.add(device)
            db.session.flush()

        task = Task(
            name=data.get('name') or f"FIO-{data['device_ip']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            device_id=device.id,
            device_ip=data['device_ip'],
            device_user=data.get('device_user'),
            device_password=data.get('device_password'),
            device_path=data['device_path'],
            config=FioConfigValidator.apply_defaults(config),
            fault_type=data.get('fault_type', 'none'),
        )
        db.session.add(task)
        db.session.flush()
        TaskService._start_task(task, device)
        db.session.commit()
        return task

    @staticmethod
    def get(task_id: int) -> Task:
        task = Task.query.get(task_id)
        if not task:
            raise ApiError('NOT_FOUND', '任务不存在', 404)
        TaskService.refresh_runtime_state(task)
        return task

    @staticmethod
    def list(status: str | None = None, keyword: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        query = Task.query
        if status and status.lower() != 'all':
            query = query.filter_by(status=status)
        if keyword:
            query = query.filter(Task.name.like(f'%{keyword}%'))

        pagination = query.order_by(Task.created_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False,
        )
        for item in pagination.items:
            TaskService.refresh_runtime_state(item)
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def delete(task_id: int) -> None:
        task = TaskService.get(task_id)
        FioTrendData.query.filter_by(task_id=task.id).delete()
        db.session.delete(task)
        db.session.commit()

    @staticmethod
    def get_status(task_id: int) -> dict:
        task = TaskService.get(task_id)
        result = task.result or {}
        return {
            'id': task.id,
            'status': task.status,
            'error': result.get('error'),
            'result': task.result,
            'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        }

    @staticmethod
    def stop(task_id: int) -> Task:
        task = TaskService.get(task_id)
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            raise ApiError('VALIDATION_ERROR', '只有运行中或待启动任务可以停止', 400)

        device = TaskService._get_task_device(task)
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法停止任务', 503)

            response = agent.fio_stop(str(task.id))
            if not response.get('success', False):
                raise ApiError('CONNECTION_ERROR', 'Agent 停止任务失败', 503)

            task.status = TaskStatus.FAILED
            task.result = task.result or {}
            task.result['error'] = 'User cancelled'
            task.updated_at = datetime.utcnow()
            TaskService._replace_trend_points(task.id, agent.fio_trend(str(task.id)))
            db.session.commit()
            return task
        finally:
            agent.close()

    @staticmethod
    def retry(task_id: int) -> Task:
        task = TaskService.get(task_id)
        if task.status != TaskStatus.FAILED:
            raise ApiError('VALIDATION_ERROR', '只有失败任务可以重试', 400)

        device = TaskService._get_task_device(task)
        FioTrendData.query.filter_by(task_id=task.id).delete()
        task.result = None
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.utcnow()
        TaskService._start_task(task, device)
        db.session.commit()
        return task

    @staticmethod
    def get_trend(task_id: int, start: str | None = None, end: str | None = None) -> list[dict]:
        task = TaskService.get(task_id)
        device = Device.query.get(task.device_id) if task.device_id else None

        if device:
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                if agent.test_connection():
                    return agent.fio_trend(str(task.id), start, end)
            except Exception:
                pass
            finally:
                agent.close()

        query = FioTrendData.query.filter_by(task_id=task.id)
        if start:
            query = query.filter(FioTrendData.timestamp >= datetime.fromisoformat(start))
        if end:
            query = query.filter(FioTrendData.timestamp <= datetime.fromisoformat(end))
        return [item.to_dict() for item in query.order_by(FioTrendData.timestamp.asc()).all()]

    @staticmethod
    def refresh_runtime_state(task: Task) -> Task:
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING} or not task.device_id:
            return task

        device = TaskService._get_task_device(task)

        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                return task

            status_payload = agent.fio_status(str(task.id))
            remote_status = str(status_payload.get('status', '')).lower()

            if remote_status in {'pending', 'running'}:
                mapped_status = TaskStatus.RUNNING if remote_status == 'running' else TaskStatus.PENDING
                if task.status != mapped_status:
                    task.status = mapped_status
                    task.updated_at = datetime.utcnow()
                    db.session.commit()
                return task

            if remote_status == 'success':
                task.status = TaskStatus.SUCCESS
                task.result = status_payload.get('result') or task.result
                task.updated_at = datetime.utcnow()
                TaskService._replace_trend_points(task.id, agent.fio_trend(str(task.id)))
                db.session.commit()
                return task

            if remote_status in {'failed', 'not_found'}:
                task.status = TaskStatus.FAILED
                task.result = task.result or {}
                if status_payload.get('error'):
                    task.result['error'] = status_payload.get('error')
                task.updated_at = datetime.utcnow()
                TaskService._replace_trend_points(task.id, agent.fio_trend(str(task.id)))
                db.session.commit()
            return task
        finally:
            agent.close()

    @staticmethod
    def _start_task(task: Task, device: Device) -> None:
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法启动任务', 503)

            response = agent.fio_start(str(task.id), task.config, task.device_path)
            if not response.get('success', False):
                raise ApiError('CONNECTION_ERROR', 'Agent 启动 FIO 任务失败', 503)

            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.utcnow()
        finally:
            agent.close()

    @staticmethod
    def _get_task_device(task: Task) -> Device:
        device = Device.query.get(task.device_id) if task.device_id else None
        if device is None:
            raise ApiError('NOT_FOUND', '任务关联设备不存在', 404)
        return device

    @staticmethod
    def _replace_trend_points(task_id: int, points: list[dict[str, Any]]) -> None:
        FioTrendData.query.filter_by(task_id=task_id).delete()
        for point in points:
            timestamp = TaskService._parse_timestamp(point.get('timestamp'))
            if timestamp is None:
                continue
            db.session.add(FioTrendData(
                task_id=task_id,
                timestamp=timestamp,
                iops_read=float(point.get('iops_read', 0) or 0),
                iops_write=float(point.get('iops_write', 0) or 0),
                iops_total=float(point.get('iops_total', 0) or 0),
                bw_read=float(point.get('bw_read', 0) or 0),
                bw_write=float(point.get('bw_write', 0) or 0),
                bw_total=float(point.get('bw_total', 0) or 0),
                lat_mean=float(point.get('lat_mean', 0) or 0),
                lat_p99=float(point.get('lat_p99', 0) or 0),
                lat_max=float(point.get('lat_max', 0) or 0),
            ))

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                try:
                    return datetime.fromtimestamp(float(value))
                except ValueError:
                    return None
        return None
