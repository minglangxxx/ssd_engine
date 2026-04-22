from __future__ import annotations

from datetime import datetime
import re

from sqlalchemy import func

from app.executors.agent_executor import AgentExecutor
from app.extensions import db
from app.models.device import Device
from app.models.nvme_smart import NvmeSmartData
from app.utils.helpers import ApiError
from app.utils.logger import get_logger
from app.utils.time import beijing_now, to_beijing_iso

logger = get_logger(__name__)


def _normalize_nvme_disk_name(disk_name: str) -> str | None:
    name = (disk_name or '').strip()
    if not name:
        return None
    match = re.match(r'^(nvme\d+n\d+)', name)
    if match is None:
        return None
    return match.group(1)


class NvmeService:
    @staticmethod
    def get_latest_smart(device_id: int) -> dict:
        """
        获取设备所有 NVMe 磁盘的最新 SMART 快照
        包含健康评分和告警
        """
        device = Device.query.get(device_id)
        if device is None:
            raise ApiError('NOT_FOUND', '设备不存在', 404)

        device_ip = device.ip

        # 查询每个磁盘的最新记录
        subquery = (
            db.session.query(
                NvmeSmartData.disk_name,
                func.max(NvmeSmartData.event_time).label('max_time'),
            )
            .filter(NvmeSmartData.device_ip == device_ip)
            .group_by(NvmeSmartData.disk_name)
            .subquery()
        )

        latest_records = (
            NvmeSmartData.query
            .filter(NvmeSmartData.device_ip == device_ip)
            .join(
                subquery,
                db.and_(
                    NvmeSmartData.disk_name == subquery.c.disk_name,
                    NvmeSmartData.event_time == subquery.c.max_time,
                ),
            )
            .all()
        )

        # 若数据库无记录，尝试从 Agent 实时获取。
        # 这里不能依赖持久化的 agent_status，因为它可能是过期状态。
        if not latest_records:
            latest_records = NvmeService._fetch_smart_from_agent(device)

        disks = []
        for record in latest_records:
            smart_dict = record.to_dict()
            health = NvmeService.compute_health_score(smart_dict)
            alerts = NvmeService.evaluate_alerts(smart_dict, record.disk_name)
            disks.append({
                **smart_dict,
                'health_score': health['score'],
                'health_level': health['level'],
                'health_details': health['details'],
                'alerts': alerts,
            })

        return {
            'device_id': device.id,
            'device_ip': device_ip,
            'disks': disks,
        }

    @staticmethod
    def get_smart_history(device_id: int, disk_name: str, start: str | None, end: str | None) -> dict:
        """获取指定磁盘的 SMART 历史趋势"""
        device = Device.query.get(device_id)
        if device is None:
            raise ApiError('NOT_FOUND', '设备不存在', 404)

        query = NvmeSmartData.query.filter_by(
            device_ip=device.ip,
            disk_name=disk_name,
        )

        if start:
            parsed_start = NvmeService._parse_datetime(start)
            if parsed_start is not None:
                query = query.filter(NvmeSmartData.event_time >= parsed_start)
        if end:
            parsed_end = NvmeService._parse_datetime(end)
            if parsed_end is not None:
                query = query.filter(NvmeSmartData.event_time <= parsed_end)

        records = query.order_by(NvmeSmartData.event_time.asc()).all()

        return {
            'device_id': device.id,
            'disk_name': disk_name,
            'points': [r.to_dict() for r in records],
        }

    @staticmethod
    def compute_health_score(smart_data: dict) -> dict:
        """
        健康评分算法
        总分 100，分为 5 个子项：
        - temperature_score: 满分 30
        - wear_score: 满分 25
        - media_errors_score: 满分 25
        - critical_warning_score: 满分 15
        - spare_score: 满分 10
        """
        temperature = int(smart_data.get('temperature', 0) or 0)
        percentage_used = int(smart_data.get('percentage_used', 0) or 0)
        media_errors = int(smart_data.get('media_errors', 0) or 0)
        critical_warning = int(smart_data.get('critical_warning', 0) or 0)
        available_spare = smart_data.get('available_spare')

        # Temperature score: T<=50 → 30; 50<T<=80 → 30*(1-(T-50)/30); T>80 → 0
        if temperature <= 50:
            temp_score = 30.0
        elif temperature <= 80:
            temp_score = 30.0 * (1 - (temperature - 50) / 30)
        else:
            temp_score = 0.0

        # Wear score: 25*(1-percentage_used/100), min 0
        wear_score = max(0.0, 25.0 * (1 - percentage_used / 100))

        # Media errors score: 0 → 25, else → 0
        media_score = 25.0 if media_errors == 0 else 0.0

        # Warning score: 0 → 15, else → 0
        warning_score = 15.0 if critical_warning == 0 else 0.0

        # Spare score
        if available_spare is not None:
            spare_score = 10.0 * (int(available_spare) / 100)
        else:
            # 无值时：其他4项满分 → 5分，否则 → 0分
            other_max = 30.0 + 25.0 + 25.0 + 15.0  # = 95
            if temp_score + wear_score + media_score + warning_score >= other_max:
                spare_score = 5.0
            else:
                spare_score = 0.0

        total = temp_score + wear_score + media_score + warning_score + spare_score
        score = max(0, min(100, int(round(total))))

        if score >= 80:
            level = 'good'
        elif score >= 60:
            level = 'warning'
        elif score >= 40:
            level = 'critical'
        else:
            level = 'failed'

        return {
            'disk_name': smart_data.get('disk_name', ''),
            'score': score,
            'level': level,
            'details': {
                'temperature_score': round(temp_score, 1),
                'wear_score': round(wear_score, 1),
                'media_errors_score': round(media_score, 1),
                'critical_warning_score': round(warning_score, 1),
                'spare_score': round(spare_score, 1),
            },
        }

    @staticmethod
    def evaluate_alerts(smart_data: dict, disk_name: str) -> list[dict]:
        """临界告警评估，6条规则"""
        temperature = int(smart_data.get('temperature', 0) or 0)
        percentage_used = int(smart_data.get('percentage_used', 0) or 0)
        media_errors = int(smart_data.get('media_errors', 0) or 0)
        critical_warning = int(smart_data.get('critical_warning', 0) or 0)
        detected_at = to_beijing_iso(beijing_now()) or beijing_now().isoformat()

        alerts: list[dict] = []

        # Rule 1: critical_warning != 0 → critical
        if critical_warning != 0:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'critical',
                'field': 'critical_warning',
                'message': f'临界警告标志非零 (值={critical_warning})',
                'value': critical_warning,
                'threshold': 0,
                'detected_at': detected_at,
            })

        # Rule 2: media_errors > 0 → critical
        if media_errors > 0:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'critical',
                'field': 'media_errors',
                'message': f'检测到介质错误 (值={media_errors})',
                'value': media_errors,
                'threshold': 0,
                'detected_at': detected_at,
            })

        # Rule 3: percentage_used > 95 → critical
        if percentage_used > 95:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'critical',
                'field': 'percentage_used',
                'message': f'磨损程度超过95% (值={percentage_used}%)',
                'value': percentage_used,
                'threshold': 95,
                'detected_at': detected_at,
            })

        # Rule 4: percentage_used > 80 → warning (only if not already critical)
        if percentage_used > 80 and percentage_used <= 95:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'warning',
                'field': 'percentage_used',
                'message': f'磨损程度超过80% (值={percentage_used}%)',
                'value': percentage_used,
                'threshold': 80,
                'detected_at': detected_at,
            })

        # Rule 5: temperature > 80 → critical
        if temperature > 80:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'critical',
                'field': 'temperature',
                'message': f'温度超过80°C (值={temperature}°C)',
                'value': temperature,
                'threshold': 80,
                'detected_at': detected_at,
            })

        # Rule 6: temperature > 70 → warning (only if not already critical for same field)
        if temperature > 70 and temperature <= 80:
            alerts.append({
                'disk_name': disk_name,
                'severity': 'warning',
                'field': 'temperature',
                'message': f'温度超过70°C (值={temperature}°C)',
                'value': temperature,
                'threshold': 70,
                'detected_at': detected_at,
            })

        # 排序: critical 在前
        alerts.sort(key=lambda a: (0 if a['severity'] == 'critical' else 1, a['detected_at']), reverse=False)
        # 重新排序让critical在前，同级别按detected_at倒序
        alerts.sort(key=lambda a: (0 if a['severity'] == 'critical' else 1, a['detected_at']))

        return alerts

    @staticmethod
    def get_health_score(device_id: int) -> dict:
        """获取设备所有 NVMe 磁盘的健康评分"""
        latest = NvmeService.get_latest_smart(device_id)
        disks = []
        for disk in latest.get('disks', []):
            disks.append({
                'disk_name': disk.get('disk_name', ''),
                'score': disk.get('health_score', 0),
                'level': disk.get('health_level', 'failed'),
                'details': disk.get('health_details', {}),
            })
        return {
            'device_id': device_id,
            'disks': disks,
        }

    @staticmethod
    def get_alerts(device_id: int) -> dict:
        """获取设备所有 NVMe 磁盘的临界告警"""
        latest = NvmeService.get_latest_smart(device_id)
        all_alerts: list[dict] = []
        for disk in latest.get('disks', []):
            all_alerts.extend(disk.get('alerts', []))
        # 排序: critical在前，同级别按detected_at倒序
        all_alerts.sort(key=lambda a: (0 if a['severity'] == 'critical' else 1, a.get('detected_at', '')), reverse=False)
        return {
            'device_id': device_id,
            'alerts': all_alerts,
        }

    @staticmethod
    def _fetch_smart_from_agent(device: Device) -> list[NvmeSmartData]:
        """从 Agent 实时获取 SMART 数据，构造 NvmeSmartData 对象（不入库）"""
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        try:
            if not agent.test_connection():
                return []
            # 获取磁盘列表
            disks = agent.get_disk_list()
            records = []
            now = datetime.utcnow()
            seen: set[str] = set()
            for disk in disks:
                raw_disk_name = disk.get('name', '') if isinstance(disk, dict) else str(disk)
                disk_name = _normalize_nvme_disk_name(raw_disk_name)
                if disk_name is None or disk_name in seen:
                    continue
                seen.add(disk_name)
                try:
                    smart_raw = agent.get_smart(f'/dev/{disk_name}')
                    if not smart_raw:
                        continue
                    record = NvmeSmartData(
                        device_ip=device.ip,
                        disk_name=disk_name,
                        event_time=now,
                        temperature=int(smart_raw.get('temperature', 0) or 0),
                        percentage_used=int(smart_raw.get('percentage_used', 0) or 0),
                        power_on_hours=int(smart_raw.get('power_on_hours', 0) or 0),
                        power_cycles=int(smart_raw.get('power_cycles', 0) or 0),
                        media_errors=int(smart_raw.get('media_errors', 0) or 0),
                        critical_warning=int(smart_raw.get('critical_warning', 0) or 0),
                        data_units_read=int(smart_raw.get('data_units_read', 0) or 0),
                        data_units_written=int(smart_raw.get('data_units_written', 0) or 0),
                        available_spare=int(smart_raw['available_spare']) if smart_raw.get('available_spare') is not None else None,
                        source='agent_realtime',
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning('Failed to get SMART for %s from agent %s: %s', disk_name, device.ip, e)
            return records
        finally:
            agent.close()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                from datetime import timezone, timedelta
                _CST = timezone(timedelta(hours=8))
                return dt.astimezone(_CST).replace(tzinfo=None)
            return dt
        except ValueError:
            return None