"""
异步诊断执行助手

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from wechat_backend.logging_config import api_logger
from wechat_backend.models_pkg.task_queue import (
    TaskQueueModel,
    TaskQueueStatus,
    save_task_queue,
    get_task_queue,
    update_task_queue_status,
)
from wechat_backend.services.task_tracker import TaskResultTracker


class AsyncDiagnosisExecutor:
    """异步诊断执行器"""

    def __init__(self):
        self.task_tracker = TaskResultTracker()

    def submit_diagnosis_task(
        self,
        user_id: str,
        brand_list: List[str],
        selected_models: List[Dict],
        custom_questions: List[str] = None,
        user_openid: str = None,
        priority: int = 0,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        提交异步诊断任务

        参数:
            user_id: 用户 ID
            brand_list: 品牌列表
            selected_models: 选中的 AI 模型列表
            custom_questions: 自定义问题列表
            user_openid: 用户 OpenID
            priority: 优先级 (0-10, 越高越优先)
            **kwargs: 其他参数

        返回:
            (execution_id, response_dict) 元组
        """
        # 生成执行 ID
        execution_id = str(uuid.uuid4())

        api_logger.info(
            f"[P2-4] 提交异步诊断任务：{execution_id}, "
            f"user: {user_id}, brands: {brand_list}"
        )

        # 准备任务参数
        payload = {
            'user_id': user_id,
            'brand_list': brand_list,
            'selected_models': selected_models,
            'custom_questions': custom_questions or [],
            'user_openid': user_openid or user_id,
            **kwargs
        }

        # 创建任务记录
        task_queue = self.task_tracker.create_task_record(
            execution_id=execution_id,
            task_type='brand_diagnosis',
            payload=payload,
            priority=priority,
            user_id=user_id
        )

        if not task_queue:
            api_logger.error(f"[P2-4] 创建任务记录失败：{execution_id}")
            return execution_id, {
                'status': 'error',
                'error': 'Failed to create task record',
                'code': 500
            }

        # 提交到 Celery 任务队列
        try:
            from wechat_backend.tasks.diagnosis_tasks import execute_diagnosis_task

            # 异步执行任务
            async_result = execute_diagnosis_task.delay(
                execution_id=execution_id,
                user_id=user_id,
                brand_list=brand_list,
                selected_models=selected_models,
                custom_questions=custom_questions or [],
                user_openid=user_openid or user_id,
                **kwargs
            )

            # 更新任务状态为已入队
            update_task_queue_status(
                execution_id=execution_id,
                status=TaskQueueStatus.QUEUED,
                celery_task_id=async_result.id
            )

            api_logger.info(
                f"[P2-4] 任务已提交到队列：{execution_id}, "
                f"celery_task_id: {async_result.id}"
            )

            # 返回响应
            return execution_id, {
                'status': 'queued',
                'execution_id': execution_id,
                'message': '任务已提交，正在处理中',
                'estimated_time': self._estimate_execution_time(brand_list, selected_models, custom_questions)
            }

        except Exception as e:
            api_logger.error(f"[P2-4] 提交 Celery 任务失败：{e}")

            # 更新任务状态为失败
            update_task_queue_status(
                execution_id=execution_id,
                status=TaskQueueStatus.FAILED,
                error_message=str(e)
            )

            return execution_id, {
                'status': 'error',
                'error': f'Failed to submit task: {str(e)}',
                'code': 500
            }

    def get_task_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        参数:
            execution_id: 执行 ID

        返回:
            任务状态字典
        """
        return self.task_tracker.get_task_status(execution_id)

    def cancel_task(self, execution_id: str) -> bool:
        """
        取消任务

        参数:
            execution_id: 执行 ID

        返回:
            是否成功
        """
        return self.task_tracker.cancel_task(execution_id)

    def _estimate_execution_time(
        self,
        brand_list: List[str],
        selected_models: List[Dict],
        custom_questions: List[str]
    ) -> int:
        """
        估算执行时间（秒）

        基于品牌数、模型数和问题数估算

        返回:
            估算时间（秒）
        """
        brand_count = len(brand_list)
        model_count = len(selected_models)
        question_count = len(custom_questions) if custom_questions else 3  # 默认 3 个问题

        # 每个 AI 调用用平均 30 秒估算
        total_calls = brand_count * model_count * question_count
        estimated_seconds = total_calls * 30

        # 最少 30 秒，最多 600 秒
        return max(30, min(600, estimated_seconds))


# 全局执行器实例
async_executor = AsyncDiagnosisExecutor()


def get_async_executor() -> AsyncDiagnosisExecutor:
    """获取异步执行器实例"""
    return async_executor
