import time

import psutil

from logger import get_logger

logger = get_logger(__name__)


class DiskCollector:
    def __init__(self):
        self.prev = psutil.disk_io_counters(perdisk=True)
        self.prev_time = time.time()

    def _build_metrics(
        self,
        disk_name: str,
        current: dict,
        previous: dict,
        now: float,
        delta: float,
    ) -> dict:
        current_disk = current.get(disk_name)
        if current_disk is None:
            logger.warning('Disk metrics requested for unknown disk: %s', disk_name)
            return {'disk_name': disk_name}

        previous_disk = previous.get(disk_name) or current_disk
        read_ios = current_disk.read_count - previous_disk.read_count
        write_ios = current_disk.write_count - previous_disk.write_count
        return {
            'disk_name': disk_name,
            'timestamp': now,
            'disk_iops_read': read_ios / delta,
            'disk_iops_write': write_ios / delta,
            'disk_bw_read_bytes_per_sec': (current_disk.read_bytes - previous_disk.read_bytes) / delta,
            'disk_bw_write_bytes_per_sec': (current_disk.write_bytes - previous_disk.write_bytes) / delta,
            'disk_latency_read_ms': ((current_disk.read_time - previous_disk.read_time) / read_ios) if read_ios > 0 else 0,
            'disk_latency_write_ms': ((current_disk.write_time - previous_disk.write_time) / write_ios) if write_ios > 0 else 0,
            'disk_queue_depth': 0,
            'disk_await_ms': ((current_disk.read_time - previous_disk.read_time) + (current_disk.write_time - previous_disk.write_time)) / max(read_ios + write_ios, 1),
            'disk_svctm_ms': 0,
            'disk_util_percent': min((getattr(current_disk, 'busy_time', 0) - getattr(previous_disk, 'busy_time', 0)) / (delta * 10), 100),
            'disk_rrqm_per_sec': 0,
            'disk_wrqm_per_sec': 0,
        }

    def list_disks(self) -> list[dict]:
        try:
            disks: list[dict] = []
            seen: set[str] = set()
            for part in psutil.disk_partitions(all=False):
                name = part.device.split('/')[-1]
                if name in seen:
                    continue
                seen.add(name)
                disks.append({'name': name, 'device': part.device, 'mountpoint': part.mountpoint, 'fstype': part.fstype})
            for name in psutil.disk_io_counters(perdisk=True).keys():
                if name not in seen:
                    disks.append({'name': name, 'device': f'/dev/{name}', 'mountpoint': '', 'fstype': ''})
            return disks
        except Exception:
            logger.exception('Failed to list disks')
            raise

    def collect(self, disk_name: str) -> dict:
        try:
            current = psutil.disk_io_counters(perdisk=True)
            now = time.time()
            delta = max(now - self.prev_time, 0.001)
            result = self._build_metrics(disk_name, current, self.prev, now, delta)
            self.prev = current
            self.prev_time = now
            return result
        except Exception:
            logger.exception('Failed to collect disk metrics for %s', disk_name)
            raise

    def collect_all(self) -> dict:
        current = psutil.disk_io_counters(perdisk=True)
        now = time.time()
        delta = max(now - self.prev_time, 0.001)
        metrics = {
            disk['name']: self._build_metrics(disk['name'], current, self.prev, now, delta)
            for disk in self.list_disks()
        }
        self.prev = current
        self.prev_time = now
        return metrics
