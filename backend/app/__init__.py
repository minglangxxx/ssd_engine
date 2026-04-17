from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .api import api_bp, register_error_handlers
from .config import Config
from .extensions import db, migrate
from .models import analysis, data_record, device, fio_trend, monitor_data, task
from .utils.logger import setup_logging


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    setup_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_bp, url_prefix='/api')
    register_error_handlers(app)

    @app.get('/')
    def index():
        return {
            'service': 'ssd-engine-backend',
            'message': 'Backend is running',
            'endpoints': {
                'health': '/api/health',
                'api_base': '/api',
            },
        }

    with app.app_context():
        db.create_all()

    _start_scheduler(app)

    return app


def _start_scheduler(app: Flask) -> None:
    from .services.data_lifecycle import DataLifecycleService
    from .utils.logger import get_logger
    logger = get_logger(__name__)

    retention_days = app.config.get('MONITOR_RETENTION_DAYS', 7)

    def cleanup_job():
        with app.app_context():
            # 1. 先自动归档超期的 active 数据
            archive_result = DataLifecycleService.auto_archive_ready_records(retention_days)
            if archive_result.get('archived_count', 0) > 0:
                logger.info('Auto-archived %d old active records', archive_result['archived_count'])
            
            # 2. 然后执行清理（原始数据已备份，可安全删除）
            result = DataLifecycleService.auto_cleanup(retention_days)
            logger.info('Scheduled cleanup done: %s', result)

    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
    scheduler.add_job(
        cleanup_job,
        trigger=CronTrigger(hour=2, minute=0, timezone='Asia/Shanghai'),
        id='monitor_cleanup',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        'Scheduler started: monitor data auto-cleanup at 02:00 CST, retention=%d days',
        retention_days,
    )
