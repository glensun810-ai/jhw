"""
日志配置加载模块

从 YAML 配置文件加载日志配置，并应用到 UnifiedLoggerFactory。

功能特性:
- 从 YAML 文件加载配置
- 支持配置热重载
- 支持环境变量覆盖
- 支持配置验证

使用示例:
    from backend_python.unified_logging.config_loader import load_config, init_logging_from_config, ConfigManager
    
    # 方式 1: 从配置文件加载
    factory = init_logging_from_config('config/logging.yaml')
    
    # 方式 2: 手动加载配置
    config = load_config('config/logging.yaml')
    factory = UnifiedLoggerFactory()
    factory.initialize_from_config(config)
    
    # 方式 3: 配置热重载
    config_manager = ConfigManager('config/logging.yaml')
    config_manager.start_auto_reload(interval=60)  # 每 60 秒检查一次
"""

import os
import sys
import yaml
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

# 确保可以导入 unified_logger
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from unified_logger import UnifiedLoggerFactory, JSONFormatter


@dataclass
class ConfigChange:
    """配置变更事件"""
    timestamp: datetime
    old_value: Any
    new_value: Any
    key_path: str


@dataclass
class ConfigState:
    """配置状态"""
    config: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[Path] = None
    last_modified: float = 0.0
    version: int = 0
    change_history: List[ConfigChange] = field(default_factory=list)


class ConfigManager:
    """
    配置管理器
    
    功能:
    - 加载 YAML 配置
    - 配置热重载
    - 配置变更通知
    - 配置验证
    - 环境变量覆盖
    """
    
    def __init__(self, config_path: str, auto_reload: bool = False):
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            # 相对于 backend_python 目录
            self.config_path = Path(__file__).parent.parent / self.config_path
        
        self._state = ConfigState()
        self._auto_reload = auto_reload
        self._reload_thread: Optional[threading.Thread] = None
        self._stop_reload = threading.Event()
        self._listeners: List[Callable[[Dict[str, Any], Dict[str, Any]], None]] = []
        self._lock = threading.Lock()
        
        # 初始加载
        self.reload()
    
    def reload(self) -> Dict[str, Any]:
        """
        重新加载配置
        
        Returns:
            配置字典
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with self._lock:
            # 读取文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)
            
            # 应用环境变量覆盖
            new_config = self._apply_env_overrides(new_config)
            
            # 记录变更
            old_config = self._state.config.copy()
            self._state.config = new_config
            self._state.file_path = self.config_path
            self._state.last_modified = self.config_path.stat().st_mtime
            self._state.version += 1
            
            # 记录变更历史
            if old_config:
                self._record_changes(old_config, new_config)
            
            # 通知监听器
            self._notify_listeners(old_config, new_config)
            
            return new_config
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖配置"""
        # 日志级别覆盖
        if os.environ.get('LOG_LEVEL'):
            config['log_level'] = os.environ.get('LOG_LEVEL')
        
        # 日志目录覆盖
        if os.environ.get('LOG_DIR'):
            config['log_dir'] = os.environ.get('LOG_DIR')
        
        # 队列大小覆盖
        if os.environ.get('LOG_QUEUE_SIZE'):
            config.setdefault('queue', {})
            config['queue']['max_size'] = int(os.environ.get('LOG_QUEUE_SIZE'))
        
        # 控制台级别覆盖
        if os.environ.get('LOG_CONSOLE_LEVEL'):
            config['console_level'] = os.environ.get('LOG_CONSOLE_LEVEL')
        
        return config
    
    def _record_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """记录配置变更"""
        changes = self._diff_configs(old_config, new_config)
        for key_path, (old_val, new_val) in changes.items():
            change = ConfigChange(
                timestamp=datetime.now(),
                old_value=old_val,
                new_value=new_val,
                key_path=key_path
            )
            self._state.change_history.append(change)
            
            # 限制历史记录数量
            if len(self._state.change_history) > 100:
                self._state.change_history.pop(0)
    
    def _diff_configs(self, old: Dict[str, Any], new: Dict[str, Any], prefix: str = '') -> Dict[str, tuple]:
        """比较两个配置的差异"""
        changes = {}
        
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            key_path = f"{prefix}.{key}" if prefix else key
            
            old_val = old.get(key)
            new_val = new.get(key)
            
            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    # 递归比较嵌套字典
                    changes.update(self._diff_configs(old_val, new_val, key_path))
                else:
                    changes[key_path] = (old_val, new_val)
        
        return changes
    
    def _notify_listeners(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """通知配置变更监听器"""
        for listener in self._listeners:
            try:
                listener(old_config, new_config)
            except Exception as e:
                # 记录错误但不影响其他监听器
                print(f"Config listener error: {e}")
    
    def add_listener(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]):
        """添加配置变更监听器"""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]):
        """移除配置变更监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def start_auto_reload(self, interval: float = 60.0):
        """
        启动自动重载
        
        Args:
            interval: 检查间隔 (秒)
        """
        if self._reload_thread is not None:
            return
        
        self._auto_reload = True
        self._stop_reload.clear()
        self._reload_thread = threading.Thread(target=self._auto_reload_loop, args=(interval,), daemon=True)
        self._reload_thread.start()
    
    def stop_auto_reload(self):
        """停止自动重载"""
        self._auto_reload = False
        self._stop_reload.set()
        if self._reload_thread:
            self._reload_thread.join(timeout=5.0)
            self._reload_thread = None
    
    def _auto_reload_loop(self, interval: float):
        """自动重载循环"""
        while not self._stop_reload.is_set():
            try:
                # 检查文件是否修改
                if self.config_path.exists():
                    current_mtime = self.config_path.stat().st_mtime
                    if current_mtime > self._state.last_modified:
                        self.reload()
            except Exception as e:
                print(f"Auto reload error: {e}")
            
            self._stop_reload.wait(interval)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._state.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._state.config.copy()
    
    @property
    def version(self) -> int:
        """获取配置版本"""
        return self._state.version
    
    def get_change_history(self, limit: int = 10) -> List[ConfigChange]:
        """获取配置变更历史"""
        return self._state.change_history[-limit:]


def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载 YAML 配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    path = Path(config_path)
    if not path.exists():
        # 尝试相对于 backend_python 目录
        path = Path(__file__).parent.parent / config_path
    
    if not path.exists():
        raise FileNotFoundError(f"Log config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 应用环境变量覆盖
    config = _apply_env_overrides(config)
    
    return config


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """应用环境变量覆盖配置"""
    # 日志级别覆盖
    if os.environ.get('LOG_LEVEL'):
        config['log_level'] = os.environ.get('LOG_LEVEL')
    
    # 日志目录覆盖
    if os.environ.get('LOG_DIR'):
        config['log_dir'] = os.environ.get('LOG_DIR')
    
    # 队列大小覆盖
    if os.environ.get('LOG_QUEUE_SIZE'):
        config.setdefault('queue', {})
        config['queue']['max_size'] = int(os.environ.get('LOG_QUEUE_SIZE'))
    
    # 控制台级别覆盖
    if os.environ.get('LOG_CONSOLE_LEVEL'):
        config['console_level'] = os.environ.get('LOG_CONSOLE_LEVEL')
    
    # 文件级别覆盖
    if os.environ.get('LOG_FILE_LEVEL'):
        config['file_level'] = os.environ.get('LOG_FILE_LEVEL')
    
    return config


def init_logging_from_config(
    config_path: str = 'config/logging.yaml',
    override_config: Dict[str, Any] = None,
    auto_reload: bool = False,
    reload_interval: float = 60.0
) -> UnifiedLoggerFactory:
    """
    从配置文件初始化日志系统
    
    Args:
        config_path: 配置文件路径
        override_config: 覆盖配置 (可选)
        auto_reload: 是否自动重载配置
        reload_interval: 重载间隔 (秒)
    
    Returns:
        UnifiedLoggerFactory 实例
    """
    config = load_config(config_path)
    
    # 应用覆盖配置
    if override_config:
        config = _merge_config(config, override_config)
    
    factory = UnifiedLoggerFactory()
    factory.initialize_from_config(config)
    
    # 启动自动重载 (可选)
    if auto_reload:
        config_manager = ConfigManager(config_path)
        config_manager.add_listener(lambda old, new: _log_config_change(old, new))
        config_manager.start_auto_reload(reload_interval)
    
    return factory


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """合并配置字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def _log_config_change(old_config: Dict[str, Any], new_config: Dict[str, Any]):
    """记录配置变更"""
    print(f"Configuration changed at {datetime.now().isoformat()}")


# 为 UnifiedLoggerFactory 添加从配置初始化的方法
def _initialize_from_config(self, config: Dict[str, Any]) -> 'UnifiedLoggerFactory':
    """
    从配置字典初始化日志系统

    Args:
        config: 配置字典

    Returns:
        self
    """
    import logging
    import logging.handlers
    import queue
    import sys
    from pathlib import Path

    with self._lock:
        if self._initialized:
            return self

        # 基础配置
        log_level = config.get('log_level', 'INFO')
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)

        # 日志目录
        log_dir_str = config.get('log_dir', 'logs')
        encoding = config.get('encoding', 'utf-8')

        # 相对于 backend_python 目录
        self._log_dir = Path(__file__).parent.parent / log_dir_str
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # 队列配置
        queue_config = config.get('queue', {})
        queue_size = queue_config.get('max_size', 10000)
        self._log_queue = queue.Queue(maxsize=queue_size)

        # 轮转配置
        rotation = config.get('rotation', {})
        app_rotation = rotation.get('app_log', {})
        ai_rotation = rotation.get('ai_log', {})
        error_rotation = rotation.get('error_log', {})

        # 处理器级别
        console_level = config.get('console_level', 'INFO')
        file_level = config.get('file_level', 'DEBUG')

        # 创建处理器
        self._handlers = []
        handlers_config = config.get('handlers', {})

        # 控制台处理器
        if handlers_config.get('console', {}).get('enabled', True):
            console_config = handlers_config['console']
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, console_config.get('level', 'INFO').upper()))
            console_handler.setFormatter(JSONFormatter())
            self._handlers.append(console_handler)

        # 应用日志文件处理器
        if handlers_config.get('app_file', {}).get('enabled', True):
            app_config = handlers_config['app_file']
            app_handler = logging.handlers.RotatingFileHandler(
                self._log_dir / 'app.log',
                maxBytes=app_config.get('maxBytes', 10 * 1024 * 1024),
                backupCount=app_config.get('backupCount', 7),
                encoding=encoding
            )
            app_handler.setLevel(getattr(logging, file_level.upper()))
            app_handler.setFormatter(JSONFormatter())
            self._handlers.append(app_handler)

        # AI 响应专用处理器
        if handlers_config.get('ai_file', {}).get('enabled', True):
            ai_config = handlers_config['ai_file']
            ai_handler = logging.handlers.RotatingFileHandler(
                self._log_dir / 'ai_responses.log',
                maxBytes=ai_config.get('maxBytes', 100 * 1024 * 1024),
                backupCount=ai_config.get('backupCount', 30),
                encoding=encoding
            )
            ai_handler.setLevel(logging.INFO)
            ai_handler.setFormatter(JSONFormatter())
            ai_handler.addFilter(lambda r: 'ai' in r.name.lower())
            self._handlers.append(ai_handler)

        # 错误日志专用处理器
        if handlers_config.get('error_file', {}).get('enabled', True):
            error_config = handlers_config['error_file']
            error_handler = logging.handlers.RotatingFileHandler(
                self._log_dir / 'errors.log',
                maxBytes=error_config.get('maxBytes', 10 * 1024 * 1024),
                backupCount=error_config.get('backupCount', 15),
                encoding=encoding
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter())
            self._handlers.append(error_handler)

        # 启动后台监听器
        self._listener = logging.handlers.QueueListener(
            self._log_queue,
            *self._handlers,
            respect_handler_level=True
        )
        self._listener.start()

        # 配置根日志器
        self._configure_root_logger(numeric_level)

        # 配置特定日志器
        loggers_config = config.get('loggers', {})
        for name, logger_config in loggers_config.items():
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, logger_config.get('level', 'INFO').upper()))

        # 抑制第三方库日志
        for logger_name in config.get('suppress_loggers', []):
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        self._initialized = True

        # 记录初始化日志
        root_logger = logging.getLogger()
        root_logger.info(
            f"UnifiedLoggerFactory initialized from config: "
            f"log_dir={self._log_dir}, level={log_level}, queue_size={queue_size}"
        )

        return self


# 动态添加方法到 UnifiedLoggerFactory
UnifiedLoggerFactory.initialize_from_config = _initialize_from_config
