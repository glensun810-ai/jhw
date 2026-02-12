"""
断路器模式实现
提供服务熔断和恢复机制
"""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"      # 关闭状态：正常请求
    OPEN = "open"          # 打开状态：拒绝请求
    HALF_OPEN = "half_open" # 半开状态：试探性请求


class CircuitBreaker:
    """断路器实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 expected_exception_types: tuple = (Exception,)):
        """
        初始化断路器
        :param failure_threshold: 失败阈值，超过此值进入打开状态
        :param recovery_timeout: 恢复超时时间（秒）
        :param expected_exception_types: 触发失败计数的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception_types = expected_exception_types
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()
        self.last_attempt_time = 0
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带断路器保护的函数调用
        :param func: 要执行的函数
        :param args: 函数位置参数
        :param kwargs: 函数关键字参数
        :return: 函数执行结果
        :raises: 如果断路器打开或函数执行失败
        """
        with self.lock:
            # 检查是否应该尝试恢复
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("断路器进入半开状态，准备尝试恢复")
                else:
                    raise Exception(f"Circuit breaker is OPEN. Last failure: {time.time() - self.last_failure_time:.1f}s ago")
            
            # 记录尝试时间
            self.last_attempt_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # 调用成功，重置失败计数
            self._on_success()
            return result
            
        except self.expected_exception_types as e:
            # 调用失败，增加失败计数
            self._on_failure(type(e).__name__, str(e))
            raise e
        except Exception as e:
            # 其他异常也计入失败
            self._on_failure(f"Unexpected-{type(e).__name__}", str(e))
            raise e
    
    def _on_success(self):
        """调用成功时的处理"""
        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            logger.debug("断路器调用成功，重置为关闭状态")
    
    def _on_failure(self, exception_type: str, exception_msg: str):
        """调用失败时的处理"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(f"断路器检测到失败 #{self.failure_count} ({exception_type}): {exception_msg}")
            
            # 检查是否需要打开断路器
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"断路器打开！失败次数达到阈值 {self.failure_threshold}")
    
    def force_open(self):
        """强制打开断路器"""
        with self.lock:
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()
            self.failure_count = self.failure_threshold
            logger.warning("断路器被强制打开")
    
    def force_close(self):
        """强制关闭断路器"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info("断路器被强制关闭")
    
    def get_state_info(self) -> dict:
        """获取断路器状态信息"""
        with self.lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
                'last_failure_time': self.last_failure_time,
                'last_attempt_time': self.last_attempt_time,
                'time_since_last_failure': time.time() - self.last_failure_time if self.last_failure_time else None,
                'can_attempt_reset': (
                    self.state == CircuitState.OPEN and 
                    time.time() - self.last_failure_time >= self.recovery_timeout
                ) if self.last_failure_time else False
            }


class CircuitBreakerGroup:
    """断路器组，用于管理多个相关服务的断路器"""
    
    def __init__(self):
        self.circuit_breakers = {}
        self.lock = threading.Lock()
    
    def get_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """获取指定名称的断路器"""
        with self.lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(**kwargs)
            return self.circuit_breakers[name]
    
    def get_state_info(self) -> dict:
        """获取所有断路器的状态信息"""
        with self.lock:
            return {name: cb.get_state_info() for name, cb in self.circuit_breakers.items()}
    
    def force_open_all(self):
        """强制打开所有断路器"""
        with self.lock:
            for cb in self.circuit_breakers.values():
                cb.force_open()
    
    def force_close_all(self):
        """强制关闭所有断路器"""
        with self.lock:
            for cb in self.circuit_breakers.values():
                cb.force_close()


# 全局断路器组实例
_circuit_breaker_group = None


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """获取指定名称的断路器"""
    global _circuit_breaker_group
    if _circuit_breaker_group is None:
        _circuit_breaker_group = CircuitBreakerGroup()
    return _circuit_breaker_group.get_circuit_breaker(name, **kwargs)


def get_circuit_breaker_group() -> CircuitBreakerGroup:
    """获取断路器组"""
    global _circuit_breaker_group
    if _circuit_breaker_group is None:
        _circuit_breaker_group = CircuitBreakerGroup()
    return _circuit_breaker_group
