from flask import request

from app.api import api_bp
from app.services.nvme_service import NvmeService
from app.utils.helpers import ApiError, success_response


@api_bp.get('/devices/<int:device_id>/smart/latest')
def get_smart_latest(device_id: int):
    result = NvmeService.get_latest_smart(device_id)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/smart/history')
def get_smart_history(device_id: int):
    disk_name = request.args.get('disk_name')
    if not disk_name:
        raise ApiError('MISSING_PARAM', 'disk_name is required', 400)
    start = request.args.get('start')
    end = request.args.get('end')
    result = NvmeService.get_smart_history(device_id, disk_name, start, end)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/smart/health-score')
def get_health_score(device_id: int):
    result = NvmeService.get_health_score(device_id)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/smart/alerts')
def get_smart_alerts(device_id: int):
    result = NvmeService.get_alerts(device_id)
    return success_response(result)