import logging
import os
from datetime import datetime
from typing import Optional


def setup_logging(app) -> None:
    """
    为Flask应用设置日志记录器
    
    Args:
        app: Flask应用实例
    """
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    
    # 设置应用logger级别
    app.logger.setLevel(log_level)
    
    # 设置根logger级别
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 如果还没有处理器，则添加
    if not root_logger.handlers:
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 文件处理器
        log_dir = os.path.join(app.root_path, '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 使用日期作为日志文件名
        today = datetime.now().strftime('%Y%m%d')
        log_filename = os.path.join(log_dir, f'app_{today}.log')
        
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)


def get_logger(name: str = __name__) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger: logger实例
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    日志混入类，可以被其他类继承以获得日志功能
    """
    @property
    def logger(self) -> logging.Logger:
        """获取logger实例"""
        return get_logger(self.__class__.__name__)