"""
输入验证工具 (Input Validation Utilities)

功能:
1. 验证输入字符串
2. 过滤危险字符
3. 限制输入长度
4. 防止 SQL 注入
5. 防止 XSS 攻击

修复记录:
- 2026-02-20: 增强 SQL 注入检测，使用更严格的白名单模式
- 2026-02-20: 添加 numeric 验证支持
- 2026-02-20: 添加更详细的错误日志
"""

import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器 (增强版)"""

    # 危险字符列表 (SQL 注入) - 增强版
    DANGEROUS_SQL_CHARS = [
        ';', '--', '/*', '*/', 'xp_', 'DROP', 'DELETE',
        'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
        'UNION', 'SELECT', 'EXEC', 'EXECUTE'
    ]

    # 危险字符列表 (XSS 攻击)
    DANGEROUS_XSS_CHARS = [
        '<script>', '</script>', '<img', 'onerror=',
        'onclick=', 'onload=', 'javascript:'
    ]

    # 字段最大长度限制
    MAX_LENGTHS = {
        'execution_id': 64,
        'brand_name': 100,
        'model_name': 100,
        'question': 500,
        'response': 100000,
        'url': 2048,
        'email': 255,
        'default': 255
    }

    # 白名单模式 - 只允许安全字符
    SAFE_PATTERNS = {
        'execution_id': r'^[a-zA-Z0-9_-]+$',  # 只允许字母、数字、下划线、连字符
        'brand_name': r'^[a-zA-Z0-9\u4e00-\u9fa5_-]+$',  # 允许中文
        'model_name': r'^[a-zA-Z0-9\u4e00-\u9fa5_.-]+$',  # 允许中文和点
        'alphanumeric': r'^[a-zA-Z0-9_]+$',
        'user_openid': r'^[a-zA-Z0-9_-]+$',  # OpenID 通常是字母、数字、下划线、连字符
    }
    
    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str = 'input',
        max_length: Optional[int] = None,
        allow_empty: bool = False,
        check_sql_injection: bool = True,
        check_xss: bool = True,
        whitelist_pattern: Optional[str] = None
    ) -> str:
        """
        验证字符串输入 (增强版)

        Args:
            value: 输入值
            field_name: 字段名称 (用于错误提示)
            max_length: 最大长度 (None 使用默认)
            allow_empty: 是否允许空字符串
            check_sql_injection: 是否检查 SQL 注入
            check_xss: 是否检查 XSS 攻击
            whitelist_pattern: 白名单正则模式 (None 不使用)

        Returns:
            验证后的字符串

        Raises:
            ValueError: 验证失败
        """
        # 类型检查
        if value is None:
            if allow_empty:
                return ''
            logger.warning(f"Validation failed: {field_name} is None")
            raise ValueError(f"{field_name} cannot be None")

        if not isinstance(value, str):
            logger.warning(f"Validation failed: {field_name} is not a string (type: {type(value).__name__})")
            raise ValueError(f"{field_name} must be a string")

        # 空值检查
        value = value.strip()
        if not value:
            if allow_empty:
                return ''
            logger.warning(f"Validation failed: {field_name} is empty")
            raise ValueError(f"{field_name} cannot be empty")

        # 长度检查
        if max_length is None:
            max_length = cls.MAX_LENGTHS.get(field_name, cls.MAX_LENGTHS['default'])

        if len(value) > max_length:
            logger.warning(f"Validation failed: {field_name} too long ({len(value)} > {max_length})")
            raise ValueError(
                f"{field_name} too long (max {max_length} chars, got {len(value)})"
            )

        # 白名单模式检查 (如果提供)
        if whitelist_pattern:
            if not re.match(whitelist_pattern, value):
                logger.warning(f"Validation failed: {field_name} contains invalid characters")
                raise ValueError(
                    f"{field_name} contains invalid characters (only {whitelist_pattern} allowed)"
                )

        # SQL 注入检查
        if check_sql_injection:
            cls._check_sql_injection(value, field_name)

        # XSS 检查
        if check_xss:
            cls._check_xss(value, field_name)

        return value
    
    @classmethod
    def _check_sql_injection(cls, value: str, field_name: str):
        """检查 SQL 注入"""
        value_upper = value.upper()
        
        for dangerous in cls.DANGEROUS_SQL_CHARS:
            if dangerous.upper() in value_upper:
                raise ValueError(
                    f"{field_name} contains dangerous SQL characters: {dangerous}"
                )
        
        # 检查 SQL 注释
        if re.search(r'(--|#|/\*|\*/)', value):
            raise ValueError(f"{field_name} contains SQL comment characters")
        
        # 检查多个语句
        if value.count(';') > 0:
            raise ValueError(f"{field_name} contains multiple SQL statements")
    
    @classmethod
    def _check_xss(cls, value: str, field_name: str):
        """检查 XSS 攻击"""
        value_lower = value.lower()
        
        for dangerous in cls.DANGEROUS_XSS_CHARS:
            if dangerous.lower() in value_lower:
                raise ValueError(
                    f"{field_name} contains dangerous XSS characters: {dangerous}"
                )
        
        # 检查 HTML 标签
        if re.search(r'<[^>]+>', value):
            raise ValueError(f"{field_name} contains HTML tags")
    
    @classmethod
    def validate_execution_id(cls, value: str) -> str:
        """验证执行 ID (增强版 - 使用白名单)"""
        return cls.validate_string(
            value,
            field_name='execution_id',
            max_length=64,
            allow_empty=False,
            whitelist_pattern=cls.SAFE_PATTERNS['execution_id']
        )

    @classmethod
    def validate_brand_name(cls, value: str) -> str:
        """验证品牌名称 (增强版 - 使用白名单)"""
        return cls.validate_string(
            value,
            field_name='brand_name',
            max_length=100,
            allow_empty=False,
            whitelist_pattern=cls.SAFE_PATTERNS['brand_name']
        )

    @classmethod
    def validate_model_name(cls, value: str) -> str:
        """验证模型名称 (增强版 - 使用白名单)"""
        return cls.validate_string(
            value,
            field_name='model_name',
            max_length=100,
            allow_empty=False,
            whitelist_pattern=cls.SAFE_PATTERNS['model_name']
        )

    @classmethod
    def validate_user_openid(cls, value: str) -> str:
        """验证用户 OpenID (增强版 - 使用白名单)"""
        return cls.validate_string(
            value,
            field_name='user_openid',
            max_length=100,
            allow_empty=False,
            whitelist_pattern=cls.SAFE_PATTERNS['user_openid']
        )
    
    @classmethod
    def validate_question(cls, value: str) -> str:
        """验证问题"""
        return cls.validate_string(
            value,
            field_name='question',
            max_length=500,
            allow_empty=False
        )

    @classmethod
    def validate_response(cls, value: str) -> str:
        """验证响应"""
        return cls.validate_string(
            value,
            field_name='response',
            max_length=100000,
            allow_empty=False,
            check_xss=False  # AI 响应可能包含特殊字符
        )

    @classmethod
    def validate_numeric(cls, value: Any, field_name: str = 'value', 
                         min_value: Optional[float] = None, 
                         max_value: Optional[float] = None,
                         allow_none: bool = False) -> float:
        """
        验证数值输入
        
        Args:
            value: 输入值
            field_name: 字段名称
            min_value: 最小值 (None 不检查)
            max_value: 最大值 (None 不检查)
            allow_none: 是否允许 None
            
        Returns:
            验证后的数值
            
        Raises:
            ValueError: 验证失败
        """
        if value is None:
            if allow_none:
                return None
            logger.warning(f"Validation failed: {field_name} is None")
            raise ValueError(f"{field_name} cannot be None")
        
        try:
            num_value = float(value)
        except (TypeError, ValueError):
            logger.warning(f"Validation failed: {field_name} is not a number")
            raise ValueError(f"{field_name} must be a number")
        
        # 检查 NaN 和 Inf
        import math
        if math.isnan(num_value):
            logger.warning(f"Validation failed: {field_name} is NaN")
            raise ValueError(f"{field_name} cannot be NaN")
        if math.isinf(num_value):
            logger.warning(f"Validation failed: {field_name} is infinite")
            raise ValueError(f"{field_name} cannot be infinite")
        
        # 范围检查
        if min_value is not None and num_value < min_value:
            logger.warning(f"Validation failed: {field_name} {num_value} < {min_value}")
            raise ValueError(f"{field_name} must be >= {min_value}")
        if max_value is not None and num_value > max_value:
            logger.warning(f"Validation failed: {field_name} {num_value} > {max_value}")
            raise ValueError(f"{field_name} must be <= {max_value}")
        
        return num_value

    @classmethod
    def validate_json_string(cls, value: str, field_name: str = 'json_data') -> str:
        """验证 JSON 字符串"""
        import json
        
        # 先验证字符串
        value = cls.validate_string(value, field_name=field_name)
        
        # 再验证 JSON 格式
        try:
            json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"{field_name} is not valid JSON: {e}")
        
        return value


# 便捷函数
def validate_string(*args, **kwargs) -> str:
    """便捷函数：验证字符串"""
    return InputValidator.validate_string(*args, **kwargs)

def validate_execution_id(value: str) -> str:
    """便捷函数：验证执行 ID"""
    return InputValidator.validate_execution_id(value)

def validate_brand_name(value: str) -> str:
    """便捷函数：验证品牌名称"""
    return InputValidator.validate_brand_name(value)

def validate_model_name(value: str) -> str:
    """便捷函数：验证模型名称"""
    return InputValidator.validate_model_name(value)

def validate_question(value: str) -> str:
    """便捷函数：验证问题"""
    return InputValidator.validate_question(value)

def validate_response(value: str) -> str:
    """便捷函数：验证响应"""
    return InputValidator.validate_response(value)

def validate_numeric(*args, **kwargs) -> float:
    """便捷函数：验证数值"""
    return InputValidator.validate_numeric(*args, **kwargs)

def validate_user_openid(value: str) -> str:
    """便捷函数：验证用户 OpenID"""
    return InputValidator.validate_user_openid(value)
