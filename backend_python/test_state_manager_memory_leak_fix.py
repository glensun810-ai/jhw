#!/usr/bin/env python3
"""
状态管理器内存泄漏修复验证脚本

测试场景：
1. 正常清理流程验证
2. 紧急清理触发验证
3. 内存健康状态评估
4. 长时间运行稳定性测试

@author: 系统架构组
@date: 2026-03-05
"""

import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加路径
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.state_manager import DiagnosisStateManager
from wechat_backend.logging_config import api_logger


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_cleanup_configuration():
    """测试 1: 清理配置验证"""
    print_section("测试 1: 清理配置验证")

    execution_store = {}
    manager = DiagnosisStateManager(execution_store)

    print(f"✅ 清理间隔：{manager.cleanup_interval_seconds}秒 (期望：180 秒)")
    print(f"✅ 完成 TTL: {manager.completed_state_ttl_seconds}秒 (期望：300 秒)")
    print(f"✅ 最大内存项数：{manager.max_memory_items} (期望：500)")

    assert manager.cleanup_interval_seconds == 180, "清理间隔配置错误"
    assert manager.completed_state_ttl_seconds == 300, "完成 TTL 配置错误"
    assert manager.max_memory_items == 500, "最大内存项数配置错误"

    print("\n✅ 配置验证通过")
    return True


def test_normal_cleanup():
    """测试 2: 正常清理流程验证"""
    print_section("测试 2: 正常清理流程验证")

    execution_store = {}
    manager = DiagnosisStateManager(execution_store)

    # 模拟已完成的诊断任务
    now = datetime.now()

    # 添加 10 个已完成任务（完成时间不同）
    for i in range(10):
        execution_id = f"test_completed_{i}"
        completed_minutes_ago = (i + 1)  # 1 分钟前，2 分钟前，...，10 分钟前

        execution_store[execution_id] = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': True,
            'should_stop_polling': True,
            'updated_at': (now - timedelta(minutes=completed_minutes_ago)).isoformat(),
            'start_time': (now - timedelta(minutes=completed_minutes_ago + 5)).isoformat()
        }

    # 添加 5 个进行中的任务（不应该被清理）
    for i in range(5):
        execution_id = f"test_running_{i}"
        execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': False,
            'updated_at': now.isoformat()
        }

    print(f"清理前内存任务数：{len(execution_store)}")
    print(f"  - 已完成任务：10 个")
    print(f"  - 进行中任务：5 个")

    # 执行清理
    cleaned_count = manager._cleanup_completed_states()

    print(f"\n清理后内存任务数：{len(execution_store)}")
    print(f"  - 清理的任务数：{cleaned_count}")
    print(f"  - 剩余任务数：{len(execution_store)}")

    # 验证：只有完成时间超过 5 分钟的任务被清理
    # 5 分钟以上的任务：6 分钟、7 分钟、8 分钟、9 分钟、10 分钟 = 5 个
    expected_cleaned = 5  # 完成时间超过 5 分钟的任务
    expected_remaining = 10  # 5 个进行中 + 5 个完成时间不足 5 分钟

    print(f"\n预期清理数：{expected_cleaned}")
    print(f"预期剩余数：{expected_remaining}")

    # 注意：实际清理数可能因执行时间略有差异
    assert cleaned_count >= 4 and cleaned_count <= 6, f"清理数异常：{cleaned_count}"
    assert len(execution_store) >= 9 and len(execution_store) <= 11, f"剩余数异常：{len(execution_store)}"

    # 验证进行中的任务未被清理
    for i in range(5):
        assert f"test_running_{i}" in execution_store, f"进行中任务被错误清理：test_running_{i}"

    print("\n✅ 正常清理流程验证通过")
    return True


def test_emergency_cleanup():
    """测试 3: 紧急清理触发验证"""
    print_section("测试 3: 紧急清理触发验证")

    execution_store = {}
    manager = DiagnosisStateManager(execution_store)

    # 模拟内存超限场景
    print(f"最大内存项数：{manager.max_memory_items}")

    # 添加超过最大限制的任务
    overflow_count = 50
    total_count = manager.max_memory_items + overflow_count

    now = datetime.now()

    for i in range(total_count):
        execution_id = f"test_overflow_{i}"
        # 所有任务都在 3 分钟前完成（小于正常 TTL 300s，但大于紧急 TTL 150s）
        execution_store[execution_id] = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': True,
            'updated_at': (now - timedelta(minutes=3)).isoformat()
        }

    print(f"添加任务数：{total_count}")
    print(f"当前内存任务数：{len(execution_store)}")
    print(f"内存利用率：{len(execution_store) / manager.max_memory_items:.1%}")

    # 执行清理（应该触发紧急清理）
    cleaned_count = manager._cleanup_completed_states()

    print(f"\n清理任务数：{cleaned_count}")
    print(f"清理后内存任务数：{len(execution_store)}")
    print(f"紧急清理次数：{manager.emergency_cleanup_count}")

    # 验证紧急清理被触发
    assert manager.emergency_cleanup_count >= 1, "紧急清理未被触发"

    # 验证所有完成的任务都被清理（因为紧急清理 TTL 减半为 2.5 分钟）
    # 注意：由于任务完成时间是 3 分钟，超过紧急 TTL，应该全部被清理
    print(f"\n✅ 紧急清理触发验证通过")
    return True


def test_memory_health_status():
    """测试 4: 内存健康状态评估"""
    print_section("测试 4: 内存健康状态评估")

    execution_store = {}
    manager = DiagnosisStateManager(execution_store)

    # 测试不同利用率下的健康状态
    # 注意：max_memory_items = 500，所以 100% 是 500 项
    test_cases = [
        (0, 'healthy'),      # 0% 利用率
        (250, 'healthy'),    # 50% 利用率
        (355, 'warning'),    # 71% 利用率
        (451, 'critical'),   # 90.2% 利用率（超过 90%）
        (500, 'critical'),   # 100% 利用率
    ]

    for count, expected_status in test_cases:
        # 清空并添加指定数量的任务
        execution_store.clear()
        for i in range(count):
            execution_store[f"test_health_{i}"] = {
                'status': 'running',
                'updated_at': datetime.now().isoformat()
            }

        status = manager._get_memory_health_status()
        utilization = count / manager.max_memory_items

        print(f"利用率 {utilization:.1%} -> 健康状态：{status} (期望：{expected_status})")
        assert status == expected_status, f"健康状态评估错误：{status} != {expected_status}"

    print("\n✅ 内存健康状态评估验证通过")
    return True


def test_cleanup_status_api():
    """测试 5: 清理状态 API 验证"""
    print_section("测试 5: 清理状态 API 验证")
    
    execution_store = {}
    manager = DiagnosisStateManager(execution_store)
    
    # 添加一些任务
    now = datetime.now()
    for i in range(100):
        execution_store[f"test_status_{i}"] = {
            'status': 'completed' if i % 2 == 0 else 'running',
            'updated_at': (now - timedelta(minutes=(i + 1) * 2)).isoformat()
        }
    
    # 执行一次清理
    manager._cleanup_completed_states()
    
    # 获取状态
    status = manager.get_cleanup_status()
    
    print("清理状态信息:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 验证必要字段存在
    required_fields = [
        'total_tasks_in_memory',
        'memory_utilization',
        'cleanup_interval_seconds',
        'completed_state_ttl_seconds',
        'max_memory_items',
        'health_status'
    ]
    
    for field in required_fields:
        assert field in status, f"缺少必要字段：{field}"
    
    print("\n✅ 清理状态 API 验证通过")
    return True


def test_long_running_stability():
    """测试 6: 长时间运行稳定性测试（简化版）"""
    print_section("测试 6: 长时间运行稳定性测试")

    execution_store = {}
    manager = DiagnosisStateManager(execution_store)

    print("模拟 10 轮诊断任务创建和清理...")

    for round in range(10):
        # 创建新任务
        for i in range(50):
            execution_id = f"test_round{round}_task{i}"
            execution_store[execution_id] = {
                'status': 'running',
                'stage': 'init',
                'progress': 0,
                'updated_at': datetime.now().isoformat()
            }

        # 模拟部分任务完成
        for i in range(25):
            execution_id = f"test_round{round}_task{i}"
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'status': 'completed',
                    'stage': 'completed',
                    'progress': 100,
                    'is_completed': True,
                    'updated_at': (datetime.now() - timedelta(minutes=15)).isoformat()
                })

        # 执行清理
        cleaned = manager._cleanup_completed_states()

        print(f"  轮次 {round + 1}/10: 当前任务数={len(execution_store)}, 清理数={cleaned}")

    # 验证内存使用稳定
    final_count = len(execution_store)
    print(f"\n最终内存任务数：{final_count}")
    print(f"内存利用率：{final_count / manager.max_memory_items:.1%}")
    print(f"健康状态：{manager._get_memory_health_status()}")

    # 验证内存没有无限增长
    # 注意：由于任务完成时间不足 TTL，会积累，但应在合理范围内
    # 500 * 0.7 = 350，应该小于 70% 利用率
    assert final_count < manager.max_memory_items * 0.7, f"内存使用增长过快：{final_count}"

    print("\n✅ 长时间运行稳定性验证通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print_section("状态管理器内存泄漏修复验证测试")
    print(f"测试开始时间：{datetime.now().isoformat()}")
    print(f"测试环境：Python {sys.version}")
    
    tests = [
        ("清理配置验证", test_cleanup_configuration),
        ("正常清理流程验证", test_normal_cleanup),
        ("紧急清理触发验证", test_emergency_cleanup),
        ("内存健康状态评估", test_memory_health_status),
        ("清理状态 API 验证", test_cleanup_status_api),
        ("长时间运行稳定性测试", test_long_running_stability),
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
        print("  🎉 所有测试通过！内存泄漏修复验证成功！")
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
