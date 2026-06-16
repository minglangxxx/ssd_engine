from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.data_record import DataRecord, DataStatus
from app.models.device import Device
from app.models.fio_trend import FioTrendData
from app.models.task import Task, TaskStatus
from app.utils.db import db_released
from app.utils.helpers import ApiError
from app.workloads.fio_workload import FioConfigError, FioConfigValidator
from app.utils.logger import get_logger
from app.utils.time import to_beijing_iso
from app.utils.time import beijing_now, to_beijing_iso

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
            name=data.get('name') or f"FIO-{data['device_ip']}-{beijing_now().strftime('%Y%m%d%H%M%S')}",
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
        response = {
            'id': task.id,
            'status': task.status,
            'error': result.get('error'),
            'result': task.result,
            'updated_at': to_beijing_iso(task.updated_at, assume_utc=True),
        }
        if getattr(task, '_agent_offline', False) and task.status == TaskStatus.RUNNING:
            response['stale'] = True
        return response

    @staticmethod
    def get_raw(task_id: int) -> dict:
        logger.info(f"Getting raw output for task {task_id}")
        task = Task.query.get(task_id)
        if not task:
            raise ApiError('NOT_FOUND', '任务不存在', 404)
        if not task.raw_output:
            raise ApiError('NO_RAW', '该任务无原始输出', 404)
        return {
            'task_id': task.id,
            'raw_output': task.raw_output,
        }

    @staticmethod
    def stop(task_id: int) -> Task:
        logger.info(f"Stopping task {task_id}")
        task = TaskService.get(task_id)
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            logger.warning(f"Attempt to stop task {task_id} that is not running/pending. Current status: {task.status}")
            raise ApiError('VALIDATION_ERROR', '只有运行中或待启动任务可以停止', 400)

        device = TaskService._get_task_device(task)
        ip, port = device.ip, device.agent_port
        task_id_str = str(task_id)

        agent = AgentExecutor(f'http://{ip}:{port}')
        try:
            with db_released():
                if not agent.test_connection():
                    raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法停止任务', 503)
                response = agent.fio_stop(task_id_str)
                if not response.get('success', False):
                    raise ApiError('CONNECTION_ERROR', 'Agent 停止任务失败', 503)
                trend_data = agent.fio_trend(task_id_str)
        finally:
            agent.close()

        try:
            task = Task.query.get(task_id)
            task.status = TaskStatus.FAILED
            task.result = task.result or {}
            task.result['error'] = 'User cancelled'
            task.updated_at = datetime.utcnow()
            TaskService._replace_trend_points(task.id, trend_data)
            db.session.commit()
            logger.info(f"Task {task_id} stopped successfully")
            return task
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def retry(task_id: int) -> Task:
        logger.info(f"Retrying task {task_id}")
        task = TaskService.get(task_id)
        if task.status != TaskStatus.FAILED:
            logger.warning(f"Attempt to retry task {task_id} that is not in FAILED state. Current status: {task.status}")
            raise ApiError('VALIDATION_ERROR', '只有失败任务可以重试', 400)

        device = TaskService._get_task_device(task)
        device_id = device.id

        FioTrendData.query.filter_by(task_id=task.id).delete()
        task.result = None
        task.raw_output = None
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.utcnow()
        db.session.commit()

        device = Device.query.get(device_id)
        TaskService._start_task(task, device)
        db.session.commit()
        logger.info(f"Task {task_id} retry initiated successfully")
        return task

    @staticmethod
    def get_trend(task_id: int, start: str | None = None, end: str | None = None) -> list[dict]:
        logger.info(f"Getting trend data for task {task_id}, time range: {start} to {end}")
        task = TaskService.get(task_id)

        query = FioTrendData.query.filter_by(task_id=task.id)
        if start:
            query = query.filter(FioTrendData.timestamp >= TaskService._parse_timestamp(start))
        if end:
            query = query.filter(FioTrendData.timestamp <= TaskService._parse_timestamp(end))
        trend_data = [item.to_dict() for item in query.order_by(FioTrendData.timestamp.asc()).all()]
        logger.info(f"Retrieved {len(trend_data)} trend points from database for task {task_id}")
        return trend_data

    @staticmethod
    def refresh_runtime_state(task: Task) -> Task:
        logger.debug(f"Refreshing runtime state for task {task.id}, current status: {task.status}")
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING} or not task.device_id:
            return task

        device = TaskService._get_task_device(task)
        ip, port = device.ip, device.agent_port
        task_id = task.id
        task_id_str = str(task_id)

        agent = AgentExecutor(f'http://{ip}:{port}')
        agent_online = False
        status_payload = {}
        trend_data = None
        try:
            with db_released():
                if agent.test_connection():
                    agent_online = True
                    status_payload = agent.fio_status(task_id_str)
                    remote_status = str(status_payload.get('status', '')).lower()
                    if remote_status not in {'pending', 'running'}:
                        trend_data = agent.fio_trend(task_id_str)
        finally:
            agent.close()

        if not agent_online:
            stale_task = Task.query.get(task_id)
            stale_task._agent_offline = True
            return stale_task

        try:
            task = Task.query.get(task_id)
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
                if 'raw_output' in status_payload:
                    task.raw_output = status_payload.get('raw_output')
                task.started_at = TaskService._parse_timestamp(status_payload.get('start_time')) or task.started_at
                task.finished_at = TaskService._parse_timestamp(status_payload.get('end_time')) or task.finished_at
                task.data_window_start = task.started_at or task.data_window_start
                task.data_window_end = task.finished_at or task.data_window_end
                task.updated_at = datetime.utcnow()
            elif remote_status in {'failed', 'not_found'}:
                task.status = TaskStatus.FAILED
                task.result = task.result or {}
                if status_payload.get('error'):
                    task.result['error'] = status_payload.get('error')
                task.started_at = TaskService._parse_timestamp(status_payload.get('start_time')) or task.started_at
                task.finished_at = TaskService._parse_timestamp(status_payload.get('end_time')) or task.finished_at
                task.data_window_start = task.started_at or task.data_window_start
                task.data_window_end = task.finished_at or task.data_window_end
                task.updated_at = datetime.utcnow()
            else:
                logger.warning('Unknown remote status %s for task %s, treating as FAILED', remote_status, task.id)
                task.status = TaskStatus.FAILED
                task.result = task.result or {}
                task.result['error'] = f'Unknown remote status: {remote_status}'
                task.updated_at = datetime.utcnow()

            if trend_data:
                TaskService._replace_trend_points(task.id, trend_data)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        if remote_status == 'success':
            logger.info(f"Task {task.id} completed successfully")
        else:
            logger.warning(f"Task {task.id} failed: {status_payload.get('error', 'Unknown error')}")
        return task

    @staticmethod
    def get_execution_window(
        task: Task,
        window_before_seconds: int = 30,
        window_after_seconds: int = 30,
    ) -> dict[str, str | float | None]:
        start_time = task.started_at
        end_time = task.finished_at

        if start_time is None or end_time is None:
            agent_start, agent_end = TaskService._get_runtime_window_from_agent(task)
            start_time = start_time or agent_start
            end_time = end_time or agent_end

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
        ip, port = device.ip, device.agent_port
        task_id = task.id
        config = task.config
        device_path = task.device_path
        agent = AgentExecutor(f'http://{ip}:{port}')
        try:
            with db_released():
                if not agent.test_connection():
                    logger.error(f"Failed to connect to agent on {ip}:{port} when starting task {task_id}")
                    raise ApiError('CONNECTION_ERROR', 'Agent 无响应，无法启动任务', 503)
                response = agent.fio_start(str(task_id), config, device_path)
                if not response.get('success', False):
                    logger.error(f"Agent failed to start task {task_id}, response: {response}")
                    raise ApiError('CONNECTION_ERROR', 'Agent 启动 FIO 任务失败', 503)
        except Exception:
            try:
                task = Task.query.get(task_id)
                if task and task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                    task.status = TaskStatus.FAILED
                    task.result = task.result or {}
                    task.result['error'] = 'Failed to start task on agent'
                    task.updated_at = datetime.utcnow()
                    db.session.commit()
            except Exception:
                db.session.rollback()
            raise
        finally:
            agent.close()
        task = Task.query.get(task_id)
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.utcnow()
        logger.info(f"Task {task_id} started successfully on device {ip}")

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
        ip, port = device.ip, device.agent_port

        agent = AgentExecutor(f'http://{ip}:{port}')
        try:
            with db_released():
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
        task = Task.query.get(task_id)
        FioTrendData.query.filter_by(task_id=task_id).delete()
        first_timestamp: datetime | None = None
        last_timestamp: datetime | None = None
        for point in points:
            timestamp = TaskService._parse_timestamp(point.get('timestamp'))
            if timestamp is None:
                continue
            first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
            last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)
            db.session.add(FioTrendData(
                task_id=task_id,
                device_ip=task.device_ip if task is not None else '',
                device_path=task.device_path if task is not None else '',
                timestamp=timestamp,
                sample_interval_ms=max(1, int(point.get('sample_interval_ms') or 1000)),
                iops_read=float(point.get('iops_read', 0) or 0),
                iops_write=float(point.get('iops_write', 0) or 0),
                iops_total=float(point.get('iops_total', 0) or 0),
                bw_read=float(point.get('bw_read', 0) or 0),
                bw_write=float(point.get('bw_write', 0) or 0),
                bw_total=float(point.get('bw_total', 0) or 0),
                lat_mean=float(point.get('lat_mean', 0) or 0),
                lat_p99=float(point.get('lat_p99', 0) or 0),
                lat_max=float(point.get('lat_max', 0) or 0),
                source=str(point.get('source') or 'agent_fio'),
            ))
        if task is not None:
            if first_timestamp is not None:
                task.started_at = first_timestamp
                task.data_window_start = first_timestamp
            if last_timestamp is not None:
                task.finished_at = last_timestamp
                task.data_window_end = last_timestamp
            TaskService._sync_fio_trend_record(task, len(points), first_timestamp, last_timestamp)
        logger.info(f"Trend points for task {task_id} replaced successfully")

    @staticmethod
    def _sync_fio_trend_record(
        task: Task,
        point_count: int,
        first_timestamp: datetime | None,
        last_timestamp: datetime | None,
    ) -> None:
        record = DataRecord.query.filter_by(
            task_id=task.id,
            data_type='fio_trend',
            device_ip=task.device_ip,
            query_scope='task',
            status=DataStatus.ACTIVE.value,
        ).first()
        if record is None:
            record = DataRecord(
                task_id=task.id,
                data_type='fio_trend',
                device_ip=task.device_ip,
                status=DataStatus.ACTIVE.value,
                storage_backend='mysql',
                storage_format='table',
                hot_table_name='fio_trend_data',
                query_scope='task',
            )
            db.session.add(record)

        record.record_count = max(0, point_count)
        record.window_start = first_timestamp
        record.window_end = last_timestamp

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.fromtimestamp(float(value))
                except ValueError:
                    logger.warning(f"Could not parse timestamp value: {value}")
                    return None
        return None
