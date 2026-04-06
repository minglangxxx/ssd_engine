from flask import Flask

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

    with app.app_context():
        db.create_all()

    return app
