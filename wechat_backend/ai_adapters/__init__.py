"""
AI Adapters Package
Contains all AI platform adapters implementing the AIClient interface
"""
from .base_adapter import AIClient, AIResponse, AIPlatformType
from .factory import AIAdapterFactory
from .manager import AIManager
from .sync_providers import (
    DeepSeekProvider, DoubaoProvider, YuanbaoProvider,
    QwenProvider, ErnieProvider, KimiProvider
)

__all__ = [
    'AIClient', 'AIResponse', 'AIPlatformType',
    'AIAdapterFactory', 'AIManager',
    'DeepSeekProvider', 'DoubaoProvider', 'YuanbaoProvider',
    'QwenProvider', 'ErnieProvider', 'KimiProvider'
]