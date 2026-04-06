from datetime import datetime

from app.extensions import db


class HostMonitorData(db.Model):
    __tablename__ = 'host_monitor_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    data_type = db.Column(db.String(20), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'device_ip': self.device_ip,
            'data_type': self.data_type,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiskMonitorData(db.Model):
    __tablename__ = 'disk_monitor_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    disk_name = db.Column(db.String(64), nullable=False, index=True)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'device_ip': self.device_ip,
            'disk_name': self.disk_name,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
