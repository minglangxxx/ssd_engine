from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.baseline import BaselineCreateRequest
from app.services.baseline_service import BaselineService
from app.utils.helpers import ApiError, get_pagination_params, success_response


@api_bp.post('/baselines')
def create_baseline():
    try:
        payload = BaselineCreateRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    baseline = BaselineService.create(payload)
    return success_response(baseline.to_dict(), 201)


@api_bp.get('/baselines')
def list_baselines():
    page, page_size = get_pagination_params()
    data = BaselineService.list(
        keyword=request.args.get('keyword'),
        device_model=request.args.get('device_model'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.get('/baselines/<int:baseline_id>')
def get_baseline(baseline_id: int):
    return success_response(BaselineService.get(baseline_id).to_dict())


@api_bp.delete('/baselines/<int:baseline_id>')
def delete_baseline(baseline_id: int):
    BaselineService.delete(baseline_id)
    return success_response(None, 204)
