from flask import request

from app.api import api_bp
from app.schemas.nvme import RunValidationRequest
from app.services.nvme_service import NvmeService
from app.services.nvme_validation_service import NvmeValidationService
from app.utils.helpers import ApiError, success_response, get_pagination_params


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


@api_bp.get('/devices/<int:device_id>/nvme/list')
def get_nvme_list(device_id: int):
    result = NvmeService.get_nvme_list(device_id)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/id-ctrl')
def get_nvme_id_ctrl(device_id: int, disk_name: str):
    result = NvmeService.get_nvme_id_ctrl(device_id, disk_name)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/id-ns')
def get_nvme_id_ns(device_id: int, disk_name: str):
    result = NvmeService.get_nvme_id_ns(device_id, disk_name)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/error-log')
def get_nvme_error_log(device_id: int, disk_name: str):
    result = NvmeService.get_nvme_error_log(device_id, disk_name)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/get-feature')
def get_nvme_feature(device_id: int, disk_name: str):
    fid = request.args.get('fid', '0x06')
    result = NvmeService.get_nvme_feature(device_id, disk_name, fid)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/fw-log')
def get_nvme_fw_log(device_id: int, disk_name: str):
    result = NvmeService.get_nvme_fw_log(device_id, disk_name)
    return success_response(result)


@api_bp.post('/devices/<int:device_id>/nvme/validate')
def run_nvme_validation(device_id: int):
    try:
        body = RunValidationRequest(**request.get_json(force=True))
    except Exception as e:
        raise ApiError('VALIDATION_ERROR', str(e), 400)
    result = NvmeValidationService.run_validation(device_id, body.disk_name, body.test_type)
    return success_response(result, 202)


@api_bp.get('/nvme-tests/<int:test_id>')
def get_nvme_test_result(test_id: int):
    result = NvmeValidationService.get_validation_result(test_id)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme-tests')
def list_nvme_tests(device_id: int):
    disk_name = request.args.get('disk_name')
    test_type = request.args.get('test_type')
    page, page_size = get_pagination_params()
    result = NvmeValidationService.list_validations(device_id, disk_name, test_type, page, page_size)
    return success_response(result)