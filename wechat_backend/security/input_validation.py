"""
输入验证和净化模块
提供安全的输入验证和净化功能
"""

import re
import html
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# 尝试导入bleach，如果不可用则使用基本的HTML转义
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    # 定义一个简单的替代函数
    def bleach_clean(text, tags=None, attributes=None, strip=False):
        """简单的HTML净化替代函数"""
        # 基本的HTML标签移除
        import re
        if strip:
            # 移除所有HTML标签
            clean_text = re.sub(r'<[^>]+>', '', text)
        else:
            # 仅转义危险字符
            clean_text = html.escape(text)
        return clean_text

    bleach = type('BleachMock', (), {'clean': bleach_clean})()

# 尝试导入marshmallow，如果不可用则使用基本验证
try:
    from marshmallow import Schema, fields, ValidationError
    MARSHMALLOW_AVAILABLE = True
except ImportError:
    # 定义基本的替代类
    class Schema:
        pass

    class fields:
        @staticmethod
        def String(*args, **kwargs):
            return str

        @staticmethod
        def Email(*args, **kwargs):
            return str

        @staticmethod
        def Url(*args, **kwargs):
            return str

    class ValidationError(Exception):
        pass

    MARSHMALLOW_AVAILABLE = False


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def validate_alphanumeric(text: str, min_length: int = 1, max_length: int = 100) -> bool:
        """验证字母数字组合"""
        pattern = f'^[a-zA-Z0-9]{{{min_length},{max_length}}}$'
        return bool(re.match(pattern, text))
    
    @staticmethod
    def validate_safe_text(text: str, max_length: int = 1000) -> bool:
        """验证安全文本（不含危险字符）"""
        if len(text) > max_length:
            return False
        # 检查是否包含潜在危险字符
        dangerous_patterns = [
            r'<script',  # XSS尝试
            r'javascript:',  # JavaScript URI
            r'on\w+\s*=',  # 事件处理器
            r'<iframe',  # iframe标签
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        return True


class InputSanitizer:
    """输入净化器"""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """净化HTML内容，移除危险标签"""
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        allowed_attributes = {}

        if BLEACH_AVAILABLE:
            return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        else:
            # 如果bleach不可用，使用基本的净化方法
            import re
            # 移除不允许的标签
            clean_text = re.sub(r'<(?!/' + '|'.join(allowed_tags) + r'|!--)[^>]*>', '', text)
            # 确保闭合标签也被处理
            for tag in allowed_tags:
                # 允许的标签保持不变
                pass
            return clean_text
    
    @staticmethod
    def sanitize_string(text: str) -> str:
        """净化字符串，移除或转义特殊字符"""
        if text is None:
            return None
        # 首先净化HTML
        text = InputSanitizer.sanitize_html(text)
        # 然后转义HTML特殊字符
        return html.escape(text, quote=True)
    
    @staticmethod
    def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """净化用户输入数据"""
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized_data[key] = InputSanitizer.sanitize_user_input(value)
            elif isinstance(value, list):
                sanitized_data[key] = [
                    InputSanitizer.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_data[key] = value
        return sanitized_data


if MARSHMALLOW_AVAILABLE:
    class RequestSchema(Schema):
        """请求数据验证模式"""

        # 通用字段验证
        user_id = fields.Str(validate=lambda x: len(x) <= 50, required=False)
        brand_list = fields.List(fields.Str(validate=lambda x: len(x) <= 100), required=True)
        selectedModels = fields.List(fields.Dict(), required=False)
        customQuestions = fields.List(fields.Str(validate=lambda x: len(x) <= 1000), required=False)
        userOpenid = fields.Str(validate=lambda x: len(x) <= 100, required=False)
        apiKey = fields.Str(validate=lambda x: len(x) <= 100, required=False)
        userLevel = fields.Str(required=False)
else:
    # 如果marshmallow不可用，创建一个简单的验证函数
    class RequestSchema:
        """简单的请求数据验证类（当marshmallow不可用时）"""

        def __init__(self):
            pass

        def load(self, data):
            """简单的数据加载和验证"""
            # 基本验证
            if 'brand_list' not in data or not isinstance(data.get('brand_list'), list) or len(data['brand_list']) == 0:
                raise ValueError("brand_list is required and must be a non-empty list")

            # 验证字段长度
            for field_name in ['user_id', 'userOpenid', 'apiKey', 'userLevel']:
                value = data.get(field_name)
                if value and isinstance(value, str) and len(value) > 100:
                    raise ValueError(f"{field_name} exceeds maximum length of 100")

            return data


def validate_and_sanitize_request(request_data: Dict[str, Any], schema_class=RequestSchema) -> Dict[str, Any]:
    """验证和净化请求数据"""
    # 首先净化输入
    sanitized_data = InputSanitizer.sanitize_user_input(request_data)

    # 然后验证结构（如果marshmallow可用）
    if MARSHMALLOW_AVAILABLE or schema_class != RequestSchema:
        schema = schema_class()
        try:
            validated_data = schema.load(sanitized_data)
            return validated_data
        except ValidationError as err:
            raise ValueError(f"请求数据验证失败: {getattr(err, 'messages', str(err))}")
        except Exception as err:
            # 如果是简单验证类，直接返回净化后的数据
            if not MARSHMALLOW_AVAILABLE and schema_class == RequestSchema:
                return sanitized_data
            else:
                raise ValueError(f"请求数据验证失败: {str(err)}")
    else:
        # 使用简单验证
        schema = schema_class()
        try:
            validated_data = schema.load(sanitized_data)
            return validated_data
        except Exception as err:
            raise ValueError(f"请求数据验证失败: {str(err)}")


# 便捷函数
def is_valid_email(email: str) -> bool:
    """便捷函数：验证邮箱"""
    return InputValidator.validate_email(email)


def is_valid_url(url: str) -> bool:
    """便捷函数：验证URL"""
    return InputValidator.validate_url(url)


def sanitize_input(text: str) -> str:
    """便捷函数：净化输入"""
    return InputSanitizer.sanitize_string(text)


def validate_safe_text(text: str, max_length: int = 1000) -> bool:
    """便捷函数：验证安全文本"""
    return InputValidator.validate_safe_text(text, max_length)