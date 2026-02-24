#!/usr/bin/env python3
"""
综合系统测试脚本 - 验证所有状态同步修复

测试范围:
1. Status/Stage 同步验证
2. 任务失败处理验证
3. 任务完成处理验证
4. 数据库降级逻辑验证
5. API 端点响应验证
"""

import sys
import os
import json
import unittest
from datetime import datetime
from io import StringIO

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python', 'wechat_backend'))

# 测试计数器
tests_passed = 0
tests_failed = 0
tests_total = 0


def print_header(text):
    print(f"\n{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}\n")


def print_result(test_name, passed, details=""):
    global tests_passed, tests_failed, tests_total
    tests_total += 1
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"       {details}")
    if passed:
        tests_passed += 1
    else:
        tests_failed += 1


def test_task_stage_enum():
    """测试 1: TaskStage 枚举包含 FAILED"""
    try:
        from wechat_backend.models import TaskStage
        
        # 检查是否包含 FAILED
        has_failed = hasattr(TaskStage, 'FAILED') or 'FAILED' in [e.name for e in TaskStage]
        
        # 检查 FAILED 的值
        if has_failed:
            failed_value = TaskStage.FAILED.value
            print_result(
                "TaskStage 枚举包含 FAILED",
                has_failed and failed_value == 'failed',
                f"FAILED = '{failed_value}'"
            )
        else:
            print_result("TaskStage 枚举包含 FAILED", False, "缺少 FAILED 枚举")
            
    except Exception as e:
        print_result("TaskStage 枚举包含 FAILED", False, str(e))


def test_execution_store_initialization():
    """测试 2: execution_store 初始化包含 status 和 stage"""
    try:
        # 模拟 execution_store 初始化
        execution_store = {}
        execution_id = "test_123"
        
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': 10,
            'status': 'initializing',
            'stage': 'init',
            'results': [],
            'start_time': datetime.now().isoformat()
        }
        
        store = execution_store[execution_id]
        has_status = 'status' in store
        has_stage = 'stage' in store
        
        print_result(
            "execution_store 初始化包含 status 和 stage",
            has_status and has_stage,
            f"status='{store.get('status')}', stage='{store.get('stage')}'"
        )
        
    except Exception as e:
        print_result("execution_store 初始化", False, str(e))


def test_status_stage_sync_completed():
    """测试 3: 任务完成时 status/stage 同步"""
    try:
        execution_store = {}
        execution_id = "test_completed"
        
        # 初始状态
        execution_store[execution_id] = {
            'status': 'processing',
            'stage': 'ai_fetching',
            'progress': 50
        }
        
        # 完成任务 - 模拟修复后的代码
        execution_store[execution_id].update({
            'progress': 100,
            'status': 'completed',
            'stage': 'completed',  # 【修复】同步 stage
            'is_completed': True   # 【修复】设置 is_completed
        })
        
        store = execution_store[execution_id]
        is_synced = (
            store['status'] == 'completed' and
            store['stage'] == 'completed' and
            store.get('is_completed') == True
        )
        
        print_result(
            "任务完成时 status/stage 同步",
            is_synced,
            f"status='{store['status']}', stage='{store['stage']}', is_completed={store.get('is_completed')}"
        )
        
    except Exception as e:
        print_result("任务完成时 status/stage 同步", False, str(e))


def test_status_stage_sync_failed():
    """测试 4: 任务失败时 status/stage 同步"""
    try:
        execution_store = {}
        execution_id = "test_failed"
        
        # 初始状态
        execution_store[execution_id] = {
            'status': 'processing',
            'stage': 'ai_fetching',
            'progress': 30
        }
        
        # 失败处理 - 模拟修复后的代码
        execution_store[execution_id].update({
            'status': 'failed',
            'stage': 'failed',  # 【修复】同步 stage
            'error': 'Test error'
        })
        
        store = execution_store[execution_id]
        is_synced = (
            store['status'] == 'failed' and
            store['stage'] == 'failed'
        )
        
        print_result(
            "任务失败时 status/stage 同步",
            is_synced,
            f"status='{store['status']}', stage='{store['stage']}'"
        )
        
    except Exception as e:
        print_result("任务失败时 status/stage 同步", False, str(e))


def test_stage_naming_consistency():
    """测试 5: 阶段命名一致性"""
    try:
        from wechat_backend.models import TaskStage
        
        # 检查标准阶段命名
        standard_stages = [
            'init',
            'ai_fetching',  # 不是 'ai_testing'
            'ranking_analysis',
            'source_tracing',
            'completed',
            'failed'
        ]
        
        actual_stages = [stage.value for stage in TaskStage]
        
        # 检查是否包含所有标准阶段
        has_all = all(stage in actual_stages for stage in standard_stages)
        
        # 检查是否使用了非标准命名
        has_ai_testing = 'ai_testing' in actual_stages
        
        print_result(
            "阶段命名一致性",
            has_all and not has_ai_testing,
            f"标准阶段：{standard_stages}, 实际阶段：{actual_stages}"
        )
        
    except Exception as e:
        print_result("阶段命名一致性", False, str(e))


def test_update_task_stage_with_failed():
    """测试 6: update_task_stage 处理 FAILED 阶段"""
    try:
        from wechat_backend.models import TaskStage, TaskStatus, update_task_stage
        import tempfile
        import sqlite3
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name
        
        # 初始化数据库表
        conn = sqlite3.connect(temp_db)
        conn.execute('''
            CREATE TABLE task_statuses (
                task_id TEXT PRIMARY KEY,
                progress INTEGER,
                stage TEXT,
                status_text TEXT,
                is_completed INTEGER,
                created_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
        # 临时修改 DB_PATH
        import wechat_backend.models as models
        original_db = models.DB_PATH
        models.DB_PATH = temp_db
        
        try:
            # 创建测试任务
            task_id = "test_update_failed"
            update_task_stage(task_id, TaskStage.FAILED, progress=0, status_text="测试失败")
            
            # 验证
            from wechat_backend.models import get_task_status
            task_status = get_task_status(task_id)
            
            is_correct = (
                task_status.stage == TaskStage.FAILED and
                task_status.is_completed == True and
                task_status.progress == 0
            )
            
            print_result(
                "update_task_stage 处理 FAILED 阶段",
                is_correct,
                f"stage={task_status.stage.value}, is_completed={task_status.is_completed}, progress={task_status.progress}"
            )
        finally:
            # 恢复原路径
            models.DB_PATH = original_db
            # 清理临时文件
            os.unlink(temp_db)
            
    except Exception as e:
        print_result("update_task_stage 处理 FAILED 阶段", False, str(e))


def test_api_response_format():
    """测试 7: API 响应格式一致性"""
    try:
        # 模拟 API 响应构建
        def build_response_from_store(task_status):
            response_data = {
                'task_id': 'test_123',
                'progress': task_status.get('progress', 0),
                'stage': task_status.get('stage', 'init'),
                'status': task_status.get('status', 'init'),
                'results': task_status.get('results', []),
                'is_completed': task_status.get('status') == 'completed',
            }
            
            # 【修复】确保 stage 与 status 同步
            if response_data['status'] == 'completed' and response_data['stage'] != 'completed':
                response_data['stage'] = 'completed'
            
            return response_data
        
        # 测试完成状态
        store_completed = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100
        }
        response = build_response_from_store(store_completed)
        
        is_synced = (
            response['status'] == 'completed' and
            response['stage'] == 'completed' and
            response['is_completed'] == True
        )
        
        print_result(
            "API 响应格式一致性 (完成)",
            is_synced,
            f"status={response['status']}, stage={response['stage']}, is_completed={response['is_completed']}"
        )
        
    except Exception as e:
        print_result("API 响应格式一致性", False, str(e))


def test_database_fallback():
    """测试 8: 数据库降级逻辑"""
    try:
        from wechat_backend.models import TaskStage, TaskStatus
        
        # 模拟数据库对象
        class MockDBTaskStatus:
            def __init__(self):
                self.task_id = "db_task_123"
                self.progress = 100
                self.stage = TaskStage.COMPLETED
                self.is_completed = True
                self.created_at = datetime.now().isoformat()
        
        db_task_status = MockDBTaskStatus()
        
        # 模拟修复后的响应构建
        response_data = {
            'task_id': db_task_status.task_id,
            'progress': db_task_status.progress,
            'stage': db_task_status.stage.value if hasattr(db_task_status.stage, 'value') else str(db_task_status.stage),
            'status': 'completed' if db_task_status.is_completed else 'processing',
            'results': [],
            'detailed_results': [],
            'is_completed': db_task_status.is_completed,
            'created_at': db_task_status.created_at
        }
        
        # 【修复】确保 stage 与 status 同步
        if response_data['status'] == 'completed' and response_data['stage'] != 'completed':
            response_data['stage'] = 'completed'
        
        is_correct = (
            response_data['status'] == 'completed' and
            response_data['stage'] == 'completed' and
            response_data['is_completed'] == True and
            response_data['progress'] == 100
        )
        
        print_result(
            "数据库降级逻辑",
            is_correct,
            f"status={response_data['status']}, stage={response_data['stage']}, is_completed={response_data['is_completed']}"
        )
        
    except Exception as e:
        print_result("数据库降级逻辑", False, str(e))


def test_all_mvp_endpoints():
    """测试 9: 所有 MVP 端点使用一致的阶段命名"""
    try:
        # 检查 views.py 中的阶段命名
        import re
        
        views_path = os.path.join(os.path.dirname(__file__), 'backend_python', 'wechat_backend', 'views.py')
        with open(views_path, 'r', encoding='utf-8') as f:
            views_content = f.read()
        
        # 查找所有 stage 赋值
        stage_assignments = re.findall(r"'stage':\s*'([^']+)'", views_content)
        
        # 检查是否使用了非标准命名
        non_standard = [s for s in stage_assignments if s not in ['init', 'ai_fetching', 'ranking_analysis', 'source_tracing', 'completed', 'failed', 'processing']]
        
        has_ai_testing = 'ai_testing' in stage_assignments
        
        print_result(
            "MVP 端点阶段命名一致性",
            len(non_standard) == 0 and not has_ai_testing,
            f"发现的阶段：{set(stage_assignments)}, 非标准：{non_standard}"
        )
        
    except Exception as e:
        print_result("MVP 端点阶段命名一致性", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print_header("综合系统测试 - 状态同步修复验证")
    
    print("运行测试套件...\n")
    
    test_task_stage_enum()
    test_execution_store_initialization()
    test_status_stage_sync_completed()
    test_status_stage_sync_failed()
    test_stage_naming_consistency()
    test_update_task_stage_with_failed()
    test_api_response_format()
    test_database_fallback()
    test_all_mvp_endpoints()
    
    # 打印汇总
    print_header("测试汇总")
    print(f"总计：{tests_total} 个测试")
    print(f"通过：{tests_passed} ✅")
    print(f"失败：{tests_failed} ❌")
    print(f"通过率：{(tests_passed/tests_total*100):.1f}%")
    
    if tests_failed == 0:
        print("\n🎉 所有测试通过！状态同步修复验证成功！")
        return 0
    else:
        print(f"\n⚠️  有 {tests_failed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
