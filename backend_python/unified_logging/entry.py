"""
统一日志入口模块

提供统一的日志系统初始化和配置入口，解决架构碎片化问题。

功能特性:
- 统一初始化入口
- 统一配置管理
- 统一日志器获取
- 支持多种初始化方式
- 向后兼容旧代码

使用示例:
    # 方式 1: 快速初始化 (使用默认配置)
    from backend_python.unified_logging.entry import init
    
    init()
    logger = get_logger('wechat_backend.api')
    
    # 方式 2: 从配置文件初始化
    from backend_python.unified_logging.entry import init_from_file
    
    init_from_file('config/logging.yaml')
    logger = get_logger('wechat_backend.api')
    
    # 方式 3: 编程式配置
    from backend_python.unified_logging.entry import init_with_config
    
    init_with_config(
        log_level='DEBUG',
        log_dir='logs',
        queue_size=10000
    )
    
    # 方式 4: 使用配置管理器 (支持热重载)
    from backend_python.unified_logging.entry import init_with_hot_reload
    
    init_with_hot_reload('config/logging.yaml', reload_interval=60)
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from unified_logging import (
    UnifiedLoggerFactory,
    UnifiedLogger,
    get_logger as _get_logger,
    init_logging as _init_logging,
    shutdown_logging as _shutdown_logging,
    ConfigManager,
)


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def init(
    log_level: str = None,
    log_dir: str = None,
    queue_size: int = 10000,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
    console_level: str = 'INFO',
    file_level: str = 'DEBUG',
    enable_ai_handler: bool = True,
) -> UnifiedLoggerFactory:
    """
    快速初始化日志系统
    
    Args:
        log_level: 日志级别 (默认从环境变量或 INFO)
        log_dir: 日志目录 (默认 backend_python/logs)
        queue_size: 队列大小 (默认 10000)
        max_bytes: 文件最大大小 (默认 10MB)
        backup_count: 备份数量 (默认 7)
        console_level: 控制台日志级别 (默认 INFO)
        file_level: 文件日志级别 (默认 DEBUG)
        enable_ai_handler: 是否启用 AI 专用处理器 (默认 True)
    
    Returns:
        UnifiedLoggerFactory 实例
    """
    # 从环境变量读取配置
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
    if log_dir is None:
        log_dir = os.environ.get('LOG_DIR', 'logs')
    if queue_size == 10000:
        queue_size = int(os.environ.get('LOG_QUEUE_SIZE', '10000'))
    if console_level == 'INFO':
        console_level = os.environ.get('LOG_CONSOLE_LEVEL', 'INFO')
    if file_level == 'DEBUG':
        file_level = os.environ.get('LOG_FILE_LEVEL', 'DEBUG')
    if enable_ai_handler:
        enable_ai_handler = os.environ.get('LOG_ENABLE_AI_HANDLER', 'true').lower() == 'true'
    
    factory = _init_logging(
        log_level=log_level,
        log_dir=log_dir,
        queue_size=queue_size,
        max_bytes=max_bytes,
        backup_count=backup_count,
        console_level=console_level,
        file_level=file_level,
        enable_ai_handler=enable_ai_handler,
    )
    
    return factory


def init_from_file(
    config_path: str = 'config/logging.yaml',
    auto_reload: bool = False,
    reload_interval: float = 60.0,
) -> UnifiedLoggerFactory:
    """
    从配置文件初始化日志系统
    
    Args:
        config_path: 配置文件路径
        auto_reload: 是否自动重载配置
        reload_interval: 重载间隔 (秒)
    
    Returns:
        UnifiedLoggerFactory 实例
    """
    from unified_logging.config_loader import init_logging_from_config
    
    global _config_manager
    
    factory = init_logging_from_config(
        config_path=config_path,
        auto_reload=auto_reload,
        reload_interval=reload_interval,
    )
    
    # 保存配置管理器实例
    if auto_reload:
        _config_manager = ConfigManager(config_path)
    
    return factory


def init_with_config(
    config: Dict[str, Any],
) -> UnifiedLoggerFactory:
    """
    使用配置字典初始化日志系统
    
    Args:
        config: 配置字典
    
    Returns:
        UnifiedLoggerFactory 实例
    """
    # 延迟导入以确保 initialize_from_config 已注册
    from unified_logging.config_loader import _initialize_from_config
    
    factory = UnifiedLoggerFactory()
    _initialize_from_config(factory, config)
    return factory


def init_with_hot_reload(
    config_path: str = 'config/logging.yaml',
    reload_interval: float = 60.0,
) -> UnifiedLoggerFactory:
    """
    初始化日志系统并启用配置热重载
    
    Args:
        config_path: 配置文件路径
        reload_interval: 重载间隔 (秒)
    
    Returns:
        UnifiedLoggerFactory 实例
    """
    global _config_manager
    
    # 初始化日志
    factory = init_from_file(config_path, auto_reload=False)
    
    # 创建配置管理器并启动热重载
    _config_manager = ConfigManager(config_path)
    _config_manager.start_auto_reload(reload_interval)
    
    return factory


def get_logger(name: str) -> UnifiedLogger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        UnifiedLogger 实例
    """
    return _get_logger(name)


def shutdown_logging(timeout: float = 5.0):
    """
    关闭日志系统
    
    Args:
        timeout: 等待时间 (秒)
    """
    _shutdown_logging(timeout)
    
    # 停止配置管理器
    global _config_manager
    if _config_manager:
        _config_manager.stop_auto_reload()
        _config_manager = None


def get_config_manager() -> Optional[ConfigManager]:
    """
    获取配置管理器实例
    
    Returns:
        ConfigManager 实例或 None
    """
    return _config_manager


def reload_config() -> Dict[str, Any]:
    """
    手动重新加载配置
    
    Returns:
        新配置字典
    """
    if _config_manager:
        return _config_manager.reload()
    return {}


def get_config(key: str = None, default: Any = None):
    """
    获取配置值
    
    Args:
        key: 配置键 (支持点分隔，如 'queue.max_size')
        default: 默认值
    
    Returns:
        配置值
    """
    if _config_manager:
        if key is None:
            return _config_manager.config
        return _config_manager.get(key, default)
    return default


# 预定义的常用日志器
def get_app_logger() -> UnifiedLogger:
    """获取应用日志器"""
    return get_logger('wechat_backend')


def get_api_logger() -> UnifiedLogger:
    """获取 API 日志器"""
    return get_logger('wechat_backend.api')


def get_ai_logger() -> UnifiedLogger:
    """获取 AI 日志器"""
    return get_logger('wechat_backend.ai')


def get_db_logger() -> UnifiedLogger:
    """获取数据库日志器"""
    return get_logger('wechat_backend.database')


def get_security_logger() -> UnifiedLogger:
    """获取安全审计日志器"""
    return get_logger('wechat_backend.security')


# 兼容性函数 - 保持与旧代码兼容
def setup_logging(log_level=None, log_file=None, max_bytes=10485760, backup_count=5):
    """
    设置日志配置 (兼容旧代码)
    
    此函数是为了保持与旧代码的兼容性，新代码应使用 init() 或 init_from_file()
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径 (已废弃，使用 log_dir)
        max_bytes: 最大文件大小
        backup_count: 备份数量
    
    Returns:
        根日志器
    """
    import logging
    
    # 使用新的初始化方式
    log_dir = os.path.dirname(log_file) if log_file else None
    init(
        log_level=log_level,
        log_dir=log_dir,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    
    return logging.getLogger()


# 导出所有符号
__all__ = [
    'init',
    'init_from_file',
    'init_with_config',
    'init_with_hot_reload',
    'get_logger',
    'shutdown_logging',
    'get_config_manager',
    'reload_config',
    'get_config',
    'get_app_logger',
    'get_api_logger',
    'get_ai_logger',
    'get_db_logger',
    'get_security_logger',
    'setup_logging',  # 兼容旧代码
]
