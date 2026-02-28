"""
缓存预热配置模块

功能：
- 缓存预热开关配置
- 预热时间配置
- 预热策略配置
- 热门数据配置

参考：P2-7: 智能缓存预热未实现
"""

import os
from typing import List, Dict, Any


class CacheWarmupConfig:
    """缓存预热配置类"""
    
    # ==================== 缓存预热基础配置 ====================
    
    # 是否启用缓存预热
    CACHE_WARMUP_ENABLED = os.environ.get('CACHE_WARMUP_ENABLED', 'true').lower() == 'true'
    
    # 是否启用自动预热（系统启动时自动预热）
    AUTO_WARMUP_ON_STARTUP = os.environ.get('AUTO_WARMUP_ON_STARTUP', 'true').lower() == 'true'
    
    # 是否启用定时预热
    SCHEDULED_WARMUP_ENABLED = os.environ.get('SCHEDULED_WARMUP_ENABLED', 'true').lower() == 'true'
    
    # ==================== 定时任务配置 ====================
    
    # 定时预热时间（cron 表达式）
    # 格式：分 时 日 月 周
    # 默认：每天凌晨 3 点执行
    WARMUP_SCHEDULE = os.environ.get('WARMUP_SCHEDULE', '0 3 * * *')
    
    # 定时预热间隔（分钟，用于简单间隔模式）
    WARMUP_INTERVAL_MINUTES = int(os.environ.get('WARMUP_INTERVAL_MINUTES', '60'))
    
    # ==================== 预热策略配置 ====================
    
    # 预热热门品牌数量
    WARMUP_POPULAR_BRANDS_COUNT = int(os.environ.get('WARMUP_POPULAR_BRANDS_COUNT', '20'))
    
    # 预热热门用户数量
    WARMUP_POPULAR_USERS_COUNT = int(os.environ.get('WARMUP_POPULAR_USERS_COUNT', '50'))
    
    # 预热热门问题数量
    WARMUP_POPULAR_QUESTIONS_COUNT = int(os.environ.get('WARMUP_POPULAR_QUESTIONS_COUNT', '20'))
    
    # 预热诊断报告数量（最近的报告）
    WARMUP_RECENT_REPORTS_COUNT = int(os.environ.get('WARMUP_RECENT_REPORTS_COUNT', '100'))
    
    # ==================== 缓存过期时间配置 ====================
    
    # 品牌统计缓存时间（秒）
    BRAND_STATS_TTL = int(os.environ.get('BRAND_STATS_TTL', '3600'))  # 1 小时
    
    # 用户统计缓存时间（秒）
    USER_STATS_TTL = int(os.environ.get('USER_STATS_TTL', '1800'))  # 30 分钟
    
    # 问题统计缓存时间（秒）
    QUESTION_STATS_TTL = int(os.environ.get('QUESTION_STATS_TTL', '3600'))  # 1 小时
    
    # 诊断报告缓存时间（秒）
    REPORT_STATS_TTL = int(os.environ.get('REPORT_STATS_TTL', '900'))  # 15 分钟
    
    # API 响应缓存时间（秒）
    API_RESPONSE_TTL = int(os.environ.get('API_RESPONSE_TTL', '300'))  # 5 分钟
    
    # ==================== 预热优先级配置 ====================
    
    # 预热任务优先级列表（高优先级的先执行）
    WARMUP_PRIORITY = os.environ.get('WARMUP_PRIORITY', '').split(',') if os.environ.get('WARMUP_PRIORITY') else [
        'popular_brands',
        'recent_reports',
        'popular_questions',
        'user_stats',
        'api_responses',
    ]
    
    # ==================== 预热并发配置 ====================
    
    # 是否启用并发预热
    CONCURRENT_WARMUP_ENABLED = os.environ.get('CONCURRENT_WARMUP_ENABLED', 'true').lower() == 'true'
    
    # 并发预热线程数
    WARMUP_THREAD_COUNT = int(os.environ.get('WARMUP_THREAD_COUNT', '4'))
    
    # ==================== 预热日志配置 ====================
    
    # 是否启用详细日志
    WARMUP_VERBOSE_LOGGING = os.environ.get('WARMUP_VERBOSE_LOGGING', 'false').lower() == 'true'
    
    # 预热超时时间（秒）
    WARMUP_TIMEOUT_SECONDS = int(os.environ.get('WARMUP_TIMEOUT_SECONDS', '300'))  # 5 分钟
    
    # ==================== 工具方法 ====================
    
    @classmethod
    def is_warmup_enabled(cls) -> bool:
        """
        检查是否启用了缓存预热
        
        Returns:
            bool: 是否启用
        """
        return cls.CACHE_WARMUP_ENABLED
    
    @classmethod
    def is_auto_warmup_enabled(cls) -> bool:
        """
        检查是否启用了自动预热（启动时）
        
        Returns:
            bool: 是否启用
        """
        return cls.AUTO_WARMUP_ON_STARTUP and cls.CACHE_WARMUP_ENABLED
    
    @classmethod
    def is_scheduled_warmup_enabled(cls) -> bool:
        """
        检查是否启用了定时预热
        
        Returns:
            bool: 是否启用
        """
        return cls.SCHEDULED_WARMUP_ENABLED and cls.CACHE_WARMUP_ENABLED
    
    @classmethod
    def get_warmup_tasks(cls) -> List[str]:
        """
        获取预热任务列表（按优先级排序）
        
        Returns:
            预热任务列表
        """
        return cls.WARMUP_PRIORITY
    
    @classmethod
    def get_brand_stats_ttl(cls) -> int:
        """
        获取品牌统计缓存时间
        
        Returns:
            缓存时间（秒）
        """
        return cls.BRAND_STATS_TTL
    
    @classmethod
    def get_report_stats_ttl(cls) -> int:
        """
        获取诊断报告缓存时间
        
        Returns:
            缓存时间（秒）
        """
        return cls.REPORT_STATS_TTL
    
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        验证缓存预热配置是否完整
        
        Returns:
            (是否有效，错误信息列表)
        """
        errors = []
        
        # 检查预热线程数
        if cls.WARMUP_THREAD_COUNT < 1:
            errors.append('WARMUP_THREAD_COUNT 必须大于 0')
        
        # 检查预热超时时间
        if cls.WARMUP_TIMEOUT_SECONDS < 60:
            errors.append('WARMUP_TIMEOUT_SECONDS 必须大于 60 秒')
        
        # 检查缓存时间配置
        if cls.BRAND_STATS_TTL < 60:
            errors.append('BRAND_STATS_TTL 必须大于 60 秒')
        
        if cls.REPORT_STATS_TTL < 60:
            errors.append('REPORT_STATS_TTL 必须大于 60 秒')
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            配置摘要字典
        """
        return {
            'cache_warmup_enabled': cls.is_warmup_enabled(),
            'auto_warmup_on_startup': cls.is_auto_warmup_enabled(),
            'scheduled_warmup_enabled': cls.is_scheduled_warmup_enabled(),
            'warmup_schedule': cls.WARMUP_SCHEDULE,
            'warmup_interval_minutes': cls.WARMUP_INTERVAL_MINUTES,
            'popular_brands_count': cls.WARMUP_POPULAR_BRANDS_COUNT,
            'popular_users_count': cls.WARMUP_POPULAR_USERS_COUNT,
            'popular_questions_count': cls.WARMUP_POPULAR_QUESTIONS_COUNT,
            'recent_reports_count': cls.WARMUP_RECENT_REPORTS_COUNT,
            'concurrent_warmup_enabled': cls.CONCURRENT_WARMUP_ENABLED,
            'warmup_thread_count': cls.WARMUP_THREAD_COUNT,
            'brand_stats_ttl': cls.BRAND_STATS_TTL,
            'report_stats_ttl': cls.REPORT_STATS_TTL,
            'api_response_ttl': cls.API_RESPONSE_TTL,
        }


# 导出配置实例
cache_warmup_config = CacheWarmupConfig()
