from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.group_task import GroupTaskCreateRequest
from app.services.group_task_service import GroupTaskService
from app.utils.helpers import ApiError, get_pagination_params, success_response


@api_bp.post('/group-tasks')
def create_group_task():
    try:
        payload = GroupTaskCreateRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    group = GroupTaskService.create(payload)
    return success_response(group.to_dict(include_sub_tasks=True), 202)


@api_bp.get('/group-tasks')
def list_group_tasks():
    page, page_size = get_pagination_params()
    data = GroupTaskService.list(
        status=request.args.get('status'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.get('/group-tasks/<int:group_task_id>')
def get_group_task(group_task_id: int):
    group = GroupTaskService.get(group_task_id)
    return success_response(group.to_dict(include_sub_tasks=True))


@api_bp.delete('/group-tasks/<int:group_task_id>')
def delete_group_task(group_task_id: int):
    GroupTaskService.delete(group_task_id)
    return success_response(None, 204)
