import os


def _load_local_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return

    with open(env_path, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_local_env()


class Config:
    HOST = os.getenv('AGENT_HOST', '0.0.0.0')
    PORT = int(os.getenv('AGENT_PORT', '8080'))
    VERSION = os.getenv('AGENT_VERSION', '0.1.0')
    BACKEND_URL = os.getenv('BACKEND_URL', '').strip()
    AGENT_DEVICE_IP = os.getenv('AGENT_DEVICE_IP', '').strip()
    INGEST_TIMEOUT_SECONDS = int(os.getenv('INGEST_TIMEOUT_SECONDS', '5'))
    FIO_INGEST_INTERVAL_SECONDS = int(os.getenv('FIO_INGEST_INTERVAL_SECONDS', '3'))
    DISK_INGEST_INTERVAL_SECONDS = int(os.getenv('DISK_INGEST_INTERVAL_SECONDS', '3'))
    INGEST_BATCH_SIZE = int(os.getenv('INGEST_BATCH_SIZE', '20'))
    SMART_COLLECT_INTERVAL_SECONDS = int(os.getenv('SMART_COLLECT_INTERVAL_SECONDS', '60'))
    SMART_INGEST_INTERVAL_SECONDS = int(os.getenv('SMART_INGEST_INTERVAL_SECONDS', '60'))
