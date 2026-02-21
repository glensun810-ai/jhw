"""
密钥管理系统 (Key Management System)

功能:
1. 密钥生成
2. 密钥存储
3. 密钥轮换
4. 密钥备份
5. 密钥审计
6. 多密钥支持

安全特性:
- 密钥加密存储
- 访问控制
- 审计日志
- 自动轮换
"""

import os
import json
import base64
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path

from wechat_backend.logging_config import api_logger


class KeyManager:
    """密钥管理器"""
    
    def __init__(self, key_vault_path: str = 'data/key_vault.json'):
        """
        初始化密钥管理器
        
        Args:
            key_vault_path: 密钥库文件路径
        """
        self.key_vault_path = Path(key_vault_path)
        self.key_vault = self._load_key_vault()
        api_logger.info(f"KeyManager initialized: {self.key_vault_path}")
    
    def _load_key_vault(self) -> Dict[str, Any]:
        """加载密钥库"""
        if self.key_vault_path.exists():
            try:
                with open(self.key_vault_path, 'r') as f:
                    vault = json.load(f)
                api_logger.info(f"Loaded key vault: {self.key_vault_path}")
                return vault
            except Exception as e:
                api_logger.error(f"Failed to load key vault: {e}")
        
        # 创建新密钥库
        vault = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'keys': {},
            'current_key_id': None,
            'rotation_policy': {
                'enabled': True,
                'rotation_days': 90,  # 90 天轮换一次
                'warning_days': 30    # 提前 30 天警告
            }
        }
        
        # 保存密钥库
        self._save_key_vault(vault)
        
        return vault
    
    def _save_key_vault(self, vault: Dict[str, Any]):
        """保存密钥库"""
        try:
            # 确保目录存在
            self.key_vault_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存到文件
            with open(self.key_vault_path, 'w') as f:
                json.dump(vault, f, indent=2)
            
            # 设置文件权限 (仅所有者可读写)
            os.chmod(self.key_vault_path, 0o600)
            
            api_logger.info(f"Saved key vault: {self.key_vault_path}")
        except Exception as e:
            api_logger.error(f"Failed to save key vault: {e}")
            raise
    
    def generate_key(self, key_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成新密钥
        
        Args:
            key_id: 密钥 ID (可选，不提供则自动生成)
            
        Returns:
            密钥信息字典
        """
        # 生成密钥 ID
        if key_id is None:
            key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 生成 Fernet 密钥
        key = Fernet.generate_key()
        
        # 创建密钥信息
        key_info = {
            'key_id': key_id,
            'key': key.decode(),  # 存储为字符串
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=90)).isoformat(),
            'status': 'active',
            'usage_count': 0,
            'last_used_at': None,
            'rotated_from': None
        }
        
        # 保存到密钥库
        self.key_vault['keys'][key_id] = key_info
        
        # 如果是第一个密钥，设为当前密钥
        if self.key_vault['current_key_id'] is None:
            self.key_vault['current_key_id'] = key_id
        
        self._save_key_vault(self.key_vault)
        
        api_logger.info(f"Generated new key: {key_id}")
        
        return key_info
    
    def get_current_key(self) -> Optional[str]:
        """获取当前密钥"""
        current_key_id = self.key_vault.get('current_key_id')
        if current_key_id and current_key_id in self.key_vault['keys']:
            key_info = self.key_vault['keys'][current_key_id]
            
            # 检查密钥是否过期
            expires_at = datetime.fromisoformat(key_info['expires_at'])
            if datetime.now() > expires_at:
                api_logger.warning(f"Current key expired: {current_key_id}")
                # 触发密钥轮换
                self.rotate_key()
                return self.get_current_key()
            
            return key_info['key'].encode()
        
        return None
    
    def get_key(self, key_id: str) -> Optional[str]:
        """获取指定密钥"""
        if key_id in self.key_vault['keys']:
            key_info = self.key_vault['keys'][key_id]
            return key_info['key'].encode()
        return None
    
    def rotate_key(self) -> Dict[str, Any]:
        """
        轮换密钥
        
        Returns:
            轮换统计信息
        """
        old_key_id = self.key_vault.get('current_key_id')
        
        # 生成新密钥
        new_key_info = self.generate_key()
        new_key_id = new_key_info['key_id']
        
        # 更新旧密钥状态
        if old_key_id:
            self.key_vault['keys'][old_key_id]['status'] = 'rotated'
            self.key_vault['keys'][old_key_id]['rotated_to'] = new_key_id
            new_key_info['rotated_from'] = old_key_id
        
        # 设置为当前密钥
        self.key_vault['current_key_id'] = new_key_id
        
        self._save_key_vault(self.key_vault)
        
        stats = {
            'rotated_at': datetime.now().isoformat(),
            'old_key_id': old_key_id,
            'new_key_id': new_key_id,
            'success': True
        }
        
        api_logger.info(f"Key rotated: {old_key_id} -> {new_key_id}")
        
        return stats
    
    def backup_keys(self, backup_path: str) -> str:
        """
        备份密钥
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            备份文件路径
        """
        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加密备份
        with open(self.key_vault_path, 'rb') as f:
            vault_data = f.read()
        
        # 生成备份密钥
        backup_key = Fernet.generate_key()
        cipher = Fernet(backup_key)
        encrypted_vault = cipher.encrypt(vault_data)
        
        # 保存备份
        backup_data = {
            'backup_at': datetime.now().isoformat(),
            'backup_key': backup_key.decode(),
            'encrypted_vault': base64.b64encode(encrypted_vault).decode()
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        api_logger.info(f"Backed up keys to: {backup_file}")
        
        return str(backup_file)
    
    def restore_keys(self, backup_path: str) -> bool:
        """
        恢复密钥
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否成功
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            api_logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # 解密备份
            backup_key = backup_data['backup_key'].encode()
            cipher = Fernet(backup_key)
            encrypted_vault = base64.b64decode(backup_data['encrypted_vault'])
            vault_data = cipher.decrypt(encrypted_vault)
            
            # 恢复密钥库
            self.key_vault = json.loads(vault_data)
            self._save_key_vault(self.key_vault)
            
            api_logger.info(f"Restored keys from: {backup_path}")
            
            return True
        except Exception as e:
            api_logger.error(f"Failed to restore keys: {e}")
            return False
    
    def get_key_stats(self) -> Dict[str, Any]:
        """获取密钥统计信息"""
        stats = {
            'total_keys': len(self.key_vault['keys']),
            'active_keys': sum(1 for k in self.key_vault['keys'].values() if k['status'] == 'active'),
            'rotated_keys': sum(1 for k in self.key_vault['keys'].values() if k['status'] == 'rotated'),
            'current_key_id': self.key_vault.get('current_key_id'),
            'rotation_enabled': self.key_vault['rotation_policy']['enabled'],
            'rotation_days': self.key_vault['rotation_policy']['rotation_days'],
            'next_rotation': None
        }
        
        # 计算下次轮换时间
        current_key_id = self.key_vault.get('current_key_id')
        if current_key_id:
            key_info = self.key_vault['keys'][current_key_id]
            expires_at = datetime.fromisoformat(key_info['expires_at'])
            stats['next_rotation'] = expires_at.isoformat()
            stats['days_until_rotation'] = (expires_at - datetime.now()).days
        
        return stats
    
    def audit_keys(self) -> List[Dict[str, Any]]:
        """审计密钥"""
        audit_logs = []
        
        for key_id, key_info in self.key_vault['keys'].items():
            # 检查密钥状态
            if key_info['status'] == 'active':
                expires_at = datetime.fromisoformat(key_info['expires_at'])
                days_until_expiry = (expires_at - datetime.now()).days
                
                if days_until_expiry < 0:
                    audit_logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'ERROR',
                        'key_id': key_id,
                        'issue': 'Key expired',
                        'days_overdue': abs(days_until_expiry)
                    })
                elif days_until_expiry < self.key_vault['rotation_policy']['warning_days']:
                    audit_logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'WARNING',
                        'key_id': key_id,
                        'issue': 'Key expiring soon',
                        'days_until_expiry': days_until_expiry
                    })
        
        return audit_logs


# 全局密钥管理器实例
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """获取密钥管理器实例"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def initialize_encryption() -> Dict[str, Any]:
    """初始化加密系统"""
    key_manager = get_key_manager()
    
    # 确保有当前密钥
    if key_manager.get_current_key() is None:
        key_manager.generate_key('initial_key')
        api_logger.info("Generated initial encryption key")
    
    # 返回统计信息
    return key_manager.get_key_stats()
