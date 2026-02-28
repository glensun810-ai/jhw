"""
ProviderFactory - AI 提供者工厂类 (src/adapters 版本)
用于创建和管理不同 AI 平台的提供者实例

注意：这是 src/adapters 目录下的 provider 工厂，主要用于向后兼容
主要使用 wechat_backend/ai_adapters/provider_factory.py

修复说明：
- 添加所有国内和海外平台的 provider 注册
- 添加配置验证，确保 API key 配置后才注册
- 添加详细的日志记录，便于诊断
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
        """
        if cls._initialized and not force:
            return
        
        cls._initialized = True
        cls._initialization_errors = []
        
        api_logger.info("=== Starting Provider Registration (src/adapters) ===")
        
        # 国内平台
        cls._register_with_key_check('doubao', DoubaoProvider, '豆包/Doubao')
        cls._register_with_key_check('deepseek', DeepSeekProvider, 'DeepSeek')
        cls._register_with_key_check('qwen', QwenProvider, '通义千问/Qwen')
        
        # 海外平台
        cls._register_with_key_check('chatgpt', ChatGPTProvider, 'ChatGPT/OpenAI')
        cls._register_with_key_check('gemini', GeminiProvider, 'Gemini/Google')
        cls._register_with_key_check('zhipu', ZhipuProvider, '智谱 AI/Zhipu')
        cls._register_with_key_check('wenxin', WenxinProvider, '文心一言/Wenxin')
        
        api_logger.info(f"=== Provider Registration Complete: {len(cls._providers)} providers ===")
        api_logger.info(f"Registered providers: {sorted(cls._providers.keys())}")

    @classmethod
    def _register_with_key_check(cls, platform_name: str, provider_class: Type[BaseAIProvider], platform_display: str):
        """检查 API key 配置后注册 provider"""
        if provider_class is None:
            api_logger.warning(f"⚠️  Provider NOT registered for '{platform_name}' ({platform_display}): Class not implemented")
            return
        
        if not Config.is_api_key_configured(platform_name):
            api_logger.warning(f"⚠️  Provider NOT registered for '{platform_name}' ({platform_display}): API key not configured")
            return
        
        cls.register(platform_name, provider_class)
        api_logger.info(f"✅ Provider registered for '{platform_name}' ({platform_display})")

    @classmethod
    def register(cls, platform_name: str, provider_class: Type[BaseAIProvider]):
        """注册 AI 提供者类"""
        cls._providers[platform_name] = provider_class
        api_logger.info(f"Registered provider for platform: {platform_name}")

    @classmethod
    def create(cls, platform_name: str, api_key: str = None, model_name: str = None, **kwargs) -> BaseAIProvider:
        """创建 AI 提供者实例"""
        cls.initialize()
        
        if platform_name not in cls._providers:
            raise ValueError(f"No provider registered for platform: {platform_name}. Available: {list(cls._providers.keys())}")

        provider_class = cls._providers[platform_name]

        if not api_key:
            api_key = Config.get_api_key(platform_name)
            if not api_key:
                raise ValueError(f"No API key configured for platform: {platform_name}")

        if model_name is None:
            return provider_class(api_key=api_key, **kwargs)
        else:
            return provider_class(api_key=api_key, model_name=model_name, **kwargs)

    @classmethod
    def get_available_providers(cls) -> list:
        """获取所有可用的提供者"""
        cls.initialize()
        return sorted(list(cls._providers.keys()))

    @classmethod
    def get_provider_info(cls) -> Dict[str, Dict[str, str]]:
        """获取所有 provider 的详细信息"""
        cls.initialize()
        info = {}
        for platform_name in cls._providers.keys():
            has_key = Config.is_api_key_configured(platform_name)
            info[platform_name] = {
                'registered': True,
                'api_key_configured': has_key,
                'status': 'available' if has_key else 'api_key_missing'
            }
        return info


# 自动初始化
ProviderFactory.initialize()
api_logger.info(f"ProviderFactory (src/adapters) initialized with providers: {ProviderFactory.get_available_providers()}")
