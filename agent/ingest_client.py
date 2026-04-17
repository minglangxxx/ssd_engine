from __future__ import annotations

import json
import socket
import threading
import time
from datetime import datetime, timezone, timedelta

_CST = timezone(timedelta(hours=8))
from typing import Any
from urllib import error, request

from config import Config
from logger import get_logger

logger = get_logger(__name__)


class BackendIngestClient:
    def __init__(self):
        self.backend_url = Config.BACKEND_URL.rstrip('/')
        self.device_ip = Config.AGENT_DEVICE_IP or self._resolve_device_ip()
        self.enabled = bool(self.backend_url and self.device_ip)
        self.timeout = max(1, Config.INGEST_TIMEOUT_SECONDS)
        self.fio_flush_interval = max(1, Config.FIO_INGEST_INTERVAL_SECONDS)
        self.disk_flush_interval = max(1, Config.DISK_INGEST_INTERVAL_SECONDS)
        self.max_batch_size = max(1, Config.INGEST_BATCH_SIZE)
        self.lock = threading.Lock()
        self.disk_samples: list[dict[str, Any]] = []
        self.disk_last_flush = time.monotonic()
        self.fio_batches: dict[str, dict[str, Any]] = {}

        self.host_metrics_batch: dict[str, Any] = {}
        self.host_metrics_last_flush = time.monotonic()
        if self.enabled:
            logger.info('Backend ingest enabled, backend=%s, device_ip=%s', self.backend_url, self.device_ip)
            threading.Thread(target=self._flush_loop, daemon=True).start()
        else:
            logger.info('Backend ingest disabled, backend_url=%s, device_ip=%s', self.backend_url or '', self.device_ip or '')

    def enqueue_host_metrics(self, snapshot_timestamp: float, host_data: dict[str, Any]) -> None:
        if not self.enabled or not host_data:
            return

        event_time = datetime.fromtimestamp(snapshot_timestamp, tz=_CST).isoformat()
        payload = dict(host_data)
        payload['timestamp'] = event_time
        payload.setdefault('source', 'agent_host')

        with self.lock:
            self.host_metrics_batch = payload
            should_flush = self._elapsed(self.host_metrics_last_flush) >= 5  # 每5秒推送一次主机监控

        if should_flush:
            self.flush_host_metrics()

    def flush_host_metrics(self) -> None:
        if not self.enabled:
            return

        with self.lock:
            if not self.host_metrics_batch:
                return
            batch = dict(self.host_metrics_batch)

        # 构造 ingest 接口期望的格式：samples 数组
        payload = {
            'device_ip': self.device_ip,
            'samples': [{
                'timestamp': batch.get('timestamp'),
                'data_type': 'host_monitor',
                'data': {k: v for k, v in batch.items() if k not in ('timestamp', 'source')},
            }],
        }

        if self._post_json('/api/internal/ingest/host-monitor', payload):
            with self.lock:
                self.host_metrics_batch = {}
                self.host_metrics_last_flush = time.monotonic()

    def enqueue_disk_metrics(self, snapshot_timestamp: float, disks: dict[str, dict[str, Any]]) -> None:
        if not self.enabled or not disks:
            return

        event_time = datetime.fromtimestamp(snapshot_timestamp, tz=_CST).isoformat()
        samples = []
        for disk_name, metrics in disks.items():
            if not isinstance(metrics, dict):
                continue
            sample = dict(metrics)
            sample['disk_name'] = disk_name
            sample['event_time'] = event_time
            sample.setdefault('source', 'agent_disk')
            samples.append(sample)

        if not samples:
            return

        with self.lock:
            self.disk_samples.extend(samples)
            should_flush = len(self.disk_samples) >= self.max_batch_size or self._elapsed(self.disk_last_flush) >= self.disk_flush_interval

        if should_flush:
            self.flush_disk_metrics()

    def enqueue_fio_trend(self, task_id: str, device_path: str, sample_interval_ms: int, point: dict[str, Any]) -> None:
        if not self.enabled:
            return

        with self.lock:
            batch = self.fio_batches.setdefault(task_id, {
                'device_path': device_path,
                'sample_interval_ms': sample_interval_ms,
                'points': [],
                'last_flush': time.monotonic(),
            })
            batch['device_path'] = device_path
            batch['sample_interval_ms'] = sample_interval_ms
            batch['points'].append(dict(point))
            should_flush = len(batch['points']) >= self.max_batch_size or self._elapsed(batch['last_flush']) >= self.fio_flush_interval

        if should_flush:
            self.flush_fio_trend(task_id)

    def flush_fio_trend(self, task_id: str) -> None:
        if not self.enabled:
            return

        with self.lock:
            batch = self.fio_batches.get(task_id)
            if not batch or not batch['points']:
                return
            points = [dict(point) for point in batch['points']]
            payload = {
                'task_id': int(task_id),
                'device_ip': self.device_ip,
                'device_path': batch['device_path'],
                'sample_interval_ms': int(batch['sample_interval_ms']),
                'points': points,
            }

        if self._post_json('/api/internal/ingest/fio-trend', payload):
            with self.lock:
                current_batch = self.fio_batches.get(task_id)
                if current_batch and current_batch['points'][:len(points)] == points:
                    del current_batch['points'][:len(points)]
                    current_batch['last_flush'] = time.monotonic()

    def flush_disk_metrics(self) -> None:
        if not self.enabled:
            return

        with self.lock:
            if not self.disk_samples:
                return
            samples = [dict(sample) for sample in self.disk_samples]

        if self._post_json('/api/internal/ingest/disk-monitor', {'device_ip': self.device_ip, 'samples': samples}):
            with self.lock:
                if self.disk_samples[:len(samples)] == samples:
                    del self.disk_samples[:len(samples)]
                    self.disk_last_flush = time.monotonic()

    def flush_task(
        self,
        task_id: str,
        status: str,
        result: dict[str, Any] | None,
        started_at: float | None,
        finished_at: float | None,
    ) -> None:
        if not self.enabled:
            return

        self.flush_fio_trend(task_id)
        payload = {
            'task_id': int(task_id),
            'status': status.upper(),
            'result': result,
            'started_at': self._to_iso_datetime(started_at),
            'finished_at': self._to_iso_datetime(finished_at),
            'data_window_start': self._to_iso_datetime(started_at),
            'data_window_end': self._to_iso_datetime(finished_at),
        }
        self._post_json('/api/internal/ingest/flush-task', payload)

    def _flush_loop(self) -> None:
        while True:
            try:
                self.flush_host_metrics()
                self.flush_disk_metrics()
                task_ids = []
                with self.lock:
                    for task_id, batch in self.fio_batches.items():
                        if batch['points'] and self._elapsed(batch['last_flush']) >= self.fio_flush_interval:
                            task_ids.append(task_id)
                for task_id in task_ids:
                    self.flush_fio_trend(task_id)
            except Exception as error:
                logger.warning('Background ingest flush loop failed: %s', error)
            time.sleep(1)

    def _post_json(self, path: str, payload: dict[str, Any]) -> bool:
        body = json.dumps(payload).encode('utf-8')
        req = request.Request(
            url=f'{self.backend_url}{path}',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                status_code = getattr(response, 'status', 200)
                if 200 <= status_code < 300:
                    return True
                logger.warning('Backend ingest returned status %s for %s', status_code, path)
                return False
        except error.URLError as exc:
            logger.warning('Failed to post ingest payload to %s: %s', path, exc)
            return False

    def _resolve_device_ip(self) -> str:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return ''

    def _to_iso_datetime(self, timestamp: float | None) -> str | None:
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp, tz=_CST).isoformat()

    def _elapsed(self, started_at: float) -> float:
        return time.monotonic() - started_at