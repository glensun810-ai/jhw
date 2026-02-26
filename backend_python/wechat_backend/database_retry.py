"""
数据库重试机制 - P0 关键修复

核心功能：
1. 自动重试数据库操作
2. 指数退避策略
3. 关键失败告警
4. 重试日志记录

作者：首席测试专家
日期：2026-02-27
"""

import time
import functools
from typing import Callable, Any, Optional
from wechat_backend.logging_config import api_logger, db_logger


class DatabaseRetryError(Exception):
    """数据库重试失败异常"""
    def __init__(self, message: str, attempts: int, last_error: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def retry_database_operation(
    max_retries: int = 3,
    base_delay: float = 0.1,  # 100ms
    max_delay: float = 2.0,   # 2s
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    数据库操作重试装饰器
    
    参数:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数退避底数
        exceptions: 需要重试的异常类型
    
    使用示例:
        @retry_database_operation(max_retries=3)
        def update_status(...):
            # 数据库操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # 成功时记录日志（仅当重试过后成功）
                    if attempt > 0:
                        api_logger.info(
                            f"[数据库重试] ✅ {func.__name__} 在第 {attempt + 1} 次尝试成功"
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # 判断是否应该重试
                    should_retry = (
                        attempt < max_retries and
                        _is_retryable_error(e)
                    )
                    
                    if should_retry:
                        # 计算延迟时间（指数退避 + 抖动）
                        import random
                        delay = min(
                            base_delay * (exponential_base ** attempt) + random.uniform(0, 0.1),
                            max_delay
                        )
                        
                        api_logger.warning(
                            f"[数据库重试] ⚠️ {func.__name__} 失败，"
                            f"{delay:.2f}s 后重试 ({attempt + 1}/{max_retries + 1}), "
                            f"错误：{e}"
                        )
                        
                        time.sleep(delay)
                    else:
                        # 不重试或已达到最大重试次数
                        break
            
            # 所有重试都失败
            error_msg = (
                f"[数据库重试] ❌ {func.__name__} 失败，"
                f"已尝试 {attempt + 1} 次，最终错误：{last_exception}"
            )
            api_logger.error(error_msg)
            
            # 关键失败告警
            _alert_critical_failure(func.__name__, str(last_exception), attempt + 1)
            
            raise DatabaseRetryError(
                error_msg,
                attempts=attempt + 1,
                last_error=last_exception
            )
        
        return wrapper
    return decorator


def _is_retryable_error(error: Exception) -> bool:
    """
    判断错误是否可重试
    
    可重试的错误：
    - 数据库锁定 (SQLITE_BUSY, SQLITE_LOCKED)
    - 连接超时
    - 临时网络错误
    
    不可重试的错误：
    - 数据验证错误
    - 约束违反
    - SQL 语法错误
    """
    error_str = str(error).lower()
    
    # 可重试的错误模式
    retryable_patterns = [
        'database is locked',
        'locked',
        'timeout',
        'timed out',
        'connection reset',
        'connection refused',
        'network',
        'busy',
        'temporary',
    ]
    
    for pattern in retryable_patterns:
        if pattern in error_str:
            return True
    
    return False


def _alert_critical_failure(function_name: str, error_message: str, attempts: int):
    """
    关键失败告警
    
    集成告警服务：
    - 钉钉告警
    - 企业微信告警
    - 邮件告警（待实现）
    """
    from wechat_backend.alerting import alert_critical_failure
    
    # 使用统一的告警服务
    alert_critical_failure(
        component=f"database.{function_name}",
        error_message=error_message,
        attempts=attempts
    )


class DatabaseOperationWithRetry:
    """
    数据库操作重试类（面向对象方式）
    
    使用示例:
        retry = DatabaseOperationWithRetry(max_retries=3)
        result = retry.execute(lambda: repo.update_status(...))
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, operation: Callable[[], Any], operation_name: str = "Database Operation") -> Any:
        """
        执行数据库操作（带重试）
        
        参数:
            operation: 要执行的数据库操作（无参数函数）
            operation_name: 操作名称（用于日志）
        
        返回:
            操作结果
        
        异常:
            DatabaseRetryError: 所有重试都失败
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = operation()
                
                if attempt > 0:
                    api_logger.info(
                        f"[数据库重试] ✅ {operation_name} 在第 {attempt + 1} 次尝试成功"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries and _is_retryable_error(e):
                    import random
                    delay = min(
                        self.base_delay * (2 ** attempt) + random.uniform(0, 0.1),
                        self.max_delay
                    )
                    
                    api_logger.warning(
                        f"[数据库重试] ⚠️ {operation_name} 失败，"
                        f"{delay:.2f}s 后重试 ({attempt + 1}/{self.max_retries + 1}), "
                        f"错误：{e}"
                    )
                    
                    time.sleep(delay)
                else:
                    break
        
        # 所有重试都失败
        error_msg = (
            f"[数据库重试] ❌ {operation_name} 失败，"
            f"已尝试 {attempt + 1} 次，最终错误：{last_exception}"
        )
        api_logger.error(error_msg)
        _alert_critical_failure(operation_name, str(last_exception), attempt + 1)
        
        raise DatabaseRetryError(error_msg, attempts=attempt + 1, last_error=last_exception)


# 全局重试器实例
_default_retry = DatabaseOperationWithRetry(max_retries=3, base_delay=0.1, max_delay=2.0)


def get_database_retryer() -> DatabaseOperationWithRetry:
    """获取全局数据库重试器"""
    return _default_retry
