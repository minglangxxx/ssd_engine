import time

import psutil


class DiskCollector:
    def __init__(self):
        self.prev = psutil.disk_io_counters(perdisk=True)
        self.prev_time = time.time()

    def list_disks(self) -> list[dict]:
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

    def collect(self, disk_name: str) -> dict:
        current = psutil.disk_io_counters(perdisk=True)
        now = time.time()
        delta = max(now - self.prev_time, 0.001)
        previous = self.prev.get(disk_name)
        current_disk = current.get(disk_name)
        if current_disk is None:
            return {'disk_name': disk_name}
        result = {'disk_name': disk_name, 'timestamp': now}
        if previous is None:
            previous = current_disk
        read_ios = current_disk.read_count - previous.read_count
        write_ios = current_disk.write_count - previous.write_count
        result.update({
            'disk_iops_read': read_ios / delta,
            'disk_iops_write': write_ios / delta,
            'disk_bw_read_bytes_per_sec': (current_disk.read_bytes - previous.read_bytes) / delta,
            'disk_bw_write_bytes_per_sec': (current_disk.write_bytes - previous.write_bytes) / delta,
            'disk_latency_read_ms': ((current_disk.read_time - previous.read_time) / read_ios) if read_ios > 0 else 0,
            'disk_latency_write_ms': ((current_disk.write_time - previous.write_time) / write_ios) if write_ios > 0 else 0,
            'disk_queue_depth': 0,
            'disk_await_ms': ((current_disk.read_time - previous.read_time) + (current_disk.write_time - previous.write_time)) / max(read_ios + write_ios, 1),
            'disk_svctm_ms': 0,
            'disk_util_percent': min((getattr(current_disk, 'busy_time', 0) - getattr(previous, 'busy_time', 0)) / (delta * 10), 100),
            'disk_rrqm_per_sec': 0,
            'disk_wrqm_per_sec': 0,
        })
        self.prev = current
        self.prev_time = now
        return result

    def collect_all(self) -> dict:
        return {disk['name']: self.collect(disk['name']) for disk in self.list_disks()}
