import logging
import os
from datetime import datetime


def setup_agent_logger(name: str = __name__, level: int = logging.INFO):
    """
    设置agent的日志记录器
    
    Args:
        name: logger名称，默认为当前模块名
        level: 日志级别，默认为INFO
    
    Returns:
        logging.Logger: 配置好的logger实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 创建文件处理器
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 使用日期作为日志文件名
    today = datetime.now().strftime('%Y%m%d')
    log_filename = os.path.join(log_dir, f'agent_{today}.log')
    
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = __name__):
    """
    获取logger实例，如果不存在则创建
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger: logger实例
    """
    return logging.getLogger(name)


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