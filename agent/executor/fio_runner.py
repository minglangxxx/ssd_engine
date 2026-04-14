from __future__ import annotations

import json
import math
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

from logger import get_logger

logger = get_logger(__name__)

FIO_OPTION_MAP = {
    'mem': 'iomem',
}


class FioTask:
    def __init__(self, task_id: str, config: dict[str, Any], device: str):
        self.task_id = task_id
        self.config = config
        self.device = device
        self.status = 'pending'
        self.process: subprocess.Popen[str] | None = None
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.trend_data: deque[dict[str, Any]] = deque(maxlen=86400)
        self.start_time: float | None = None
        self.end_time: float | None = None


class FioRunner:
    def __init__(self):
        self.tasks: dict[str, FioTask] = {}
        logger.info('FIO Runner initialized')

    def start(self, task_id: str, config: dict[str, Any], device: str) -> None:
        logger.info('Starting FIO task %s on device %s', task_id, device)
        task = FioTask(task_id, config, device)
        self.tasks[task_id] = task
        threading.Thread(target=self._run, args=(task,), daemon=True).start()

    def _run(self, task: FioTask) -> None:
        logger.info('Running FIO task %s', task.task_id)
        try:
            task.status = 'running'
            task.start_time = time.time()

            command = self._build_command(task)
            logger.info('Launching FIO task %s with command: %s', task.task_id, ' '.join(command))
            reports: list[dict[str, Any]] = []
            stderr_chunks: list[str] = []
            task.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            stdout_thread = threading.Thread(
                target=self._consume_stdout,
                args=(task, reports),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=self._consume_stderr,
                args=(task, stderr_chunks),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            task.process.wait()
            stdout_thread.join()
            stderr_thread.join()

            stderr = ''.join(stderr_chunks).strip()

            if task.process.returncode == 0:
                task.status = 'success'
                task.result = self._parse_result(reports[-1] if reports else None)
                task.error = None
                logger.info('FIO task %s completed successfully', task.task_id)
                return

            task.status = 'failed'
            task.error = stderr or f'fio exited with code {task.process.returncode}'
            logger.error('FIO task %s failed with error: %s', task.task_id, task.error)
        except Exception as error:
            task.status = 'failed'
            task.error = str(error) or 'Unexpected error while running fio task'
            logger.exception('Exception occurred while running FIO task %s', task.task_id)
        finally:
            task.end_time = time.time()
            logger.info(
                'FIO task %s ended at %s',
                task.task_id,
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.end_time)),
            )

    def _build_command(self, task: FioTask) -> list[str]:
        logger.debug('Building FIO command for task %s on device %s', task.task_id, task.device)
        status_interval_seconds = self._resolve_status_interval(task.config)
        command = [
            'fio',
            f'--name=task_{task.task_id}',
            f'--filename={task.device}',
            '--output-format=json',
            '--group_reporting=1',
            f'--status-interval={status_interval_seconds}',
        ]

        for key, value in task.config.items():
            argument = self._format_option(key, value)
            if argument:
                command.append(argument)

        return command

    def _format_option(self, key: str, value: Any) -> str | None:
        if value is None or value == '':
            return None

        if key in {'filename', 'stats_interval'}:
            return None

        fio_key = FIO_OPTION_MAP.get(key, key)
        if isinstance(value, bool):
            return f'--{fio_key}={1 if value else 0}'

        return f'--{fio_key}={value}'

    def _resolve_status_interval(self, config: dict[str, Any]) -> int:
        raw_value = config.get('stats_interval')
        if raw_value is None:
            return 1
        return max(1, math.ceil(int(raw_value) / 1000))

    def _consume_stdout(self, task: FioTask, reports: list[dict[str, Any]]) -> None:
        if task.process is None or task.process.stdout is None:
            return

        decoder = json.JSONDecoder()
        buffer = ''
        while True:
            chunk = task.process.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk
            buffer = self._extract_json_reports(buffer, decoder, task, reports)

        remaining = buffer.strip()
        if remaining:
            logger.debug('Unparsed FIO stdout tail for task %s: %s', task.task_id, remaining[:200])

    def _consume_stderr(self, task: FioTask, stderr_chunks: list[str]) -> None:
        if task.process is None or task.process.stderr is None:
            return
        stderr_chunks.append(task.process.stderr.read())

    def _extract_json_reports(
        self,
        buffer: str,
        decoder: json.JSONDecoder,
        task: FioTask,
        reports: list[dict[str, Any]],
    ) -> str:
        cursor = 0
        while cursor < len(buffer):
            while cursor < len(buffer) and buffer[cursor].isspace():
                cursor += 1

            if cursor >= len(buffer):
                return ''

            try:
                payload, end = decoder.raw_decode(buffer, cursor)
            except json.JSONDecodeError:
                return buffer[cursor:]

            cursor = end
            if not isinstance(payload, dict):
                continue

            reports.append(payload)
            point = self._build_trend_point(payload)
            if point is not None:
                task.trend_data.append(point)

        return ''

    def _build_trend_point(self, report: dict[str, Any]) -> dict[str, Any] | None:
        jobs = report.get('jobs', [])
        if not isinstance(jobs, list) or not jobs:
            return None

        read_iops = 0.0
        write_iops = 0.0
        read_bw = 0.0
        write_bw = 0.0
        latency_means: list[float] = []
        latency_p99s: list[float] = []
        latency_maxes: list[float] = []

        for job in jobs:
            if not isinstance(job, dict):
                continue
            for direction in ('read', 'write'):
                stats = job.get(direction, {})
                if not isinstance(stats, dict):
                    continue

                iops = float(stats.get('iops', 0) or 0)
                bw = float(stats.get('bw', 0) or 0)
                if direction == 'read':
                    read_iops += iops
                    read_bw += bw
                else:
                    write_iops += iops
                    write_bw += bw

                latency = self._extract_latency_stats(stats)
                if latency is None:
                    continue

                mean_value = float(latency.get('mean', 0) or 0)
                max_value = float(latency.get('max', 0) or 0)
                percentile_value = self._extract_percentile_value(latency)
                latency_means.append(self._convert_to_microseconds(mean_value, latency['divisor']))
                latency_maxes.append(self._convert_to_microseconds(max_value, latency['divisor']))
                latency_p99s.append(self._convert_to_microseconds(percentile_value, latency['divisor']))

        if not any((read_iops, write_iops, read_bw, write_bw, latency_means, latency_p99s, latency_maxes)):
            return None

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'iops_read': read_iops,
            'iops_write': write_iops,
            'iops_total': read_iops + write_iops,
            'bw_read': read_bw,
            'bw_write': write_bw,
            'bw_total': read_bw + write_bw,
            'lat_mean': sum(latency_means) / len(latency_means) if latency_means else 0,
            'lat_p99': max(latency_p99s) if latency_p99s else 0,
            'lat_max': max(latency_maxes) if latency_maxes else 0,
        }

    def _extract_latency_stats(self, stats: dict[str, Any]) -> dict[str, Any] | None:
        for key, divisor in (
            ('clat_ns', 1000.0),
            ('lat_ns', 1000.0),
            ('clat_us', 1.0),
            ('lat_us', 1.0),
            ('clat_ms', 0.001),
            ('lat_ms', 0.001),
        ):
            value = stats.get(key)
            if isinstance(value, dict):
                latency = dict(value)
                latency['divisor'] = divisor
                return latency
        return None

    def _extract_percentile_value(self, latency: dict[str, Any]) -> float:
        percentile = latency.get('percentile', {})
        if not isinstance(percentile, dict):
            return 0.0

        for key in ('99.000000', '99.00', '99.0', '99'):
            if key in percentile:
                return float(percentile.get(key, 0) or 0)
        return 0.0

    def _convert_to_microseconds(self, value: float, divisor: float) -> float:
        if divisor == 0:
            return 0.0
        return value / divisor

    def _parse_result(self, report: dict[str, Any] | None) -> dict[str, Any]:
        logger.debug('Parsing FIO result')
        try:
            if report is None:
                raise ValueError('fio produced no JSON output')

            jobs = report.get('jobs', [])
            read_iops = sum(job.get('read', {}).get('iops', 0) for job in jobs)
            write_iops = sum(job.get('write', {}).get('iops', 0) for job in jobs)
            read_bw = sum(job.get('read', {}).get('bw', 0) for job in jobs)
            write_bw = sum(job.get('write', {}).get('bw', 0) for job in jobs)

            latency_mean = 0.0
            latency_min = 0.0
            latency_max = 0.0
            latency_samples = []
            for direction in ('read', 'write'):
                for job in jobs:
                    stats = job.get(direction, {})
                    if not isinstance(stats, dict):
                        continue
                    latency = self._extract_latency_stats(stats)
                    if latency:
                        latency_samples.append(latency)

            if latency_samples:
                latency_mean = sum(
                    self._convert_to_microseconds(float(sample.get('mean', 0) or 0), float(sample.get('divisor', 1) or 1))
                    for sample in latency_samples
                ) / len(latency_samples)
                latency_min = min(
                    self._convert_to_microseconds(float(sample.get('min', 0) or 0), float(sample.get('divisor', 1) or 1))
                    for sample in latency_samples
                )
                latency_max = max(
                    self._convert_to_microseconds(float(sample.get('max', 0) or 0), float(sample.get('divisor', 1) or 1))
                    for sample in latency_samples
                )

            result = {
                'iops': read_iops + write_iops,
                'bandwidth': read_bw + write_bw,
                'read_iops': read_iops,
                'write_iops': write_iops,
                'read_bw': read_bw,
                'write_bw': write_bw,
                'latency': {
                    'mean': latency_mean,
                    'min': latency_min,
                    'max': latency_max,
                },
            }
            logger.info(
                'Parsed FIO result for task output. Total IOPS=%s, bandwidth=%s',
                result['iops'],
                result['bandwidth'],
            )
            return result
        except Exception as error:
            logger.error('Error parsing FIO result: %s', error)
            return {'error': str(error)}

    def get_status(self, task_id: str) -> dict[str, Any]:
        logger.debug('Getting status for FIO task %s', task_id)
        task = self.tasks.get(task_id)
        if task is None:
            logger.warning('Attempt to get status for non-existent FIO task: %s', task_id)
            return {'status': 'not_found'}

        return {
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'start_time': task.start_time,
            'end_time': task.end_time,
        }

    def get_trend_data(self, task_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        logger.debug('Getting trend data for FIO task %s, time range: %s to %s', task_id, start, end)
        task = self.tasks.get(task_id)
        if task is None:
            logger.warning('Attempt to get trend data for non-existent FIO task: %s', task_id)
            return []

        start_ts = self._parse_timestamp(start) if start is not None else float('-inf')
        end_ts = self._parse_timestamp(end) if end is not None else float('inf')
        return [
            point for point in task.trend_data
            if start_ts <= self._parse_timestamp(point.get('timestamp')) <= end_ts
        ]

    def _parse_timestamp(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
                except ValueError:
                    return 0.0
        return 0.0

    def stop(self, task_id: str) -> None:
        logger.info('Stopping FIO task %s', task_id)
        task = self.tasks.get(task_id)
        if task and task.process:
            task.process.terminate()
            task.status = 'failed'
            task.error = 'User cancelled'
            logger.info('FIO task %s marked as cancelled', task_id)
            return

        logger.warning('Attempt to stop non-existent or inactive FIO task: %s', task_id)