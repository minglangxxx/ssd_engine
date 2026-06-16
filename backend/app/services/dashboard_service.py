import time

from app.extensions import db
from app.models.device import Device
from app.models.task import Task, TaskStatus
from app.utils.time import to_beijing_iso

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 5

MAX_RECENT_CHART = 30
MAX_RECENT_TABLE = 10


class DashboardService:
    @staticmethod
    def get_summary() -> dict:
        now = time.time()
        cached = _cache.get('summary')
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        total = Device.query.count()
        online = Device.query.filter_by(agent_status='online').count()

        online_devices = Device.query.filter_by(agent_status='online').all()
        cpu_values = [d.cpu_usage for d in online_devices if d.cpu_usage is not None]
        mem_values = [d.memory_usage for d in online_devices if d.memory_usage is not None]
        avg_cpu = round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None
        avg_memory = round(sum(mem_values) / len(mem_values), 1) if mem_values else None

        total_tasks = Task.query.count()
        running_tasks = Task.query.filter_by(status=TaskStatus.RUNNING).count()
        success_tasks = Task.query.filter_by(status=TaskStatus.SUCCESS).count()
        failed_tasks = Task.query.filter_by(status=TaskStatus.FAILED).count()

        recent = Task.query.filter(
            Task.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILED])
        ).order_by(Task.created_at.desc()).limit(MAX_RECENT_CHART).all()

        recent = [t for t in recent if t.result and 'iops' in t.result]

        recent_tasks = []
        for t in recent[:MAX_RECENT_TABLE]:
            r = t.result or {}
            lat = r.get('latency') or {}
            bw_kib = r.get('bandwidth')
            bw_mib = round(bw_kib / 1024, 2) if bw_kib else None
            recent_tasks.append({
                'id': t.id,
                'name': t.name,
                'status': t.status,
                'iops': r.get('iops'),
                'bw_mib': bw_mib,
                'lat_mean_us': lat.get('mean'),
                'lat_max_us': lat.get('max'),
                'created_at': to_beijing_iso(t.created_at, assume_utc=True),
            })

        chart_data = []
        for t in reversed([t for t in recent if t.finished_at is not None]):
            r = t.result or {}
            lat = r.get('latency') or {}
            iops = r.get('iops')
            lat_mean_us = lat.get('mean')
            lat_ms = round(lat_mean_us / 1000, 3) if lat_mean_us else None
            chart_data.append({
                'time': to_beijing_iso(t.finished_at, assume_utc=True),
                'iops': iops,
                'lat_ms': lat_ms,
            })

        summary = {
            'agents': {'total': total, 'online': online},
            'avg_cpu': avg_cpu,
            'avg_memory': avg_memory,
            'tasks': {
                'total': total_tasks,
                'running': running_tasks,
                'success': success_tasks,
                'failed': failed_tasks,
            },
            'recent_tasks': recent_tasks,
            'chart_data': chart_data,
        }

        _cache['summary'] = (now, summary)
        return summary
