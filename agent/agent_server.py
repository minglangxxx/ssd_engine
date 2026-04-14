# -*- coding: utf-8 -*-

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
from logger import get_logger, setup_agent_logger

# 初始化日志
setup_agent_logger()
logger = get_logger(__name__)


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
        start_ts = self._parse_timestamp(start) if start is not None else float('-inf')
        end_ts = self._parse_timestamp(end) if end is not None else float('inf')
        with self.lock:
            return [item for item in self.buffer if start_ts <= item.get('timestamp', 0) <= end_ts]

    def query_disk(self, disk_name: str, start: str | None = None, end: str | None = None) -> list[dict]:
        points = []
        for item in self.query(start, end):
            disk = item.get('disks', {}).get(disk_name)
            if disk:
                point = dict(disk)
                point.setdefault('timestamp', item.get('timestamp'))
                points.append(point)
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
    logger.info("Starting background monitoring collection")
    while True:
        try:
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
        except Exception as e:
            logger.error(f"Error in background monitoring collection: {str(e)}")
            time.sleep(1)  # 避免错误导致循环过快


threading.Thread(target=collect_background, daemon=True).start()


def run_command(command: str, timeout: int = 300) -> dict:
    logger.info(f"Executing command: {command[:100]}{'...' if len(command) > 100 else ''}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, check=False)
        logger.info(f"Command completed with return code: {result.returncode}")
        return {'stdout': result.stdout, 'stderr': result.stderr, 'return_code': result.returncode}
    except subprocess.TimeoutExpired:
        logger.warning(f"Command execution timed out after {timeout} seconds: {command[:50]}...")
        return {'stdout': '', 'stderr': f'命令执行超时（{timeout}秒）', 'return_code': -1}


@app.get('/health')
def health():
    logger.debug("Health check endpoint called")
    return jsonify({'status': 'healthy', 'version': Config.VERSION})


@app.post('/execute')
def execute():
    logger.info("Execute command endpoint called")
    payload = request.get_json(force=True) or {}
    command = payload.get('command', '')
    timeout = payload.get('timeout', 300)
    logger.info(f"Executing command via API: {command[:100]}{'...' if len(command) > 100 else ''}, timeout: {timeout}s")
    return jsonify(run_command(command, timeout))


@app.post('/fio/start')
def fio_start():
    logger.info("FIO start endpoint called")
    payload = request.get_json(force=True) or {}
    task_id = payload['task_id']
    device = payload['device']
    config = payload.get('config', {})
    logger.info(f"Starting FIO task {task_id} on device {device} with config: {list(config.keys()) if config else 'default'}")
    fio_runner.start(task_id, config, device)
    logger.info(f"FIO task {task_id} started successfully")
    return jsonify({'success': True, 'task_id': payload['task_id']})


@app.get('/fio/status/<task_id>')
def fio_status(task_id: str):
    logger.debug(f"FIO status endpoint called for task: {task_id}")
    status = fio_runner.get_status(task_id)
    logger.debug(f"Status for task {task_id}: {status.get('status', 'unknown')}")
    return jsonify(status)


@app.get('/fio/trend/<task_id>')
def fio_trend(task_id: str):
    logger.debug(f"FIO trend endpoint called for task: {task_id}")
    start = request.args.get('start')
    end = request.args.get('end')
    logger.debug(f"Requesting trend data for task {task_id}, time range: {start} to {end}")
    trend_data = fio_runner.get_trend_data(task_id, start, end)
    logger.debug(f"Returning {len(trend_data)} trend points for task {task_id}")
    return jsonify({'data': trend_data})


@app.post('/fio/stop/<task_id>')
def fio_stop(task_id: str):
    logger.info(f"FIO stop endpoint called for task: {task_id}")
    logger.info(f"Stopping FIO task {task_id}")
    fio_runner.stop(task_id)
    logger.info(f"FIO task {task_id} stopped successfully")
    return jsonify({'success': True})


@app.get('/monitor/host')
def monitor_host():
    logger.debug("Host monitoring endpoint called")
    snapshot = {
        'timestamp': time.time(),
        'cpu': cpu_collector.collect(),
        'memory': memory_collector.collect(),
        'network': network_collector.collect(),
        'system': system_collector.collect(),
    }
    logger.debug("Host monitoring data collected")
    return jsonify(snapshot)


@app.get('/monitor/host/history')
def monitor_host_history():
    logger.debug("Host history monitoring endpoint called")
    start = request.args.get('start')
    end = request.args.get('end')
    logger.debug(f"Requesting host history, time range: {start} to {end}")
    history_data = buffer.query(start, end)
    logger.debug(f"Returning {len(history_data)} host history records")
    return jsonify({'data': history_data})


@app.get('/monitor/disks')
def monitor_disks():
    logger.debug("Disk list monitoring endpoint called")
    disks = disk_collector.list_disks()
    logger.debug(f"Found {len(disks)} disks")
    return jsonify({'disks': disks})


@app.get('/monitor/disk/<disk_name>')
def monitor_disk(disk_name: str):
    logger.debug(f"Disk monitoring endpoint called for disk: {disk_name}")
    disk_data = disk_collector.collect(disk_name)
    logger.debug(f"Collected data for disk: {disk_name}")
    return jsonify(disk_data)


@app.get('/monitor/disk/<disk_name>/history')
def monitor_disk_history(disk_name: str):
    logger.debug(f"Disk history monitoring endpoint called for disk: {disk_name}")
    start = request.args.get('start')
    end = request.args.get('end')
    logger.debug(f"Requesting history for disk {disk_name}, time range: {start} to {end}")
    history_data = buffer.query_disk(disk_name, start, end)
    logger.debug(f"Returning {len(history_data)} history records for disk {disk_name}")
    return jsonify({'data': history_data})


@app.get('/smart/<path:device>')
def smart(device: str):
    logger.info(f"SMART data endpoint called for device: {device}")
    smart_data = smart_collector.collect(device)
    logger.info(f"SMART data collected for device: {device}")
    return jsonify(smart_data)


if __name__ == '__main__':
    logger.info(f"Starting agent server on {Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT)