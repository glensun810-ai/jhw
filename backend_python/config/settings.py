"""
项目配置设置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent

# 加载配置
root_dir = get_project_root()
env_file = root_dir / '.env'

if env_file.exists():
    load_dotenv(str(env_file))

class Config:
    """配置类"""
    
    # 基础配置
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # 数据库配置
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')
    DATABASE_DIR = os.environ.get('DATABASE_DIR', '')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # AI 平台配置
    ARK_API_KEY = os.environ.get('ARK_API_KEY', '')
    DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY', '')
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    QWEN_API_KEY = os.environ.get('QWEN_API_KEY', '')
    
    # 豆包多模型配置
    DOUBAO_MODEL_PRIORITY_1 = os.environ.get('DOUBAO_MODEL_PRIORITY_1', '')
    DOUBAO_MODEL_PRIORITY_2 = os.environ.get('DOUBAO_MODEL_PRIORITY_2', '')
    DOUBAO_MODEL_PRIORITY_3 = os.environ.get('DOUBAO_MODEL_PRIORITY_3', '')
    DOUBAO_MODEL_PRIORITY_4 = os.environ.get('DOUBAO_MODEL_PRIORITY_4', '')
    DOUBAO_AUTO_SELECT_MODEL = os.environ.get('DOUBAO_AUTO_SELECT_MODEL', 'true').lower() == 'true'
    
    @classmethod
    def get_api_key(cls, platform: str) -> str:
        """获取平台 API Key"""
        platform_keys = {
            'doubao': cls.ARK_API_KEY or cls.DOUBAO_API_KEY,
            'deepseek': cls.DEEPSEEK_API_KEY,
            'qwen': cls.QWEN_API_KEY,
        }
        return platform_keys.get(platform.lower(), '')
    
    @classmethod
    def get_doubao_priority_models(cls) -> list:
        """获取豆包优先级模型列表"""
        priority_models = []
        
        for i in range(1, 11):
            model_key = f'DOUBAO_MODEL_PRIORITY_{i}'
            model_id = os.environ.get(model_key, '')
            if model_id and model_id.strip():
                priority_models.append(model_id.strip())
        
        return priority_models
    
    @classmethod
    def is_doubao_auto_select(cls) -> bool:
        """检查是否启用豆包自动选择"""
        return cls.DOUBAO_AUTO_SELECT_MODEL


def get_config(key: str, default: str = '') -> str:
    """获取配置项（可选）"""
    return os.environ.get(key, default)


def get_required_config(key: str) -> str:
    """获取配置项（必需）"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"缺少必需的配置项：{key}")
    return value
