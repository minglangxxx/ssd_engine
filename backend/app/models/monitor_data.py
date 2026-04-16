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


class DiskMonitorSample(db.Model):
    __tablename__ = 'disk_monitor_samples'
    __table_args__ = (
        db.Index('idx_disk_time', 'device_ip', 'disk_name', 'event_time'),
        db.Index('idx_task_time', 'task_id', 'event_time'),
        db.Index('idx_event_time', 'event_time'),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    disk_name = db.Column(db.String(64), nullable=False, index=True)
    event_time = db.Column(db.DateTime, nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True, index=True)
    sample_interval_ms = db.Column(db.Integer, nullable=False, default=1000)
    disk_iops_read = db.Column(db.Float, nullable=False, default=0)
    disk_iops_write = db.Column(db.Float, nullable=False, default=0)
    disk_bw_read_bytes_per_sec = db.Column(db.Float, nullable=False, default=0)
    disk_bw_write_bytes_per_sec = db.Column(db.Float, nullable=False, default=0)
    disk_latency_read_ms = db.Column(db.Float, nullable=False, default=0)
    disk_latency_write_ms = db.Column(db.Float, nullable=False, default=0)
    disk_queue_depth = db.Column(db.Float, nullable=False, default=0)
    disk_await_ms = db.Column(db.Float, nullable=False, default=0)
    disk_svctm_ms = db.Column(db.Float, nullable=False, default=0)
    disk_util_percent = db.Column(db.Float, nullable=False, default=0)
    disk_rrqm_per_sec = db.Column(db.Float, nullable=False, default=0)
    disk_wrqm_per_sec = db.Column(db.Float, nullable=False, default=0)
    source = db.Column(db.String(32), nullable=False, default='agent_disk')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'device_ip': self.device_ip,
            'disk_name': self.disk_name,
            'event_time': self.event_time.isoformat() if self.event_time else None,
            'timestamp': self.event_time.isoformat() if self.event_time else None,
            'task_id': self.task_id,
            'sample_interval_ms': self.sample_interval_ms,
            'disk_iops_read': self.disk_iops_read,
            'disk_iops_write': self.disk_iops_write,
            'disk_bw_read_bytes_per_sec': self.disk_bw_read_bytes_per_sec,
            'disk_bw_write_bytes_per_sec': self.disk_bw_write_bytes_per_sec,
            'disk_latency_read_ms': self.disk_latency_read_ms,
            'disk_latency_write_ms': self.disk_latency_write_ms,
            'disk_queue_depth': self.disk_queue_depth,
            'disk_await_ms': self.disk_await_ms,
            'disk_svctm_ms': self.disk_svctm_ms,
            'disk_util_percent': self.disk_util_percent,
            'disk_rrqm_per_sec': self.disk_rrqm_per_sec,
            'disk_wrqm_per_sec': self.disk_wrqm_per_sec,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
