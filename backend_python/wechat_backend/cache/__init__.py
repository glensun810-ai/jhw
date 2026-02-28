"""
缓存模块

P2-2 修复：引入 Redis 缓存层
P2-7 修复：智能缓存预热
P1-CACHE 修复：内存缓存导入失败

模块：
- redis_config: Redis 配置
- redis_cache: Redis 缓存服务
- task_status_cache: 任务状态缓存
- cache_decorator: 缓存装饰器
- cache_warmup: 缓存预热核心
- cache_warmup_tasks: 预热任务实现
- cache_warmup_scheduler: 定时调度器
- cache_warmup_init: 预热初始化
- api_cache: API 缓存（含全局 memory_cache 实例）

@author: 系统架构组
@date: 2026-02-28
"""

from wechat_backend.cache.redis_config import (
    RedisConfig,
    get_redis_config,
    redis_config
)

from wechat_backend.cache.redis_cache import (
    RedisCacheService,
    get_redis_cache,
    init_redis_cache,
    cached
)

from wechat_backend.cache.task_status_cache import (
    TaskStatusCacheService,
    TaskResultCacheService,
    get_task_status_cache,
    get_task_result_cache,
    get_cached_task_status,
    set_cached_task_status,
    update_cached_task_status,
    get_or_set_task_status
)

# P2-7: 缓存预热
from wechat_backend.cache.cache_warmup_init import (
    start_cache_warmup,
    get_warmup_status,
)

from wechat_backend.cache.cache_warmup import (
    get_warmup_engine,
    register_warmup_task,
    execute_warmup,
)

from wechat_backend.cache.cache_warmup_tasks import (
    warmup_popular_brands,
    warmup_user_stats,
    warmup_popular_questions,
    warmup_recent_reports,
    warmup_api_responses,
)

# P1-CACHE: 全局内存缓存实例
from wechat_backend.cache.api_cache import memory_cache

__all__ = [
    # 配置
    'RedisConfig',
    'get_redis_config',
    'redis_config',

    # 缓存服务
    'RedisCacheService',
    'get_redis_cache',
    'init_redis_cache',

    # 缓存装饰器
    'cached',

    # 任务状态缓存
    'TaskStatusCacheService',
    'TaskResultCacheService',
    'get_task_status_cache',
    'get_task_result_cache',
    'get_cached_task_status',
    'set_cached_task_status',
    'update_cached_task_status',
    'get_or_set_task_status',

    # P2-7: 缓存预热
    'start_cache_warmup',
    'get_warmup_status',
    'get_warmup_engine',
    'register_warmup_task',
    'execute_warmup',
    'warmup_popular_brands',
    'warmup_user_stats',
    'warmup_popular_questions',
    'warmup_recent_reports',
    'warmup_api_responses',

    # P1-CACHE: 全局内存缓存实例
    'memory_cache',
]
