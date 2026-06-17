
from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class FwUpgradeTest(db.Model):
    __tablename__ = 'fw_upgrade_tests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, index=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    device_path = db.Column(db.String(255), nullable=False)
    fw_before = db.Column(db.String(64), nullable=True)
    fw_after = db.Column(db.String(64), nullable=True)
    fio_config = db.Column(db.JSON, nullable=False)
    result_before = db.Column(db.JSON, nullable=True)
    task_before_id = db.Column(db.Integer, nullable=True)
    result_after = db.Column(db.JSON, nullable=True)
    task_after_id = db.Column(db.Integer, nullable=True)
    regression_id = db.Column(db.Integer, db.ForeignKey('regression_results.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=beijing_now, onupdate=beijing_now)

    device = db.relationship('Device', backref='fw_tests')
    regression = db.relationship('RegressionResult', backref='fw_test')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'device_id': self.device_id,
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'fw_before': self.fw_before,
            'fw_after': self.fw_after,
            'fio_config': self.fio_config,
            'result_before': self.result_before,
            'task_before_id': self.task_before_id,
            'result_after': self.result_after,
            'task_after_id': self.task_after_id,
            'regression_id': self.regression_id,
            'status': self.status,
            'error': self.error,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
            'updated_at': to_beijing_iso(self.updated_at, assume_utc=True),
        }
