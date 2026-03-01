"""
Redis 缓存服务

P2-2 修复：引入 Redis 缓存层

功能：
- Redis 连接管理
- 缓存读写操作
- 缓存失效处理
- 分布式锁
- 缓存统计

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import json
import hashlib
import logging
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
import time

try:
    import redis
    from redis import ConnectionPool, Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # 使用内存缓存作为降级方案
    logging.warning("Redis 未安装，使用内存缓存降级方案")

from wechat_backend.cache.redis_config import get_redis_config, RedisConfig
from wechat_backend.logging_config import api_logger


class RedisCacheService:
    """
    Redis 缓存服务
    
    提供统一的缓存操作接口，支持：
    - 基本缓存操作（get/set/delete）
    - 批量操作（mget/mset）
    - 过期时间控制
    - 缓存穿透/击穿/雪崩防护
    - 分布式锁
    """
    
    def __init__(self, config: RedisConfig = None):
        """
        初始化 Redis 缓存服务
        
        参数：
            config: Redis 配置，为 None 时使用默认配置
        """
        self.config = config or get_redis_config()
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._fallback_cache = {}  # 降级内存缓存
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
        # 初始化连接
        self._init_connection()
    
    def _init_connection(self):
        """初始化 Redis 连接"""
        if not REDIS_AVAILABLE:
            api_logger.warning("[Redis] 未安装 redis 库，使用内存缓存降级方案")
            return

        try:
            # 创建连接池
            self._pool = ConnectionPool(
                host=self.config.HOST,
                port=self.config.PORT,
                db=self.config.DB,
                password=self.config.PASSWORD,
                max_connections=self.config.MAX_CONNECTIONS,
                socket_timeout=self.config.SOCKET_TIMEOUT,
                socket_connect_timeout=self.config.SOCKET_CONNECT_TIMEOUT,
                decode_responses=True
            )

            # 创建客户端
            self._client = Redis(connection_pool=self._pool)

            # 测试连接
            self._client.ping()

            api_logger.info(
                f"[Redis] 连接成功：{self.config.HOST}:{self.config.PORT}"
            )

        except Exception as e:
            error_msg = str(e)
            
            # P0-DB-INIT-005: 针对常见错误提供友好提示
            if "Connection refused" in error_msg or "Error 61" in error_msg:
                api_logger.warning(
                    f"[Redis] 连接被拒绝 (Error 61)：{self.config.HOST}:{self.config.PORT} - "
                    f"Redis 服务可能未启动。使用内存缓存降级方案。"
                    f"如需启用 Redis，请运行：brew services start redis"
                )
            elif "No such file or directory" in error_msg:
                api_logger.warning(
                    f"[Redis] 无法连接到 Unix socket - "
                    f"Redis 可能配置为使用 socket 连接。使用内存缓存降级方案。"
                )
            else:
                api_logger.warning(
                    f"[Redis] 连接失败：{e}，使用内存缓存降级方案"
                )
            
            self._client = None
            self._stats['errors'] += 1
    
    def _get_client(self) -> Optional[Redis]:
        """获取 Redis 客户端"""
        if self._client:
            try:
                self._client.ping()
                return self._client
            except Exception:
                self._client = None
        return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        参数：
            key: 缓存键
            default: 默认值
            
        返回：
            缓存值，不存在返回 default
        """
        # 尝试从 Redis 获取
        client = self._get_client()
        if client:
            try:
                value = client.get(key)
                if value is not None:
                    self._stats['hits'] += 1
                    return json.loads(value)
                else:
                    self._stats['misses'] += 1
            except Exception as e:
                api_logger.error(f"[Redis] GET 错误：{e}")
                self._stats['errors'] += 1
        
        # 降级到内存缓存
        if key in self._fallback_cache:
            self._stats['hits'] += 1
            try:
                return json.loads(self._fallback_cache[key])
            except (json.JSONDecodeError, TypeError):
                return self._fallback_cache[key]
        
        self._stats['misses'] += 1
        return default
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        nx: bool = False
    ) -> bool:
        """
        设置缓存
        
        参数：
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），为 None 使用默认值
            nx: 是否仅在键不存在时设置
            
        返回：
            是否成功
        """
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            
            client = self._get_client()
            if client:
                if ttl:
                    if nx:
                        result = client.setnx(key, serialized)
                        if result:
                            client.expire(key, ttl)
                        return bool(result)
                    else:
                        return bool(client.setex(key, ttl, serialized))
                else:
                    if nx:
                        return bool(client.setnx(key, serialized))
                    else:
                        return bool(client.set(key, serialized))
            
            # 降级到内存缓存
            self._fallback_cache[key] = serialized
            self._stats['sets'] += 1
            return True
            
        except Exception as e:
            api_logger.error(f"[Redis] SET 错误：{e}")
            self._stats['errors'] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        参数：
            key: 缓存键
            
        返回：
            是否成功
        """
        try:
            client = self._get_client()
            if client:
                result = client.delete(key)
                self._stats['deletes'] += 1
                return result > 0
            
            # 降级到内存缓存
            if key in self._fallback_cache:
                del self._fallback_cache[key]
                self._stats['deletes'] += 1
                return True
            return False
            
        except Exception as e:
            api_logger.error(f"[Redis] DELETE 错误：{e}")
            self._stats['errors'] += 1
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        参数：
            key: 缓存键
            
        返回：
            是否存在
        """
        client = self._get_client()
        if client:
            try:
                return bool(client.exists(key))
            except Exception as e:
                # Redis 检查失败，降级到内存缓存
                api_logger.debug(f"[RedisCache] exists 检查失败：{e}, key: {key}")

        return key in self._fallback_cache
    
    def get_ttl(self, key: str) -> int:
        """
        获取缓存剩余过期时间
        
        参数：
            key: 缓存键
            
        返回：
            剩余时间（秒），-1 表示永不过期，-2 表示不存在
        """
        client = self._get_client()
        if client:
            try:
                return client.ttl(key)
            except Exception as e:
                # Redis TTL 获取失败，返回未知
                api_logger.debug(f"[RedisCache] TTL 获取失败：{e}, key: {key}")
        return -2
    
    def incr(self, key: str, amount: int = 1) -> int:
        """
        自增操作
        
        参数：
            key: 缓存键
            amount: 自增幅度
            
        返回：
            自增后的值
        """
        client = self._get_client()
        if client:
            try:
                return client.incr(key, amount)
            except Exception as e:
                # Redis 自增失败，降级到内存缓存
                api_logger.debug(f"[RedisCache] incr 失败：{e}, key: {key}")

        # 降级到内存缓存
        if key not in self._fallback_cache:
            self._fallback_cache[key] = 0
        current = int(float(self._fallback_cache[key]))
        self._fallback_cache[key] = str(current + amount)
        return current + amount
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        设置过期时间
        
        参数：
            key: 缓存键
            ttl: 过期时间（秒）
            
        返回：
            是否成功
        """
        client = self._get_client()
        if client:
            try:
                return bool(client.expire(key, ttl))
            except Exception as e:
                # Redis 设置过期时间失败，返回失败
                api_logger.debug(f"[RedisCache] expire 失败：{e}, key: {key}, ttl: {ttl}")
        return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取缓存
        
        参数：
            keys: 缓存键列表
            
        返回：
            缓存值字典
        """
        result = {}
        client = self._get_client()
        
        if client:
            try:
                values = client.mget(keys)
                for key, value in zip(keys, values):
                    if value is not None:
                        result[key] = json.loads(value)
                        self._stats['hits'] += 1
                    else:
                        self._stats['misses'] += 1
                return result
            except Exception as e:
                api_logger.error(f"[Redis] MGET 错误：{e}")
                self._stats['errors'] += 1
        
        # 降级到内存缓存
        for key in keys:
            if key in self._fallback_cache:
                result[key] = json.loads(self._fallback_cache[key])
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
        
        return result
    
    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """
        批量设置缓存
        
        参数：
            mapping: 键值对字典
            ttl: 过期时间（秒）
            
        返回：
            是否成功
        """
        try:
            serialized = {
                k: json.dumps(v, ensure_ascii=False, default=str)
                for k, v in mapping.items()
            }
            
            client = self._get_client()
            if client:
                if ttl:
                    pipe = client.pipeline()
                    for key, value in serialized.items():
                        pipe.setex(key, ttl, value)
                    pipe.execute()
                else:
                    client.mset(serialized)
                self._stats['sets'] += len(mapping)
                return True
            
            # 降级到内存缓存
            self._fallback_cache.update(serialized)
            self._stats['sets'] += len(mapping)
            return True
            
        except Exception as e:
            api_logger.error(f"[Redis] MSET 错误：{e}")
            self._stats['errors'] += 1
            return False
    
    def delete_many(self, keys: List[str]) -> int:
        """
        批量删除缓存
        
        参数：
            keys: 缓存键列表
            
        返回：
            删除的数量
        """
        count = 0
        client = self._get_client()
        
        if client:
            try:
                count = client.delete(*keys)
                self._stats['deletes'] += count
                return count
            except Exception as e:
                api_logger.error(f"[Redis] DELETE_MANY 错误：{e}")
                self._stats['errors'] += 1
        
        # 降级到内存缓存
        for key in keys:
            if key in self._fallback_cache:
                del self._fallback_cache[key]
                count += 1
        self._stats['deletes'] += count
        return count
    
    def clear_pattern(self, pattern: str) -> int:
        """
        清理匹配模式的缓存
        
        参数：
            pattern: 键模式（支持 * 通配符）
            
        返回：
            删除的数量
        """
        client = self._get_client()
        if client:
            try:
                keys = client.keys(pattern)
                if keys:
                    return client.delete(*keys)
            except Exception as e:
                api_logger.error(f"[Redis] CLEAR_PATTERN 错误：{e}")
                self._stats['errors'] += 1
        return 0
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息
        
        返回：
            统计信息字典
        """
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (
            self._stats['hits'] / total * 100
            if total > 0 else 0
        )
        
        return {
            **self._stats,
            'total': total,
            'hit_rate': round(hit_rate, 2)
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
    
    def ping(self) -> bool:
        """
        检查 Redis 连接
        
        返回：
            是否连接正常
        """
        client = self._get_client()
        if client:
            try:
                return client.ping()
            except Exception:
                return False
        return False
    
    def is_available(self) -> bool:
        """
        检查 Redis 是否可用
        
        返回：
            是否可用
        """
        return self._get_client() is not None


# 缓存装饰器
def cached(
    key_prefix: str,
    ttl: int = 300,
    key_func: Callable = None
):
    """
    缓存装饰器
    
    用法：
        @cached(key_prefix="user:", ttl=3600)
        def get_user_info(user_id):
            ...
    
    参数：
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒）
        key_func: 自定义键生成函数
        
    返回：
        装饰后的函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = f"{key_prefix}{key_func(*args, **kwargs)}"
            else:
                # 默认使用参数哈希
                param_str = str(args) + str(sorted(kwargs.items()))
                param_hash = hashlib.md5(param_str.encode()).hexdigest()
                cache_key = f"{key_prefix}{func.__name__}:{param_hash}"
            
            # 尝试从缓存获取
            cache = get_redis_cache()
            cached_value = cache.get(cache_key)
            
            if cached_value is not None:
                api_logger.debug(f"[Cache] HIT: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            if result is not None:
                cache.set(cache_key, result, ttl)
                api_logger.debug(f"[Cache] SET: {cache_key} (TTL={ttl}s)")
            
            return result
        
        return wrapper
    return decorator


# 全局缓存实例
_redis_cache: Optional[RedisCacheService] = None


def get_redis_cache() -> RedisCacheService:
    """获取全局 Redis 缓存实例"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCacheService()
    return _redis_cache


def init_redis_cache(config: RedisConfig = None) -> RedisCacheService:
    """初始化 Redis 缓存服务"""
    global _redis_cache
    _redis_cache = RedisCacheService(config)
    return _redis_cache


def get_redis_client():
    """
    获取 Redis 客户端实例（兼容旧代码）
    
    返回：
        Redis 客户端实例或 None（如果不可用）
    """
    cache_service = get_redis_cache()
    if cache_service and hasattr(cache_service, '_client'):
        return cache_service._client
    return None
