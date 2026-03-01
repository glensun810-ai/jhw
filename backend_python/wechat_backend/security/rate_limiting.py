"""
API限流模块
提供多种限流策略和实现
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Callable
from functools import wraps
from flask import request, jsonify
import hashlib
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """基础限流器"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        raise NotImplementedError("子类必须实现 is_allowed 方法")


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口限流器"""
    
    def __init__(self):
        super().__init__()
        self.requests = defaultdict(deque)
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """检查请求是否被允许（滑动窗口算法）"""
        with self.lock:
            now = time.time()
            window_queue = self.requests[key]
            
            # 移除超出时间窗口的请求记录
            while window_queue and now - window_queue[0] > window:
                window_queue.popleft()
            
            # 检查是否超过限制
            if len(window_queue) < limit:
                window_queue.append(now)
                return True
            else:
                return False


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶限流器"""
    
    def __init__(self):
        super().__init__()
        self.buckets = {}
    
    def is_allowed(self, key: str, capacity: int, refill_rate: float) -> bool:
        """检查请求是否被允许（令牌桶算法）"""
        with self.lock:
            now = time.time()
            
            if key not in self.buckets:
                self.buckets[key] = {
                    'tokens': capacity,
                    'last_refill': now
                }
            
            bucket = self.buckets[key]
            
            # 计算应该添加的令牌数
            time_passed = now - bucket['last_refill']
            tokens_to_add = time_passed * refill_rate
            bucket['tokens'] = min(capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now
            
            # 检查是否有足够的令牌
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            else:
                return False


class IPBasedRateLimiter:
    """基于IP的限流器"""
    
    def __init__(self, sliding_window_limiter: SlidingWindowRateLimiter = None):
        self.sliding_window_limiter = sliding_window_limiter or SlidingWindowRateLimiter()
        # 默认限制：每分钟100个请求
        self.default_limits = {
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
            'requests_per_day': 10000
        }
    
    def get_client_ip(self) -> str:
        """获取客户端IP地址"""
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
        elif request.headers.get('X-Real-IP'):
            ip = request.headers.get('X-Real-IP')
        else:
            ip = request.remote_addr
        return ip
    
    def is_allowed(self, 
                   limit_type: str = 'requests_per_minute', 
                   custom_limit: int = None, 
                   custom_window: int = None) -> bool:
        """检查IP是否被允许发送请求"""
        client_ip = self.get_client_ip()
        
        if custom_limit and custom_window:
            limit = custom_limit
            window = custom_window
        else:
            # 根据限制类型设置默认值
            if limit_type == 'requests_per_minute':
                limit, window = self.default_limits['requests_per_minute'], 60
            elif limit_type == 'requests_per_hour':
                limit, window = self.default_limits['requests_per_hour'], 3600
            elif limit_type == 'requests_per_day':
                limit, window = self.default_limits['requests_per_day'], 86400
            else:
                limit, window = 100, 60  # 默认值
        
        key = f"ip:{client_ip}:{limit_type}"
        return self.sliding_window_limiter.is_allowed(key, limit, window)
    
    def get_rate_limit_headers(self, limit_type: str = 'requests_per_minute') -> Dict[str, str]:
        """获取限流相关的HTTP头信息"""
        client_ip = self.get_client_ip()
        
        # 根据限制类型设置值
        if limit_type == 'requests_per_minute':
            limit, window = self.default_limits['requests_per_minute'], 60
        elif limit_type == 'requests_per_hour':
            limit, window = self.default_limits['requests_per_hour'], 3600
        elif limit_type == 'requests_per_day':
            limit, window = self.default_limits['requests_per_day'], 86400
        else:
            limit, window = 100, 60
        
        key = f"ip:{client_ip}:{limit_type}"
        window_queue = self.sliding_window_limiter.requests[key]
        
        remaining = max(0, limit - len(window_queue))
        reset_time = int(time.time()) + window
        
        return {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time)
        }


class EndpointRateLimiter:
    """端点级别的限流器"""
    
    def __init__(self, sliding_window_limiter: SlidingWindowRateLimiter = None):
        self.sliding_window_limiter = sliding_window_limiter or SlidingWindowRateLimiter()
        # 不同端点的默认限制
        self.endpoint_limits = {
            '/api/perform-brand-test': {'limit': 10, 'window': 60},  # 每分钟10次
            '/api/login': {'limit': 5, 'window': 60},  # 每分钟5次
            '/api/test': {'limit': 100, 'window': 60},  # 每分钟100次
            '/api/platform-status': {'limit': 50, 'window': 60},  # 每分钟50次
            '/test/status/': {'limit': 30, 'window': 60},  # 每分钟30次
            '/api/test-history': {'limit': 20, 'window': 60},  # 每分钟20次
            '/api/test-record': {'limit': 20, 'window': 60},  # 每分钟20次
        }
    
    def is_allowed(self, endpoint: str = None, custom_limit: int = None, custom_window: int = None) -> bool:
        """检查端点请求是否被允许"""
        if endpoint is None:
            endpoint = request.endpoint or request.path
        
        if custom_limit and custom_window:
            limit, window = custom_limit, custom_window
        else:
            limits = self.endpoint_limits.get(endpoint, {'limit': 100, 'window': 60})
            limit, window = limits['limit'], limits['window']
        
        # 使用客户端IP和端点作为限流键
        client_ip = request.remote_addr
        key = f"endpoint:{endpoint}:ip:{client_ip}"
        
        return self.sliding_window_limiter.is_allowed(key, limit, window)
    
    def get_rate_limit_headers(self, endpoint: str = None) -> Dict[str, str]:
        """获取端点限流相关的HTTP头信息"""
        if endpoint is None:
            endpoint = request.endpoint or request.path
        
        limits = self.endpoint_limits.get(endpoint, {'limit': 100, 'window': 60})
        limit, window = limits['limit'], limits['window']
        
        client_ip = request.remote_addr
        key = f"endpoint:{endpoint}:ip:{client_ip}"
        window_queue = self.sliding_window_limiter.requests[key]
        
        remaining = max(0, limit - len(window_queue))
        reset_time = int(time.time()) + window
        
        return {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time)
        }


class CombinedRateLimiter:
    """组合限流器 - 同时应用IP和端点级别的限流"""
    
    def __init__(self):
        self.ip_limiter = IPBasedRateLimiter()
        self.endpoint_limiter = EndpointRateLimiter()
    
    def is_allowed(self, 
                   ip_limit_type: str = 'requests_per_minute',
                   endpoint: str = None,
                   custom_ip_limit: int = None,
                   custom_ip_window: int = None,
                   custom_endpoint_limit: int = None,
                   custom_endpoint_window: int = None) -> bool:
        """检查请求是否被允许（同时检查IP和端点限制）"""
        # 检查IP级别的限制
        ip_allowed = self.ip_limiter.is_allowed(
            ip_limit_type, custom_ip_limit, custom_ip_window
        )
        
        # 检查端点级别的限制
        endpoint_allowed = self.endpoint_limiter.is_allowed(
            endpoint, custom_endpoint_limit, custom_endpoint_window
        )
        
        return ip_allowed and endpoint_allowed


def rate_limit(limit: int, window: int, per: str = 'ip'):
    """装饰器：应用限流"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = CombinedRateLimiter()
            
            if per == 'ip':
                # 只检查IP级别的限制
                client_ip = request.remote_addr
                key = f"ip:{client_ip}:global"
                allowed = limiter.ip_limiter.sliding_window_limiter.is_allowed(key, limit, window)
            elif per == 'endpoint':
                # 只检查端点级别的限制
                endpoint = request.endpoint or request.path
                allowed = limiter.endpoint_limiter.is_allowed(endpoint, limit, window)
            else:
                # 检查组合限制
                allowed = limiter.is_allowed(
                    endpoint=request.endpoint or request.path,
                    custom_ip_limit=limit,
                    custom_ip_window=window
                )
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {per}: {request.remote_addr} on {request.path}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again later.'
                }), 429
            
            # 添加限流头信息
            resp = f(*args, **kwargs)
            if hasattr(resp, 'headers'):
                headers = limiter.ip_limiter.get_rate_limit_headers()
                for header, value in headers.items():
                    resp.headers[header] = value
            
            return resp
        return decorated_function
    return decorator


# 全局限流器实例
combined_limiter = CombinedRateLimiter()


def check_rate_limit() -> bool:
    """检查全局限流"""
    return combined_limiter.is_allowed()


def get_rate_limit_info() -> Dict[str, str]:
    """获取限流信息"""
    return combined_limiter.ip_limiter.get_rate_limit_headers()