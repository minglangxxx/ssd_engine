from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.regression import RegressionRunRequest
from app.services.regression_service import RegressionService
from app.utils.helpers import ApiError, get_pagination_params, success_response


@api_bp.post('/regressions')
def run_regression():
    try:
        payload = RegressionRunRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    result = RegressionService.run(payload)
    return success_response(result.to_dict(), 201)


@api_bp.get('/regressions')
def list_regressions():
    page, page_size = get_pagination_params()
    data = RegressionService.list(
        verdict=request.args.get('verdict'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.get('/regressions/<int:regression_id>')
def get_regression(regression_id: int):
    return success_response(RegressionService.get(regression_id).to_dict())
