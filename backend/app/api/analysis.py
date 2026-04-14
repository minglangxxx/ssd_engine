from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.analysis import AiAnalysisRequest
from app.services.analysis_service import AnalysisService
from app.services.task_service import TaskService
from app.utils.helpers import ApiError, success_response


def _empty_analysis_result(task_id: int) -> dict:
    return {
        'id': None,
        'task_id': task_id,
        'status': 'idle',
        'report': '',
        'summary': {
            'performance_rating': 'normal',
            'issues_found': 0,
            'suggestions_count': 0,
        },
        'error': None,
        'created_at': None,
        'completed_at': None,
    }


@api_bp.post('/tasks/<int:task_id>/ai-analysis')
def analyze_task(task_id: int):
    try:
        payload = AiAnalysisRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    service = AnalysisService()
    result = service.analyze(task_id, **payload)
    return success_response(result.to_dict())


@api_bp.get('/tasks/<int:task_id>/ai-analysis')
def get_analysis_result(task_id: int):
    result = AnalysisService.get_latest(task_id)
    if result is None:
        TaskService.get(task_id)
        return success_response(_empty_analysis_result(task_id))
    return success_response(result.to_dict())


@api_bp.get('/tasks/<int:task_id>/ai-analysis/history')
def get_analysis_history(task_id: int):
    return success_response([item.to_dict() for item in AnalysisService.get_history(task_id)])
