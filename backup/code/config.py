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

    # Logging Configuration (兼容旧配置和新配置)
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'  # 默认日志文件
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB default
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))

    # 数据库配置
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'database.db'
    DATABASE_DIR = os.environ.get('DATABASE_DIR') or ''
    
    # 如果设置了 DATABASE_DIR，则使用完整路径
    if DATABASE_DIR:
        DATABASE_PATH = os.path.join(DATABASE_DIR, 'database.db')
    
    # 同步数据存储配置
    SYNC_STORAGE_ENABLED = os.environ.get('SYNC_STORAGE_ENABLED', 'true').lower() == 'true'
    SYNC_RETENTION_DAYS = int(os.environ.get('SYNC_RETENTION_DAYS', '90'))
    
    # 新日志系统配置
    USE_UNIFIED_LOGGING = os.environ.get('USE_UNIFIED_LOGGING', 'true').lower() == 'true'
    LOG_DIR = os.environ.get('LOG_DIR') or 'logs'
    LOG_CONSOLE_LEVEL = os.environ.get('LOG_CONSOLE_LEVEL', 'INFO')
    LOG_FILE_LEVEL = os.environ.get('LOG_FILE_LEVEL', 'DEBUG')
    LOG_QUEUE_SIZE = int(os.environ.get('LOG_QUEUE_SIZE', '10000'))
    LOG_ENABLE_AI_HANDLER = os.environ.get('LOG_ENABLE_AI_HANDLER', 'true').lower() == 'true'

    # WeChat API Endpoints
    WECHAT_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_CODE_TO_SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
    WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_SEND_TEMPLATE_MSG_URL = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send'

    # AI Platform API Keys
    # 豆包 API 配置（使用 ARK_API_KEY 格式）
    ARK_API_KEY = os.environ.get('ARK_API_KEY') or ''
    # 兼容旧配置
    DOUBAO_ACCESS_KEY_ID = os.environ.get('DOUBAO_ACCESS_KEY_ID') or ''
    DOUBAO_SECRET_ACCESS_KEY = os.environ.get('DOUBAO_SECRET_ACCESS_KEY') or ''
    DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY') or ''
    
    # 豆包多模型优先级配置（2026 年 2 月更新）
    # 按优先级顺序加载多个模型 ID
    DOUBAO_MODEL_PRIORITY_1 = os.environ.get('DOUBAO_MODEL_PRIORITY_1') or ''
    DOUBAO_MODEL_PRIORITY_2 = os.environ.get('DOUBAO_MODEL_PRIORITY_2') or ''
    DOUBAO_MODEL_PRIORITY_3 = os.environ.get('DOUBAO_MODEL_PRIORITY_3') or ''
    DOUBAO_MODEL_PRIORITY_4 = os.environ.get('DOUBAO_MODEL_PRIORITY_4') or ''
    DOUBAO_MODEL_PRIORITY_5 = os.environ.get('DOUBAO_MODEL_PRIORITY_5') or ''
    DOUBAO_MODEL_PRIORITY_6 = os.environ.get('DOUBAO_MODEL_PRIORITY_6') or ''
    DOUBAO_MODEL_PRIORITY_7 = os.environ.get('DOUBAO_MODEL_PRIORITY_7') or ''
    DOUBAO_MODEL_PRIORITY_8 = os.environ.get('DOUBAO_MODEL_PRIORITY_8') or ''
    DOUBAO_MODEL_PRIORITY_9 = os.environ.get('DOUBAO_MODEL_PRIORITY_9') or ''
    DOUBAO_MODEL_PRIORITY_10 = os.environ.get('DOUBAO_MODEL_PRIORITY_10') or ''
    
    # 自动选择模式
    DOUBAO_AUTO_SELECT_MODEL = os.environ.get('DOUBAO_AUTO_SELECT_MODEL', 'true').lower() == 'true'
    
    # 兼容旧配置（如果未设置优先级模型，则使用此配置）
    DOUBAO_MODEL_ID = os.environ.get('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')

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
            'doubao': cls.get_doubao_api_key(),  # 使用特殊方法处理豆包密钥
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
    def get_doubao_api_key(cls) -> Optional[str]:
        """
        获取豆包 API Token（使用 ARK_API_KEY 格式）

        Returns:
            豆包 API Token 或 None
        """
        # 优先使用 ARK_API_KEY 格式（OpenAI SDK 兼容）
        if cls.ARK_API_KEY and cls.ARK_API_KEY != "${ARK_API_KEY}":
            return cls.ARK_API_KEY
        # 回退到旧的单 Key 格式
        elif cls.DOUBAO_API_KEY and cls.DOUBAO_API_KEY != "${DOUBAO_API_KEY}":
            return cls.DOUBAO_API_KEY
        return None

    @staticmethod
    def get_doubao_models() -> list:
        """
        获取豆包所有可用的模型列表（按优先级顺序）
        2026 年 2 月更新：使用新的部署点 ID 和多模型优先级配置

        Returns:
            模型列表（按优先级排序）
        """
        # 收集所有优先级模型配置
        priority_models = []
        
        # 按优先级顺序添加模型（优先级 1-10）
        for i in range(1, 11):
            model_key = f'DOUBAO_MODEL_PRIORITY_{i}'
            model_id = os.environ.get(model_key, '')
            if model_id and model_id.strip():
                priority_models.append(model_id.strip())
        
        # 如果配置了优先级模型，则返回优先级列表
        if priority_models:
            return priority_models
        
        # 否则使用兼容旧配置
        return [
            os.environ.get('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq'),  # 兼容旧配置
        ]
    
    @staticmethod
    def get_doubao_priority_models() -> list:
        """
        获取豆包优先级模型列表（仅包含配置的优先级模型）
        
        Returns:
            优先级模型列表
        """
        priority_models = []
        
        # 按优先级顺序添加模型（优先级 1-10）
        for i in range(1, 11):
            model_key = f'DOUBAO_MODEL_PRIORITY_{i}'
            model_id = os.environ.get(model_key, '')
            if model_id and model_id.strip():
                priority_models.append(model_id.strip())
        
        return priority_models
    
    @staticmethod
    def is_doubao_auto_select() -> bool:
        """
        检查是否启用豆包自动选择模式
        
        Returns:
            bool: 是否启用自动选择
        """
        return os.environ.get('DOUBAO_AUTO_SELECT_MODEL', 'true').lower() == 'true'

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
        return bool(api_key and api_key.strip() != '' and not api_key.endswith('[在此粘贴你的 Key]'))  # Fixed: removed sk- check