"""
性能优化模块

功能：
- 并发控制
- 缓存管理
- 限流策略

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from collections import OrderedDict
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger


class ConcurrencyController:
    """
    并发控制器
    
    限制同时执行的任务数量，防止系统过载
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        初始化并发控制器
        
        参数:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._total_executed = 0
        self._total_failed = 0
        self.logger = api_logger
    
    async def execute(
        self,
        coro: Awaitable[Any],
        task_name: str = 'unnamed'
    ) -> Any:
        """
        执行任务（带并发限制）
        
        参数:
            coro: 协程对象
            task_name: 任务名称
            
        返回:
            任务执行结果
        """
        async with self._semaphore:
            self._active_count += 1
            self._total_executed += 1
            
            start_time = time.time()
            try:
                result = await coro
                
                elapsed = time.time() - start_time
                self.logger.info("task_executed", extra={
                    'event': 'task_executed',
                    'task_name': task_name,
                    'elapsed_time': round(elapsed, 3),
                    'active_count': self._active_count,
                    'timestamp': datetime.now().isoformat()
                })
                
                return result
            except Exception as e:
                self._total_failed += 1
                self.logger.error("task_failed", extra={
                    'event': 'task_failed',
                    'task_name': task_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                raise
            finally:
                self._active_count -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            统计信息字典
        """
        return {
            'max_concurrent': self.max_concurrent,
            'active_count': self._active_count,
            'total_executed': self._total_executed,
            'total_failed': self._total_failed,
            'success_rate': round(
                (self._total_executed - self._total_failed) / self._total_executed * 100, 2
            ) if self._total_executed > 0 else 100.0
        }


class RateLimiter:
    """
    限流器
    
    限制单位时间内的请求数量
    """
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """
        初始化限流器
        
        参数:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: OrderedDict = OrderedDict()
        self.logger = api_logger
    
    async def acquire(self) -> bool:
        """
        获取许可
        
        返回:
            是否获取成功
        """
        now = time.time()
        
        # 清理过期请求
        self._cleanup_expired(now)
        
        # 检查是否超过限制
        if len(self._requests) >= self.max_requests:
            self.logger.warning("rate_limit_exceeded", extra={
                'event': 'rate_limit_exceeded',
                'max_requests': self.max_requests,
                'time_window': self.time_window,
                'timestamp': datetime.now().isoformat()
            })
            return False
        
        # 记录请求
        self._requests[now] = True
        return True
    
    def _cleanup_expired(self, now: float) -> None:
        """
        清理过期请求
        
        参数:
            now: 当前时间戳
        """
        cutoff = now - self.time_window
        
        while self._requests and next(iter(self._requests)) < cutoff:
            self._requests.popitem(last=False)
    
    async def execute(
        self,
        coro: Awaitable[Any],
        task_name: str = 'unnamed'
    ) -> Optional[Any]:
        """
        执行任务（带限流）
        
        参数:
            coro: 协程对象
            task_name: 任务名称
            
        返回:
            任务执行结果，如果限流则返回 None
        """
        if not await self.acquire():
            return None
        
        return await coro


class LRUCache:
    """
    LRU 缓存
    
    最近最少使用的缓存淘汰策略
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化 LRU 缓存
        
        参数:
            max_size: 最大缓存条目数
            ttl: 缓存超时时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0
        self.logger = api_logger
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        参数:
            key: 缓存键
            
        返回:
            缓存值，如果不存在或已过期则返回 None
        """
        # 检查是否存在
        if key not in self._cache:
            self._misses += 1
            return None
        
        # 检查是否过期
        if self._is_expired(key):
            self._delete(key)
            self._misses += 1
            return None
        
        # 移动到末尾（最近使用）
        self._cache.move_to_end(key)
        self._hits += 1
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存
        
        参数:
            key: 缓存键
            value: 缓存值
        """
        # 如果已存在，先删除
        if key in self._cache:
            self._delete(key)
        
        # 如果超过最大大小，删除最旧的条目
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._delete(oldest_key)
        
        # 添加新条目
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        参数:
            key: 缓存键
            
        返回:
            是否删除成功
        """
        return self._delete(key)
    
    def _delete(self, key: str) -> bool:
        """
        内部删除方法
        
        参数:
            key: 缓存键
            
        返回:
            是否删除成功
        """
        if key in self._cache:
            del self._cache[key]
            if key in self._timestamps:
                del self._timestamps[key]
            return True
        return False
    
    def _is_expired(self, key: str) -> bool:
        """
        检查是否过期
        
        参数:
            key: 缓存键
            
        返回:
            是否过期
        """
        if key not in self._timestamps:
            return True
        
        return (time.time() - self._timestamps[key]) > self.ttl
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            统计信息字典
        """
        total = self._hits + self._misses
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(self._hits / total * 100, 2) if total > 0 else 0.0
        }


# 全局实例
_default_concurrency_controller = ConcurrencyController(max_concurrent=10)
_default_cache = LRUCache(max_size=1000, ttl=300)  # 5 分钟 TTL


def get_concurrency_controller(max_concurrent: Optional[int] = None) -> ConcurrencyController:
    """
    获取并发控制器
    
    参数:
        max_concurrent: 最大并发数（可选）
        
    返回:
        并发控制器实例
    """
    if max_concurrent is not None:
        return ConcurrencyController(max_concurrent=max_concurrent)
    return _default_concurrency_controller


def get_cache(ttl: Optional[int] = None) -> LRUCache:
    """
    获取缓存实例
    
    参数:
        ttl: 缓存超时时间（可选）
        
    返回:
        缓存实例
    """
    if ttl is not None:
        return LRUCache(max_size=1000, ttl=ttl)
    return _default_cache


# 便捷装饰器
def cache_result(key_prefix: str = '', ttl: int = 300):
    """
    缓存结果装饰器
    
    参数:
        key_prefix: 缓存键前缀
        ttl: 缓存超时时间（秒）
    """
    def decorator(func: Callable):
        cache = LRUCache(max_size=1000, ttl=ttl)
        
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator
