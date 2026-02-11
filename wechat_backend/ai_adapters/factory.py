"""
Factory for creating and managing AI adapters
"""
from typing import Dict, Type, Union
from .base_adapter import AIClient, AIPlatformType
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

class AIAdapterFactory:
    """
    Factory class for creating AI adapters based on platform type.
    """

    _adapters: Dict[AIPlatformType, Type[AIClient]] = {}

    @classmethod
    def register(cls, platform_type: AIPlatformType, adapter_class: Type[AIClient]):
        """
        Register an AI adapter class for a specific platform type
        """
        cls._adapters[platform_type] = adapter_class

    @classmethod
    def create(cls, platform_type: Union[AIPlatformType, str], api_key: str, model_name: str, **kwargs) -> AIClient:
        """
        Create an instance of an AI adapter for the specified platform
        """
        if isinstance(platform_type, str):
            try:
                platform_type = AIPlatformType(platform_type.lower())
            except ValueError:
                raise ValueError(f"Unknown platform type: {platform_type}")

        if platform_type not in cls._adapters:
            raise ValueError(f"No adapter registered for platform: {platform_type}")

        adapter_class = cls._adapters[platform_type]
        return adapter_class(api_key, model_name, **kwargs)

# Register default providers - prioritize the new provider implementations
AIAdapterFactory.register(AIPlatformType.DEEPSEEK, DeepSeekProvider)
AIAdapterFactory.register(AIPlatformType.QWEN, QwenProvider)
AIAdapterFactory.register(AIPlatformType.DOUBAO, DoubaoProvider)
AIAdapterFactory.register(AIPlatformType.YUANBAO, YuanbaoProvider)
AIAdapterFactory.register(AIPlatformType.WENXIN, ErnieProvider)
AIAdapterFactory.register(AIPlatformType.KIMI, KimiProvider)

# Register fallback adapters if the new providers are not available
adapter_mapping = {
    AIPlatformType.DEEPSEEK: DeepSeekAdapter,
    AIPlatformType.QWEN: QwenAdapter,
    AIPlatformType.DOUBAO: DoubaoAdapter,
    AIPlatformType.CHATGPT: ChatGPTAdapter,
    AIPlatformType.GEMINI: GeminiAdapter,
}

for platform_type, adapter_class in adapter_mapping.items():
    if adapter_class and platform_type not in AIAdapterFactory._adapters:
        AIAdapterFactory.register(platform_type, adapter_class)
