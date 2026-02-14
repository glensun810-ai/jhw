"""
WorkflowManager - 智能任务分发系统
处理负面证据的自动任务打包和分发
"""
import json
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import threading
import queue
from dataclasses import dataclass
from ..logging_config import api_logger
from ..database import DB_PATH
from ..security.sql_protection import SafeDatabaseQuery, sql_protector
from ..circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from ..ai_adapters.base_provider import BaseAIProvider
from ..ai_adapters.doubao_provider import DoubaoProvider
from ..ai_adapters.deepseek_provider import DeepSeekProvider
from ..config_manager import config_manager
import sys
import os
# Add the project root directory to the Python path to allow importing from utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from utils.debug_manager import debug_log, ai_io_log, status_flow_log, exception_log

# Import the new DEBUG_AI_CODE logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from backend_python.utils.logger import debug_log_status_flow, debug_log_exception, ENABLE_DEBUG_AI_CODE


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WorkflowTask:
    """工作流任务数据结构"""
    task_id: str
    evidence_fragment: str
    associated_url: str
    source_name: str
    risk_level: str
    brand_name: str
    intervention_script: str
    source_meta: Dict[str, Any]
    webhook_url: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    next_retry_at: Optional[datetime] = None


class WebhookManager:
    """Webhook管理器 - 处理任务推送至第三方API"""
    
    def __init__(self):
        self.session = requests.Session()
        # 设置默认请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'EvolutionBay-GEO-Workflow-Manager/1.0'
        })
        
        # 初始化电路断路器
        self.circuit_breaker = get_circuit_breaker(platform_name="webhook", model_name="dispatcher")
    
    def send_webhook(self, webhook_url: str, payload: Dict[str, Any], task_id: str, max_retries: int = 3) -> bool:
        """
        发送Webhook请求到目标URL，包含重试机制

        Args:
            webhook_url: 目标Webhook URL
            payload: 要发送的载荷数据
            task_id: 任务ID，用于日志记录
            max_retries: 最大重试次数

        Returns:
            bool: 是否发送成功
        """
        debug_log("WEBHOOK_DISPATCH", f"Starting webhook dispatch for task {task_id} to {webhook_url}")

        retry_count = 0

        while retry_count <= max_retries:
            try:
                # 使用电路断路器保护Webhook调用
                success = self.circuit_breaker.call(
                    self._send_webhook_internal,
                    webhook_url,
                    payload,
                    task_id
                )

                if success:
                    debug_log("WEBHOOK_DISPATCH", f"Webhook dispatch successful for task {task_id}")
                    return True
                else:
                    # 如果失败，检查是否需要重试
                    if retry_count < max_retries:
                        # 计算重试延迟时间（指数退避算法）
                        delay_seconds = min(60 * (2 ** retry_count), 300)  # 最大5分钟延迟
                        debug_log("WEBHOOK_DISPATCH", f"Webhook failed for task {task_id}, retrying in {delay_seconds}s (attempt {retry_count + 1}/{max_retries})")
                        time.sleep(delay_seconds)
                        retry_count += 1
                    else:
                        debug_log("WEBHOOK_DISPATCH", f"Webhook failed for task {task_id} after {max_retries} retries")
                        return False

            except CircuitBreakerOpenError as e:
                exception_log(f"Circuit breaker is open for task {task_id}, skipping webhook to {webhook_url}. Error: {str(e)}")
                return False
            except Exception as e:
                exception_log(f"Error sending webhook for task {task_id}: {str(e)}")
                if retry_count < max_retries:
                    delay_seconds = min(60 * (2 ** retry_count), 300)
                    debug_log("WEBHOOK_DISPATCH", f"Retrying webhook for task {task_id} in {delay_seconds}s (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(delay_seconds)
                    retry_count += 1
                else:
                    return False

        return False
    
    def _send_webhook_internal(self, webhook_url: str, payload: Dict[str, Any], task_id: str) -> bool:
        """
        内部Webhook发送逻辑
        """
        try:
            debug_log("WEBHOOK_INTERNAL", f"Sending internal webhook request for task {task_id} to {webhook_url}")

            response = self.session.post(
                webhook_url,
                json=payload,
                timeout=30  # 30秒超时
            )

            if response.status_code in [200, 201, 202]:
                debug_log("WEBHOOK_INTERNAL", f"Webhook sent successfully to {webhook_url} for task {task_id}, status: {response.status_code}")
                return True
            else:
                debug_log("WEBHOOK_INTERNAL", f"Webhook received non-success status {response.status_code} from {webhook_url} for task {task_id}")
                return False

        except requests.exceptions.Timeout:
            exception_log(f"Webhook request timed out for {webhook_url} (task {task_id})")
            # 超时应该传播给断路器以触发熔断
            raise requests.exceptions.Timeout(f"Webhook request to {webhook_url} timed out")
        except requests.exceptions.RequestException as e:
            exception_log(f"Webhook request failed for {webhook_url} (task {task_id}): {str(e)}")
            # 其他请求异常也应传播给断路器
            raise e
        except Exception as e:
            exception_log(f"Unexpected error sending webhook to {webhook_url} (task {task_id}): {str(e)}")
            return False


class WorkflowManager:
    """工作流管理器 - 智能任务分发系统"""
    
    def __init__(self):
        self.webhook_manager = WebhookManager()
        self.db_path = DB_PATH
        self.safe_query = SafeDatabaseQuery(self.db_path)
        
        # 任务队列
        self.task_queue = queue.Queue()
        
        # 重试队列 - 存储需要重试的任务
        self.retry_queue = queue.PriorityQueue()  # 使用优先级队列，按重试时间排序
        
        # 启动后台任务处理器
        self._start_background_processor()
        self._start_retry_processor()

    def _start_background_processor(self):
        """启动后台任务处理器"""
        def worker():
            while True:
                try:
                    task_tuple = self.task_queue.get(timeout=1)
                    if task_tuple is None:
                        break
                    self._process_task(task_tuple)
                    self.task_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    exception_log(f"Error in background processor: {str(e)}")

        # 启动后台线程
        debug_log("WORKFLOW_MANAGER", "Starting background processor thread")
        self.processor_thread = threading.Thread(target=worker, daemon=True)
        self.processor_thread.start()

    def _start_retry_processor(self):
        """启动重试处理器"""
        def retry_worker():
            while True:
                try:
                    # 检查是否有需要重试的任务
                    if not self.retry_queue.empty():
                        next_retry_time, task_data = self.retry_queue.queue[0]
                        current_time = datetime.now().timestamp()

                        if next_retry_time <= current_time:
                            # 从队列中取出任务
                            self.retry_queue.get()
                            # 处理重试任务
                            self._process_task_with_retry(task_data)

                    # 每秒检查一次
                    time.sleep(1)
                except Exception as e:
                    exception_log(f"Error in retry processor: {str(e)}")
                    time.sleep(1)

        # 启动重试处理线程
        debug_log("WORKFLOW_MANAGER", "Starting retry processor thread")
        self.retry_thread = threading.Thread(target=retry_worker, daemon=True)
        self.retry_thread.start()

    def create_task_package(
        self, 
        evidence_fragment: str, 
        associated_url: str, 
        source_name: str, 
        risk_level: str, 
        brand_name: str,
        intervention_script: str,
        source_meta: Dict[str, Any],
        webhook_url: str
    ) -> Dict[str, Any]:
        """
        创建标准化的任务包

        Args:
            evidence_fragment: 证据片段
            associated_url: 关联URL
            source_name: 信源名称
            risk_level: 风险等级
            brand_name: 品牌名称
            intervention_script: 干预脚本
            source_meta: 信源元数据
            webhook_url: Webhook URL

        Returns:
            Dict: 标准化任务包
        """
        task_package = {
            "task_type": "negative_evidence_intervention",
            "evidence_data": {
                "evidence_fragment": evidence_fragment,
                "associated_url": associated_url,
                "source_name": source_name,
                "risk_level": risk_level,
                "brand_name": brand_name,
                "intervention_script": intervention_script,
                "source_meta": source_meta
            },
            "delivery_instructions": {
                "webhook_url": webhook_url,
                "delivery_format": "standard_payload",
                "callback_required": True
            },
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        }
        
        return task_package
    
    def dispatch_task(
        self,
        evidence_fragment: str,
        associated_url: str,
        source_name: str,
        risk_level: str,
        brand_name: str,
        intervention_script: str,
        source_meta: Dict[str, Any],
        webhook_url: str,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """
        分发任务到指定的Webhook URL

        Args:
            evidence_fragment: 证据片段
            associated_url: 关联URL
            source_name: 信源名称
            risk_level: 风险等级
            brand_name: 品牌名称
            intervention_script: 干预脚本
            source_meta: 信源元数据
            webhook_url: Webhook URL
            priority: 任务优先级

        Returns:
            str: 任务ID
        """
        import uuid

        # 生成任务ID
        task_id = f"wf_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        debug_log("TASK_DISPATCH", f"Creating task package for task {task_id}")

        # 创建任务包
        task_package = self.create_task_package(
            evidence_fragment, associated_url, source_name,
            risk_level, brand_name, intervention_script, source_meta, webhook_url
        )

        # 创建任务数据
        task_data = {
            'task_id': task_id,
            'task_package': task_package,
            'webhook_url': webhook_url,
            'priority': priority.value,
            'created_at': datetime.utcnow(),
            'retry_count': 0,
            'max_retries': 3
        }

        # 将任务添加到队列（优先级队列）
        priority_num = self._priority_to_number(priority)
        self.task_queue.put((priority_num, task_data))

        debug_log("TASK_DISPATCH", f"Task {task_id} queued for dispatch to {webhook_url} with priority {priority.value}")

        return task_id
    
    def _priority_to_number(self, priority: TaskPriority) -> int:
        """将优先级转换为数字，用于队列排序"""
        priority_map = {
            TaskPriority.CRITICAL: 1,  # 最高优先级
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4   # 最低优先级
        }
        return priority_map.get(priority, 3)  # 默认为MEDIUM
    
    def _process_task(self, task_tuple: tuple):
        """处理单个任务"""
        priority_num, task_data = task_tuple
        task_id = task_data['task_id']
        task_package = task_data['task_package']
        webhook_url = task_data['webhook_url']

        debug_log("TASK_PROCESS", f"Processing workflow task {task_id}")

        # 发送Webhook
        success = self.webhook_manager.send_webhook(webhook_url, task_package, task_id)

        if success:
            debug_log("TASK_PROCESS", f"Task {task_id} completed successfully")
            # 更新任务状态为完成
            self._update_task_status(task_id, TaskStatus.COMPLETED)
        else:
            # 检查是否需要重试
            retry_count = task_data.get('retry_count', 0)
            max_retries = task_data.get('max_retries', 3)

            if retry_count < max_retries:
                # 计算重试延迟时间（指数退避算法）
                delay_seconds = min(60 * (2 ** retry_count), 300)  # 最大5分钟延迟
                next_retry_time = datetime.now() + timedelta(seconds=delay_seconds)

                # 更新任务数据
                task_data['retry_count'] = retry_count + 1
                task_data['next_retry_at'] = next_retry_time

                # 添加到重试队列
                self.retry_queue.put((next_retry_time.timestamp(), task_data))

                debug_log("TASK_PROCESS", f"Task {task_id} failed, scheduled for retry #{retry_count + 1} at {next_retry_time} (delay: {delay_seconds}s)")
                self._update_task_status(task_id, TaskStatus.RETRYING)
            else:
                # 达到最大重试次数，标记为失败
                debug_log("TASK_PROCESS", f"Task {task_id} failed after {max_retries} retries")
                self._update_task_status(task_id, TaskStatus.FAILED)
    
    def _process_task_with_retry(self, task_data: Dict[str, Any]):
        """处理重试任务"""
        task_id = task_data['task_id']
        task_package = task_data['task_package']
        webhook_url = task_data['webhook_url']

        debug_log("TASK_RETRY", f"Retrying workflow task {task_id}")

        # 发送Webhook
        success = self.webhook_manager.send_webhook(webhook_url, task_package, task_id)

        if success:
            debug_log("TASK_RETRY", f"Task {task_id} completed successfully after retry")
            # 更新任务状态为完成
            self._update_task_status(task_id, TaskStatus.COMPLETED)
        else:
            # 检查是否需要继续重试
            retry_count = task_data.get('retry_count', 0)
            max_retries = task_data.get('max_retries', 3)

            if retry_count < max_retries:
                # 计算重试延迟时间（指数退避算法）
                delay_seconds = min(60 * (2 ** retry_count), 300)  # 最大5分钟延迟
                next_retry_time = datetime.now() + timedelta(seconds=delay_seconds)

                # 更新任务数据
                task_data['retry_count'] = retry_count + 1
                task_data['next_retry_at'] = next_retry_time

                # 添加到重试队列
                self.retry_queue.put((next_retry_time.timestamp(), task_data))

                debug_log("TASK_RETRY", f"Task {task_id} retry failed, scheduled for retry #{retry_count + 1} at {next_retry_time} (delay: {delay_seconds}s)")
                self._update_task_status(task_id, TaskStatus.RETRYING)
            else:
                # 达到最大重试次数，标记为失败
                debug_log("TASK_RETRY", f"Task {task_id} failed after {max_retries} retries")
                self._update_task_status(task_id, TaskStatus.FAILED)
    
    def _update_task_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        # Extract execution_id from task_id if it contains one (for DEBUG_AI_CODE logging)
        # Assuming task_id format might contain execution_id, or we can pass it separately
        execution_id = getattr(self, '_current_execution_id', 'unknown')  # Default to unknown if not set

        # Here we would normally have access to the old and new stages and progress
        # For now, we'll simulate the old/new stage transition info
        old_stage = getattr(self, '_previous_stage', 'unknown')
        new_stage = status.value
        progress_value = getattr(self, '_current_progress', 0)  # Default to 0 if not set

        # 这里可以实现数据库更新逻辑
        # 暂时只记录日志
        debug_log("STATUS_FLOW", f"Task {task_id} status updated to {status.value}")
        status_flow_log(f"Task {task_id} status updated to {status.value}")

        # Log with DEBUG_AI_CODE system
        if ENABLE_DEBUG_AI_CODE:
            debug_log_status_flow("WORKFLOW_MANAGER", execution_id, old_stage, new_stage, progress_value) # #DEBUG_CLEAN

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 这里可以实现从数据库获取任务状态的逻辑
        # 暂时返回模拟数据
        debug_log("STATUS_QUERY", f"Getting status for task {task_id}")
        return {
            'task_id': task_id,
            'status': 'completed',  # 模拟状态
            'completed_at': datetime.utcnow().isoformat()
        }