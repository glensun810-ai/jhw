"""
令牌桶速率限制器

实现：
1. 令牌桶算法控制 API 请求频率
2. 智能等待：如果桶中有足够令牌，立即执行
3. 支持多模型独立限流

参考：
- AWS API Gateway: 令牌桶限流
- Google Cloud Endpoints: 自适应速率限制
"""

import asyncio
import time
from typing import Dict, Optional
from wechat_backend.logging_config import api_logger


class TokenBucket:
    """
    令牌桶速率限制器
    
    算法说明：
    1. 桶以固定速率生成令牌
    2. 每次请求消耗一个令牌
    3. 如果桶为空，等待直到有足够令牌
    4. 桶有最大容量，防止令牌无限累积
    """
    
    def __init__(
        self,
        rate: float = 1.0,  # 每秒生成的令牌数
        capacity: int = 5,  # 桶的最大容量
        initial_tokens: Optional[int] = None  # 初始令牌数
    ):
        """
        初始化令牌桶
        
        参数：
            rate: 令牌生成速率（个/秒）
            capacity: 桶容量上限
            initial_tokens: 初始令牌数（默认为 capacity）
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
        api_logger.debug(
            f"[TokenBucket] 初始化：rate={rate} tokens/s, "
            f"capacity={capacity}, initial={self.tokens}"
        )
    
    def _refill(self):
        """补充令牌（基于时间流逝）"""
        now = time.monotonic()
        elapsed = now - self.last_update
        
        # 计算新增令牌数
        new_tokens = elapsed * self.rate
        
        # 更新令牌数（不超过容量）
        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now
            
            api_logger.debug(
                f"[TokenBucket] 补充令牌：elapsed={elapsed:.3f}s, "
                f"new={new_tokens:.2f}, total={self.tokens:.2f}"
            )
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        获取令牌（如果不足则等待）
        
        参数：
            tokens: 需要的令牌数
        
        返回：
            等待时间（秒）
        """
        async with self._lock:
            wait_time = 0.0
            
            while True:
                self._refill()
                
                if self.tokens >= tokens:
                    # 有足够令牌，立即消耗
                    self.tokens -= tokens
                    api_logger.debug(
                        f"[TokenBucket] 获取令牌：need={tokens}, "
                        f"wait={wait_time:.3f}s, remaining={self.tokens:.2f}"
                    )
                    return wait_time
                
                # 计算需要等待的时间
                tokens_needed = tokens - self.tokens
                wait_needed = tokens_needed / self.rate
                
                api_logger.debug(
                    f"[TokenBucket] 令牌不足：need={tokens}, "
                    f"have={self.tokens:.2f}, wait={wait_needed:.3f}s"
                )
                
                # 释放锁并等待
                self._lock.release()
                try:
                    await asyncio.sleep(wait_needed)
                    wait_time += wait_needed
                finally:
                    await self._lock.acquire()
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        尝试获取令牌（不等待）
        
        参数：
            tokens: 需要的令牌数
        
        返回：
            是否成功获取
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict:
        """获取桶状态"""
        self._refill()
        return {
            'tokens': round(self.tokens, 2),
            'capacity': self.capacity,
            'rate': self.rate,
            'utilization': round(1 - (self.tokens / self.capacity), 2)
        }


class RateLimiter:
    """
    速率限制器管理器
    
    功能：
    1. 为每个模型维护独立的令牌桶
    2. 统一的限流配置
    3. 监控和统计
    """
    
    # 默认配置（每秒请求数）
    DEFAULT_RATES = {
        'deepseek-chat': 2.0,      # DeepSeek: 2 次/秒
        'doubao-seed-2-0-mini-260215': 5.0,  # 豆包 Mini: 5 次/秒
        'doubao-seed-2-0-pro-260215': 3.0,   # 豆包 Pro: 3 次/秒
        'doubao-seed-2-0-lite-260215': 5.0,  # 豆包 Lite: 5 次/秒
        'doubao-seed-1-8-251228': 3.0,       # 豆包 1.8: 3 次/秒
        'qwen-plus': 2.0,          # 通义千问：2 次/秒
        'gpt-3.5-turbo': 3.0,      # GPT-3.5: 3 次/秒
        'gemini-pro': 2.0,         # Gemini: 2 次/秒
        'default': 2.0,            # 默认：2 次/秒
    }
    
    def __init__(self):
        """初始化速率限制器"""
        self._buckets: Dict[str, TokenBucket] = {}
        self._stats = {
            'total_requests': 0,
            'waited_requests': 0,
            'total_wait_time': 0.0
        }
    
    def get_bucket(self, model_name: str) -> TokenBucket:
        """
        获取或创建模型的令牌桶
        
        参数：
            model_name: 模型名称
        
        返回：
            TokenBucket 实例
        """
        if model_name not in self._buckets:
            # 获取该模型的速率限制
            rate = self.DEFAULT_RATES.get(model_name, self.DEFAULT_RATES['default'])
            
            # 创建令牌桶（容量 = 速率 × 2，允许短暂突发）
            capacity = max(5, int(rate * 2))
            
            self._buckets[model_name] = TokenBucket(
                rate=rate,
                capacity=capacity,
                initial_tokens=capacity  # 初始满桶
            )
            
            api_logger.info(
                f"[RateLimiter] 创建令牌桶：model={model_name}, "
                f"rate={rate}/s, capacity={capacity}"
            )
        
        return self._buckets[model_name]
    
    async def acquire(self, model_name: str) -> float:
        """
        获取令牌（等待）
        
        参数：
            model_name: 模型名称
        
        返回：
            等待时间（秒）
        """
        bucket = self.get_bucket(model_name)
        wait_time = await bucket.acquire()
        
        # 更新统计
        self._stats['total_requests'] += 1
        if wait_time > 0:
            self._stats['waited_requests'] += 1
            self._stats['total_wait_time'] += wait_time
        
        if wait_time > 0:
            api_logger.info(
                f"[RateLimiter] 频率控制：model={model_name}, "
                f"wait={wait_time:.3f}s"
            )
        
        return wait_time
    
    async def try_acquire(self, model_name: str) -> bool:
        """
        尝试获取令牌（不等待）
        
        参数：
            model_name: 模型名称
        
        返回：
            是否成功
        """
        bucket = self.get_bucket(model_name)
        success = await bucket.try_acquire()
        
        self._stats['total_requests'] += 1
        
        return success
    
    def get_status(self, model_name: str = None) -> Dict:
        """
        获取状态
        
        参数：
            model_name: 模型名称（可选）
        
        返回：
            状态字典
        """
        if model_name:
            bucket = self.get_bucket(model_name)
            return {
                'model': model_name,
                'bucket': bucket.get_status(),
                'stats': self._stats.copy()
            }
        else:
            return {
                'models': {
                    name: bucket.get_status()
                    for name, bucket in self._buckets.items()
                },
                'stats': self._stats.copy()
            }


# 全局速率限制器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局速率限制器"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def acquire_rate_limit(model_name: str) -> float:
    """
    便捷函数：获取速率限制
    
    参数：
        model_name: 模型名称
    
    返回：
        等待时间（秒）
    """
    return await get_rate_limiter().acquire(model_name)


def get_rate_limit_status(model_name: str = None) -> Dict:
    """
    便捷函数：获取速率限制状态
    
    参数：
        model_name: 模型名称（可选）
    
    返回：
        状态字典
    """
    return get_rate_limiter().get_status(model_name)
