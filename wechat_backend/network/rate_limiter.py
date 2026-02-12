"""
速率限制器
实现多种速率限制算法
"""

import time
import threading
from collections import deque, defaultdict
from typing import Dict, Optional
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """速率限制算法类型"""
    TOKEN_BUCKET = "token_bucket"
    LEAKING_BUCKET = "leaking_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class RateLimiter:
    """速率限制器基类"""
    
    def __init__(self, algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET):
        self.algorithm = algorithm
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """检查请求是否被允许"""
        raise NotImplementedError("子类必须实现 is_allowed 方法")


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.TOKEN_BUCKET)
        self.buckets = {}
    
    def is_allowed(self, key: str, capacity: int, refill_rate: float) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键（如用户ID、IP地址等）
        :param capacity: 桶容量
        :param refill_rate: 令牌填充速率（每秒填充的令牌数）
        """
        with self.lock:
            now = time.time()
            
            if key not in self.buckets:
                # 初始化桶
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


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.SLIDING_WINDOW)
        self.windows = defaultdict(deque)
    
    def is_allowed(self, key: str, limit: int, window_size: int) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 时间窗口内的最大请求数
        :param window_size: 时间窗口大小（秒）
        """
        with self.lock:
            now = time.time()
            window = self.windows[key]
            
            # 移除超出时间窗口的请求记录
            while window and now - window[0] > window_size:
                window.popleft()
            
            # 检查是否超过限制
            if len(window) < limit:
                window.append(now)
                return True
            else:
                return False


class FixedWindowRateLimiter(RateLimiter):
    """固定窗口算法速率限制器"""
    
    def __init__(self):
        super().__init__(RateLimitAlgorithm.FIXED_WINDOW)
        self.windows = {}
    
    def is_allowed(self, key: str, limit: int, window_size: int) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 时间窗口内的最大请求数
        :param window_size: 时间窗口大小（秒）
        """
        with self.lock:
            now = time.time()
            window_start = int(now // window_size) * window_size  # 当前窗口开始时间
            
            if key not in self.windows:
                self.windows[key] = {'count': 0, 'window_start': window_start}
            
            window = self.windows[key]
            
            # 检查是否进入新窗口
            if now >= window['window_start'] + window_size:
                # 重置窗口
                window['count'] = 1
                window['window_start'] = window_start
                return True
            else:
                # 检查是否超过限制
                if window['count'] < limit:
                    window['count'] += 1
                    return True
                else:
                    return False


class RateLimiterManager:
    """速率限制器管理器"""
    
    def __init__(self):
        self.limiters = {
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketRateLimiter(),
            RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowRateLimiter(),
            RateLimitAlgorithm.FIXED_WINDOW: FixedWindowRateLimiter(),
        }
        self.default_algorithm = RateLimitAlgorithm.SLIDING_WINDOW
        self.lock = threading.Lock()
    
    def is_allowed(self, 
                   key: str, 
                   limit: int, 
                   window_size: int, 
                   algorithm: RateLimitAlgorithm = None,
                   capacity: int = None,
                   refill_rate: float = None) -> bool:
        """
        检查请求是否被允许
        :param key: 限流键
        :param limit: 限制数量
        :param window_size: 时间窗口大小
        :param algorithm: 限流算法
        :param capacity: 桶容量（令牌桶算法）
        :param refill_rate: 填充速率（令牌桶算法）
        """
        algorithm = algorithm or self.default_algorithm
        
        limiter = self.limiters[algorithm]
        
        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            # 令牌桶使用capacity和refill_rate参数
            cap = capacity or limit
            rate = refill_rate or (limit / window_size)
            return limiter.is_allowed(key, cap, rate)
        else:
            # 其他算法使用limit和window_size参数
            return limiter.is_allowed(key, limit, window_size)
    
    def get_limiter(self, algorithm: RateLimitAlgorithm):
        """获取指定算法的限流器"""
        return self.limiters[algorithm]


# 全局速率限制器实例
_rate_limiter_manager = None


def get_rate_limiter_manager() -> RateLimiterManager:
    """获取速率限制器管理器实例"""
    global _rate_limiter_manager
    if _rate_limiter_manager is None:
        _rate_limiter_manager = RateLimiterManager()
    return _rate_limiter_manager


def is_rate_limited(key: str, limit: int, window_size: int, **kwargs) -> bool:
    """便捷函数：检查是否被限流"""
    manager = get_rate_limiter_manager()
    return not manager.is_allowed(key, limit, window_size, **kwargs)


def check_rate_limit(key: str, limit: int, window_size: int, **kwargs) -> Dict[str, Any]:
    """检查速率限制状态"""
    manager = get_rate_limiter_manager()
    allowed = manager.is_allowed(key, limit, window_size, **kwargs)
    
    return {
        'allowed': allowed,
        'limit': limit,
        'window_size': window_size,
        'key': key
    }
