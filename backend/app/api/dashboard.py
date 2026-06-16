from app.api import api_bp
from app.services.dashboard_service import DashboardService
from app.utils.helpers import success_response


@api_bp.get('/dashboard/summary')
def dashboard_summary():
    return success_response(DashboardService.get_summary())
