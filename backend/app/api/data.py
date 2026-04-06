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
