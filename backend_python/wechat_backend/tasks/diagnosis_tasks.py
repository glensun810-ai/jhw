"""
诊断相关 Celery 异步任务

P2-4 消息队列实现

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import json
import time
from datetime import datetime
from celery import shared_task
from typing import Dict, Any, List, Optional

from wechat_backend.celery_app import celery_app
from wechat_backend.logging_config import api_logger
from wechat_backend.models_pkg.task_queue import (
    TaskQueueModel,
    TaskQueueStatus,
    save_task_queue,
    get_task_queue,
    update_task_queue_status,
)
from wechat_backend.nxm_execution_engine import execute_nxm_test
from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
from wechat_backend.state_manager import StateManager


@celery_app.task(
    bind=True,
    name='wechat_backend.tasks.diagnosis_tasks.execute_diagnosis_task',
    max_retries=3,
    default_retry_delay=60,
    time_limit=600,
    soft_time_limit=540
)
def execute_diagnosis_task(
    self,
    execution_id: str,
    user_id: str,
    brand_list: List[str],
    selected_models: List[Dict],
    custom_questions: List[str] = None,
    user_openid: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    执行品牌诊断任务（异步）

    参数:
        execution_id: 执行 ID
        user_id: 用户 ID
        brand_list: 品牌列表
        selected_models: 选中的 AI 模型列表
        custom_questions: 自定义问题列表
        user_openid: 用户 OpenID
        **kwargs: 其他参数

    返回:
        执行结果字典
    """
    task_start_time = time.time()
    api_logger.info(f"[Celery] 开始执行诊断任务：{execution_id}, user: {user_id}")

    # 更新任务状态为运行中
    update_task_queue_status(
        execution_id=execution_id,
        status=TaskQueueStatus.RUNNING,
        celery_task_id=self.request.id,
        worker_name=self.request.hostname
    )

    try:
        # 准备执行参数
        params = {
            'execution_id': execution_id,
            'user_id': user_id,
            'brand_list': brand_list,
            'selected_models': selected_models,
            'custom_questions': custom_questions or [],
            'user_openid': user_openid or user_id,
        }

        # 执行诊断测试
        api_logger.info(f"[Celery] 执行 NXM 测试：{execution_id}")
        result = execute_nxm_test(**params)

        # 计算执行时间
        execution_time = time.time() - task_start_time

        # 更新任务状态为成功
        update_task_queue_status(
            execution_id=execution_id,
            status=TaskQueueStatus.SUCCESS,
            result={
                'execution_time': execution_time,
                'result_summary': result.get('summary', {}),
            }
        )

        api_logger.info(
            f"[Celery] 诊断任务执行成功：{execution_id}, "
            f"耗时：{execution_time:.2f}s"
        )

        return {
            'status': 'success',
            'execution_id': execution_id,
            'execution_time': execution_time,
            'result': result
        }

    except Exception as e:
        api_logger.error(f"[Celery] 诊断任务执行失败：{execution_id}, error: {e}")

        # 获取当前重试次数
        retry_count = self.request.retries or 0

        # 判断是否需要重试
        if retry_count < 3:
            # 更新任务状态为重试
            update_task_queue_status(
                execution_id=execution_id,
                status=TaskQueueStatus.RETRY,
                error_message=str(e),
                retry_count=retry_count + 1
            )

            # 抛出重试异常
            raise self.retry(exc=e, countdown=60 * (retry_count + 1))
        else:
            # 更新任务状态为失败
            update_task_queue_status(
                execution_id=execution_id,
                status=TaskQueueStatus.FAILED,
                error_message=str(e),
                retry_count=retry_count
            )

            # 发送任务失败通知
            send_task_failure_notification(execution_id, str(e))

            return {
                'status': 'failed',
                'execution_id': execution_id,
                'error': str(e)
            }


@celery_app.task(
    bind=True,
    name='wechat_backend.tasks.diagnosis_tasks.execute_nxm_batch_task',
    max_retries=2,
    default_retry_delay=30,
    time_limit=1200,
    soft_time_limit=1140
)
def execute_nxm_batch_task(
    self,
    execution_id: str,
    batch_params: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    批量执行 NXM 诊断任务

    参数:
        execution_id: 执行 ID
        batch_params: 批量参数列表

    返回:
        批量执行结果
    """
    api_logger.info(f"[Celery] 开始执行批量诊断任务：{execution_id}, 批次大小：{len(batch_params)}")

    results = []
    success_count = 0
    failed_count = 0

    for i, params in enumerate(batch_params):
        try:
            api_logger.info(f"[Celery] 执行批次 {i+1}/{len(batch_params)}")
            result = execute_nxm_test(**params)
            results.append({
                'execution_id': params.get('execution_id'),
                'status': 'success',
                'result': result
            })
            success_count += 1
        except Exception as e:
            api_logger.error(f"[Celery] 批次 {i+1} 执行失败：{e}")
            results.append({
                'execution_id': params.get('execution_id'),
                'status': 'failed',
                'error': str(e)
            })
            failed_count += 1

    api_logger.info(
        f"[Celery] 批量诊断任务完成：{execution_id}, "
        f"成功：{success_count}, 失败：{failed_count}"
    )

    return {
        'status': 'completed',
        'execution_id': execution_id,
        'total': len(batch_params),
        'success_count': success_count,
        'failed_count': failed_count,
        'results': results
    }


@celery_app.task(
    name='wechat_backend.tasks.diagnosis_tasks.check_failed_tasks',
    time_limit=300
)
def check_failed_tasks() -> Dict[str, Any]:
    """
    检查失败的任务并尝试恢复

    返回:
        检查结果
    """
    api_logger.info("[Celery] 开始检查失败的任务")

    # TODO: 实现失败任务检查和恢复逻辑
    # 1. 查询状态为 running 但超过超时时间的任务
    # 2. 查询状态为 retry 的任务
    # 3. 尝试重新提交这些任务

    return {
        'status': 'completed',
        'checked_count': 0,
        'recovered_count': 0
    }


def send_task_failure_notification(execution_id: str, error_message: str):
    """
    发送任务失败通知

    参数:
        execution_id: 执行 ID
        error_message: 错误信息
    """
    # TODO: 实现通知逻辑（邮件、短信等）
    api_logger.warning(
        f"[通知] 诊断任务失败：{execution_id}, 错误：{error_message}"
    )


@celery_app.task(
    bind=True,
    name='wechat_backend.tasks.diagnosis_tasks.retry_failed_task',
    max_retries=1
)
def retry_failed_task(
    self,
    execution_id: str,
    original_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    重试失败的任务

    参数:
        execution_id: 执行 ID
        original_params: 原始参数

    返回:
        重试结果
    """
    api_logger.info(f"[Celery] 重试失败任务：{execution_id}")

    try:
        # 重新执行诊断任务
        result = execute_nxm_test(**original_params)

        update_task_queue_status(
            execution_id=execution_id,
            status=TaskQueueStatus.SUCCESS,
            result={'retried': True, 'result': result}
        )

        return {
            'status': 'success',
            'execution_id': execution_id,
            'result': result
        }

    except Exception as e:
        api_logger.error(f"[Celery] 重试失败：{execution_id}, error: {e}")

        update_task_queue_status(
            execution_id=execution_id,
            status=TaskQueueStatus.FAILED,
            error_message=f"重试失败：{str(e)}"
        )

        return {
            'status': 'failed',
            'execution_id': execution_id,
            'error': str(e)
        }
