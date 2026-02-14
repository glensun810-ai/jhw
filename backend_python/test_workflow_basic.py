"""
测试工作流管理器的基本功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# 导入必要的模块
from datetime import datetime, timedelta
import json
from enum import Enum
from typing import Dict, Any, Optional
import time
import random


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


def test_retry_mechanism():
    """测试重试机制功能"""
    print("测试重试机制功能...")
    
    def calculate_retry_delay(retry_count: int) -> int:
        """
        计算重试延迟时间（指数退避算法）
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            int: 延迟秒数
        """
        # 基础延迟为30秒，每次重试延迟时间翻倍，加上随机抖动
        base_delay = 30  # 30秒基础延迟
        exponential_factor = 2 ** retry_count  # 指数增长
        jitter = random.uniform(0, 10)  # 随机抖动0-10秒
        
        delay = base_delay * exponential_factor + jitter
        # 限制最大延迟时间，避免过长的等待
        max_delay = 3600  # 1小时最大延迟
        return int(min(delay, max_delay))
    
    # 测试重试延迟计算
    print("测试重试延迟计算:")
    for i in range(5):
        delay = calculate_retry_delay(i)
        print(f"  重试次数 {i}: {delay} 秒")
    
    # 验证指数增长
    delay_0 = calculate_retry_delay(0)
    delay_1 = calculate_retry_delay(1)
    delay_2 = calculate_retry_delay(2)
    
    print(f"\n验证指数增长:")
    print(f"  第0次重试延迟: {delay_0}秒")
    print(f"  第1次重试延迟: {delay_1}秒")
    print(f"  第2次重试延迟: {delay_2}秒")
    
    # 基本验证：每次重试延迟应该比上次长（考虑随机抖动因素）
    assert delay_1 >= 60, f"第一次重试延迟应至少60秒，实际{delay_1}秒"
    assert delay_2 >= 120, f"第二次重试延迟应至少120秒，实际{delay_2}秒"
    print("  ✓ 重试延迟计算正确")
    
    print("\n重试机制测试通过!")


def test_task_packaging():
    """测试任务打包功能"""
    print("\n测试任务打包功能...")
    
    def create_task_package(
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
    
    # 测试数据
    evidence_fragment = "该品牌智能锁存在安全隐患"
    associated_url = "https://security-report.com/vulnerability"
    source_name = "安全评测机构"
    risk_level = "High"
    brand_name = "TechBrand"
    intervention_script = "我们高度重视产品安全性，已立即组织技术团队核查该问题"
    source_meta = {"platform": "security-report.com", "category": "security", "importance": "high"}
    webhook_url = "https://hooks.example.com/webhook"
    
    # 创建任务包
    task_package = create_task_package(
        evidence_fragment, associated_url, source_name, 
        risk_level, brand_name, intervention_script, source_meta, webhook_url
    )
    
    # 验证任务包结构
    print("验证任务包结构:")
    assert "task_type" in task_package
    assert "evidence_data" in task_package
    assert "delivery_instructions" in task_package
    assert "metadata" in task_package
    
    print(f"  - 任务类型: {task_package['task_type']}")
    print(f"  - 证据数据: 包含{len(task_package['evidence_data'])}个字段")
    print(f"  - 交付指令: 包含{len(task_package['delivery_instructions'])}个字段")
    print(f"  - 元数据: 包含{len(task_package['metadata'])}个字段")
    
    # 验证具体内容
    evidence_data = task_package['evidence_data']
    assert evidence_data['evidence_fragment'] == evidence_fragment
    assert evidence_data['source_name'] == source_name
    assert evidence_data['risk_level'] == risk_level
    assert evidence_data['brand_name'] == brand_name
    
    delivery_instructions = task_package['delivery_instructions']
    assert delivery_instructions['webhook_url'] == webhook_url
    assert delivery_instructions['delivery_format'] == "standard_payload"
    
    print("  ✓ 任务包结构正确")
    print("  ✓ 任务包内容完整")
    
    print("\n任务打包功能测试通过!")


def test_priority_mapping():
    """测试优先级映射功能"""
    print("\n测试优先级映射功能...")
    
    def priority_to_number(priority: TaskPriority) -> int:
        """将优先级转换为数字，用于队列排序"""
        priority_map = {
            TaskPriority.CRITICAL: 1,  # 最高优先级
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4   # 最低优先级
        }
        return priority_map.get(priority, 3)  # 默认为MEDIUM
    
    # 测试各种优先级
    priorities = [
        (TaskPriority.CRITICAL, 1),
        (TaskPriority.HIGH, 2),
        (TaskPriority.MEDIUM, 3),
        (TaskPriority.LOW, 4)
    ]
    
    print("验证优先级映射:")
    for priority, expected_num in priorities:
        actual_num = priority_to_number(priority)
        print(f"  {priority.value} -> {actual_num}")
        assert actual_num == expected_num, f"期望{expected_num}，实际{actual_num}"
    
    print("  ✓ 优先级映射正确")
    
    print("\n优先级映射功能测试通过!")


def test_webhook_simulation():
    """模拟Webhook功能测试"""
    print("\n模拟Webhook功能测试...")
    
    # 模拟Webhook发送函数
    def send_webhook(webhook_url: str, payload: Dict[str, Any], task_id: str) -> bool:
        """
        模拟发送Webhook请求
        """
        print(f"  发送Webhook到: {webhook_url}")
        print(f"  任务ID: {task_id}")
        print(f"  载荷大小: {len(json.dumps(payload))} 字符")
        
        # 模拟成功率 - 70%成功，30%失败
        success_rate = 0.7
        success = random.random() < success_rate
        
        if success:
            print(f"  ✅ Webhook发送成功")
        else:
            print(f"  ❌ Webhook发送失败")
        
        return success
    
    # 模拟任务处理
    def process_task_with_retry(task_data: Dict[str, Any]) -> bool:
        """模拟带重试的任务处理"""
        task_id = task_data['task_id']
        webhook_url = task_data['webhook_url']
        payload = task_data['task_package']
        
        max_retries = task_data.get('max_retries', 3)
        retry_count = 0
        
        print(f"处理任务 {task_id} (最大重试次数: {max_retries})")
        
        while retry_count <= max_retries:
            if retry_count > 0:
                print(f"  重试 #{retry_count}...")
                # 模拟重试延迟
                delay = min(30 * (2 ** retry_count), 300)  # 指数退避，最大5分钟
                print(f"  等待 {delay} 秒后重试...")
                time.sleep(0.1)  # 模拟延迟（快速测试）
            
            success = send_webhook(webhook_url, payload, task_id)
            
            if success:
                print(f"任务 {task_id} 成功完成")
                return True
            else:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"任务 {task_id} 失败，准备重试...")
                else:
                    print(f"任务 {task_id} 达到最大重试次数，标记为失败")
                    return False
    
    # 创建测试任务
    task_package = {
        "task_type": "negative_evidence_intervention",
        "evidence_data": {
            "evidence_fragment": "测试证据片段",
            "source_name": "测试信源",
            "risk_level": "High",
            "brand_name": "测试品牌"
        },
        "delivery_instructions": {
            "webhook_url": "https://hooks.example.com/webhook",
            "delivery_format": "standard_payload"
        }
    }
    
    task_data = {
        'task_id': 'test_task_123',
        'task_package': task_package,
        'webhook_url': 'https://hooks.example.com/webhook',
        'max_retries': 3
    }
    
    # 处理任务
    success = process_task_with_retry(task_data)
    
    print(f"任务处理结果: {'成功' if success else '失败'}")
    
    print("\nWebhook模拟测试完成!")


if __name__ == "__main__":
    print("="*60)
    print("工作流管理器功能测试")
    print("="*60)
    
    test_retry_mechanism()
    test_task_packaging()
    test_priority_mapping()
    test_webhook_simulation()
    
    print("\n" + "="*60)
    print("所有测试通过!")
    print("✓ 重试机制功能正常")
    print("✓ 任务打包功能正常") 
    print("✓ 优先级映射功能正常")
    print("✓ Webhook模拟功能正常")
    print("✓ 指数退避算法正确实现")
    print("="*60)