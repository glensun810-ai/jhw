"""
Factory for creating and managing AI adapters
"""
from typing import Dict, Type, Union
from .base_adapter import AIClient, AIPlatformType
from ..logging_config import api_logger

# 动态导入适配器，防止单个适配器的依赖问题导致整个应用崩溃
try:
    from .deepseek_adapter import DeepSeekAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import DeepSeekAdapter: {e}")
    DeepSeekAdapter = None

try:
    from .qwen_adapter import QwenAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import QwenAdapter: {e}")
    QwenAdapter = None

try:
    from .doubao_adapter import DoubaoAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import DoubaoAdapter: {e}")
    DoubaoAdapter = None

try:
    from .chatgpt_adapter import ChatGPTAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import ChatGPTAdapter: {e}")
    ChatGPTAdapter = None

try:
    from .gemini_adapter import GeminiAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import GeminiAdapter: {e}")
    GeminiAdapter = None

try:
    from .zhipu_adapter import ZhipuAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import ZhipuAdapter: {e}")
    ZhipuAdapter = None


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
        if adapter_class:
            cls._adapters[platform_type] = adapter_class
            api_logger.info(f"Registered adapter for {platform_type.value}")
        else:
            api_logger.warning(f"Skipping registration for {platform_type.value}: Adapter class is None")

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

# Register default providers
if DeepSeekAdapter:
    AIAdapterFactory.register(AIPlatformType.DEEPSEEK, DeepSeekAdapter)
if QwenAdapter:
    AIAdapterFactory.register(AIPlatformType.QWEN, QwenAdapter)
if DoubaoAdapter:
    AIAdapterFactory.register(AIPlatformType.DOUBAO, DoubaoAdapter)
if ChatGPTAdapter:
    AIAdapterFactory.register(AIPlatformType.CHATGPT, ChatGPTAdapter)
if GeminiAdapter:
    AIAdapterFactory.register(AIPlatformType.GEMINI, GeminiAdapter)
if ZhipuAdapter:
    AIAdapterFactory.register(AIPlatformType.ZHIPU, ZhipuAdapter)
