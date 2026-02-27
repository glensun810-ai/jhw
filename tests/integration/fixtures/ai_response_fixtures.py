"""
AI 响应模拟数据夹具

提供：
1. 成功响应模拟
2. 失败响应模拟
3. 延迟响应模拟
4. 部分成功响应模拟

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import random
from typing import Dict, Any, List, Optional
from datetime import datetime


class MockAIAdapter:
    """模拟 AI 适配器，用于测试"""

    def __init__(
        self,
        should_fail: bool = False,
        fail_rate: float = 0,
        latency_range: tuple = (100, 500),
        fail_until_attempt: int = 0,
        custom_response: Optional[Dict[str, Any]] = None
    ):
        self.should_fail = should_fail
        self.fail_rate = fail_rate
        self.latency_range = latency_range
        self.fail_until_attempt = fail_until_attempt
        self.custom_response = custom_response
        self.call_count = 0
        self.attempts = {}

    async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
        """模拟发送提示词"""
        self.call_count += 1
        key = f"{brand}_{model}"
        self.attempts[key] = self.attempts.get(key, 0) + 1

        # 模拟延迟
        latency = random.randint(*self.latency_range)
        await asyncio.sleep(latency / 1000)

        # 使用自定义响应
        if self.custom_response:
            return self.custom_response

        # 模拟失败（在指定次数前）
        if self.fail_until_attempt > 0 and self.attempts[key] <= self.fail_until_attempt:
            raise Exception(f"模拟 AI 调用失败（第{self.attempts[key]}次尝试）: {model}")

        # 模拟随机失败
        if self.should_fail or random.random() < self.fail_rate:
            raise Exception(f"模拟 AI 调用失败：{model}")

        # 模拟成功响应
        return {
            'content': f"这是关于{brand}的模拟响应，问题：{question}",
            'model': model,
            'latency_ms': latency,
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200},
            'geo_data': {
                'exposure': random.choice([True, False]),
                'sentiment': random.choice(['positive', 'neutral', 'negative']),
                'platform': model
            }
        }

    def get_call_count(self) -> int:
        """获取调用次数"""
        return self.call_count

    def get_attempts(self) -> Dict[str, int]:
        """获取各键的尝试次数"""
        return self.attempts


class SlowAIAdapter:
    """模拟慢速 AI 适配器（用于超时测试）"""

    def __init__(self, delay_seconds: float = 5.0):
        self.delay_seconds = delay_seconds
        self.call_count = 0

    async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
        """模拟慢速响应"""
        self.call_count += 1
        await asyncio.sleep(self.delay_seconds)
        return {
            'content': f'慢速响应：{brand}',
            'model': model,
            'latency_ms': int(self.delay_seconds * 1000)
        }


class FlakyAIAdapter:
    """模拟不稳定的 AI 适配器（随机失败）"""

    def __init__(self, fail_rate: float = 0.3):
        self.fail_rate = fail_rate
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
        """模拟不稳定响应"""
        self.call_count += 1

        if random.random() < self.fail_rate:
            self.failure_count += 1
            raise Exception(f"随机失败：{model}")

        self.success_count += 1
        return {
            'content': f'成功响应：{brand}',
            'model': model,
            'latency_ms': random.randint(100, 300)
        }

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count


@pytest.fixture
def mock_ai_adapter() -> MockAIAdapter:
    """提供模拟 AI 适配器（总是成功）"""
    return MockAIAdapter()


@pytest.fixture
def failing_ai_adapter() -> MockAIAdapter:
    """提供总是失败的模拟 AI 适配器"""
    return MockAIAdapter(should_fail=True)


@pytest.fixture
def flaky_ai_adapter() -> MockAIAdapter:
    """提供偶尔失败的模拟 AI 适配器（30% 失败率）"""
    return MockAIAdapter(fail_rate=0.3)


@pytest.fixture
def retry_ai_adapter() -> MockAIAdapter:
    """提供前几次失败、后几次成功的模拟器"""
    return MockAIAdapter(fail_until_attempt=2)


@pytest.fixture
def slow_ai_adapter() -> SlowAIAdapter:
    """提供慢速 AI 适配器（5 秒延迟）"""
    return SlowAIAdapter(delay_seconds=5.0)


@pytest.fixture
def very_slow_ai_adapter() -> SlowAIAdapter:
    """提供极慢 AI 适配器（10 秒延迟）"""
    return SlowAIAdapter(delay_seconds=10.0)


@pytest.fixture
def flaky_50_ai_adapter() -> FlakyAIAdapter:
    """提供 50% 失败率的 AI 适配器"""
    return FlakyAIAdapter(fail_rate=0.5)


@pytest.fixture
def custom_response_ai_adapter() -> MockAIAdapter:
    """提供自定义响应的 AI 适配器"""
    custom_response = {
        'content': '这是自定义响应内容',
        'model': 'custom',
        'latency_ms': 100,
        'usage': {'prompt_tokens': 50, 'completion_tokens': 100},
        'geo_data': {
            'exposure': True,
            'sentiment': 'positive',
            'platform': 'custom'
        }
    }
    return MockAIAdapter(custom_response=custom_response)


@pytest.fixture
def deterministic_ai_adapter():
    """提供确定性响应的 AI 适配器（用于需要可重复性的测试）"""
    class DeterministicAdapter:
        def __init__(self):
            self.call_count = 0
            self.responses = {}

        async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
            self.call_count += 1
            key = f"{brand}_{model}_{question}"

            if key not in self.responses:
                self.responses[key] = {
                    'content': f'确定性响应：{brand}_{model}',
                    'model': model,
                    'latency_ms': 100,
                    'geo_data': {
                        'exposure': True,
                        'sentiment': 'positive',
                        'platform': model
                    }
                }

            return self.responses[key]

    return DeterministicAdapter()


@pytest.fixture
def brand_specific_ai_adapter():
    """提供品牌特定响应的 AI 适配器"""
    class BrandSpecificAdapter:
        def __init__(self):
            self.call_count = 0

        async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
            self.call_count += 1

            # 根据品牌返回不同响应
            if '失败' in brand:
                raise Exception(f"品牌 {brand} 不可用")

            sentiment_map = {
                '品牌 A': 'positive',
                '品牌 B': 'neutral',
                '品牌 C': 'negative',
            }

            sentiment = sentiment_map.get(brand, 'neutral')

            return {
                'content': f'品牌 {brand} 的分析结果',
                'model': model,
                'latency_ms': 150,
                'geo_data': {
                    'exposure': True,
                    'sentiment': sentiment,
                    'platform': model
                }
            }

    return BrandSpecificAdapter()
