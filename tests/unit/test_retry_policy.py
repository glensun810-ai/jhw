"""
重试策略单元测试

测试覆盖率目标：> 90%

测试范围:
1. 成功场景：第一次调用成功
2. 重试成功场景：前 n-1 次失败，第 n 次成功
3. 重试耗尽场景：所有重试都失败
4. 不可重试异常场景
5. 延迟计算测试
6. 抖动测试
7. 并发测试
8. 重试上下文记录测试

作者：系统架构组
日期：2026-02-27
"""

import pytest
import asyncio
import random
import time
from unittest.mock import Mock, patch
from typing import List

from wechat_backend.v2.services.retry_policy import RetryPolicy, RetryContext
from wechat_backend.v2.exceptions import (
    AIPlatformError,
    DiagnosisValidationError,
)


# ==================== Fixture ====================

@pytest.fixture
def retry_policy():
    """创建默认重试策略"""
    return RetryPolicy(
        max_retries=3,
        base_delay=0.1,  # 测试使用短延迟
        max_delay=1.0,
        jitter=False,  # 默认关闭抖动以便测试
    )


# ==================== RetryContext 测试 ====================

class TestRetryContext:
    """重试上下文测试"""
    
    def test_init(self):
        """测试初始化"""
        context = RetryContext(func_name='test_func', max_retries=3)
        
        assert context.func_name == 'test_func'
        assert context.max_retries == 3
        assert context.attempts == []
    
    def test_add_attempt(self):
        """测试添加尝试记录"""
        context = RetryContext(func_name='test_func', max_retries=3)
        
        # 添加失败尝试
        context.add_attempt(
            attempt=1,
            delay=1.5,
            error=TimeoutError("Timeout"),
        )
        
        assert len(context.attempts) == 1
        assert context.attempts[0]['attempt'] == 1
        assert context.attempts[0]['delay'] == 1.5
        assert context.attempts[0]['error'] == "Timeout"
        assert context.attempts[0]['error_type'] == "TimeoutError"
        assert 'timestamp' in context.attempts[0]
        
        # 添加成功尝试
        context.add_attempt(
            attempt=2,
            delay=0,
            error=None,
        )
        
        assert len(context.attempts) == 2
        assert context.attempts[1]['error'] is None
    
    def test_to_log_dict(self):
        """测试转换为日志字典"""
        context = RetryContext(func_name='test_func', max_retries=3)
        
        # 空上下文
        log_dict = context.to_log_dict()
        assert log_dict['func_name'] == 'test_func'
        assert log_dict['max_retries'] == 3
        assert log_dict['total_attempts'] == 0
        assert log_dict['successful'] is False
        
        # 添加尝试
        context.add_attempt(1, 1.0, error=TimeoutError("Error"))
        context.add_attempt(2, 0, error=None)
        
        log_dict = context.to_log_dict()
        assert log_dict['total_attempts'] == 2
        assert log_dict['successful'] is True
        assert log_dict['total_delay'] == 1.0
        assert len(log_dict['attempts']) == 2
    
    def test_get_last_error(self):
        """测试获取最后一次错误"""
        context = RetryContext(func_name='test_func', max_retries=3)
        
        # 无尝试
        assert context.get_last_error() is None
        
        # 添加失败尝试
        context.add_attempt(1, 1.0, error=TimeoutError("Error"))
        error = context.get_last_error()
        assert error is not None
        assert "TimeoutError" in str(error)


# ==================== 初始化测试 ====================

class TestRetryPolicyInit:
    """重试策略初始化测试"""
    
    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        policy = RetryPolicy()
        
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 30.0
        assert policy._exponential_backoff is True
        assert policy._jitter is True
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        policy = RetryPolicy(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_backoff=False,
            jitter=False,
        )
        
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 60.0
        assert policy._exponential_backoff is False
        assert policy._jitter is False
    
    def test_init_with_invalid_max_retries(self):
        """测试无效的 max_retries"""
        with pytest.raises(ValueError, match="max_retries 必须 >= 0"):
            RetryPolicy(max_retries=-1)
    
    def test_init_with_invalid_base_delay(self):
        """测试无效的 base_delay"""
        with pytest.raises(ValueError, match="base_delay 必须 > 0"):
            RetryPolicy(base_delay=0)
    
    def test_init_with_invalid_max_delay(self):
        """测试无效的 max_delay"""
        with pytest.raises(ValueError, match="max_delay 必须 > 0"):
            RetryPolicy(max_delay=0)
    
    def test_init_with_max_delay_less_than_base(self):
        """测试 max_delay 小于 base_delay"""
        with pytest.raises(ValueError, match="max_delay 必须 >= base_delay"):
            RetryPolicy(base_delay=10.0, max_delay=5.0)


# ==================== 延迟计算测试 ====================

class TestCalculateDelay:
    """延迟计算测试"""
    
    def test_exponential_backoff(self):
        """测试指数退避"""
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0, jitter=False)
        
        assert policy.calculate_delay(0) == 1.0  # 1 * 2^0 = 1
        assert policy.calculate_delay(1) == 2.0  # 1 * 2^1 = 2
        assert policy.calculate_delay(2) == 4.0  # 1 * 2^2 = 4
        assert policy.calculate_delay(3) == 8.0  # 1 * 2^3 = 8
    
    def test_max_delay_cap(self):
        """测试最大延迟限制"""
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=False)
        
        # 超过最大延迟
        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(3) == 8.0
        assert policy.calculate_delay(4) == 10.0  #  capped at max_delay
        assert policy.calculate_delay(5) == 10.0
    
    def test_no_exponential_backoff(self):
        """测试不使用指数退避"""
        policy = RetryPolicy(base_delay=2.0, exponential_backoff=False, jitter=False)
        
        assert policy.calculate_delay(0) == 2.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 2.0
    
    def test_with_jitter(self):
        """测试带随机抖动"""
        policy = RetryPolicy(base_delay=1.0, jitter=True)
        
        # 多次测试，验证抖动范围
        delays = [policy.calculate_delay(1) for _ in range(100)]
        
        # base_delay=1.0, retry_count=1 => 2.0 + 0-10% jitter
        for delay in delays:
            assert 2.0 <= delay <= 2.2
        
        # 验证有抖动（不是所有值都相同）
        unique_delays = set(delays)
        assert len(unique_delays) > 1
    
    def test_jitter_range(self):
        """测试抖动范围在 0-10%"""
        policy = RetryPolicy(base_delay=10.0, jitter=True)
        
        delays = [policy.calculate_delay(0) for _ in range(1000)]
        
        for delay in delays:
            # 10.0 + 0-10% => 10.0-11.0
            assert 10.0 <= delay <= 11.0


# ==================== 重试判断测试 ====================

class TestShouldRetry:
    """重试判断测试"""
    
    def test_retry_count_not_exceeded(self):
        """测试重试次数未超限"""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry(TimeoutError("timeout"), 0) is True
        assert policy.should_retry(TimeoutError("timeout"), 1) is True
        assert policy.should_retry(TimeoutError("timeout"), 2) is True
        assert policy.should_retry(TimeoutError("timeout"), 3) is False  # 达到上限
    
    def test_retryable_exception(self):
        """测试可重试的异常"""
        policy = RetryPolicy(
            retryable_exceptions=[TimeoutError, ConnectionError, AIPlatformError]
        )
        
        assert policy.should_retry(TimeoutError("timeout"), 0) is True
        assert policy.should_retry(ConnectionError("conn error"), 0) is True
        assert policy.should_retry(AIPlatformError("AI error"), 0) is True
    
    def test_non_retryable_exception(self):
        """测试不可重试的异常"""
        policy = RetryPolicy(
            retryable_exceptions=[TimeoutError, ConnectionError]
        )
        
        # ValidationError 不在可重试列表中
        assert policy.should_retry(ValueError("validation"), 0) is False
        assert policy.should_retry(KeyError("key"), 0) is False
    
    def test_custom_retryable_exceptions(self):
        """测试自定义可重试异常"""
        class CustomRetryableError(Exception):
            pass
        
        policy = RetryPolicy(retryable_exceptions=[CustomRetryableError])
        
        assert policy.should_retry(CustomRetryableError("custom"), 0) is True
        assert policy.should_retry(TimeoutError("timeout"), 0) is False


# ==================== 异步执行测试 ====================

class TestExecuteAsync:
    """异步执行测试"""
    
    @pytest.mark.asyncio
    async def test_success_first_attempt(self, retry_policy):
        """测试第一次调用成功"""
        call_count = 0
        
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_policy.execute_async(success_func)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_then_success(self, retry_policy):
        """测试重试后成功"""
        call_count = 0
        
        async def fail_twice_then_success():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TimeoutError("Timeout")
            return "success"
        
        result = await retry_policy.execute_async(fail_twice_then_success)
        
        assert result == "success"
        assert call_count == 3  # 1 次尝试 + 2 次重试
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self, retry_policy):
        """测试重试耗尽"""
        call_count = 0
        
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always fail")
        
        with pytest.raises(TimeoutError):
            await retry_policy.execute_async(always_fail)
        
        assert call_count == 4  # 1 次尝试 + 3 次重试
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """测试不可重试的异常"""
        call_count = 0
        
        async def validation_error():
            nonlocal call_count
            call_count += 1
            raise DiagnosisValidationError("Invalid input")
        
        policy = RetryPolicy(
            max_retries=3,
            retryable_exceptions=[TimeoutError, ConnectionError, AIPlatformError]
        )
        
        with pytest.raises(DiagnosisValidationError):
            await policy.execute_async(validation_error)
        
        assert call_count == 1  # 不重试
    
    @pytest.mark.asyncio
    async def test_retry_context_recording(self, retry_policy):
        """测试重试上下文记录"""
        call_count = 0
        
        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First fail")
            return "success"
        
        result = await retry_policy.execute_async(fail_once)
        
        assert result == "success"
        
        # 验证上下文被记录
        context = retry_policy.get_last_context()
        assert context is not None
        assert context.func_name == "fail_once"
        assert context.max_retries == 3
        assert len(context.attempts) == 2
        assert context.attempts[0]['error'] is not None
        assert context.attempts[1]['error'] is None
    
    @pytest.mark.asyncio
    async def test_retry_with_args(self):
        """测试带参数的重试"""
        retry_policy = RetryPolicy(max_retries=2, base_delay=0.1, jitter=False)
        results = []
        
        async def process(data: str, multiplier: int) -> str:
            if not results:
                results.append('failed')
                raise TimeoutError("First fail")
            return f"{data}:{multiplier}"
        
        result = await retry_policy.execute_async(process, "test", 5)
        
        assert result == "test:5"


# ==================== 同步执行测试 ====================

class TestExecuteSync:
    """同步执行测试"""
    
    def test_success_first_attempt(self, retry_policy):
        """测试第一次调用成功"""
        call_count = 0
        
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = retry_policy.execute_sync(success_func)
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_then_success(self, retry_policy):
        """测试重试后成功"""
        call_count = 0
        
        def fail_twice_then_success():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TimeoutError("Timeout")
            return "success"
        
        result = retry_policy.execute_sync(fail_twice_then_success)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self, retry_policy):
        """测试重试耗尽"""
        call_count = 0
        
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always fail")
        
        with pytest.raises(TimeoutError):
            retry_policy.execute_sync(always_fail)
        
        assert call_count == 4  # 1 次尝试 + 3 次重试


# ==================== 装饰器测试 ====================

class TestDecorator:
    """装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """测试异步装饰器"""
        call_count = 0
        policy = RetryPolicy(max_retries=2, base_delay=0.1, jitter=False)
        
        @policy.as_decorator()
        async def flaky_async_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First fail")
            return "success"
        
        result = await flaky_async_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_sync_decorator(self):
        """测试同步装饰器"""
        call_count = 0
        policy = RetryPolicy(max_retries=2, base_delay=0.1, jitter=False)
        
        @policy.as_decorator()
        def flaky_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First fail")
            return "success"
        
        result = flaky_sync_func()
        
        assert result == "success"
        assert call_count == 2


# ==================== 并发测试 ====================

class TestConcurrency:
    """并发测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """测试并发重试"""
        policy = RetryPolicy(max_retries=2, base_delay=0.1, jitter=True)
        
        async def flaky_func(task_id: int):
            # 模拟随机失败（30% 失败率）
            if random.random() < 0.3:
                raise TimeoutError(f"Random fail: {task_id}")
            return f"success-{task_id}"
        
        # 并发执行 10 个任务
        tasks = [
            policy.execute_async(flaky_func, i)
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有任务都完成（可能有些失败）
        assert len(results) == 10
        
        # 统计成功和失败
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        
        # 由于有重试，大部分应该成功
        assert len(successes) >= 7  # 至少 70% 成功


# ==================== 日志测试 ====================

class TestLogging:
    """日志测试"""
    
    @pytest.mark.asyncio
    async def test_retry_logging(self, caplog):
        """测试重试日志"""
        retry_policy = RetryPolicy(max_retries=2, base_delay=0.01, jitter=False)
        
        call_count = 0
        
        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First fail")
            return "success"
        
        result = await retry_policy.execute_async(fail_once)
        
        assert result == "success"
        
        # 验证日志包含重试信息
        assert "retrying" in caplog.text.lower()


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=wechat_backend.v2.services.retry_policy', '--cov-report=html'])
