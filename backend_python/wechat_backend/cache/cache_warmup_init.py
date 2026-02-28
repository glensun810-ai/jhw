"""
缓存预热初始化模块

功能：
- 注册预热任务
- 启动定时调度
- 执行启动时预热
- 提供 API 接口

参考：P2-7: 智能缓存预热未实现
"""

from wechat_backend.logging_config import api_logger
from config.config_cache_warmup import cache_warmup_config
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
from wechat_backend.cache.cache_warmup_scheduler import (
    get_scheduler,
    start_scheduler,
)


def register_all_warmup_tasks():
    """注册所有预热任务"""
    # 注册预热任务
    register_warmup_task('popular_brands', warmup_popular_brands)
    register_warmup_task('user_stats', warmup_user_stats)
    register_warmup_task('popular_questions', warmup_popular_questions)
    register_warmup_task('recent_reports', warmup_recent_reports)
    register_warmup_task('api_responses', warmup_api_responses)
    
    api_logger.info(f"已注册 {len(get_warmup_engine()._warmup_tasks)} 个预热任务")


def start_cache_warmup():
    """
    启动缓存预热服务
    
    包括：
    1. 注册预热任务
    2. 执行启动时预热（可选）
    3. 启动定时调度器
    """
    if not cache_warmup_config.is_warmup_enabled():
        api_logger.info("缓存预热未启用，跳过初始化")
        return
    
    try:
        # 1. 注册所有预热任务
        register_all_warmup_tasks()
        
        # 2. 执行启动时预热
        if cache_warmup_config.is_auto_warmup_enabled():
            api_logger.info("执行启动时缓存预热...")
            
            # 在后台线程中执行预热，避免阻塞启动
            import threading
            thread = threading.Thread(
                target=_execute_startup_warmup,
                daemon=True
            )
            thread.start()
        else:
            api_logger.info("启动时自动预热已禁用")
        
        # 3. 启动定时调度器
        if cache_warmup_config.is_scheduled_warmup_enabled():
            _setup_scheduled_tasks()
            start_scheduler()
            api_logger.info("定时缓存预热已启动")
        else:
            api_logger.info("定时缓存预热已禁用")
        
        api_logger.info("✅ 缓存预热服务已启动")
        
    except Exception as e:
        api_logger.error(f"缓存预热启动失败：{e}")
        import traceback
        api_logger.error(traceback.format_exc())


def _execute_startup_warmup():
    """执行启动时预热"""
    try:
        # 获取预热任务列表
        tasks = cache_warmup_config.get_warmup_tasks()
        
        # 执行预热
        metrics = execute_warmup(tasks=tasks, concurrent=True)
        
        api_logger.info(
            f"启动时预热完成：耗时 {metrics.get('duration_seconds', 0):.2f}s, "
            f"成功 {metrics.get('completed_tasks', 0)}/{metrics.get('total_tasks', 0)}"
        )
        
    except Exception as e:
        api_logger.error(f"启动时预热失败：{e}")


def _setup_scheduled_tasks():
    """设置定时任务"""
    scheduler = get_scheduler()
    
    # 添加 cron 定时任务（每天凌晨 3 点执行）
    scheduler.add_cron_task(
        name='daily_cache_warmup',
        func=_execute_scheduled_warmup,
        cron_expression=cache_warmup_config.WARMUP_SCHEDULE
    )
    
    api_logger.info(
        f"定时缓存预热已配置：cron={cache_warmup_config.WARMUP_SCHEDULE}"
    )


def _execute_scheduled_warmup():
    """执行定时预热"""
    try:
        api_logger.info("开始执行定时缓存预热...")
        
        # 获取预热任务列表
        tasks = cache_warmup_config.get_warmup_tasks()
        
        # 执行预热
        metrics = execute_warmup(tasks=tasks, concurrent=True)
        
        api_logger.info(
            f"定时预热完成：耗时 {metrics.get('duration_seconds', 0):.2f}s, "
            f"成功 {metrics.get('completed_tasks', 0)}/{metrics.get('total_tasks', 0)}"
        )
        
    except Exception as e:
        api_logger.error(f"定时预热失败：{e}")


def get_warmup_status():
    """获取预热状态"""
    from wechat_backend.cache.cache_warmup import get_warmup_status as get_status
    from wechat_backend.cache.cache_warmup_scheduler import get_scheduler_status
    
    return {
        'warmup': get_status(),
        'scheduler': get_scheduler_status(),
        'config': cache_warmup_config.get_config_summary(),
    }
