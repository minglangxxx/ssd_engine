import time

import psutil

from logger import get_logger

logger = get_logger(__name__)


class NetworkCollector:
    def __init__(self):
        self.prev = psutil.net_io_counters()
        self.prev_time = time.time()

    def collect(self) -> dict:
        try:
            current = psutil.net_io_counters()
            now = time.time()
            delta = max(now - self.prev_time, 0.001)
            result = {
                'net_rx_bytes_per_sec': (current.bytes_recv - self.prev.bytes_recv) / delta,
                'net_tx_bytes_per_sec': (current.bytes_sent - self.prev.bytes_sent) / delta,
                'net_rx_packets_per_sec': (current.packets_recv - self.prev.packets_recv) / delta,
                'net_tx_packets_per_sec': (current.packets_sent - self.prev.packets_sent) / delta,
                'net_rx_errors': current.errin,
                'net_tx_errors': current.errout,
            }
            try:
                conns = psutil.net_connections(kind='tcp')
                result['tcp_connections'] = len(conns)
            except Exception:
                logger.exception('Failed to count TCP connections')
                result['tcp_connections'] = 0
            self.prev = current
            self.prev_time = now
            return result
        except Exception:
            logger.exception('Failed to collect network metrics')
            raise
