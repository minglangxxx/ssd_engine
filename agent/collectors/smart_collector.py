import subprocess

from logger import get_logger

logger = get_logger(__name__)

_UINT64_SHIFT = 1 << 64
_TEMPERATURE_SHIFT = 1 << 8


def _normalize_counter(value) -> int:
    parsed = int(value or 0)
    if parsed > 0 and parsed % _UINT64_SHIFT == 0:
        shifted = parsed // _UINT64_SHIFT
        if shifted < parsed:
            return shifted
    return parsed


def _normalize_temperature(value) -> int:
    parsed = int(value or 0)
    if parsed > 200 and parsed % _TEMPERATURE_SHIFT == 0:
        shifted = parsed // _TEMPERATURE_SHIFT
        if 0 <= shifted <= 200:
            return shifted
    return parsed


def _normalize_device_path(device: str) -> str:
    normalized = (device or '').strip().lstrip('/')
    if normalized.startswith('dev/'):
        return f'/{normalized}'
    if normalized.startswith('/dev/'):
        return normalized
    return f'/dev/{normalized}'


class SmartCollector:
    def collect(self, device: str) -> dict:
        try:
            device_path = _normalize_device_path(device)
            result = subprocess.run(
                ['nvme', 'smart-log', device_path, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme smart-log failed for %s: %s', device_path, result.stderr.strip())
                return {}
            import json

            data = json.loads(result.stdout)
            return {
                'temperature': _normalize_temperature(data.get('temperature', 0)),
                'percentage_used': int(data.get('percentage_used', data.get('percent_used', 0)) or 0),
                'power_on_hours': _normalize_counter(data.get('power_on_hours', 0)),
                'power_cycles': _normalize_counter(data.get('power_cycles', 0)),
                'media_errors': _normalize_counter(data.get('media_errors', 0)),
                'critical_warning': int(data.get('critical_warning', 0) or 0),
                'data_units_read': _normalize_counter(data.get('data_units_read', 0)),
                'data_units_written': _normalize_counter(data.get('data_units_written', 0)),
                'available_spare': data.get('available_spare', data.get('avail_spare')),
            }
        except Exception:
            logger.exception('Failed to collect SMART metrics for %s', device)
            return {}
