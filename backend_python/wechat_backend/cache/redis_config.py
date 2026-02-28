"""
Redis 缓存配置模块

P2-2 修复：引入 Redis 缓存层

功能：
- Redis 连接配置
- 缓存键命名规范
- 缓存过期时间配置
- 缓存统计配置

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import os
from typing import Optional


class RedisConfig:
    """Redis 配置类"""
    
    # Redis 连接配置
    HOST = os.getenv('REDIS_HOST', 'localhost')
    PORT = int(os.getenv('REDIS_PORT', 6379))
    DB = int(os.getenv('REDIS_DB', 0))
    PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # 连接池配置
    MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', 50))
    SOCKET_TIMEOUT = float(os.getenv('REDIS_SOCKET_TIMEOUT', 5.0))
    SOCKET_CONNECT_TIMEOUT = float(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 5.0))
    
    # 缓存过期时间配置（秒）
    class TTL:
        """缓存过期时间"""
        # 任务状态：5 分钟
        TASK_STATUS = 300
        # 诊断报告：30 分钟
        DIAGNOSIS_REPORT = 1800
        # 用户信息：1 小时
        USER_INFO = 3600
        # 统计数据：10 分钟
        STATISTICS = 600
        # API 响应：5 分钟
        API_RESPONSE = 300
        # 频率限制：1 分钟
        RATE_LIMIT = 60
        # 会话数据：2 小时
        SESSION = 7200
        # 默认：10 分钟
        DEFAULT = 600
    
    # 缓存键前缀
    class KeyPrefix:
        """缓存键前缀"""
        TASK_STATUS = "task:status:"
        TASK_RESULT = "task:result:"
        DIAGNOSIS_REPORT = "diagnosis:report:"
        DIAGNOSIS_RESULTS = "diagnosis:results:"
        USER_INFO = "user:info:"
        USER_HISTORY = "user:history:"
        STATISTICS = "stats:"
        API_RESPONSE = "api:response:"
        RATE_LIMIT = "rate:limit:"
        SESSION = "session:"
        LOCK = "lock:"
    
    # 缓存键模板
    @classmethod
    def task_status_key(cls, execution_id: str) -> str:
        """任务状态缓存键"""
        return f"{cls.KeyPrefix.TASK_STATUS}{execution_id}"
    
    @classmethod
    def task_result_key(cls, execution_id: str) -> str:
        """任务结果缓存键"""
        return f"{cls.KeyPrefix.TASK_RESULT}{execution_id}"
    
    @classmethod
    def diagnosis_report_key(cls, execution_id: str) -> str:
        """诊断报告缓存键"""
        return f"{cls.KeyPrefix.DIAGNOSIS_REPORT}{execution_id}"
    
    @classmethod
    def diagnosis_results_key(cls, execution_id: str) -> str:
        """诊断结果缓存键"""
        return f"{cls.KeyPrefix.DIAGNOSIS_RESULTS}{execution_id}"
    
    @classmethod
    def user_info_key(cls, user_id: str) -> str:
        """用户信息缓存键"""
        return f"{cls.KeyPrefix.USER_INFO}{user_id}"
    
    @classmethod
    def user_history_key(cls, user_id: str, page: int = 0) -> str:
        """用户历史缓存键"""
        return f"{cls.KeyPrefix.USER_HISTORY}{user_id}:page{page}"
    
    @classmethod
    def statistics_key(cls, stat_type: str, date: str = None) -> str:
        """统计数据缓存键"""
        if date:
            return f"{cls.KeyPrefix.STATISTICS}{stat_type}:{date}"
        return f"{cls.KeyPrefix.STATISTICS}{stat_type}"
    
    @classmethod
    def api_response_key(cls, endpoint: str, params_hash: str) -> str:
        """API 响应缓存键"""
        return f"{cls.KeyPrefix.API_RESPONSE}{endpoint}:{params_hash}"
    
    @classmethod
    def rate_limit_key(cls, identifier: str, action: str) -> str:
        """频率限制缓存键"""
        return f"{cls.KeyPrefix.RATE_LIMIT}{identifier}:{action}"
    
    @classmethod
    def lock_key(cls, resource: str, identifier: str) -> str:
        """分布式锁缓存键"""
        return f"{cls.KeyPrefix.LOCK}{resource}:{identifier}"
    
    # 连接 URL
    @classmethod
    def get_connection_url(cls) -> str:
        """获取 Redis 连接 URL"""
        if cls.PASSWORD:
            return f"redis://:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DB}"
        return f"redis://{cls.HOST}:{cls.PORT}/{cls.DB}"


# 全局配置实例
redis_config = RedisConfig()


def get_redis_config() -> RedisConfig:
    """获取 Redis 配置实例"""
    return redis_config
