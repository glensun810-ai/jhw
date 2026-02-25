"""
配置验证器 - P1-3 修复
验证配置完整性，确保系统启动前所有必需配置都已正确设置
"""

import sys
import os as os_module
from pathlib import Path

# 添加项目根目录到路径
base_dir = Path(__file__).parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# 现在可以导入日志
try:
    from wechat_backend.logging_config import api_logger
except ImportError:
    api_logger = None


class ConfigValidationResult:
    """配置验证结果"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def add_error(self, message):
        self.errors.append(message)
    
    def add_warning(self, message):
        self.warnings.append(message)
    
    def add_info(self, message):
        self.info.append(message)
    
    def is_valid(self):
        return len(self.errors) == 0
    
    def print_report(self):
        """打印验证报告"""
        print("=" * 60)
        print("配置验证报告")
        print("=" * 60)
        
        if self.info:
            print("\n信息:")
            for msg in self.info:
                print(f"   - {msg}")
        
        if self.warnings:
            print("\n警告:")
            for msg in self.warnings:
                print(f"   - {msg}")
        
        if self.errors:
            print("\n错误:")
            for msg in self.errors:
                print(f"   - {msg}")
        
        print("\n" + "=" * 60)
        if self.is_valid():
            if self.warnings:
                print("✅ 配置验证通过（有警告）")
            else:
                print("✅ 配置验证通过")
        else:
            print(f"❌ 配置验证失败（{len(self.errors)} 个错误）")
        print("=" * 60)


def validate_config():
    """验证配置完整性"""
    result = ConfigValidationResult()
    
    # 1. 验证必需配置
    required_configs = {
        'WECHAT_APP_ID': '微信小程序 AppID',
        'WECHAT_APP_SECRET': '微信小程序 AppSecret',
        'SECRET_KEY': 'Flask 密钥',
    }
    
    for key, description in required_configs.items():
        value = os_module.environ.get(key, '').strip()
        if not value:
            result.add_error(f"缺少必需配置：{key} ({description})")
        elif key == 'SECRET_KEY' and len(value) < 16:
            result.add_warning(f"{key} 长度过短，建议至少 16 字符")
    
    # 2. 验证 AI 平台配置
    ai_platforms = {
        'ARK_API_KEY': '豆包 AI (ARK)',
        'DEEPSEEK_API_KEY': 'DeepSeek AI',
        'QWEN_API_KEY': '通义千问 AI',
        'CHATGPT_API_KEY': 'ChatGPT AI',
        'GEMINI_API_KEY': 'Gemini AI',
        'ZHIPU_API_KEY': '智谱 AI',
    }
    
    configured_platforms = []
    unavailable_platforms = []
    
    for key, name in ai_platforms.items():
        value = os_module.environ.get(key, '').strip()
        if value and value != '${' + key + '}':
            configured_platforms.append(name)
        else:
            unavailable_platforms.append(name)
    
    if not configured_platforms:
        result.add_error("至少需要配置一个 AI 平台 API Key")
    else:
        result.add_info(f"已配置的 AI 平台：{', '.join(configured_platforms)}")
    
    if unavailable_platforms:
        result.add_warning(f"未配置的 AI 平台：{', '.join(unavailable_platforms)}")
    
    # 3. 验证豆包模型配置
    doubao_api_key = os_module.environ.get('ARK_API_KEY', '') or os_module.environ.get('DOUBAO_API_KEY', '')
    if doubao_api_key and doubao_api_key != '${ARK_API_KEY}':
        priority_models = []
        for i in range(1, 6):
            model_id = os_module.environ.get(f'DOUBAO_MODEL_PRIORITY_{i}', '').strip()
            if model_id:
                priority_models.append(model_id)
        
        default_model = os_module.environ.get('DOUBAO_MODEL_ID', '').strip()
        
        if not priority_models and not default_model:
            result.add_warning("豆包 API Key 已配置，但未设置模型 ID")
        elif priority_models:
            result.add_info(f"豆包优先级模型 ({len(priority_models)} 个): {', '.join(priority_models)}")
        elif default_model:
            result.add_info(f"豆包默认模型：{default_model}")
    
    # 4. 检查调试模式
    debug_mode = os_module.environ.get('DEBUG', 'false').lower() == 'true'
    if debug_mode:
        result.add_warning("⚠️  系统运行在调试模式，生产环境请关闭")
    
    return result


def print_config_status():
    """打印配置状态"""
    result = validate_config()
    result.print_report()
    return result.is_valid()


if __name__ == '__main__':
    # 加载环境变量
    env_file = base_dir / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"已加载环境变量：{env_file}")
    
    # 验证配置
    print_config_status()
