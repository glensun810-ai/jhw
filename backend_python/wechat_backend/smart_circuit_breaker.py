"""
智能熔断器

功能:
- 细粒度熔断 (模型 + 品牌)
- 半开状态测试
- 自动恢复

配置:
- failure_threshold: 5 次失败才熔断
- recovery_timeout: 30 秒后恢复
- half_open_max_calls: 半开状态允许 1 次测试

作者：后端开发 李工
日期：2026-03-06
"""

from enum import Enum
import time
from typing import Dict, Optional
from wechat_backend.logging_config import api_logger


class CircuitState(Enum):
    """熔断状态"""
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 熔断
    HALF_OPEN = "half_open"  # 半开 (测试)


class SmartCircuitBreaker:
    """智能熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # 状态存储 (key: model:brand)
        self.states: Dict[str, CircuitState] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_failure_times: Dict[str, float] = {}
        self.half_open_calls: Dict[str, int] = {}
    
    def _get_key(self, model: str, brand: str) -> str:
        """生成熔断键 (模型 + 品牌)"""
        return f"{model}:{brand}"
    
    def is_available(self, model: str, brand: str) -> bool:
        """检查是否可用"""
        key = self._get_key(model, brand)
        state = self.states.get(key, CircuitState.CLOSED)
        
        if state == CircuitState.CLOSED:
            return True
        
        if state == CircuitState.OPEN:
            # 检查是否达到恢复时间
            last_failure = self.last_failure_times.get(key, 0)
            if time.time() - last_failure > self.recovery_timeout:
                # 进入半开状态
                self.states[key] = CircuitState.HALF_OPEN
                self.half_open_calls[key] = 0
                api_logger.info(f"[熔断器] {key} 进入半开状态")
                return True
            return False
        
        if state == CircuitState.HALF_OPEN:
            # 半开状态允许有限调用
            calls = self.half_open_calls.get(key, 0)
            if calls < self.half_open_max_calls:
                self.half_open_calls[key] = calls + 1
                return True
            return False
        
        return True
    
    def record_success(self, model: str, brand: str):
        """记录成功"""
        key = self._get_key(model, brand)
        self.failure_counts[key] = 0
        self.states[key] = CircuitState.CLOSED
        api_logger.debug(f"[熔断器] {key} 成功，已重置")
    
    def record_failure(self, model: str, brand: str):
        """记录失败"""
        key = self._get_key(model, brand)
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
        self.last_failure_times[key] = time.time()
        
        # 检查是否达到熔断阈值
        if self.failure_counts[key] >= self.failure_threshold:
            self.states[key] = CircuitState.OPEN
            api_logger.warning(f"[熔断器] {key} 已熔断 (失败{self.failure_counts[key]}次)")
        
        # 半开状态失败，返回熔断
        if self.states.get(key) == CircuitState.HALF_OPEN:
            self.states[key] = CircuitState.OPEN
            self.last_failure_times[key] = time.time()
            api_logger.warning(f"[熔断器] {key} 半开测试失败，重新熔断")
    
    def get_state(self, model: str, brand: str) -> str:
        """获取状态 (用于监控)"""
        key = self._get_key(model, brand)
        state = self.states.get(key, CircuitState.CLOSED)
        failure_count = self.failure_counts.get(key, 0)
        return f"{state.value} (失败{failure_count}次)"


# 全局实例
circuit_breaker = SmartCircuitBreaker(
    failure_threshold=5,      # 5 次失败才熔断
    recovery_timeout=30,      # 30 秒后恢复
    half_open_max_calls=1     # 半开状态允许 1 次测试
)


# 便捷函数
def is_model_available(model: str, brand: str) -> bool:
    """检查模型是否可用"""
    return circuit_breaker.is_available(model, brand)


def record_model_success(model: str, brand: str):
    """记录模型成功"""
    circuit_breaker.record_success(model, brand)


def record_model_failure(model: str, brand: str):
    """记录模型失败"""
    circuit_breaker.record_failure(model, brand)


__all__ = [
    'SmartCircuitBreaker',
    'CircuitState',
    'circuit_breaker',
    'is_model_available',
    'record_model_success',
    'record_model_failure'
]
