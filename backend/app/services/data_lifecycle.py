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
            'expiring_soon_count': 0,
        }

    @staticmethod
    def _sum_size(status: str) -> int:
        return sum(item.size_bytes for item in DataRecord.query.filter_by(status=status).all())

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
    def manual_archive(record_ids: list[int]) -> None:
        """
        归档记录：从数据库中读取数据，导出到 JSON 文件，然后标记为已归档
        """
        from app.models.fio_trend import FioTrendData
        from app.models.monitor_data import HostMonitorData
        
        logger = get_logger(__name__)
        os.makedirs(DATA_DIR, exist_ok=True)
        
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        for record in records:
            try:
                archive_path = os.path.join(
                    DATA_DIR,
                    f"archive_{record.id}_{record.data_type}_{beijing_now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                
                # 从数据库读取对应的数据
                data_to_archive = []
                
                if record.data_type == 'fio_trend' and record.task_id:
                    fio_records = FioTrendData.query.filter_by(task_id=record.task_id)
                    if record.window_start:
                        fio_records = fio_records.filter(FioTrendData.timestamp >= record.window_start)
                    if record.window_end:
                        fio_records = fio_records.filter(FioTrendData.timestamp <= record.window_end)
                    data_to_archive = [item.to_dict() if hasattr(item, 'to_dict') else item for item in fio_records.all()]
                
                elif record.data_type == 'disk_monitor_samples' and record.device_ip:
                    disk_records = DiskMonitorSample.query.filter_by(
                        device_ip=record.device_ip,
                        disk_name=record.disk_name
                    )
                    if record.window_start:
                        disk_records = disk_records.filter(DiskMonitorSample.event_time >= record.window_start)
                    if record.window_end:
                        disk_records = disk_records.filter(DiskMonitorSample.event_time <= record.window_end)
                    data_to_archive = [item.to_dict() for item in disk_records.all()]
                
                elif record.data_type == 'host_monitor_data' and record.device_ip:
                    host_records = HostMonitorData.query.filter_by(device_ip=record.device_ip)
                    if record.window_start:
                        host_records = host_records.filter(HostMonitorData.created_at >= record.window_start)
                    if record.window_end:
                        host_records = host_records.filter(HostMonitorData.created_at <= record.window_end)
                    data_to_archive = [item.to_dict() for item in host_records.all()]
                
                # 写入 JSON 文件
                with open(archive_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'record_id': record.id,
                        'data_type': record.data_type,
                        'device_ip': record.device_ip,
                        'window_start': to_beijing_iso(record.window_start),
                        'window_end': to_beijing_iso(record.window_end),
                        'archived_at': beijing_now().isoformat(),
                        'data_count': len(data_to_archive),
                        'data': data_to_archive
                    }, f, ensure_ascii=False, indent=2, default=str)
                
                # 更新 DataRecord
                record.status = DataStatus.ARCHIVED.value
                record.file_path = archive_path
                record.archived_at = datetime.utcnow()
                record.archived_at = beijing_now().replace(tzinfo=None)
                record.size_bytes = os.path.getsize(archive_path)
                logger.info(f'Archived record {record.id} to {archive_path} ({record.size_bytes} bytes)')
                
            except Exception as e:
                logger.error(f'Failed to archive record {record.id}: {str(e)}')
                continue
        
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
        archive_path = os.path.join(DATA_DIR, f"download_{beijing_now().strftime('%Y%m%d_%H%M%S')}.tar.gz")
        records = DataRecord.query.filter(DataRecord.id.in_(record_ids)).all()
        with tarfile.open(archive_path, 'w:gz') as tar:
            for record in records:
                source = record.compressed_path or record.file_path
                if source and os.path.exists(source):
                    tar.add(source, arcname=os.path.basename(source))
        return archive_path

    @staticmethod
    def auto_compress() -> dict:
        """
        自动压缩已归档的数据：将 JSON 文件转换为 Parquet 格式
        可以节省 60-80% 的存储空间
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
            # 查找所有已归档但未压缩的记录
            archived_records = DataRecord.query.filter_by(status=DataStatus.ARCHIVED.value).all()
            
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
                    
                    # 更新 DataRecord
                    record.status = DataStatus.COMPRESSED.value
                    record.compressed_path = parquet_path
                    record.storage_format = 'parquet'
                    record.size_bytes = compressed_size
                    
                    # 删除原始 JSON 文件（可选，保留备份）
                    # os.remove(record.file_path)
                    # record.file_path = None
                    
                    compress_result['records_compressed'] += 1
                    logger.info(
                        f'Compressed record {record.id}: {original_size} -> {compressed_size} bytes '
                        f'({100 * compressed_size / original_size:.1f}%)'
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
            return True  # 如果没有 checksum，跳过验证
        
        import hashlib
        import json
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
        
        这样超过 retention_days 的数据会先备份后删除
        """
        logger = get_logger(__name__)
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        # 查找所有超期的 active 数据
        active_old = DataRecord.query.filter(
            DataRecord.status == DataStatus.ACTIVE.value,
            DataRecord.created_at < cutoff
        ).all()
        
        if not active_old:
            logger.info('No old active records to archive')
            return {'archived_count': 0}
        
        archive_result = {
            'archived_count': len(active_old),
            'archived_ids': [r.id for r in active_old],
        }
        
        # 批量归档
        try:
            record_ids = [r.id for r in active_old]
            DataLifecycleService.manual_archive(record_ids)
            logger.info('Auto-archived %d old active records', len(record_ids))
        except Exception as e:
            logger.error('Failed to auto-archive records: %s', str(e))
            archive_result['error'] = str(e)
        
        return archive_result

    @staticmethod
    def auto_cleanup(retention_days: int) -> dict:
        """
        数据清理流程：删除所有超过 retention_days 天的原始数据
        前置条件：auto_archive_ready_records() 已经将超期的 active 数据备份为 archived
        
        清理策略：
        1. 删除超期的原始数据（DiskMonitorSample/FioTrendData/HostMonitorData）
        2. 删除超期的 AI 分析结果
        3. 删除过期的 DataRecord 元数据
        """
        from app.models.fio_trend import FioTrendData
        from app.models.monitor_data import HostMonitorData
        from app.models.analysis import AiAnalysis
        
        logger = get_logger(__name__)
        cutoff = datetime.now() - timedelta(days=retention_days)

        cleanup_result = {
            'cutoff': cutoff.isoformat(),
            'disk_monitor_samples': 0,
            'fio_trend_data': 0,
            'host_monitor_data': 0,
            'ai_analyses': 0,
            'orphaned_data_records': 0,
            'total': 0,
        }

        try:
            # 1. 清理磁盘监控样本（超过 retention_days 的直接删除）
            logger.info('Cleaning DiskMonitorSample older than %s', cutoff)
            deleted_disk = DiskMonitorSample.query.filter(
                DiskMonitorSample.event_time < cutoff
            ).delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['disk_monitor_samples'] = deleted_disk
            logger.info('Deleted %d disk monitor samples', deleted_disk)

            # 2. 清理 FIO 趋势数据
            logger.info('Cleaning FioTrendData older than %s', cutoff)
            deleted_fio = FioTrendData.query.filter(
                FioTrendData.timestamp < cutoff
            ).delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['fio_trend_data'] = deleted_fio
            logger.info('Deleted %d FIO trend records', deleted_fio)

            # 3. 清理主机监控数据
            logger.info('Cleaning HostMonitorData older than %s', cutoff)
            deleted_host = HostMonitorData.query.filter(
                HostMonitorData.created_at < cutoff
            ).delete(synchronize_session=False)
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

            # 5. 清理已标记为 expired 的 DataRecord 元数据
            logger.info('Cleaning expired DataRecords')
            deleted_records = DataRecord.query.filter(
                DataRecord.expires_at is not None,
                DataRecord.expires_at < datetime.utcnow()
            ).delete(synchronize_session=False)
            db.session.commit()
            cleanup_result['orphaned_data_records'] = deleted_records
            logger.info('Deleted %d expired data records', deleted_records)

            cleanup_result['total'] = sum([
                cleanup_result['disk_monitor_samples'],
                cleanup_result['fio_trend_data'],
                cleanup_result['host_monitor_data'],
                cleanup_result['ai_analyses'],
                cleanup_result['orphaned_data_records'],
            ])

            logger.info(
                'auto_cleanup completed: total=%d items (disk=%d, fio=%d, host=%d, analysis=%d, records=%d)',
                cleanup_result['total'],
                cleanup_result['disk_monitor_samples'],
                cleanup_result['fio_trend_data'],
                cleanup_result['host_monitor_data'],
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
