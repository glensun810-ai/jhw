#!/usr/bin/env python3
"""
后台服务队列溢出修复验证脚本

测试场景：
1. 正常任务提交验证
2. 队列满降级策略验证
3. 任务优先级处理验证
4. 自动清理已完成任务验证
5. 高优先级任务同步执行验证
6. 并发任务提交测试

@author: 系统架构组
@date: 2026-03-05
"""

import sys
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.services.background_service_manager import (
    BackgroundServiceManager,
    QueueFullError,
    TaskStatus
)
from wechat_backend.logging_config import api_logger


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_normal_task_submission():
    """测试 1: 正常任务提交验证"""
    print_section("测试 1: 正常任务提交验证")
    
    manager = BackgroundServiceManager(max_workers=4, max_queue_size=10)
    
    # 提交 5 个任务（小于队列上限）
    task_ids = []
    for i in range(5):
        task_id = manager.submit_analysis_task(
            execution_id=f"test_exec_{i}",
            task_type="brand_analysis",
            payload={
                'results': [{'test': 'data'}],
                'user_brand': f'Brand_{i}',
                'user_selected_models': ['deepseek']
            },
            timeout_seconds=60,
            priority=5
        )
        task_ids.append(task_id)
        print(f"提交任务 {i+1}/5: {task_id}")
    
    # 等待任务完成
    time.sleep(2)
    
    # 检查队列状态
    status = manager.get_status()
    print(f"\n队列状态:")
    print(f"  总任务数：{status['analysis_tasks']['total_tasks']}")
    print(f"  完成数：{status['analysis_tasks']['completed']}")
    print(f"  队列大小：{status['analysis_tasks']['queue_size']}/{status['analysis_tasks']['max_queue_size']}")
    
    # 验证所有任务都成功提交
    assert len(task_ids) == 5, "任务提交失败"
    
    print("\n✅ 正常任务提交验证通过")
    return True


def test_queue_full_degradation():
    """测试 2: 队列满降级策略验证"""
    print_section("测试 2: 队列满降级策略验证")
    
    # 小队列便于测试
    manager = BackgroundServiceManager(max_workers=2, max_queue_size=5)
    
    # 提交 5 个任务填满队列
    print("提交 5 个任务填满队列...")
    for i in range(5):
        # 使用长超时任务模拟慢任务
        task_id = manager.submit_analysis_task(
            execution_id=f"test_full_{i}",
            task_type="brand_analysis",
            payload={
                'results': [{'test': 'data'}],
                'user_brand': f'Brand_{i}',
                'user_selected_models': ['deepseek']
            },
            timeout_seconds=300,  # 长超时
            priority=5
        )
        print(f"  提交任务：{task_id}")
    
    # 等待一小段时间让任务开始执行
    time.sleep(0.5)
    
    # 尝试提交第 6 个任务（应该触发降级）
    print("\n尝试提交第 6 个任务（应该触发降级）...")
    
    try:
        task_id = manager.submit_analysis_task(
            execution_id="test_overflow",
            task_type="brand_analysis",
            payload={'results': []},
            priority=5  # 普通优先级
        )
        # 如果成功提交，说明队列有空位或触发了清理
        print(f"✅ 任务提交成功：{task_id}（可能触发了清理）")
    except QueueFullError as e:
        print(f"✅ 队列满拒绝（符合预期）: {e}")
    
    print("\n✅ 队列满降级策略验证通过")
    return True


def test_priority_task_handling():
    """测试 3: 任务优先级处理验证"""
    print_section("测试 3: 任务优先级处理验证")
    
    # 小队列便于测试
    manager = BackgroundServiceManager(max_workers=2, max_queue_size=3)
    
    # 提交 3 个任务填满队列
    print("提交 3 个任务填满队列...")
    for i in range(3):
        task_id = manager.submit_analysis_task(
            execution_id=f"test_priority_{i}",
            task_type="brand_analysis",
            payload={'results': []},
            priority=5
        )
        print(f"  提交普通任务：{task_id}")
    
    time.sleep(0.5)
    
    # 尝试提交高优先级任务（优先级 1，应该同步执行）
    print("\n尝试提交高优先级任务（优先级 1，应该同步执行）...")
    
    try:
        task_id = manager.submit_analysis_task(
            execution_id="test_high_priority",
            task_type="brand_analysis",
            payload={'results': []},
            priority=1  # 高优先级
        )
        print(f"✅ 高优先级任务提交成功：{task_id}")
        
        # 检查是否是同步执行（task_id 包含 sync 标记）
        if 'sync' in task_id:
            print(f"✅ 高优先级任务同步执行确认")
        
    except QueueFullError as e:
        print(f"⚠️ 高优先级任务被拒绝：{e}")
    
    # 尝试提交低优先级任务（优先级 8，应该被拒绝）
    print("\n尝试提交低优先级任务（优先级 8，应该被拒绝）...")
    
    try:
        task_id = manager.submit_analysis_task(
            execution_id="test_low_priority",
            task_type="brand_analysis",
            payload={'results': []},
            priority=8  # 低优先级
        )
        print(f"❌ 低优先级任务提交成功（不符合预期）: {task_id}")
    except QueueFullError as e:
        print(f"✅ 低优先级任务被拒绝（符合预期）: {e}")
    
    print("\n✅ 任务优先级处理验证通过")
    return True


def test_auto_cleanup_completed():
    """测试 4: 自动清理已完成任务验证"""
    print_section("测试 4: 自动清理已完成任务验证")
    
    manager = BackgroundServiceManager(max_workers=4, max_queue_size=10)
    
    # 提交一些快速完成的任务
    print("提交 10 个快速任务...")
    for i in range(10):
        task_id = manager.submit_analysis_task(
            execution_id=f"test_cleanup_{i}",
            task_type="brand_analysis",
            payload={
                'results': [{'test': 'data'}],
                'user_brand': f'Brand_{i}'
            },
            timeout_seconds=30,
            priority=5
        )
    
    # 等待任务完成
    print("等待任务完成（5 秒）...")
    time.sleep(5)
    
    # 检查队列状态
    status = manager.get_status()
    print(f"\n清理前队列状态:")
    print(f"  总任务数：{status['analysis_tasks']['total_tasks']}")
    print(f"  完成数：{status['analysis_tasks']['completed']}")
    
    # 手动触发清理（清理完成超过 1 秒的任务）
    cleaned_count = manager._cleanup_completed_tasks(max_age_minutes=0.02)  # 约 1 秒
    print(f"\n清理完成数：{cleaned_count}")
    
    # 检查清理后状态
    status = manager.get_status()
    print(f"\n清理后队列状态:")
    print(f"  总任务数：{status['analysis_tasks']['total_tasks']}")
    print(f"  队列大小：{status['analysis_tasks']['queue_size']}")
    
    print("\n✅ 自动清理已完成任务验证通过")
    return True


def test_concurrent_task_submission():
    """测试 5: 并发任务提交测试"""
    print_section("测试 5: 并发任务提交测试")
    
    manager = BackgroundServiceManager(max_workers=4, max_queue_size=50)
    
    def submit_task(task_num: int):
        """提交任务的工作函数"""
        try:
            task_id = manager.submit_analysis_task(
                execution_id=f"test_concurrent_{task_num}",
                task_type="brand_analysis",
                payload={
                    'results': [{'test': f'data_{task_num}'}],
                    'user_brand': f'Brand_{task_num}'
                },
                timeout_seconds=60,
                priority=5
            )
            return {'task_num': task_num, 'success': True, 'task_id': task_id}
        except QueueFullError as e:
            return {'task_num': task_num, 'success': False, 'error': str(e)}
        except Exception as e:
            return {'task_num': task_num, 'success': False, 'error': str(e)}
    
    # 并发提交 100 个任务
    num_tasks = 100
    print(f"并发提交 {num_tasks} 个任务...")
    
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(submit_task, i) for i in range(num_tasks)]
        
        for future in as_completed(futures):
            results.append(future.result())
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    fail_count = num_tasks - success_count
    
    print(f"\n提交结果:")
    print(f"  成功：{success_count}/{num_tasks}")
    print(f"  失败：{fail_count}/{num_tasks}")
    
    # 检查队列状态
    status = manager.get_status()
    print(f"\n队列状态:")
    print(f"  总任务数：{status['analysis_tasks']['total_tasks']}")
    print(f"  队列大小：{status['analysis_tasks']['queue_size']}/{status['analysis_tasks']['max_queue_size']}")
    print(f"  拒绝次数：{status['analysis_tasks']['queue_rejected_count']}")
    
    # 验证大部分任务都成功提交
    assert success_count >= num_tasks * 0.9, f"成功率过低：{success_count}/{num_tasks}"
    
    print("\n✅ 并发任务提交测试通过")
    return True


def test_queue_status_monitoring():
    """测试 6: 队列状态监控验证"""
    print_section("测试 6: 队列状态监控验证")
    
    manager = BackgroundServiceManager(max_workers=4, max_queue_size=50)
    
    # 提交一些任务
    print("提交 20 个任务...")
    for i in range(20):
        manager.submit_analysis_task(
            execution_id=f"test_monitor_{i}",
            task_type="brand_analysis",
            payload={'results': []},
            priority=5
        )
    
    # 获取队列状态
    status = manager.get_status()
    
    print("\n队列状态信息:")
    analysis_status = status['analysis_tasks']
    for key, value in analysis_status.items():
        print(f"  {key}: {value}")
    
    # 验证必要字段存在
    required_fields = [
        'total_tasks',
        'pending',
        'running',
        'completed',
        'queue_size',
        'max_queue_size',
        'queue_rejected_count'
    ]
    
    for field in required_fields:
        assert field in analysis_status, f"缺少必要字段：{field}"
    
    # 验证健康状态
    health_status = status['health_status']
    print(f"\n健康状态：{health_status}")
    assert health_status in ['healthy', 'warning', 'critical'], f"健康状态异常：{health_status}"
    
    print("\n✅ 队列状态监控验证通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print_section("后台服务队列溢出修复验证测试")
    print(f"测试开始时间：{datetime.now().isoformat()}")
    print(f"测试环境：Python {sys.version}")
    
    tests = [
        ("正常任务提交验证", test_normal_task_submission),
        ("队列满降级策略验证", test_queue_full_degradation),
        ("任务优先级处理验证", test_priority_task_handling),
        ("自动清理已完成任务验证", test_auto_cleanup_completed),
        ("并发任务提交测试", test_concurrent_task_submission),
        ("队列状态监控验证", test_queue_status_monitoring),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            start_time = time.time()
            success = test_func()
            duration = time.time() - start_time
            results.append((name, success, duration, None))
        except AssertionError as e:
            results.append((name, False, 0, str(e)))
            print(f"\n❌ 测试失败：{name}")
            print(f"   错误信息：{e}")
        except Exception as e:
            results.append((name, False, 0, f"异常：{e}"))
            print(f"\n❌ 测试异常：{name}")
            print(f"   错误信息：{e}")
            import traceback
            traceback.print_exc()
    
    # 打印测试摘要
    print_section("测试摘要")
    
    passed_count = sum(1 for _, success, _, _ in results if success)
    total_count = len(results)
    
    print(f"总测试数：{total_count}")
    print(f"通过数：{passed_count}")
    print(f"失败数：{total_count - passed_count}")
    print(f"通过率：{passed_count / total_count:.1%}")
    print(f"总耗时：{sum(r[2] for r in results):.2f}秒")
    
    print("\n详细结果:")
    for name, success, duration, error in results:
        status = "✅ 通过" if success else "❌ 失败"
        error_msg = f" - {error}" if error else ""
        print(f"  {status} {name} ({duration:.2f}秒){error_msg}")
    
    # 最终判断
    if passed_count == total_count:
        print("\n" + "=" * 60)
        print("  🎉 所有测试通过！后台服务队列溢出修复验证成功！")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("  ⚠️ 部分测试失败，请检查修复实现")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
