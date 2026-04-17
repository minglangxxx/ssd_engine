from flask import request, send_file

from app.api import api_bp
from app.services.data_lifecycle import DataLifecycleService
from app.utils.helpers import get_pagination_params, success_response


@api_bp.get('/data')
def list_data_records():
    page, page_size = get_pagination_params(default_page_size=20)
    return success_response(DataLifecycleService.list_records(
        data_type=request.args.get('data_type'),
        status=request.args.get('status'),
        device_ip=request.args.get('device_ip'),
        task_id=request.args.get('task_id', type=int),
        disk_name=request.args.get('disk_name'),
        window_start=request.args.get('window_start'),
        window_end=request.args.get('window_end'),
        page=page,
        page_size=page_size,
    ))


@api_bp.get('/data/overview')
def get_data_overview():
    return success_response(DataLifecycleService.get_overview())


@api_bp.post('/data/download')
def download_data_records():
    payload = request.get_json(force=True) or {}
    archive_path = DataLifecycleService.build_download_archive(payload.get('ids', []))
    return send_file(archive_path, as_attachment=True, download_name='ssd-data.tar.gz')


@api_bp.post('/data/archive')
def archive_data_records():
    payload = request.get_json(force=True) or {}
    DataLifecycleService.manual_archive(payload.get('ids', []))
    return success_response(None, 204)


@api_bp.post('/data/delete')
def delete_data_records():
    payload = request.get_json(force=True) or {}
    DataLifecycleService.manual_delete(payload.get('ids', []))
    return success_response(None, 204)


@api_bp.post('/data/auto-archive-and-cleanup')
def auto_archive_and_cleanup():
    """
    手动触发自动归档和清理流程：
    1. 将超过 retention_days 的 active 数据自动归档到 JSON
    2. 删除超过 retention_days 的原始数据
    """
    from app.config import Config
    retention_days = int(Config.MONITOR_RETENTION_DAYS or 7)
    
    # 1. 自动归档
    archive_result = DataLifecycleService.auto_archive_ready_records(retention_days)
    
    # 2. 自动清理
    cleanup_result = DataLifecycleService.auto_cleanup(retention_days)
    
    return success_response({
        'archive': archive_result,
        'cleanup': cleanup_result
    })


@api_bp.post('/data/compress')
def compress_data_records():
    """
    触发数据压缩：将已归档的数据从 JSON 转换为 Parquet 格式
    """
    result = DataLifecycleService.auto_compress()
    return success_response(result)


@api_bp.post('/data/cleanup')
def cleanup_data():
    """
    触发数据清理：删除超过保留期的数据
    前置条件：超过保留期的 active 数据应先被自动归档
    """
    from app.config import Config
    retention_days = int(Config.MONITOR_RETENTION_DAYS or 7)
    result = DataLifecycleService.auto_cleanup(retention_days)
    return success_response(result)
