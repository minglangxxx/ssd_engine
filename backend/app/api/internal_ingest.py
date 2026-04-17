from flask import request

from app.api import api_bp
from app.services.ingest_service import IngestService
from app.utils.helpers import success_response


@api_bp.post('/internal/ingest/fio-trend')
def ingest_fio_trend():
    payload = request.get_json(force=True) or {}
    result = IngestService.ingest_fio_trend(
        task_id=int(payload.get('task_id')),
        device_ip=str(payload.get('device_ip') or ''),
        device_path=payload.get('device_path'),
        sample_interval_ms=int(payload.get('sample_interval_ms') or 1000),
        points=payload.get('points') or [],
    )
    return success_response(result, 201)


@api_bp.post('/internal/ingest/disk-monitor')
def ingest_disk_monitor():
    payload = request.get_json(force=True) or {}
    result = IngestService.ingest_disk_monitor(
        device_ip=str(payload.get('device_ip') or ''),
        samples=payload.get('samples') or [],
    )
    return success_response(result, 201)


@api_bp.post('/internal/ingest/host-monitor')
def ingest_host_monitor():
    """入库主机监控数据"""
    payload = request.get_json(force=True) or {}
    result = IngestService.ingest_host_monitor(
        device_ip=str(payload.get('device_ip') or ''),
        samples=payload.get('samples') or [],
    )
    return success_response(result, 201)


@api_bp.post('/internal/ingest/flush-task')
def flush_task():
    payload = request.get_json(force=True) or {}
    task_id = int(payload.get('task_id'))
    result = IngestService.flush_task(task_id, payload)
    return success_response(result)