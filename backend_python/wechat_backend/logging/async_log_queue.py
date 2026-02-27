"""
异步日志队列模块

功能：
1. 日志异步写入（非阻塞）
2. 批量处理日志
3. 背压处理
4. 优雅关闭

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import logging
import threading
import queue
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path


# ==================== 配置常量 ====================

class AsyncLogConfig:
    """异步日志配置"""
    # 队列最大大小
    MAX_QUEUE_SIZE = 10000
    # 批量写入大小
    BATCH_SIZE = 100
    # 批量写入间隔（秒）
    BATCH_INTERVAL = 1.0
    # 队列满时的处理策略
    QUEUE_FULL_POLICY = 'drop'  # 'drop' | 'block' | 'raise'
    # 优雅关闭超时（秒）
    SHUTDOWN_TIMEOUT = 5.0
    # 日志文件路径
    LOG_DIR = Path(__file__).parent.parent / 'logs'
    # 日志文件保留天数
    LOG_RETENTION_DAYS = 30


# ==================== 日志记录数据结构 ====================

class LogRecord:
    """日志记录"""
    
    def __init__(
        self,
        level: str,
        message: str,
        logger_name: str,
        timestamp: Optional[datetime] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.timestamp = timestamp or datetime.now()
        self.extra = extra or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'logger': self.logger_name,
            'message': self.message,
            'extra': self.extra
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_logging_record(cls, record: logging.LogRecord) -> 'LogRecord':
        """从 logging.LogRecord 创建"""
        extra = {}
        if hasattr(record, 'extra'):
            extra = record.extra
        elif hasattr(record, '__dict__'):
            extra = {
                k: v for k, v in record.__dict__.items()
                if k not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                            'levelname', 'levelno', 'lineno', 'module', 'msecs',
                            'message', 'msg', 'name', 'pathname', 'process',
                            'processName', 'relativeCreated', 'stack_info',
                            'exc_info', 'exc_text', 'thread', 'threadName']
            }
        
        return cls(
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            timestamp=datetime.fromtimestamp(record.created),
            extra=extra
        )


# ==================== 异步日志处理器 ====================

class AsyncLogHandler(logging.Handler):
    """
    异步日志处理器
    
    将日志记录放入队列，由后台线程异步写入
    """
    
    def __init__(
        self,
        handler: logging.Handler,
        queue_size: int = AsyncLogConfig.MAX_QUEUE_SIZE,
        batch_size: int = AsyncLogConfig.BATCH_SIZE,
        batch_interval: float = AsyncLogConfig.BATCH_INTERVAL
    ):
        """
        初始化异步处理器
        
        Args:
            handler: 实际写入的处理器
            queue_size: 队列大小
            batch_size: 批量写入大小
            batch_interval: 批量写入间隔
        """
        super().__init__()
        
        self.handler = handler
        self.queue = queue.Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
        self._shutdown = False
        self._records_dropped = 0
        self._records_written = 0
        
        # 注册退出处理
        import atexit
        atexit.register(self.shutdown)
    
    def emit(self, record: logging.LogRecord):
        """
        发出日志记录
        
        Args:
            record: 日志记录
        """
        if self._shutdown:
            return
        
        try:
            log_record = LogRecord.from_logging_record(record)
            
            # 尝试放入队列
            try:
                self.queue.put(log_record, block=False)
            except queue.Full:
                # 队列满时的处理
                if AsyncLogConfig.QUEUE_FULL_POLICY == 'drop':
                    self._records_dropped += 1
                    
                    # 每丢弃 100 条记录记录一次警告
                    if self._records_dropped % 100 == 0:
                        print(f"AsyncLogHandler: Dropped {self._records_dropped} log records")
                        
                elif AsyncLogConfig.QUEUE_FULL_POLICY == 'block':
                    self.queue.put(log_record, block=True, timeout=1.0)
                    
                elif AsyncLogConfig.QUEUE_FULL_POLICY == 'raise':
                    raise
                    
        except Exception:
            self.handleError(record)
    
    def _worker_loop(self):
        """工作线程循环"""
        batch: List[LogRecord] = []
        last_flush_time = time.time()
        
        while not self._shutdown:
            try:
                # 尝试获取日志记录
                try:
                    record = self.queue.get(timeout=0.1)
                    batch.append(record)
                except queue.Empty:
                    pass
                
                # 检查是否需要批量写入
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush_time >= self.batch_interval)
                )
                
                if should_flush and batch:
                    self._flush_batch(batch)
                    batch = []
                    last_flush_time = current_time
                
            except Exception as e:
                print(f"AsyncLogHandler worker error: {e}")
        
        # 关闭前写入剩余记录
        if batch:
            self._flush_batch(batch)
    
    def _flush_batch(self, batch: List[LogRecord]):
        """批量写入日志"""
        try:
            for record in batch:
                # 创建临时的 logging.LogRecord
                log_record = logging.LogRecord(
                    name=record.logger_name,
                    level=getattr(logging, record.level),
                    pathname='',
                    lineno=0,
                    msg=record.message,
                    args=(),
                    exc_info=None
                )
                log_record.created = record.timestamp.timestamp()
                log_record.extra = record.extra
                
                # 写入实际处理器
                self.handler.emit(log_record)
            
            self._records_written += len(batch)
            
        except Exception as e:
            print(f"AsyncLogHandler flush error: {e}")
    
    def shutdown(self):
        """关闭处理器"""
        if self._shutdown:
            return
        
        self._shutdown = True
        
        # 等待工作线程完成
        self._worker_thread.join(timeout=AsyncLogConfig.SHUTDOWN_TIMEOUT)
        
        # 报告统计
        if self._records_dropped > 0:
            print(
                f"AsyncLogHandler shutdown: "
                f"written={self._records_written}, dropped={self._records_dropped}"
            )
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            'queue_size': self.queue.qsize(),
            'records_written': self._records_written,
            'records_dropped': self._records_dropped
        }


# ==================== 异步日志管理器 ====================

class AsyncLogManager:
    """
    异步日志管理器
    
    单例模式，全局访问
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._handlers: Dict[str, AsyncLogHandler] = {}
        self._loggers: Dict[str, logging.Logger] = {}
        
        # 确保日志目录存在
        AsyncLogConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"AsyncLogManager initialized (log_dir={AsyncLogConfig.LOG_DIR})")
    
    def setup_async_logger(
        self,
        logger_name: str,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        queue_size: int = AsyncLogConfig.MAX_QUEUE_SIZE,
        batch_size: int = AsyncLogConfig.BATCH_SIZE,
        batch_interval: float = AsyncLogConfig.BATCH_INTERVAL
    ) -> logging.Logger:
        """
        设置异步日志记录器
        
        Args:
            logger_name: 日志记录器名称
            log_file: 日志文件路径
            level: 日志级别
            queue_size: 队列大小
            batch_size: 批量写入大小
            batch_interval: 批量写入间隔
            
        Returns:
            logging.Logger: 日志记录器
        """
        # 创建或获取日志记录器
        if logger_name in self._loggers:
            return self._loggers[logger_name]
        
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # 避免重复添加处理器
        if logger.handlers:
            self._loggers[logger_name] = logger
            return logger
        
        # 确定日志文件
        if not log_file:
            log_file = AsyncLogConfig.LOG_DIR / f"{logger_name.replace('.', '_')}.log"
        else:
            log_file = Path(log_file)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 创建异步处理器
        async_handler = AsyncLogHandler(
            handler=file_handler,
            queue_size=queue_size,
            batch_size=batch_size,
            batch_interval=batch_interval
        )
        
        # 添加处理器
        logger.addHandler(async_handler)
        self._handlers[logger_name] = async_handler
        self._loggers[logger_name] = logger
        
        print(
            f"Async logger setup: {logger_name} -> {log_file} "
            f"(queue_size={queue_size}, batch_size={batch_size})"
        )
        
        return logger
    
    def get_logger(self, logger_name: str) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            logger_name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器
        """
        if logger_name not in self._loggers:
            return self.setup_async_logger(logger_name)
        
        return self._loggers[logger_name]
    
    def shutdown(self):
        """关闭所有异步处理器"""
        print("AsyncLogManager shutting down...")
        
        for name, handler in self._handlers.items():
            print(f"Shutting down async handler: {name}")
            handler.shutdown()
        
        self._handlers.clear()
        self._loggers.clear()
        
        print("AsyncLogManager shutdown complete")
    
    def get_all_stats(self) -> Dict[str, Dict[str, int]]:
        """获取所有处理器的统计"""
        stats = {}
        for name, handler in self._handlers.items():
            stats[name] = handler.get_stats()
        return stats


# ==================== 便捷函数 ====================

def setup_async_logging(
    logger_name: str,
    log_file: Optional[str] = None,
    **kwargs
) -> logging.Logger:
    """
    设置异步日志
    
    Args:
        logger_name: 日志记录器名称
        log_file: 日志文件路径
        **kwargs: 额外参数
        
    Returns:
        logging.Logger: 日志记录器
    """
    manager = AsyncLogManager()
    return manager.setup_async_logger(logger_name, log_file, **kwargs)

def get_async_logger(logger_name: str) -> logging.Logger:
    """
    获取异步日志记录器
    
    Args:
        logger_name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    manager = AsyncLogManager()
    return manager.get_logger(logger_name)

def shutdown_async_logging():
    """关闭异步日志"""
    manager = AsyncLogManager()
    manager.shutdown()

def get_async_log_stats() -> Dict[str, Dict[str, int]]:
    """获取异步日志统计"""
    manager = AsyncLogManager()
    return manager.get_all_stats()


# ==================== 全局实例 ====================

# 全局异步日志管理器
async_log_manager = AsyncLogManager()
