from flask import request
from pydantic import ValidationError

from app.api import api_bp
from app.schemas.device import DeviceAddRequest, DeviceTestConnectionRequest, DeviceUpdateRequest
from app.services.device_service import DeviceService
from app.utils.helpers import ApiError, success_response


@api_bp.get('/devices')
def list_devices():
    return success_response([device.to_dict() for device in DeviceService.list_all()])


@api_bp.post('/devices')
def create_device():
    try:
        payload = DeviceAddRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    
    device = DeviceService.create(payload)
    
    # 自动检测 Agent 状态
    DeviceService.get_agent_status(device.id)
    
    return success_response(device.to_dict(), 201)


@api_bp.put('/devices/<int:device_id>')
def update_device(device_id: int):
    try:
        payload = DeviceUpdateRequest.model_validate(request.get_json(force=True)).model_dump(exclude_none=True)
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    return success_response(DeviceService.update(device_id, payload).to_dict())


@api_bp.delete('/devices/<int:device_id>')
def delete_device(device_id: int):
    DeviceService.delete(device_id)
    return success_response(None, 204)


@api_bp.get('/devices/<int:device_id>/info')
def get_device_info(device_id: int):
    return success_response(DeviceService.get_info(device_id))


@api_bp.post('/devices/test-connection')
def test_device_connection():
    try:
        payload = DeviceTestConnectionRequest.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as error:
        raise ApiError('VALIDATION_ERROR', error.errors()[0]['msg'], 400) from error
    return success_response(DeviceService.test_connection(**payload))


@api_bp.get('/devices/<int:device_id>/agent-status')
def get_device_agent_status(device_id: int):
    return success_response(DeviceService.get_agent_status(device_id))