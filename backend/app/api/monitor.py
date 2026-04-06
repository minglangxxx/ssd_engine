from flask import request

from app.api import api_bp
from app.services.monitor_service import MonitorService
from app.utils.helpers import success_response


@api_bp.get('/monitor/hosts/<host>/metrics')
def get_host_metrics(host: str):
    return success_response(MonitorService.get_host_metrics(host, request.args.get('start'), request.args.get('end')))


@api_bp.get('/monitor/hosts/<host>/disks')
def get_disk_list(host: str):
    return success_response(MonitorService.get_disk_list(host))


@api_bp.get('/monitor/hosts/<host>/disks/<disk>/metrics')
def get_disk_metrics(host: str, disk: str):
    return success_response(MonitorService.get_disk_metrics(host, disk, request.args.get('start'), request.args.get('end')))


@api_bp.get('/monitor/hosts/<host>/summary')
def get_host_summary(host: str):
    return success_response(MonitorService.get_host_summary(host))
