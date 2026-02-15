import os
from typing import Optional


class Config:
    # WeChat Mini Program Configuration
    WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID') or ''
    WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET') or ''
    WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN') or ''

    # Server Configuration
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''

    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'  # 默认日志文件
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB default
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))

    # WeChat API Endpoints
    WECHAT_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_CODE_TO_SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
    WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_SEND_TEMPLATE_MSG_URL = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send'

    # AI Platform API Keys
    DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY') or ''
    DOUBAO_MODEL_ID = os.environ.get('DOUBAO_MODEL_ID') or 'ep-default-model'

    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY') or ''
    QWEN_API_KEY = os.environ.get('QWEN_API_KEY') or ''
    KIMI_API_KEY = os.environ.get('KIMI_API_KEY') or ''

    # Optional API Keys for other platforms
    CHATGPT_API_KEY = os.environ.get('CHATGPT_API_KEY') or ''
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or ''
    ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY') or ''
    WENXIN_API_KEY = os.environ.get('WENXIN_API_KEY') or ''

    @classmethod
    def get_api_key(cls, platform: str) -> Optional[str]:
        """
        根据平台名称获取对应的API密钥

        Args:
            platform: 平台名称

        Returns:
            API密钥或None
        """
        # 平台别名映射，处理不同的平台名称变体
        platform_aliases = {
            '豆包': 'doubao',
            'doubao-cn': 'doubao',
            'Doubao': 'doubao',
            'DOUBAO': 'doubao',
            'deepseekr1': 'deepseek',
            'deepseek-r1': 'deepseek',
        }
        
        # 检查是否是别名，如果是则转换为主名称
        normalized_platform = platform_aliases.get(platform.lower(), platform.lower())
        
        platform_keys = {
            'doubao': cls.DOUBAO_API_KEY,
            'deepseek': cls.DEEPSEEK_API_KEY,
            'qwen': cls.QWEN_API_KEY,
            'kimi': cls.KIMI_API_KEY,
            'chatgpt': cls.CHATGPT_API_KEY,
            'gemini': cls.GEMINI_API_KEY,
            'zhipu': cls.ZHIPU_API_KEY,
            'wenxin': cls.WENXIN_API_KEY
        }

        return platform_keys.get(normalized_platform)

    @classmethod
    def is_api_key_configured(cls, platform: str) -> bool:
        """
        检查指定平台的API密钥是否已配置

        Args:
            platform: 平台名称

        Returns:
            bool: 是否已配置API密钥
        """
        # 平台别名映射，处理不同的平台名称变体
        platform_aliases = {
            '豆包': 'doubao',
            'doubao-cn': 'doubao',
            'Doubao': 'doubao',
            'DOUBAO': 'doubao',
            'deepseekr1': 'deepseek',
            'deepseek-r1': 'deepseek',
        }
        
        # 检查是否是别名，如果是则转换为主名称
        normalized_platform = platform_aliases.get(platform.lower(), platform.lower())
        
        api_key = cls.get_api_key(normalized_platform)
        return bool(api_key and api_key.strip() != '' and not api_key.startswith('sk-') and not api_key.endswith('[在此粘贴你的Key]'))