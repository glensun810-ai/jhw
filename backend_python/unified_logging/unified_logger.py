"""
统一日志工厂模块

实现异步队列日志写入，解决同步阻塞导致的性能瓶颈问题。

核心特性:
- 异步队列日志写入 (QueueHandler + QueueListener)
- JSON 结构化日志格式
- 链路追踪支持 (trace_id, span_id)
- 多处理器分发 (Console + File + AI 专用 + Error 专用)
- 线程安全的日志上下文
- 优雅关闭机制
- 错误日志增强（分类、轮转、保留策略）

架构设计:
    应用代码 -> UnifiedLogger -> QueueHandler -> Queue -> QueueListener -> Handlers -> Files/Console

性能指标:
- 日志吞吐量：10000+ 条/秒
- 主线程延迟：<1ms (P99)
- 队列容量：10000 条 (可配置)
"""

import logging
import logging.handlers
import queue
import json
import uuid
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import contextvars
import threading
import traceback
import glob
import re


# ============================================================================
# 全局上下文变量
# ============================================================================

# 链路追踪上下文 (线程/协程隔离)
_trace_context = contextvars.ContextVar('trace_context', default={})

# 全局工厂实例 (单例)
_factory_instance: Optional['UnifiedLoggerFactory'] = None
_factory_lock = threading.Lock()


# ============================================================================
# JSON 格式化器
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    JSON 格式化器

    输出结构化 JSON 日志，便于日志聚合系统解析。

    输出格式:
    {
        "timestamp": "2026-02-19T10:30:00.123456",
        "level": "INFO",
        "logger": "wechat_backend.api",
        "message": "API 请求成功",
        "module": "api_handler",
        "function": "handle_request",
        "line": 42,
        "thread": "MainThread",
        "process": 12345,
        "trace_id": "abc-123-xyz",
        "span_id": "def-456",
        "endpoint": "/api/ai/chat",
        "user_id": "user_001"
    }
    """

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'process': record.process,
        }

        # 注入链路追踪上下文
        context = _trace_context.get()
        if context:
            if 'trace_id' in context:
                log_data['trace_id'] = context['trace_id']
            if 'span_id' in context:
                log_data['span_id'] = context['span_id']

        # 添加额外字段 (排除标准字段)
        if self.include_extra:
            exclude_keys = {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                'message', 'trace_id', 'span_id'
            }
            for key, value in record.__dict__.items():
                if key not in exclude_keys:
                    try:
                        # 确保值可 JSON 序列化
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        # 不可序列化的值转为字符串
                        log_data[key] = str(value)

        # 处理异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else 'Unknown',
                'message': str(record.exc_info[1]) if record.exc_info[1] else '',
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================================
# 错误日志格式化器（增强版）
# ============================================================================

class ErrorLogFormatter(logging.Formatter):
    """
    错误日志格式化器

    专门为错误日志设计，包含更详细的上下文信息
    """

    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # 位置信息
        if record.filename:
            log_data['location'] = {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName,
                'module': record.module,
            }

        # 注入链路追踪上下文
        context = _trace_context.get()
        if context:
            log_data['trace'] = context

        # 添加额外字段
        exclude_keys = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'trace_id', 'span_id', 'level', 'logger', 'timestamp'
        }
        for key, value in record.__dict__.items():
            if key not in exclude_keys:
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        # 处理异常信息（增强版）
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            log_data['exception'] = {
                'type': exc_type.__name__ if exc_type else 'Unknown',
                'message': str(exc_val) if exc_val else '',
                'traceback': self.formatException(record.exc_info),
            }
            # 添加异常链信息
            if exc_val and hasattr(exc_val, '__cause__') and exc_val.__cause__:
                log_data['exception']['cause'] = {
                    'type': type(exc_val.__cause__).__name__,
                    'message': str(exc_val.__cause__),
                }
            if exc_val and hasattr(exc_val, '__context__') and exc_val.__context__:
                log_data['exception']['context'] = {
                    'type': type(exc_val.__context__).__name__,
                    'message': str(exc_val.__context__),
                }

        # 进程和线程信息
        log_data['process_info'] = {
            'pid': os.getpid(),
            'thread': record.threadName,
            'thread_id': record.thread,
        }

        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================================
# 日志保留策略管理器
# ============================================================================

class RetentionManager:
    """
    日志保留策略管理器

    功能:
    - 定期清理过期日志文件
    - 按天数保留
    - 按大小保留
    - 压缩旧日志
    """

    def __init__(
        self,
        log_dir: Path,
        retention_days: int = 30,
        max_total_size_mb: int = 1000,
        compress_after_days: int = 7,
    ):
        """
        Args:
            log_dir: 日志目录
            retention_days: 日志保留天数
            max_total_size_mb: 日志总大小上限（MB）
            compress_after_days: 多少天后压缩日志
        """
        self.log_dir = log_dir
        self.retention_days = retention_days
        self.max_total_size_mb = max_total_size_mb
        self.compress_after_days = compress_after_days
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_background_cleanup(self, check_interval_hours: int = 1):
        """启动后台清理任务"""
        def cleanup_loop():
            while not self._stop_event.is_set():
                try:
                    self.cleanup()
                except Exception as e:
                    logging.getLogger('unified_logging.retention').error(
                        f"Cleanup failed: {e}", exc_info=True
                    )
                # 等待指定间隔或停止信号
                self._stop_event.wait(timeout=check_interval_hours * 3600)

        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="LogRetentionCleanup"
        )
        self._cleanup_thread.start()

    def stop_background_cleanup(self):
        """停止后台清理任务"""
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=10)

    def cleanup(self):
        """执行清理任务"""
        now = datetime.now()
        cutoff_date = now - timedelta(days=self.retention_days)
        compress_date = now - timedelta(days=self.compress_after_days)

        # 清理过期文件
        deleted_count = 0
        compressed_count = 0
        total_size = 0

        for log_file in self._find_log_files():
            try:
                file_stat = log_file.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                file_size_mb = file_stat.st_size / (1024 * 1024)
                total_size += file_size_mb

                # 删除过期文件
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    continue

                # 压缩旧日志（如果尚未压缩）
                if file_mtime < compress_date and not log_file.name.endswith('.gz'):
                    if self._compress_file(log_file):
                        compressed_count += 1
            except Exception as e:
                logging.getLogger('unified_logging.retention').warning(
                    f"Error processing {log_file}: {e}"
                )

        # 如果总大小超过限制，删除最旧的文件
        if total_size > self.max_total_size_mb:
            self._enforce_size_limit()

        logging.getLogger('unified_logging.retention').info(
            f"Cleanup completed: deleted={deleted_count}, "
            f"compressed={compressed_count}, total_size_mb={total_size:.2f}"
        )

    def _find_log_files(self) -> List[Path]:
        """查找所有日志文件"""
        patterns = ['*.log', '*.log.*', '*.gz']
        files = []
        for pattern in patterns:
            files.extend(self.log_dir.glob(pattern))
        return files

    def _compress_file(self, file_path: Path) -> bool:
        """压缩日志文件"""
        import gzip
        try:
            gz_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            # 压缩成功后删除原文件
            file_path.unlink()
            return True
        except Exception as e:
            logging.getLogger('unified_logging.retention').warning(
                f"Failed to compress {file_path}: {e}"
            )
            # 如果压缩失败但生成了部分文件，清理它
            gz_path = file_path.with_suffix(file_path.suffix + '.gz')
            if gz_path.exists():
                gz_path.unlink()
            return False

    def _enforce_size_limit(self):
        """强制执行大小限制"""
        # 获取所有日志文件并按修改时间排序
        log_files = self._find_log_files()
        log_files_with_size = [
            (f, f.stat().st_size)
            for f in log_files
            if f.exists()
        ]
        # 按修改时间排序（最旧的在前）
        log_files_with_size.sort(key=lambda x: x[1].st_mtime)

        current_total_mb = sum(size for _, size in log_files_with_size) / (1024 * 1024)
        deleted_count = 0

        while current_total_mb > self.max_total_size_mb and log_files_with_size:
            oldest_file, _ = log_files_with_size.pop(0)
            if oldest_file.exists():
                try:
                    oldest_file.unlink()
                    deleted_count += 1
                    current_total_mb = (
                        sum(size for _, size in log_files_with_size) / (1024 * 1024)
                    )
                except Exception as e:
                    logging.getLogger('unified_logging.retention').warning(
                        f"Failed to delete {oldest_file}: {e}"
                    )
                    break

        if deleted_count > 0:
            logging.getLogger('unified_logging.retention').info(
                f"Enforced size limit: deleted {deleted_count} files"
            )


# ============================================================================
# 统一日志器
# ============================================================================

class UnifiedLogger:
    """
    统一日志器
    
    提供便捷的日志记录接口，支持链路追踪上下文注入。
    
    使用示例:
        logger = UnifiedLogger('wechat_backend.api', log_queue)
        
        # 设置链路追踪
        logger.set_trace_context(trace_id='abc-123')
        
        # 记录日志
        logger.info('API 请求', endpoint='/api/chat', user_id='user_001')
        logger.error('处理失败', error=str(e), exc_info=True)
    """
    
    def __init__(self, name: str, log_queue: queue.Queue):
        self.name = name
        self.log_queue = log_queue
        self._logger = logging.getLogger(name)
        self._context_lock = threading.Lock()
    
    def set_trace_context(self, trace_id: str = None, span_id: str = None) -> Dict[str, str]:
        """
        设置链路追踪上下文
        
        Args:
            trace_id: 追踪 ID，自动生成如果未提供
            span_id: 跨度 ID，自动生成如果未提供
        
        Returns:
            设置的上下文字典
        """
        context = {
            'trace_id': trace_id or str(uuid.uuid4()),
            'span_id': span_id or str(uuid.uuid4())[:8]
        }
        _trace_context.set(context)
        return context
    
    def get_trace_context(self) -> Dict[str, str]:
        """获取当前链路追踪上下文"""
        return _trace_context.get()
    
    def clear_trace_context(self):
        """清除链路追踪上下文"""
        _trace_context.set({})
    
    def _log(self, level: int, message: str, exc_info: bool = False, **kwargs):
        """
        底层日志记录方法
        
        Args:
            level: 日志级别
            message: 日志消息
            exc_info: 是否记录异常堆栈
            **kwargs: 额外字段
        """
        # 合并上下文和额外字段
        context = _trace_context.get()
        extra = {**context, **kwargs} if context else kwargs
        
        # 记录日志
        self._logger.log(level, message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录 INFO 级别日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """记录 ERROR 级别日志"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """记录异常日志 (自动包含堆栈信息)"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)


# ============================================================================
# 日志上下文管理器
# ============================================================================

class LoggingContext:
    """
    日志上下文管理器
    
    使用 with 语句自动管理链路追踪上下文。
    
    使用示例:
        with LoggingContext(trace_id='abc-123', span_id='def-456'):
            logger.info('在上下文中记录日志')
        # 退出 with 块后自动恢复原上下文
    """
    
    def __init__(self, trace_id: str = None, span_id: str = None, **extra_context):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())[:8]
        self.extra_context = extra_context
        self._token = None
    
    def __enter__(self) -> 'LoggingContext':
        context = {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            **self.extra_context
        }
        self._token = _trace_context.set(context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token is not None:
            _trace_context.reset(self._token)
        return False


# ============================================================================
# 统一日志工厂 (单例)
# ============================================================================

class UnifiedLoggerFactory:
    """
    统一日志工厂 (单例模式)
    
    负责:
    - 初始化日志系统
    - 创建和管理异步队列
    - 配置日志处理器
    - 提供日志器实例
    
    使用示例:
        # 应用启动时初始化
        factory = UnifiedLoggerFactory()
        factory.initialize(
            log_level='INFO',
            log_dir='logs',
            queue_size=10000,
            max_bytes=10*1024*1024,
            backup_count=7
        )
        
        # 获取日志器
        logger = factory.get_logger('wechat_backend.api')
        
        # 应用关闭时
        factory.shutdown()
    """
    
    def __init__(self):
        self._initialized = False
        self._log_queue: Optional[queue.Queue] = None
        self._listener: Optional[logging.handlers.QueueListener] = None
        self._handlers: List[logging.Handler] = []
        self._error_handlers: List[logging.Handler] = []
        self._lock = threading.Lock()
        self._log_dir: Optional[Path] = None
        self._retention_manager: Optional[RetentionManager] = None
    
    def __new__(cls) -> 'UnifiedLoggerFactory':
        global _factory_instance, _factory_lock
        
        with _factory_lock:
            if _factory_instance is None:
                _factory_instance = super().__new__(cls)
            return _factory_instance
    
    def initialize(
        self,
        log_level: str = None,
        log_dir: str = None,
        queue_size: int = 10000,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 7,
        console_level: str = 'INFO',
        file_level: str = 'DEBUG',
        enable_ai_handler: bool = True,
        ai_max_bytes: int = 100 * 1024 * 1024,
        ai_backup_count: int = 30,
        enable_error_handler: bool = True,
        error_max_bytes: int = 50 * 1024 * 1024,
        error_backup_count: int = 10,
        retention_days: int = 30,
        max_total_size_mb: int = 1000,
        compress_after_days: int = 7,
        enable_retention_cleanup: bool = True,
    ) -> 'UnifiedLoggerFactory':
        """
        初始化日志系统

        Args:
            log_level: 根日志级别 (默认从环境变量 LOG_LEVEL 读取，或 INFO)
            log_dir: 日志目录 (默认 backend_python/logs)
            queue_size: 队列大小 (默认 10000)
            max_bytes: 日志文件最大大小 (默认 10MB)
            backup_count: 日志备份数量 (默认 7)
            console_level: 控制台日志级别 (默认 INFO)
            file_level: 文件日志级别 (默认 DEBUG)
            enable_ai_handler: 是否启用 AI 响应专用处理器 (默认 True)
            ai_max_bytes: AI 日志文件最大大小 (默认 100MB)
            ai_backup_count: AI 日志备份数量 (默认 30)
            enable_error_handler: 是否启用错误日志专用处理器 (默认 True)
            error_max_bytes: 错误日志文件最大大小 (默认 50MB)
            error_backup_count: 错误日志备份数量 (默认 10)
            retention_days: 日志保留天数 (默认 30 天)
            max_total_size_mb: 日志总大小上限 (默认 1000MB)
            compress_after_days: 多少天后压缩日志 (默认 7 天)
            enable_retention_cleanup: 是否启用后台清理任务 (默认 True)

        Returns:
            self (支持链式调用)
        """
        with self._lock:
            if self._initialized:
                return self

            # 解析日志级别
            if log_level is None:
                log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
            numeric_level = getattr(logging, log_level, logging.INFO)

            # 确定日志目录
            if log_dir is None:
                # 默认使用 backend_python/logs
                self._log_dir = Path(__file__).parent.parent / 'logs'
            else:
                self._log_dir = Path(log_dir)

            # 创建日志目录
            self._log_dir.mkdir(parents=True, exist_ok=True)

            # 创建异步队列
            self._log_queue = queue.Queue(maxsize=queue_size)

            # 创建处理器
            self._handlers = self._create_handlers(
                console_level=console_level,
                file_level=file_level,
                max_bytes=max_bytes,
                backup_count=backup_count,
                enable_ai_handler=enable_ai_handler,
                ai_max_bytes=ai_max_bytes,
                ai_backup_count=ai_backup_count,
            )

            # 创建错误日志处理器
            if enable_error_handler:
                self._error_handlers = self._create_error_handlers(
                    error_max_bytes=error_max_bytes,
                    error_backup_count=error_backup_count,
                )

            # 启动后台监听器
            all_handlers = self._handlers + self._error_handlers
            self._listener = logging.handlers.QueueListener(
                self._log_queue,
                *all_handlers,
                respect_handler_level=True
            )
            self._listener.start()

            # 配置根日志器
            self._configure_root_logger(numeric_level)

            # 初始化保留策略管理器
            if enable_retention_cleanup:
                self._retention_manager = RetentionManager(
                    log_dir=self._log_dir,
                    retention_days=retention_days,
                    max_total_size_mb=max_total_size_mb,
                    compress_after_days=compress_after_days,
                )
                self._retention_manager.start_background_cleanup()

            self._initialized = True

            # 记录初始化日志
            root_logger = logging.getLogger()
            root_logger.info(
                f"UnifiedLoggerFactory initialized: log_dir={self._log_dir}, "
                f"level={log_level}, queue_size={queue_size}, "
                f"error_handler={enable_error_handler}, retention={enable_retention_cleanup}"
            )

            return self
    
    def _create_handlers(
        self,
        console_level: str,
        file_level: str,
        max_bytes: int,
        backup_count: int,
        enable_ai_handler: bool,
        ai_max_bytes: int,
        ai_backup_count: int,
    ) -> List[logging.Handler]:
        """创建日志处理器列表"""
        handlers = []
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level, logging.INFO))
        console_handler.setFormatter(JSONFormatter())
        handlers.append(console_handler)
        
        # 2. 文件处理器 (异步轮转)
        file_path = self._log_dir / 'app.log'
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, file_level, logging.DEBUG))
        file_handler.setFormatter(JSONFormatter())
        handlers.append(file_handler)
        
        # 3. AI 响应专用处理器 (可选)
        if enable_ai_handler:
            ai_path = self._log_dir / 'ai_responses.log'
            ai_handler = logging.handlers.RotatingFileHandler(
                ai_path,
                maxBytes=ai_max_bytes,
                backupCount=ai_backup_count,
                encoding='utf-8'
            )
            ai_handler.setLevel(logging.INFO)
            ai_handler.setFormatter(JSONFormatter())
            # 只处理包含'ai'的日志器
            ai_handler.addFilter(lambda r: 'ai' in r.name.lower())
            handlers.append(ai_handler)
        
        # 4. 错误专用处理器 (记录所有 ERROR 及以上级别)
        error_path = self._log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        handlers.append(error_handler)
        
        return handlers

    def _create_error_handlers(
        self,
        error_max_bytes: int,
        error_backup_count: int,
    ) -> List[logging.Handler]:
        """创建错误日志处理器列表"""
        error_handlers = []

        # 1. 所有错误汇总文件
        error_path = self._log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_path,
            maxBytes=error_max_bytes,
            backupCount=error_backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(ErrorLogFormatter())
        error_handlers.append(error_handler)

        # 2. 按错误分类创建专用文件
        error_categories = ['api', 'database', 'ai', 'system', 'security', 'network']
        for category in error_categories:
            category_path = self._log_dir / f'errors_{category}.log'
            category_handler = logging.handlers.RotatingFileHandler(
                category_path,
                maxBytes=error_max_bytes,
                backupCount=error_backup_count,
                encoding='utf-8'
            )
            category_handler.setLevel(logging.ERROR)
            category_handler.setFormatter(ErrorLogFormatter())
            # 只处理对应分类的日志
            category_handler.addFilter(
                lambda r, cat=category: cat in r.name.lower() or r.levelno >= logging.ERROR
            )
            error_handlers.append(category_handler)

        return handlers

    def _configure_root_logger(self, numeric_level: int):
        """配置根日志器"""
        root = logging.getLogger()
        root.setLevel(numeric_level)
        
        # 清除现有处理器
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        # 添加队列处理器 (非阻塞)
        queue_handler = logging.handlers.QueueHandler(self._log_queue)
        root.addHandler(queue_handler)
        
        # 配置常用日志器级别
        logging.getLogger('wechat_backend').setLevel(numeric_level)
        logging.getLogger('wechat_backend.api').setLevel(logging.INFO)
        logging.getLogger('wechat_backend.database').setLevel(logging.WARNING)
        logging.getLogger('wechat_backend.ai').setLevel(logging.INFO)
        
        # 抑制第三方库的冗余日志
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> UnifiedLogger:
        """
        获取统一日志器
        
        Args:
            name: 日志器名称 (如 'wechat_backend.api')
        
        Returns:
            UnifiedLogger 实例
        """
        if not self._initialized:
            # 自动初始化 (使用默认配置)
            self.initialize()
        
        return UnifiedLogger(name, self._log_queue)
    
    def get_queue(self) -> queue.Queue:
        """获取日志队列 (用于高级用法)"""
        return self._log_queue
    
    def shutdown(self, timeout: float = 5.0):
        """
        关闭日志系统

        Args:
            timeout: 等待队列清空的最大时间 (秒)
        """
        if not self._initialized:
            return

        # 停止监听器
        if self._listener:
            self._listener.stop()
            self._listener = None

        # 停止保留策略管理器
        if self._retention_manager:
            self._retention_manager.stop_background_cleanup()
            self._retention_manager = None

        # 关闭所有处理器
        for handler in self._handlers:
            try:
                handler.close()
            except Exception:
                pass
        self._handlers.clear()

        # 关闭错误处理器
        for handler in self._error_handlers:
            try:
                handler.close()
            except Exception:
                pass
        self._error_handlers.clear()

        # 关闭根日志器
        logging.shutdown()

        self._initialized = False
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    @property
    def log_dir(self) -> Optional[Path]:
        """获取日志目录"""
        return self._log_dir


# ============================================================================
# 便捷函数
# ============================================================================

def get_logger(name: str) -> UnifiedLogger:
    """
    便捷函数：获取统一日志器
    
    使用示例:
        from backend_python.logging import get_logger
        
        logger = get_logger('wechat_backend.api')
        logger.info('Hello, World!')
    """
    factory = UnifiedLoggerFactory()
    return factory.get_logger(name)


def init_logging(**kwargs) -> UnifiedLoggerFactory:
    """
    便捷函数：初始化日志系统
    
    使用示例:
        from backend_python.logging import init_logging
        
        factory = init_logging(log_level='DEBUG', log_dir='logs')
    """
    factory = UnifiedLoggerFactory()
    factory.initialize(**kwargs)
    return factory


def shutdown_logging(timeout: float = 5.0):
    """
    便捷函数：关闭日志系统
    
    使用示例:
        import atexit
        from backend_python.logging import shutdown_logging
        
        atexit.register(shutdown_logging)
    """
    factory = UnifiedLoggerFactory()
    factory.shutdown(timeout=timeout)


# ============================================================================
# 自动注册 (可选)
# ============================================================================

# 如果需要在模块导入时自动初始化，取消下面注释
# init_logging()
