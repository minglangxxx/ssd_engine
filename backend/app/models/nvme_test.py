from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class NvmeTest(db.Model):
    __tablename__ = 'nvme_tests'
    __table_args__ = (
        db.Index('idx_nvme_test_device', 'device_id', 'disk_name'),
        db.Index('idx_nvme_test_type', 'test_type'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    disk_name = db.Column(db.String(64), nullable=False)
    test_type = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='pending')
    result = db.Column(db.JSON, nullable=True)
    verdict = db.Column(db.String(16), nullable=True, default=None)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=beijing_now, onupdate=beijing_now)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'device_id': self.device_id,
            'disk_name': self.disk_name,
            'test_type': self.test_type,
            'status': self.status,
            'result': self.result,
            'verdict': self.verdict,
            'error': self.error,
            'created_at': to_beijing_iso(self.created_at),
            'updated_at': to_beijing_iso(self.updated_at),
        }
