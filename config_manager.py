import os
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PlatformConfig:
    """单个AI平台的配置"""
    api_key: str
    base_url: Optional[str] = None
    default_temperature: float = 0.7
    default_max_tokens: int = 1000
    timeout: int = 30  # 请求超时时间（秒）
    retry_times: int = 3  # 重试次数


class Config:
    """多AI平台系统配置管理类"""

    def __init__(self):
        # 初始化平台配置字典
        self.platforms: Dict[str, PlatformConfig] = {}

        # 从环境变量加载配置
        self._load_from_env()

    def _load_from_env(self):
        """从环境变量加载配置"""
        # 支持的平台列表
        supported_platforms = [
            'openai', 'qwen', 'anthropic', 'google', 'chatgpt', 'deepseek', 'doubao',
            'gemini', 'wenxin', 'kimi', 'yuanbao', 'spark', 'zhipu'
        ]  # 添加更多平台

        for platform in supported_platforms:
            api_key = os.getenv(f'{platform.upper()}_API_KEY')
            if api_key:
                base_url = os.getenv(f'{platform.upper()}_BASE_URL')
                temperature = float(os.getenv(f'{platform.upper()}_TEMPERATURE', 0.7))
                max_tokens = int(os.getenv(f'{platform.upper()}_MAX_TOKENS', 1000))
                timeout = int(os.getenv(f'{platform.upper()}_TIMEOUT', 30))
                retry_times = int(os.getenv(f'{platform.upper()}_RETRY_TIMES', 3))

                self.platforms[platform] = PlatformConfig(
                    api_key=api_key,
                    base_url=base_url,
                    default_temperature=temperature,
                    default_max_tokens=max_tokens,
                    timeout=timeout,
                    retry_times=retry_times
                )

    def get_platform_config(self, platform_name: str) -> Optional[PlatformConfig]:
        """获取指定平台的配置"""
        return self.platforms.get(platform_name)

    def add_platform(self, platform_name: str, config: PlatformConfig):
        """添加新平台配置"""
        self.platforms[platform_name] = config

    def validate_keys(self) -> Dict[str, bool]:
        """验证所有已配置平台的API密钥是否有效"""
        validation_results = {}
        for platform_name, config in self.platforms.items():
            validation_results[platform_name] = bool(config.api_key.strip())
        return validation_results

    def check_missing_keys(self) -> list:
        """检查缺失的API密钥"""
        missing_keys = []
        for platform_name, config in self.platforms.items():
            if not config.api_key.strip():
                missing_keys.append(platform_name)
        return missing_keys

    def get_available_platforms(self) -> list:
        """获取所有已配置的平台名称"""
        return list(self.platforms.keys())