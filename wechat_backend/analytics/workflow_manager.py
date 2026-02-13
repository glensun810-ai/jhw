"""
工作流管理器 - 智能任务分发系统
"""
import json
import requests
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging
from dataclasses import dataclass
from ..logging_config import api_logger


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
    next_retry_at: Optional[datetime] = None


class WorkflowManager:
    """工作流管理器 - 实现智能任务分发系统"""

    def __init__(self):
        self.logger = api_logger
        self.active_tasks = {}  # 存储活动任务
        self.webhook_timeout = 30  # Webhook请求超时时间（秒）
        self.retry_delay_base = 60  # 重试延迟基数（秒）

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
            intervention_script: 纠偏建议脚本
            source_meta: 源元数据
            webhook_url: Webhook URL

        Returns:
            Dict: 标准化任务包
        """
        task_package = {
            "task_id": f"wf_{int(time.time())}_{hash(evidence_fragment) % 10000}",
            "payload": {
                "evidence_fragment": evidence_fragment,
                "associated_url": associated_url,
                "source_name": source_name,
                "risk_level": risk_level,
                "brand_name": brand_name,
                "intervention_script": intervention_script,
                "source_meta": source_meta,
                "created_at": datetime.utcnow().isoformat()
            },
            "webhook_url": webhook_url,
            "delivery_attempts": 0,
            "max_delivery_attempts": 3
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
        webhook_url: str
    ) -> str:
        """
        分发任务到指定的Webhook URL

        Args:
            evidence_fragment: 证据片段
            associated_url: 关联URL
            source_name: 信源名称
            risk_level: 风险等级
            brand_name: 品牌名称
            intervention_script: 纠偏建议脚本
            source_meta: 源元数据
            webhook_url: Webhook URL

        Returns:
            str: 任务ID
        """
        # 创建任务包
        task_package = self.create_task_package(
            evidence_fragment, associated_url, source_name, risk_level,
            brand_name, intervention_script, source_meta, webhook_url
        )

        task_id = task_package["task_id"]

        # 创建任务对象
        task = WorkflowTask(
            task_id=task_id,
            evidence_fragment=evidence_fragment,
            associated_url=associated_url,
            source_name=source_name,
            risk_level=risk_level,
            brand_name=brand_name,
            intervention_script=intervention_script,
            source_meta=source_meta,
            webhook_url=webhook_url,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 存储任务
        self.active_tasks[task_id] = task

        # 异步发送Webhook请求
        threading.Thread(
            target=self._send_webhook_async,
            args=(task_package, task),
            daemon=True
        ).start()

        self.logger.info(f"Task {task_id} dispatched to {webhook_url}")

        return task_id

    def _send_webhook_async(self, task_package: Dict[str, Any], task: WorkflowTask):
        """异步发送Webhook请求"""
        task.status = TaskStatus.PROCESSING
        task.updated_at = datetime.utcnow()
        
        success = self._send_webhook_request(task_package, task)
        
        if success:
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.utcnow()
            self.logger.info(f"Task {task.task_id} completed successfully")
        else:
            # 如果失败，检查是否需要重试
            if task.retry_count < task.max_retries:
                self._schedule_retry(task_package, task)
            else:
                task.status = TaskStatus.FAILED
                task.updated_at = datetime.utcnow()
                self.logger.error(f"Task {task.task_id} failed after {task.max_retries} attempts")

    def _send_webhook_request(self, task_package: Dict[str, Any], task: WorkflowTask) -> bool:
        """
        发送Webhook请求

        Args:
            task_package: 任务包
            task: 任务对象

        Returns:
            bool: 是否成功
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'EvolutionBay-Workflow-Manager/1.0'
            }

            response = requests.post(
                task.webhook_url,
                json=task_package,
                headers=headers,
                timeout=self.webhook_timeout
            )

            # 检查响应状态
            if response.status_code in [200, 201, 202]:
                self.logger.info(f"Webhook request to {task.webhook_url} succeeded with status {response.status_code}")
                return True
            else:
                self.logger.warning(f"Webhook request to {task.webhook_url} failed with status {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            self.logger.error(f"Webhook request to {task.webhook_url} timed out after {self.webhook_timeout}s")
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Webhook request to {task.webhook_url} failed due to connection error")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Webhook request to {task.webhook_url} failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending webhook to {task.webhook_url}: {str(e)}")
            return False

    def _schedule_retry(self, task_package: Dict[str, Any], task: WorkflowTask):
        """
        安排重试

        Args:
            task_package: 任务包
            task: 任务对象
        """
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        task.updated_at = datetime.utcnow()
        
        # 计算下次重试时间（指数退避）
        delay_seconds = self.retry_delay_base * (2 ** (task.retry_count - 1))
        task.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        self.logger.info(f"Scheduling retry #{task.retry_count} for task {task.task_id} in {delay_seconds}s")
        
        # 在延迟后重试
        def delayed_retry():
            time.sleep(delay_seconds)
            self._handle_retry(task_package, task)
        
        threading.Thread(target=delayed_retry, daemon=True).start()

    def _handle_retry(self, task_package: Dict[str, Any], task: WorkflowTask):
        """
        处理重试逻辑

        Args:
            task_package: 任务包
            task: 任务对象
        """
        self.logger.info(f"Retrying task {task.task_id}, attempt #{task.retry_count}")
        
        success = self._send_webhook_request(task_package, task)
        
        if success:
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.utcnow()
            self.logger.info(f"Task {task.task_id} completed successfully on retry #{task.retry_count}")
        else:
            if task.retry_count < task.max_retries:
                self._schedule_retry(task_package, task)
            else:
                task.status = TaskStatus.FAILED
                task.updated_at = datetime.utcnow()
                self.logger.error(f"Task {task.task_id} failed after {task.max_retries} retry attempts")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 任务状态信息
        """
        if task_id not in self.active_tasks:
            return None

        task = self.active_tasks[task_id]
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "next_retry_at": task.next_retry_at.isoformat() if task.next_retry_at else None
        }

    def get_all_active_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有活动任务

        Returns:
            List[Dict]: 活动任务列表
        """
        tasks = []
        for task in self.active_tasks.values():
            tasks.append({
                "task_id": task.task_id,
                "status": task.status.value,
                "retry_count": task.retry_count,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            })
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]
        task.status = TaskStatus.FAILED  # 标记为失败以停止任何进一步的重试
        del self.active_tasks[task_id]
        
        self.logger.info(f"Task {task_id} cancelled")
        return True


# Example usage
if __name__ == "__main__":
    # Create workflow manager
    wf_manager = WorkflowManager()
    
    # Example evidence data
    evidence_fragment = "该品牌智能锁存在安全隐患，容易被破解"
    associated_url = "https://security-report.com/vulnerability"
    source_name = "安全评测机构"
    risk_level = "High"
    brand_name = "TechBrand"
    intervention_script = "我们非常重视产品的安全性，已立即组织技术团队核查该问题，将在48小时内发布安全补丁。"
    source_meta = {
        "platform": "security-report.com",
        "category": "security",
        "importance": "high",
        "last_updated": "2023-01-01T10:00:00Z"
    }
    webhook_url = "https://hooks.example.com/webhook"
    
    # Dispatch task
    task_id = wf_manager.dispatch_task(
        evidence_fragment, associated_url, source_name, risk_level,
        brand_name, intervention_script, source_meta, webhook_url
    )
    
    print(f"Dispatched task with ID: {task_id}")
    
    # Check task status
    time.sleep(2)  # Wait a bit for processing
    status = wf_manager.get_task_status(task_id)
    print(f"Task status: {status}")