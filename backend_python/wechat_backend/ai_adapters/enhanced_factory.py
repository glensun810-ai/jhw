"""增强版AI适配器工厂"""
from typing import Dict, Type, Union, Optional
from wechat_backend.ai_adapters.base_adapter import AIClient, AIPlatformType
from wechat_backend.analytics.api_monitor import ApiMonitor
import random


class EnhancedAIAdapterFactory:
    """增强版AI适配器工厂"""
    
    _adapters: Dict[AIPlatformType, Type[AIClient]] = {}
    _monitor = ApiMonitor()
    
    @classmethod
    def register(cls, platform_type: AIPlatformType, adapter_class: Type[AIClient]):
        """注册适配器"""
        cls._adapters[platform_type] = adapter_class
    
    @classmethod
    def create(cls, platform_type: Union[AIPlatformType, str], 
               api_key: str, model_name: str, **kwargs) -> AIClient:
        """创建AI客户端，智能选择最佳配置"""
        if isinstance(platform_type, str):
            # 尝试将字符串转换为AIPlatformType
            platform_type = cls._str_to_platform_type(platform_type)
        
        if platform_type not in cls._adapters:
            raise ValueError(f"No adapter registered for platform: {platform_type}")
        
        # 检查API可用性
        platform_name = platform_type.value
        if not cls._monitor.check_api_availability(platform_name):
            # 如果当前平台不可用，尝试使用备用平台
            backup_platform = cls._get_backup_platform(platform_type)
            if backup_platform:
                platform_type = backup_platform
                platform_name = backup_platform.value
        
        adapter_class = cls._adapters[platform_type]
        return adapter_class(api_key, model_name, **kwargs)
    
    @classmethod
    def _str_to_platform_type(cls, platform_str: str) -> AIPlatformType:
        """将字符串转换为AIPlatformType"""
        platform_map = {
            'deepseek': AIPlatformType.DEEPSEEK,
            'doubao': AIPlatformType.DOUBAO,
            'yuanbao': AIPlatformType.YUANBAO,
            'qwen': AIPlatformType.QWEN,
            'wenxin': AIPlatformType.WENXIN,
            'kimi': AIPlatformType.KIMI,
            'chatgpt': AIPlatformType.CHATGPT,
            'claude': AIPlatformType.CLAUDE,
            'gemini': AIPlatformType.GEMINI,
            'spark': AIPlatformType.SPARK,
            'google': AIPlatformType.GOOGLE,
            'anthropic': AIPlatformType.ANTHROPIC,
            'openai': AIPlatformType.OPENAI
        }
        
        platform_lower = platform_str.lower()
        if platform_lower in platform_map:
            return platform_map[platform_lower]
        else:
            # 尝试直接匹配枚举值
            for platform_type in AIPlatformType:
                if platform_type.value == platform_lower:
                    return platform_type
            raise ValueError(f"Unknown platform type: {platform_str}")
    
    @classmethod
    def _get_backup_platform(cls, primary_platform: AIPlatformType) -> Optional[AIPlatformType]:
        """获取备用平台"""
        backup_mapping = {
            AIPlatformType.QWEN: [AIPlatformType.CHATGPT, AIPlatformType.GEMINI],
            AIPlatformType.CHATGPT: [AIPlatformType.QWEN, AIPlatformType.CLAUDE],
            AIPlatformType.DOUBAO: [AIPlatformType.QWEN, AIPlatformType.CHATGPT],
            AIPlatformType.DEEPSEEK: [AIPlatformType.CHATGPT, AIPlatformType.QWEN],
            AIPlatformType.CLAUDE: [AIPlatformType.CHATGPT, AIPlatformType.GEMINI],
            AIPlatformType.GEMINI: [AIPlatformType.CHATGPT, AIPlatformType.CLAUDE],
        }
        
        backups = backup_mapping.get(primary_platform, [])
        for backup in backups:
            if cls._monitor.check_api_availability(backup.value):
                return backup
        return None
    
    @classmethod
    def register_with_monitoring(cls, platform_type: AIPlatformType, 
                                adapter_class: Type[AIClient], 
                                config=None):
        """注册适配器并关联监控配置"""
        cls.register(platform_type, adapter_class)
        if config:
            cls._monitor.update_platform_config(platform_type.value, config)
    
    @classmethod
    def get_monitor(cls):
        """获取监控器实例"""
        return cls._monitor