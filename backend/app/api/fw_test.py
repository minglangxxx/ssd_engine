from flask import request

from pydantic import ValidationError

from app.api import api_bp
from app.schemas.fw_test import FwTestCreateRequest
from app.services.fw_upgrade_service import FwUpgradeService
from app.utils.helpers import ApiError, get_pagination_params, success_response


@api_bp.post('/fw-tests')
def create_fw_test():
    try:
        payload = FwTestCreateRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    fw_test = FwUpgradeService.create(payload)
    return success_response(fw_test.to_dict(), 202)


@api_bp.get('/fw-tests')
def list_fw_tests():
    page, page_size = get_pagination_params()
    data = FwUpgradeService.list(
        status=request.args.get('status'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.get('/fw-tests/<int:fw_test_id>')
def get_fw_test(fw_test_id: int):
    return success_response(FwUpgradeService.get(fw_test_id).to_dict())


@api_bp.post('/fw-tests/<int:fw_test_id>/confirm-upgrade')
def confirm_fw_upgrade(fw_test_id: int):
    fw_test = FwUpgradeService.confirm_upgrade(fw_test_id)
    return success_response(fw_test.to_dict())


@api_bp.post('/fw-tests/<int:fw_test_id>/abort')
def abort_fw_test(fw_test_id: int):
    fw_test = FwUpgradeService.abort(fw_test_id)
    return success_response(fw_test.to_dict())


@api_bp.get('/fw-tests/<int:fw_test_id>/report')
def get_fw_test_report(fw_test_id: int):
    return success_response(FwUpgradeService.report(fw_test_id))
