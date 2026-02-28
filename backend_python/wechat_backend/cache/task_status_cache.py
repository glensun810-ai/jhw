"""
任务状态缓存服务

P2-2 修复：引入 Redis 缓存层

功能：
- 任务状态缓存
- 任务结果缓存
- 缓存穿透防护
- 缓存更新策略

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from wechat_backend.cache.redis_cache import get_redis_cache, RedisCacheService
from wechat_backend.cache.redis_config import RedisConfig
from wechat_backend.logging_config import api_logger, db_logger


class TaskStatusCacheService:
    """
    任务状态缓存服务
    
    缓存策略：
    1. 查询任务状态时先查缓存
    2. 缓存未命中时查数据库并回写缓存
    3. 任务完成后自动清理缓存
    4. 缓存过期时间 5 分钟
    """
    
    def __init__(self, cache: RedisCacheService = None):
        """
        初始化任务状态缓存服务
        
        参数：
            cache: Redis 缓存实例
        """
        self.cache = cache or get_redis_cache()
        self.ttl = RedisConfig.TTL.TASK_STATUS
    
    def get_task_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态（带缓存）
        
        参数：
            execution_id: 执行 ID
            
        返回：
            任务状态字典，不存在返回 None
        """
        cache_key = RedisConfig.task_status_key(execution_id)
        
        # 尝试从缓存获取
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            api_logger.debug(f"[TaskCache] HIT: {execution_id}")
            return cached_data
        
        api_logger.debug(f"[TaskCache] MISS: {execution_id}")
        return None
    
    def set_task_status(
        self,
        execution_id: str,
        status: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """
        设置任务状态缓存
        
        参数：
            execution_id: 执行 ID
            status: 状态字典
            ttl: 过期时间（秒）
            
        返回：
            是否成功
        """
        cache_key = RedisConfig.task_status_key(execution_id)
        
        # 添加时间戳
        status['_cached_at'] = datetime.now().isoformat()
        
        # 写入缓存
        result = self.cache.set(
            cache_key,
            status,
            ttl=ttl or self.ttl
        )
        
        if result:
            api_logger.debug(f"[TaskCache] SET: {execution_id} (TTL={ttl or self.ttl}s)")
        
        return result
    
    def update_task_status(
        self,
        execution_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新任务状态缓存
        
        参数：
            execution_id: 执行 ID
            updates: 更新字段
            
        返回：
            是否成功
        """
        # 获取现有缓存
        cached_data = self.get_task_status(execution_id)
        
        if cached_data is None:
            # 缓存不存在，直接设置
            return self.set_task_status(execution_id, updates)
        
        # 合并更新
        cached_data.update(updates)
        cached_data['_cached_at'] = datetime.now().isoformat()
        
        # 写回缓存
        cache_key = RedisConfig.task_status_key(execution_id)
        return self.cache.set(cache_key, cached_data, ttl=self.ttl)
    
    def delete_task_status(self, execution_id: str) -> bool:
        """
        删除任务状态缓存
        
        参数：
            execution_id: 执行 ID
            
        返回：
            是否成功
        """
        cache_key = RedisConfig.task_status_key(execution_id)
        result = self.cache.delete(cache_key)
        
        if result:
            api_logger.debug(f"[TaskCache] DELETE: {execution_id}")
        
        return result
    
    def get_or_set(
        self,
        execution_id: str,
        db_query_func,
        ttl: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取或设置任务状态（缓存穿透防护）
        
        用法：
            status = cache_service.get_or_set(
                execution_id,
                lambda: db.query_task_status(execution_id)
            )
        
        参数：
            execution_id: 执行 ID
            db_query_func: 数据库查询函数
            ttl: 过期时间（秒）
            
        返回：
            任务状态
        """
        # 尝试从缓存获取
        cached_data = self.get_task_status(execution_id)
        if cached_data is not None:
            return cached_data
        
        # 缓存未命中，查询数据库
        try:
            db_data = db_query_func()
            
            if db_data is not None:
                # 写入缓存
                self.set_task_status(execution_id, db_data, ttl)
                return db_data
            else:
                # 数据库也不存在，设置空缓存防止穿透
                # 使用较短的过期时间
                empty_data = {'_empty': True, '_timestamp': datetime.now().isoformat()}
                self.cache.set(
                    RedisConfig.task_status_key(execution_id),
                    empty_data,
                    ttl=60  # 空缓存只保留 1 分钟
                )
                return None
                
        except Exception as e:
            api_logger.error(f"[TaskCache] get_or_set 错误：{e}")
            return None


class TaskResultCacheService:
    """
    任务结果缓存服务
    
    缓存策略：
    1. 任务完成后缓存结果
    2. 结果较大时使用压缩
    3. 缓存过期时间 30 分钟
    """
    
    def __init__(self, cache: RedisCacheService = None):
        """
        初始化任务结果缓存服务
        
        参数：
            cache: Redis 缓存实例
        """
        self.cache = cache or get_redis_cache()
        self.ttl = RedisConfig.TTL.DIAGNOSIS_REPORT
    
    def get_task_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        参数：
            execution_id: 执行 ID
            
        返回：
            任务结果
        """
        cache_key = RedisConfig.task_result_key(execution_id)
        return self.cache.get(cache_key)
    
    def set_task_result(
        self,
        execution_id: str,
        result: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """
        设置任务结果缓存
        
        参数：
            execution_id: 执行 ID
            result: 结果数据
            ttl: 过期时间（秒）
            
        返回：
            是否成功
        """
        cache_key = RedisConfig.task_result_key(execution_id)
        
        # 添加时间戳
        result['_cached_at'] = datetime.now().isoformat()
        
        return self.cache.set(
            cache_key,
            result,
            ttl=ttl or self.ttl
        )
    
    def delete_task_result(self, execution_id: str) -> bool:
        """
        删除任务结果缓存
        
        参数：
            execution_id: 执行 ID
            
        返回：
            是否成功
        """
        cache_key = RedisConfig.task_result_key(execution_id)
        return self.cache.delete(cache_key)


# 全局服务实例
_task_status_cache: Optional[TaskStatusCacheService] = None
_task_result_cache: Optional[TaskResultCacheService] = None


def get_task_status_cache() -> TaskStatusCacheService:
    """获取任务状态缓存服务"""
    global _task_status_cache
    if _task_status_cache is None:
        _task_status_cache = TaskStatusCacheService()
    return _task_status_cache


def get_task_result_cache() -> TaskResultCacheService:
    """获取任务结果缓存服务"""
    global _task_result_cache
    if _task_result_cache is None:
        _task_result_cache = TaskResultCacheService()
    return _task_result_cache


# 便捷函数
def get_cached_task_status(execution_id: str) -> Optional[Dict[str, Any]]:
    """
    获取缓存的任务状态
    
    参数：
        execution_id: 执行 ID
        
    返回：
        任务状态
    """
    return get_task_status_cache().get_task_status(execution_id)


def set_cached_task_status(
    execution_id: str,
    status: Dict[str, Any]
) -> bool:
    """
    设置缓存的任务状态
    
    参数：
        execution_id: 执行 ID
        status: 状态字典
        
    返回：
        是否成功
    """
    return get_task_status_cache().set_task_status(execution_id, status)


def update_cached_task_status(
    execution_id: str,
    updates: Dict[str, Any]
) -> bool:
    """
    更新缓存的任务状态
    
    参数：
        execution_id: 执行 ID
        updates: 更新字段
        
    返回：
        是否成功
    """
    return get_task_status_cache().update_task_status(execution_id, updates)


def get_or_set_task_status(
    execution_id: str,
    db_query_func
) -> Optional[Dict[str, Any]]:
    """
    获取或设置任务状态（带缓存穿透防护）
    
    参数：
        execution_id: 执行 ID
        db_query_func: 数据库查询函数
        
    返回：
        任务状态
    """
    return get_task_status_cache().get_or_set(execution_id, db_query_func)
