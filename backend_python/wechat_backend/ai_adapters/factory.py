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
    from .deepseek_r1_adapter import DeepSeekR1Adapter
except ImportError as e:
    api_logger.warning(f"Failed to import DeepSeekR1Adapter: {e}")
    DeepSeekR1Adapter = None

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

try:
    from .erniebot_adapter import ErnieBotAdapter
except ImportError as e:
    api_logger.warning(f"Failed to import ErnieBotAdapter: {e}")
    ErnieBotAdapter = None


class AIAdapterFactory:
    """
    Factory class for creating AI adapters based on platform type.
    """

    # 名称映射引擎：在类中注入或更新映射表
    MODEL_NAME_MAP = {
        "豆包": "doubao",
        "doubao": "doubao",
        "doubao-pro": "doubao",
        "qwen": "qwen",
        "千问": "qwen",
        "通义千问": "qwen",
        "tongyi": "qwen",
        "aliyun-qwen": "qwen",
        "deepseek": "deepseek",
        "deepseekr1": "deepseekr1",
        "deepseek-r1": "deepseekr1",
        "文心一言": "wenxin",
        "wenxin": "wenxin",
        "ernie": "wenxin",
        "Kimi": "kimi",
        "月之暗面": "kimi",
        "moonshot": "kimi",
        "元宝": "yuanbao",
        "bytedance-yuanbao": "yuanbao",
        "讯飞星火": "spark",
        "xinghuo": "spark",
        "iFlytek": "spark",
        "智谱AI": "zhipu",
        "智谱": "zhipu",
        "zhipu": "zhipu",
        "chatglm": "zhipu",
        "OpenAI": "openai",
        "ChatGPT": "chatgpt",
        "GPT": "chatgpt",
        "Claude": "claude",
        "Anthropic": "claude",
        "Gemini": "gemini",
        "Google": "gemini",
        "Perplexity": "perplexity",
        "Grok": "grok",
        "xAI": "grok"
    }

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
    def get_normalized_model_name(cls, model_name: str) -> str:
        """
        将输入名称通过 MODEL_NAME_MAP 转换
        """
        # 检查是否为中文名称，如果是则转换为英文标识符
        if model_name in cls.MODEL_NAME_MAP:
            return cls.MODEL_NAME_MAP[model_name]
        elif model_name.title() in cls.MODEL_NAME_MAP:  # 检查首字母大写的版本
            return cls.MODEL_NAME_MAP[model_name.title()]
        elif model_name.lower() in cls.MODEL_NAME_MAP:  # 检查小写的版本
            return cls.MODEL_NAME_MAP[model_name.lower()]
        else:
            # 如果没有找到映射，返回原始名称的小写版本
            return model_name.lower()

    @classmethod
    def create(cls, platform_type: Union[AIPlatformType, str], api_key: str = None, model_name: str = None, **kwargs) -> AIClient:
        """
        Create an instance of an AI adapter for the specified platform
        If api_key is not provided, attempts to load from environment variables
        If model_name is not provided, uses platform-specific default
        """
        if isinstance(platform_type, str):
            # 先将输入名称通过 MODEL_NAME_MAP 转换
            normalized_platform_type = cls.get_normalized_model_name(platform_type)
            try:
                platform_type = AIPlatformType(normalized_platform_type)
            except ValueError:
                raise ValueError(f"Unknown platform type: {platform_type}")

        # 注入核心调试日志
        api_logger.error(f"REGISTERED_MODELS: {list(cls._adapters.keys())}")

        if platform_type not in cls._adapters:
            raise ValueError(f"No adapter registered for platform: {platform_type}")

        # If API key is not provided, try to get it from config
        if not api_key:
            from ..config_manager import config_manager
            api_key = config_manager.get_api_key(platform_type.value)
            if not api_key:
                raise ValueError(f"No API key provided or configured for platform: {platform_type.value}")

        # If model name is not provided, try to get default from config
        if not model_name:
            from ..config_manager import config_manager
            model_name = config_manager.get_platform_model(platform_type.value) or f"default-{platform_type.value}-model"

        adapter_class = cls._adapters[platform_type]
        return adapter_class(api_key, model_name, **kwargs)

# Register default providers
if DeepSeekAdapter:
    AIAdapterFactory.register(AIPlatformType.DEEPSEEK, DeepSeekAdapter)
if DeepSeekR1Adapter:
    AIAdapterFactory.register(AIPlatformType.DEEPSEEKR1, DeepSeekR1Adapter)  # New R1 adapter
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
if ErnieBotAdapter:
    AIAdapterFactory.register(AIPlatformType.WENXIN, ErnieBotAdapter)

# 添加日志，显示当前注册的模型
api_logger.info(f"Current Registered Models: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
print(f"Current Registered Models: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
