"""
Celery 异步任务配置

P2-4 消息队列实现

使用方法:
    # 启动 worker
    celery -A wechat_backend.celery_app:celery_app worker -l info --pool=gevent
    
    # 启动 beat 调度器
    celery -A wechat_backend.celery_app:celery_app beat -l info
    
    # 启动 flower 监控
    celery -A wechat_backend.celery_app:celery_app flower --port=5555

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue
from datetime import timedelta

# 导入配置
from wechat_backend.config.celery_config import CeleryConfig

# 创建 Celery 应用
celery_app = Celery('diagnosis')

# 从配置类加载配置
celery_app.config_from_object(CeleryConfig)

# 自动发现任务
celery_app.autodiscover_tasks(['wechat_backend.tasks'])


# 配置任务路由
celery_app.conf.task_routes = {
    'wechat_backend.tasks.diagnosis_tasks.execute_diagnosis_task': {'queue': 'diagnosis'},
    'wechat_backend.tasks.diagnosis_tasks.execute_nxm_batch_task': {'queue': 'diagnosis'},
    'wechat_backend.tasks.analytics_tasks.generate_report_task': {'queue': 'analytics'},
    'wechat_backend.tasks.cleanup_tasks.cleanup_old_tasks': {'queue': 'cleanup'},
    'wechat_backend.tasks.cleanup_tasks.cleanup_expired_cache': {'queue': 'cleanup'},
}

# 配置任务队列
celery_app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('diagnosis', Exchange('diagnosis'), routing_key='diagnosis'),
    Queue('analytics', Exchange('analytics'), routing_key='analytics'),
    Queue('cleanup', Exchange('cleanup'), routing_key='cleanup'),
)

# 配置任务序列化
celery_app.conf.task_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.result_serializer = 'json'
celery_app.conf.timezone = 'Asia/Shanghai'
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True

# 配置结果后端（使用数据库）
celery_app.conf.result_backend = 'db+sqlite:///../celery_results.db'

# 配置 broker
# 如果使用 Redis: celery_app.conf.broker_url = 'redis://localhost:6379/0'
# 如果使用 RabbitMQ: celery_app.conf.broker_url = 'amqp://guest:guest@localhost:5672//'
# 默认使用 SQLite 作为简单 broker（开发环境）
celery_app.conf.broker_url = 'sqlalchemy+sqlite:///../celery_broker.db'

# 配置并发数
celery_app.conf.worker_concurrency = 4

# 配置任务限流
celery_app.conf.task_default_rate_limit = '10/m'

# 配置任务超时
celery_app.conf.task_time_limit = 600  # 10 分钟
celery_app.conf.task_soft_time_limit = 540  # 9 分钟

# 配置任务确认
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_or_lost = True

# 配置预取限制
celery_app.conf.worker_prefetch_multiplier = 1


# 注册定时任务
celery_app.conf.beat_schedule = {
    # 每小时清理一次过期任务
    'cleanup-old-tasks': {
        'task': 'wechat_backend.tasks.cleanup_tasks.cleanup_old_tasks',
        'schedule': crontab(minute=0),  # 每小时整点执行
        'args': (30,)  # 保留 30 天
    },
    
    # 每天凌晨清理缓存
    'cleanup-expired-cache': {
        'task': 'wechat_backend.tasks.cleanup_tasks.cleanup_expired_cache',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨 3 点
        'args': (7,)  # 保留 7 天
    },
    
    # 每 5 分钟检查一次失败任务
    'check-failed-tasks': {
        'task': 'wechat_backend.tasks.diagnosis_tasks.check_failed_tasks',
        'schedule': timedelta(minutes=5),
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'


# 任务信号处理器
from celery import signals
from wechat_backend.logging_config import api_logger


@signals.task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务执行前日志"""
    api_logger.info(f"[Celery] 任务开始执行：{task.name}, task_id: {task_id}")


@signals.task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """任务执行后日志"""
    retval = kwargs.get('retval')
    api_logger.info(f"[Celery] 任务执行完成：{task.name}, task_id: {task_id}, result: {retval}")


@signals.task_failure.connect
def task_failure_handler(task_id, task, *args, **kwargs):
    """任务失败日志"""
    einfo = kwargs.get('einfo')
    api_logger.error(f"[Celery] 任务执行失败：{task.name}, task_id: {task_id}, error: {einfo}")


@signals.task_retry.connect
def task_retry_handler(task_id, task, *args, **kwargs):
    """任务重试日志"""
    reason = kwargs.get('reason')
    api_logger.warning(f"[Celery] 任务重试：{task.name}, task_id: {task_id}, reason: {reason}")
