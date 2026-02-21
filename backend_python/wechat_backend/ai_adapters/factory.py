"""
Factory for creating and managing AI adapters
"""
from typing import Dict, Type, Union
from wechat_backend.ai_adapters.base_adapter import AIClient, AIPlatformType
from wechat_backend.logging_config import api_logger

api_logger.info("=== Starting AI Adapter Imports ===")

# 动态导入适配器，防止单个适配器的依赖问题导致整个应用崩溃
try:
    from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
    api_logger.info("Successfully imported DeepSeekAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import DeepSeekAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for DeepSeekAdapter import error: {traceback.format_exc()}")
    DeepSeekAdapter = None

try:
    from .deepseek_r1_adapter import DeepSeekR1Adapter
    api_logger.info("Successfully imported DeepSeekR1Adapter")
except ImportError as e:
    api_logger.error(f"Failed to import DeepSeekR1Adapter: {e}")
    import traceback
    api_logger.error(f"Traceback for DeepSeekR1Adapter import error: {traceback.format_exc()}")
    DeepSeekR1Adapter = None

try:
    from wechat_backend.ai_adapters.qwen_adapter import QwenAdapter
    api_logger.info("Successfully imported QwenAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import QwenAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for QwenAdapter import error: {traceback.format_exc()}")
    QwenAdapter = None

try:
    from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
    api_logger.info("Successfully imported DoubaoAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import DoubaoAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for DoubaoAdapter import error: {traceback.format_exc()}")
    DoubaoAdapter = None

try:
    from .chatgpt_adapter import ChatGPTAdapter
    api_logger.info("Successfully imported ChatGPTAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import ChatGPTAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for ChatGPTAdapter import error: {traceback.format_exc()}")
    ChatGPTAdapter = None

try:
    from .gemini_adapter import GeminiAdapter
    api_logger.info("Successfully imported GeminiAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import GeminiAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for GeminiAdapter import error: {traceback.format_exc()}")
    GeminiAdapter = None

try:
    from wechat_backend.ai_adapters.zhipu_adapter import ZhipuAdapter
    api_logger.info("Successfully imported ZhipuAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import ZhipuAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for ZhipuAdapter import error: {traceback.format_exc()}")
    ZhipuAdapter = None

try:
    from .erniebot_adapter import ErnieBotAdapter
    api_logger.info("Successfully imported ErnieBotAdapter")
except ImportError as e:
    api_logger.error(f"Failed to import ErnieBotAdapter: {e}")
    import traceback
    api_logger.error(f"Traceback for ErnieBotAdapter import error: {traceback.format_exc()}")
    ErnieBotAdapter = None

api_logger.info("=== Completed AI Adapter Imports ===")


class AIAdapterFactory:
    """
    Factory class for creating AI adapters based on platform type.
    """

    # 名称映射引擎：在类中注入或更新映射表
    MODEL_NAME_MAP = {
        "豆包": "doubao",
        "doubao": "doubao",
        "doubao-pro": "doubao",
        "doubao-cn": "doubao",  # 添加额外的豆包映射
        "Doubao": "doubao",     # 添加大小写变体
        "DOUBAO": "doubao",
        "doubao-pro-5b": "doubao",
        "doubao-pro-7b": "doubao",
        # 豆包平台映射（2026 年 2 月 19 日更新：使用新部署点）
        "ep-20260212000000-gd5tq": "doubao",
        "doubao-pro": "doubao",
        "qwen": "qwen",
        "千问": "qwen",
        "通义千问": "qwen",
        "tongyi": "qwen",
        "aliyun-qwen": "qwen",
        "qwen-max": "qwen",
        "qwen-plus": "qwen",
        "qwen-turbo": "qwen",
        "deepseek": "deepseek",  # 修正：将deepseek映射回自身，而不是deepseekr1
        "deepseek-chat": "deepseek",  # 添加具体的deepseek模型映射
        "deepseek-coder": "deepseek",
        "deepseekr1": "deepseekr1",
        "deepseek-r1": "deepseekr1",
        "deepseek-r1-distill": "deepseekr1",
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
        "glm-4": "zhipu",
        "glm-4-air": "zhipu",
        "glm-4-plus": "zhipu",
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
        # 首先尝试精确匹配
        if model_name in cls.MODEL_NAME_MAP:
            return cls.MODEL_NAME_MAP[model_name]
        elif model_name.title() in cls.MODEL_NAME_MAP:
            return cls.MODEL_NAME_MAP[model_name.title()]
        elif model_name.lower() in cls.MODEL_NAME_MAP:
            return cls.MODEL_NAME_MAP[model_name.lower()]
        else:
            # 如果没有精确匹配，尝试模糊匹配
            lower_model_name = model_name.lower()
            for key, value in cls.MODEL_NAME_MAP.items():
                if lower_model_name in key.lower() or key.lower() in lower_model_name:
                    api_logger.info(f"Fuzzy match found for '{model_name}' -> '{key}' -> '{value}'")
                    return value
            # 如果没有找到映射，返回原始名称的小写版本
            return model_name.lower()

    @classmethod
    def is_platform_available(cls, platform_type: Union[AIPlatformType, str]) -> bool:
        """
        检查平台是否可用（已注册且API密钥已配置）
        """
        if isinstance(platform_type, str):
            # 先将输入名称通过 MODEL_NAME_MAP 转换
            normalized_platform_type = cls.get_normalized_model_name(platform_type)
            try:
                platform_type = AIPlatformType(normalized_platform_type)
            except ValueError:
                return False
        
        return platform_type in cls._adapters

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
            from config_manager import config_manager
            api_key = config_manager.get_api_key(platform_type.value)
            if not api_key:
                raise ValueError(f"No API key provided or configured for platform: {platform_type.value}")

        # If model name is not provided, try to get default from config
        if not model_name:
            from config_manager import config_manager
            model_name = config_manager.get_platform_model(platform_type.value) or f"default-{platform_type.value}-model"

        adapter_class = cls._adapters[platform_type]
        return adapter_class(api_key, model_name, **kwargs)

# Debug logging for adapter availability
api_logger.info("=== Adapter Registration Debug Info ===")
api_logger.info(f"DeepSeekAdapter status: {DeepSeekAdapter is not None}")
api_logger.info(f"DeepSeekR1Adapter status: {DeepSeekR1Adapter is not None}")
api_logger.info(f"QwenAdapter status: {QwenAdapter is not None}")
api_logger.info(f"DoubaoAdapter status: {DoubaoAdapter is not None}")
api_logger.info(f"ChatGPTAdapter status: {ChatGPTAdapter is not None}")
api_logger.info(f"GeminiAdapter status: {GeminiAdapter is not None}")
api_logger.info(f"ZhipuAdapter status: {ZhipuAdapter is not None}")
api_logger.info(f"ErnieBotAdapter status: {ErnieBotAdapter is not None}")

# Register default providers
if DeepSeekAdapter:
    api_logger.info("Registering DeepSeekAdapter")
    AIAdapterFactory.register(AIPlatformType.DEEPSEEK, DeepSeekAdapter)
else:
    api_logger.warning("NOT registering DeepSeekAdapter - it is None or failed to import")

if DeepSeekR1Adapter:
    api_logger.info("Registering DeepSeekR1Adapter")
    AIAdapterFactory.register(AIPlatformType.DEEPSEEKR1, DeepSeekR1Adapter)  # New R1 adapter
else:
    api_logger.warning("NOT registering DeepSeekR1Adapter - it is None or failed to import")

if QwenAdapter:
    api_logger.info("Registering QwenAdapter")
    AIAdapterFactory.register(AIPlatformType.QWEN, QwenAdapter)
else:
    api_logger.warning("NOT registering QwenAdapter - it is None or failed to import")

if DoubaoAdapter:
    api_logger.info("Registering DoubaoAdapter")
    AIAdapterFactory.register(AIPlatformType.DOUBAO, DoubaoAdapter)
else:
    api_logger.warning("NOT registering DoubaoAdapter - it is None or failed to import")

if ChatGPTAdapter:
    api_logger.info("Registering ChatGPTAdapter")
    AIAdapterFactory.register(AIPlatformType.CHATGPT, ChatGPTAdapter)
else:
    api_logger.warning("NOT registering ChatGPTAdapter - it is None or failed to import")

if GeminiAdapter:
    api_logger.info("Registering GeminiAdapter")
    AIAdapterFactory.register(AIPlatformType.GEMINI, GeminiAdapter)
else:
    api_logger.warning("NOT registering GeminiAdapter - it is None or failed to import")

if ZhipuAdapter:
    api_logger.info("Registering ZhipuAdapter")
    AIAdapterFactory.register(AIPlatformType.ZHIPU, ZhipuAdapter)
else:
    api_logger.warning("NOT registering ZhipuAdapter - it is None or failed to import")

if ErnieBotAdapter:
    api_logger.info("Registering ErnieBotAdapter")
    AIAdapterFactory.register(AIPlatformType.WENXIN, ErnieBotAdapter)
else:
    api_logger.warning("NOT registering ErnieBotAdapter - it is None or failed to import")

# Final debug logging
api_logger.info(f"Final registered models: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
api_logger.info("=== End Adapter Registration Debug Info ===")

# 添加日志，显示当前注册的模型
api_logger.info(f"Current Registered Models: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
print(f"Current Registered Models: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
