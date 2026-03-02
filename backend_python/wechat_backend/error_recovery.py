"""
错误恢复与自动重试模块

功能：
- 基于错误类型的智能重试策略
- 指数退避算法
- 熔断器集成
- 死信队列
- 事务回滚

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import asyncio
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict, List, Tuple, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from functools import wraps
import logging

from wechat_backend.error_codes import ErrorCodeDefinition, ErrorSeverity, get_error_code
from wechat_backend.error_logger import get_error_logger, ErrorLogger


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = 'fixed'                       # 固定间隔
    LINEAR = 'linear'                     # 线性退避
    EXPONENTIAL = 'exponential'           # 指数退避
    EXPONENTIAL_WITH_JITTER = 'exponential_with_jitter'  # 指数退避 + 抖动


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3                          # 最大重试次数
    base_delay: float = 1.0                        # 基础延迟（秒）
    max_delay: float = 60.0                        # 最大延迟（秒）
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_WITH_JITTER
    jitter: bool = True                            # 是否添加随机抖动
    retryable_error_codes: List[str] = field(default_factory=list)  # 可重试的错误码
    non_retryable_error_codes: List[str] = field(default_factory=list)  # 不可重试的错误码

    def is_retryable(self, error_code: str) -> bool:
        """判断错误码是否可重试"""
        # 明确指定不可重试的错误码优先
        if error_code in self.non_retryable_error_codes:
            return False
        # 如果指定了可重试的错误码列表，只重试这些
        if self.retryable_error_codes:
            return error_code in self.retryable_error_codes
        # 默认所有错误都可重试（除非明确指定不可重试）
        return True


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt_number: int
    timestamp: datetime
    delay: float
    error: Exception
    error_code: str
    success: bool = False


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_time: float = 0.0
    trace_id: Optional[str] = None


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        初始化重试处理器
        
        Args:
            config: 重试配置
        """
        self.config = config or RetryConfig()
        self.logger = get_error_logger()
        self._attempt_history: Dict[str, List[RetryAttempt]] = defaultdict(list)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟

        Args:
            attempt: 当前尝试次数

        Returns:
            float: 延迟时间（秒）
        """
        strategy = self.config.strategy

        if strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt - 1))
        elif strategy == RetryStrategy.EXPONENTIAL_WITH_JITTER:
            # 指数退避 + 随机抖动（避免雷群效应）
            base = self.config.base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0.5, 1.5) if self.config.jitter else 1.0
            delay = base * jitter
        else:
            delay = self.config.base_delay

        # 限制最大延迟
        return min(delay, self.config.max_delay)
    
    def _get_error_code_from_exception(self, exc: Exception) -> str:
        """从异常中提取错误码"""
        # 如果异常有 code 属性
        if hasattr(exc, 'code'):
            return exc.code
        # 如果异常有 error_code 属性
        if hasattr(exc, 'error_code'):
            return exc.error_code
        # 从异常类型和消息中尝试解析
        error_type = type(exc).__name__.upper()
        error_msg = str(exc).upper()
        
        # 根据异常类型判断
        if 'TIMEOUT' in error_type or 'TIMEOUT' in error_msg:
            return 'TIMEOUT_ERROR'
        if 'CONNECTION' in error_type or 'CONNECTION' in error_msg:
            return 'CONNECTION_ERROR'
        if 'VALIDATION' in error_type or 'VALIDATION' in error_msg:
            return 'VALIDATION_ERROR'
        if 'VALUE' in error_type:
            return 'VALUE_ERROR'
        
        # 从异常消息中尝试解析诊断相关错误码
        if 'DIAGNOSIS_' in error_msg:
            for code in ['DIAGNOSIS_TIMEOUT', 'DIAGNOSIS_INIT_FAILED',
                        'DIAGNOSIS_EXECUTION_FAILED', 'DIAGNOSIS_SAVE_FAILED']:
                if code in error_msg:
                    return code
        
        # 默认返回未知错误
        return 'UNKNOWN_ERROR'

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        判断是否应该重试

        Args:
            attempt: 当前尝试次数 (从 1 开始)
            error: 异常对象

        Returns:
            bool: 是否重试
        """
        # 检查是否超过最大尝试次数
        # attempt 从 1 开始，所以 attempt > max_attempts 时停止
        if attempt > self.config.max_attempts:
            return False
        
        # 获取错误码
        error_code = self._get_error_code_from_exception(error)

        # 检查是否可重试
        return self.config.is_retryable(error_code)
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        execution_id: Optional[str] = None,
        **kwargs
    ) -> RetryResult:
        """
        执行带重试的函数（同步版本）

        Args:
            func: 要执行的函数
            *args: 函数参数
            execution_id: 执行 ID（用于追踪）
            **kwargs: 函数关键字参数

        Returns:
            RetryResult: 重试结果
        """
        trace_id = f"retry_{uuid.uuid4().hex[:12]}"
        attempts = []
        start_time = time.time()
        
        # 处理 max_attempts=0 的情况
        if self.config.max_attempts <= 0:
            try:
                result = func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=[],
                    total_time=time.time() - start_time,
                    trace_id=trace_id
                )
            except Exception as e:
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=[],
                    total_time=time.time() - start_time,
                    trace_id=trace_id
                )

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)

                # 成功，记录尝试
                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0 if attempt == 1 else self.calculate_delay(attempt - 1),
                    error=None,  # type: ignore
                    error_code='',
                    success=True
                )
                attempts.append(attempt_record)

                total_time = time.time() - start_time

                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_time=total_time,
                    trace_id=trace_id
                )
                
            except Exception as e:
                error_code = self._get_error_code_from_exception(e)

                # 记录失败尝试
                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0 if attempt == 1 else self.calculate_delay(attempt - 1),
                    error=e,
                    error_code=error_code,
                    success=False
                )
                attempts.append(attempt_record)

                # 保存到历史记录
                if execution_id:
                    self._attempt_history[execution_id].append(attempt_record)

                # 判断是否重试
                # attempt 从 1 开始，当 attempt < max_attempts 时，还可以再试一次
                if attempt < self.config.max_attempts and self.should_retry(attempt, e):
                    delay = self.calculate_delay(attempt)

                    self.logger.log_warning(
                        f"第 {attempt} 次尝试失败：{error_code} - {str(e)}, "
                        f"{delay:.2f}秒后重试...",
                        additional_info={
                            'function': func.__name__,
                            'execution_id': execution_id,
                            'attempt': attempt,
                            'max_attempts': self.config.max_attempts,
                        }
                    )

                    time.sleep(delay)
                else:
                    # 不再重试，记录最终失败
                    total_time = time.time() - start_time

                    self.logger.log_error(
                        error=e,
                        error_code=get_error_code(error_code),
                        execution_id=execution_id,
                        additional_info={
                            'function': func.__name__,
                            'total_attempts': attempt,
                            'total_time': total_time,
                            'trace_id': trace_id,
                        }
                    )

                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_time=total_time,
                        trace_id=trace_id
                    )

        # 理论上不会到这里
        return RetryResult(
            success=False,
            error=Exception("Unexpected retry loop exit"),
            attempts=attempts,
            total_time=time.time() - start_time,
            trace_id=trace_id
        )
    
    async def execute_with_retry_async(
        self,
        func: Callable,
        *args,
        execution_id: Optional[str] = None,
        **kwargs
    ) -> RetryResult:
        """
        执行带重试的函数（异步版本）

        Args:
            func: 要执行的函数（可以是 async 函数）
            *args: 函数参数
            execution_id: 执行 ID
            **kwargs: 函数关键字参数

        Returns:
            RetryResult: 重试结果
        """
        trace_id = f"retry_{uuid.uuid4().hex[:12]}"
        attempts = []
        start_time = time.time()
        
        # 处理 max_attempts=0 的情况
        if self.config.max_attempts <= 0:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=[],
                    total_time=time.time() - start_time,
                    trace_id=trace_id
                )
            except Exception as e:
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=[],
                    total_time=time.time() - start_time,
                    trace_id=trace_id
                )

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                # 判断是否是协程函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # 成功
                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0 if attempt == 1 else self.calculate_delay(attempt - 1),
                    error=None,  # type: ignore
                    error_code='',
                    success=True
                )
                attempts.append(attempt_record)

                total_time = time.time() - start_time

                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_time=total_time,
                    trace_id=trace_id
                )

            except Exception as e:
                error_code = self._get_error_code_from_exception(e)

                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0 if attempt == 1 else self.calculate_delay(attempt - 1),
                    error=e,
                    error_code=error_code,
                    success=False
                )
                attempts.append(attempt_record)

                if execution_id:
                    self._attempt_history[execution_id].append(attempt_record)

                # 判断是否重试
                # attempt 从 1 开始，当 attempt < max_attempts 时，还可以再试一次
                if attempt < self.config.max_attempts and self.should_retry(attempt, e):
                    delay = self.calculate_delay(attempt)

                    self.logger.log_warning(
                        f"第 {attempt} 次尝试失败：{error_code} - {str(e)}, "
                        f"{delay:.2f}秒后重试...",
                        additional_info={
                            'function': func.__name__,
                            'execution_id': execution_id,
                            'attempt': attempt,
                        }
                    )

                    await asyncio.sleep(delay)
                else:
                    total_time = time.time() - start_time

                    self.logger.log_error(
                        error=e,
                        error_code=get_error_code(error_code),
                        execution_id=execution_id,
                        additional_info={
                            'function': func.__name__,
                            'total_attempts': attempt,
                            'trace_id': trace_id,
                        }
                    )

                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_time=total_time,
                        trace_id=trace_id
                    )

        return RetryResult(
            success=False,
            error=Exception("Unexpected retry loop exit"),
            attempts=attempts,
            total_time=time.time() - start_time,
            trace_id=trace_id
        )
    
    def get_attempt_history(self, execution_id: str) -> List[RetryAttempt]:
        """获取指定 execution_id 的重试历史"""
        return self._attempt_history.get(execution_id, [])
    
    def clear_history(self, execution_id: Optional[str] = None):
        """清除重试历史"""
        if execution_id:
            self._attempt_history.pop(execution_id, None)
        else:
            self._attempt_history.clear()


# ==================== 智能重试配置预设 ====================

class PresetRetryConfigs:
    """预设重试配置"""
    
    # AI 调用重试配置（容忍度高，多次重试）
    AI_CALL_RETRY = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_WITH_JITTER,
        retryable_error_codes=[
            'AI_PLATFORM_UNAVAILABLE',
            'AI_PLATFORM_TIMEOUT',
            'AI_PLATFORM_RATE_LIMIT',
            'AI_RESPONSE_INVALID',
            'AI_RESPONSE_EMPTY',
        ],
        non_retryable_error_codes=[
            'AI_API_KEY_MISSING',
            'AI_MODEL_NOT_FOUND',
            'AI_PLATFORM_QUOTA_EXHAUSTED',
        ]
    )
    
    # 数据库操作重试配置（中等容忍度）
    DATABASE_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_WITH_JITTER,
        retryable_error_codes=[
            'DB_CONNECTION_FAILED',
            'DB_CONNECTION_TIMEOUT',
            'DB_QUERY_FAILED',
            'DB_INSERT_FAILED',
            'DB_TRANSACTION_FAILED',
        ],
        non_retryable_error_codes=[
            'DB_DATA_INTEGRITY_ERROR',
            'DB_CONSTRAINT_VIOLATION',
            'DB_ROLLBACK_FAILED',
        ]
    )
    
    # 诊断执行重试配置（高容忍度）
    DIAGNOSIS_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=3.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_WITH_JITTER,
        retryable_error_codes=[
            'DIAGNOSIS_INIT_FAILED',
            'DIAGNOSIS_EXECUTION_FAILED',
            'DIAGNOSIS_TIMEOUT',
            'DIAGNOSIS_RESULT_COUNT_MISMATCH',
            'DIAGNOSIS_SAVE_FAILED',
        ],
        non_retryable_error_codes=[
            'DIAGNOSIS_STATE_ERROR',
            'DIAGNOSIS_ROLLBACK_FAILED',
        ]
    )
    
    # 后台分析重试配置
    ANALYSIS_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_WITH_JITTER,
        retryable_error_codes=[
            'ANALYTICS_PROCESSING_FAILED',
            'ANALYTICS_DATA_INCOMPLETE',
        ],
        non_retryable_error_codes=[
            'ANALYTICS_DATA_INVALID',
            'ANALYTICS_CONFIG_INVALID',
        ]
    )
    
    # 通用重试配置（默认）
    DEFAULT_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_WITH_JITTER,
    )


# ==================== 装饰器 ====================

def with_retry(config: Optional[RetryConfig] = None):
    """
    重试装饰器
    
    Args:
        config: 重试配置，默认使用 DEFAULT_RETRY
        
    Returns:
        装饰器函数
    """
    retry_config = config or PresetRetryConfigs.DEFAULT_RETRY
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                handler = RetryHandler(retry_config)
                execution_id = kwargs.get('execution_id') or args[0] if args else None
                result = await handler.execute_with_retry_async(
                    func, *args, execution_id=execution_id, **kwargs
                )
                if not result.success:
                    raise result.error  # type: ignore
                return result.result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                handler = RetryHandler(retry_config)
                execution_id = kwargs.get('execution_id') or args[0] if args else None
                result = handler.execute_with_retry(
                    func, *args, execution_id=execution_id, **kwargs
                )
                if not result.success:
                    raise result.error  # type: ignore
                return result.result
            return sync_wrapper
    return decorator


def ai_call_retry(func: Callable) -> Callable:
    """AI 调用重试装饰器（使用预设的 AI 重试配置）"""
    return with_retry(PresetRetryConfigs.AI_CALL_RETRY)(func)


def database_retry(func: Callable) -> Callable:
    """数据库操作重试装饰器"""
    return with_retry(PresetRetryConfigs.DATABASE_RETRY)(func)


def diagnosis_retry(func: Callable) -> Callable:
    """诊断执行重试装饰器"""
    return with_retry(PresetRetryConfigs.DIAGNOSIS_RETRY)(func)


def analysis_retry(func: Callable) -> Callable:
    """后台分析重试装饰器"""
    return with_retry(PresetRetryConfigs.ANALYSIS_RETRY)(func)
