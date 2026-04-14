from datetime import datetime

from app.extensions import db


class TaskStatus:
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=True, index=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    device_path = db.Column(db.String(255), nullable=False)
    config = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=TaskStatus.PENDING)
    result = db.Column(db.JSON, nullable=True)
    fault_type = db.Column(db.String(20), nullable=False, default='none')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    device = db.relationship('Device', backref='tasks')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'device_id': self.device_id,
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'config': self.config,
            'fault_type': self.fault_type,
            'result': self.result,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
