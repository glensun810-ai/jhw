"""
连接池管理模块
提供高效的HTTP连接复用机制
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self, pool_connections=10, pool_maxsize=20, max_retries=3):
        """
        初始化连接池管理器
        :param pool_connections: 连接池数量
        :param pool_maxsize: 最大连接数
        :param max_retries: 最大重试次数
        """
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.sessions = {}
        self.lock = Lock()
        
        # 创建默认会话
        self.default_session = self._create_session()
    
    def _create_session(self):
        """创建配置好的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认头部
        session.headers.update({
            'User-Agent': 'GEO-Validator-Pooled-Client/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def get_session_for_host(self, host: str):
        """获取特定主机的会话"""
        with self.lock:
            if host not in self.sessions:
                self.sessions[host] = self._create_session()
            return self.sessions[host]
    
    def get_default_session(self):
        """获取默认会话"""
        return self.default_session
    
    def close_all_sessions(self):
        """关闭所有会话"""
        for session in self.sessions.values():
            session.close()
        self.default_session.close()
        logger.info("已关闭所有连接池会话")


# 全局连接池管理器实例
_pool_manager = None


def get_connection_pool_manager() -> ConnectionPoolManager:
    """获取连接池管理器实例"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    return _pool_manager


def get_session_for_url(url: str):
    """根据URL获取适当的会话"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = f"{parsed.scheme}://{parsed.netloc}"
    
    manager = get_connection_pool_manager()
    return manager.get_session_for_host(host)


def get_default_session():
    """获取默认会话"""
    manager = get_connection_pool_manager()
    return manager.get_default_session()


def cleanup_connection_pools():
    """清理所有连接池"""
    global _pool_manager
    if _pool_manager:
        _pool_manager.close_all_sessions()
        _pool_manager = None
