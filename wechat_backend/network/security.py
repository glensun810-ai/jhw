"""
网络安全模块
提供安全的HTTP请求和证书验证功能
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
import certifi
import hashlib
import hmac
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SecureHttpClient:
    """安全HTTP客户端"""
    
    def __init__(self, 
                 verify_ssl: bool = True, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 cert_file: Optional[str] = None):
        """
        初始化安全HTTP客户端
        :param verify_ssl: 是否验证SSL证书
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        :param cert_file: 自定义证书文件路径
        """
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.cert_file = cert_file or certifi.where()  # 使用certifi提供的证书包
        
        # 创建会话
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认头部
        self.session.headers.update({
            'User-Agent': 'GEO-Validator-Secure-Client/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _prepare_headers(self, additional_headers: Optional[Dict] = None) -> Dict:
        """准备请求头部"""
        headers = self.session.headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def get(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全GET请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('GET', url, headers=headers, **kwargs)
    
    def post(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全POST请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('POST', url, headers=headers, **kwargs)
    
    def put(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全PUT请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('PUT', url, headers=headers, **kwargs)
    
    def delete(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全DELETE请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('DELETE', url, headers=headers, **kwargs)
    
    def _make_request(self, method: str, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """执行安全请求"""
        # 确保使用HTTPS（除非明确指定不验证SSL）
        if self.verify_ssl and not url.startswith('https://'):
            logger.warning(f"尝试对非HTTPS URL 进行安全请求: {url}")
        
        # 设置默认参数
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('verify', self.cert_file if self.verify_ssl else False)
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            
            # 记录请求指标
            logger.info(f"API请求: {method} {url} -> {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
            
            # 验证响应
            self._validate_response(response)
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {str(e)}")
            raise
    
    def _validate_response(self, response: requests.Response) -> None:
        """验证响应的安全性"""
        # 检查内容类型是否符合预期
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/json' in content_type:
            # 尝试解析JSON以验证响应完整性
            try:
                response.json()
            except ValueError:
                raise ValueError("响应不是有效的JSON格式")
        
        # 检查是否有安全相关的头部
        if 'server' in response.headers:
            server_header = response.headers['server']
            logger.debug(f"Server: {server_header}")
    
    def close(self):
        """关闭会话"""
        self.session.close()


class CertificatePinner:
    """证书固定器"""
    
    def __init__(self, pinned_certificates: Dict[str, str]):
        """
        初始化证书固定器
        :param pinned_certificates: 主机名到证书指纹的映射
        """
        self.pinned_certificates = pinned_certificates
    
    def verify_certificate(self, hostname: str, certificate_der: bytes) -> bool:
        """验证证书是否与固定的指纹匹配"""
        if hostname not in self.pinned_certificates:
            return True  # 如果没有固定证书，则跳过验证
        
        expected_fingerprint = self.pinned_certificates[hostname]
        actual_fingerprint = hashlib.sha256(certificate_der).hexdigest()
        
        return hmac.compare_digest(expected_fingerprint, actual_fingerprint)


# 全局HTTP客户端实例
_http_client = None


def get_http_client(**kwargs) -> SecureHttpClient:
    """获取安全HTTP客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = SecureHttpClient(**kwargs)
    return _http_client


def reset_http_client():
    """重置HTTP客户端实例"""
    global _http_client
    if _http_client:
        _http_client.close()
    _http_client = None
