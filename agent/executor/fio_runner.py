from __future__ import annotations

import json
import subprocess
import threading
import time
from collections import deque


class FioTask:
    def __init__(self, task_id: str, config: dict, device: str):
        self.task_id = task_id
        self.config = config
        self.device = device
        self.status = 'pending'
        self.process: subprocess.Popen[str] | None = None
        self.result: dict | None = None
        self.error: str | None = None
        self.trend_data: deque[dict] = deque(maxlen=86400)
        self.start_time: float | None = None
        self.end_time: float | None = None


class FioRunner:
    def __init__(self):
        self.tasks: dict[str, FioTask] = {}

    def start(self, task_id: str, config: dict, device: str) -> None:
        task = FioTask(task_id, config, device)
        self.tasks[task_id] = task
        threading.Thread(target=self._run, args=(task,), daemon=True).start()

    def _run(self, task: FioTask) -> None:
        try:
            task.status = 'running'
            task.start_time = time.time()
            cmd = self._build_command(task.config, task.device)
            task.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while task.process.poll() is None:
                self._collect_placeholder_trend(task)
                time.sleep(1)
            stdout, stderr = task.process.communicate()
            if task.process.returncode == 0:
                task.status = 'success'
                task.result = self._parse_result(stdout)
            else:
                task.status = 'failed'
                task.error = stderr
        except Exception as error:
            task.status = 'failed'
            task.error = str(error)
        finally:
            task.end_time = time.time()

    def _collect_placeholder_trend(self, task: FioTask) -> None:
        task.trend_data.append({
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'iops_read': 0,
            'iops_write': 0,
            'iops_total': 0,
            'bw_read': 0,
            'bw_write': 0,
            'bw_total': 0,
            'lat_mean': 0,
            'lat_p99': 0,
            'lat_max': 0,
        })

    def _build_command(self, config: dict, device: str) -> str:
        parts = ['fio', f'--filename={device}', '--output-format=json']
        for key, value in config.items():
            if value is None:
                continue
            fio_key = key.replace('_', '-')
            if isinstance(value, bool):
                if value:
                    parts.append(f'--{fio_key}')
            else:
                parts.append(f'--{fio_key}={value}')
        return ' '.join(parts)

    def _parse_result(self, stdout: str) -> dict:
        try:
            data = json.loads(stdout)
            jobs = data.get('jobs', [])
            read_iops = sum(job.get('read', {}).get('iops', 0) for job in jobs)
            write_iops = sum(job.get('write', {}).get('iops', 0) for job in jobs)
            read_bw = sum(job.get('read', {}).get('bw', 0) for job in jobs)
            write_bw = sum(job.get('write', {}).get('bw', 0) for job in jobs)
            return {
                'iops': read_iops + write_iops,
                'bandwidth': read_bw + write_bw,
                'read_iops': read_iops,
                'write_iops': write_iops,
                'read_bw': read_bw,
                'write_bw': write_bw,
                'latency': {'mean': 0, 'min': 0, 'max': 0},
            }
        except Exception as error:
            return {'error': str(error)}

    def get_status(self, task_id: str) -> dict:
        task = self.tasks.get(task_id)
        if task is None:
            return {'status': 'not_found'}
        return {
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'start_time': task.start_time,
            'end_time': task.end_time,
        }

    def get_trend_data(self, task_id: str, start: str | None = None, end: str | None = None) -> list[dict]:
        del start
        del end
        task = self.tasks.get(task_id)
        return list(task.trend_data) if task else []

    def stop(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task and task.process:
            task.process.terminate()
            task.status = 'failed'
            task.error = 'User cancelled'
