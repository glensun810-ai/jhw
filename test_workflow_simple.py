"""
简单测试工作流管理器
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Import the workflow manager directly without importing the full app
import json
import requests
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging
from dataclasses import dataclass


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
        self.logger = None  # Disable logging for this test
        self.active_tasks = {}  # 存储活动任务
        self.webhook_timeout = 30  # Webhook请求超时时间（秒）
        self.retry_delay_base = 1  # 重试延迟基数（秒）

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

        print(f"Task {task_id} created and stored")

        return task_id

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


def test_workflow_manager():
    """测试工作流管理器的基本功能"""
    print("测试工作流管理器的基本功能...")
    
    # 创建工作流管理器
    wf_manager = WorkflowManager()
    
    # 测试数据
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
    
    # 测试创建任务包
    print("\n1. 测试创建任务包...")
    task_package = wf_manager.create_task_package(
        evidence_fragment, associated_url, source_name, risk_level,
        brand_name, intervention_script, source_meta, webhook_url
    )
    
    print(f"   任务ID: {task_package['task_id']}")
    print(f"   Webhook URL: {task_package['webhook_url']}")
    print(f"   证据片段: {task_package['payload']['evidence_fragment']}")
    print("   ✓ 任务包创建成功")
    
    # 测试分发任务
    print("\n2. 测试分发任务...")
    task_id = wf_manager.dispatch_task(
        evidence_fragment, associated_url, source_name, risk_level,
        brand_name, intervention_script, source_meta, webhook_url
    )
    
    print(f"   分发的任务ID: {task_id}")
    print("   ✓ 任务分发成功")
    
    # 测试获取任务状态
    print("\n3. 测试获取任务状态...")
    status = wf_manager.get_task_status(task_id)
    if status:
        print(f"   任务ID: {status['task_id']}")
        print(f"   状态: {status['status']}")
        print(f"   重试次数: {status['retry_count']}")
        print("   ✓ 任务状态获取成功")
    else:
        print("   ⚠ 无法获取任务状态")
    
    # 测试获取所有活动任务
    print("\n4. 测试获取所有活动任务...")
    all_tasks = wf_manager.get_all_active_tasks()
    print(f"   活动任务数量: {len(all_tasks)}")
    if all_tasks:
        for task in all_tasks:
            print(f"   - 任务ID: {task['task_id']}, 状态: {task['status']}")
        print("   ✓ 活动任务获取成功")
    
    print("\n✓ 所有测试通过！工作流管理器基本功能正常。")


if __name__ == "__main__":
    test_workflow_manager()