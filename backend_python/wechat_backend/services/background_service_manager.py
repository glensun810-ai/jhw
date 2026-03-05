"""
统一后台服务管理器 - BackgroundServiceManager

功能：
1. 统一管理所有后台清理任务（SSE、缓存、导出文件等）
2. 避免并发写入数据库导致的 database is locked 错误
3. 提供统一的生命周期管理（启动、停止、重启）
4. 提供服务健康状态监控
5. 支持分析任务队列（品牌分析、竞争分析等）

设计原则：
- 单一调度线程，避免多个清理线程同时运行
- 任务错峰执行，避免同一时间并发操作数据库
- 统一异常处理，单个任务失败不影响其他任务
- 分析任务使用线程池异步执行，不阻塞主流程
"""

import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

from wechat_backend.logging_config import api_logger


# ==================== 异常类 ====================

class QueueFullError(Exception):
    """队列已满异常"""
    pass


class ServiceStatus(Enum):
    """服务状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ScheduledTask:
    """计划任务配置"""
    name: str
    func: Callable[[], Any]
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    enabled: bool = True


@dataclass
class AnalysisTask:
    """分析任务记录"""
    task_id: str
    execution_id: str
    task_type: str  # 'brand_analysis', 'competitive_analysis', 'statistics'
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout_seconds: int = 180  # 【P0 修复 - 2026-03-05】默认 3 分钟超时，与 submit_analysis_task 默认值一致


class BackgroundServiceManager:
    """
    统一后台服务管理器

    管理所有后台清理任务和分析任务，避免资源竞争和数据库锁定问题
    """

    def __init__(self, max_workers: int = 4, max_queue_size: int = 100):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._analysis_tasks: Dict[str, AnalysisTask] = {}  # 分析任务队列
        self._status = ServiceStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # 【P0 修复 - 2026-03-05】线程池限制
        # max_workers: 最大工作线程数（默认 4，避免过多并发写入数据库）
        # max_queue_size: 最大队列长度（默认 100，防止内存耗尽）
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size

        # 线程池用于执行分析任务
        # 【P0 修复 - 2026-03-05】Python 3.14 兼容性修复
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AnalysisTask"
        )
        
        # 队列监控
        self._queue_rejected_count = 0  # 队列满拒绝次数
        self._queue_current_size = 0  # 当前队列大小

        # 统计信息
        self._start_time: Optional[datetime] = None
        self._total_executions = 0
        self._total_errors = 0
        
        api_logger.info(
            f"[BackgroundService] 初始化完成：max_workers={max_workers}, "
            f"max_queue_size={max_queue_size}"
        )
    
    def _on_worker_start(self):
        """工作线程启动回调"""
        api_logger.debug(f"[BackgroundService] 工作线程启动：{threading.current_thread().name}")

    def register_task(
        self,
        name: str,
        func: Callable[[], Any],
        interval_seconds: int,
        enabled: bool = True
    ) -> 'BackgroundServiceManager':
        """
        注册计划任务

        Args:
            name: 任务名称
            func: 任务函数
            interval_seconds: 执行间隔（秒）
            enabled: 是否启用

        Returns:
            self（支持链式调用）
        """
        with self._lock:
            now = datetime.now()
            self._tasks[name] = ScheduledTask(
                name=name,
                func=func,
                interval_seconds=interval_seconds,
                next_run=now,  # 立即执行一次
                enabled=enabled
            )
            api_logger.info(f"[BackgroundService] 注册任务：{name} (interval={interval_seconds}s)")
        return self

    def unregister_task(self, name: str) -> bool:
        """
        注销计划任务

        Args:
            name: 任务名称

        Returns:
            是否成功注销
        """
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                api_logger.info(f"[BackgroundService] 注销任务：{name}")
                return True
            return False

    def enable_task(self, name: str) -> bool:
        """启用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = True
                api_logger.info(f"[BackgroundService] 启用任务：{name}")
                return True
            return False

    def disable_task(self, name: str) -> bool:
        """禁用任务"""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = False
                api_logger.info(f"[BackgroundService] 禁用任务：{name}")
                return True
            return False

    def start(self, stagger_seconds: int = 5):
        """
        启动后台服务管理器

        Args:
            stagger_seconds: 任务错峰间隔（秒），避免所有任务同时执行
        """
        with self._lock:
            if self._status == ServiceStatus.RUNNING:
                api_logger.warning("[BackgroundService] 服务已在运行中")
                return

            self._stop_event.clear()
            self._status = ServiceStatus.RUNNING
            self._start_time = datetime.now()
            
            # 设置任务的下次执行时间（错峰）
            now = datetime.now()
            for i, task in enumerate(self._tasks.values()):
                task.next_run = now.replace(second=0, microsecond=0)
                # 每个任务间隔 stagger_seconds 秒
                from datetime import timedelta
                task.next_run = task.next_run + timedelta(seconds=i * stagger_seconds)

        # 启动调度线程
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="BackgroundServiceManager"
        )
        self._thread.start()
        
        api_logger.info(
            f"[BackgroundService] 服务已启动，管理 {len(self._tasks)} 个任务，"
            f"错峰间隔 {stagger_seconds}秒"
        )

    def stop(self, timeout_seconds: float = 10.0):
        """
        停止后台服务管理器

        Args:
            timeout_seconds: 等待线程结束的超时时间
        """
        with self._lock:
            if self._status != ServiceStatus.RUNNING:
                return
            
            self._stop_event.set()
            self._status = ServiceStatus.STOPPED

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
            if self._thread.is_alive():
                api_logger.warning("[BackgroundService] 停止超时，强制终止")
            else:
                api_logger.info("[BackgroundService] 服务已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                self._execute_due_tasks()
            except Exception as e:
                api_logger.error(f"[BackgroundService] 调度器错误：{e}", exc_info=True)
            
            # 每秒检查一次
            self._stop_event.wait(1.0)

    def _execute_due_tasks(self):
        """执行到期的任务"""
        now = datetime.now()
        
        with self._lock:
            due_tasks = [
                task for task in self._tasks.values()
                if task.enabled and task.next_run and task.next_run <= now
            ]
        
        # 按 next_run 时间排序，确保顺序执行
        due_tasks.sort(key=lambda t: t.next_run or now)
        
        for task in due_tasks:
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        try:
            api_logger.debug(f"[BackgroundService] 执行任务：{task.name}")
            task.func()
            
            with self._lock:
                task.run_count += 1
                task.last_run = datetime.now()
                task.next_run = datetime.now().replace(second=0, microsecond=0)
                from datetime import timedelta
                task.next_run = task.next_run + timedelta(seconds=task.interval_seconds)
                self._total_executions += 1
                
        except Exception as e:
            api_logger.error(
                f"[BackgroundService] 任务执行失败：{task.name}, 错误：{e}",
                exc_info=True
            )
            with self._lock:
                task.error_count += 1
                task.last_error = str(e)
                self._total_errors += 1

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        with self._lock:
            tasks_status = {}
            for name, task in self._tasks.items():
                tasks_status[name] = {
                    'enabled': task.enabled,
                    'run_count': task.run_count,
                    'error_count': task.error_count,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'last_error': task.last_error,
                    'interval_seconds': task.interval_seconds
                }

            # 【P0 修复 - 2026-03-05】添加分析任务队列状态
            analysis_tasks_status = {
                'total_tasks': len(self._analysis_tasks),
                'pending': sum(1 for t in self._analysis_tasks.values() if t.status == TaskStatus.PENDING),
                'running': sum(1 for t in self._analysis_tasks.values() if t.status == TaskStatus.RUNNING),
                'completed': sum(1 for t in self._analysis_tasks.values() if t.status == TaskStatus.COMPLETED),
                'failed': sum(1 for t in self._analysis_tasks.values() if t.status == TaskStatus.FAILED),
                'timeout': sum(1 for t in self._analysis_tasks.values() if t.status == TaskStatus.TIMEOUT),
                'queue_size': self._queue_current_size,
                'max_queue_size': self.max_queue_size,
                'queue_rejected_count': self._queue_rejected_count,
                'thread_pool_workers': self.max_workers
            }

            return {
                'status': self._status.value,
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                'total_tasks': len(self._tasks),
                'enabled_tasks': sum(1 for t in self._tasks.values() if t.enabled),
                'total_executions': self._total_executions,
                'total_errors': self._total_errors,
                'tasks': tasks_status,
                'analysis_tasks': analysis_tasks_status,
                'health_status': self._get_health_status()
            }
    
    def _get_health_status(self) -> str:
        """
        获取健康状态
        
        返回：
            'healthy' | 'warning' | 'critical'
        """
        # 队列利用率检查
        queue_utilization = self._queue_current_size / self.max_queue_size if self.max_queue_size > 0 else 0
        
        if queue_utilization > 0.9:
            return 'critical'
        elif queue_utilization > 0.7:
            return 'warning'
        elif self._status == ServiceStatus.ERROR:
            return 'critical'
        elif self._total_errors > self._total_executions * 0.1 and self._total_executions > 10:
            return 'warning'
        else:
            return 'healthy'

    # =========================================================================
    # 分析任务管理方法（Phase 3: 增强后台任务管理器）
    # =========================================================================

    def submit_analysis_task(
        self,
        execution_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout_seconds: int = 180,
        priority: int = 5  # 【P0 新增】优先级 1-10，数字越小优先级越高
    ) -> str:
        """
        提交分析任务到后台队列（P0 增强版 - 修复队列溢出）

        【P0 关键修复 - 2026-03-05】
        1. 队列满时三级降级策略
        2. 支持任务优先级（1-10）
        3. 自动清理旧任务腾空间
        4. 高优先级任务同步执行

        Args:
            execution_id: 执行 ID
            task_type: 任务类型 (brand_analysis/competitive_analysis/statistics)
            payload: 任务参数
            timeout_seconds: 任务超时时间（秒），默认 180 秒（3 分钟）
            priority: 任务优先级（1-10，数字越小优先级越高，默认 5）

        Returns:
            task_id: 任务 ID

        Raises:
            QueueFullError: 队列已满且无法降级

        【降级策略】
        1 级：清理已完成任务（>5 分钟）腾空间
        2 级：高优先级任务（<=3）同步执行
        3 级：低优先级任务拒绝
        """
        # 【P0 关键修复】队列满时降级策略
        with self._lock:
            self._queue_current_size = len(self._analysis_tasks)

            if self._queue_current_size >= self.max_queue_size:
                api_logger.warning(
                    f"[BackgroundService] ⚠️ 队列已满，触发降级策略："
                    f"current_size={self._queue_current_size}, max_size={self.max_queue_size}, "
                    f"priority={priority}"
                )

                # 【降级策略 1】清理已完成任务腾空间
                cleaned_count = self._cleanup_completed_tasks(max_age_minutes=5)
                if cleaned_count > 0:
                    api_logger.info(
                        f"[BackgroundService] ✅ 清理 {cleaned_count} 个已完成任务后重试提交"
                    )
                    # 更新队列大小
                    self._queue_current_size = len(self._analysis_tasks)
                    # 如果清理后有空位，继续提交
                    if self._queue_current_size < self.max_queue_size:
                        # 继续下面的提交流程
                        pass
                    else:
                        # 清理后仍然满，继续降级
                        self._queue_rejected_count += 1
                        if priority <= 3:
                            # 【降级策略 2】高优先级任务同步执行
                            api_logger.warning(
                                f"[BackgroundService] 🚀 队列满，同步执行高优先级任务：{execution_id}"
                            )
                            return self._execute_task_sync(
                                execution_id=execution_id,
                                task_type=task_type,
                                payload=payload,
                                timeout_seconds=min(timeout_seconds, 300)
                            )
                        else:
                            # 【降级策略 3】低优先级任务拒绝
                            api_logger.error(
                                f"[BackgroundService] ❌ 队列已满，拒绝低优先级任务："
                                f"current_size={self._queue_current_size}, priority={priority}"
                            )
                            raise QueueFullError(
                                f"分析任务队列已满（{self._queue_current_size}/{self.max_queue_size}），"
                                f"请稍后重试（优先级={priority}）"
                            )
                else:
                    # 没有可清理的任务，继续降级
                    self._queue_rejected_count += 1
                    if priority <= 3:
                        # 【降级策略 2】高优先级任务同步执行
                        api_logger.warning(
                            f"[BackgroundService] 🚀 队列满，同步执行高优先级任务：{execution_id}"
                        )
                        return self._execute_task_sync(
                            execution_id=execution_id,
                            task_type=task_type,
                            payload=payload,
                            timeout_seconds=min(timeout_seconds, 300)
                        )
                    else:
                        # 【降级策略 3】低优先级任务拒绝
                        api_logger.error(
                            f"[BackgroundService] ❌ 队列已满，拒绝低优先级任务："
                            f"current_size={self._queue_current_size}, priority={priority}"
                        )
                        raise QueueFullError(
                            f"分析任务队列已满（{self._queue_current_size}/{self.max_queue_size}），"
                            f"请稍后重试（优先级={priority}）"
                        )

        # 正常提交流程
        task_id = f"{execution_id}_{task_type}_{uuid.uuid4().hex[:8]}"
        effective_timeout = max(180, min(timeout_seconds, 300))

        task_record = AnalysisTask(
            task_id=task_id,
            execution_id=execution_id,
            task_type=task_type,
            payload=payload,
            status=TaskStatus.PENDING,
            timeout_seconds=effective_timeout
        )

        with self._lock:
            self._analysis_tasks[task_id] = task_record
            self._queue_current_size = len(self._analysis_tasks)

        future = self._executor.submit(self._execute_analysis_task, task_id)

        api_logger.info(
            f"[BackgroundService] 提交分析任务：{task_id}, "
            f"type={task_type}, priority={priority}, 队列大小={self._queue_current_size}/{self.max_queue_size}"
        )

        return task_id

    def _cleanup_completed_tasks(self, max_age_minutes: int = 5) -> int:
        """
        清理已完成的任务（为队列腾空间）

        参数：
            max_age_minutes: 完成超过多少分钟的任务被清理

        返回：
            清理的任务数

        【P0 新增】自动清理已完成任务
        """
        cleaned_count = 0
        current_time = datetime.now()

        with self._lock:
            tasks_to_remove = []

            # 查找已完成/失败/超时的任务
            for task_id, task in self._analysis_tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                    if task.completed_at:
                        age = (current_time - task.completed_at).total_seconds()
                        if age > max_age_minutes * 60:
                            tasks_to_remove.append(task_id)

            # 清理旧任务
            for task_id in tasks_to_remove:
                del self._analysis_tasks[task_id]
                cleaned_count += 1

            # 更新队列大小
            self._queue_current_size = len(self._analysis_tasks)

        if cleaned_count > 0:
            api_logger.info(
                f"[BackgroundService] 🧹 清理 {cleaned_count} 个已完成任务 "
                f"(>{max_age_minutes}分钟)"
            )

        return cleaned_count

    def _execute_task_sync(
        self,
        execution_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout_seconds: int
    ) -> str:
        """
        同步执行任务（降级策略）

        参数：
            execution_id: 执行 ID
            task_type: 任务类型
            payload: 任务参数
            timeout_seconds: 超时时间

        返回：
            task_id

        【P0 新增】高优先级任务同步执行
        """
        task_id = f"{execution_id}_{task_type}_sync_{uuid.uuid4().hex[:8]}"

        task_record = AnalysisTask(
            task_id=task_id,
            execution_id=execution_id,
            task_type=task_type,
            payload=payload,
            status=TaskStatus.RUNNING,  # 直接标记为运行中
            timeout_seconds=timeout_seconds
        )

        with self._lock:
            self._analysis_tasks[task_id] = task_record
            self._queue_current_size = len(self._analysis_tasks)

        try:
            # 同步执行
            self._execute_analysis_task(task_id)

            api_logger.info(
                f"[BackgroundService] ✅ 同步任务完成：{task_id}"
            )
        except Exception as e:
            api_logger.error(
                f"[BackgroundService] ❌ 同步任务失败：{task_id}, error={e}"
            )

        return task_id

    def _execute_analysis_task(self, task_id: str):
        """
        执行分析任务

        Args:
            task_id: 任务 ID
        """
        task = None
        with self._lock:
            if task_id in self._analysis_tasks:
                task = self._analysis_tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()

        if not task:
            api_logger.error(f"[BackgroundService] 任务不存在：{task_id}")
            return

        try:
            # 检查超时
            elapsed = (datetime.now() - task.started_at).total_seconds() if task.started_at else 0
            if elapsed > task.timeout_seconds:
                raise TimeoutError(f"任务执行超时：{task.timeout_seconds}秒")

            # 根据任务类型执行不同的分析
            task_type = task.task_type
            payload = task.payload

            if task_type == 'brand_analysis':
                result = self._execute_brand_analysis(payload)
            elif task_type == 'competitive_analysis':
                result = self._execute_competitive_analysis(payload)
            elif task_type == 'statistics':
                result = self._execute_statistics(payload)
            else:
                raise ValueError(f"未知任务类型：{task_type}")

            # 更新状态为完成
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()

            api_logger.info(f"[BackgroundService] 分析任务完成：{task_id}, type={task.task_type}")

        except TimeoutError as e:
            api_logger.error(f"[BackgroundService] 分析任务超时：{task_id}, error={e}")
            with self._lock:
                task.status = TaskStatus.TIMEOUT
                task.error = str(e)
                task.completed_at = datetime.now()
                # 【P1 修复】确保 result 不为 None，即使超时也有部分数据
                if task.result is None:
                    task.result = {'_timeout': True, '_error': str(e)}

        except Exception as e:
            api_logger.error(f"[BackgroundService] 分析任务失败：{task_id}, error={e}", exc_info=True)
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                # 【P1 修复】确保 result 不为 None，即使失败也有错误信息
                if task.result is None:
                    task.result = {'_failed': True, '_error': str(e)}

    def _execute_brand_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行品牌分析任务

        Args:
            payload: 任务参数，包含：
                - results: AI 诊断结果列表
                - user_brand: 用户品牌名称
                - user_selected_models: 用户选择的模型列表（新增）

        Returns:
            品牌分析结果
        """
        # 【P0 关键修复 - 2026-03-04】增强日志埋点，便于排查问题
        start_time = datetime.now()
        try:
            from .brand_analysis_service import BrandAnalysisService

            results = payload.get('results', [])
            user_brand = payload.get('user_brand', '')
            competitor_brands = payload.get('competitor_brands', [])
            user_selected_models = payload.get('user_selected_models', [])  # 【P0 修复】获取用户选择的模型

            api_logger.info(
                f"[BackgroundService] 🚀 品牌分析任务开始：user_brand={user_brand}, "
                f"results_count={len(results)}, competitor_count={len(competitor_brands)}, "
                f"user_selected_models={user_selected_models}"
            )

            if not results or not user_brand:
                raise ValueError(
                    f"品牌分析缺少必要参数：results={len(results) if results else 0}, "
                    f"user_brand='{user_brand}'"
                )

            # 【P0 修复】传递用户选择的模型列表，让品牌分析服务使用用户选择的模型
            service = BrandAnalysisService(user_selected_models=user_selected_models)
            api_logger.info(f"[BackgroundService] 调用 BrandAnalysisService.analyze_brand_mentions")

            # 【P0 新增】记录分析开始时间
            analysis_start = datetime.now()
            analysis_result = service.analyze_brand_mentions(
                results=results,
                user_brand=user_brand,
                competitor_brands=competitor_brands
            )
            analysis_duration = (datetime.now() - analysis_start).total_seconds()

            api_logger.info(
                f"[BackgroundService] ⏱️ 品牌分析耗时：{analysis_duration:.2f}秒"
            )

            # 检查是否有错误
            if '_analysis_error' in analysis_result:
                api_logger.warning(
                    f"[BackgroundService] 品牌分析返回错误：{analysis_result['_analysis_error']}"
                )

            total_duration = (datetime.now() - start_time).total_seconds()
            api_logger.info(
                f"[BackgroundService] ✅ 品牌分析完成：user_brand={user_brand}, "
                f"总耗时={total_duration:.2f}秒"
            )

            return {
                'success': True,
                'data': analysis_result,
                'brand': user_brand,
                'duration_seconds': total_duration
            }

        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            api_logger.error(
                f"[BackgroundService] ❌ 品牌分析失败：user_brand={user_brand}, "
                f"耗时={total_duration:.2f}秒，错误={e}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    def _execute_competitive_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行竞争分析任务

        Args:
            payload: 任务参数，包含：
                - results: AI 诊断结果列表
                - main_brand: 主品牌名称
                - competitor_brands: 竞品品牌列表

        Returns:
            竞争分析结果
        """
        # 【P0 关键修复 - 2026-03-04】增强日志埋点，便于排查问题
        start_time = datetime.now()
        try:
            from .competitive_analysis_service import CompetitiveAnalysisService

            results = payload.get('results', [])
            main_brand = payload.get('main_brand', '')
            competitor_brands = payload.get('competitor_brands', [])

            api_logger.info(
                f"[BackgroundService] 🚀 竞争分析任务开始：main_brand={main_brand}, "
                f"results_count={len(results)}, competitor_count={len(competitor_brands)}"
            )

            if not results or not main_brand:
                raise ValueError("竞争分析缺少必要参数：results 或 main_brand")

            # 【P0 新增】记录分析开始时间
            analysis_start = datetime.now()
            analysis_result = CompetitiveAnalysisService.analyze_competition(
                results=results,
                main_brand=main_brand,
                competitor_brands=competitor_brands
            )
            analysis_duration = (datetime.now() - analysis_start).total_seconds()

            api_logger.info(
                f"[BackgroundService] ⏱️ 竞争分析耗时：{analysis_duration:.2f}秒"
            )

            total_duration = (datetime.now() - start_time).total_seconds()
            api_logger.info(
                f"[BackgroundService] ✅ 竞争分析完成：main_brand={main_brand}, "
                f"总耗时={total_duration:.2f}秒"
            )

            return {
                'success': True,
                'data': analysis_result,
                'main_brand': main_brand,
                'duration_seconds': total_duration
            }

        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            api_logger.error(
                f"[BackgroundService] ❌ 竞争分析失败：main_brand={main_brand}, "
                f"耗时={total_duration:.2f}秒，错误={e}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    def _execute_statistics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行统计计算任务

        Args:
            payload: 任务参数，包含：
                - results: AI 诊断结果列表

        Returns:
            统计结果
        """
        try:
            results = payload.get('results', [])

            if not results:
                raise ValueError("统计计算缺少必要参数：results")

            # 基础统计
            total_count = len(results)
            avg_score = sum(r.get('score', 0) for r in results) / total_count if total_count > 0 else 0

            # 按平台分组统计
            platform_stats = {}
            for result in results:
                platform = result.get('platform', 'unknown')
                if platform not in platform_stats:
                    platform_stats[platform] = {'count': 0, 'total_score': 0}
                platform_stats[platform]['count'] += 1
                platform_stats[platform]['total_score'] += result.get('score', 0)

            # 计算平均分
            for stats in platform_stats.values():
                if stats['count'] > 0:
                    stats['avg_score'] = round(stats['total_score'] / stats['count'])

            api_logger.info(f"[BackgroundService] 统计计算完成：total={total_count}, avg_score={avg_score:.1f}")

            return {
                'success': True,
                'data': {
                    'total_count': total_count,
                    'average_score': round(avg_score),
                    'platform_stats': platform_stats
                }
            }

        except Exception as e:
            api_logger.error(f"[BackgroundService] 统计计算失败：{e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_task_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            execution_id: 执行 ID

        Returns:
            任务状态字典，包含：
                - execution_id: 执行 ID
                - total_tasks: 总任务数
                - completed_tasks: 已完成任务数
                - analysis_complete: 是否所有分析都完成（或已终止）
                - analysis_results: 分析结果聚合

        【P0 关键修复 - 2026-03-05】
        改进 analysis_complete 判断逻辑：
        1. 所有任务终止（COMPLETED/FAILED/TIMEOUT）即视为分析结束
        2. 至少有一个任务完成（确保有部分结果）
        3. 避免编排器无限等待已失败/超时的任务
        """
        with self._lock:
            # 查找所有属于该 execution_id 的任务
            tasks = [
                task for task in self._analysis_tasks.values()
                if task.execution_id == execution_id
            ]

        if not tasks:
            return None

        # 【P0 修复】检查是否所有任务都已终止（完成/失败/超时）
        all_terminated = all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]
            for task in tasks
        )

        # 【P0 修复】检查是否至少有一个任务成功完成
        has_completed = any(
            task.status == TaskStatus.COMPLETED
            for task in tasks
        )

        # 【P0 修复】分析结束条件：所有任务终止 + 至少一个完成
        # 这样即使有任务失败/超时，编排器也能感知并继续生成报告
        analysis_complete = all_terminated and has_completed

        # 聚合结果
        analysis_results = {}
        for task in tasks:
            if task.result:
                analysis_results[task.task_type] = task.result

        return {
            'execution_id': execution_id,
            'total_tasks': len(tasks),
            'completed_tasks': sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            'failed_tasks': sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            'timeout_tasks': sum(1 for t in tasks if t.status == TaskStatus.TIMEOUT),
            'running_tasks': sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            'pending_tasks': sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            'analysis_complete': analysis_complete,
            'analysis_results': analysis_results,
            # 【P0 新增】详细状态字段，便于调试
            'all_terminated': all_terminated,
            'has_completed': has_completed
        }

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据任务 ID 获取任务详情

        Args:
            task_id: 任务 ID

        Returns:
            任务详情字典
        """
        with self._lock:
            if task_id not in self._analysis_tasks:
                return None

            task = self._analysis_tasks[task_id]
            return {
                'task_id': task.task_id,
                'execution_id': task.execution_id,
                'task_type': task.task_type,
                'status': task.status.value,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'result': task.result,
                'error': task.error,
                'timeout_seconds': task.timeout_seconds
            }

    def cleanup_completed_tasks(self, max_age_minutes: int = 30) -> int:
        """
        清理已完成的任务记录

        Args:
            max_age_minutes: 保留最大分钟数

        Returns:
            清理的任务数量
        """
        now = datetime.now()
        cleaned_count = 0

        with self._lock:
            to_remove = []
            for task_id, task in self._analysis_tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                    if task.completed_at:
                        age = (now - task.completed_at).total_seconds() / 60
                        if age > max_age_minutes:
                            to_remove.append(task_id)

            for task_id in to_remove:
                del self._analysis_tasks[task_id]
                cleaned_count += 1

        if cleaned_count > 0:
            api_logger.info(f"[BackgroundService] 清理 {cleaned_count} 个已完成的任务记录")

        return cleaned_count


# =============================================================================
# 全局单例
# =============================================================================

_service_manager: Optional[BackgroundServiceManager] = None
_manager_lock = threading.Lock()
_services_initialized = False  # P0-20260302: 防止重复初始化


def get_background_service_manager(max_workers: int = 4) -> BackgroundServiceManager:
    """获取全局后台服务管理器（单例模式）"""
    global _service_manager
    if _service_manager is None:
        with _manager_lock:
            if _service_manager is None:
                _service_manager = BackgroundServiceManager(max_workers=max_workers)
    return _service_manager


def reset_background_service_manager():
    """重置全局后台服务管理器（用于测试）"""
    global _service_manager, _services_initialized
    with _manager_lock:
        if _service_manager:
            _service_manager.stop()
        _service_manager = None
        _services_initialized = False


def is_services_initialized() -> bool:
    """检查后台服务是否已初始化"""
    return _services_initialized


# =============================================================================
# 预定义的清理任务函数
# =============================================================================

def create_sse_cleanup_task(sse_manager_getter: Callable) -> Callable:
    """
    创建 SSE 清理任务

    Args:
        sse_manager_getter: 获取 SSE 管理器的函数

    Returns:
        清理任务函数
    """
    def cleanup():
        try:
            manager = sse_manager_getter()
            if manager:
                manager.cleanup_inactive()
                api_logger.debug("[BackgroundService] SSE 清理完成")
        except Exception as e:
            api_logger.error(f"[BackgroundService] SSE 清理失败：{e}")
    
    return cleanup


def create_export_cleanup_task(export_service_getter: Callable, max_age_hours: int = 24) -> Callable:
    """
    创建导出文件清理任务

    Args:
        export_service_getter: 获取导出服务的函数
        max_age_hours: 保留最大小时数

    Returns:
        清理任务函数
    """
    def cleanup():
        try:
            service = export_service_getter()
            if service:
                cleaned = service.cleanup_old_tasks(max_age_hours)
                api_logger.info(f"[BackgroundService] 导出文件清理：移除 {cleaned} 个旧任务")
        except Exception as e:
            api_logger.error(f"[BackgroundService] 导出文件清理失败：{e}")
    
    return cleanup


def create_cache_maintenance_task(cache_maintenance_func: Callable) -> Callable:
    """
    创建缓存维护任务

    Args:
        cache_maintenance_func: 缓存维护函数

    Returns:
        维护任务函数
    """
    def maintenance():
        try:
            cache_maintenance_func()
            api_logger.debug("[BackgroundService] 缓存维护完成")
        except Exception as e:
            api_logger.error(f"[BackgroundService] 缓存维护失败：{e}")
    
    return maintenance


# =============================================================================
# 初始化函数
# =============================================================================

def initialize_background_services():
    """
    初始化所有后台服务

    应该在 app.py 启动时调用，替代各个独立的清理线程
    
    P0-20260302: 添加重复初始化防护
    """
    global _services_initialized
    
    # 防止重复初始化（Flask Debug 模式可能导致）
    if _services_initialized:
        api_logger.warning("[BackgroundService] 服务已初始化，跳过重复初始化")
        return
    
    _services_initialized = True
    manager = get_background_service_manager()

    # 【P0 关键修复 - 2026-03-02】删除 SSE 清理任务（微信小程序不支持 SSE）
    # 注册 SSE 清理任务（每 60 秒） - 已删除
    # try:
    #     from wechat_backend.services.sse_service_v2 import get_sse_manager
    #     manager.register_task(
    #         name="sse_cleanup",
    #         func=create_sse_cleanup_task(get_sse_manager),
    #         interval_seconds=60,
    #         enabled=True
    #     )
    # except Exception as e:
    #     api_logger.warning(f"[BackgroundService] 注册 SSE 清理任务失败：{e}")

    # 注册导出文件清理任务（每小时）
    try:
        from wechat_backend.services.async_export_service import get_async_export_service
        manager.register_task(
            name="export_cleanup",
            func=create_export_cleanup_task(get_async_export_service, max_age_hours=24),
            interval_seconds=3600,  # 1 小时
            enabled=True
        )
    except Exception as e:
        api_logger.warning(f"[BackgroundService] 注册导出清理任务失败：{e}")
    
    # 注册缓存维护任务（每 5 分钟）
    try:
        from wechat_backend.cache.api_cache import _cleanup_expired_entries
        manager.register_task(
            name="cache_maintenance",
            func=create_cache_maintenance_task(_cleanup_expired_entries),
            interval_seconds=300,  # 5 分钟
            enabled=True
        )
    except Exception as e:
        api_logger.warning(f"[BackgroundService] 注册缓存维护任务失败：{e}")
    
    # 启动服务管理器（任务错峰 10 秒）
    manager.start(stagger_seconds=10)
    
    api_logger.info("✅ 统一后台服务管理器已启动")
    
    return manager
