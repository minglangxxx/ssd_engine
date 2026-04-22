import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_me')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', '5000'))

    MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'ssd_engine')

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
    }

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-4.1')
    AI_ANALYSIS_MAX_AGE_DAYS = int(os.getenv('AI_ANALYSIS_MAX_AGE_DAYS', '7'))

    # 监控数据保留天数（超过后自动删除）
    MONITOR_RETENTION_DAYS = int(os.getenv('MONITOR_RETENTION_DAYS', '7'))

    # NVMe SMART 数据保留天数
    NVME_SMART_RETENTION_DAYS = int(os.getenv('NVME_SMART_RETENTION_DAYS', '90'))
