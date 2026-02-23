#!/usr/bin/env python3
"""
P0 修复：AI 调用重试机制

功能：
1. 自动重试失败的 AI 调用
2. 指数退避延迟
3. 记录重试日志
4. 支持自定义重试策略

使用方法：
    from wechat_backend.ai_adapters.retry_decorator import retry_ai_call
    
    @retry_ai_call(max_retries=3, delay=1.0)
    def generate_response(self, prompt, **kwargs):
        # AI 调用逻辑
"""

import time
import random
from functools import wraps
from typing import Callable, Any, Optional
from wechat_backend.logging_config import api_logger


def retry_ai_call(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    AI 调用重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
        max_delay: 最大延迟（秒）
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型
    
    Returns:
        装饰器函数
    
    Example:
        @retry_ai_call(max_retries=3, delay=1.0)
        def call_ai_api(prompt):
            # AI 调用逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    # 记录重试信息
                    if attempt > 0:
                        api_logger.info(
                            f"[AI Retry] 重试 {func.__name__} (attempt {attempt+1}/{max_retries})"
                        )
                    
                    # 调用原函数
                    result = func(*args, **kwargs)
                    
                    # 成功，记录日志
                    if attempt > 0:
                        api_logger.info(
                            f"[AI Retry] {func.__name__} 重试成功"
                        )
                    
                    return result
                
                except exceptions as e:
                    last_exception = e
                    
                    # 记录失败信息
                    api_logger.warning(
                        f"[AI Retry] {func.__name__} 失败 (attempt {attempt+1}/{max_retries}): {str(e)}"
                    )
                    
                    # 如果是最后一次尝试，抛出异常
                    if attempt == max_retries - 1:
                        api_logger.error(
                            f"[AI Retry] {func.__name__} 重试失败，已达到最大重试次数"
                        )
                        break
                    
                    # 计算延迟时间
                    sleep_time = current_delay
                    if jitter:
                        # 添加 ±20% 的随机抖动
                        jitter_factor = random.uniform(0.8, 1.2)
                        sleep_time *= jitter_factor
                    
                    # 记录等待信息
                    api_logger.info(
                        f"[AI Retry] 等待 {sleep_time:.2f}秒后重试..."
                    )
                    
                    # 等待
                    time.sleep(sleep_time)
                    
                    # 增加延迟（指数退避）
                    current_delay = min(current_delay * backoff, max_delay)
            
            # 所有重试都失败，抛出最后的异常
            raise last_exception
        
        return wrapper
    return decorator


class AIRetryConfig:
    """AI 重试配置"""
    
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 10.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.jitter = jitter
    
    def get_retry_decorator(self, exceptions: tuple = (Exception,)) -> Callable:
        """获取重试装饰器"""
        return retry_ai_call(
            max_retries=self.max_retries,
            delay=self.delay,
            backoff=self.backoff,
            max_delay=self.max_delay,
            jitter=self.jitter,
            exceptions=exceptions
        )


# 默认重试配置
DEFAULT_RETRY_CONFIG = AIRetryConfig(
    max_retries=3,
    delay=1.0,
    backoff=2.0,
    max_delay=10.0,
    jitter=True
)


def retry_with_default_config(func: Callable) -> Callable:
    """使用默认配置的重试装饰器"""
    return DEFAULT_RETRY_CONFIG.get_retry_decorator()(func)


if __name__ == '__main__':
    # 测试重试机制
    import random
    
    @retry_ai_call(max_retries=3, delay=0.5)
    def test_function():
        if random.random() < 0.7:  # 70% 概率失败
            raise Exception("随机失败")
        return "成功"
    
    print("测试 AI 重试机制...")
    for i in range(5):
        try:
            result = test_function()
            print(f"测试 {i+1}: {result}")
        except Exception as e:
            print(f"测试 {i+1}: 失败 - {e}")
    
    print("\n测试完成")
