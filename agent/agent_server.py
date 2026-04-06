from __future__ import annotations

import subprocess
import threading
import time
from collections import deque
from datetime import datetime

from flask import Flask, jsonify, request

from collectors.cpu_collector import CpuCollector
from collectors.disk_collector import DiskCollector
from collectors.memory_collector import MemoryCollector
from collectors.network_collector import NetworkCollector
from collectors.smart_collector import SmartCollector
from collectors.system_collector import SystemCollector
from config import Config
from executor.fio_runner import FioRunner


class MonitorRingBuffer:
    def __init__(self, maxlen: int = 3600):
        self.buffer: deque[dict] = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def append(self, snapshot: dict) -> None:
        with self.lock:
            self.buffer.append(snapshot)

    def _parse_timestamp(self, timestamp_str: str | None) -> float:
        """将时间戳字符串解析为浮点数时间戳，支持数值和ISO格式"""
        if not timestamp_str:
            return 0
        try:
            # 尝试直接转换为浮点数（原始格式）
            return float(timestamp_str)
        except ValueError:
            # 如果失败，则尝试解析ISO格式的时间字符串
            try:
                # 解析ISO格式时间字符串，如 "2026-04-06T11:54:38.063Z"
                # 替换Z为+00:00以适配fromisoformat
                iso_string = timestamp_str.replace('Z', '+00:00')
                if '+' in iso_string and len(iso_string.split('+')[1]) == 2:
                    iso_string += '00'  # 补全时区格式
                elif iso_string.endswith('+00'):
                    iso_string += ':00'
                
                # 对于基本ISO格式，如没有时区标识的情况，直接处理
                if 'Z' not in timestamp_str and '+' not in timestamp_str and '-' in timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str)
                else:
                    dt = datetime.fromisoformat(iso_string)
                return dt.timestamp()
            except ValueError:
                # 如果仍然失败，返回0
                return 0

    def query(self, start: str | None = None, end: str | None = None) -> list[dict]:
        start_ts = self._parse_timestamp(start)
        end_ts = self._parse_timestamp(end)
        with self.lock:
            return [item for item in self.buffer if start_ts <= item.get('timestamp', 0) <= end_ts]

    def query_disk(self, disk_name: str, start: str | None = None, end: str | None = None) -> list[dict]:
        points = []
        for item in self.query(start, end):
            disk = item.get('disks', {}).get(disk_name)
            if disk:
                points.append(disk)
        return points


app = Flask(__name__)

cpu_collector = CpuCollector()
memory_collector = MemoryCollector()
disk_collector = DiskCollector()
network_collector = NetworkCollector()
system_collector = SystemCollector()
smart_collector = SmartCollector()
fio_runner = FioRunner()
buffer = MonitorRingBuffer()


def collect_background() -> None:
    while True:
        snapshot = {
            'timestamp': time.time(),
            'cpu': cpu_collector.collect(),
            'memory': memory_collector.collect(),
            'network': network_collector.collect(),
            'system': system_collector.collect(),
            'disks': disk_collector.collect_all(),
        }
        buffer.append(snapshot)
        time.sleep(1)


threading.Thread(target=collect_background, daemon=True).start()


def run_command(command: str, timeout: int = 300) -> dict:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, check=False)
        return {'stdout': result.stdout, 'stderr': result.stderr, 'return_code': result.returncode}
    except subprocess.TimeoutExpired:
        return {'stdout': '', 'stderr': f'命令执行超时（{timeout}秒）', 'return_code': -1}


@app.get('/health')
def health():
    return jsonify({'status': 'healthy', 'version': Config.VERSION})


@app.post('/execute')
def execute():
    payload = request.get_json(force=True) or {}
    return jsonify(run_command(payload.get('command', ''), payload.get('timeout', 300)))


@app.post('/fio/start')
def fio_start():
    payload = request.get_json(force=True) or {}
    fio_runner.start(payload['task_id'], payload.get('config', {}), payload['device'])
    return jsonify({'success': True, 'task_id': payload['task_id']})


@app.get('/fio/status/<task_id>')
def fio_status(task_id: str):
    return jsonify(fio_runner.get_status(task_id))


@app.get('/fio/trend/<task_id>')
def fio_trend(task_id: str):
    return jsonify({'data': fio_runner.get_trend_data(task_id, request.args.get('start'), request.args.get('end'))})


@app.post('/fio/stop/<task_id>')
def fio_stop(task_id: str):
    fio_runner.stop(task_id)
    return jsonify({'success': True})


@app.get('/monitor/host')
def monitor_host():
    return jsonify({
        'timestamp': time.time(),
        'cpu': cpu_collector.collect(),
        'memory': memory_collector.collect(),
        'network': network_collector.collect(),
        'system': system_collector.collect(),
    })


@app.get('/monitor/host/history')
def monitor_host_history():
    return jsonify({'data': buffer.query(request.args.get('start'), request.args.get('end'))})


@app.get('/monitor/disks')
def monitor_disks():
    return jsonify({'disks': disk_collector.list_disks()})


@app.get('/monitor/disk/<disk_name>')
def monitor_disk(disk_name: str):
    return jsonify(disk_collector.collect(disk_name))


@app.get('/monitor/disk/<disk_name>/history')
def monitor_disk_history(disk_name: str):
    return jsonify({'data': buffer.query_disk(disk_name, request.args.get('start'), request.args.get('end'))})


@app.get('/smart/<path:device>')
def smart(device: str):
    return jsonify(smart_collector.collect(device))


if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT)