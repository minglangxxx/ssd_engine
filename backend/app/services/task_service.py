from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.models.fio_trend import FioTrendData
from app.models.task import Task, TaskStatus
from app.utils.helpers import ApiError
from app.workloads.fio_workload import FioConfigError, FioConfigValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskService:
    @staticmethod
    def create(data: dict) -> Task:
        logger.info(f"Creating new task for device {data['device_ip']}")
        raw_command = data.get('fio_command')
        config = data.get('config', {})
        if raw_command:
            config = FioConfigValidator.parse_cli_command(raw_command, data.get('device_path'))
        errors = FioConfigValidator.validate(config)
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            raise FioConfigError(errors)

        device = Device.query.filter_by(ip=data['device_ip']).first()
        if device is None:
            logger.info(f"Device {data['device_ip']} not found, creating new device")
            device = Device(
                ip=data['device_ip'],
                name=data.get('name') or data['device_ip'],
            )
            db.session.add(device)
            db.session.flush()
            logger.info(f"New device {data['device_ip']} created")

        task = Task(
            name=data.get('name') or f"FIO-{data['device_ip']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            device_id=device.id,
            device_ip=data['device_ip'],
            device_path=data['device_path'],
            config=FioConfigValidator.apply_defaults(config),
            fault_type=data.get('fault_type', 'none'),
        )
        db.session.add(task)
        db.session.flush()
        logger.info(f"Starting task {task.id} on device {task.device_ip}")
        TaskService._start_task(task, device)
        db.session.commit()
        logger.info(f"Task {task.id} creation completed successfully")
        return task

    @staticmethod
    def get(task_id: int) -> Task:
        logger.info(f"Retrieving task {task_id}")
        task = Task.query.get(task_id)
        if not task:
            logger.warning(f"Attempt to retrieve non-existent task {task_id}")
            raise ApiError('NOT_FOUND', '任务不存在', 404)
        TaskService.refresh_runtime_state(task)
        return task

    @staticmethod
    def list(status: str | None = None, keyword: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        logger.info(f"Listing tasks with filters - status: {status}, keyword: {keyword}, page: {page}/{page_size}")
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
        logger.info(f"Returning {len(pagination.items)} tasks out of total {pagination.total}")
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def delete(task_id: int) -> None:
        logger.info(f"Deleting task {task_id}")
        task = TaskService.get(task_id)
        FioTrendData.query.filter_by(task_id=task.id).delete()
        db.session.delete(task)
        db.session.commit()
        logger.info(f"Task {task_id} deleted successfully")

    @staticmethod
    def get_status(task_id: int) -> dict:
        logger.info(f"Getting status for task {task_id}")
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
        logger.info(f"Stopping task {task_id}")
        task = TaskService.get(task_id)
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            logger.warning(f"Attempt to stop task {task_id} that is not running/pending. Current status: {task.status}")
            raise ApiError('VALIDATION_ERROR', '只有运行中或待启动任务可以停止', 400)

        device = TaskService._get_task_device(task)
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                logger.error(f"Failed to connect to agent on {device.ip}:{device.agent_port} when stopping task {task_id}")
                raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法停止任务', 503)

            response = agent.fio_stop(str(task_id))
            if not response.get('success', False):
                logger.error(f"Agent failed to stop task {task_id}, response: {response}")
                raise ApiError('CONNECTION_ERROR', 'Agent 停止任务失败', 503)

            task.status = TaskStatus.FAILED
            task.result = task.result or {}
            task.result['error'] = 'User cancelled'
            task.updated_at = datetime.utcnow()
            TaskService._replace_trend_points(task.id, agent.fio_trend(str(task_id)))
            db.session.commit()
            logger.info(f"Task {task_id} stopped successfully")
            return task
        finally:
            agent.close()

    @staticmethod
    def retry(task_id: int) -> Task:
        logger.info(f"Retrying task {task_id}")
        task = TaskService.get(task_id)
        if task.status != TaskStatus.FAILED:
            logger.warning(f"Attempt to retry task {task_id} that is not in FAILED state. Current status: {task.status}")
            raise ApiError('VALIDATION_ERROR', '只有失败任务可以重试', 400)

        device = TaskService._get_task_device(task)
        FioTrendData.query.filter_by(task_id=task.id).delete()
        task.result = None
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.utcnow()
        TaskService._start_task(task, device)
        db.session.commit()
        logger.info(f"Task {task_id} retry initiated successfully")
        return task

    @staticmethod
    def get_trend(task_id: int, start: str | None = None, end: str | None = None) -> list[dict]:
        logger.info(f"Getting trend data for task {task_id}, time range: {start} to {end}")
        task = TaskService.get(task_id)
        device = Device.query.get(task.device_id) if task.device_id else None

        if device:
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                if agent.test_connection():
                    trend_data = agent.fio_trend(str(task_id), start, end)
                    logger.info(f"Retrieved {len(trend_data)} trend points from agent for task {task_id}")
                    return trend_data
            except Exception as e:
                logger.error(f"Error getting trend data from agent for task {task_id}: {str(e)}")
            finally:
                agent.close()

        query = FioTrendData.query.filter_by(task_id=task.id)
        if start:
            query = query.filter(FioTrendData.timestamp >= datetime.fromisoformat(start))
        if end:
            query = query.filter(FioTrendData.timestamp <= datetime.fromisoformat(end))
        trend_data = [item.to_dict() for item in query.order_by(FioTrendData.timestamp.asc()).all()]
        logger.info(f"Retrieved {len(trend_data)} trend points from database for task {task_id}")
        return trend_data

    @staticmethod
    def refresh_runtime_state(task: Task) -> Task:
        logger.debug(f"Refreshing runtime state for task {task.id}, current status: {task.status}")
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING} or not task.device_id:
            return task

        device = TaskService._get_task_device(task)

        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                logger.warning(f"Cannot connect to agent on {device.ip}:{device.agent_port} for task {task.id}")
                return task

            status_payload = agent.fio_status(str(task.id))
            remote_status = str(status_payload.get('status', '')).lower()
            logger.debug(f"Remote status for task {task.id}: {remote_status}")

            if remote_status in {'pending', 'running'}:
                mapped_status = TaskStatus.RUNNING if remote_status == 'running' else TaskStatus.PENDING
                if task.status != mapped_status:
                    task.status = mapped_status
                    task.updated_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"Updated task {task.id} status to {mapped_status}")
                return task

            if remote_status == 'success':
                task.status = TaskStatus.SUCCESS
                task.result = status_payload.get('result') or task.result
                task.updated_at = datetime.utcnow()
                TaskService._replace_trend_points(task.id, agent.fio_trend(str(task.id)))
                db.session.commit()
                logger.info(f"Task {task.id} completed successfully")
                return task

            if remote_status in {'failed', 'not_found'}:
                task.status = TaskStatus.FAILED
                task.result = task.result or {}
                if status_payload.get('error'):
                    task.result['error'] = status_payload.get('error')
                task.updated_at = datetime.utcnow()
                TaskService._replace_trend_points(task.id, agent.fio_trend(str(task.id)))
                db.session.commit()
                logger.warning(f"Task {task.id} failed: {status_payload.get('error', 'Unknown error')}")
            return task
        finally:
            agent.close()

    @staticmethod
    def get_execution_window(
        task: Task,
        window_before_seconds: int = 30,
        window_after_seconds: int = 30,
    ) -> dict[str, str | float | None]:
        start_time, end_time = TaskService._get_runtime_window_from_agent(task)

        if start_time is None or end_time is None:
            trend_start, trend_end = TaskService._get_runtime_window_from_db(task.id)
            start_time = start_time or trend_start
            end_time = end_time or trend_end

        if start_time is None:
            start_time = task.created_at or datetime.utcnow()

        if end_time is None:
            configured_runtime = int((task.config or {}).get('runtime') or 0)
            fallback_end = task.updated_at or start_time
            if configured_runtime > 0 and fallback_end <= start_time:
                fallback_end = start_time + timedelta(seconds=configured_runtime)
            end_time = fallback_end

        if end_time < start_time:
            end_time = start_time

        analysis_start = start_time - timedelta(seconds=max(0, window_before_seconds))
        analysis_end = end_time + timedelta(seconds=max(0, window_after_seconds))

        return {
            'fio_start': start_time.isoformat(),
            'fio_end': end_time.isoformat(),
            'analysis_start': analysis_start.isoformat(),
            'analysis_end': analysis_end.isoformat(),
            'window_before_seconds': max(0, window_before_seconds),
            'window_after_seconds': max(0, window_after_seconds),
            'duration_seconds': max(0.0, (end_time - start_time).total_seconds()),
        }

    @staticmethod
    def _start_task(task: Task, device: Device) -> None:
        logger.info(f"Starting task {task.id} on device {device.ip}")
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                logger.error(f"Failed to connect to agent on {device.ip}:{device.agent_port} when starting task {task.id}")
                raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法启动任务', 503)

            response = agent.fio_start(str(task.id), task.config, task.device_path)
            if not response.get('success', False):
                logger.error(f"Agent failed to start task {task.id}, response: {response}")
                raise ApiError('CONNECTION_ERROR', 'Agent 启动 FIO 任务失败', 503)

            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.utcnow()
            logger.info(f"Task {task.id} started successfully on device {device.ip}")
        finally:
            agent.close()

    @staticmethod
    def _get_task_device(task: Task) -> Device:
        device = Device.query.get(task.device_id) if task.device_id else None
        if device is None:
            logger.error(f"Task {task.id} is associated with non-existent device ID: {task.device_id}")
            raise ApiError('NOT_FOUND', '任务关联设备不存在', 404)
        return device

    @staticmethod
    def _get_runtime_window_from_agent(task: Task) -> tuple[datetime | None, datetime | None]:
        if not task.device_id:
            return None, None

        device = Device.query.get(task.device_id)
        if device is None:
            return None, None

        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                return None, None
            status_payload = agent.fio_status(str(task.id))
            return (
                TaskService._parse_timestamp(status_payload.get('start_time')),
                TaskService._parse_timestamp(status_payload.get('end_time')),
            )
        except Exception as error:
            logger.warning('Failed to read execution window from agent for task %s: %s', task.id, error)
            return None, None
        finally:
            agent.close()

    @staticmethod
    def _get_runtime_window_from_db(task_id: int) -> tuple[datetime | None, datetime | None]:
        first_point = FioTrendData.query.filter_by(task_id=task_id).order_by(FioTrendData.timestamp.asc()).first()
        last_point = FioTrendData.query.filter_by(task_id=task_id).order_by(FioTrendData.timestamp.desc()).first()
        return (
            first_point.timestamp if first_point else None,
            last_point.timestamp if last_point else None,
        )

    @staticmethod
    def _replace_trend_points(task_id: int, points: list[dict[str, Any]]) -> None:
        logger.info(f"Replacing trend points for task {task_id}, received {len(points)} data points")
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
        logger.info(f"Trend points for task {task_id} replaced successfully")

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
                    logger.warning(f"Could not parse timestamp value: {value}")
                    return None
        return None