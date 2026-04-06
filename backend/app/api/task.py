from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.task import TaskCreateRequest
from app.services.task_service import TaskService
from app.utils.helpers import ApiError, get_pagination_params, success_response
from app.workloads.fio_workload import FioConfigError


@api_bp.get('/tasks')
def list_tasks():
    page, page_size = get_pagination_params()
    data = TaskService.list(
        status=request.args.get('status'),
        keyword=request.args.get('keyword'),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@api_bp.post('/tasks')
def create_task():
    try:
        payload = TaskCreateRequest.model_validate(request.get_json(force=True)).model_dump()
        task = TaskService.create(payload)
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    except FioConfigError as error:
        raise ApiError('FIO_CONFIG_ERROR', str(error), 400) from error
    return success_response(task.to_dict(), 201)


@api_bp.get('/tasks/<int:task_id>')
def get_task(task_id: int):
    return success_response(TaskService.get(task_id).to_dict())


@api_bp.get('/tasks/<int:task_id>/status')
def get_task_status(task_id: int):
    return success_response(TaskService.get_status(task_id))


@api_bp.delete('/tasks/<int:task_id>')
def delete_task(task_id: int):
    TaskService.delete(task_id)
    return success_response(None, 204)


@api_bp.get('/tasks/<int:task_id>/trend')
def get_task_trend(task_id: int):
    return success_response(TaskService.get_trend(
        task_id,
        start=request.args.get('start'),
        end=request.args.get('end'),
    ))


@api_bp.post('/tasks/<int:task_id>/stop')
def stop_task(task_id: int):
    return success_response(TaskService.stop(task_id).to_dict())


@api_bp.post('/tasks/<int:task_id>/retry')
def retry_task(task_id: int):
    return success_response(TaskService.retry(task_id).to_dict())
