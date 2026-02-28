"""
ProviderFactory - AI 提供者工厂类
用于创建和管理不同 AI 平台的提供者实例

修复说明：
- 添加所有国内和海外平台的 provider 注册
- 添加配置验证，确保 API key 配置后才注册
- 添加详细的日志记录，便于诊断
- 防止平台消失的复发保护机制
"""
from typing import Dict, Type, List
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.ai_adapters.doubao_provider import DoubaoProvider
from wechat_backend.ai_adapters.deepseek_provider import DeepSeekProvider
from wechat_backend.ai_adapters.qwen_provider import QwenProvider
from wechat_backend.ai_adapters.overseas_providers import (
    ChatGPTProvider,
    GeminiProvider,
    ZhipuProvider,
    WenxinProvider
)
from wechat_backend.logging_config import api_logger

# 导入配置用于 API key 验证
import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from legacy_config import Config


class ProviderFactory:
    """
    AI 提供者工厂类 - 根据平台类型创建相应的提供者实例
    
    支持的平台：
    - 国内平台：豆包 (doubao)、DeepSeek (deepseek)、通义千问 (qwen)
    - 海外平台：ChatGPT (chatgpt)、Gemini (gemini)、智谱 AI (zhipu)、文心一言 (wenxin)
    """

    _providers: Dict[str, Type[BaseAIProvider]] = {}
    _initialized = False
    _initialization_errors: List[str] = []

    @classmethod
    def initialize(cls, force: bool = False):
        """
        初始化 provider 注册
        
        Args:
            force: 是否强制重新初始化（用于配置更新后重新加载）
        
        只在第一次调用时执行，避免重复注册（除非 force=True）
        """
        if cls._initialized and not force:
            return
        
        cls._initialized = True
        cls._initialization_errors = []
        
        api_logger.info("=== Starting Provider Registration ===")
        api_logger.info(f"Configuration check: Config class available = {Config is not None}")
        
        # 国内平台
        cls._register_with_key_check('doubao', DoubaoProvider, '豆包/Doubao')
        cls._register_with_key_check('deepseek', DeepSeekProvider, 'DeepSeek')
        cls._register_with_key_check('qwen', QwenProvider, '通义千问/Qwen')
        
        # 海外平台
        cls._register_with_key_check('chatgpt', ChatGPTProvider, 'ChatGPT/OpenAI')
        cls._register_with_key_check('gemini', GeminiProvider, 'Gemini/Google')
        cls._register_with_key_check('zhipu', ZhipuProvider, '智谱 AI/Zhipu')
        cls._register_with_key_check('wenxin', WenxinProvider, '文心一言/Wenxin')
        
        # 输出注册统计
        registered_count = len(cls._providers)
        total_platforms = 7  # 总共 7 个平台
        
        api_logger.info(f"=== Provider Registration Complete ===")
        api_logger.info(f"Registered: {registered_count}/{total_platforms} providers")
        api_logger.info(f"Registered providers: {sorted(cls._providers.keys())}")
        
        if registered_count == 0:
            error_msg = "⚠️  WARNING: No providers registered! Check API key configuration."
            api_logger.error(error_msg)
            cls._initialization_errors.append(error_msg)
        elif registered_count < total_platforms:
            api_logger.warning(f"⚠️  Some providers not registered. Missing: {cls._get_missing_providers()}")
        else:
            api_logger.info(f"✅ All {registered_count} providers registered successfully!")

    @classmethod
    def _get_missing_providers(cls) -> List[str]:
        """获取未注册的提供者列表"""
        all_platforms = ['doubao', 'deepseek', 'qwen', 'chatgpt', 'gemini', 'zhipu', 'wenxin']
        return [p for p in all_platforms if p not in cls._providers]

    @classmethod
    def _register_with_key_check(cls, platform_name: str, provider_class: Type[BaseAIProvider], platform_display: str):
        """
        检查 API key 配置后注册 provider
        
        Args:
            platform_name: 平台名称（内部标识）
            provider_class: 提供者类（如果为 None，则跳过注册）
            platform_display: 平台显示名称（用于日志）
        """
        # 检查 provider 类是否存在
        if provider_class is None:
            error_msg = f"⚠️  Provider NOT registered for '{platform_name}' ({platform_display}): Provider class not implemented"
            api_logger.warning(error_msg)
            cls._initialization_errors.append(error_msg)
            return
        
        # 检查 API key 是否配置
        api_key_configured = Config.is_api_key_configured(platform_name)
        
        if not api_key_configured:
            # 获取 API key 配置状态的详细信息
            api_key = cls._get_api_key_for_debug(platform_name)
            error_msg = f"⚠️  Provider NOT registered for '{platform_name}' ({platform_display}): API key not configured (value: '{api_key[:10] if api_key else 'EMPTY'}...')"
            api_logger.warning(error_msg)
            cls._initialization_errors.append(error_msg)
            return
        
        # 注册 provider
        cls.register(platform_name, provider_class)
        api_logger.info(f"✅ Provider registered for '{platform_name}' ({platform_display})")

    @classmethod
    def _get_api_key_for_debug(cls, platform_name: str) -> str:
        """获取 API key 用于调试（脱敏）"""
        try:
            api_key = Config.get_api_key(platform_name)
            if api_key:
                # 脱敏处理：只显示前 3 个和后 3 个字符
                if len(api_key) > 10:
                    return api_key[:3] + "***" + api_key[-3:]
                return "***"
            return ""
        except Exception:
            return "ERROR_GETTING_KEY"

    @classmethod
    def register(cls, platform_name: str, provider_class: Type[BaseAIProvider]):
        """
        注册 AI 提供者类

        Args:
            platform_name: 平台名称
            provider_class: 提供者类
        """
        cls._providers[platform_name] = provider_class
        api_logger.info(f"Registered provider for platform: {platform_name}")

    @classmethod
    def create(cls, platform_name: str, api_key: str = None, model_name: str = None, **kwargs) -> BaseAIProvider:
        """
        创建 AI 提供者实例

        Args:
            platform_name: 平台名称
            api_key: API 密钥（可选，如果不提供则从配置读取）
            model_name: 模型名称
            **kwargs: 其他参数

        Returns:
            BaseAIProvider: AI 提供者实例
        """
        # 确保已初始化
        cls.initialize()
        
        if platform_name not in cls._providers:
            available = list(cls._providers.keys())
            error_msg = f"No provider registered for platform: {platform_name}. Available: {available}"
            api_logger.error(error_msg)
            raise ValueError(error_msg)

        provider_class = cls._providers[platform_name]

        # 如果 API key 未提供，从配置获取
        if not api_key:
            api_key = Config.get_api_key(platform_name)
            if not api_key:
                error_msg = f"No API key provided or configured for platform: {platform_name}"
                api_logger.error(error_msg)
                raise ValueError(error_msg)

        # 如果模型名称未指定，使用提供者的默认值
        if model_name is None:
            return provider_class(api_key=api_key, **kwargs)
        else:
            return provider_class(api_key=api_key, model_name=model_name, **kwargs)

    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的提供者

        Returns:
            list: 可用提供者列表
        """
        # 确保已初始化
        cls.initialize()
        return sorted(list(cls._providers.keys()))

    @classmethod
    def get_provider_info(cls) -> Dict[str, Dict[str, str]]:
        """
        获取所有 provider 的详细信息（用于诊断）

        Returns:
            Dict: provider 信息字典
        """
        cls.initialize()
        info = {}
        for platform_name in sorted(cls._providers.keys()):
            has_key = Config.is_api_key_configured(platform_name)
            info[platform_name] = {
                'registered': True,
                'api_key_configured': has_key,
                'status': 'available' if has_key else 'api_key_missing',
                'provider_class': cls._providers[platform_name].__name__
            }
        
        # 添加未注册的平台信息
        all_platforms = ['doubao', 'deepseek', 'qwen', 'chatgpt', 'gemini', 'zhipu', 'wenxin']
        for platform in all_platforms:
            if platform not in info:
                has_key = Config.is_api_key_configured(platform)
                info[platform] = {
                    'registered': False,
                    'api_key_configured': has_key,
                    'status': 'not_registered',
                    'provider_class': 'N/A'
                }
        
        return info

    @classmethod
    def get_initialization_status(cls) -> Dict[str, any]:
        """
        获取初始化状态（用于健康检查）

        Returns:
            Dict: 初始化状态信息
        """
        return {
            'initialized': cls._initialized,
            'provider_count': len(cls._providers),
            'providers': cls.get_available_providers(),
            'errors': cls._initialization_errors,
            'healthy': len(cls._providers) > 0
        }


# 自动初始化
try:
    ProviderFactory.initialize()
    api_logger.info(f"ProviderFactory initialized with providers: {ProviderFactory.get_available_providers()}")
except Exception as e:
    api_logger.error(f"ProviderFactory initialization failed: {e}")
    import traceback
    api_logger.error(f"Traceback: {traceback.format_exc()}")
