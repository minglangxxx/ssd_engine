from datetime import datetime

from app.extensions import db
from app.utils.time import to_beijing_iso


class NvmeSmartData(db.Model):
    __tablename__ = 'nvme_smart_data'
    __table_args__ = (
        db.Index('idx_smart_device_disk_time', 'device_ip', 'disk_name', 'event_time'),
        db.Index('idx_smart_event_time', 'event_time'),
        db.Index('idx_smart_device_ip', 'device_ip'),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_ip = db.Column(db.String(50), nullable=False)
    disk_name = db.Column(db.String(64), nullable=False)
    event_time = db.Column(db.DateTime, nullable=False)
    temperature = db.Column(db.SmallInteger, nullable=False, default=0)
    percentage_used = db.Column(db.SmallInteger, nullable=False, default=0)
    power_on_hours = db.Column(db.BigInteger, nullable=False, default=0)
    power_cycles = db.Column(db.BigInteger, nullable=False, default=0)
    media_errors = db.Column(db.BigInteger, nullable=False, default=0)
    critical_warning = db.Column(db.SmallInteger, nullable=False, default=0)
    data_units_read = db.Column(db.BigInteger, nullable=False, default=0)
    data_units_written = db.Column(db.BigInteger, nullable=False, default=0)
    available_spare = db.Column(db.SmallInteger, nullable=True)
    source = db.Column(db.String(32), nullable=False, default='agent_smart')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'disk_name': self.disk_name,
            'event_time': to_beijing_iso(self.event_time),
            'temperature': self.temperature,
            'percentage_used': self.percentage_used,
            'power_on_hours': self.power_on_hours,
            'power_cycles': self.power_cycles,
            'media_errors': self.media_errors,
            'critical_warning': self.critical_warning,
            'data_units_read': self.data_units_read,
            'data_units_written': self.data_units_written,
            'available_spare': self.available_spare,
        }