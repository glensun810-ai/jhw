"""
AI Adapters Package
Contains all AI platform adapters implementing the AIClient interface
"""
from .base_adapter import AIClient, AIResponse, AIPlatformType
from .base_provider import BaseAIProvider
from .factory import AIAdapterFactory
from .provider_factory import ProviderFactory
from .manager import AIManager
from .doubao_provider import DoubaoProvider
from .deepseek_provider import DeepSeekProvider
from .sync_providers import (
    YuanbaoProvider, QwenProvider, ErnieProvider, KimiProvider
)

__all__ = [
    'AIClient', 'AIResponse', 'AIPlatformType', 'BaseAIProvider',
    'AIAdapterFactory', 'ProviderFactory', 'AIManager',
    'DoubaoProvider', 'DeepSeekProvider', 'YuanbaoProvider',
    'QwenProvider', 'ErnieProvider', 'KimiProvider'
]