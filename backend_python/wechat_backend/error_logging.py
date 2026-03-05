"""
增强错误日志配置模块

功能特性:
- 错误分类记录（API 错误、数据库错误、AI 错误、系统错误）
- 专用错误日志文件（按错误类型分离）
- 错误上下文增强（堆栈、环境变量、请求信息等）
- 错误频率限制（避免日志风暴）
- 错误统计和告警集成

使用示例:
    from wechat_backend.error_logging import (
        ErrorLogger,
        ErrorCategory,
        get_error_logger,
        log_api_error,
        log_db_error,
        log_ai_error,
        log_system_error,
    )

    # 方式 1: 使用分类日志函数
    log_api_error("API 请求失败", request_data, exception)
    log_db_error("数据库操作失败", query, params)
    log_ai_error("AI 调用失败", model_name, prompt)
    log_system_error("系统错误", module_name)

    # 方式 2: 使用 ErrorLogger 实例
    error_logger = get_error_logger()
    error_logger.log_error(ErrorCategory.API, "错误消息", context)
"""

import logging
import json
import os
import sys
import time
import traceback
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from collections import defaultdict
import hashlib


class ErrorCategory(Enum):
    """错误分类"""
    API = "api"  # API 相关错误
    DATABASE = "database"  # 数据库错误
    AI = "ai"  # AI 模型调用错误
    SYSTEM = "system"  # 系统级错误
    SECURITY = "security"  # 安全相关错误
    NETWORK = "network"  # 网络错误
    VALIDATION = "validation"  # 数据验证错误
    CONFIGURATION = "configuration"  # 配置错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"  # 低 - 可恢复的错误
    MEDIUM = "medium"  # 中 - 影响部分功能
    HIGH = "high"  # 高 - 影响核心功能
    CRITICAL = "critical"  # 严重 - 系统不可用


class RateLimiter:
    """
    错误频率限制器

    防止相同错误在短时间内大量记录
    """

    def __init__(self, max_count: int = 10, window_seconds: int = 60):
        """
        Args:
            max_count: 时间窗口内允许的最大错误数
            window_seconds: 时间窗口（秒）
        """
        self.max_count = max_count
        self.window_seconds = window_seconds
        self._error_counts: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _generate_key(self, category: ErrorCategory, message: str) -> str:
        """生成错误唯一标识"""
        key_str = f"{category.value}:{message}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def should_log(self, category: ErrorCategory, message: str) -> bool:
        """
        判断是否应该记录此错误

        Returns:
            True 表示应该记录，False 表示应该跳过
        """
        key = self._generate_key(category, message)
        now = time.time()

        with self._lock:
            # 清理过期记录
            self._error_counts[key] = [
                ts for ts in self._error_counts[key]
                if now - ts < self.window_seconds
            ]

            # 检查是否超过阈值
            if len(self._error_counts[key]) >= self.max_count:
                return False

            # 记录此次错误
            self._error_counts[key].append(now)
            return True

    def get_count(self, category: ErrorCategory, message: str) -> int:
        """获取当前时间窗口内的错误计数"""
        key = self._generate_key(category, message)
        now = time.time()

        with self._lock:
            return len([
                ts for ts in self._error_counts[key]
                if now - ts < self.window_seconds
            ])


class ErrorContext:
    """
    错误上下文管理器

    收集和格式化错误的上下文信息
    """

    @staticmethod
    def collect(
        exception: Optional[Exception] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        include_env: bool = True,
        include_stack: bool = True,
    ) -> Dict[str, Any]:
        """
        收集错误上下文

        Args:
            exception: 异常对象
            extra_context: 额外的上下文字典
            include_env: 是否包含环境变量
            include_stack: 是否包含堆栈信息

        Returns:
            上下文字典
        """
        context = {}

        # 时间戳
        context['timestamp'] = datetime.now(timezone.utc).isoformat()
        context['unix_timestamp'] = int(time.time())

        # 异常信息
        if exception:
            context['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'args': ErrorContext._safe_serialize(getattr(exception, 'args', None)),
            }

        # 堆栈信息
        if include_stack:
            context['stack_trace'] = traceback.format_exc().strip() if exception else None
            context['stack_frames'] = ErrorContext._extract_stack_frames()

        # 额外上下文
        if extra_context:
            context['extra'] = ErrorContext._safe_serialize(extra_context)

        # 环境变量（敏感信息已过滤）
        if include_env:
            context['environment'] = ErrorContext._collect_env_info()

        # 系统信息
        context['system'] = ErrorContext._collect_system_info()

        return context

    @staticmethod
    def _safe_serialize(obj: Any) -> Any:
        """安全地序列化对象"""
        if obj is None:
            return None
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

    @staticmethod
    def _extract_stack_frames(skip_frames: int = 3) -> List[Dict[str, Any]]:
        """提取堆栈帧"""
        frames = []
        for frame_info in traceback.extract_stack()[:-skip_frames]:
            frames.append({
                'filename': frame_info.filename,
                'lineno': frame_info.lineno,
                'name': frame_info.name,
                'line': frame_info.line,
            })
        return frames

    @staticmethod
    def _collect_env_info() -> Dict[str, Any]:
        """收集环境变量信息"""
        sensitive_keys = {
            'SECRET', 'KEY', 'TOKEN', 'PASSWORD', 'SECRET_KEY',
            'API_KEY', 'ACCESS_TOKEN', 'PRIVATE'
        }

        env_info = {}
        for key, value in os.environ.items():
            # 过滤敏感信息
            if any(s in key.upper() for s in sensitive_keys):
                env_info[key] = "***REDACTED***"
            else:
                env_info[key] = value

        return {
            'env_vars': env_info,
            'flask_env': os.getenv('FLASK_ENV', 'unknown'),
            'python_version': sys.version,
            'platform': sys.platform,
        }

    @staticmethod
    def _collect_system_info() -> Dict[str, Any]:
        """收集系统信息"""
        import platform
        return {
            'hostname': platform.node(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'processor': platform.processor(),
        }


class ErrorLogger:
    """
    增强错误日志记录器

    提供错误分类、上下文增强、频率限制等功能
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        enable_rate_limit: bool = True,
        rate_limit_count: int = 10,
        rate_limit_window: int = 60,
        enable_console: bool = True,
        enable_json_format: bool = True,
    ):
        """
        Args:
            log_dir: 日志目录
            enable_rate_limit: 是否启用频率限制
            rate_limit_count: 频率限制计数
            rate_limit_window: 频率限制窗口（秒）
            enable_console: 是否输出到控制台
            enable_json_format: 是否使用 JSON 格式
        """
        self._initialized = False
        self._lock = threading.Lock()

        # 配置
        self.enable_rate_limit = enable_rate_limit
        self.enable_console = enable_console
        self.enable_json_format = enable_json_format

        # 频率限制器
        self._rate_limiter = RateLimiter(
            max_count=rate_limit_count,
            window_seconds=rate_limit_window
        )

        # 日志目录
        if log_dir is None:
            self.log_dir = Path(__file__).parent.parent / 'logs' / 'errors'
        else:
            self.log_dir = Path(log_dir)

        # 错误分类日志器映射
        self._category_loggers: Dict[ErrorCategory, logging.Logger] = {}

        # 错误统计
        self._error_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'last_seen': None, 'first_seen': None}
        )

        # 告警回调
        self._alert_callbacks: List[Callable] = []

    def initialize(self):
        """初始化错误日志系统"""
        with self._lock:
            if self._initialized:
                return

            # 创建日志目录
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # 为每个错误分类创建专用日志器
            for category in ErrorCategory:
                self._setup_category_logger(category)

            # 创建根错误日志器
            self._setup_root_logger()

            self._initialized = True

    def _setup_category_logger(self, category: ErrorCategory):
        """为错误分类设置日志器"""
        logger_name = f"errors.{category.value}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)

        # 清除现有处理器
        logger.handlers = []

        # 文件处理器
        file_path = self.log_dir / f"{category.value}_errors.log"
        file_handler = self._create_file_handler(file_path)
        logger.addHandler(file_handler)

        # 控制台处理器（可选）
        if self.enable_console:
            console_handler = self._create_console_handler()
            logger.addHandler(console_handler)

        self._category_loggers[category] = logger

    def _setup_root_logger(self):
        """设置根错误日志器"""
        logger = logging.getLogger('errors')
        logger.setLevel(logging.ERROR)
        logger.handlers = []

        # 所有错误汇总文件
        file_path = self.log_dir / 'all_errors.log'
        file_handler = self._create_file_handler(file_path)
        logger.addHandler(file_handler)

        if self.enable_console:
            console_handler = self._create_console_handler()
            logger.addHandler(console_handler)

    def _create_file_handler(self, file_path: Path) -> logging.Handler:
        """创建文件处理器"""
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            file_path,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        handler.setLevel(logging.ERROR)

        if self.enable_json_format:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
            ))

        return handler

    def _create_console_handler(self) -> logging.Handler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.ERROR)

        if self.enable_json_format:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            ))

        return handler

    def log_error(
        self,
        category: ErrorCategory,
        message: str,
        exception: Optional[Exception] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        include_stack: bool = True,
        raise_exception: bool = False,
    ):
        """
        记录错误

        Args:
            category: 错误分类
            message: 错误消息
            exception: 异常对象
            extra_context: 额外上下文
            severity: 严重程度
            include_stack: 是否包含堆栈
            raise_exception: 是否重新抛出异常
        """
        if not self._initialized:
            self.initialize()

        # 频率限制检查
        if self.enable_rate_limit:
            if not self._rate_limiter.should_log(category, message):
                count = self._rate_limiter.get_count(category, message)
                # 只记录一次频率限制警告
                if count == self._rate_limiter.max_count + 1:
                    self._log_rate_limit_warning(category, message, count)
                return

        # 收集上下文
        context = ErrorContext.collect(
            exception=exception,
            extra_context=extra_context,
            include_stack=include_stack,
        )

        # 添加分类和严重程度
        context['category'] = category.value
        context['severity'] = severity.value

        # 获取日志器
        logger = self._category_loggers.get(category)
        root_logger = logging.getLogger('errors')

        # 格式化日志消息
        if self.enable_json_format:
            log_message = json.dumps({
                'message': message,
                **context
            }, ensure_ascii=False, default=str)
        else:
            log_message = f"{message} | Category: {category.value} | Severity: {severity.value}"

        # 记录日志
        if logger:
            logger.error(log_message, extra=context)
        root_logger.error(log_message, extra=context)

        # 更新统计
        self._update_stats(category, message, severity)

        # 触发告警
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            self._trigger_alerts(category, message, context)

        # 重新抛出异常（可选）
        if raise_exception and exception:
            raise exception

    def _log_rate_limit_warning(
        self,
        category: ErrorCategory,
        message: str,
        count: int
    ):
        """记录频率限制警告"""
        logger = logging.getLogger('errors.rate_limit')
        logger.warning(
            f"Rate limit reached for error: category={category.value}, "
            f"message='{message[:100]}...', count={count}"
        )

    def _update_stats(
        self,
        category: ErrorCategory,
        message: str,
        severity: ErrorSeverity
    ):
        """更新错误统计"""
        key = f"{category.value}:{message}"
        now = datetime.now(timezone.utc)

        stats = self._error_stats[key]
        stats['count'] += 1
        stats['last_seen'] = now.isoformat()
        if stats['first_seen'] is None:
            stats['first_seen'] = now.isoformat()
        stats['severity'] = severity.value

    def _trigger_alerts(
        self,
        category: ErrorCategory,
        message: str,
        context: Dict[str, Any]
    ):
        """触发告警回调"""
        alert_data = {
            'category': category.value,
            'message': message,
            'context': context,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        for callback in self._alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logging.getLogger('errors.alert').error(
                    f"Alert callback failed: {e}",
                    exc_info=True
                )

    def register_alert_callback(self, callback: Callable):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取错误统计"""
        return dict(self._error_stats)

    def get_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        total_errors = sum(s['count'] for s in self._error_stats.values())
        
        # 按分类统计
        category_stats = defaultdict(int)
        severity_stats = defaultdict(int)
        
        for key, stats in self._error_stats.items():
            category = key.split(':')[0]
            category_stats[category] += stats['count']
            severity_stats[stats.get('severity', 'unknown')] += stats['count']

        return {
            'total_errors': total_errors,
            'by_category': dict(category_stats),
            'by_severity': dict(severity_stats),
            'top_errors': sorted(
                [
                    {'key': k, **v}
                    for k, v in self._error_stats.items()
                ],
                key=lambda x: x['count'],
                reverse=True
            )[:10],
        }


# 全局错误日志器实例
_error_logger: Optional[ErrorLogger] = None
_error_logger_lock = threading.Lock()


def get_error_logger() -> ErrorLogger:
    """获取全局错误日志器"""
    global _error_logger
    if _error_logger is None:
        with _error_logger_lock:
            if _error_logger is None:
                _error_logger = ErrorLogger()
                _error_logger.initialize()
    return _error_logger


def init_error_logging(
    log_dir: Optional[str] = None,
    enable_rate_limit: bool = True,
    **kwargs
) -> ErrorLogger:
    """
    初始化错误日志系统

    Args:
        log_dir: 日志目录
        enable_rate_limit: 是否启用频率限制
        **kwargs: 其他参数传递给 ErrorLogger

    Returns:
        ErrorLogger 实例
    """
    global _error_logger
    with _error_logger_lock:
        _error_logger = ErrorLogger(
            log_dir=log_dir,
            enable_rate_limit=enable_rate_limit,
            **kwargs
        )
        _error_logger.initialize()
    return _error_logger


def log_error(
    category: ErrorCategory,
    message: str,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录错误"""
    get_error_logger().log_error(category, message, exception, **kwargs)


def log_api_error(
    message: str,
    request_data: Optional[Dict] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录 API 错误"""
    get_error_logger().log_error(
        ErrorCategory.API,
        message,
        exception,
        extra_context={'request_data': request_data},
        **kwargs
    )


def log_db_error(
    message: str,
    query: Optional[str] = None,
    params: Optional[tuple] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录数据库错误"""
    get_error_logger().log_error(
        ErrorCategory.DATABASE,
        message,
        exception,
        extra_context={'query': query, 'params': params},
        **kwargs
    )


def log_ai_error(
    message: str,
    model_name: Optional[str] = None,
    prompt: Optional[str] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录 AI 模型调用错误"""
    get_error_logger().log_error(
        ErrorCategory.AI,
        message,
        exception,
        extra_context={'model_name': model_name, 'prompt': prompt},
        **kwargs
    )


def log_system_error(
    message: str,
    module_name: Optional[str] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录系统错误"""
    get_error_logger().log_error(
        ErrorCategory.SYSTEM,
        message,
        exception,
        extra_context={'module_name': module_name},
        **kwargs
    )


def log_security_error(
    message: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """便捷函数：记录安全错误"""
    get_error_logger().log_error(
        ErrorCategory.SECURITY,
        message,
        exception,
        extra_context={'user_id': user_id, 'ip_address': ip_address},
        severity=ErrorSeverity.HIGH,
        **kwargs
    )


def get_error_summary() -> Dict[str, Any]:
    """获取错误摘要"""
    return get_error_logger().get_summary()


def register_error_alert(callback: Callable):
    """注册错误告警回调"""
    get_error_logger().register_alert_callback(callback)


# 导出所有符号
__all__ = [
    'ErrorCategory',
    'ErrorSeverity',
    'ErrorLogger',
    'ErrorContext',
    'RateLimiter',
    'get_error_logger',
    'init_error_logging',
    'log_error',
    'log_api_error',
    'log_db_error',
    'log_ai_error',
    'log_system_error',
    'log_security_error',
    'get_error_summary',
    'register_error_alert',
]
