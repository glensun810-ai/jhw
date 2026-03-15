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
    检查失败的任务并尝试恢复（P0-03 修复版 - 2026-03-14）
    
    核心功能:
    1. 查询状态为 running 但超过超时时间的任务
    2. 查询状态为 retry 的任务
    3. 尝试重新提交这些任务
    4. 发送失败通知

    返回:
        检查结果
    """
    api_logger.info("[Celery] 开始检查失败的任务")
    
    from datetime import datetime, timedelta
    from wechat_backend.models import DiagnosisReport
    
    current_time = datetime.now()
    timeout_threshold = current_time - timedelta(minutes=15)  # 超过 15 分钟的任务视为卡死
    
    checked_count = 0
    recovered_count = 0
    failed_count = 0
    
    try:
        # 1. 查询状态为 running 但超过超时时间的任务
        api_logger.info(f"[Celery] 查询超时任务（阈值：{timeout_threshold}）")
        
        timeout_tasks = DiagnosisReport.query.filter(
            DiagnosisReport.status.in_(['running', 'processing']),
            DiagnosisReport.updated_at < timeout_threshold
        ).limit(50).all()
        
        api_logger.info(f"[Celery] 发现 {len(timeout_tasks)} 个超时任务")
        
        for task in timeout_tasks:
            checked_count += 1
            execution_id = task.execution_id
            
            try:
                api_logger.warning(
                    f"[Celery] 发现超时任务：{execution_id}, "
                    f"运行时长={(current_time - task.updated_at).total_seconds() / 60:.1f}分钟"
                )
                
                # 标记为失败
                task.status = 'failed'
                task.progress = 0
                task.stage = 'timeout'
                task.error_message = f'任务执行超时（超过 15 分钟无更新）'
                task.updated_at = current_time
                
                from wechat_backend.database_connection_pool import db
                db.session.commit()
                
                # 发送失败通知
                send_task_failure_notification(
                    execution_id, 
                    f'任务执行超时（超过 15 分钟无更新）'
                )
                
                # 尝试恢复 - 重新提交任务
                try:
                    # 获取原始任务参数
                    original_params = json.loads(task.selected_models or '{}')
                    
                    # 异步重试任务
                    retry_failed_task.delay(
                        execution_id=execution_id,
                        original_params={
                            'brand_list': json.loads(task.brand_name or '[]'),
                            'selected_models': original_params if isinstance(original_params, list) else [],
                            'custom_questions': []
                        }
                    )
                    
                    recovered_count += 1
                    api_logger.info(f"[Celery] ✅ 已重新提交任务：{execution_id}")
                    
                except Exception as retry_err:
                    api_logger.error(
                        f"[Celery] ❌ 重试失败：{execution_id}, error={retry_err}"
                    )
                    failed_count += 1
                    
            except Exception as task_err:
                api_logger.error(f"[Celery] 处理超时任务失败：{execution_id}, error={task_err}")
                failed_count += 1
        
        # 2. 查询状态为 retry 的任务
        api_logger.info("[Celery] 查询 retry 状态任务")
        
        retry_tasks = DiagnosisReport.query.filter(
            DiagnosisReport.status == 'retry'
        ).limit(50).all()
        
        api_logger.info(f"[Celery] 发现 {len(retry_tasks)} 个 retry 状态任务")
        
        for task in retry_tasks:
            checked_count += 1
            execution_id = task.execution_id
            
            try:
                api_logger.info(f"[Celery] 处理 retry 任务：{execution_id}")
                
                # 直接重试
                retry_failed_task.delay(
                    execution_id=execution_id,
                    original_params={
                        'brand_list': json.loads(task.brand_name or '[]'),
                        'selected_models': json.loads(task.selected_models or '[]'),
                        'custom_questions': []
                    }
                )
                
                recovered_count += 1
                
            except Exception as retry_err:
                api_logger.error(f"[Celery] 处理 retry 任务失败：{execution_id}, error={retry_err}")
                failed_count += 1
        
        # 3. 汇总结果
        result = {
            'status': 'completed',
            'checked_count': checked_count,
            'recovered_count': recovered_count,
            'failed_count': failed_count,
            'timeout_tasks': len(timeout_tasks),
            'retry_tasks': len(retry_tasks),
            'check_time': current_time.isoformat()
        }
        
        api_logger.info(f"[Celery] ✅ 任务检查完成：{result}")
        
        return result
        
    except Exception as e:
        api_logger.error(f"[Celery] 检查失败任务异常：{e}", exc_info=True)
        
        return {
            'status': 'error',
            'error': str(e),
            'checked_count': checked_count,
            'recovered_count': recovered_count,
            'failed_count': failed_count
        }


def send_task_failure_notification(execution_id: str, error_message: str):
    """
    发送任务失败通知（P0-01/P0-03 修复版 - 2026-03-14）
    
    功能:
    1. 记录失败日志
    2. 发送微信模板消息（生产环境）
    3. 发送系统告警

    参数:
        execution_id: 执行 ID
        error_message: 错误信息
    """
    import os
    
    # 1. 记录失败日志
    api_logger.warning(
        f"[任务失败通知] execution_id={execution_id}, 错误：{error_message}"
    )
    
    try:
        # 2. 获取任务信息
        from wechat_backend.models import DiagnosisReport
        task = DiagnosisReport.query.filter_by(execution_id=execution_id).first()
        
        if not task:
            api_logger.warning(f"[通知] 任务不存在：{execution_id}")
            return
        
        # 3. 获取用户信息
        user_openid = task.user_openid if hasattr(task, 'user_openid') else None
        
        if not user_openid:
            api_logger.warning(f"[通知] 无法获取用户 OpenID：{execution_id}")
            return
        
        # 4. 生产环境：发送微信模板消息
        env = os.getenv('FLASK_ENV', 'development')
        
        if env == 'production':
            try:
                from wechat_backend.wechat_push import WechatPush
                from wechat_backend.config_loader import wechat_config
                
                appid = wechat_config.get('appid', '')
                secret = wechat_config.get('appsecret', '')
                
                if appid and secret:
                    push_client = WechatPush(appid=appid, secret=secret)
                    
                    # 发送模板消息
                    template_data = {
                        'thing1': {'value': '诊断任务失败'},
                        'thing2': {'value': error_message[:20]},  # 限制长度
                        'time3': {'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                        'thing4': {'value': '请检查后重试'}
                    }
                    
                    push_client.send_template_message(
                        openid=user_openid,
                        template_id='YOUR_TEMPLATE_ID',  # 需配置实际模板 ID
                        page='pages/diagnosis/diagnosis',
                        data=template_data
                    )
                    
                    api_logger.info(f"[通知] ✅ 微信模板消息已发送：{execution_id}")
                    
            except Exception as wechat_err:
                api_logger.error(f"[通知] 微信消息发送失败：{wechat_err}")
        
        # 5. 发送系统告警（开发/生产环境都发送）
        try:
            from wechat_backend.monitoring.enhanced_alert_manager import get_alert_manager
            
            alert_manager = get_alert_manager()
            alert_manager.send_alert(
                alert_type='task_failure',
                severity='warning',
                title=f'诊断任务失败：{execution_id}',
                message=f'用户：{user_openid[:8]}..., 错误：{error_message}',
                context={
                    'execution_id': execution_id,
                    'brand_name': task.brand_name,
                    'error_message': error_message
                }
            )
            
            api_logger.info(f"[通知] ✅ 系统告警已发送：{execution_id}")
            
        except Exception as alert_err:
            api_logger.error(f"[通知] 系统告警发送失败：{alert_err}")
            
    except Exception as e:
        api_logger.error(f"[通知] 发送失败通知异常：{e}", exc_info=True)


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
