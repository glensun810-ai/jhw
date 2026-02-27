"""
数据脱敏工具

用于处理敏感信息的脱敏，确保日志和存储中不包含敏感数据。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple


class DataSanitizer:
    """
    数据脱敏工具类
    
    功能：
    1. 脱敏字典中的敏感信息
    2. 脱敏 HTTP 头中的敏感信息
    3. 检查是否包含敏感信息
    
    使用示例:
        >>> sanitized = DataSanitizer.sanitize_dict({'api_key': 'secret123'})
        >>> DataSanitizer.contains_sensitive_data({'password': 'xxx'})
        True
    """
    
    # 敏感信息模式（正则表达式，替换对）
    SENSITIVE_PATTERNS: List[Tuple[str, str]] = [
        (r'("api[_-]?key"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("token"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("password"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("secret"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("authorization"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("openid"\s*:\s*")([^"]+)(")', r'\1***\3'),
        (r'("phone"\s*:\s*")(\d{11})(")', r'\1***\3'),
        (r'("id[_-]?card"\s*:\s*")(\d{18}[\dXx])(")', r'\1***\3'),
    ]
    
    # 敏感头列表
    SENSITIVE_HEADERS = [
        'authorization', 'cookie', 'x-api-key', 'api-key', 
        'token', 'x-token', 'access-token', 'refresh-token'
    ]
    
    # 敏感关键词
    SENSITIVE_KEYWORDS = [
        'apikey', 'api_key', 'token', 'password', 
        'secret', 'authorization', 'openid', 'phone', 'idcard'
    ]
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        脱敏字典中的敏感信息
        
        返回脱敏后的新字典，不修改原数据。
        
        Args:
            data: 原始字典
        
        Returns:
            Dict[str, Any]: 脱敏后的字典
        """
        if not data:
            return data
        
        try:
            # 转换为 JSON 字符串进行正则替换
            json_str = json.dumps(data, ensure_ascii=False)
            
            # 应用所有脱敏规则
            for pattern, replacement in cls.SENSITIVE_PATTERNS:
                json_str = re.sub(pattern, replacement, json_str, flags=re.IGNORECASE)
            
            # 转回字典
            return json.loads(json_str)
            
        except Exception:
            # 如果脱敏失败，返回空字典（安全失败）
            return {}
    
    @classmethod
    def sanitize_headers(cls, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """
        脱敏 HTTP 头中的敏感信息
        
        常见的敏感头：Authorization, Cookie, X-API-Key 等
        
        Args:
            headers: 原始 HTTP 头
        
        Returns:
            Dict[str, str]: 脱敏后的 HTTP 头
        """
        if not headers:
            return headers
        
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in cls.SENSITIVE_HEADERS:
                # 保留前 4 位和后 4 位，中间用***代替
                if value and len(value) > 8:
                    masked = value[:4] + '***' + value[-4:]
                else:
                    masked = '***'
                sanitized[key] = masked
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def contains_sensitive_data(cls, data: Dict[str, Any]) -> bool:
        """
        检查是否包含敏感信息
        
        Args:
            data: 待检查的字典
        
        Returns:
            bool: True 表示包含敏感信息
        """
        if not data:
            return False
        
        try:
            json_str = json.dumps(data).lower()
            
            for keyword in cls.SENSITIVE_KEYWORDS:
                if keyword in json_str:
                    return True
            
            return False
            
        except Exception:
            # 如果检查失败，保守认为包含敏感信息
            return True
    
    @classmethod
    def mask_value(cls, value: str, keep_chars: int = 4) -> str:
        """
        通用值脱敏方法
        
        Args:
            value: 原始值
            keep_chars: 保留的字符数（前后各保留）
        
        Returns:
            str: 脱敏后的值
        """
        if not value:
            return '***'
        
        if len(value) <= keep_chars * 2:
            return '***'
        
        return value[:keep_chars] + '***' + value[-keep_chars:]
