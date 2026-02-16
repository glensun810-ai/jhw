"""
配置管理器
用于管理各个AI平台的配置信息
"""

import os
from typing import Optional, Dict, Any


class PlatformConfig:
    """单个平台的配置"""

    def __init__(self, api_key: str, default_model: Optional[str] = None,
                 timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries


def _get_config_attr(attr_name: str, default: str = ''):
    """安全获取配置属性，只从环境变量获取 - FIXED VERSION 2026-02-16"""
    # 只使用环境变量，避免模块导入问题
    env_value = os.getenv(attr_name)
    if env_value:
        return env_value
    return default


class Config:
    """配置管理器"""

    def __init__(self):
        self.platform_configs = {}
        self._load_configs()

    def _load_configs(self):
        """从环境变量加载配置"""
        # 豆包配置
        doubao_api_key = _get_config_attr('DOUBAO_API_KEY')
        if doubao_api_key:
            self.platform_configs['doubao'] = PlatformConfig(
                api_key=doubao_api_key,
                default_model=os.getenv('DOUBAO_MODEL_ID') or 'ep-default-model'
            )

        # DeepSeek配置
        deepseek_api_key = _get_config_attr('DEEPSEEK_API_KEY')
        if deepseek_api_key:
            self.platform_configs['deepseek'] = PlatformConfig(
                api_key=deepseek_api_key,
                default_model=os.getenv('DEEPSEEK_MODEL_ID') or 'deepseek-chat'
            )

        # 通义千问配置
        qwen_api_key = _get_config_attr('QWEN_API_KEY')
        if qwen_api_key:
            self.platform_configs['qwen'] = PlatformConfig(
                api_key=qwen_api_key,
                default_model=os.getenv('QWEN_MODEL_ID') or 'qwen-max'
            )

        # ChatGPT配置
        chatgpt_api_key = _get_config_attr('CHATGPT_API_KEY')
        if chatgpt_api_key:
            self.platform_configs['chatgpt'] = PlatformConfig(
                api_key=chatgpt_api_key,
                default_model=os.getenv('CHATGPT_MODEL_ID') or 'gpt-4'
            )

        # Gemini配置
        gemini_api_key = _get_config_attr('GEMINI_API_KEY')
        if gemini_api_key:
            self.platform_configs['gemini'] = PlatformConfig(
                api_key=gemini_api_key,
                default_model=os.getenv('GEMINI_MODEL_ID') or 'gemini-pro'
            )

        # 智谱AI配置
        zhipu_api_key = _get_config_attr('ZHIPU_API_KEY')
        if zhipu_api_key:
            self.platform_configs['zhipu'] = PlatformConfig(
                api_key=zhipu_api_key,
                default_model=os.getenv('ZHIPU_MODEL_ID') or 'glm-4'
            )

        # 文心一言配置
        wenxin_api_key = _get_config_attr('WENXIN_API_KEY')
        if wenxin_api_key:
            self.platform_configs['wenxin'] = PlatformConfig(
                api_key=wenxin_api_key,
                default_model=os.getenv('WENXIN_MODEL_ID') or 'ernie-bot'
            )
    
    def get_platform_config(self, platform_name: str) -> Optional[PlatformConfig]:
        """获取指定平台的配置"""
        return self.platform_configs.get(platform_name.lower())
    
    def get_api_key(self, platform_name: str) -> Optional[str]:
        """获取指定平台的API密钥"""
        config = self.get_platform_config(platform_name)
        return config.api_key if config else None
    
    def get_platform_model(self, platform_name: str) -> Optional[str]:
        """获取指定平台的默认模型"""
        config = self.get_platform_config(platform_name)
        return config.default_model if config else None
    
    def is_platform_configured(self, platform_name: str) -> bool:
        """检查平台是否已配置"""
        config = self.get_platform_config(platform_name)
        return config is not None and bool(config.api_key)
    
    def add_platform_config(self, platform_name: str, config: PlatformConfig):
        """添加平台配置"""
        self.platform_configs[platform_name.lower()] = config
    
    def update_platform_config(self, platform_name: str, api_key: str = None, 
                              default_model: str = None, timeout: int = None, 
                              max_retries: int = None):
        """更新平台配置"""
        platform_name = platform_name.lower()
        if platform_name in self.platform_configs:
            existing_config = self.platform_configs[platform_name]
            self.platform_configs[platform_name] = PlatformConfig(
                api_key=api_key or existing_config.api_key,
                default_model=default_model or existing_config.default_model,
                timeout=timeout or existing_config.timeout,
                max_retries=max_retries or existing_config.max_retries
            )
        else:
            self.platform_configs[platform_name] = PlatformConfig(
                api_key=api_key or '',
                default_model=default_model,
                timeout=timeout or 30,
                max_retries=max_retries or 3
            )