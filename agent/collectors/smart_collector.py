import subprocess

from logger import get_logger

logger = get_logger(__name__)


class SmartCollector:
    def collect(self, device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'smart-log', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme smart-log failed for %s: %s', device, result.stderr.strip())
                return {}
            import json

            data = json.loads(result.stdout)
            return {
                'temperature': data.get('temperature', 0),
                'percentage_used': data.get('percentage_used', 0),
                'power_on_hours': data.get('power_on_hours', 0),
                'power_cycles': data.get('power_cycles', 0),
                'media_errors': data.get('media_errors', 0),
                'critical_warning': data.get('critical_warning', 0),
                'data_units_read': data.get('data_units_read', 0),
                'data_units_written': data.get('data_units_written', 0),
            }
        except Exception:
            logger.exception('Failed to collect SMART metrics for %s', device)
            return {}
