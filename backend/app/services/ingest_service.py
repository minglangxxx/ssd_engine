from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models.data_record import DataRecord, DataStatus
from app.models.device import Device
from app.models.fio_trend import FioTrendData
from app.models.monitor_data import DiskMonitorSample
from app.models.task import Task
from app.utils.helpers import ApiError


class IngestService:
    @staticmethod
    def ingest_fio_trend(
        task_id: int,
        device_ip: str,
        device_path: str | None,
        sample_interval_ms: int,
        points: list[dict],
    ) -> dict:
        task = Task.query.get(task_id)
        if task is None:
            raise ApiError('NOT_FOUND', '任务不存在', 404)
        if task.device_ip != device_ip:
            raise ApiError('VALIDATION_ERROR', '设备 IP 与任务不匹配', 400)

        inserted_count = 0
        first_timestamp: datetime | None = None
        last_timestamp: datetime | None = None

        for point in points:
            timestamp = IngestService._parse_timestamp(point.get('timestamp'))
            if timestamp is None:
                continue
            first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
            last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)
            db.session.add(FioTrendData(
                task_id=task.id,
                device_ip=device_ip,
                device_path=device_path or task.device_path,
                timestamp=timestamp,
                sample_interval_ms=max(1, int(point.get('sample_interval_ms') or sample_interval_ms or 1000)),
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
            inserted_count += 1

        IngestService._update_task_window(task, first_timestamp, last_timestamp)
        if inserted_count > 0:
            record = IngestService._get_or_create_record(
                data_type='fio_trend',
                device_ip=device_ip,
                task_id=task.id,
                query_scope='task',
                disk_name=None,
            )
            IngestService._update_record_window(record, first_timestamp, last_timestamp, inserted_count)
            record.hot_table_name = 'fio_trend_data'
            record.storage_backend = 'mysql'
            record.storage_format = 'table'

        db.session.commit()
        return {
            'inserted': inserted_count,
            'task_id': task.id,
        }

    @staticmethod
    def ingest_disk_monitor(device_ip: str, samples: list[dict]) -> dict:
        device = Device.query.filter_by(ip=device_ip).first()
        if device is None:
            raise ApiError('NOT_FOUND', '设备不存在', 404)

        inserted_count = 0
        grouped_windows: dict[tuple[str, str], dict] = {}

        for sample in samples:
            disk_name = str(sample.get('disk_name') or '').strip()
            event_time = IngestService._parse_timestamp(sample.get('event_time') or sample.get('timestamp'))
            if not disk_name or event_time is None:
                continue

            task_id = sample.get('task_id')
            db.session.add(DiskMonitorSample(
                device_ip=device_ip,
                disk_name=disk_name,
                event_time=event_time,
                task_id=int(task_id) if task_id is not None else None,
                sample_interval_ms=max(1, int(sample.get('sample_interval_ms') or 1000)),
                disk_iops_read=float(sample.get('disk_iops_read', 0) or 0),
                disk_iops_write=float(sample.get('disk_iops_write', 0) or 0),
                disk_bw_read_bytes_per_sec=float(sample.get('disk_bw_read_bytes_per_sec', 0) or 0),
                disk_bw_write_bytes_per_sec=float(sample.get('disk_bw_write_bytes_per_sec', 0) or 0),
                disk_latency_read_ms=float(sample.get('disk_latency_read_ms', 0) or 0),
                disk_latency_write_ms=float(sample.get('disk_latency_write_ms', 0) or 0),
                disk_queue_depth=float(sample.get('disk_queue_depth', 0) or 0),
                disk_await_ms=float(sample.get('disk_await_ms', 0) or 0),
                disk_svctm_ms=float(sample.get('disk_svctm_ms', 0) or 0),
                disk_util_percent=float(sample.get('disk_util_percent', 0) or 0),
                disk_rrqm_per_sec=float(sample.get('disk_rrqm_per_sec', 0) or 0),
                disk_wrqm_per_sec=float(sample.get('disk_wrqm_per_sec', 0) or 0),
                source=str(sample.get('source') or 'agent_disk'),
            ))
            inserted_count += 1

            day_key = event_time.strftime('%Y%m%d')
            group_key = (disk_name, day_key)
            window = grouped_windows.setdefault(group_key, {
                'start': event_time,
                'end': event_time,
                'count': 0,
            })
            window['start'] = min(window['start'], event_time)
            window['end'] = max(window['end'], event_time)
            window['count'] += 1

        for (disk_name, _day_key), window in grouped_windows.items():
            record = IngestService._get_or_create_record(
                data_type='disk_monitor',
                device_ip=device_ip,
                task_id=None,
                query_scope='device_disk_day',
                disk_name=disk_name,
            )
            IngestService._update_record_window(record, window['start'], window['end'], window['count'])
            record.hot_table_name = 'disk_monitor_samples'
            record.storage_backend = 'mysql'
            record.storage_format = 'table'

        db.session.commit()
        return {
            'inserted': inserted_count,
            'device_ip': device_ip,
        }

    @staticmethod
    def flush_task(task_id: int, payload: dict) -> dict:
        task = Task.query.get(task_id)
        if task is None:
            raise ApiError('NOT_FOUND', '任务不存在', 404)

        started_at = IngestService._parse_timestamp(payload.get('started_at'))
        finished_at = IngestService._parse_timestamp(payload.get('finished_at'))
        data_window_start = IngestService._parse_timestamp(payload.get('data_window_start'))
        data_window_end = IngestService._parse_timestamp(payload.get('data_window_end'))

        if started_at is not None:
            task.started_at = started_at
        if finished_at is not None:
            task.finished_at = finished_at
        if data_window_start is not None:
            task.data_window_start = data_window_start
        if data_window_end is not None:
            task.data_window_end = data_window_end
        if payload.get('result') is not None:
            task.result = payload.get('result')
        if payload.get('status'):
            task.status = str(payload.get('status'))

        db.session.commit()
        return task.to_dict()

    @staticmethod
    def _get_or_create_record(
        data_type: str,
        device_ip: str,
        task_id: int | None,
        query_scope: str,
        disk_name: str | None,
    ) -> DataRecord:
        record = DataRecord.query.filter_by(
            data_type=data_type,
            device_ip=device_ip,
            task_id=task_id,
            query_scope=query_scope,
            disk_name=disk_name,
            status=DataStatus.ACTIVE.value,
        ).first()
        if record is not None:
            return record

        record = DataRecord(
            task_id=task_id,
            data_type=data_type,
            device_ip=device_ip,
            disk_name=disk_name,
            status=DataStatus.ACTIVE.value,
            storage_backend='mysql',
            storage_format='table',
            hot_table_name='fio_trend_data' if data_type == 'fio_trend' else 'disk_monitor_samples',
            query_scope=query_scope,
            record_count=0,
        )
        db.session.add(record)
        return record

    @staticmethod
    def _update_record_window(
        record: DataRecord,
        window_start: datetime | None,
        window_end: datetime | None,
        record_count_delta: int,
    ) -> None:
        if window_start is not None:
            record.window_start = window_start if record.window_start is None else min(record.window_start, window_start)
        if window_end is not None:
            record.window_end = window_end if record.window_end is None else max(record.window_end, window_end)
        record.record_count = int(record.record_count or 0) + max(0, record_count_delta)

    @staticmethod
    def _update_task_window(task: Task, start_time: datetime | None, end_time: datetime | None) -> None:
        if start_time is not None:
            task.started_at = start_time if task.started_at is None else min(task.started_at, start_time)
            task.data_window_start = task.started_at
        if end_time is not None:
            task.finished_at = end_time if task.finished_at is None else max(task.finished_at, end_time)
            task.data_window_end = task.finished_at

    @staticmethod
    def _parse_timestamp(value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            try:
                return datetime.fromisoformat(normalized.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.fromtimestamp(float(normalized))
                except ValueError:
                    return None
        return None