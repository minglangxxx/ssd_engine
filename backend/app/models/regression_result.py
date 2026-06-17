from app.extensions import db
from app.utils.time import beijing_now, to_beijing_iso


class RegressionResult(db.Model):
    __tablename__ = 'regression_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    baseline_id = db.Column(db.Integer, db.ForeignKey('baselines.id'), nullable=False, index=True)
    iops_diff = db.Column(db.Float, nullable=True)
    bw_diff = db.Column(db.Float, nullable=True)
    lat_mean_diff = db.Column(db.Float, nullable=True)
    lat_p99_diff = db.Column(db.Float, nullable=True)
    verdict = db.Column(db.String(10), nullable=False)
    detail = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=beijing_now)

    task = db.relationship('Task', backref='regressions')
    baseline = db.relationship('Baseline', backref='regressions')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'baseline_id': self.baseline_id,
            'iops_diff': self.iops_diff,
            'bw_diff': self.bw_diff,
            'lat_mean_diff': self.lat_mean_diff,
            'lat_p99_diff': self.lat_p99_diff,
            'verdict': self.verdict,
            'detail': self.detail,
            'created_at': to_beijing_iso(self.created_at, assume_utc=True),
        }
