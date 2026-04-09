import psutil

from logger import get_logger

logger = get_logger(__name__)


class MemoryCollector:
    def collect(self) -> dict:
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                'mem_total_bytes': mem.total,
                'mem_used_bytes': mem.used,
                'mem_available_bytes': mem.available,
                'mem_usage_percent': mem.percent,
                'mem_buffers_bytes': getattr(mem, 'buffers', 0),
                'mem_cached_bytes': getattr(mem, 'cached', 0),
                'swap_total_bytes': swap.total,
                'swap_used_bytes': swap.used,
            }
        except Exception:
            logger.exception('Failed to collect memory metrics')
            raise
