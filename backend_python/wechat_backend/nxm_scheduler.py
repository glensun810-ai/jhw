"""
NxM 执行引擎 - 任务调度模块

功能：
- NxM 任务调度与并发控制
- 进度跟踪与更新
- 超时控制
"""

import time
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.nxm_circuit_breaker import get_circuit_breaker

# P1 优化配置
PROGRESS_UPDATE_INTERVAL = 5  # 每 5 次任务更新一次进度

# P1 修复：导入 SSE 推送函数
try:
    from wechat_backend.services.sse_service import send_progress_update
except ImportError:
    # 如果 SSE 服务不可用，使用空函数替代
    def send_progress_update(execution_id: str, **kwargs):
        """空实现的 SSE 推送函数"""
        pass


class NxMScheduler:
    """
    NxM 任务调度器

    功能：
    - 管理 NxM 执行流程
    - 跟踪进度
    - 处理超时
    """

    def __init__(self, execution_id: str, execution_store: Dict[str, Any]):
        self.execution_id = execution_id
        self.execution_store = execution_store
        self.circuit_breaker = get_circuit_breaker()
        self._lock = threading.Lock()
        self._timeout_timer: Optional[threading.Timer] = None
        self._update_counter = 0  # P1 优化：更新计数器
        self._total_tasks = 0  # P1 优化：总任务数

    def initialize_execution(self, total_tasks: int):
        """初始化执行状态"""
        with self._lock:
            self.execution_store[self.execution_id] = {
                'progress': 0,
                'completed': 0,
                'total': total_tasks,
                'status': 'initializing',
                'stage': 'init',
                'results': [],
                'start_time': datetime.now().isoformat()
            }
            self._total_tasks = total_tasks  # P1 优化：保存总任务数
            self._update_counter = 0  # P1 优化：重置计数器
        api_logger.info(f"[Scheduler] 执行初始化：{self.execution_id}, 总任务数：{total_tasks}")

    def update_progress(self, completed: int, total: int, stage: str = 'ai_fetching'):
        """
        更新进度（P1 优化：批量更新，减少数据库写入）
        
        P1 优化：
        - 每 5 次更新才实际写入一次数据库
        - 减少 I/O 开销，提升性能
        
        Args:
            completed: 已完成任务数
            total: 总任务数
            stage: 当前阶段（init/ai_fetching/analyzing/completed/failed）
        """
        progress = int((completed / total) * 100) if total > 0 else 0

        # P1 优化：批量更新（每 5 次更新一次）
        self._update_counter += 1
        should_update = (self._update_counter % PROGRESS_UPDATE_INTERVAL == 0)
        
        # 最后一次更新（progress=100）必须立即写入
        if progress >= 100:
            should_update = True

        # P0 修复：根据 stage 推导 status
        status_stage_map = {
            'init': 'initializing',
            'ai_fetching': 'ai_fetching',
            'analyzing': 'analyzing',
            'intelligence_analyzing': 'analyzing',
            'competition_analyzing': 'analyzing',
            'completed': 'completed',
            'failed': 'failed'
        }
        status = status_stage_map.get(stage, 'ai_fetching')

        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['progress'] = progress
                store['completed'] = completed
                store['stage'] = stage
                store['status'] = status  # P0 修复：同步 status
                
                # P1 优化：批量更新，减少 SSE 推送频率
                if should_update:
                    # SSE 推送
                    try:
                        # P1 修复：添加 status_text 参数
                        status_texts = {
                            'init': '正在初始化',
                            'ai_fetching': '正在连接 AI 平台',
                            'intelligence_analyzing': '正在分析数据',
                            'competition_analyzing': '正在比对竞品',
                            'completed': '诊断完成'
                        }
                        status_text = status_texts.get(stage, stage)

                        send_progress_update(
                            execution_id=self.execution_id,
                            progress=progress,
                            stage=stage,
                            status_text=status_text,
                            completed=completed,
                            total=total
                        )
                    except Exception as e:
                        api_logger.error(f"[Scheduler] SSE 推送失败：{e}")
                    
                    # 【P0 关键修复】同时写入数据库，确保服务重启后进度不丢失
                    try:
                        from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
                        repo = DiagnosisReportRepository()
                        repo.update_status(
                            execution_id=self.execution_id,
                            status=status,
                            progress=progress,
                            stage=stage
                        )
                        api_logger.debug(f"[Scheduler] 数据库进度已更新：{self.execution_id}, progress={progress}")
                    except Exception as db_err:
                        api_logger.error(f"[Scheduler] 数据库更新失败：{db_err}")
                        # 数据库失败不影响内存更新，但记录告警
                        from wechat_backend.alerting import alert_warning
                        alert_warning(
                            component='scheduler.update_progress',
                            warning_message=f'数据库进度更新失败',
                            context={
                                'execution_id': self.execution_id,
                                'progress': progress,
                                'stage': stage,
                                'error': str(db_err)
                            }
                        )

    def add_result(self, result: Dict[str, Any]):
        """添加结果"""
        with self._lock:
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['results'].append(result)

    def complete_execution(self):
        """完成执行（P0 修复：强制写入数据库）"""
        # 【P0 修复 - 架构师决策】取消超时计时器，避免完成后被删除
        self.cancel_timeout_timer()

        # 【P0 修复】同步更新 execution_store，确保 fail_execution 能检查到完成状态
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'completed'
                store['stage'] = 'completed'
                store['is_completed'] = True
                store['progress'] = 100
                store['end_time'] = datetime.now().isoformat()

        # 【P0 关键修复】强制写入数据库，确保状态持久化
        try:
            from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
            repo = DiagnosisReportRepository()
            repo.update_status(
                execution_id=self.execution_id,
                status='completed',
                progress=100,
                stage='completed',
                is_completed=True
            )
            api_logger.info(f"[Scheduler] ✅ 数据库完成状态已更新：{self.execution_id}")
        except Exception as e:
            api_logger.error(f"[Scheduler] 数据库完成状态更新失败：{e}")
            # 【P0 关键修复】数据库失败时发送告警
            from wechat_backend.alerting import alert_critical_failure
            alert_critical_failure(
                component='scheduler.complete_execution',
                error_message=f'数据库完成状态更新失败：{e}',
                execution_id=self.execution_id
            )
            # 数据库失败不影响内存状态

        api_logger.info(f"[Scheduler] 执行完成（计时器已取消）：{self.execution_id}")

    def fail_execution(self, error: str):
        """
        失败执行（P0 修复：失败时清理空报告 + 强制写入数据库）

        Args:
            error: 错误信息
        """
        # 【P0 修复】确保 error 总是有值
        if not error or not error.strip():
            error = "执行失败，原因未知"

        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]

                # 【P0 修复 - 架构师决策】检查是否已完成，已完成则不删除
                if store.get('status') == 'completed' or store.get('stage') == 'completed' or store.get('is_completed') == True:
                    api_logger.warning(f"[Scheduler] 任务已完成，跳过失败处理：{self.execution_id}")
                    return

                store['status'] = 'failed'
                store['stage'] = 'failed'  # 【修复】同步 stage 与 status
                store['error'] = error
                store['end_time'] = datetime.now().isoformat()

                # 【P0 关键修复】强制停止轮询标志
                store['should_stop_polling'] = True

                # P0 修复：失败时清理空报告
                # 如果没有任何结果，删除 diagnosis_reports 记录
                if not store.get('results') or len(store.get('results', [])) == 0:
                    try:
                        from wechat_backend.diagnosis_report_repository import delete_diagnosis_report_by_execution_id
                        delete_diagnosis_report_by_execution_id(self.execution_id)
                        api_logger.info(f"[Scheduler] 清理空报告：{self.execution_id}")
                    except Exception as e:
                        api_logger.error(f"[Scheduler] 清理空报告失败：{e}")

        # 【P0 关键修复】强制写入数据库，确保状态持久化
        try:
            from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
            repo = DiagnosisReportRepository()
            repo.update_status(
                execution_id=self.execution_id,
                status='failed',
                progress=100,  # 失败也是完成执行，进度设为 100%
                stage='failed',
                is_completed=True  # 失败也是完成，让前端停止轮询
            )
            api_logger.info(f"[Scheduler] ✅ 数据库失败状态已更新：{self.execution_id}")
        except Exception as e:
            api_logger.error(f"[Scheduler] 数据库失败状态更新失败：{e}")
            # 【P0 关键修复】数据库失败时发送告警
            from wechat_backend.alerting import alert_critical_failure
            alert_critical_failure(
                component='scheduler.fail_execution',
                error_message=f'数据库失败状态更新失败：{e}',
                execution_id=self.execution_id
            )
            # 数据库失败不影响内存状态

        api_logger.error(f"[Scheduler] 执行失败：{self.execution_id}, 错误：{error}")

    def start_timeout_timer(self, timeout_seconds: int, timeout_callback: Callable):
        """启动超时计时器"""
        def on_timeout():
            api_logger.warning(f"[Scheduler] 执行超时：{self.execution_id}")
            timeout_callback()

        self._timeout_timer = threading.Timer(timeout_seconds, on_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def cancel_timeout_timer(self):
        """取消超时计时器"""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def is_model_available(self, model_name: str) -> bool:
        """检查模型是否可用"""
        return self.circuit_breaker.is_available(model_name)

    def record_model_success(self, model_name: str):
        """记录模型成功"""
        self.circuit_breaker.record_success(model_name)

    def record_model_failure(self, model_name: str):
        """记录模型失败"""
        self.circuit_breaker.record_failure(model_name)


def create_scheduler(execution_id: str, execution_store: Dict[str, Any]) -> NxMScheduler:
    """创建调度器实例"""
    return NxMScheduler(execution_id, execution_store)
