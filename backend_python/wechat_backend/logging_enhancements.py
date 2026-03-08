"""
日志采样和优化工具模块

P2-1 优化：日志级别调整和日志采样机制

功能特性:
- 日志采样：减少高频日志的输出量
- 动态日志级别：支持运行时调整日志级别
- 日志聚合：将重复日志聚合输出
- 性能关键日志：标记性能关键路径的日志

使用示例:
    from wechat_backend.logging_enhancements import (
        sampled_logger,
        LogSampler,
        AggregatedLogger
    )
    
    # 使用采样日志器（10% 采样率）
    logger = sampled_logger('wechat_backend.api', sample_rate=0.1)
    logger.info('高频日志消息')
    
    # 使用聚合日志器
    agg_logger = AggregatedLogger('wechat_backend.database', interval=10)
    for i in range(100):
        agg_logger.debug(f'数据库操作 {i}')
    agg_logger.flush()  # 输出聚合日志
"""

import time
import hashlib
import threading
from collections import defaultdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .logging_config import get_logger


class LogSampler:
    """
    日志采样器
    
    按照采样率输出日志，减少日志量
    """
    
    def __init__(self, sample_rate: float = 0.1):
        """
        初始化采样器
        
        Args:
            sample_rate: 采样率 (0.0-1.0)，0.1 表示 10% 的日志会被输出
        """
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("sample_rate 必须在 0.0 到 1.0 之间")
        self.sample_rate = sample_rate
        self._counter = 0
        self._lock = threading.Lock()
    
    def should_log(self) -> bool:
        """判断是否应该输出日志"""
        with self._lock:
            self._counter += 1
            # 固定比例采样
            return (self._counter % int(1 / self.sample_rate)) == 0 if self.sample_rate > 0 else False
    
    def should_log_hash(self, message: str) -> bool:
        """
        基于消息哈希的采样（确保相同消息的采样一致性）
        
        Args:
            message: 日志消息
            
        Returns:
            是否应该输出日志
        """
        hash_value = int(hashlib.md5(message.encode()).hexdigest(), 16)
        return (hash_value % 100) < (self.sample_rate * 100)


class AggregatedLogger:
    """
    聚合日志器
    
    将重复或相似的日志聚合后输出，减少日志量
    """
    
    def __init__(self, name: str, interval: float = 10.0, max_aggregated: int = 100):
        """
        初始化聚合日志器
        
        Args:
            name: 日志器名称
            interval: 聚合时间间隔（秒）
            max_aggregated: 最大聚合数量
        """
        self.name = name
        self.interval = interval
        self.max_aggregated = max_aggregated
        self.logger = get_logger(name)
        
        self._buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._flush_thread = None
        self._stop_event = threading.Event()
    
    def _get_message_key(self, message: str, level: str) -> str:
        """获取消息的聚合键"""
        return f"{level}:{message}"
    
    def _add_to_buffer(self, message: str, level: str, extra: Dict[str, Any] = None):
        """添加消息到缓冲区"""
        key = self._get_message_key(message, level)
        with self._lock:
            self._buffer[key].append({
                'message': message,
                'level': level,
                'extra': extra,
                'timestamp': datetime.now().isoformat()
            })
            
            # 达到最大聚合数量时立即刷新
            if len(self._buffer[key]) >= self.max_aggregated:
                self._flush_key(key)
    
    def _flush_key(self, key: str):
        """刷新指定键的日志"""
        with self._lock:
            entries = self._buffer.pop(key, [])
        
        if not entries:
            return
        
        count = len(entries)
        first_time = entries[0]['timestamp']
        last_time = entries[-1]['timestamp']
        
        # 输出聚合日志
        self.logger.log(
            level=getattr(__import__('logging'), entries[0]['level']),
            msg=f"[聚合] {entries[0]['message']} (出现 {count} 次，时间范围：{first_time} ~ {last_time})"
        )
    
    def _flush_all(self):
        """刷新所有缓冲的日志"""
        with self._lock:
            keys = list(self._buffer.keys())
        
        for key in keys:
            self._flush_key(key)
    
    def flush(self):
        """立即刷新所有缓冲的日志"""
        self._flush_all()
    
    def _auto_flush_loop(self):
        """自动刷新循环"""
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            self._flush_all()
    
    def start_auto_flush(self):
        """启动自动刷新线程"""
        if self._flush_thread is None:
            self._flush_thread = threading.Thread(target=self._auto_flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop_auto_flush(self):
        """停止自动刷新线程"""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=2.0)
            self._flush_thread = None
        self.flush()
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """DEBUG 级别日志"""
        self._add_to_buffer(message, 'DEBUG', extra)
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """INFO 级别日志"""
        self._add_to_buffer(message, 'INFO', extra)
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """WARNING 级别日志"""
        self._add_to_buffer(message, 'WARNING', extra)
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """ERROR 级别日志"""
        # 错误日志不聚合，立即输出
        self.logger.error(message, extra=extra)
    
    def __del__(self):
        """析构时停止自动刷新"""
        self.stop_auto_flush()


class SampledLogger:
    """
    采样日志器包装器
    
    对高频日志进行采样，减少日志量
    """
    
    def __init__(self, name: str, sample_rate: float = 0.1, use_hash: bool = True):
        """
        初始化采样日志器
        
        Args:
            name: 日志器名称
            sample_rate: 采样率 (0.0-1.0)
            use_hash: 是否使用基于消息哈希的采样
        """
        self.logger = get_logger(name)
        self.sampler = LogSampler(sample_rate)
        self.use_hash = use_hash
        self._skipped_count = 0
        self._logged_count = 0
    
    def _should_log(self, message: str) -> bool:
        """判断是否应该输出日志"""
        if self.use_hash:
            return self.sampler.should_log_hash(message)
        else:
            return self.sampler.should_log()
    
    def debug(self, message: str, *args, **kwargs):
        """DEBUG 级别日志（采样）"""
        if self._should_log(message):
            self.logger.debug(message, *args, **kwargs)
            self._logged_count += 1
        else:
            self._skipped_count += 1
    
    def info(self, message: str, *args, **kwargs):
        """INFO 级别日志（采样）"""
        if self._should_log(message):
            self.logger.info(message, *args, **kwargs)
            self._logged_count += 1
        else:
            self._skipped_count += 1
    
    def warning(self, message: str, *args, **kwargs):
        """WARNING 级别日志（不采样）"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """ERROR 级别日志（不采样）"""
        self.logger.error(message, *args, **kwargs)
    
    def get_stats(self) -> Dict[str, int]:
        """获取采样统计"""
        return {
            'logged': self._logged_count,
            'skipped': self._skipped_count,
            'total': self._logged_count + self._skipped_count,
            'rate': self._logged_count / (self._logged_count + self._skipped_count) if (self._logged_count + self._skipped_count) > 0 else 0
        }


# 便捷函数
def sampled_logger(name: str, sample_rate: float = 0.1, use_hash: bool = True) -> SampledLogger:
    """
    创建采样日志器
    
    Args:
        name: 日志器名称
        sample_rate: 采样率 (0.0-1.0)
        use_hash: 是否使用基于消息哈希的采样
        
    Returns:
        SampledLogger 实例
    """
    return SampledLogger(name, sample_rate, use_hash)


def aggregated_logger(name: str, interval: float = 10.0, max_aggregated: int = 100) -> AggregatedLogger:
    """
    创建聚合日志器
    
    Args:
        name: 日志器名称
        interval: 聚合时间间隔（秒）
        max_aggregated: 最大聚合数量
        
    Returns:
        AggregatedLogger 实例
    """
    logger = AggregatedLogger(name, interval, max_aggregated)
    logger.start_auto_flush()
    return logger


# P2-1 新增：日志级别动态管理
class LogLevelManager:
    """
    日志级别管理器
    
    支持运行时动态调整日志级别
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
        self._log_levels: Dict[str, str] = {}
        self._default_level = 'INFO'
        self._initialized = True
    
    def set_level(self, logger_name: str, level: str):
        """
        设置日志器的日志级别
        
        Args:
            logger_name: 日志器名称
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        import logging
        level = level.upper()
        if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"无效的日志级别：{level}")
        
        with self._lock:
            self._log_levels[logger_name] = level
            logger = get_logger(logger_name)
            logger.setLevel(getattr(logging, level))
    
    def get_level(self, logger_name: str) -> str:
        """获取日志器的日志级别"""
        with self._lock:
            return self._log_levels.get(logger_name, self._default_level)
    
    def set_default_level(self, level: str):
        """设置默认日志级别"""
        import logging
        level = level.upper()
        if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"无效的日志级别：{level}")
        self._default_level = level
    
    def list_levels(self) -> Dict[str, str]:
        """列出所有日志器的日志级别"""
        with self._lock:
            return dict(self._log_levels)
    
    def reset_level(self, logger_name: str):
        """重置日志器的日志级别为默认值"""
        with self._lock:
            if logger_name in self._log_levels:
                del self._log_levels[logger_name]


# 便捷函数
def set_log_level(logger_name: str, level: str):
    """设置日志器的日志级别"""
    LogLevelManager().set_level(logger_name, level)


def get_log_level(logger_name: str) -> str:
    """获取日志器的日志级别"""
    return LogLevelManager().get_level(logger_name)


def list_log_levels() -> Dict[str, str]:
    """列出所有日志器的日志级别"""
    return LogLevelManager().list_levels()


# 导出所有符号
__all__ = [
    'LogSampler',
    'AggregatedLogger',
    'SampledLogger',
    'sampled_logger',
    'aggregated_logger',
    'LogLevelManager',
    'set_log_level',
    'get_log_level',
    'list_log_levels',
]
