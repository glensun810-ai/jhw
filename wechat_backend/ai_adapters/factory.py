"""
Factory for creating and managing AI adapters
"""
from typing import Dict, Type, Union
from .base_adapter import AIClient, AIPlatformType
from .enhanced_factory import EnhancedAIAdapterFactory
# Import the new synchronous provider implementations
from .sync_providers import (
    DeepSeekProvider, DoubaoProvider, QwenProvider,
    YuanbaoProvider, ErnieProvider, KimiProvider
)
# Also import the original adapters if they still exist with safe imports
try:
    from .deepseek_adapter import DeepSeekAdapter
except ImportError:
    DeepSeekAdapter = None
try:
    from .qwen_adapter import QwenAdapter
except ImportError:
    QwenAdapter = None
try:
    from .doubao_adapter import DoubaoAdapter
except ImportError:
    DoubaoAdapter = None
try:
    from .chatgpt_adapter import ChatGPTAdapter
except ImportError:
    ChatGPTAdapter = None
try:
    from .gemini_adapter import GeminiAdapter
except ImportError:
    GeminiAdapter = None

# Register default providers - prioritize the new provider implementations
EnhancedAIAdapterFactory.register(AIPlatformType.DEEPSEEK, DeepSeekProvider)
EnhancedAIAdapterFactory.register(AIPlatformType.QWEN, QwenProvider)
EnhancedAIAdapterFactory.register(AIPlatformType.DOUBAO, DoubaoProvider)
EnhancedAIAdapterFactory.register(AIPlatformType.YUANBAO, YuanbaoProvider)
EnhancedAIAdapterFactory.register(AIPlatformType.WENXIN, ErnieProvider)
EnhancedAIAdapterFactory.register(AIPlatformType.KIMI, KimiProvider)

# Register fallback adapters if the new providers are not available
adapter_mapping = {
    AIPlatformType.DEEPSEEK: DeepSeekAdapter,
    AIPlatformType.QWEN: QwenAdapter,
    AIPlatformType.DOUBAO: DoubaoAdapter,
    AIPlatformType.CHATGPT: ChatGPTAdapter,
    AIPlatformType.GEMINI: GeminiAdapter,
}

for platform_type, adapter_class in adapter_mapping.items():
    if adapter_class and platform_type not in EnhancedAIAdapterFactory._adapters:
        EnhancedAIAdapterFactory.register(platform_type, adapter_class)

# Create an alias for backward compatibility
AIAdapterFactory = EnhancedAIAdapterFactory
