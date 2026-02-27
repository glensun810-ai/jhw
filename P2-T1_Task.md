系统重构 阶段二 - P2-T1 AI平台标准化数据交互层
任务背景
当前阶段：阶段二（核心业务功能实现）- Week 3-5
阶段目标：交付真实的统计分析报告
已完成任务：

阶段一所有任务已完成并合并（P1-T1 到 P1-T10）

基础能力已加固：状态机、超时、重试、死信队列、日志持久化、数据持久化、报告存根、轮询优化、集成测试、预发布验证

当前任务：P2-T1 - AI 平台标准化数据交互层

参考文档
重构基线：第 2.1.2 节 - AI 平台 API 交互设计、第 4.1 节 - 核心功能点清单

开发规范：第 2 章 - 代码开发规范、第 6 章 - API 设计规范、第 8 章 - 安全规范

实施路线图：第 2.2.2 节 - P2-T1 详细设计

核心要求（通用部分）
1. 严格遵守重构基线
业务导向：所有代码必须服务于"让用户获取真实品牌诊断报告"这一核心目标

真实数据：必须通过真实 API 调用获取数据，禁止模拟

可扩展性：设计必须支持未来接入新的 AI 平台，无需修改核心代码

错误处理：必须妥善处理各平台特有的错误码和异常

2. 严格遵守开发规范
目录结构：所有 v2 代码必须放在 wechat_backend/v2/ 目录下

命名规范：类名 PascalCase，函数名 snake_case，常量 UPPER_SNAKE_CASE

类型注解：所有函数必须有完整的类型注解

抽象基类：必须使用 ABC 定义接口，确保各适配器实现一致

异常处理：必须使用自定义异常类，统一错误处理

日志规范：必须使用结构化日志，记录每次 API 调用的关键信息

特性开关：所有新功能必须通过特性开关控制，默认关闭

配置管理：API Key 等敏感信息必须从环境变量读取，禁止硬编码

3. 与阶段一的集成
复用基础能力：必须使用阶段一实现的超时、重试、日志持久化机制

状态机集成：AI 调用过程中的状态更新需通过状态机管理

数据持久化：获取的响应数据需通过 P1-T6 的机制持久化

当前任务：P2-T1 - AI 平台标准化数据交互层
任务描述
实现 AI 平台适配器接口层，为后续接入多个 AI 平台（DeepSeek、豆包、通义千问等）提供统一标准。这是阶段二的核心基础，后续的所有统计分析和报告生成都依赖于本层提供的标准化数据。

核心职责：

定义统一接口：所有 AI 平台适配器必须实现相同的接口

请求标准化：将内部请求转换为各平台特定的 API 格式

响应标准化：将各平台返回的异构数据转换为统一格式

错误统一处理：将各平台特有的错误码转换为内部错误类型

适配器工厂：根据模型名称动态获取对应的适配器实例

可扩展性：新增 AI 平台时只需添加新的适配器类，无需修改核心逻辑

业务价值
标准化数据交互层的价值在于：

解耦：业务逻辑与具体 AI 平台解耦，更换平台不影响核心代码

可维护性：新增平台只需添加适配器，无需修改已有代码

数据一致性：所有平台返回的数据格式统一，便于后续分析

错误统一：业务层只需处理标准错误，无需关心各平台细节

具体需求
文件路径
text
wechat_backend/v2/adapters/
├── __init__.py
├── base.py                           # 抽象基类和公共数据结构
├── factory.py                         # 适配器工厂
├── deepseek_adapter.py                # DeepSeek 适配器
├── doubao_adapter.py                  # 豆包适配器
├── qwen_adapter.py                    # 通义千问适配器
├── errors.py                          # 适配器相关异常
└── models.py                          # 请求/响应数据模型

wechat_backend/v2/config/
└── ai_platforms.py                    # AI平台配置（API地址、超时等）

tests/unit/adapters/
├── test_base.py
├── test_factory.py
├── test_deepseek_adapter.py
├── test_doubao_adapter.py
└── test_qwen_adapter.py

tests/integration/
└── test_ai_adapters_integration.py    # 集成测试（使用mock）
第一部分：数据模型定义
python
# wechat_backend/v2/adapters/models.py

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AIProvider(str, Enum):
    """AI 平台枚举"""
    DEEPSEEK = 'deepseek'
    DOUBAO = 'doubao'
    QWEN = 'qwen'
    # 后续可扩展


@dataclass
class AIRequest:
    """
    标准化 AI 请求
    
    业务层统一使用此模型，适配器负责转换为各平台特有格式
    """
    # 核心参数
    prompt: str                                 # 提示词
    model: str                                  # 模型名称（如 deepseek-chat）
    
    # 可选参数
    temperature: float = 0.7                    # 温度（0-2）
    max_tokens: int = 2000                       # 最大输出 token 数
    top_p: float = 1.0                           # 核采样
    frequency_penalty: float = 0.0                # 频率惩罚
    presence_penalty: float = 0.0                 # 存在惩罚
    
    # 元数据
    request_id: Optional[str] = None             # 请求ID（用于追踪）
    timeout: int = 60                             # 超时时间（秒）
    
    # 上下文（用于对话场景）
    messages: Optional[List[Dict[str, str]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'prompt_preview': self.prompt[:100] + '...' if len(self.prompt) > 100 else self.prompt,
            'request_id': self.request_id,
        }


@dataclass
class AIResponse:
    """
    标准化 AI 响应
    
    各平台返回的原始响应需转换为此格式
    """
    # 核心响应
    content: str                                # 生成的文本内容
    model: str                                   # 实际使用的模型
    
    # 性能指标
    latency_ms: int                              # 响应延迟（毫秒）
    
    # Token 使用情况
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # 完成原因
    finish_reason: Optional[str] = None          # stop, length, content_filter等
    
    # 原始响应（保留用于调试和审计）
    raw_response: Optional[Dict[str, Any]] = None
    
    # 错误信息
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # 元数据
    request_id: Optional[str] = None
    provider: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        return {
            'model': self.model,
            'latency_ms': self.latency_ms,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'finish_reason': self.finish_reason,
            'error': self.error,
            'error_code': self.error_code,
            'provider': self.provider,
            'content_preview': self.content[:100] + '...' if self.content and len(self.content) > 100 else self.content,
        }
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.error is None
    
    @property
    def text_length(self) -> int:
        """响应文本长度"""
        return len(self.content) if self.content else 0


@dataclass
class AIStreamChunk:
    """
    流式响应块
    
    用于支持流式输出（后续扩展）
    """
    content: str
    is_finished: bool = False
    finish_reason: Optional[str] = None
    index: int = 0
第二部分：异常定义
python
# wechat_backend/v2/adapters/errors.py

from typing import Optional


class AIAdapterError(Exception):
    """AI 适配器基础异常"""
    
    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class AIAuthenticationError(AIAdapterError):
    """认证错误（API Key 无效）"""
    pass


class AIRateLimitError(AIAdapterError):
    """限流错误"""
    pass


class AIQuotaExceededError(AIAdapterError):
    """配额超限"""
    pass


class AITimeoutError(AIAdapterError):
    """超时错误"""
    pass


class AIConnectionError(AIAdapterError):
    """连接错误"""
    pass


class AIResponseError(AIAdapterError):
    """响应格式错误"""
    pass


class AIModelNotFoundError(AIAdapterError):
    """模型不存在"""
    pass


class AIContentFilterError(AIAdapterError):
    """内容被过滤"""
    pass


# 错误码映射（用于将平台特有错误转换为内部错误）
ERROR_CODE_MAPPING = {
    # 格式: ('provider', 'platform_error_code'): InternalErrorClass
}
第三部分：抽象基类
python
# wechat_backend/v2/adapters/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator
import asyncio
import time

from wechat_backend.v2.adapters.models import AIRequest, AIResponse, AIStreamChunk
from wechat_backend.v2.adapters.errors import (
    AIAdapterError, AIAuthenticationError, AIRateLimitError,
    AIQuotaExceededError, AITimeoutError, AIConnectionError,
    AIResponseError, AIModelNotFoundError, AIContentFilterError
)
from wechat_backend.v2.services.retry_policy import RetryPolicy
from wechat_backend.v2.services.api_call_logger import APICallLogger
from wechat_backend.v2.config.ai_platforms import get_platform_config


class BaseAIAdapter(ABC):
    """
    AI 适配器抽象基类
    
    所有具体平台的适配器必须继承此类并实现抽象方法。
    该类提供了通用的重试、日志、错误处理机制。
    """
    
    def __init__(self, provider: str):
        """
        初始化适配器
        
        Args:
            provider: 平台名称（如 'deepseek'）
        """
        self.provider = provider
        self.config = get_platform_config(provider)
        
        # 复用阶段一的基础服务
        self.retry_policy = RetryPolicy(
            max_retries=self.config.get('max_retries', 3),
            base_delay=self.config.get('retry_base_delay', 1.0),
            max_delay=self.config.get('retry_max_delay', 30.0),
            retryable_exceptions=[
                AITimeoutError,
                AIConnectionError,
                AIRateLimitError,
            ]
        )
        
        self.logger = APICallLogger()
        
        # 从环境变量获取 API Key
        self.api_key = self._get_api_key()
    
    @abstractmethod
    def _get_api_key(self) -> str:
        """
        获取 API Key（从环境变量）
        
        子类必须实现，从不同的环境变量名获取
        """
        pass
    
    @abstractmethod
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        构建平台特有的请求体
        
        Args:
            request: 标准化请求
            
        Returns:
            平台特有的请求字典
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        解析平台特有的响应
        
        Args:
            response_data: 平台返回的原始响应
            request: 原始请求（用于日志）
            
        Returns:
            标准化响应
            
        Raises:
            AIResponseError: 响应格式错误
        """
        pass
    
    @abstractmethod
    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        解析平台特有的错误
        
        Args:
            response_data: 错误响应
            status_code: HTTP 状态码
            
        Returns:
            对应的内部异常
        """
        pass
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（包含认证信息）"""
        pass
    
    @abstractmethod
    def _get_api_url(self) -> str:
        """获取 API 地址"""
        pass
    
    async def send(self, request: AIRequest) -> AIResponse:
        """
        发送请求（带重试和日志）
        
        这是对外提供的主要方法，子类通常不需要重写。
        
        Args:
            request: 标准化请求
            
        Returns:
            标准化响应
        """
        start_time = time.time()
        
        # 准备日志上下文
        log_context = {
            'provider': self.provider,
            'model': request.model,
            'request_id': request.request_id,
        }
        
        try:
            # 使用重试策略执行请求
            response = await self.retry_policy.execute_async(
                self._send_single,
                request=request
            )
            
            # 记录成功日志
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                response=response,
                latency_ms=latency_ms,
                success=True
            )
            
            return response
            
        except AIAdapterError as e:
            # 记录失败日志
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                error=e,
                latency_ms=latency_ms,
                success=False
            )
            raise
            
        except Exception as e:
            # 未知异常包装
            latency_ms = int((time.time() - start_time) * 1000)
            wrapped_error = AIAdapterError(
                f"Unexpected error: {str(e)}",
                provider=self.provider,
                original_error=e
            )
            self.logger.log_api_call(
                provider=self.provider,
                request=request,
                error=wrapped_error,
                latency_ms=latency_ms,
                success=False
            )
            raise wrapped_error
    
    async def _send_single(self, request: AIRequest) -> AIResponse:
        """
        发送单次请求（由重试策略调用）
        
        Args:
            request: 标准化请求
            
        Returns:
            标准化响应
            
        Raises:
            AIAdapterError: 各种适配器异常
        """
        # 1. 构建请求 payload
        payload = self._build_request_payload(request)
        
        # 2. 获取请求头和 URL
        headers = self._get_headers()
        url = self._get_api_url()
        
        # 3. 发送 HTTP 请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as resp:
                    
                    # 4. 读取响应
                    response_data = await resp.json()
                    
                    # 5. 检查 HTTP 状态码
                    if resp.status >= 400:
                        error = self._parse_error(response_data, resp.status)
                        raise error
                    
                    # 6. 解析响应
                    return self._parse_response(response_data, request)
                    
        except asyncio.TimeoutError:
            raise AITimeoutError(
                f"Request timeout after {request.timeout}s",
                provider=self.provider
            )
        except aiohttp.ClientConnectionError as e:
            raise AIConnectionError(
                f"Connection error: {str(e)}",
                provider=self.provider,
                original_error=e
            )
        except aiohttp.ClientError as e:
            raise AIAdapterError(
                f"HTTP client error: {str(e)}",
                provider=self.provider,
                original_error=e
            )
    
    async def send_stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        """
        流式发送（可选实现）
        
        子类可按需重写此方法支持流式输出
        """
        raise NotImplementedError(f"{self.provider} does not support streaming")
    
    def validate_response(self, response: AIResponse) -> bool:
        """
        验证响应有效性
        
        子类可重写此方法添加特定验证逻辑
        
        Args:
            response: 标准化响应
            
        Returns:
            是否有效
        """
        return response.is_success and response.content and len(response.content) > 0
第四部分：适配器工厂
python
# wechat_backend/v2/adapters/factory.py

from typing import Dict, Type, Optional
import importlib

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.errors import AIModelNotFoundError


class AIAdapterFactory:
    """
    AI 适配器工厂
    
    负责根据模型名称创建对应的适配器实例。
    支持动态注册和懒加载。
    """
    
    _adapters: Dict[str, Type[BaseAIAdapter]] = {}
    _instances: Dict[str, BaseAIAdapter] = {}
    
    @classmethod
    def register(cls, provider: str, adapter_class: Type[BaseAIAdapter]):
        """
        注册适配器类
        
        Args:
            provider: 平台名称
            adapter_class: 适配器类
        """
        cls._adapters[provider.lower()] = adapter_class
        # 清除已缓存的实例
        if provider.lower() in cls._instances:
            del cls._instances[provider.lower()]
    
    @classmethod
    def get_adapter(cls, provider: str) -> BaseAIAdapter:
        """
        获取适配器实例（单例模式）
        
        Args:
            provider: 平台名称
            
        Returns:
            适配器实例
            
        Raises:
            AIModelNotFoundError: 平台未注册
        """
        provider = provider.lower()
        
        # 返回缓存的实例
        if provider in cls._instances:
            return cls._instances[provider]
        
        # 获取适配器类
        adapter_class = cls._adapters.get(provider)
        if not adapter_class:
            # 尝试动态导入
            cls._try_import_adapter(provider)
            adapter_class = cls._adapters.get(provider)
            
        if not adapter_class:
            raise AIModelNotFoundError(
                f"AI provider '{provider}' not registered",
                provider=provider
            )
        
        # 创建并缓存实例
        instance = adapter_class(provider)
        cls._instances[provider] = instance
        return instance
    
    @classmethod
    def _try_import_adapter(cls, provider: str):
        """
        尝试动态导入适配器模块
        
        支持按需加载，避免导入所有适配器
        """
        try:
            module_name = f"wechat_backend.v2.adapters.{provider}_adapter"
            module = importlib.import_module(module_name)
            
            # 查找适配器类（通常命名为 {Provider}Adapter）
            class_name = f"{provider.capitalize()}Adapter"
            if hasattr(module, class_name):
                adapter_class = getattr(module, class_name)
                cls.register(provider, adapter_class)
        except ImportError:
            pass  # 忽略导入错误，后续会抛出异常
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """获取所有已注册的平台列表"""
        # 确保常用平台已加载
        for provider in ['deepseek', 'doubao', 'qwen']:
            cls._try_import_adapter(provider)
        
        return list(cls._adapters.keys())
    
    @classmethod
    def clear_cache(cls):
        """清除缓存（主要用于测试）"""
        cls._instances.clear()
    
    @classmethod
    def is_supported(cls, provider: str) -> bool:
        """检查平台是否支持"""
        return provider.lower() in cls.get_supported_providers()


# 便捷函数
def get_adapter(provider: str) -> BaseAIAdapter:
    """获取适配器的快捷方式"""
    return AIAdapterFactory.get_adapter(provider)


def get_supported_providers() -> list[str]:
    """获取支持平台的快捷方式"""
    return AIAdapterFactory.get_supported_providers()
第五部分：DeepSeek 适配器实现
python
# wechat_backend/v2/adapters/deepseek_adapter.py

import os
from typing import Dict, Any, Optional

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.errors import (
    AIAuthenticationError, AIRateLimitError, AIQuotaExceededError,
    AIResponseError, AIContentFilterError, AIModelNotFoundError
)


class DeepSeekAdapter(BaseAIAdapter):
    """
    DeepSeek AI 适配器
    
    官方文档: https://platform.deepseek.com/api-docs/
    """
    
    def __init__(self, provider: str = 'deepseek'):
        super().__init__(provider)
    
    def _get_api_key(self) -> str:
        """从环境变量获取 DeepSeek API Key"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        return api_key
    
    def _get_api_url(self) -> str:
        """获取 API 地址"""
        return self.config.get('api_url', 'https://api.deepseek.com/v1/chat/completions')
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        构建 DeepSeek 特有的请求体
        
        DeepSeek API 格式：
        {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "prompt"}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": false
        }
        """
        messages = request.messages or []
        if not messages and request.prompt:
            messages = [{"role": "user", "content": request.prompt}]
        
        payload = {
            "model": request.model or "deepseek-chat",
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False,
        }
        
        # 移除 None 值
        return {k: v for k, v in payload.items() if v is not None}
    
    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        解析 DeepSeek 响应
        
        DeepSeek 响应格式：
        {
            "id": "chatcmpl-xxx",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "response text"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        """
        try:
            # 提取响应内容
            choices = response_data.get('choices', [])
            if not choices:
                raise AIResponseError("No choices in response", provider=self.provider)
            
            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            # 提取使用情况
            usage = response_data.get('usage', {})
            
            # 提取完成原因
            finish_reason = first_choice.get('finish_reason')
            
            return AIResponse(
                content=content,
                model=response_data.get('model', request.model),
                latency_ms=0,  # 由上层填充
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                finish_reason=finish_reason,
                raw_response=response_data,
                provider=self.provider,
                request_id=response_data.get('id'),
            )
            
        except KeyError as e:
            raise AIResponseError(
                f"Missing field in response: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        解析 DeepSeek 错误
        
        DeepSeek 错误格式：
        {
            "error": {
                "message": "Invalid API key",
                "type": "invalid_request_error",
                "param": null,
                "code": "invalid_api_key"
            }
        }
        """
        error = response_data.get('error', {})
        message = error.get('message', 'Unknown error')
        error_code = error.get('code', '')
        error_type = error.get('type', '')
        
        # 根据状态码和错误码映射到内部异常
        if status_code == 401:
            return AIAuthenticationError(message, provider=self.provider)
        elif status_code == 429:
            if 'rate' in message.lower():
                return AIRateLimitError(message, provider=self.provider)
            else:
                return AIQuotaExceededError(message, provider=self.provider)
        elif status_code == 404:
            return AIModelNotFoundError(message, provider=self.provider)
        elif status_code == 400 and 'content' in message.lower():
            return AIContentFilterError(message, provider=self.provider)
        else:
            return AIAdapterError(message, provider=self.provider)
第六部分：豆包适配器实现
python
# wechat_backend/v2/adapters/doubao_adapter.py

import os
from typing import Dict, Any, Optional

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.errors import (
    AIAuthenticationError, AIRateLimitError, AIQuotaExceededError,
    AIResponseError, AIContentFilterError, AIModelNotFoundError
)


class DoubaoAdapter(BaseAIAdapter):
    """
    豆包 AI 适配器（字节跳动）
    
    官方文档: https://www.volcengine.com/docs/82379
    """
    
    def __init__(self, provider: str = 'doubao'):
        super().__init__(provider)
    
    def _get_api_key(self) -> str:
        """从环境变量获取豆包 API Key"""
        api_key = os.getenv('DOUBAO_API_KEY')
        if not api_key:
            raise ValueError("DOUBAO_API_KEY environment variable not set")
        return api_key
    
    def _get_api_url(self) -> str:
        """获取 API 地址"""
        return self.config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
    
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        构建豆包特有的请求体
        
        豆包 API 格式（兼容 OpenAI）：
        {
            "model": "doubao-lite-32k",
            "messages": [
                {"role": "user", "content": "prompt"}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        """
        messages = request.messages or []
        if not messages and request.prompt:
            messages = [{"role": "user", "content": request.prompt}]
        
        # 豆包特有：需要指定 endpoint_id 或 model
        # 这里简化处理，使用 model 字段
        payload = {
            "model": request.model or "doubao-lite-32k",
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
        }
        
        return {k: v for k, v in payload.items() if v is not None}
    
    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        解析豆包响应（兼容 OpenAI 格式）
        """
        try:
            choices = response_data.get('choices', [])
            if not choices:
                raise AIResponseError("No choices in response", provider=self.provider)
            
            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            usage = response_data.get('usage', {})
            
            return AIResponse(
                content=content,
                model=response_data.get('model', request.model),
                latency_ms=0,
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                finish_reason=first_choice.get('finish_reason'),
                raw_response=response_data,
                provider=self.provider,
                request_id=response_data.get('id'),
            )
            
        except KeyError as e:
            raise AIResponseError(
                f"Missing field in response: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        解析豆包错误
        """
        error = response_data.get('error', {})
        message = error.get('message', 'Unknown error')
        
        if status_code == 401:
            return AIAuthenticationError(message, provider=self.provider)
        elif status_code == 429:
            return AIRateLimitError(message, provider=self.provider)
        elif status_code == 404:
            return AIModelNotFoundError(message, provider=self.provider)
        elif status_code == 400:
            if 'content' in message.lower() or '敏感' in message:
                return AIContentFilterError(message, provider=self.provider)
            return AIAdapterError(message, provider=self.provider)
        else:
            return AIAdapterError(message, provider=self.provider)
第七部分：通义千问适配器实现
python
# wechat_backend/v2/adapters/qwen_adapter.py

import os
from typing import Dict, Any, Optional

from wechat_backend.v2.adapters.base import BaseAIAdapter
from wechat_backend.v2.adapters.models import AIRequest, AIResponse
from wechat_backend.v2.adapters.errors import (
    AIAuthenticationError, AIRateLimitError, AIQuotaExceededError,
    AIResponseError, AIContentFilterError, AIModelNotFoundError
)


class QwenAdapter(BaseAIAdapter):
    """
    通义千问适配器（阿里云）
    
    官方文档: https://help.aliyun.com/document_detail/613695.html
    """
    
    def __init__(self, provider: str = 'qwen'):
        super().__init__(provider)
    
    def _get_api_key(self) -> str:
        """从环境变量获取通义千问 API Key"""
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            raise ValueError("QWEN_API_KEY environment variable not set")
        return api_key
    
    def _get_api_url(self) -> str:
        """获取 API 地址"""
        return self.config.get('api_url', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（通义千问使用不同的认证方式）"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-SSE': 'disable',  # 禁用流式
        }
    
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """
        构建通义千问特有的请求体
        
        通义千问 API 格式：
        {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {"role": "user", "content": "prompt"}
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.8,
                "result_format": "message"
            }
        }
        """
        messages = request.messages or []
        if not messages and request.prompt:
            messages = [{"role": "user", "content": request.prompt}]
        
        payload = {
            "model": request.model or "qwen-turbo",
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "result_format": "message",
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
            }
        }
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any], request: AIRequest) -> AIResponse:
        """
        解析通义千问响应
        
        通义千问响应格式：
        {
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "response text"
                        },
                        "finish_reason": "stop"
                    }
                ]
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30
            }
        }
        """
        try:
            output = response_data.get('output', {})
            choices = output.get('choices', [])
            
            if not choices:
                raise AIResponseError("No choices in response", provider=self.provider)
            
            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            usage = response_data.get('usage', {})
            
            # 通义千问的 token 字段名不同
            prompt_tokens = usage.get('input_tokens')
            completion_tokens = usage.get('output_tokens')
            total_tokens = usage.get('total_tokens')
            
            return AIResponse(
                content=content,
                model=response_data.get('model', request.model),
                latency_ms=0,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=first_choice.get('finish_reason'),
                raw_response=response_data,
                provider=self.provider,
                request_id=response_data.get('request_id'),
            )
            
        except KeyError as e:
            raise AIResponseError(
                f"Missing field in response: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def _parse_error(self, response_data: Dict[str, Any], status_code: int) -> AIAdapterError:
        """
        解析通义千问错误
        
        通义千问错误格式：
        {
            "code": "InvalidApiKey",
            "message": "The API key is invalid",
            "request_id": "xxx"
        }
        """
        code = response_data.get('code', '')
        message = response_data.get('message', 'Unknown error')
        
        if status_code == 401 or 'InvalidApiKey' in code:
            return AIAuthenticationError(message, provider=self.provider)
        elif status_code == 429 or 'Throttling' in code:
            return AIRateLimitError(message, provider=self.provider)
        elif 'ModelNotFound' in code:
            return AIModelNotFoundError(message, provider=self.provider)
        elif 'ContentFilter' in code:
            return AIContentFilterError(message, provider=self.provider)
        elif 'QuotaExceeded' in code:
            return AIQuotaExceededError(message, provider=self.provider)
        else:
            return AIAdapterError(message, provider=self.provider)
第八部分：平台配置
python
# wechat_backend/v2/config/ai_platforms.py

"""
AI 平台配置管理
"""

from typing import Dict, Any
import os

# 平台默认配置
DEFAULT_CONFIGS = {
    'deepseek': {
        'api_url': 'https://api.deepseek.com/v1/chat/completions',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 10,  # 每分钟请求数
        'models': ['deepseek-chat', 'deepseek-coder'],
    },
    'doubao': {
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 20,
        'models': ['doubao-lite-32k', 'doubao-pro-32k'],
    },
    'qwen': {
        'api_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        'max_retries': 3,
        'retry_base_delay': 1.0,
        'retry_max_delay': 30.0,
        'timeout': 60,
        'rate_limit': 15,
        'models': ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    },
}


def get_platform_config(provider: str) -> Dict[str, Any]:
    """
    获取平台配置
    
    支持从环境变量覆盖默认配置
    """
    config = DEFAULT_CONFIGS.get(provider.lower(), {}).copy()
    
    # 从环境变量覆盖
    env_prefix = f"AI_{provider.upper()}_"
    for key in config.keys():
        env_key = env_prefix + key.upper()
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    
    return config


def get_all_platforms() -> list[str]:
    """获取所有已配置的平台"""
    return list(DEFAULT_CONFIGS.keys())


def is_platform_configured(provider: str) -> bool:
    """检查平台是否已配置（API Key 是否存在）"""
    env_var = f"{provider.upper()}_API_KEY"
    return env_var in os.environ
第九部分：与阶段一服务的集成
在诊断服务中使用适配器
python
# wechat_backend/v2/services/diagnosis_service.py（需要修改）

from wechat_backend.v2.adapters.factory import get_adapter
from wechat_backend.v2.adapters.models import AIRequest
from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine

class DiagnosisService:
    """诊断服务（集成AI适配器）"""
    
    def __init__(self):
        # ... 其他初始化
        self.adapter_factory = AIAdapterFactory
    
    async def execute_ai_call(
        self,
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        prompt: str
    ) -> Dict:
        """
        执行单个 AI 调用
        
        使用标准化适配器，集成阶段一的超时、重试、日志机制
        """
        # 1. 获取适配器
        adapter = get_adapter(model)
        
        # 2. 构建标准化请求
        request = AIRequest(
            prompt=prompt,
            model=model,
            temperature=0.7,
            max_tokens=2000,
            request_id=f"{execution_id}_{brand}_{model}"
        )
        
        # 3. 发送请求（自动包含重试和日志）
        response = await adapter.send(request)
        
        # 4. 更新状态机进度
        state_machine = DiagnosisStateMachine(execution_id)
        # ... 进度更新逻辑
        
        return response
    
    async def execute_diagnosis(self, execution_id: str, config: Dict):
        """执行完整诊断"""
        
        # 1. 获取所有需要调用的组合
        tasks = self._generate_tasks(config)
        total_tasks = len(tasks)
        completed = 0
        
        # 2. 并发执行 AI 调用
        async def execute_task(task):
            nonlocal completed
            try:
                response = await self.execute_ai_call(
                    execution_id=execution_id,
                    brand=task['brand'],
                    question=task['question'],
                    model=task['model'],
                    prompt=self._build_prompt(task['brand'], task['question'])
                )
                completed += 1
                
                # 更新进度
                progress = int(completed / total_tasks * 100)
                await self._update_progress(execution_id, progress)
                
                return {
                    'success': True,
                    'brand': task['brand'],
                    'question': task['question'],
                    'model': task['model'],
                    'response': response.to_dict(),
                }
            except Exception as e:
                completed += 1
                return {
                    'success': False,
                    'brand': task['brand'],
                    'question': task['question'],
                    'model': task['model'],
                    'error': str(e),
                }
        
        # 3. 并发执行
        results = await asyncio.gather(*[execute_task(t) for t in tasks])
        
        # 4. 保存结果到数据库（复用 P1-T6）
        await self.data_persistence.save_batch_responses(
            execution_id=execution_id,
            report_id=self._get_report_id(execution_id),
            responses=results
        )
        
        return results
第十部分：特性开关配置
python
# wechat_backend/v2/feature_flags.py（更新）

FEATURE_FLAGS = {
    # 阶段一已完成的功能（默认开启）
    'diagnosis_v2_state_machine': True,
    'diagnosis_v2_timeout': True,
    'diagnosis_v2_retry': True,
    'diagnosis_v2_dead_letter': True,
    'diagnosis_v2_api_logging': True,
    'diagnosis_v2_data_persistence': True,
    'diagnosis_v2_report_stub': True,
    
    # 阶段二新增开关
    'diagnosis_v2_ai_adapters': False,        # AI适配器总开关
    'diagnosis_v2_ai_deepseek': False,        # DeepSeek适配器开关
    'diagnosis_v2_ai_doubao': False,          # 豆包适配器开关
    'diagnosis_v2_ai_qwen': False,            # 通义千问适配器开关
    
    # 灰度控制
    'diagnosis_v2_gray_users': [],
    'diagnosis_v2_gray_percentage': 0,
    
    # 降级开关
    'diagnosis_v2_fallback_to_v1': True,
}
测试要求
单元测试覆盖场景
python
# tests/unit/adapters/test_base.py

class TestBaseAdapter:
    """测试基类功能"""
    
    def test_abstract_methods(self):
        """测试抽象方法必须实现"""
        pass
    
    def test_retry_integration(self):
        """测试与重试机制的集成"""
        pass
    
    def test_logging_integration(self):
        """测试与日志系统的集成"""
        pass
    
    def test_error_handling(self):
        """测试错误处理"""
        pass
python
# tests/unit/adapters/test_deepseek_adapter.py

class TestDeepSeekAdapter:
    """测试 DeepSeek 适配器"""
    
    def test_build_request_payload(self):
        """测试请求体构建"""
        adapter = DeepSeekAdapter()
        request = AIRequest(prompt="test", model="deepseek-chat")
        payload = adapter._build_request_payload(request)
        
        assert payload['model'] == 'deepseek-chat'
        assert payload['messages'][0]['content'] == 'test'
    
    def test_parse_response(self):
        """测试响应解析"""
        adapter = DeepSeekAdapter()
        mock_response = {
            'id': 'test-id',
            'model': 'deepseek-chat',
            'choices': [
                {
                    'message': {'content': 'test response'},
                    'finish_reason': 'stop'
                }
            ],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20}
        }
        
        response = adapter._parse_response(mock_response, AIRequest(prompt="test"))
        assert response.content == 'test response'
        assert response.prompt_tokens == 10
    
    def test_parse_error(self):
        """测试错误解析"""
        adapter = DeepSeekAdapter()
        mock_error = {'error': {'message': 'Invalid API key', 'code': 'invalid_api_key'}}
        
        error = adapter._parse_error(mock_error, 401)
        assert isinstance(error, AIAuthenticationError)
python
# tests/unit/adapters/test_factory.py

class TestAdapterFactory:
    """测试适配器工厂"""
    
    def test_get_adapter(self):
        """测试获取适配器"""
        adapter = AIAdapterFactory.get_adapter('deepseek')
        assert isinstance(adapter, DeepSeekAdapter)
        
        with pytest.raises(AIModelNotFoundError):
            AIAdapterFactory.get_adapter('unknown')
    
    def test_singleton(self):
        """测试单例模式"""
        adapter1 = AIAdapterFactory.get_adapter('deepseek')
        adapter2 = AIAdapterFactory.get_adapter('deepseek')
        assert adapter1 is adapter2
    
    def test_get_supported_providers(self):
        """测试获取支持平台"""
        providers = AIAdapterFactory.get_supported_providers()
        assert 'deepseek' in providers
        assert 'doubao' in providers
        assert 'qwen' in providers
集成测试
python
# tests/integration/test_ai_adapters_integration.py

class TestAIAdaptersIntegration:
    """AI适配器集成测试（使用mock）"""
    
    @pytest.mark.asyncio
    async def test_deepseek_real_call(self):
        """测试DeepSeek真实调用（需要API Key）"""
        if not os.getenv('DEEPSEEK_API_KEY'):
            pytest.skip("DEEPSEEK_API_KEY not set")
        
        adapter = get_adapter('deepseek')
        request = AIRequest(prompt="Hello", model="deepseek-chat")
        
        response = await adapter.send(request)
        assert response.is_success
        assert response.content
    
    @pytest.mark.asyncio
    async def test_all_adapters_same_interface(self):
        """测试所有适配器接口一致"""
        for provider in get_supported_providers():
            adapter = get_adapter(provider)
            assert hasattr(adapter, 'send')
            assert hasattr(adapter, 'send_stream')
            assert callable(adapter.send)
输出要求
1. 完整代码实现
wechat_backend/v2/adapters/base.py

wechat_backend/v2/adapters/models.py

wechat_backend/v2/adapters/errors.py

wechat_backend/v2/adapters/factory.py

wechat_backend/v2/adapters/deepseek_adapter.py

wechat_backend/v2/adapters/doubao_adapter.py

wechat_backend/v2/adapters/qwen_adapter.py

wechat_backend/v2/config/ai_platforms.py

wechat_backend/v2/feature_flags.py（更新）

2. 测试代码
tests/unit/adapters/test_base.py

tests/unit/adapters/test_factory.py

tests/unit/adapters/test_deepseek_adapter.py

tests/unit/adapters/test_doubao_adapter.py

tests/unit/adapters/test_qwen_adapter.py

tests/integration/test_ai_adapters_integration.py

3. 提交信息
bash
feat(ai-adapters): implement standardized AI platform interaction layer

- Add base abstract class with common retry/logging/error handling
- Define standardized request/response models
- Implement adapter factory with dynamic loading
- Add DeepSeek, Doubao, Qwen adapters with platform-specific logic
- Integrate with phase-one services (timeout, retry, logging)
- Add comprehensive unit and integration tests
- Update feature flags for phase two

Closes #201
Refs: 2026-02-27-重构基线.md, 2026-02-27-重构实施路线图.md

Change-Id: I1234567890abcdef
4. PR 描述模板
markdown
## 变更说明
实现 AI 平台标准化数据交互层，为后续统计分析提供统一的数据接口。

主要功能：
1. 抽象基类 BaseAIAdapter 定义统一接口
2. 标准化请求/响应模型 AIRequest/AIResponse
3. 适配器工厂支持动态加载和单例模式
4. DeepSeek、豆包、通义千问三个平台的适配器实现
5. 集成阶段一的超时、重试、日志机制
6. 完善的错误处理和错误码映射

## 关联文档
- 重构基线：第 2.1.2 节 - AI 平台 API 交互设计
- 实施路线图：P2-T1
- 开发规范：第 2 章 - 代码开发规范、第 8 章 - 安全规范

## 测试计划
- [x] 单元测试已添加（覆盖率 92%）
- [x] 集成测试已添加
- [ ] 真实环境测试（需要 API Key）

### 测试结果
单元测试：25 passed, 0 failed
集成测试：3 passed, 0 failed
覆盖率：92%
关键场景验证：

请求构建 ✓

响应解析 ✓

错误处理 ✓

工厂模式 ✓

重试集成 ✓

text

## 验收标准
- [x] 所有抽象方法在子类中实现
- [x] 统一请求/响应模型
- [x] 支持至少3个AI平台
- [x] 与阶段一服务正确集成
- [x] 测试覆盖率 > 85%

## 回滚方案
关闭特性开关 `diagnosis_v2_ai_adapters` 即可禁用新适配器，系统继续使用旧的AI调用方式。

```python
FEATURE_FLAGS['diagnosis_v2_ai_adapters'] = False
环境变量
需要配置以下环境变量：

DEEPSEEK_API_KEY

DOUBAO_API_KEY

QWEN_API_KEY

依赖关系
依赖阶段一的所有基础能力

本任务完成后，P2-T2 数据清洗管道将依赖此层的标准化数据

text

---

## 注意事项

1. **API Key 安全**：所有 API Key 必须从环境变量读取，禁止硬编码
2. **错误处理**：必须妥善处理各平台特有的错误码，转换为内部统一异常
3. **重试集成**：必须正确使用阶段一的重试机制，避免重复实现
4. **日志记录**：每次调用都要记录结构化日志，包含请求ID便于追踪
5. **超时控制**：必须使用阶段一的超时机制，避免请求卡死
6. **可扩展性**：新增平台只需添加新的适配器类，无需修改核心代码
7. **测试覆盖**：每个适配器都要有单元测试，覆盖正常和异常场景

---

## 验证清单（交付前自查）

### 代码完整性
- [ ] 所有抽象方法在子类中实现
- [ ] 请求/响应模型定义完整
- [ ] 异常类层次清晰
- [ ] 工厂模式实现正确

### 功能完整性
- [ ] DeepSeek适配器可正常工作
- [ ] 豆包适配器可正常工作
- [ ] 通义千问适配器可正常工作
- [ ] 错误码正确映射
- [ ] 重试机制生效

### 安全规范
- [ ] API Key 从环境变量读取
- [ ] 无敏感信息硬编码
- [ ] 请求头包含必要认证信息

### 测试覆盖
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试通过
- [ ] 边界条件测试覆盖

### 文档
- [ ] 代码有完整 docstring
- [ ] 使用示例完整
- [ ] 环境变量说明清晰