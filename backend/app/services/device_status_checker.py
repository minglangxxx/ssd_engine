from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.extensions import db
from app.models.device import Device
from app.executors.agent_executor import AgentExecutor
from app.utils.logger import get_logger

logger = get_logger(__name__)

CHECK_INTERVAL_SECONDS = 30
MAX_WORKERS = 10


def check_all_agents():
    """Background task: concurrently check all device agent statuses and update DB."""
    from flask import current_app

    with current_app.app_context():
        devices = Device.query.all()
        if not devices:
            return

        # 提取设备信息后立即释放 DB 连接
        device_info = [(d.id, d.ip, d.agent_port) for d in devices]
        db.session.commit()

        # 并发 HTTP 检测（不占用 DB 连接）
        results = _check_devices_concurrently(device_info)

        # 重新获取 DB 连接更新结果
        for device_id, result in results.items():
            device = Device.query.get(device_id)
            if device is None:
                continue
            device.agent_status = result['status']
            device.agent_version = result['version']
            if result['status'] == 'online':
                device.last_heartbeat = datetime.utcnow()

        db.session.commit()
        logger.info("Agent status check completed: %d devices updated", len(results))


def _check_devices_concurrently(device_info: list[tuple]) -> dict[int, dict]:
    results: dict[int, dict] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_check_single_device, ip, port): device_id
            for device_id, ip, port in device_info
        }
        for future in as_completed(futures):
            device_id = futures[future]
            try:
                results[device_id] = future.result()
            except Exception as error:
                logger.warning("Check failed for device %s: %s", device_id, error)
                results[device_id] = {'status': 'offline', 'version': ''}

    return results


def _check_single_device(ip: str, agent_port: int) -> dict:
    agent = AgentExecutor(f'http://{ip}:{agent_port}')
    try:
        if agent.test_connection():
            health = agent.get_health()
            return {'status': 'online', 'version': health.get('version', '')}
        return {'status': 'offline', 'version': ''}
    except Exception:
        return {'status': 'offline', 'version': ''}
    finally:
        agent.close()
