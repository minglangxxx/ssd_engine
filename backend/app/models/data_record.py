from datetime import datetime
from enum import Enum

from app.extensions import db


class DataStatus(str, Enum):
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    COMPRESSED = 'compressed'


class DataRecord(db.Model):
    __tablename__ = 'data_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True, index=True)
    data_type = db.Column(db.String(50), nullable=False, index=True)
    device_ip = db.Column(db.String(50), nullable=False, index=True)
    disk_name = db.Column(db.String(64), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=DataStatus.ACTIVE.value, index=True)
    window_start = db.Column(db.DateTime, nullable=True, index=True)
    window_end = db.Column(db.DateTime, nullable=True, index=True)
    record_count = db.Column(db.BigInteger, nullable=False, default=0)
    storage_backend = db.Column(db.String(32), nullable=False, default='mysql')
    storage_format = db.Column(db.String(32), nullable=False, default='table')
    manifest_path = db.Column(db.String(500), nullable=True)
    hot_table_name = db.Column(db.String(128), nullable=True)
    checksum = db.Column(db.String(128), nullable=True)
    extra_metadata = db.Column('metadata', db.JSON, nullable=True)
    query_scope = db.Column(db.String(64), nullable=True, index=True)
    file_path = db.Column(db.String(500), nullable=True)
    compressed_path = db.Column(db.String(500), nullable=True)
    size_bytes = db.Column(db.BigInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    archived_at = db.Column(db.DateTime, nullable=True)
    compressed_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'data_type': self.data_type,
            'device_ip': self.device_ip,
            'disk_name': self.disk_name,
            'status': self.status,
            'window_start': self.window_start.isoformat() if self.window_start else None,
            'window_end': self.window_end.isoformat() if self.window_end else None,
            'record_count': self.record_count,
            'storage_backend': self.storage_backend,
            'storage_format': self.storage_format,
            'manifest_path': self.manifest_path,
            'hot_table_name': self.hot_table_name,
            'checksum': self.checksum,
            'metadata': self.extra_metadata,
            'query_scope': self.query_scope,
            'file_path': self.file_path,
            'compressed_path': self.compressed_path,
            'size_bytes': self.size_bytes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'compressed_at': self.compressed_at.isoformat() if self.compressed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }