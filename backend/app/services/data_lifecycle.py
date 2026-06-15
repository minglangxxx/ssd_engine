from __future__ import annotations

import os
import tarfile
import json
from datetime import datetime, timedelta

from app.extensions import db
from app.models.data_record import DataRecord, DataStatus
from app.models.monitor_data import DiskMonitorSample
from app.utils.time import beijing_now, to_beijing_iso
from app.utils.logger import get_logger


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
            'expiring_soon_count': DataLifecycleService._count_expiring_soon(),
        }

    @staticmethod
    def _sum_size(status: str) -> int:
        result = db.session.query(db.func.sum(DataRecord.size_bytes)).filter_by(status=status).scalar()
        return result or 0

    @staticmethod
    def _count_expiring_soon() -> int:
        from app.config import Config
        retention_days = int(Config.MONITOR_RETENTION_DAYS or 7)
        threshold = datetime.utcnow() + timedelta(days=1)
        return DataRecord.query.filter(
            DataRecord.status == DataStatus.ACTIVE.value,
            DataRecord.expires_at.isnot(None),
            DataRecord.expires_at <= threshold,
        ).count()

    @staticmethod
    def list_records(
        data_type: str | None,
        status: str | None,
        device_ip: str | None,
        task_id: int | None,
        disk_name: str | None,
        window_start: str | None,
        window_end: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        query = DataRecord.query
        if data_type:
            query = query.filter_by(data_type=data_type)
        if status:
            query = query.filter_by(status=status)
        if device_ip:
            query = query.filter_by(device_ip=device_ip)
        if task_id is not None:
            query = query.filter_by(task_id=task_id)
        if disk_name:
            query = query.filter_by(disk_name=disk_name)
        parsed_start = DataLifecycleService._parse_datetime(window_start)
        parsed_end = DataLifecycleService._parse_datetime(window_end)
        if parsed_start is not None:
            query = query.filter(DataRecord.window_end >= parsed_start)
        if parsed_end is not None:
            query = query.filter(DataRecord.window_start <= parsed_end)
        pagination = query.order_by(DataRecord.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {'items': [item.to_dict() for item in pagination.items], 'total': pagination.total}

    @staticmethod
    def _export_record_data(record: DataRecord) -> list[dict]:
        """根据 DataRecord 的元数据从 DB 导出对应原始数据"""
        from app.models.fio_trend import FioTrendData
        from app.models.monitor_data import HostMonitorData, DiskMonitorSample
        from app.models.nvme_smart import NvmeSmartData

        if record.data_type == 'fio_trend' and record.task_id:
            query = FioTrendData.query.filter_by(task_id=record.task_id)
            if record.window_start:
                query = query.filter(FioTrendData.timestamp >= record.window_start)
            if record.window_end:
                query = query.filter(FioTrendData.timestamp <= record.window_end)
            return [item.to_dict() if hasattr(item, 'to_dict') else item for item in query.all()]

        elif record.data_type == 'disk_monitor' and record.device_ip:
            query = DiskMonitorSample.query.filter_by(
                device_ip=record.device_ip,
                disk_name=record.disk_name
       )
            if record.window_start:
                query = query.filter(DiskMonitorSample.event_time >= record.window_start)
            if record.window_end:
                query = query.filter(DiskMonitorSample.event_time <= record.window_end)
            return [item.to_dict() for item in query.all()]

        elif record.data_type == 'host_monitor' and record.device_ip:
            query = HostMonitorData.query.filter_by(device_ip=record.device_ip)
            if record.window_start:
                query = query.filter(HostMonitorData.created_at >= record.window_start)
            if record.window_end:
                query = query.filter(HostMonitorData.created_at <= record.window_end)
            return [item.to_dict() for item in query.all()]

        elif record.data_type == 'nvme_smart' and record.device_ip:
            query = NvmeSmartData.query.filter_by(
                device_ip=record.device_ip,
                disk_name=record.disk_name
            )
            if record.window_start:
                query = query.filter(NvmeSmartData.event_time >= record.window_start)
            if record.window_end:
                query = query.filter(NvmeSmartData.event_time <= record.window_end)
            return [item.to_dict() for item in query.all()]

        return []

    @staticmethod
    def manual_archive(record_ids: list[int]) -> list[int]:
        """
        归档记录：从数据库中读取数据，导出到 JSON 文件，然后标记为已归档。
        返回成功归档的记录 ID 列表。
        """
        logger = get_logger(__name__)
        os.makedirs(DATA_DIR, exist_ok=True)
        success_ids: list[int] = []

        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        for record in records:
            try:
                archive_path = os.path.join(
                    DATA_DIR,
                    f"archive_{record.id}_{record.data_type}_{beijing_now().strftime('%Y%m%d_%H%M%S')}.json"
                )

                data_to_archive = DataLifecycleService._export_record_data(record)

                # 写入 JSON 文件
                with open(archive_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'record_id': record.id,
                        'data_type': record.data_type,
                        'device_ip': record.device_ip,
                        'disk_name': record.disk_name,
                        'window_start': to_beijing_iso(record.window_start),
                        'window_end': to_beijing_iso(record.window_end),
                        'archived_at': beijing_now().isoformat(),
                        'data_count': len(data_to_archive),
                        'data': data_to_archive
                    }, f, ensure_ascii=False, indent=2, default=str)

                # 校验归档数据完整性
                if record.checksum and data_to_archive:
                    if not DataLifecycleService.verify_checksum(record, data_to_archive):
                        logger.warning(f'Checksum mismatch for record {record.id}, archive may be incomplete')

                # 更新 DataRecord
                from app.config import Config
                archive_retention = int(Config.ARCHIVE_RETENTION_DAYS or 30)
                record.status = DataStatus.ARCHIVED.value
                record.file_path = archive_path
                record.archived_at = beijing_now().replace(tzinfo=None)
                record.size_bytes = os.path.getsize(archive_path)
                record.expires_at = datetime.utcnow() + timedelta(days=archive_retention)
                success_ids.append(record.id)
                logger.info(f'Archived record {record.id} to {archive_path} ({record.size_bytes} bytes)')

            except Exception as e:
                logger.error(f'Failed to archive record {record.id}: {str(e)}')
                continue

        db.session.commit()
        return success_ids

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
        archive_path = os.path.join(DATA_DIR, f"download_{beijing_now().strftime('%Y%m%d_%H%M%S')}.tar.gz")
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        temp_files: list[str] = []
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                for record in records:
                    source = record.compressed_path or record.file_path
                    if source and os.path.exists(source):
                        tar.add(source, arcname=os.path.basename(source))
                    else:
                        # ACTIVE 记录：实时从 DB 导出数据生成临时 JSON
                        data = DataLifecycleService._export_record_data(record)
                        if data:
                            tmp_path = os.path.join(
                                DATA_DIR,
                                f"active_{record.id}_{record.data_type}_{beijing_now().strftime('%Y%m%d_%H%M%S')}.json"
                            )
                            with open(tmp_path, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'record_id': record.id,
                                    'data_type': record.data_type,
                                    'device_ip': record.device_ip,
                                    'disk_name': record.disk_name,
                                    'window_start': to_beijing_iso(record.window_start),
                                    'window_end': to_beijing_iso(record.window_end),
                                    'data_count': len(data),
                                    'data': data
                                }, f, ensure_ascii=False, indent=2, default=str)
                            tar.add(tmp_path, arcname=os.path.basename(tmp_path))
                            temp_files.append(tmp_path)
        finally:
            for tmp in temp_files:
                if os.path.exists(tmp):
                    os.remove(tmp)
        return archive_path

    @staticmethod
    def auto_compress(record_ids: list[int] | None = None) -> dict:
        """
        压缩已归档的数据：将 JSON 文件转换为 Parquet 格式。
        record_ids 为 None 时压缩所有 ARCHIVED 记录，否则只压缩指定记录。
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            logger = get_logger(__name__)
            logger.warning('pyarrow not installed, skipping compress')
            return {'status': 'skipped', 'reason': 'pyarrow not installed'}

        logger = get_logger(__name__)
        os.makedirs(DATA_DIR, exist_ok=True)

        compress_result = {
            'status': 'success',
            'records_compressed': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'compression_ratio': 0.0,
        }

        try:
            query = DataRecord.query.filter_by(status=DataStatus.ARCHIVED.value)
            if record_ids:
                query = query.filter(DataRecord.id.in_(record_ids))
            archived_records = query.all()

            for record in archived_records:
                if not record.file_path or not os.path.exists(record.file_path):
                    logger.warning(f'Archive file not found for record {record.id}')
                    continue

                try:
                    # 读取 JSON 文件
                    with open(record.file_path, 'r', encoding='utf-8') as f:
                        archive_data = json.load(f)

                    # 获取原始大小
                    original_size = os.path.getsize(record.file_path)
                    compress_result['total_size_before'] += original_size

                    # 转换数据列表为 PyArrow Table
                    data_list = archive_data.get('data', [])
                    if not data_list:
                        logger.info(f'No data to compress for record {record.id}')
                        continue

                    # 构建 Parquet 文件
                    parquet_path = os.path.join(
                        DATA_DIR,
                        f"compressed_{record.id}_{record.data_type}_{beijing_now().strftime('%Y%m%d_%H%M%S')}.parquet"
                    )

                    # 转换为 PyArrow Table
                    table = pa.Table.from_pylist(data_list)

                    # 写入 Parquet，使用 snappy 压缩
                    pq.write_table(table, parquet_path, compression='snappy')

                    # 获取压缩后的大小
                    compressed_size = os.path.getsize(parquet_path)
                    compress_result['total_size_after'] += compressed_size

                    # 验证压缩后的数据完整性
                    table_read = pq.read_table(parquet_path)
                    if table_read.num_rows != table.num_rows:
                        raise Exception(f'Data integrity check failed: {table_read.num_rows} != {table.num_rows}')

                    # 压缩前校验原始 JSON 数据完整性
                    original_data = archive_data.get('data', [])
                    if record.checksum and original_data:
                        if not DataLifecycleService.verify_checksum(record, original_data):
                            logger.error(f'Checksum mismatch for record {record.id} before compress')

                    # 更新 DataRecord
                    from app.config import Config
                    compress_retention = int(Config.COMPRESS_RETENTION_DAYS or 90)
                    record.status = DataStatus.COMPRESSED.value
                    record.compressed_path = parquet_path
                    record.compressed_at = beijing_now().replace(tzinfo=None)
                    record.storage_format = 'parquet'
                    record.size_bytes = compressed_size
                    record.expires_at = datetime.utcnow() + timedelta(days=compress_retention)

                    compress_result['records_compressed'] += 1
                    logger.info(
                        f'Compressed record {record.id}: {original_size} -> {compressed_size} bytes '
                        f'({100 * compressed_size/ original_size:.1f}%)'
                    )

                except Exception as e:
                    logger.error(f'Failed to compress record {record.id}: {str(e)}')
                    continue

            if compress_result['total_size_before'] > 0:
                compress_result['compression_ratio'] = (
                    1 - compress_result['total_size_after'] / compress_result['total_size_before']
                ) * 100

            db.session.commit()
            logger.info(
                f'auto_compress completed: {compress_result["records_compressed"]} records, '
                f'ratio={compress_result["compression_ratio"]:.1f}%'
            )
            return compress_result

        except Exception as e:
            db.session.rollback()
            logger.exception(f'auto_compress failed: {str(e)}')
            compress_result['status'] = 'failed'
            compress_result['error'] = str(e)
            return compress_result

    @staticmethod
    def verify_checksum(record: DataRecord, data: list | dict) -> bool:
        """验证数据的 checksum，防止数据损坏"""
        if not record.checksum:
            return True

        import hashlib
        data_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        computed_checksum = hashlib.sha256(data_json.encode('utf-8')).hexdigest()
        return computed_checksum == record.checksum

    @staticmethod
    def auto_archive_ready_records(retention_days: int) -> dict:
        """
        自动归档已过期的数据：
        - 找出所有 active 且 created_at < retention_days 的 DataRecord
        - 自动调用 manual_archive() 导出到 JSON
        - 更新状态为 archived
        """
        logger = get_logger(__name__)
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        active_old = DataRecord.query.filter(
            DataRecord.status == DataStatus.ACTIVE.value,
            DataRecord.created_at < cutoff
        ).all()

        if not active_old:
            logger.info('No old active records to archive')
            return {'archived_count': 0}

        archive_result = {
            'archived_ids': [r.id for r in active_old],
        }

        try:
            record_ids = [r.id for r in active_old]
            success_ids = DataLifecycleService.manual_archive(record_ids)
            archive_result['archived_count'] = len(success_ids)
            logger.info('Auto-archived %d old active records (out of %d)', len(success_ids), len(record_ids))
        except Exception as e:
            logger.error('Failed to auto-archive records: %s', str(e))
            archive_result['error'] = str(e)
            archive_result['archived_count'] = 0

        return archive_result

    @staticmethod
    def auto_cleanup(retention_days: int) -> dict:
        """
        数据清理流程：删除所有超过 retention_days 天的原始数据。
        只删除已被归档/压缩的 DataRecord 对应的时间窗口内数据，保护 ACTIVE 记录的数据完整性。
        """
        from app.models.fio_trend import FioTrendData
        from app.models.monitor_data import HostMonitorData
        from app.models.analysis import AiAnalysis
        from app.models.nvme_smart import NvmeSmartData

        logger = get_logger(__name__)
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        # 收集所有 ACTIVE 记录的时间窗口，清理时排除这些窗口
        active_records = DataRecord.query.filter_by(status=DataStatus.ACTIVE.value).all()
        protected_task_ids = {r.task_id for r in active_records if r.task_id and r.data_type == 'fio_trend'}
        protected_disk_windows = [
            (r.device_ip, r.disk_name, r.window_start, r.window_end)
            for r in active_records if r.data_type == 'disk_monitor' and r.device_ip
        ]
        protected_host_windows = [
            (r.device_ip, r.window_start, r.window_end)
            for r in active_records if r.data_type == 'host_monitor' and r.device_ip
        ]
        protected_smart_windows = [
            (r.device_ip, r.disk_name, r.window_start, r.window_end)
            for r in active_records if r.data_type == 'nvme_smart' and r.device_ip
        ]

        cleanup_result = {
            'cutoff': cutoff.isoformat(),
            'disk_monitor_samples': 0,
            'fio_trend_data': 0,
            'host_monitor_data': 0,
            'nvme_smart_data': 0,
            'ai_analyses': 0,
            'orphaned_data_records': 0,
            'total': 0,
        }

        try:
            # 1. 清理磁盘监控样本（排除 ACTIVE 记录的时间窗口）
            logger.info('Cleaning DiskMonitorSample older than %s', cutoff)
            from sqlalchemy import not_, and_ as sql_and
            disk_query = DiskMonitorSample.query.filter(DiskMonitorSample.event_time < cutoff)
            for _device_ip, _disk_name, _ws, _we in protected_disk_windows:
                if _ws and _we:
                    disk_query = disk_query.filter(
                        not_(sql_and(
                            DiskMonitorSample.device_ip == _device_ip,
                            DiskMonitorSample.disk_name == _disk_name,
                            DiskMonitorSample.event_time >= _ws,
                            DiskMonitorSample.event_time <= _we,
                        ))
                    )
            deleted_disk = disk_query.delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['disk_monitor_samples'] = deleted_disk
            logger.info('Deleted %d disk monitor samples', deleted_disk)

            # 2. 清理 FIO 趋势数据（排除 ACTIVE 任务的数据）
            logger.info('Cleaning FioTrendData older than %s', cutoff)
            fio_query = FioTrendData.query.filter(FioTrendData.timestamp < cutoff)
            if protected_task_ids:
                fio_query = fio_query.filter(FioTrendData.task_id.notin_(protected_task_ids))
            deleted_fio = fio_query.delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['fio_trend_data'] = deleted_fio
            logger.info('Deleted %d FIO trend records', deleted_fio)

            # 3. 清理主机监控数据（排除 ACTIVE 记录的时间窗口）
            logger.info('Cleaning HostMonitorData older than %s', cutoff)
            host_query = HostMonitorData.query.filter(HostMonitorData.created_at < cutoff)
            for _device_ip, _ws, _we in protected_host_windows:
                if _ws and _we:
                    host_query = host_query.filter(
                        not_(sql_and(
                            HostMonitorData.device_ip == _device_ip,
                            HostMonitorData.created_at >= _ws,
                            HostMonitorData.created_at <= _we,
                        ))
                    )
            deleted_host = host_query.delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['host_monitor_data'] = deleted_host
            logger.info('Deleted %d host monitor records', deleted_host)

            # 4. 清理过期的 AI 分析结果
            logger.info('Cleaning AiAnalysis older than %s', cutoff)
            deleted_analysis = AiAnalysis.query.filter(
                AiAnalysis.created_at < cutoff
            ).delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['ai_analyses'] = deleted_analysis
            logger.info('Deleted %d AI analysis records', deleted_analysis)

            # 5. 清理 NVMe SMART 数据（排除 ACTIVE 记录的时间窗口）
            logger.info('Cleaning NvmeSmartData older than %s', cutoff)
            smart_query = NvmeSmartData.query.filter(NvmeSmartData.event_time < cutoff)
            for _device_ip, _disk_name, _ws, _we in protected_smart_windows:
                if _ws and _we:
                    smart_query = smart_query.filter(
                        not_(sql_and(
                            NvmeSmartData.device_ip == _device_ip,
                            NvmeSmartData.disk_name == _disk_name,
                            NvmeSmartData.event_time >= _ws,
                            NvmeSmartData.event_time <= _we,
                        ))
                    )
            deleted_smart = smart_query.delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['nvme_smart_data'] = deleted_smart
            logger.info('Deleted %d NVMe SMART records', deleted_smart)

            # 6. 清理已过期的 DataRecord 元数据
            logger.info('Cleaning expired DataRecords')
            deleted_records = DataRecord.query.filter(
                DataRecord.expires_at.isnot(None),
                DataRecord.expires_at < datetime.utcnow()
            ).delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['orphaned_data_records'] = deleted_records
            logger.info('Deleted %d expired data records', deleted_records)

            cleanup_result['total'] = sum([
                cleanup_result['disk_monitor_samples'],
                cleanup_result['fio_trend_data'],
                cleanup_result['host_monitor_data'],
                cleanup_result['nvme_smart_data'],
                cleanup_result['ai_analyses'],
                cleanup_result['orphaned_data_records'],
            ])

            logger.info(
                'auto_cleanup completed: total=%d items (disk=%d, fio=%d, host=%d, smart=%d, analysis=%d, records=%d)',
                cleanup_result['total'],
                cleanup_result['disk_monitor_samples'],
                cleanup_result['fio_trend_data'],
                cleanup_result['host_monitor_data'],
                cleanup_result['nvme_smart_data'],
                cleanup_result['ai_analyses'],
                cleanup_result['orphaned_data_records'],
            )
            return cleanup_result

        except Exception as e:
            db.session.rollback()
            logger.exception('auto_cleanup failed: %s', str(e))
            cleanup_result['error'] = str(e)
            return cleanup_result

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
