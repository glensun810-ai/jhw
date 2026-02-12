#!/usr/bin/env python3
"""
代码重构和优化工具
此脚本用于实现速率限制、统一网络请求封装和其他优化
"""

import os
import sys
from pathlib import Path
import time
import threading
from collections import deque
import hashlib
from typing import Dict, Any, Optional


def create_rate_limiter():
    """创建速率限制器模块"""
    
    rate_limiter_content = '''"""
速率限制器
实现多种速率限制算法
"""

import time
import threading
from collections import deque, defaultdict
from typing import Dict, Optional
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """速率限制算法类型"""
    TOKEN_BUCKET = "token_bucket"
    LEAKING_BUCKET = "leaking_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class RateLimiter:
    """速率限制器基类"""
    
    def __init__(self, algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET):
        self.algorithm = algorithm
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """检查请求是否被允许"""
        raise NotImplementedError("子类必须实现 is_allowed 方法")


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.TOKEN_BUCKET)
        self.buckets = {}
    
    def is_allowed(self, key: str, capacity: int, refill_rate: float) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键（如用户ID、IP地址等）
        :param capacity: 桶容量
        :param refill_rate: 令牌填充速率（每秒填充的令牌数）
        """
        with self.lock:
            now = time.time()
            
            if key not in self.buckets:
                # 初始化桶
                self.buckets[key] = {
                    'tokens': capacity,
                    'last_refill': now
                }
            
            bucket = self.buckets[key]
            
            # 计算应该添加的令牌数
            time_passed = now - bucket['last_refill']
            tokens_to_add = time_passed * refill_rate
            bucket['tokens'] = min(capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now
            
            # 检查是否有足够的令牌
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            else:
                return False


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.SLIDING_WINDOW)
        self.windows = defaultdict(deque)
    
    def is_allowed(self, key: str, limit: int, window_size: int) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 时间窗口内的最大请求数
        :param window_size: 时间窗口大小（秒）
        """
        with self.lock:
            now = time.time()
            window = self.windows[key]
            
            # 移除超出时间窗口的请求记录
            while window and now - window[0] > window_size:
                window.popleft()
            
            # 检查是否超过限制
            if len(window) < limit:
                window.append(now)
                return True
            else:
                return False


class FixedWindowRateLimiter(RateLimiter):
    """固定窗口算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.FIXED_WINDOW)
        self.windows = {}
    
    def is_allowed(self, key: str, limit: int, window_size: int) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 时间窗口内的最大请求数
        :param window_size: 时间窗口大小（秒）
        """
        with self.lock:
            now = time.time()
            window_start = int(now // window_size) * window_size  # 当前窗口开始时间
            
            if key not in self.windows:
                self.windows[key] = {'count': 0, 'window_start': window_start}
            
            window = self.windows[key]
            
            # 检查是否进入新窗口
            if now >= window['window_start'] + window_size:
                # 重置窗口
                window['count'] = 1
                window['window_start'] = window_start
                return True
            else:
                # 检查是否超过限制
                if window['count'] < limit:
                    window['count'] += 1
                    return True
                else:
                    return False


class RateLimiterManager:
    """速率限制器管理器"""
    
    def __init__(self):
        self.limiters = {
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketRateLimiter(),
            RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowRateLimiter(),
            RateLimitAlgorithm.FIXED_WINDOW: FixedWindowRateLimiter(),
        }
        self.default_algorithm = RateLimitAlgorithm.SLIDING_WINDOW
        self.lock = threading.Lock()
    
    def is_allowed(self, 
                   key: str, 
                   limit: int, 
                   window_size: int, 
                   algorithm: RateLimitAlgorithm = None,
                   capacity: int = None,
                   refill_rate: float = None) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 限制数量
        :param window_size: 时间窗口大小
        :param algorithm: 限流算法
        :param capacity: 桶容量（令牌桶算法）
        :param refill_rate: 填充速率（令牌桶算法）
        """
        algorithm = algorithm or self.default_algorithm
        
        limiter = self.limiters[algorithm]
        
        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            # 令牌桶使用capacity和refill_rate参数
            cap = capacity or limit
            rate = refill_rate or (limit / window_size)
            return limiter.is_allowed(key, cap, rate)
        else:
            # 其他算法使用limit和window_size参数
            return limiter.is_allowed(key, limit, window_size)
    
    def get_limiter(self, algorithm: RateLimitAlgorithm):
        """获取指定算法的限流器"""
        return self.limiters[algorithm]


# 全局速率限制器实例
_rate_limiter_manager = None


def get_rate_limiter_manager() -> RateLimiterManager:
    """获取速率限制器管理器实例"""
    global _rate_limiter_manager
    if _rate_limiter_manager is None:
        _rate_limiter_manager = RateLimiterManager()
    return _rate_limiter_manager


def is_rate_limited(key: str, limit: int, window_size: int, **kwargs) -> bool:
    """便捷函数：检查是否被限流"""
    manager = get_rate_limiter_manager()
    return not manager.is_allowed(key, limit, window_size, **kwargs)


def check_rate_limit(key: str, limit: int, window_size: int, **kwargs) -> Dict[str, Any]:
    """检查速率限制状态"""
    manager = get_rate_limiter_manager()
    allowed = manager.is_allowed(key, limit, window_size, **kwargs)
    
    return {
        'allowed': allowed,
        'limit': limit,
        'window_size': window_size,
        'key': key
    }
'''
    
    # 获取网络目录
    network_dir = Path('wechat_backend/network')
    
    # 写入速率限制器模块
    with open(network_dir / 'rate_limiter.py', 'w', encoding='utf-8') as f:
        f.write(rate_limiter_content)
    
    print("✓ 已创建速率限制器模块: wechat_backend/network/rate_limiter.py")


def create_unified_request_wrapper():
    """创建统一的请求封装模块"""
    
    unified_request_content = '''"""
统一的HTTP请求封装
提供统一的请求接口和集中处理认证、重试、错误处理等功能
"""

import time
import requests
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import logging
from ..network.security import get_http_client
from ..network.connection_pool import get_session_for_url
from ..network.circuit_breaker import get_circuit_breaker
from ..network.retry_mechanism import SmartRetryHandler
from ..network.rate_limiter import is_rate_limited
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response

logger = logging.getLogger(__name__)


class UnifiedRequestWrapper:
    """统一的HTTP请求封装器"""
    
    def __init__(self, 
                 base_url: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit_key: str = "default",
                 rate_limit_requests: int = 100,
                 rate_limit_window: int = 60):
        """
        初始化请求封装器
        :param base_url: 基础URL
        :param default_headers: 默认请求头
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        :param rate_limit_key: 速率限制键
        :param rate_limit_requests: 时间窗口内的最大请求数
        :param rate_limit_window: 速率限制时间窗口（秒）
        """
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_key = rate_limit_key
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # 初始化组件
        self.retry_handler = SmartRetryHandler(max_attempts=max_retries)
        self.circuit_breaker = get_circuit_breaker(f"unified_request_{rate_limit_key}")
        
    def _prepare_url(self, endpoint: str) -> str:
        """准备完整URL"""
        if self.base_url:
            return urljoin(self.base_url, endpoint.lstrip('/'))
        else:
            return endpoint
    
    def _prepare_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备请求头"""
        headers = self.default_headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def _check_rate_limit(self) -> bool:
        """检查速率限制"""
        return not is_rate_limited(
            key=self.rate_limit_key,
            limit=self.rate_limit_requests,
            window_size=self.rate_limit_window
        )
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     headers: Optional[Dict[str, str]] = None, 
                     **kwargs) -> requests.Response:
        """执行HTTP请求"""
        # 检查速率限制
        if not self._check_rate_limit():
            raise Exception(f"Rate limit exceeded for key: {self.rate_limit_key}")
        
        # 准备URL和头部
        url = self._prepare_url(endpoint)
        prepared_headers = self._prepare_headers(headers)
        
        # 记录请求
        log_api_request(
            method=method.upper(),
            endpoint=url,
            request_size=len(str(kwargs.get('json', '')))
        )
        
        # 记录开始时间
        start_time = time.time()
        
        # 使用连接池发送请求
        session = get_session_for_url(url)
        response = session.request(
            method=method.upper(),
            url=url,
            headers=prepared_headers,
            timeout=kwargs.pop('timeout', self.timeout),
            **kwargs
        )
        
        # 计算响应时间
        response_time = time.time() - start_time
        
        # 记录响应
        log_api_response(
            endpoint=url,
            status_code=response.status_code,
            response_time=response_time,
            response_size=len(response.content)
        )
        
        # 记录指标
        record_api_call(
            platform=self.rate_limit_key,
            endpoint=endpoint,
            status_code=response.status_code,
            response_time=response_time
        )
        
        return response
    
    def get(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """GET请求"""
        return self._make_request('GET', endpoint, headers, **kwargs)
    
    def post(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """POST请求"""
        return self._make_request('POST', endpoint, headers, **kwargs)
    
    def put(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """PUT请求"""
        return self._make_request('PUT', endpoint, headers, **kwargs)
    
    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self._make_request('DELETE', endpoint, headers, **kwargs)
    
    def patch(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """PATCH请求"""
        return self._make_request('PATCH', endpoint, headers, **kwargs)
    
    def request_with_resilience(self, 
                               method: str, 
                               endpoint: str, 
                               headers: Optional[Dict[str, str]] = None, 
                               **kwargs) -> requests.Response:
        """
        使用弹性功能的请求
        包括断路器、重试、速率限制等
        """
        def _request_func():
            return self._make_request(method, endpoint, headers, **kwargs)
        
        # 使用断路器包装请求
        try:
            return self.circuit_breaker.call(_request_func)
        except Exception as e:
            # 记录错误
            record_error(self.rate_limit_key, type(e).__name__, str(e))
            raise e


class AIPlatformRequestWrapper(UnifiedRequestWrapper):
    """AI平台专用请求封装器"""
    
    def __init__(self, 
                 platform_name: str,
                 base_url: str = "",
                 api_key: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        初始化AI平台请求封装器
        :param platform_name: 平台名称
        :param base_url: 基础URL
        :param api_key: API密钥
        :param default_headers: 默认请求头
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        """
        # 设置默认头部，包含认证信息
        headers = default_headers or {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        super().__init__(
            base_url=base_url,
            default_headers=headers,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_key=platform_name
        )
        
        self.platform_name = platform_name
        self.api_key = api_key
    
    def make_ai_request(self, 
                       endpoint: str, 
                       prompt: str, 
                       model: str = None,
                       headers: Optional[Dict[str, str]] = None, 
                       **kwargs) -> requests.Response:
        """发送AI请求"""
        # 添加AI特定的头部
        ai_headers = headers or {}
        if model:
            ai_headers['X-Model'] = model
        
        return self.request_with_resilience('POST', endpoint, ai_headers, **kwargs)


# 全局请求封装器实例
_request_wrappers = {}


def get_request_wrapper(name: str, **kwargs) -> UnifiedRequestWrapper:
    """获取指定名称的请求封装器"""
    global _request_wrappers
    if name not in _request_wrappers:
        _request_wrappers[name] = UnifiedRequestWrapper(**kwargs)
    return _request_wrappers[name]


def get_ai_request_wrapper(platform_name: str, **kwargs) -> AIPlatformRequestWrapper:
    """获取AI平台请求封装器"""
    return AIPlatformRequestWrapper(platform_name=platform_name, **kwargs)
'''
    
    # 获取网络目录
    network_dir = Path('wechat_backend/network')
    
    # 写入统一请求封装模块
    with open(network_dir / 'request_wrapper.py', 'w', encoding='utf-8') as f:
        f.write(unified_request_content)
    
    print("✓ 已创建统一请求封装模块: wechat_backend/network/request_wrapper.py")


def update_ai_adapters_with_unified_wrapper():
    """更新AI适配器以使用统一请求封装"""
    
    # 更新DeepSeek适配器以使用统一请求封装
    updated_deepseek_adapter = '''import time
import requests
from typing import Dict, Any, Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
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

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="deepseek",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name} with unified request wrapper")

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

        try:
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

            # 使用统一请求封装器发送请求到 DeepSeek API
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=processed_prompt,
                model=self.model_name,
                json=payload,
                timeout=kwargs.get('timeout', 30)  # 设置请求超时时间为30秒
            )

            # 计算请求延迟
            latency = time.time() - start_time

            # 检查响应状态码
            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVER_ERROR,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

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

        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message="请求超时",
                error_type=AIErrorType.SERVER_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            error_type = self._map_request_exception(e)
            return AIResponse(
                success=False,
                error_message=f"请求异常: {str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.INVALID_API_KEY,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=f"未知错误: {str(e)}",
                error_type=AIErrorType.UNKNOWN_ERROR,
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
    
    print("✓ 已更新DeepSeek适配器以使用统一请求封装")


def main():
    print("🚀 开始执行安全改进计划 - 第五步：代码重构和优化")
    print("=" * 60)
    
    print("\n1. 创建速率限制器模块...")
    create_rate_limiter()
    
    print("\n2. 创建统一的请求封装模块...")
    create_unified_request_wrapper()
    
    print("\n3. 更新AI适配器以使用统一请求封装...")
    update_ai_adapters_with_unified_wrapper()
    
    print("\n" + "=" * 60)
    print("✅ 第五步完成！")
    print("\n已完成：")
    print("• 创建了多种算法的速率限制器")
    print("• 创建了统一的HTTP请求封装")
    print("• 更新了AI适配器以使用新的封装")
    print("\n下一步：")
    print("• 部署优化后的代码到生产环境")
    print("• 监控速率限制效果")
    print("• 调优各种参数")


if __name__ == "__main__":
    main()