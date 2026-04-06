from datetime import datetime

from app.extensions import db


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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'agent_status': self.agent_status,
            'agent_version': self.agent_version or '',
            'agent_port': self.agent_port,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'disks': [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
