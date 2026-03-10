"""
AI Adapters Package
Contains all AI platform adapters implementing the AIClient interface
"""
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.provider_factory import ProviderFactory
from wechat_backend.ai_adapters.manager import AIManager
from wechat_backend.ai_adapters.doubao_provider import DoubaoProvider
from wechat_backend.ai_adapters.deepseek_provider import DeepSeekProvider
from wechat_backend.ai_adapters.sync_providers import (
    YuanbaoProvider, QwenProvider, ErnieProvider, KimiProvider
)

__all__ = [
    'AIClient', 'AIResponse', 'AIPlatformType', 'BaseAIProvider',
    'AIAdapterFactory', 'ProviderFactory', 'AIManager',
    'DoubaoProvider', 'DeepSeekProvider', 'YuanbaoProvider',
    'QwenProvider', 'ErnieProvider', 'KimiProvider'
]