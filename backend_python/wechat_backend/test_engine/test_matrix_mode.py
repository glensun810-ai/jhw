#!/usr/bin/env python3
"""
测试矩阵模式执行 (N 个问题*M 个平台)
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_engine.scheduler import TestScheduler, ExecutionStrategy, TestTask

def test_matrix_mode():
    """测试矩阵模式执行"""
    print("=" * 80)
    print("测试矩阵模式执行 (N 个问题*M 个平台)")
    print("=" * 80)
    
    # 创建测试任务 (3 个问题)
    test_tasks = [
        TestTask(
            id=f"matrix_test_q{i}",
            brand_name="测试品牌",
            ai_model="豆包",  # 初始模型会被覆盖
            question=f"测试问题 {i}: 请介绍一下数字转型咨询服务",
            priority=1,
            timeout=30,
            max_retries=1,  # 测试时减少重试次数
            metadata={'test_mode': True}
        )
        for i in range(1, 4)  # 3 个问题
    ]
    
    print(f"\n创建 {len(test_tasks)} 个测试问题")
    for task in test_tasks:
        print(f"  - {task.id}: {task.question[:50]}...")
    
    # 创建调度器 (使用矩阵模式)
    print("\n创建 TestScheduler (MATRIX 模式)...")
    scheduler = TestScheduler(max_workers=1, strategy=ExecutionStrategy.MATRIX)
    
    # 执行测试
    print("\n开始矩阵执行...")
    print("-" * 80)
    
    results = []
    def callback(task, result):
        results.append({
            'task': task,
            'result': result
        })
        status = "✓" if result.get('success') else "✗"
        platform = task.ai_model
        question = task.question[:40] + "..." if len(task.question) > 40 else task.question
        print(f"  {status} {platform}: {question} (success={result.get('success')})")
    
    stats = scheduler.schedule_tests(test_tasks, callback=callback)
    
    # 输出统计
    print("\n" + "=" * 80)
    print("执行统计")
    print("=" * 80)
    print(f"总任务数：{stats['total_tasks']}")
    print(f"成功：{stats['completed_tasks']}")
    print(f"失败：{stats['failed_tasks']}")
    print(f"执行时间：{stats['execution_time']:.2f}秒")
    print(f"策略：{stats['strategy']}")
    
    # 验证 N*M 对应关系
    print("\n" + "=" * 80)
    print("N*M 对应关系验证")
    print("=" * 80)
    
    # 按原始任务 ID 分组
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in results:
        task = r['task']
        orig_id = task.metadata.get('original_task_id', task.id) if task.metadata else task.id
        grouped[orig_id].append({
            'platform': task.ai_model,
            'question_index': task.metadata.get('question_index') if task.metadata else None,
            'platform_index': task.metadata.get('platform_index') if task.metadata else None,
            'success': r['result'].get('success')
        })
    
    for orig_id, items in grouped.items():
        print(f"\n【{orig_id}】")
        platforms = set(item['platform'] for item in items)
        print(f"  问题：{items[0]['question_index'] if items[0]['question_index'] else 'N/A'}")
        print(f"  平台数：{len(platforms)}")
        for item in items:
            status = "✓" if item['success'] else "✗"
            print(f"    {status} {item['platform']} (platform_index={item['platform_index']})")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    return stats

if __name__ == '__main__':
    test_matrix_mode()
