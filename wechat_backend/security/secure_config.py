"""
安全配置管理模块
提供加密存储和管理敏感配置信息的功能
"""

import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfig:
    """安全配置管理类"""
    
    def __init__(self, password: str = None):
        """
        初始化安全配置管理器
        :param password: 用于加密/解密的密码，如果未提供则使用环境变量
        """
        self.password = password or os.getenv('SECURE_CONFIG_PASSWORD', 'default_password_for_dev')
        self.password_bytes = self.password.encode()
        
    def _get_cipher(self, salt: bytes) -> Fernet:
        """根据盐值获取加密器"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password_bytes))
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """加密单个值"""
        salt = os.urandom(16)
        cipher = self._get_cipher(salt)
        encrypted_value = cipher.encrypt(value.encode())
        # 将盐和加密值一起编码
        return base64.b64encode(salt + encrypted_value).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """解密单个值"""
        try:
            encrypted_data = base64.b64decode(encrypted_value.encode())
            salt = encrypted_data[:16]
            encrypted_part = encrypted_data[16:]
            cipher = self._get_cipher(salt)
            decrypted = cipher.decrypt(encrypted_part)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def encrypt_config_dict(self, config_dict: dict) -> str:
        """加密整个配置字典"""
        json_str = json.dumps(config_dict)
        return self.encrypt_value(json_str)
    
    def decrypt_config_dict(self, encrypted_config: str) -> dict:
        """解密配置字典"""
        json_str = self.decrypt_value(encrypted_config)
        return json.loads(json_str)


# 全局配置管理器实例
_config_manager = None


def get_config_manager(password: str = None) -> SecureConfig:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfig(password)
    return _config_manager


def load_secure_config_from_file(file_path: str, password: str = None) -> dict:
    """从加密文件加载配置"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        encrypted_content = f.read().strip()
    
    manager = get_config_manager(password)
    return manager.decrypt_config_dict(encrypted_content)


def save_secure_config_to_file(config_dict: dict, file_path: str, password: str = None) -> None:
    """保存配置到加密文件"""
    manager = get_config_manager(password)
    encrypted_content = manager.encrypt_config_dict(config_dict)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(encrypted_content)
    
    # 设置文件权限，只允许所有者读写
    os.chmod(file_path, 0o600)
    print(f"已安全保存配置到: {file_path}")


# 便捷函数
def encrypt_sensitive_value(value: str, password: str = None) -> str:
    """便捷函数：加密敏感值"""
    manager = get_config_manager(password)
    return manager.encrypt_value(value)


def decrypt_sensitive_value(encrypted_value: str, password: str = None) -> str:
    """便捷函数：解密敏感值"""
    manager = get_config_manager(password)
    return manager.decrypt_value(encrypted_value)
