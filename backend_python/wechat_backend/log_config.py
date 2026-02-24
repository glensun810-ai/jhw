"""
日志级别配置模块

BUG-009 修复：添加日志级别控制，生产环境可关闭 DEBUG 日志
"""

import logging
import os
from typing import Optional


class LogLevel:
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogConfig:
    """日志配置管理器"""
    
    _instance: Optional['LogConfig'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LogConfig':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._configure_logging()
    
    def _configure_logging(self):
        """配置日志系统"""
        # 从环境变量读取日志级别
        env = os.getenv('FLASK_ENV', 'development')
        log_level_str = os.getenv('LOG_LEVEL', 'DEBUG' if env == 'development' else 'INFO')
        
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # 配置根日志记录器
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 设置特定模块的日志级别
        logging.getLogger('wechat_backend.api').setLevel(log_level)
        logging.getLogger('wechat_backend.database').setLevel(log_level)
        
        # 生产环境降低第三方库的日志级别
        if env == 'production':
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('werkzeug').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    # 确保日志系统已配置
    LogConfig()
    return logging.getLogger(name)


def set_log_level(level: int):
    """
    设置全局日志级别
    
    Args:
        level: 日志级别（logging.DEBUG, logging.INFO 等）
    """
    logging.getLogger().setLevel(level)


def set_production_mode():
    """切换到生产环境模式"""
    set_log_level(logging.WARNING)
    get_logger(__name__).info("已切换到生产环境模式")


def set_development_mode():
    """切换到开发环境模式"""
    set_log_level(logging.DEBUG)
    get_logger(__name__).info("已切换到开发环境模式")


# 便捷的日志函数
def debug(msg: str, *args, **kwargs):
    """DEBUG 级别日志"""
    get_logger(__name__).debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """INFO 级别日志"""
    get_logger(__name__).info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """WARNING 级别日志"""
    get_logger(__name__).warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """ERROR 级别日志"""
    get_logger(__name__).error(msg, *args, **kwargs)


# 初始化日志系统
LogConfig()
