from datetime import datetime

from app.extensions import db
from app.utils.time import to_beijing_iso


class FioTrendData(db.Model):
    __tablename__ = 'fio_trend_data'
    __table_args__ = (
        db.Index('idx_fio_trend_task_time', 'task_id', 'timestamp'),
        db.Index('idx_fio_trend_device_time', 'device_ip', 'timestamp'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    device_ip = db.Column(db.String(50), nullable=False, default='', index=True)
    device_path = db.Column(db.String(255), nullable=False, default='')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    sample_interval_ms = db.Column(db.Integer, nullable=False, default=1000)
    iops_read = db.Column(db.Float, nullable=False, default=0)
    iops_write = db.Column(db.Float, nullable=False, default=0)
    iops_total = db.Column(db.Float, nullable=False, default=0)
    bw_read = db.Column(db.Float, nullable=False, default=0)
    bw_write = db.Column(db.Float, nullable=False, default=0)
    bw_total = db.Column(db.Float, nullable=False, default=0)
    lat_mean = db.Column(db.Float, nullable=False, default=0)
    lat_p99 = db.Column(db.Float, nullable=False, default=0)
    lat_max = db.Column(db.Float, nullable=False, default=0)
    source = db.Column(db.String(32), nullable=False, default='agent_fio')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'timestamp': to_beijing_iso(self.timestamp),
            'sample_interval_ms': self.sample_interval_ms,
            'iops_read': self.iops_read,
            'iops_write': self.iops_write,
            'iops_total': self.iops_total,
            'bw_read': self.bw_read,
            'bw_write': self.bw_write,
            'bw_total': self.bw_total,
            'lat_mean': self.lat_mean,
            'lat_p99': self.lat_p99,
            'lat_max': self.lat_max,
            'source': self.source,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
        }
