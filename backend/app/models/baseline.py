from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class Baseline(db.Model):
    __tablename__ = 'baselines'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    device_model = db.Column(db.String(128), nullable=True)
    firmware = db.Column(db.String(64), nullable=True)
    fio_config = db.Column(db.JSON, nullable=False)
    result = db.Column(db.JSON, nullable=False)
    source_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    device_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)
    created_by = db.Column(db.String(64), nullable=False, default='system')

    source_task = db.relationship('Task', backref='baselines')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'device_model': self.device_model,
            'firmware': self.firmware,
            'fio_config': self.fio_config,
            'result': self.result,
            'source_task_id': self.source_task_id,
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
            'created_by': self.created_by,
        }
