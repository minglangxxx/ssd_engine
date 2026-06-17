
from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    ssh_user = db.Column(db.String(64), nullable=True)
    ssh_password = db.Column(db.String(255), nullable=True)
    agent_port = db.Column(db.Integer, nullable=False, default=8080)
    agent_status = db.Column(db.String(20), nullable=False, default='offline')
    agent_version = db.Column(db.String(32), nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    hostname = db.Column(db.String(64), nullable=True)
    os_version = db.Column(db.String(128), nullable=True)
    kernel_version = db.Column(db.String(128), nullable=True)
    cpu_usage = db.Column(db.Float, nullable=True)
    memory_usage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=beijing_now, onupdate=beijing_now)

    def to_dict(self, include_disks: bool = False) -> dict:
        return {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'agent_status': self.agent_status,
            'agent_version': self.agent_version or '',
            'agent_port': self.agent_port,
            'last_heartbeat': to_beijing_iso(self.last_heartbeat, assume_utc=True),
            'hostname': self.hostname,
            'os_version': self.os_version,
            'kernel_version': self.kernel_version,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
            'updated_at': to_beijing_iso(self.updated_at, assume_utc=True),
            'disks': [d.to_dict() for d in getattr(self, 'disks', [])] if include_disks else [],
        }
