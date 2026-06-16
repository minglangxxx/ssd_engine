from datetime import datetime, timedelta

from app.extensions import db
from app.models.device import Device
from app.utils.logger import get_logger

logger = get_logger(__name__)

CHECK_INTERVAL_SECONDS = 30
OFFLINE_THRESHOLD_SECONDS = 90


def check_all_agents():
    """定时扫描：将超过阈值未心跳的设备标为 offline。调用方须提供 app context。"""
    threshold = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)
    updated = Device.query.filter(
        Device.agent_status == 'online',
        Device.last_heartbeat < threshold,
    ).update(
        {'agent_status': 'offline', 'cpu_usage': None, 'memory_usage': None}
    )
    db.session.commit()
    if updated > 0:
        logger.info('Marked %d devices offline (heartbeat timeout)', updated)
