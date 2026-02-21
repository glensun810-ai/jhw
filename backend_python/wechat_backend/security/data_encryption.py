"""
数据加密模块 (Data Encryption Module)

P0-3 敏感数据加密修复

功能:
1. 字段级加密 (Field-level encryption)
2. AES-256-GCM 对称加密
3. 密钥轮换支持 (Key rotation)
4. 审计日志

加密范围:
- user_openid (用户标识)
- preference_value (用户偏好)
- detailed_results (详细测试结果)
- 其他敏感字段

使用示例:
    # 初始化加密器
    encryptor = FieldEncryptor()
    
    # 加密
    encrypted = encryptor.encrypt("sensitive_data")
    
    # 解密
    decrypted = encryptor.decrypt(encrypted)
    
    # 或使用便捷函数
    encrypted = encrypt_field("sensitive_data")
    decrypted = decrypt_field(encrypted)

配置:
    在 .env 文件中设置:
    ENCRYPTION_KEY=your-32-byte-base64-encoded-key
    
    生成新密钥:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
import base64
import logging
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 检查 cryptography 库是否可用
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography library not installed. Install with: pip install cryptography")


class FieldEncryptor:
    """
    字段级加密器 (Field-level Encryptor)
    
    使用 AES-256-GCM 进行对称加密
    支持密钥轮换和审计日志
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        初始化加密器

        Args:
            key: 加密密钥 (32 字节 base64 编码)
                 如果为 None，从环境变量 ENCRYPTION_KEY 读取
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(
                "cryptography library is required. "
                "Install with: pip install cryptography"
            )

        # 获取密钥
        if key is None:
            key_str = os.environ.get('ENCRYPTION_KEY')
            if not key_str:
                # 开发模式下，如果没有密钥则生成一个临时密钥 (仅用于测试)
                logger.warning(
                    "ENCRYPTION_KEY not set. Generating temporary key for development. "
                    "Set ENCRYPTION_KEY in production!"
                )
                key = Fernet.generate_key()
            else:
                key = key_str.encode()
        
        # 验证密钥长度
        if len(key) < 32:
            raise ValueError(
                f"Encryption key too short ({len(key)} bytes). "
                "Key must be at least 32 bytes (256 bits)"
            )

        # 使用 Fernet (基于 AES-128-CBC + HMAC)
        # Fernet 密钥必须是 32 字节 base64 编码
        if len(key) != 44 or not key.endswith(b'='):
            # 如果不是 Fernet 格式，转换为适合 AESGCM 的密钥
            self.key = self._derive_key(key)
            self.cipher = AESGCM(self.key)
            self.use_aesgcm = True
        else:
            self.key = key
            self.cipher = Fernet(self.key)
            self.use_aesgcm = False

        self._encryption_count = 0
        self._decryption_count = 0
        self._last_key_rotation = datetime.now()

    def _derive_key(self, key_material: bytes) -> bytes:
        """
        从密钥材料派生 32 字节密钥
        
        使用简单的哈希方法 (生产环境应使用 PBKDF2 或 HKDF)
        """
        import hashlib
        # 使用 SHA-256 派生 32 字节密钥
        return hashlib.sha256(key_material).digest()

    def encrypt(self, plaintext: str) -> str:
        """
        加密明文

        Args:
            plaintext: 要加密的字符串

        Returns:
            base64 编码的密文
        """
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)

        plaintext_bytes = plaintext.encode('utf-8')

        if self.use_aesgcm:
            # AES-256-GCM 模式
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)
            # 组合 nonce + ciphertext 并 base64 编码
            encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
        else:
            # Fernet 模式
            encrypted = self.cipher.encrypt(plaintext_bytes).decode('utf-8')

        self._encryption_count += 1
        logger.debug(f"Encrypted data (count: {self._encryption_count})")

        return encrypted

    def decrypt(self, ciphertext: str) -> str:
        """
        解密密文

        Args:
            ciphertext: base64 编码的密文

        Returns:
            解密后的字符串
        """
        try:
            if self.use_aesgcm:
                # AES-256-GCM 模式
                data = base64.b64decode(ciphertext.encode('utf-8'))
                nonce = data[:12]
                actual_ciphertext = data[12:]
                plaintext_bytes = self.cipher.decrypt(nonce, actual_ciphertext, None)
            else:
                # Fernet 模式
                plaintext_bytes = self.cipher.decrypt(ciphertext.encode('utf-8'))

            self._decryption_count += 1
            logger.debug(f"Decrypted data (count: {self._decryption_count})")

            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    def rotate_key(self, new_key: Optional[bytes] = None) -> bytes:
        """
        轮换密钥

        Args:
            new_key: 新密钥 (如果为 None，生成新密钥)

        Returns:
            新密钥
        """
        if new_key is None:
            new_key = Fernet.generate_key()

        # 重新初始化加密器
        self.__init__(new_key)
        self._last_key_rotation = datetime.now()

        logger.info(f"Encryption key rotated at {self._last_key_rotation.isoformat()}")

        return new_key

    def get_stats(self) -> dict:
        """获取加密器统计信息"""
        return {
            'encryption_count': self._encryption_count,
            'decryption_count': self._decryption_count,
            'last_key_rotation': self._last_key_rotation.isoformat(),
            'algorithm': 'AES-256-GCM' if self.use_aesgcm else 'Fernet (AES-128-CBC)'
        }


# 全局加密器实例 (延迟初始化)
_encryptor: Optional[FieldEncryptor] = None


def get_encryptor() -> FieldEncryptor:
    """获取全局加密器实例"""
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryptor()
    return _encryptor


def encrypt_field(value: str) -> str:
    """
    便捷函数：加密字段

    Args:
        value: 要加密的值

    Returns:
        加密后的值
    """
    return get_encryptor().encrypt(value)


def decrypt_field(encrypted_value: str) -> str:
    """
    便捷函数：解密字段

    Args:
        encrypted_value: 加密的值

    Returns:
        解密后的值
    """
    return get_encryptor().decrypt(encrypted_value)


def encrypt_sensitive_data(data: dict, fields: list) -> dict:
    """
    加密字典中的敏感字段

    Args:
        data: 原始数据字典
        fields: 需要加密的字段列表

    Returns:
        加密后的字典 (新对象)
    """
    result = data.copy()
    for field in fields:
        if field in result and result[field] is not None:
            result[field] = encrypt_field(str(result[field]))
    return result


def decrypt_sensitive_data(data: dict, fields: list) -> dict:
    """
    解密字典中的敏感字段

    Args:
        data: 加密的数据字典
        fields: 需要解密的字段列表

    Returns:
        解密后的字典 (新对象)
    """
    result = data.copy()
    for field in fields:
        if field in result and result[field] is not None:
            try:
                result[field] = decrypt_field(result[field])
            except ValueError:
                # 如果解密失败，保持原值 (可能未加密)
                logger.warning(f"Failed to decrypt field {field}, keeping original value")
    return result


# 预定义的敏感字段列表
SENSITIVE_FIELDS = {
    'users': ['openid', 'avatar_url'],
    'user_preferences': ['preference_value'],
    'test_records': ['detailed_results'],
}


class EncryptedDatabaseMixin:
    """
    数据库加密混合类
    
    用于为数据库操作添加加密支持
    """

    SENSITIVE_FIELDS = SENSITIVE_FIELDS

    def encrypt_record(self, table: str, data: dict) -> dict:
        """加密记录中的敏感字段"""
        if table in self.SENSITIVE_FIELDS:
            return encrypt_sensitive_data(data, self.SENSITIVE_FIELDS[table])
        return data

    def decrypt_record(self, table: str, data: dict) -> dict:
        """解密记录中的敏感字段"""
        if table in self.SENSITIVE_FIELDS:
            return decrypt_sensitive_data(data, self.SENSITIVE_FIELDS[table])
        return data


# 生成密钥的辅助函数
def generate_encryption_key() -> str:
    """
    生成新的加密密钥

    Returns:
        base64 编码的密钥字符串
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("cryptography library is required")
    
    key = Fernet.generate_key().decode()
    print(f"Generated encryption key: {key}")
    print("\nAdd this to your .env file:")
    print(f"ENCRYPTION_KEY={key}")
    return key


if __name__ == '__main__':
    # 测试加密模块
    print("Testing FieldEncryptor...")
    
    # 生成新密钥
    key = generate_encryption_key()
    
    # 创建加密器
    encryptor = FieldEncryptor(key.encode())
    
    # 测试加密/解密
    test_data = "sensitive_user_openid_12345"
    encrypted = encryptor.encrypt(test_data)
    decrypted = encryptor.decrypt(encrypted)
    
    print(f"\nOriginal:  {test_data}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {test_data == decrypted}")
    
    # 打印统计信息
    stats = encryptor.get_stats()
    print(f"\nStats: {stats}")
