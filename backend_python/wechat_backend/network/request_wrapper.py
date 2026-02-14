"""
统一的HTTP请求封装
提供统一的请求接口和集中处理认证、重试、错误处理等功能
"""

import time
import requests
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import logging
from ..network.security import get_http_client
from ..network.connection_pool import get_session_for_url
from ..network.circuit_breaker import get_circuit_breaker
from ..network.retry_mechanism import SmartRetryHandler
from ..network.rate_limiter import is_rate_limited
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response

logger = logging.getLogger(__name__)


class UnifiedRequestWrapper:
    """统一的HTTP请求封装器"""
    
    def __init__(self, 
                 base_url: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit_key: str = "default",
                 rate_limit_requests: int = 100,
                 rate_limit_window: int = 60):
        """
        初始化请求封装器
        :param base_url: 基础URL
        :param default_headers: 默认请求头
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        :param rate_limit_key: 速率限制键
        :param rate_limit_requests: 时间窗口内的最大请求数
        :param rate_limit_window: 速率限制时间窗口（秒）
        """
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_key = rate_limit_key
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # 初始化组件
        self.retry_handler = SmartRetryHandler(max_attempts=max_retries)
        self.circuit_breaker = get_circuit_breaker(f"unified_request_{rate_limit_key}")
        
    def _prepare_url(self, endpoint: str) -> str:
        """准备完整URL"""
        if self.base_url:
            return urljoin(self.base_url, endpoint.lstrip('/'))
        else:
            return endpoint
    
    def _prepare_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备请求头"""
        headers = self.default_headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def _check_rate_limit(self) -> bool:
        """检查速率限制"""
        return not is_rate_limited(
            key=self.rate_limit_key,
            limit=self.rate_limit_requests,
            window_size=self.rate_limit_window
        )
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     headers: Optional[Dict[str, str]] = None, 
                     **kwargs) -> requests.Response:
        """执行HTTP请求"""
        # 检查速率限制
        if not self._check_rate_limit():
            raise Exception(f"Rate limit exceeded for key: {self.rate_limit_key}")
        
        # 准备URL和头部
        url = self._prepare_url(endpoint)
        prepared_headers = self._prepare_headers(headers)
        
        # 记录请求
        log_api_request(
            method=method.upper(),
            endpoint=url,
            request_size=len(str(kwargs.get('json', '')))
        )
        
        # 记录开始时间
        start_time = time.time()
        
        # 使用连接池发送请求
        session = get_session_for_url(url)
        response = session.request(
            method=method.upper(),
            url=url,
            headers=prepared_headers,
            timeout=kwargs.pop('timeout', self.timeout),
            **kwargs
        )
        
        # 计算响应时间
        response_time = time.time() - start_time
        
        # 记录响应
        log_api_response(
            endpoint=url,
            status_code=response.status_code,
            response_time=response_time,
            response_size=len(response.content)
        )
        
        # 记录指标
        record_api_call(
            platform=self.rate_limit_key,
            endpoint=endpoint,
            status_code=response.status_code,
            response_time=response_time
        )
        
        return response
    
    def get(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """GET请求"""
        return self._make_request('GET', endpoint, headers, **kwargs)
    
    def post(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """POST请求"""
        return self._make_request('POST', endpoint, headers, **kwargs)
    
    def put(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """PUT请求"""
        return self._make_request('PUT', endpoint, headers, **kwargs)
    
    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self._make_request('DELETE', endpoint, headers, **kwargs)
    
    def patch(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """PATCH请求"""
        return self._make_request('PATCH', endpoint, headers, **kwargs)
    
    def request_with_resilience(self, 
                               method: str, 
                               endpoint: str, 
                               headers: Optional[Dict[str, str]] = None, 
                               **kwargs) -> requests.Response:
        """
        使用弹性功能的请求
        包括断路器、重试、速率限制等
        """
        def _request_func():
            return self._make_request(method, endpoint, headers, **kwargs)
        
        # 使用断路器包装请求
        try:
            return self.circuit_breaker.call(_request_func)
        except Exception as e:
            # 记录错误
            record_error(self.rate_limit_key, type(e).__name__, str(e))
            raise e


class AIPlatformRequestWrapper(UnifiedRequestWrapper):
    """AI平台专用请求封装器"""
    
    def __init__(self, 
                 platform_name: str,
                 base_url: str = "",
                 api_key: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        初始化AI平台请求封装器
        :param platform_name: 平台名称
        :param base_url: 基础URL
        :param api_key: API密钥
        :param default_headers: 默认请求头
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        """
        # 设置默认头部，包含认证信息
        headers = default_headers or {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        super().__init__(
            base_url=base_url,
            default_headers=headers,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_key=platform_name
        )
        
        self.platform_name = platform_name
        self.api_key = api_key
    
    def make_ai_request(self, 
                       endpoint: str, 
                       prompt: str, 
                       model: str = None,
                       headers: Optional[Dict[str, str]] = None, 
                       **kwargs) -> requests.Response:
        """发送AI请求"""
        # 添加AI特定的头部
        ai_headers = headers or {}
        if model:
            ai_headers['X-Model'] = model
        
        return self.request_with_resilience('POST', endpoint, ai_headers, **kwargs)


# 全局请求封装器实例
_request_wrappers = {}


def get_request_wrapper(name: str, **kwargs) -> UnifiedRequestWrapper:
    """获取指定名称的请求封装器"""
    global _request_wrappers
    if name not in _request_wrappers:
        _request_wrappers[name] = UnifiedRequestWrapper(**kwargs)
    return _request_wrappers[name]


def get_ai_request_wrapper(platform_name: str, **kwargs) -> AIPlatformRequestWrapper:
    """获取AI平台请求封装器"""
    return AIPlatformRequestWrapper(platform_name=platform_name, **kwargs)
