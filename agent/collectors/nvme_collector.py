import subprocess

from logger import get_logger

logger = get_logger(__name__)


class NvmeCollector:
    @staticmethod
    def id_ctrl(device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'id-ctrl', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme id-ctrl failed for %s: %s', device, result.stderr.strip())
                return {}
            import json
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect id-ctrl for %s', device)
            return {}

    @staticmethod
    def id_ns(device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'id-ns', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme id-ns failed for %s: %s', device, result.stderr.strip())
                return {}
            import json
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect id-ns for %s', device)
            return {}

    @staticmethod
    def error_log(device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'error-log', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme error-log failed for %s: %s', device, result.stderr.strip())
                return {}
            import json
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect error-log for %s', device)
            return {}
