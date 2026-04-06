from datetime import datetime

from app.extensions import db


class FioTrendData(db.Model):
    __tablename__ = 'fio_trend_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    iops_read = db.Column(db.Float, nullable=False, default=0)
    iops_write = db.Column(db.Float, nullable=False, default=0)
    iops_total = db.Column(db.Float, nullable=False, default=0)
    bw_read = db.Column(db.Float, nullable=False, default=0)
    bw_write = db.Column(db.Float, nullable=False, default=0)
    bw_total = db.Column(db.Float, nullable=False, default=0)
    lat_mean = db.Column(db.Float, nullable=False, default=0)
    lat_p99 = db.Column(db.Float, nullable=False, default=0)
    lat_max = db.Column(db.Float, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'iops_read': self.iops_read,
            'iops_write': self.iops_write,
            'iops_total': self.iops_total,
            'bw_read': self.bw_read,
            'bw_write': self.bw_write,
            'bw_total': self.bw_total,
            'lat_mean': self.lat_mean,
            'lat_p99': self.lat_p99,
            'lat_max': self.lat_max,
        }
