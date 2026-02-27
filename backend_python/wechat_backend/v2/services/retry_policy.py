"""
重试策略服务

为 AI 平台 API 调用提供自动重试能力，支持：
1. 可配置的最大重试次数
2. 指数退避策略（重试延迟递增）
3. 可重试的异常类型配置
4. 随机抖动（避免惊群效应）
5. 重试上下文记录（用于日志和监控）

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import asyncio
import random
import time
import logging
from typing import Callable, Awaitable, Type, List, Optional, Dict, Any, TypeVar
from dataclasses import dataclass, field
from functools import wraps

from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import (
    DiagnosisError,
    AIPlatformError,
    DiagnosisValidationError,
)

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar('T')


@dataclass
class RetryContext:
    """
    重试上下文，记录每次重试的详细信息
    
    Attributes:
        func_name: 函数名称
        max_retries: 最大重试次数
        attempts: 尝试记录列表
    """
    
    func_name: str
    max_retries: int
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_attempt(
        self,
        attempt: int,
        delay: float,
        error: Optional[Exception] = None,
    ) -> None:
        """
        添加一次尝试记录
        
        Args:
            attempt: 尝试次数（从 1 开始）
            delay: 本次延迟时间（秒）
            error: 异常信息（如果有）
        """
        self.attempts.append({
            'attempt': attempt,
            'delay': round(delay, 3),
            'error': str(error) if error else None,
            'error_type': type(error).__name__ if error else None,
            'timestamp': time.time(),
        })
    
    def to_log_dict(self) -> Dict[str, Any]:
        """
        转换为日志字典（结构化日志用）
        
        Returns:
            Dict[str, Any]: 日志字典
        """
        if not self.attempts:
            return {
                'func_name': self.func_name,
                'max_retries': self.max_retries,
                'total_attempts': 0,
                'successful': False,
            }
        
        return {
            'func_name': self.func_name,
            'max_retries': self.max_retries,
            'total_attempts': len(self.attempts),
            'successful': self.attempts[-1]['error'] is None,
            'total_delay': sum(a['delay'] for a in self.attempts),
            'attempts': self.attempts,
        }
    
    def get_last_error(self) -> Optional[Exception]:
        """获取最后一次尝试的异常"""
        if not self.attempts:
            return None
        
        last_attempt = self.attempts[-1]
        if last_attempt.get('error_type'):
            # 重建异常对象（仅用于日志，不抛出）
            return Exception(f"{last_attempt['error_type']}: {last_attempt['error']}")
        return None


class RetryPolicy:
    """
    重试策略类
    
    支持同步和异步函数的重试，使用指数退避策略。
    
    使用示例:
        >>> policy = RetryPolicy(
        ...     max_retries=3,
        ...     base_delay=1.0,
        ...     retryable_exceptions=[TimeoutError, ConnectionError]
        ... )
        >>> result = await policy.execute_async(some_async_func, arg1, arg2)
    """
    
    # 默认可重试的异常类型
    DEFAULT_RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
        TimeoutError,
        ConnectionError,
        AIPlatformError,
    ]
    
    # 默认不可重试的异常类型
    NON_RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
        DiagnosisValidationError,
        # AuthenticationError,  # 如有需要可添加
        # NotFoundError,  # 如有需要可添加
    ]
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_backoff: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        jitter: bool = True,
    ):
        """
        初始化重试策略
        
        Args:
            max_retries: 最大重试次数（不包括第一次尝试）
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_backoff: 是否使用指数退避
            retryable_exceptions: 可重试的异常类型列表
            jitter: 是否添加随机抖动（避免多个任务同时重试）
        
        Raises:
            ValueError: 如果参数值不合理
        """
        if max_retries < 0:
            raise ValueError("max_retries 必须 >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay 必须 > 0")
        if max_delay <= 0:
            raise ValueError("max_delay 必须 > 0")
        if max_delay < base_delay:
            raise ValueError("max_delay 必须 >= base_delay")
        
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exponential_backoff = exponential_backoff
        self._retryable_exceptions = retryable_exceptions or self.DEFAULT_RETRYABLE_EXCEPTIONS
        self._jitter = jitter
        
        # 当前重试上下文（用于日志）
        self._current_context: Optional[RetryContext] = None
        
        api_logger.debug(
            "retry_policy_initialized",
            extra={
                'event': 'retry_policy_initialized',
                'max_retries': max_retries,
                'base_delay': base_delay,
                'max_delay': max_delay,
                'exponential_backoff': exponential_backoff,
                'jitter': jitter,
                'retryable_exceptions': [e.__name__ for e in self._retryable_exceptions],
            }
        )
    
    @property
    def max_retries(self) -> int:
        """获取最大重试次数"""
        return self._max_retries
    
    @property
    def base_delay(self) -> float:
        """获取基础延迟"""
        return self._base_delay
    
    @property
    def max_delay(self) -> float:
        """获取最大延迟"""
        return self._max_delay
    
    def get_last_context(self) -> Optional[RetryContext]:
        """获取最后一次重试的上下文"""
        return self._current_context
    
    def calculate_delay(self, retry_count: int) -> float:
        """
        计算第 retry_count 次重试的延迟时间
        
        Args:
            retry_count: 重试次数（从 0 开始）
        
        Returns:
            float: 延迟时间（秒）
        
        Example:
            >>> policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=False)
            >>> policy.calculate_delay(0)
            1.0
            >>> policy.calculate_delay(1)
            2.0
            >>> policy.calculate_delay(2)
            4.0
        """
        if self._exponential_backoff:
            # 指数退避：delay = base_delay * (2 ^ retry_count)
            delay = self._base_delay * (2 ** retry_count)
        else:
            # 固定延迟
            delay = self._base_delay
        
        # 限制最大延迟
        delay = min(delay, self._max_delay)
        
        # 添加随机抖动（0-10%）
        if self._jitter:
            jitter_range = delay * 0.1
            delay = delay + random.uniform(0, jitter_range)
        
        return round(delay, 3)
    
    def should_retry(self, exception: Exception, retry_count: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 异常对象
            retry_count: 当前重试次数（从 0 开始）
        
        Returns:
            bool: True 表示应该重试
        """
        # 检查是否达到最大重试次数
        if retry_count >= self._max_retries:
            return False
        
        # 检查异常类型是否可重试
        for exception_type in self._retryable_exceptions:
            if isinstance(exception, exception_type):
                return True
        
        return False
    
    async def execute_async(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        异步执行带重试的函数
        
        Args:
            func: 异步函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            T: 函数返回值
        
        Raises:
            Exception: 最后一次尝试的异常
        
        Example:
            >>> async def fetch_data(url: str) -> str:
            ...     # 可能失败的异步操作
            ...     pass
            >>> result = await policy.execute_async(fetch_data, "https://example.com")
        """
        func_name = getattr(func, '__name__', str(func))
        
        # 创建重试上下文
        self._current_context = RetryContext(
            func_name=func_name,
            max_retries=self._max_retries,
        )
        
        retry_count = 0
        last_exception: Optional[Exception] = None
        
        while True:
            try:
                # 尝试执行函数
                result = await func(*args, **kwargs)
                
                # 成功，记录日志并返回
                self._current_context.add_attempt(
                    attempt=retry_count + 1,
                    delay=0,
                    error=None,
                )
                
                api_logger.info(
                    "async_execution_succeeded",
                    extra={
                        'event': 'async_execution_succeeded',
                        'func_name': func_name,
                        'attempts': retry_count + 1,
                    }
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 判断是否应该重试
                if not self.should_retry(e, retry_count):
                    # 不可重试的异常，直接抛出
                    self._current_context.add_attempt(
                        attempt=retry_count + 1,
                        delay=0,
                        error=e,
                    )
                    
                    api_logger.warning(
                        "async_execution_non_retryable_error",
                        extra={
                            'event': 'async_execution_non_retryable_error',
                            'func_name': func_name,
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'attempt': retry_count + 1,
                        }
                    )
                    raise
                
                # 计算延迟
                delay = self.calculate_delay(retry_count)
                
                # 记录重试日志
                self._current_context.add_attempt(
                    attempt=retry_count + 1,
                    delay=delay,
                    error=e,
                )
                
                api_logger.warning(
                    "async_execution_retrying",
                    extra={
                        'event': 'async_execution_retrying',
                        'func_name': func_name,
                        'attempt': retry_count + 1,
                        'max_retries': self._max_retries,
                        'delay': delay,
                        'error': str(e),
                        'error_type': type(e).__name__,
                    }
                )
                
                # 等待后重试
                await asyncio.sleep(delay)
                retry_count += 1
    
    def execute_sync(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        同步执行带重试的函数
        
        Args:
            func: 同步函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            T: 函数返回值
        
        Raises:
            Exception: 最后一次尝试的异常
        
        Example:
            >>> def fetch_data(url: str) -> str:
            ...     # 可能失败的同步操作
            ...     pass
            >>> result = policy.execute_sync(fetch_data, "https://example.com")
        """
        func_name = getattr(func, '__name__', str(func))
        
        # 创建重试上下文
        self._current_context = RetryContext(
            func_name=func_name,
            max_retries=self._max_retries,
        )
        
        retry_count = 0
        last_exception: Optional[Exception] = None
        
        while True:
            try:
                # 尝试执行函数
                result = func(*args, **kwargs)
                
                # 成功，记录日志并返回
                self._current_context.add_attempt(
                    attempt=retry_count + 1,
                    delay=0,
                    error=None,
                )
                
                api_logger.info(
                    "sync_execution_succeeded",
                    extra={
                        'event': 'sync_execution_succeeded',
                        'func_name': func_name,
                        'attempts': retry_count + 1,
                    }
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 判断是否应该重试
                if not self.should_retry(e, retry_count):
                    # 不可重试的异常，直接抛出
                    self._current_context.add_attempt(
                        attempt=retry_count + 1,
                        delay=0,
                        error=e,
                    )
                    
                    api_logger.warning(
                        "sync_execution_non_retryable_error",
                        extra={
                            'event': 'sync_execution_non_retryable_error',
                            'func_name': func_name,
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'attempt': retry_count + 1,
                        }
                    )
                    raise
                
                # 计算延迟
                delay = self.calculate_delay(retry_count)
                
                # 记录重试日志
                self._current_context.add_attempt(
                    attempt=retry_count + 1,
                    delay=delay,
                    error=e,
                )
                
                api_logger.warning(
                    "sync_execution_retrying",
                    extra={
                        'event': 'sync_execution_retrying',
                        'func_name': func_name,
                        'attempt': retry_count + 1,
                        'max_retries': self._max_retries,
                        'delay': delay,
                        'error': str(e),
                        'error_type': type(e).__name__,
                    }
                )
                
                # 等待后重试
                time.sleep(delay)
                retry_count += 1
    
    def as_decorator(self) -> Callable:
        """
        返回一个装饰器，用于装饰需要重试的函数
        
        Returns:
            Callable: 装饰器函数
        
        Example:
            >>> policy = RetryPolicy(max_retries=3)
            >>> @policy.as_decorator()
            ... async def fetch_data(url: str) -> str:
            ...     pass
        """
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self.execute_async(func, *args, **kwargs)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self.execute_sync(func, *args, **kwargs)
                return sync_wrapper
        
        return decorator
