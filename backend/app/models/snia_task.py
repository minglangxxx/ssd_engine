import json
from datetime import datetime

from app.extensions import db
from app.utils.time import to_beijing_iso


class SniaTask(db.Model):
    __tablename__ = 'snia_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, index=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    device_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    current_phase = db.Column(db.String(20), nullable=True)
    current_round = db.Column(db.Integer, nullable=False, default=0)
    total_rounds = db.Column(db.Integer, nullable=False, default=25)
    iops_history = db.Column(db.Text, nullable=True)
    is_steady = db.Column(db.Boolean, nullable=False, default=False)
    config = db.Column(db.JSON, nullable=False)
    result = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    device = db.relationship('Device', backref='snia_tasks')

    def to_dict(self) -> dict:
        iops_list = json.loads(self.iops_history) if self.iops_history else []
        return {
            'id': self.id,
            'name': self.name,
            'device_id': self.device_id,
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'status': self.status,
            'current_phase': self.current_phase,
            'current_round': self.current_round,
            'total_rounds': self.total_rounds,
            'iops_history': iops_list,
            'is_steady': self.is_steady,
            'config': self.config,
            'result': self.result,
            'error': self.error,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
            'updated_at': to_beijing_iso(self.updated_at, assume_utc=True),
        }
