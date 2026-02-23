"""
ProviderFactory - AI提供者工厂类
用于创建和管理不同AI平台的提供者实例
"""
from typing import Dict, Type
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.ai_adapters.doubao_provider import DoubaoProvider
from wechat_backend.ai_adapters.deepseek_provider import DeepSeekProvider
from wechat_backend.ai_adapters.qwen_provider import QwenProvider
from wechat_backend.logging_config import api_logger


class ProviderFactory:
    """
    AI提供者工厂类 - 根据平台类型创建相应的提供者实例
    """
    
    _providers: Dict[str, Type[BaseAIProvider]] = {}
    
    @classmethod
    def register(cls, platform_name: str, provider_class: Type[BaseAIProvider]):
        """
        注册AI提供者类
        
        Args:
            platform_name: 平台名称
            provider_class: 提供者类
        """
        cls._providers[platform_name] = provider_class
        api_logger.info(f"Registered provider for platform: {platform_name}")
    
    @classmethod
    def create(cls, platform_name: str, api_key: str, model_name: str = None, **kwargs) -> BaseAIProvider:
        """
        创建AI提供者实例
        
        Args:
            platform_name: 平台名称
            api_key: API密钥
            model_name: 模型名称
            **kwargs: 其他参数
            
        Returns:
            BaseAIProvider: AI提供者实例
        """
        if platform_name not in cls._providers:
            raise ValueError(f"No provider registered for platform: {platform_name}")
        
        provider_class = cls._providers[platform_name]
        
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
        return list(cls._providers.keys())


# 注册默认提供者
ProviderFactory.register('doubao', DoubaoProvider)
ProviderFactory.register('deepseek', DeepSeekProvider)
ProviderFactory.register('qwen', QwenProvider)  # Register Qwen provider

api_logger.info("ProviderFactory initialized with default providers")