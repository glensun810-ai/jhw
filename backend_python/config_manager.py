"""
配置管理器 - 修复版本
用于管理各个AI平台的配置信息，不依赖外部Config类
"""

import os
from typing import Optional


class PlatformConfig:
    """单个平台的配置"""

    def __init__(self, api_key: str, default_model: Optional[str] = None,
                 timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries


class Config:
    """配置管理器 - 修复版本，只使用环境变量"""

    def __init__(self):
        self.platform_configs = {}
        # 不再加载配置，直接使用环境变量

    def get_platform_config(self, platform_name: str):
        """获取平台配置，直接从环境变量获取"""
        # 映射平台名称到环境变量
        platform_env_map = {
            'doubao': 'DOUBAO_API_KEY',
            '豆包': 'DOUBAO_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'DeepSeek': 'DEEPSEEK_API_KEY',
            'qwen': 'QWEN_API_KEY',
            '通义千问': 'QWEN_API_KEY',
            'chatgpt': 'CHATGPT_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'zhipu': 'ZHIPU_API_KEY',
            '智谱AI': 'ZHIPU_API_KEY',
            'wenxin': 'WENXIN_API_KEY',
        }
        
        env_var = platform_env_map.get(platform_name)
        if env_var:
            api_key = os.getenv(env_var, '')
            if api_key:
                return PlatformConfig(api_key=api_key)
        return None

    def get_api_key(self, platform_name: str) -> Optional[str]:
        """获取API密钥"""
        config = self.get_platform_config(platform_name)
        return config.api_key if config else None

    def is_platform_configured(self, platform_name: str) -> bool:
        """检查平台是否已配置"""
        config = self.get_platform_config(platform_name)
        return config is not None and bool(config.api_key)