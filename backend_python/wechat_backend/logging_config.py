"""
日志兼容性包装器

为现有代码提供向后兼容的日志接口，同时使用新的异步队列日志系统。

使用方式:
    # 现有代码无需修改
    from wechat_backend.logging_config import app_logger, api_logger, get_logger
    
    # 新代码使用统一接口
    from backend_python.unified_logging.entry import get_logger, init
    
    logger = get_logger('wechat_backend.api')
    logger.info('Hello, World!')

注意:
    此模块是为了平滑迁移而设计的，新代码应直接使用 backend_python.unified_logging.entry 模块。
"""

import logging
from pathlib import Path

# 尝试导入新日志系统，如果失败则回退到旧系统
try:
    from backend_python.unified_logging.entry import (
        init as _init_logging,
        get_logger as _get_unified_logger,
        shutdown_logging as _shutdown_logging,
    )
    _NEW_LOGGING_AVAILABLE = True
except ImportError:
    _NEW_LOGGING_AVAILABLE = False
    _init_logging = None
    _get_unified_logger = None
    _shutdown_logging = None

# 全局工厂实例
_factory = None
_initialized = False


def _ensure_initialized():
    """确保日志系统已初始化"""
    global _initialized
    if not _initialized and _NEW_LOGGING_AVAILABLE:
        _init_logging()
        _initialized = True


def _get_factory():
    """获取或创建日志工厂实例"""
    global _factory
    if _factory is None:
        if _NEW_LOGGING_AVAILABLE:
            _ensure_initialized()
            _factory = 'unified'
        else:
            # 回退到标准 logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
            )
            _factory = 'legacy'
    return _factory


def get_logger(name: str):
    """
    获取日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        日志器实例
    """
    _ensure_initialized()
    factory = _get_factory()
    if factory == 'legacy':
        return logging.getLogger(name)
    else:
        return _get_unified_logger(name)


# 预定义的常用日志器 (保持与旧代码兼容)
# 延迟初始化以确保配置已加载
def _get_app_logger():
    return get_logger('wechat_backend')


def _get_api_logger():
    return get_logger('wechat_backend.api')


def _get_db_logger():
    return get_logger('wechat_backend.database')


def _get_wechat_logger():
    return get_logger('wechat_backend.wechat')


# 使用 property 实现延迟初始化
class _LazyLoggers:
    @property
    def app_logger(self):
        return _get_app_logger()
    
    @property
    def api_logger(self):
        return _get_api_logger()
    
    @property
    def db_logger(self):
        return _get_db_logger()
    
    @property
    def wechat_logger(self):
        return _get_wechat_logger()


_lazy_loggers = _LazyLoggers()

# 为了向后兼容，直接导出 logger 实例（首次使用时初始化）
app_logger = property(lambda self: _lazy_loggers.app_logger) if False else _get_app_logger()
api_logger = _get_api_logger()
db_logger = _get_db_logger()
wechat_logger = _get_wechat_logger()


def setup_logging(log_level=None, log_file=None, max_bytes=10485760, backup_count=5):
    """
    设置日志配置 (保持与旧代码兼容)
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        max_bytes: 最大文件大小
        backup_count: 备份数量
    
    Returns:
        根日志器
    """
    global _initialized
    
    if _NEW_LOGGING_AVAILABLE:
        # 使用新日志系统
        from backend_python.unified_logging.entry import init
        
        log_dir = None
        if log_file:
            log_dir = str(Path(log_file).parent)
        
        init(
            log_level=log_level,
            log_dir=log_dir,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )
        
        print(f"Unified logging initialized with level: {log_level}")
        return logging.getLogger()
    else:
        # 使用标准 logging 配置
        import logging.handlers
        
        numeric_level = getattr(logging, (log_level or 'INFO').upper(), logging.INFO)
        
        logs_dir = Path(__file__).parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        if log_file is None:
            log_file = logs_dir / 'app.log'
        else:
            log_file = Path(log_file)
            if not log_file.parent.exists():
                log_file.parent.mkdir(parents=True, exist_ok=True)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
        )
        
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        print(f"Logging initialized with level: {log_level}, file: {log_file}")
        return root_logger


def shutdown_logging(timeout=5.0):
    """
    关闭日志系统
    
    Args:
        timeout: 等待时间 (秒)
    """
    global _initialized
    if _NEW_LOGGING_AVAILABLE and _initialized:
        _shutdown_logging(timeout=timeout)
        _initialized = False


# 导出所有符号
__all__ = [
    'setup_logging',
    'get_logger',
    'app_logger',
    'api_logger',
    'db_logger',
    'wechat_logger',
    'shutdown_logging',
]
