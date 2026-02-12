"""
智能重试机制模块
提供基于错误类型和指数退避的重试策略
"""

import time
import random
from typing import Callable, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略类型"""
    FIXED_INTERVAL = "fixed_interval"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


class RetryHandler:
    """重试处理器"""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                 jitter: bool = True,
                 retryable_exceptions: tuple = (Exception,)):
        """
        初始化重试处理器
        :param max_attempts: 最大尝试次数
        :param base_delay: 基础延迟时间
        :param max_delay: 最大延迟时间
        :param strategy: 重试策略
        :param jitter: 是否添加抖动以避免雷群效应
        :param retryable_exceptions: 可重试的异常类型
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        if self.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.base_delay
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 添加抖动
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_attempts:
            return False
        
        # 检查异常类型是否在可重试列表中
        return isinstance(exception, self.retryable_exceptions)
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        执行带重试的函数
        :return: (是否成功, 返回值, 异常对象)
        """
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                return True, result, None
            
            except self.retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.max_attempts and self.should_retry(attempt, e):
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"第 {attempt} 次尝试失败: {type(e).__name__}: {str(e)}, "
                                 f"{delay:.2f}秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"所有 {self.max_attempts} 次尝试均失败: {type(e).__name__}: {str(e)}")
                    break
        
        return False, None, last_exception


class SmartRetryHandler(RetryHandler):
    """智能重试处理器，根据错误类型调整重试策略"""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                 jitter: bool = True):
        super().__init__(max_attempts, base_delay, max_delay, strategy, jitter, (Exception,))
        
        # 不同错误类型的特殊处理
        self.error_configs = {
            'rate_limit': {'max_attempts': 5, 'base_delay': 2.0, 'strategy': RetryStrategy.EXPONENTIAL_BACKOFF},
            'timeout': {'max_attempts': 3, 'base_delay': 1.0, 'strategy': RetryStrategy.LINEAR_BACKOFF},
            'server_error': {'max_attempts': 4, 'base_delay': 1.5, 'strategy': RetryStrategy.EXPONENTIAL_BACKOFF},
            'connection_error': {'max_attempts': 3, 'base_delay': 1.0, 'strategy': RetryStrategy.FIXED_INTERVAL},
        }
    
    def execute_with_smart_retry(self, func: Callable, error_type: Optional[str] = None, *args, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        执行带智能重试的函数
        :param func: 要执行的函数
        :param error_type: 错误类型，用于选择特定的重试配置
        :return: (是否成功, 返回值, 异常对象)
        """
        # 根据错误类型调整配置
        original_config = None
        if error_type and error_type in self.error_configs:
            original_config = {
                'max_attempts': self.max_attempts,
                'base_delay': self.base_delay,
                'strategy': self.strategy
            }
            
            config = self.error_configs[error_type]
            self.max_attempts = config.get('max_attempts', self.max_attempts)
            self.base_delay = config.get('base_delay', self.base_delay)
            self.strategy = config.get('strategy', self.strategy)
        
        try:
            return self.execute_with_retry(func, *args, **kwargs)
        finally:
            # 恢复原始配置
            if original_config:
                self.max_attempts = original_config['max_attempts']
                self.base_delay = original_config['base_delay']
                self.strategy = original_config['strategy']


# 便捷函数
def retry_execution(max_attempts: int = 3, base_delay: float = 1.0, **kwargs):
    """装饰器：为函数添加重试功能"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **func_kwargs):
            handler = RetryHandler(max_attempts=max_attempts, base_delay=base_delay, **kwargs)
            success, result, exception = handler.execute_with_retry(func, *args, **func_kwargs)
            if not success:
                raise exception
            return result
        return wrapper
    return decorator
