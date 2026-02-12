#!/usr/bin/env python3
"""
性能和可靠性改进工具
此脚本用于实现连接池管理、断路器模式和优化的超时重试机制
"""

import os
import sys
from pathlib import Path
import time
import threading
from collections import deque, defaultdict
from enum import Enum
from typing import Callable, Any, Optional, Dict


def create_connection_pool_module():
    """创建连接池管理模块"""
    
    connection_pool_content = '''"""
连接池管理模块
提供高效的HTTP连接复用机制
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self, pool_connections=10, pool_maxsize=20, max_retries=3):
        """
        初始化连接池管理器
        :param pool_connections: 连接池数量
        :param pool_maxsize: 最大连接数
        :param max_retries: 最大重试次数
        """
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.sessions = {}
        self.lock = Lock()
        
        # 创建默认会话
        self.default_session = self._create_session()
    
    def _create_session(self):
        """创建配置好的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认头部
        session.headers.update({
            'User-Agent': 'GEO-Validator-Pooled-Client/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def get_session_for_host(self, host: str):
        """获取特定主机的会话"""
        with self.lock:
            if host not in self.sessions:
                self.sessions[host] = self._create_session()
            return self.sessions[host]
    
    def get_default_session(self):
        """获取默认会话"""
        return self.default_session
    
    def close_all_sessions(self):
        """关闭所有会话"""
        for session in self.sessions.values():
            session.close()
        self.default_session.close()
        logger.info("已关闭所有连接池会话")


# 全局连接池管理器实例
_pool_manager = None


def get_connection_pool_manager() -> ConnectionPoolManager:
    """获取连接池管理器实例"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    return _pool_manager


def get_session_for_url(url: str):
    """根据URL获取适当的会话"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = f"{parsed.scheme}://{parsed.netloc}"
    
    manager = get_connection_pool_manager()
    return manager.get_session_for_host(host)


def get_default_session():
    """获取默认会话"""
    manager = get_connection_pool_manager()
    return manager.get_default_session()


def cleanup_connection_pools():
    """清理所有连接池"""
    global _pool_manager
    if _pool_manager:
        _pool_manager.close_all_sessions()
        _pool_manager = None
'''
    
    # 获取网络目录
    network_dir = Path('wechat_backend/network')
    
    # 写入连接池模块
    with open(network_dir / 'connection_pool.py', 'w', encoding='utf-8') as f:
        f.write(connection_pool_content)
    
    print("✓ 已创建连接池管理模块: wechat_backend/network/connection_pool.py")


def create_circuit_breaker_module():
    """创建断路器模块"""
    
    circuit_breaker_content = '''"""
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
'''
    
    # 获取网络目录
    network_dir = Path('wechat_backend/network')
    
    # 写入断路器模块
    with open(network_dir / 'circuit_breaker.py', 'w', encoding='utf-8') as f:
        f.write(circuit_breaker_content)
    
    print("✓ 已创建断路器模块: wechat_backend/network/circuit_breaker.py")


def create_retry_mechanism_module():
    """创建重试机制模块"""
    
    retry_mechanism_content = '''"""
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
'''
    
    # 获取网络目录
    network_dir = Path('wechat_backend/network')
    
    # 写入重试机制模块
    with open(network_dir / 'retry_mechanism.py', 'w', encoding='utf-8') as f:
        f.write(retry_mechanism_content)
    
    print("✓ 已创建重试机制模块: wechat_backend/network/retry_mechanism.py")


def update_ai_adapters_with_resilience_features():
    """更新AI适配器以使用弹性和连接池功能"""
    
    # 更新DeepSeek适配器以使用新的弹性功能
    updated_deepseek_adapter = '''import time
import requests
from typing import Dict, Any, Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.security import get_http_client
from ..network.connection_pool import get_session_for_url
from ..network.circuit_breaker import get_circuit_breaker
from ..network.retry_mechanism import SmartRetryHandler
from config_manager import Config as PlatformConfigManager


class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台适配器
    用于将 DeepSeek API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式（deepseek-chat）和搜索/推理模式（deepseek-reasoner）
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_chinese_constraint: bool = True  # 新增参数：是否启用中文约束
    ):
        """
        初始化 DeepSeek 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示搜索/推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_chinese_constraint: 是否启用中文回答约束，默认为 True
        """
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_chinese_constraint = enable_chinese_constraint  # 存储中文约束开关
        
        # 初始化弹性组件
        self.circuit_breaker = get_circuit_breaker(f"deepseek_{model_name}")
        self.retry_handler = SmartRetryHandler(max_attempts=3, base_delay=1.0)
        
        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name} with resilience features")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示到 DeepSeek 并返回标准化响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek 响应的统一数据结构
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        def _make_request():
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 如果启用了中文约束，在原始 prompt 基础上添加约束指令
            # 这样做不会影响上层传入的原始 prompt，仅在发送给 AI 时附加约束
            processed_prompt = prompt
            if self.enable_chinese_constraint:
                constraint_instruction = (
                    "请严格按照以下要求作答：\\n"
                    "1. 必须使用中文回答\\n"
                    "2. 基于事实和公开信息作答\\n"
                    "3. 避免在不确定时胡编乱造\\n"
                    "4. 输出结构清晰（分点或分段）\\n\\n"
                )
                processed_prompt = constraint_instruction + prompt

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 搜索/推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力

            # 使用连接池发送请求到 DeepSeek API
            session = get_session_for_url(f"{self.base_url}/chat/completions")
            response = session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)  # 设置请求超时时间为30秒
            )

            # 检查响应状态码
            if response.status_code != 200:
                raise requests.HTTPError(f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}")

            # 解析响应数据
            response_data = response.json()

            # 提取所需信息
            content = ""
            usage = {}

            # 从响应中提取实际回答文本
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            # 从响应中提取使用情况信息
            usage = response_data.get("usage", {})

            # 计算请求延迟
            latency = time.time() - start_time

            # 返回成功的 AIResponse，包含模式信息
            return AIResponse(
                success=True,
                content=content,
                model=response_data.get("model", self.model_name),
                platform=self.platform_type.value,
                tokens_used=usage.get("total_tokens", 0),
                latency=latency,
                metadata=response_data
            )

        try:
            # 使用断路器包装请求
            response = self.circuit_breaker.call(_make_request)
            return response
        except Exception as e:
            # 记录延迟
            latency = time.time() - start_time
            
            # 根据错误类型确定错误类别
            error_type = self._map_request_exception(e) if isinstance(e, requests.RequestException) else AIErrorType.UNKNOWN_ERROR
            
            # 返回错误响应
            return AIResponse(
                success=False,
                error_message=f"请求失败: {str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_request_exception(self, e: requests.RequestException) -> AIErrorType:
        """将请求异常映射到标准错误类型"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return AIErrorType.INVALID_API_KEY
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT_EXCEEDED
            elif status_code >= 500:
                return AIErrorType.SERVER_ERROR
            elif status_code == 403:
                return AIErrorType.INVALID_API_KEY
        return AIErrorType.UNKNOWN_ERROR

    def health_check(self) -> bool:
        """
        检查 DeepSeek 客户端的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("你好，请回复'正常'。")
            return test_response.success
        except Exception:
            return False
'''
    
    # 更新AI适配器
    ai_adapters_dir = Path('wechat_backend/ai_adapters')
    
    # 保存更新后的DeepSeek适配器
    with open(ai_adapters_dir / 'deepseek_adapter.py', 'w', encoding='utf-8') as f:
        f.write(updated_deepseek_adapter)
    
    print("✓ 已更新DeepSeek适配器以使用弹性和连接池功能")


def main():
    print("🚀 开始执行安全改进计划 - 第三步：性能和可靠性改进")
    print("=" * 60)
    
    print("\n1. 创建连接池管理模块...")
    create_connection_pool_module()
    
    print("\n2. 创建断路器模块...")
    create_circuit_breaker_module()
    
    print("\n3. 创建重试机制模块...")
    create_retry_mechanism_module()
    
    print("\n4. 更新AI适配器以使用弹性和连接池功能...")
    update_ai_adapters_with_resilience_features()
    
    print("\n" + "=" * 60)
    print("✅ 第三步完成！")
    print("\n已完成：")
    print("• 创建了连接池管理模块，提高连接复用效率")
    print("• 创建了断路器模块，防止级联故障")
    print("• 创建了智能重试机制，提高请求成功率")
    print("• 更新了AI适配器以使用新的弹性功能")
    print("\n下一步：")
    print("• 部署弹性功能到生产环境")
    print("• 监控断路器状态和重试率")
    print("• 调优连接池和重试参数")


if __name__ == "__main__":
    main()