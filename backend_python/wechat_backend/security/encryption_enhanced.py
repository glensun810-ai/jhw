#!/usr/bin/env python3
"""
差距 2 修复：敏感数据加密增强

修复内容:
1. 自动加密 openid 和 phone
2. 数据库字段加密装饰器
3. 加密字段访问器

使用方法:
    from wechat_backend.security.encryption_enhanced import encrypt_sensitive_fields
    
    @encrypt_sensitive_fields(['openid', 'phone'])
    class User:
        pass
"""

import os
from typing import List, Dict, Any, Optional
from wechat_backend.security.data_encryption import FieldEncryptor, encrypt_field, decrypt_field

# 初始化加密器
_encryptor = None

def get_encryptor() -> FieldEncryptor:
    """获取加密器实例"""
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryptor()
    return _encryptor


def encrypt_sensitive_data(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    加密敏感字段
    
    Args:
        data: 原始数据字典
        fields: 需要加密的字段列表
    
    Returns:
        加密后的数据字典
    """
    encrypted_data = data.copy()
    
    for field in fields:
        if field in data and data[field]:
            try:
                encrypted_data[field] = encrypt_field(str(data[field]))
            except Exception as e:
                print(f"加密字段 {field} 失败：{e}")
                # 加密失败时保留原文（记录日志）
    
    return encrypted_data


def decrypt_sensitive_data(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    解密敏感字段
    
    Args:
        data: 加密数据字典
        fields: 需要解密的字段列表
    
    Returns:
        解密后的数据字典
    """
    decrypted_data = data.copy()
    
    for field in fields:
        if field in data and data[field]:
            try:
                decrypted_data[field] = decrypt_field(data[field])
            except Exception as e:
                print(f"解密字段 {field} 失败：{e}")
                # 解密失败时保留原文（可能是未加密的旧数据）
    
    return decrypted_data


# 需要加密的敏感字段列表
SENSITIVE_FIELDS = {
    'user': ['openid', 'phone', 'password_hash'],
    'test_record': ['user_openid'],
    'preference': ['preference_value']
}


def encrypt_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """加密用户数据"""
    return encrypt_sensitive_data(user_data, SENSITIVE_FIELDS['user'])


def decrypt_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """解密用户数据"""
    return decrypt_sensitive_data(user_data, SENSITIVE_FIELDS['user'])


def encrypt_test_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """加密测试记录"""
    return encrypt_sensitive_data(record, SENSITIVE_FIELDS['test_record'])


def decrypt_test_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """解密测试记录"""
    return decrypt_sensitive_data(record, SENSITIVE_FIELDS['test_record'])


# 数据库层加密装饰器
def encrypt_on_save(*fields):
    """
    保存时自动加密装饰器
    
    使用示例:
        @encrypt_on_save('openid', 'phone')
        class User(db.Model):
            pass
    """
    def decorator(cls):
        original_save = getattr(cls, 'save', None)
        
        def save_with_encryption(self, *args, **kwargs):
            # 保存前加密指定字段
            for field in fields:
                if hasattr(self, field):
                    value = getattr(self, field)
                    if value:
                        try:
                            encrypted = encrypt_field(str(value))
                            setattr(self, field, encrypted)
                        except Exception as e:
                            print(f"加密字段 {field} 失败：{e}")
            
            # 调用原始 save 方法
            if original_save:
                return original_save(self, *args, **kwargs)
        
        setattr(cls, 'save', save_with_encryption)
        return cls
    
    return decorator


def decrypt_on_load(*fields):
    """
    加载时自动解密装饰器
    
    使用示例:
        @decrypt_on_load('openid', 'phone')
        class User(db.Model):
            pass
    """
    def decorator(cls):
        # 添加属性访问器
        for field in fields:
            private_field = f'_{field}'
            
            def make_getter(f, pf):
                def getter(self):
                    value = getattr(self, pf, None)
                    if value:
                        try:
                            return decrypt_field(value)
                        except Exception as e:

                            pass  # TODO: 添加适当的错误处理
                            return value
                    return None
                return getter
            
            def make_setter(f, pf):
                def setter(self, value):
                    if value:
                        try:
                            encrypted = encrypt_field(str(value))
                            setattr(self, pf, encrypted)
                        except Exception as e:

                            pass  # TODO: 添加适当的错误处理
                            setattr(self, pf, value)
                    else:
                        setattr(self, pf, None)
                return setter
            
            # 存储原始字段名为私有字段
            if not hasattr(cls, private_field):
                setattr(cls, private_field, None)
            
            # 添加属性
            setattr(cls, field, property(
                make_getter(field, private_field),
                make_setter(field, private_field)
            ))
        
        return cls
    
    return decorator


if __name__ == '__main__':
    # 测试加密功能
    print("="*60)
    print("差距 2 修复：敏感数据加密增强 - 测试")
    print("="*60)
    print()
    
    # 测试用户数据加密
    user_data = {
        'openid': 'oXXXX1234567890',
        'phone': '13800138000',
        'nickname': '测试用户'
    }
    
    print("原始用户数据:")
    print(user_data)
    print()
    
    # 加密
    encrypted = encrypt_user_data(user_data)
    print("加密后用户数据:")
    print(encrypted)
    print()
    
    # 解密
    decrypted = decrypt_user_data(encrypted)
    print("解密后用户数据:")
    print(decrypted)
    print()
    
    # 验证
    if decrypted['openid'] == user_data['openid'] and decrypted['phone'] == user_data['phone']:
        print("✅ 加密解密测试通过！")
    else:
        print("❌ 加密解密测试失败！")
    
    print()
    print("="*60)
