"""
Celery 异步任务模块

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

from wechat_backend.tasks.diagnosis_tasks import (
    execute_diagnosis_task,
    execute_nxm_batch_task,
    check_failed_tasks,
)
from wechat_backend.tasks.analytics_tasks import (
    generate_report_task,
    analyze_brand_task,
)
from wechat_backend.tasks.cleanup_tasks import (
    cleanup_old_tasks,
    cleanup_expired_cache,
)

__all__ = [
    'execute_diagnosis_task',
    'execute_nxm_batch_task',
    'check_failed_tasks',
    'generate_report_task',
    'analyze_brand_task',
    'cleanup_old_tasks',
    'cleanup_expired_cache',
]
