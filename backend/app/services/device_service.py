from datetime import datetime

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.utils.helpers import ApiError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeviceService:
    @staticmethod
    def list_all(refresh_agent_status: bool = False) -> list[Device]:
        logger.info("Listing all devices")
        devices = Device.query.order_by(Device.created_at.desc()).all()
        if refresh_agent_status:
            for device in devices:
                try:
                    DeviceService.get_agent_status(device.id)
                except Exception as error:
                    logger.warning('Failed to refresh agent status for device %s: %s', device.ip, error)
            devices = Device.query.order_by(Device.created_at.desc()).all()
        logger.info(f"Total {len(devices)} devices retrieved")
        return devices

    @staticmethod
    def create(data: dict) -> Device:
        logger.info(f"Creating new device with IP: {data['ip']}")
        existing = Device.query.filter_by(ip=data['ip']).first()
        if existing:
            logger.warning(f"Attempt to create device with existing IP: {data['ip']}")
            raise ApiError('VALIDATION_ERROR', '设备 IP 已存在', 400)

        device = Device(
            ip=data['ip'],
            name=data['name'],
            agent_port=data.get('agent_port', 8080),
        )
        db.session.add(device)
        db.session.commit()
        logger.info(f"Device {data['ip']} created successfully with ID: {device.id}")
        return device

    @staticmethod
    def get(device_id: int) -> Device:
        logger.debug(f"Retrieving device with ID: {device_id}")
        device = Device.query.get(device_id)
        if not device:
            logger.warning(f"Attempt to retrieve non-existent device with ID: {device_id}")
            raise ApiError('NOT_FOUND', '设备不存在', 404)
        logger.debug(f"Device {device.ip} retrieved successfully")
        return device

    @staticmethod
    def update(device_id: int, data: dict) -> Device:
        logger.info(f"Updating device with ID: {device_id}")
        device = DeviceService.get(device_id)
        if data.get('name') is not None:
            old_name = device.name
            device.name = data['name']
            logger.info(f"Device {device.ip} name updated from '{old_name}' to '{data['name']}'")
        if data.get('agent_port') is not None:
            old_port = device.agent_port
            device.agent_port = data['agent_port']
            logger.info(f"Device {device.ip} agent port updated from {old_port} to {data['agent_port']}")
        device.updated_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"Device {device.ip} updated successfully")
        return device

    @staticmethod
    def delete(device_id: int) -> None:
        logger.info(f"Deleting device with ID: {device_id}")
        device = DeviceService.get(device_id)
        db.session.delete(device)
        db.session.commit()
        logger.info(f"Device {device.ip} deleted successfully")

    @staticmethod
    def get_agent(device_or_ip, agent_port: int | None = None) -> AgentExecutor:
        if isinstance(device_or_ip, Device):
            ip = device_or_ip.ip
            port = device_or_ip.agent_port
            logger.debug(f"Getting agent for device {ip} on port {port}")
        else:
            ip = device_or_ip
            port = agent_port or 8080
            logger.debug(f"Getting agent for IP {ip} on port {port}")
        return AgentExecutor(f'http://{ip}:{port}')

    @staticmethod
    def test_connection(ip: str, user: str, password: str, agent_port: int = 8080) -> dict:
        logger.info(f"Testing connection to device {ip} on port {agent_port}")
        del user
        del password
        agent = DeviceService.get_agent(ip, agent_port)
        try:
            if not agent.test_connection():
                logger.warning(f"Connection test failed for device {ip} on port {agent_port}")
                return {'success': False, 'message': 'Agent 无响应'}
            health = agent.get_health()
            logger.info(f"Connection test successful for device {ip}, version: {health.get('version', '')}")
            return {
                'success': True,
                'message': '连接成功',
                'version': health.get('version', ''),
            }
        except Exception as error:
            logger.error(f"Exception during connection test for device {ip}: {str(error)}")
            return {'success': False, 'message': f'连接失败: {error}'}
        finally:
            agent.close()

    @staticmethod
    def get_info(device_id: int) -> dict:
        logger.info(f"Getting device info for device ID: {device_id}")
        device = DeviceService.get(device_id)
        data = device.to_dict()
        agent = DeviceService.get_agent(device)
        try:
            if agent.test_connection():
                logger.debug(f"Fetching disk list for device {device.ip}")
                disks = agent.get_disk_list()
                normalized_disks = []
                for disk in disks:
                    if isinstance(disk, dict):
                        name = disk.get('name') or ''
                        device_path = disk.get('device') or (f"/dev/{name}" if name else '')
                        normalized_disks.append({
                            'name': name,
                            'device': device_path,
                            'mountpoint': disk.get('mountpoint', ''),
                            'fstype': disk.get('fstype', ''),
                        })
                    elif isinstance(disk, str):
                        normalized_disks.append({
                            'name': disk,
                            'device': f'/dev/{disk}',
                            'mountpoint': '',
                            'fstype': '',
                        })
                data['disks'] = normalized_disks
                logger.info(f"Retrieved {len(disks)} disks for device {device.ip}")
            else:
                logger.warning(f"Agent connection failed when fetching device info for {device.ip}")
            return data
        finally:
            agent.close()

    @staticmethod
    def get_agent_status(device_id: int) -> dict:
        logger.info(f"Getting agent status for device ID: {device_id}")
        device = DeviceService.get(device_id)
        agent = DeviceService.get_agent(device)
        try:
            if agent.test_connection():
                health = agent.get_health()
                device.agent_status = 'online'
                device.agent_version = health.get('version', '')
                device.last_heartbeat = datetime.utcnow()
                logger.info(f"Agent for device {device.ip} is online, version: {device.agent_version}")
            else:
                device.agent_status = 'offline'
                logger.warning(f"Agent for device {device.ip} is offline")
            db.session.commit()
            return {
                'status': device.agent_status,
                'version': device.agent_version or '',
            }
        finally:
            agent.close()