"""
AI Adapters Package

This package provides standardized AI platform adapters for:
- DeepSeek
- Doubao (ByteDance)
- Qwen (Alibaba Cloud)

Usage:
    from wechat_backend.v2.adapters import get_adapter, AIRequest
    from wechat_backend.v2.adapters.factory import get_supported_providers

    adapter = get_adapter('deepseek')
    request = AIRequest(prompt="Hello", model="deepseek-chat")
    response = await adapter.send(request)
"""

from wechat_backend.v2.adapters.models import AIRequest, AIResponse, AIStreamChunk, AIProvider
from wechat_backend.v2.adapters.factory import get_adapter, get_supported_providers, AIAdapterFactory
from wechat_backend.v2.adapters.errors import (
    AIAdapterError,
    AIAuthenticationError,
    AIRateLimitError,
    AIQuotaExceededError,
    AITimeoutError,
    AIConnectionError,
    AIResponseError,
    AIModelNotFoundError,
    AIContentFilterError,
)
from wechat_backend.v2.adapters.base import BaseAIAdapter

__all__ = [
    # Models
    'AIRequest',
    'AIResponse',
    'AIStreamChunk',
    'AIProvider',
    
    # Factory
    'get_adapter',
    'get_supported_providers',
    'AIAdapterFactory',
    
    # Base class
    'BaseAIAdapter',
    
    # Errors
    'AIAdapterError',
    'AIAuthenticationError',
    'AIRateLimitError',
    'AIQuotaExceededError',
    'AITimeoutError',
    'AIConnectionError',
    'AIResponseError',
    'AIModelNotFoundError',
    'AIContentFilterError',
]
