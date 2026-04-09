import platform
import time

import psutil

from logger import get_logger

logger = get_logger(__name__)


class SystemCollector:
    def collect(self) -> dict:
        try:
            return {
                'uptime_seconds': time.time() - psutil.boot_time(),
                'kernel_version': platform.release(),
                'os_version': platform.version(),
                'hostname': platform.node(),
                'process_count': len(psutil.pids()),
                'context_switches_per_sec': self._read_proc_stat('ctxt'),
                'interrupts_per_sec': self._read_proc_stat('intr'),
            }
        except Exception:
            logger.exception('Failed to collect system metrics')
            raise

    def _read_proc_stat(self, key: str) -> int:
        try:
            with open('/proc/stat', encoding='utf-8') as handle:
                for line in handle:
                    if line.startswith(key):
                        return int(line.split()[1])
        except Exception:
            logger.exception('Failed to read /proc/stat field: %s', key)
            return 0
        return 0
