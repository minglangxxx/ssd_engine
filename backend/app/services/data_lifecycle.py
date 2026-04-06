from __future__ import annotations

import os
import tarfile
from datetime import datetime

from app.extensions import db
from app.models.data_record import DataRecord, DataStatus


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')


class DataLifecycleService:
    @staticmethod
    def get_overview() -> dict:
        return {
            'active_count': DataRecord.query.filter_by(status=DataStatus.ACTIVE.value).count(),
            'active_size_bytes': DataLifecycleService._sum_size(DataStatus.ACTIVE.value),
            'archived_count': DataRecord.query.filter_by(status=DataStatus.ARCHIVED.value).count(),
            'archived_size_bytes': DataLifecycleService._sum_size(DataStatus.ARCHIVED.value),
            'compressed_count': DataRecord.query.filter_by(status=DataStatus.COMPRESSED.value).count(),
            'compressed_size_bytes': DataLifecycleService._sum_size(DataStatus.COMPRESSED.value),
            'expiring_soon_count': 0,
        }

    @staticmethod
    def _sum_size(status: str) -> int:
        return sum(item.size_bytes for item in DataRecord.query.filter_by(status=status).all())

    @staticmethod
    def list_records(data_type: str | None, status: str | None, device_ip: str | None, page: int, page_size: int) -> dict:
        query = DataRecord.query
        if data_type:
            query = query.filter_by(data_type=data_type)
        if status:
            query = query.filter_by(status=status)
        if device_ip:
            query = query.filter_by(device_ip=device_ip)
        pagination = query.order_by(DataRecord.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {'items': [item.to_dict() for item in pagination.items], 'total': pagination.total}

    @staticmethod
    def manual_archive(record_ids: list[int]) -> None:
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        for record in records:
            record.status = DataStatus.ARCHIVED.value
            record.archived_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def manual_delete(record_ids: list[int]) -> None:
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        for record in records:
            for path in [record.file_path, record.compressed_path]:
                if path and os.path.exists(path):
                    os.remove(path)
            db.session.delete(record)
        db.session.commit()

    @staticmethod
    def build_download_archive(record_ids: list[int]) -> str:
        os.makedirs(DATA_DIR, exist_ok=True)
        archive_path = os.path.join(DATA_DIR, f"download_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz")
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        with tarfile.open(archive_path, 'w:gz') as tar:
            for record in records:
                source = record.compressed_path or record.file_path
                if source and os.path.exists(source):
                    tar.add(source, arcname=os.path.basename(source))
        return archive_path
