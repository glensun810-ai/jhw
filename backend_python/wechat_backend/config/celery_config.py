"""
Celery 配置类

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import os
from pathlib import Path
from kombu import Queue, Exchange

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class CeleryConfig:
    """Celery 配置类"""
    
    # Broker 配置（消息队列）
    # 支持多种 broker: Redis, RabbitMQ, SQLAlchemy
    broker_url = os.environ.get(
        'CELERY_BROKER_URL',
        'sqlalchemy+sqlite:///../celery_broker.db'
    )
    
    # 结果后端配置
    result_backend = os.environ.get(
        'CELERY_RESULT_BACKEND',
        'db+sqlite:///../celery_results.db'
    )
    
    # 序列化配置
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    
    # 时区配置
    timezone = 'Asia/Shanghai'
    enable_utc = False
    
    # 任务配置
    task_default_queue = 'default'
    task_default_exchange = 'default'
    task_default_exchange_type = 'direct'
    task_default_routing_key = 'default'
    
    # 队列配置
    task_queues = (
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('diagnosis', Exchange('diagnosis'), routing_key='diagnosis'),
        Queue('analytics', Exchange('analytics'), routing_key='analytics'),
        Queue('cleanup', Exchange('cleanup'), routing_key='cleanup'),
    )
    
    # 任务路由
    task_routes = {
        'wechat_backend.tasks.diagnosis_tasks.*': {'queue': 'diagnosis'},
        'wechat_backend.tasks.analytics_tasks.*': {'queue': 'analytics'},
        'wechat_backend.tasks.cleanup_tasks.*': {'queue': 'cleanup'},
    }
    
    # Worker 配置
    worker_concurrency = int(os.environ.get('CELERY_WORKER_CONCURRENCY', 4))
    worker_prefetch_multiplier = 1
    worker_send_task_events = True
    
    # 任务事件配置
    task_send_sent_event = True
    
    # 超时配置
    task_time_limit = 600  # 10 分钟
    task_soft_time_limit = 540  # 9 分钟
    
    # 限流配置
    task_default_rate_limit = '10/m'
    
    # 任务确认配置
    task_acks_late = True
    task_reject_on_worker_or_lost = True
    
    # 结果配置
    result_expires = 3600 * 24 * 7  # 7 天后过期
    result_persistent = True
    
    # 定时任务配置
    beat_schedule = {
        # 每小时清理一次过期任务
        'cleanup-old-tasks': {
            'task': 'wechat_backend.tasks.cleanup_tasks.cleanup_old_tasks',
            'schedule': 3600.0,  # 每小时
            'args': (30,)  # 保留 30 天
        },
        # 每天凌晨清理缓存
        'cleanup-expired-cache': {
            'task': 'wechat_backend.tasks.cleanup_tasks.cleanup_expired_cache',
            'schedule': 3600.0 * 24,  # 每天
            'args': (7,)  # 保留 7 天
        },
    }
    
    # 任务存储配置
    task_store_errors_after_retry = True
    task_store_eager_result = False
    
    # 重试配置
    task_default_retry_delay = 60  # 默认重试延迟 60 秒
    task_max_retries = 3  # 最大重试次数
    
    # 数据库引擎配置（用于 broker 和 backend）
    broker_transport_options = {
        'visibility_timeout': 3600,  # 1 小时
        'confirm_publish': True,
    }
    
    result_backend_transport_options = {
        'retry_policy': {
            'max_retries': 3,
            'interval_start': 0,
            'interval_step': 0.2,
            'interval_max': 0.5,
        }
    }
