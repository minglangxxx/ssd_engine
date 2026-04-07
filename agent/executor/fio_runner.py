from __future__ import annotations

import json
import subprocess
import threading
import time
from collections import deque

from ..logger import get_logger

logger = get_logger(__name__)


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
        logger.info("FIO Runner initialized")

    def start(self, task_id: str, config: dict, device: str) -> None:
        logger.info(f"Starting FIO task {task_id} on device {device}")
        task = FioTask(task_id, config, device)
        self.tasks[task_id] = task
        logger.debug(f"FIO task {task_id} added to task list")
        threading.Thread(target=self._run, args=(task,), daemon=True).start()
        logger.debug(f"Thread started for FIO task {task_id}")

    def _run(self, task: FioTask) -> None:
        logger.info(f"Running FIO task {task.task_id}")
        try:
            task.status = 'running'
            task.start_time = time.time()
            logger.info(f"FIO task {task.task_id} set to running state")
            
            cmd = self._build_command(task.config, task.device)
            logger.debug(f"Built FIO command for task {task.task_id}: {cmd[:100]}...")
            
            task.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info(f"FIO process started for task {task.task_id}")
            
            while task.process.poll() is None:
                self._collect_placeholder_trend(task)
                time.sleep(1)
            logger.debug(f"FIO process for task {task.task_id} finished, return code: {task.process.returncode}")
            
            stdout, stderr = task.process.communicate()
            if task.process.returncode == 0:
                task.status = 'success'
                task.result = self._parse_result(stdout)
                logger.info(f"FIO task {task.task_id} completed successfully")
            else:
                task.status = 'failed'
                task.error = stderr
                logger.error(f"FIO task {task.task_id} failed with error: {stderr}")
        except Exception as error:
            logger.error(f"Exception occurred while running FIO task {task.task_id}: {str(error)}")
            task.status = 'failed'
            task.error = str(error)
        finally:
            task.end_time = time.time()
            logger.info(f"FIO task {task.task_id} ended at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.end_time))}")

    def _collect_placeholder_trend(self, task: FioTask) -> None:
        # 在实际FIO运行期间收集趋势数据的占位符
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
        logger.debug(f"Building FIO command for device {device}")
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
        cmd = ' '.join(parts)
        logger.debug(f"FIO command built: {cmd}")
        return cmd

    def _parse_result(self, stdout: str) -> dict:
        logger.debug("Parsing FIO result")
        try:
            data = json.loads(stdout)
            jobs = data.get('jobs', [])
            read_iops = sum(job.get('read', {}).get('iops', 0) for job in jobs)
            write_iops = sum(job.get('write', {}).get('iops', 0) for job in jobs)
            read_bw = sum(job.get('read', {}).get('bw', 0) for job in jobs)
            write_bw = sum(job.get('write', {}).get('bw', 0) for job in jobs)
            result = {
                'iops': read_iops + write_iops,
                'bandwidth': read_bw + write_bw,
                'read_iops': read_iops,
                'write_iops': write_iops,
                'read_bw': read_bw,
                'write_bw': write_bw,
                'latency': {'mean': 0, 'min': 0, 'max': 0},
            }
            logger.info(f"Parsed FIO result - Total IOPS: {result['iops']}, Bandwidth: {result['bandwidth']}")
            return result
        except Exception as error:
            logger.error(f"Error parsing FIO result: {str(error)}")
            return {'error': str(error)}

    def get_status(self, task_id: str) -> dict:
        logger.debug(f"Getting status for FIO task {task_id}")
        task = self.tasks.get(task_id)
        if task is None:
            logger.warning(f"Attempt to get status for non-existent FIO task: {task_id}")
            return {'status': 'not_found'}
        status_info = {
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'start_time': task.start_time,
            'end_time': task.end_time,
        }
        logger.debug(f"Status for FIO task {task_id}: {task.status}")
        return status_info

    def get_trend_data(self, task_id: str, start: str | None = None, end: str | None = None) -> list[dict]:
        logger.debug(f"Getting trend data for FIO task {task_id}, time range: {start} to {end}")
        del start
        del end
        task = self.tasks.get(task_id)
        if task:
            data_count = len(task.trend_data)
            logger.debug(f"Returning {data_count} trend data points for FIO task {task_id}")
            return list(task.trend_data)
        else:
            logger.warning(f"Attempt to get trend data for non-existent FIO task: {task_id}")
            return []

    def stop(self, task_id: str) -> None:
        logger.info(f"Stopping FIO task {task_id}")
        task = self.tasks.get(task_id)
        if task and task.process:
            logger.info(f"Terminating FIO process for task {task_id}")
            task.process.terminate()
            task.status = 'failed'
            task.error = 'User cancelled'
            logger.info(f"FIO task {task_id} marked as cancelled")
        else:
            logger.warning(f"Attempt to stop non-existent or inactive FIO task: {task_id}")