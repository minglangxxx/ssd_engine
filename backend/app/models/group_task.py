from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class GroupTask(db.Model):
    __tablename__ = 'group_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    fio_config = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    summary = db.Column(db.JSON, nullable=True)
    total_count = db.Column(db.Integer, nullable=False, default=0)
    done_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=beijing_now, onupdate=beijing_now)

    sub_tasks = db.relationship('Task', backref='group_task', foreign_keys='Task.group_task_id')

    def to_dict(self, include_sub_tasks: bool = False) -> dict:
        d = {
            'id': self.id,
            'name': self.name,
            'fio_config': self.fio_config,
            'status': self.status,
            'summary': self.summary,
            'total_count': self.total_count,
            'done_count': self.done_count,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
            'updated_at': to_beijing_iso(self.updated_at, assume_utc=True),
        }
        if include_sub_tasks:
            d['sub_tasks'] = [t.to_dict() for t in self.sub_tasks]
        return d
