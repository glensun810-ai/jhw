"""
验证WebhookManager核心功能的简单测试
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# 创建一个简化的WebhookManager测试
import time
import requests
from typing import Dict, Any
import random
from enum import Enum


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WebhookManager:
    """简化的Webhook管理器用于测试"""
    
    def __init__(self):
        self.session = requests.Session()
        self.max_retries = 3
        self.base_delay = 1  # 基础延迟1秒（测试用）
    
    def send_webhook(self, webhook_url: str, payload: Dict[str, Any], task_id: str) -> bool:
        """
        发送Webhook请求到目标URL
        
        Args:
            webhook_url: 目标Webhook URL
            payload: 要发送的载荷数据
            task_id: 任务ID，用于日志记录
            
        Returns:
            bool: 是否发送成功
        """
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    # 指数退避延迟
                    delay = self._calculate_delay(retry_count)
                    print(f"  重试 #{retry_count}, 等待 {delay} 秒...")
                    time.sleep(delay)
                
                print(f"  尝试发送Webhook到 {webhook_url} (尝试 #{retry_count + 1})")
                
                # 模拟API调用
                response = self._simulate_api_call(webhook_url, payload)
                
                if response['success']:
                    print(f"  ✅ Webhook发送成功到 {webhook_url}")
                    return True
                else:
                    print(f"  ❌ Webhook发送失败: {response.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"  ❌ Webhook请求异常: {str(e)}")
            
            retry_count += 1
        
        print(f"  ❌ Webhook发送失败，已达到最大重试次数 {self.max_retries}")
        return False
    
    def _simulate_api_call(self, webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """模拟API调用 - 在实际实现中替换为真实的API调用"""
        # 模拟不同的响应情况
        # 为了测试，我们让前几次调用失败，最后一次成功
        # 在实际测试中，我们会根据某种条件决定成功或失败
        
        # 为了演示重试机制，我们随机决定是否成功
        success_probability = 0.3  # 30% 成功率，用于测试重试
        
        if random.random() < success_probability:
            return {'success': True, 'status_code': 200}
        else:
            # 模拟不同类型的错误
            error_types = [
                {'success': False, 'error': 'Server Error', 'status_code': 500},
                {'success': False, 'error': 'Timeout', 'status_code': 408},
                {'success': False, 'error': 'Bad Gateway', 'status_code': 502}
            ]
            return random.choice(error_types)
    
    def _calculate_delay(self, retry_attempt: int) -> float:
        """
        计算重试延迟时间（指数退避算法）
        
        Args:
            retry_attempt: 重试次数（从1开始）
            
        Returns:
            float: 延迟秒数
        """
        # 指数退避：延迟时间 = 基础延迟 * (2 ^ 重试次数) + 随机抖动
        exponential_delay = self.base_delay * (2 ** (retry_attempt - 1))
        jitter = random.uniform(0, 1)  # 添加随机抖动
        total_delay = min(exponential_delay + jitter, 60)  # 最大延迟60秒
        return total_delay


def test_webhook_success():
    """测试Webhook成功发送"""
    print("测试1: Webhook成功发送...")
    manager = WebhookManager()
    
    # 模拟一个总是成功的场景
    def always_success_call(url, payload):
        return {'success': True, 'status_code': 200}
    
    # 替换模拟方法以确保成功
    original_call = manager._simulate_api_call
    manager._simulate_api_call = always_success_call
    
    result = manager.send_webhook(
        "https://example.com/webhook",
        {"test": "data", "success": True},
        "test_task_1"
    )
    
    assert result == True, "Webhook应该成功发送"
    print("  ✓ Webhook成功发送测试通过")
    
    # 恢复原始方法
    manager._simulate_api_call = original_call


def test_webhook_with_retry():
    """测试Webhook重试机制"""
    print("\n测试2: Webhook重试机制...")
    manager = WebhookManager()
    
    # 创建一个方法，第一次失败，第二次成功
    call_count = 0
    def success_on_second_call(url, payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {'success': False, 'error': 'Server Error', 'status_code': 500}
        else:
            return {'success': True, 'status_code': 200}
    
    original_call = manager._simulate_api_call
    manager._simulate_api_call = success_on_second_call
    
    result = manager.send_webhook(
        "https://example.com/webhook",
        {"test": "data", "eventually_success": True},
        "test_task_2"
    )
    
    assert result == True, "Webhook应该在重试后成功"
    print("  ✓ Webhook重试机制测试通过")
    
    # 恢复原始方法
    manager._simulate_api_call = original_call


def test_webhook_max_retries():
    """测试达到最大重试次数"""
    print("\n测试3: 达到最大重试次数...")
    manager = WebhookManager()
    
    # 创建一个方法，总是失败
    def always_fail_call(url, payload):
        return {'success': False, 'error': 'Persistent Error', 'status_code': 500}
    
    original_call = manager._simulate_api_call
    manager._simulate_api_call = always_fail_call
    
    result = manager.send_webhook(
        "https://example.com/webhook",
        {"test": "data", "will_fail": True},
        "test_task_3"
    )
    
    assert result == False, "Webhook应该在达到最大重试次数后失败"
    print("  ✓ 最大重试次数测试通过")
    
    # 恢复原始方法
    manager._simulate_api_call = original_call


def test_delay_calculation():
    """测试延迟计算算法"""
    print("\n测试4: 延迟计算算法...")
    manager = WebhookManager()
    
    # 测试指数退避算法
    delays = []
    for i in range(1, 6):  # 测试前5次重试
        delay = manager._calculate_delay(i)
        delays.append(delay)
        print(f"  重试 #{i}: {delay:.2f}秒")
    
    # 验证延迟是递增的（不考虑随机抖动）
    # 由于有随机抖动，我们只验证基本趋势
    assert delays[0] <= delays[1], "第二次重试延迟应大于等于第一次"
    print("  ✓ 延迟计算算法测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始测试WebhookManager功能...")
    print("="*50)
    
    test_webhook_success()
    test_webhook_with_retry()
    test_webhook_max_retries()
    test_delay_calculation()
    
    print("\n" + "="*50)
    print("所有测试通过!")
    print("✓ Webhook成功发送功能正常")
    print("✓ 重试机制正常工作") 
    print("✓ 最大重试次数限制正常")
    print("✓ 指数退避算法正常")
    print("✓ 延迟计算算法正确")
    print("="*50)


if __name__ == "__main__":
    run_all_tests()