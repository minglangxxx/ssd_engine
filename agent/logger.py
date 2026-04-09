import logging
import os
from datetime import datetime
from pathlib import Path


BASE_LOGGER_NAME = 'ssd_agent'
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'


def _resolve_log_dir(log_dir: str | None = None) -> Path:
    if log_dir:
        return Path(log_dir)

    env_log_dir = os.getenv('AGENT_LOG_DIR')
    if env_log_dir:
        return Path(env_log_dir)

    return Path(__file__).resolve().parent / 'logs'


def _normalize_logger_name(name: str | None) -> str:
    if not name or name in {__name__, '__main__', BASE_LOGGER_NAME}:
        return BASE_LOGGER_NAME
    if name.startswith(f'{BASE_LOGGER_NAME}.'):
        return name
    return f'{BASE_LOGGER_NAME}.{name}'


def _configure_base_logger(level: int = DEFAULT_LOG_LEVEL, log_dir: str | None = None) -> logging.Logger:
    base_logger = logging.getLogger(BASE_LOGGER_NAME)
    base_logger.setLevel(level)

    if base_logger.handlers:
        return base_logger

    resolved_log_dir = _resolve_log_dir(log_dir)
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d')
    log_filename = resolved_log_dir / f'agent_{today}.log'
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    base_logger.addHandler(console_handler)
    base_logger.addHandler(file_handler)
    base_logger.propagate = False
    return base_logger


def setup_agent_logger(name: str = BASE_LOGGER_NAME, level: int = DEFAULT_LOG_LEVEL, log_dir: str | None = None) -> logging.Logger:
    """设置 agent 公共日志器，并返回指定名称的子 logger。"""
    _configure_base_logger(level=level, log_dir=log_dir)
    logger = logging.getLogger(_normalize_logger_name(name))
    logger.setLevel(level)
    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """获取已完成基础配置的 logger。"""
    return setup_agent_logger(name)


# 便捷的日志方法
def info(message: str, logger_name: str = __name__):
    """记录info级别的日志"""
    logger = get_logger(logger_name)
    logger.info(message)


def error(message: str, logger_name: str = __name__):
    """记录error级别的日志"""
    logger = get_logger(logger_name)
    logger.error(message)


def warning(message: str, logger_name: str = __name__):
    """记录warning级别的日志"""
    logger = get_logger(logger_name)
    logger.warning(message)


def debug(message: str, logger_name: str = __name__):
    """记录debug级别的日志"""
    logger = get_logger(logger_name)
    logger.debug(message)


def critical(message: str, logger_name: str = __name__):
    """记录critical级别的日志"""
    logger = get_logger(logger_name)
    logger.critical(message)