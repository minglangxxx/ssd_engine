from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.snia_task import SniaTaskCreateRequest
from app.services.snia_service import SniaService
from app.utils.helpers import ApiError, get_pagination_params, success_response


@api_bp.post('/snia-tasks')
def create_snia_task():
    try:
        payload = SniaTaskCreateRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    task = SniaService.create(payload)
    return success_response(task.to_dict(), 202)


@api_bp.get('/snia-tasks')
def list_snia_tasks():
    page, page_size = get_pagination_params()
    data = SniaService.list(
        status=request.args.get('status'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.get('/snia-tasks/<int:snia_task_id>')
def get_snia_task(snia_task_id: int):
    task = SniaService.get(snia_task_id)
    return success_response(task.to_dict())


@api_bp.post('/snia-tasks/<int:snia_task_id>/abort')
def abort_snia_task(snia_task_id: int):
    task = SniaService.abort(snia_task_id)
    return success_response(task.to_dict())


@api_bp.get('/snia-tasks/<int:snia_task_id>/report')
def get_snia_report(snia_task_id: int):
    report = SniaService.report(snia_task_id)
    return success_response(report)
