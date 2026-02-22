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

    def initialize_execution(self, total_tasks: int):
        """初始化执行状态"""
        with self._lock:
            self.execution_store[self.execution_id] = {
                'progress': 0,
                'completed': 0,
                'total': total_tasks,
                'status': 'running',
                'stage': 'ai_fetching',
                'results': [],
                'start_time': datetime.now().isoformat()
            }
        api_logger.info(f"[Scheduler] 执行初始化：{self.execution_id}, 总任务数：{total_tasks}")

    def update_progress(self, completed: int, total: int, stage: str = 'ai_fetching'):
        """更新进度"""
        progress = int((completed / total) * 100) if total > 0 else 0

        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['progress'] = progress
                store['completed'] = completed
                store['stage'] = stage

                # SSE 推送
                try:
                    send_progress_update(
                        execution_id=self.execution_id,
                        progress=progress,
                        stage=stage,
                        completed=completed,
                        total=total
                    )
                except Exception as e:
                    api_logger.error(f"[Scheduler] SSE 推送失败：{e}")

    def add_result(self, result: Dict[str, Any]):
        """添加结果"""
        with self._lock:
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['results'].append(result)

    def complete_execution(self):
        """完成执行"""
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'completed'
                store['progress'] = 100
                store['stage'] = 'completed'
                store['end_time'] = datetime.now().isoformat()

        api_logger.info(f"[Scheduler] 执行完成：{self.execution_id}")

    def fail_execution(self, error: str):
        """失败执行"""
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'failed'
                store['error'] = error
                store['end_time'] = datetime.now().isoformat()

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
