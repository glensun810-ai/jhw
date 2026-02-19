"""
Configuration Manager - Centralized API Key Management
Provides secure access to API keys from environment variables
"""
from typing import Optional
from config import Config


class ConfigData:
    """配置数据类"""
    def __init__(self, api_key: str, default_model: Optional[str] = None, 
                 default_temperature: float = 0.7, default_max_tokens: int = 1000,
                 timeout: int = 60):
        self.api_key = api_key
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout = timeout


class ConfigurationManager:
    """
    配置管理器 - 统一管理 API 密钥和其他配置
    """

    @staticmethod
    def get_api_key(platform_name: str) -> Optional[str]:
        """
        根据平台名称获取 API 密钥

        Args:
            platform_name: 平台名称 (e.g., 'deepseek', 'doubao', 'qwen')

        Returns:
            API 密钥字符串或 None
        """
        return Config.get_api_key(platform_name)

    @staticmethod
    def is_platform_configured(platform_name: str) -> bool:
        """
        检查指定平台是否已配置 API 密钥

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
            默认模型名称或 None
        """
        platform_models = {
            'deepseek': 'deepseek-chat',
            'deepseekr1': 'deepseek-chat',  # deepseekr1 使用相同的默认模型
            # 2026 年 2 月 19 日更新：使用新的豆包部署点 ID
            'doubao': 'ep-20260212000000-gd5tq',
            'qwen': 'qwen-max',
            'kimi': 'kimi-large',
            'chatgpt': 'gpt-4',
            'gemini': 'gemini-pro',
            'zhipu': 'glm-4',
            'wenxin': 'ernie-bot-4.5'
        }
        return platform_models.get(platform_name.lower())

    @staticmethod
    def get_platform_config(platform_name: str) -> Optional[ConfigData]:
        """
        获取平台完整配置

        Args:
            platform_name: 平台名称

        Returns:
            ConfigData 对象或 None
        """
        api_key = Config.get_api_key(platform_name)
        if not api_key:
            return None
        
        model = ConfigurationManager.get_platform_model(platform_name)
        return ConfigData(api_key=api_key, default_model=model)


# Create a singleton instance
config_manager = ConfigurationManager()
