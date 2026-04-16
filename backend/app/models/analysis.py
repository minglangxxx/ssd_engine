from datetime import datetime

from app.extensions import db


class AiAnalysis(db.Model):
    __tablename__ = 'ai_analyses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    report = db.Column(db.Text, nullable=True)
    summary = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    data_window_start = db.Column(db.DateTime, nullable=True)
    data_window_end = db.Column(db.DateTime, nullable=True)
    input_manifest = db.Column(db.JSON, nullable=True)
    source_snapshot_version = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'status': self.status,
            'report': self.report,
            'summary': self.summary,
            'error': self.error,
            'data_window_start': self.data_window_start.isoformat() if self.data_window_start else None,
            'data_window_end': self.data_window_end.isoformat() if self.data_window_end else None,
            'input_manifest': self.input_manifest,
            'source_snapshot_version': self.source_snapshot_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
