from datetime import datetime

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.utils.helpers import ApiError


class DeviceService:
    @staticmethod
    def list_all() -> list[Device]:
        return Device.query.order_by(Device.created_at.desc()).all()

    @staticmethod
    def create(data: dict) -> Device:
        existing = Device.query.filter_by(ip=data['ip']).first()
        if existing:
            raise ApiError('VALIDATION_ERROR', '设备 IP 已存在', 400)

        device = Device(
            ip=data['ip'],
            name=data['name'],
            agent_port=data.get('agent_port', 8080),
        )
        db.session.add(device)
        db.session.commit()
        return device

    @staticmethod
    def get(device_id: int) -> Device:
        device = Device.query.get(device_id)
        if not device:
            raise ApiError('NOT_FOUND', '设备不存在', 404)
        return device

    @staticmethod
    def update(device_id: int, data: dict) -> Device:
        device = DeviceService.get(device_id)
        if data.get('name') is not None:
            device.name = data['name']
        if data.get('agent_port') is not None:
            device.agent_port = data['agent_port']
        device.updated_at = datetime.utcnow()
        db.session.commit()
        return device

    @staticmethod
    def delete(device_id: int) -> None:
        device = DeviceService.get(device_id)
        db.session.delete(device)
        db.session.commit()

    @staticmethod
    def get_agent(device_or_ip, agent_port: int | None = None) -> AgentExecutor:
        if isinstance(device_or_ip, Device):
            ip = device_or_ip.ip
            port = device_or_ip.agent_port
        else:
            ip = device_or_ip
            port = agent_port or 8080
        return AgentExecutor(f'http://{ip}:{port}')

    @staticmethod
    def test_connection(ip: str, user: str, password: str, agent_port: int = 8080) -> dict:
        del user
        del password
        agent = DeviceService.get_agent(ip, agent_port)
        try:
            if not agent.test_connection():
                return {'success': False, 'message': 'Agent 无响应'}
            health = agent.get_health()
            return {
                'success': True,
                'message': '连接成功',
                'version': health.get('version', ''),
            }
        except Exception as error:
            return {'success': False, 'message': f'连接失败: {error}'}
        finally:
            agent.close()

    @staticmethod
    def get_info(device_id: int) -> dict:
        device = DeviceService.get(device_id)
        data = device.to_dict()
        agent = DeviceService.get_agent(device)
        try:
            if agent.test_connection():
                disks = agent.get_disk_list()
                data['disks'] = [disk.get('name') if isinstance(disk, dict) else disk for disk in disks]
            return data
        finally:
            agent.close()

    @staticmethod
    def get_agent_status(device_id: int) -> dict:
        device = DeviceService.get(device_id)
        agent = DeviceService.get_agent(device)
        try:
            if agent.test_connection():
                health = agent.get_health()
                device.agent_status = 'online'
                device.agent_version = health.get('version', '')
                device.last_heartbeat = datetime.utcnow()
            else:
                device.agent_status = 'offline'
            db.session.commit()
            return {
                'status': device.agent_status,
                'version': device.agent_version or '',
            }
        finally:
            agent.close()
