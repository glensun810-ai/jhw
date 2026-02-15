"""
Configuration Manager - Centralized API Key Management
Provides secure access to API keys from environment variables
"""
from typing import Optional
from config import Config


class ConfigurationManager:
    """
    配置管理器 - 统一管理API密钥和其他配置
    """
    
    @staticmethod
    def get_api_key(platform_name: str) -> Optional[str]:
        """
        根据平台名称获取API密钥
        
        Args:
            platform_name: 平台名称 (e.g., 'deepseek', 'doubao', 'qwen')
            
        Returns:
            API密钥字符串或None
        """
        return Config.get_api_key(platform_name)
    
    @staticmethod
    def is_platform_configured(platform_name: str) -> bool:
        """
        检查指定平台是否已配置API密钥
        
        Args:
            platform_name: 平台名称
            
        Returns:
            bool: 平台是否已配置
        """
        return Config.is_api_key_configured(platform_name)
    
    @staticmethod
    def get_platform_model(platform_name: str) -> Optional[str]:
        """
        获取平台的默认模型名称
        
        Args:
            platform_name: 平台名称
            
        Returns:
            默认模型名称或None
        """
        platform_models = {
            'deepseek': 'deepseek-chat',
            'deepseekr1': 'deepseek-chat',  # deepseekr1 使用相同的默认模型
            'doubao': 'doubao-lite',
            'qwen': 'qwen-max',
            'kimi': 'kimi-large',
            'chatgpt': 'gpt-4',
            'gemini': 'gemini-pro',
            'zhipu': 'glm-4',
            'wenxin': 'ernie-bot-4.5'
        }
        return platform_models.get(platform_name.lower())


# Create a singleton instance
config_manager = ConfigurationManager()