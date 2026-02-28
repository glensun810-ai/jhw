"""
数据模型模块

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

# 从原有 models.py 导入
from wechat_backend.models import (
    TaskStatus,
    TaskStage,
    BrandTestResult,
    DeepIntelligenceResult,
    init_task_status_db,
    save_task_status,
    get_task_status,
    save_deep_intelligence_result,
    get_deep_intelligence_result,
    update_task_stage,
    save_brand_test_result,
    get_brand_test_result,
)

# 从 task_queue 导入
from wechat_backend.models_pkg.task_queue import (
    TaskQueueStatus,
    TaskQueueModel,
    init_task_queue_db,
    save_task_queue,
    get_task_queue,
    update_task_queue_status,
    get_pending_tasks,
    get_task_statistics,
)

__all__ = [
    # 原有模型
    'TaskStatus',
    'TaskStage',
    'BrandTestResult',
    'DeepIntelligenceResult',
    'init_task_status_db',
    'save_task_status',
    'get_task_status',
    'save_deep_intelligence_result',
    'get_deep_intelligence_result',
    'update_task_stage',
    'save_brand_test_result',
    'get_brand_test_result',
    # 任务队列模型
    'TaskQueueStatus',
    'TaskQueueModel',
    'init_task_queue_db',
    'save_task_queue',
    'get_task_queue',
    'update_task_queue_status',
    'get_pending_tasks',
    'get_task_statistics',
]
