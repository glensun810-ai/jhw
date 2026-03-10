"""
品牌诊断系统 - 集成测试套件

测试范围:
1. 端到端流程测试
2. AI 调用容错测试
3. 数据持久化测试
4. 快照存储测试
5. 历史查询测试
6. 部分失败场景测试
7. 全部失败场景测试

运行测试:
    cd backend_python
    python3 -m pytest tests/test_integration_full.py -v --tb=short

作者：测试工程师 赵工
日期：2026-02-25
"""

import pytest
import json
import time
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 导入被测试模块
from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor, ErrorType
from wechat_backend.repositories import (
    save_report_snapshot,
    get_report_snapshot,
    save_dimension_result,
    get_dimension_results,
    save_task_status,
    get_task_status
)
from wechat_backend.nxm_execution_engine import execute_nxm_test, verify_nxm_execution


# ==================== 测试配置 ====================

class TestConfig:
    """测试配置"""
    TEST_DB_PATH = Path(__file__).parent.parent / 'database_test.db'
    TEST_EXECUTION_ID = f"test_exec_{int(time.time())}"
    TEST_USER_ID = "test_user_123"
    TEST_BRAND = "测试品牌"
    TEST_COMPETITORS = ["竞品 A", "竞品 B"]
    TEST_MODELS = [{"name": "doubao", "checked": True}]
    TEST_QUESTIONS = ["介绍一下测试品牌"]


# ==================== 数据库 fixture ====================

@pytest.fixture(scope="function")
def db_connection():
    """数据库连接 fixture"""
    import sqlite3
    from pathlib import Path
    
    db_path = Path(__file__).parent.parent / 'database_test.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # 创建测试表
    cursor = conn.cursor()
    
    # 创建 report_snapshots 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            report_data TEXT NOT NULL,
            report_hash TEXT NOT NULL,
            size_kb INTEGER NOT NULL,
            storage_timestamp TEXT NOT NULL,
            report_version TEXT DEFAULT 'v2.0'
        )
    ''')
    
    # 创建 dimension_results 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dimension_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL,
            dimension_name TEXT NOT NULL,
            dimension_type TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            score REAL,
            data TEXT,
            error_message TEXT
        )
    ''')
    
    # 创建 task_statuses 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            progress INTEGER DEFAULT 0,
            stage TEXT NOT NULL,
            status_text TEXT,
            is_completed BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    yield conn
    
    # 清理测试数据
    cursor.execute('DELETE FROM report_snapshots')
    cursor.execute('DELETE FROM dimension_results')
    cursor.execute('DELETE FROM task_statuses')
    conn.commit()
    conn.close()


# ==================== 集成测试类 ====================

class TestEndToEndFlow:
    """端到端流程测试"""
    
    def test_normal_report_generation(self, db_connection):
        """测试正常报告生成流程"""
        # 模拟成功场景
        execution_id = TestConfig.TEST_EXECUTION_ID
        user_id = TestConfig.TEST_USER_ID
        
        # 1. 构建模拟报告数据
        report_data = {
            "reportId": execution_id,
            "userId": user_id,
            "brandName": TestConfig.TEST_BRAND,
            "generateTime": datetime.now().isoformat(),
            "reportVersion": "v2.0",
            "reportData": {
                "overallScore": 85,
                "overallStatus": "completed",
                "dimensions": [
                    {
                        "dimension_name": "社交媒体影响力",
                        "status": "success",
                        "score": 90,
                        "data": {"mentionCount": 12500}
                    }
                ]
            }
        }
        
        # 2. 保存快照
        snapshot_id = save_report_snapshot(
            execution_id=execution_id,
            user_id=user_id,
            report_data=report_data
        )
        
        # 3. 验证快照保存成功
        assert snapshot_id == execution_id
        
        # 4. 检索快照
        retrieved = get_report_snapshot(execution_id)
        
        assert retrieved is not None
        assert retrieved["reportId"] == execution_id
        assert retrieved["reportData"]["overallScore"] == 85
        
        print("✅ 正常报告生成流程测试通过")
    
    def test_partial_failure_scenario(self, db_connection):
        """测试部分失败场景"""
        execution_id = f"{TestConfig.TEST_EXECUTION_ID}_partial"
        user_id = TestConfig.TEST_USER_ID
        
        # 1. 保存成功的维度结果
        save_dimension_result(
            execution_id=execution_id,
            dimension_name="社交媒体影响力",
            dimension_type="ai_analysis",
            source="doubao",
            status="success",
            score=90,
            data={"mentionCount": 12500}
        )
        
        # 2. 保存失败的维度结果
        save_dimension_result(
            execution_id=execution_id,
            dimension_name="新闻舆情",
            dimension_type="ai_analysis",
            source="baidu",
            status="failed",
            score=None,
            data=None,
            error_message="【新闻舆情】AI 平台配额已用尽"
        )
        
        # 3. 检索维度结果
        dimensions = get_dimension_results(execution_id)
        
        assert len(dimensions) == 2
        success_count = sum(1 for d in dimensions if d['status'] == 'success')
        failed_count = sum(1 for d in dimensions if d['status'] == 'failed')
        
        assert success_count == 1
        assert failed_count == 1
        
        # 4. 保存部分失败的报告快照
        report_data = {
            "reportId": execution_id,
            "userId": user_id,
            "brandName": TestConfig.TEST_BRAND,
            "reportData": {
                "overallScore": 90,
                "overallStatus": "completed_with_warnings",
                "dimensions": dimensions
            }
        }
        
        save_report_snapshot(
            execution_id=execution_id,
            user_id=user_id,
            report_data=report_data
        )
        
        # 5. 验证快照
        retrieved = get_report_snapshot(execution_id)
        
        assert retrieved is not None
        assert retrieved["reportData"]["overallStatus"] == "completed_with_warnings"
        
        print("✅ 部分失败场景测试通过")
    
    def test_all_failed_scenario(self, db_connection):
        """测试全部失败场景"""
        execution_id = f"{TestConfig.TEST_EXECUTION_ID}_all_failed"
        user_id = TestConfig.TEST_USER_ID
        
        # 1. 保存全部失败的维度结果
        for i, source in enumerate(["doubao", "baidu", "openai"]):
            save_dimension_result(
                execution_id=execution_id,
                dimension_name=f"维度{i}",
                dimension_type="ai_analysis",
                source=source,
                status="failed",
                score=None,
                data=None,
                error_message=f"【{source}】AI 调用失败"
            )
        
        # 2. 检索维度结果
        dimensions = get_dimension_results(execution_id)
        
        assert len(dimensions) == 3
        assert all(d['status'] == 'failed' for d in dimensions)
        
        # 3. 保存全部失败的报告快照
        report_data = {
            "reportId": execution_id,
            "userId": user_id,
            "brandName": TestConfig.TEST_BRAND,
            "reportData": {
                "overallScore": None,
                "overallStatus": "all_failed",
                "dimensions": dimensions
            }
        }
        
        save_report_snapshot(
            execution_id=execution_id,
            user_id=user_id,
            report_data=report_data
        )
        
        # 4. 验证快照
        retrieved = get_report_snapshot(execution_id)
        
        assert retrieved is not None
        assert retrieved["reportData"]["overallStatus"] == "all_failed"
        assert retrieved["reportData"]["overallScore"] is None
        
        print("✅ 全部失败场景测试通过")


class TestFaultTolerantExecutor:
    """容错执行器测试"""
    
    @pytest.mark.asyncio
    async def test_successful_ai_call(self):
        """测试成功的 AI 调用"""
        executor = FaultTolerantExecutor(timeout_seconds=5)
        
        async def mock_ai_call():
            return {"content": "测试响应", "success": True}
        
        result = await executor.execute_with_fallback(
            task_func=mock_ai_call,
            task_name="测试 AI 调用",
            source="test_ai"
        )
        
        assert result.status == "success"
        assert result.data["content"] == "测试响应"
        assert result.error_message is None
        
        print("✅ 成功的 AI 调用测试通过")
    
    @pytest.mark.asyncio
    async def test_timeout_ai_call(self):
        """测试超时的 AI 调用"""
        executor = FaultTolerantExecutor(timeout_seconds=1)
        
        async def slow_ai_call():
            import asyncio
            await asyncio.sleep(10)
            return {"content": "不应到达这里"}
        
        result = await executor.execute_with_fallback(
            task_func=slow_ai_call,
            task_name="慢速 AI 调用",
            source="slow_ai"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.TIMEOUT
        assert "超时" in result.error_message
        
        print("✅ 超时的 AI 调用测试通过")
    
    @pytest.mark.asyncio
    async def test_quota_exhausted_error(self):
        """测试配额用尽错误"""
        executor = FaultTolerantExecutor(timeout_seconds=5)
        
        async def quota_error_call():
            raise Exception("insufficient_quota: 配额已用尽")
        
        result = await executor.execute_with_fallback(
            task_func=quota_error_call,
            task_name="配额测试",
            source="quota_ai"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.QUOTA_EXHAUSTED
        assert "配额" in result.error_message
        
        print("✅ 配额用尽错误测试通过")
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_error(self):
        """测试无效 API Key 错误"""
        executor = FaultTolerantExecutor(timeout_seconds=5)
        
        async def auth_error_call():
            raise Exception("401 Unauthorized: Invalid API key")
        
        result = await executor.execute_with_fallback(
            task_func=auth_error_call,
            task_name="认证测试",
            source="auth_ai"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.INVALID_API_KEY
        assert "密钥" in result.error_message or "API" in result.error_message
        
        print("✅ 无效 API Key 错误测试通过")


class TestDataPersistence:
    """数据持久化测试"""
    
    def test_dimension_result_persistence(self, db_connection):
        """测试维度结果持久化"""
        execution_id = f"{TestConfig.TEST_EXECUTION_ID}_dim"
        
        # 保存维度结果
        record_id = save_dimension_result(
            execution_id=execution_id,
            dimension_name="测试维度",
            dimension_type="ai_analysis",
            source="test_source",
            status="success",
            score=85,
            data={"test": "data"}
        )
        
        assert record_id > 0
        
        # 检索维度结果
        dimensions = get_dimension_results(execution_id)
        
        assert len(dimensions) == 1
        assert dimensions[0]['dimension_name'] == "测试维度"
        assert dimensions[0]['score'] == 85
        assert dimensions[0]['data'] == {"test": "data"}
        
        print("✅ 维度结果持久化测试通过")
    
    def test_task_status_persistence(self, db_connection):
        """测试任务状态持久化"""
        execution_id = f"{TestConfig.TEST_EXECUTION_ID}_task"
        
        # 保存任务状态
        record_id = save_task_status(
            task_id=execution_id,
            stage='ai_fetching',
            progress=50,
            status_text='已完成 5/10',
            is_completed=False
        )
        
        assert record_id > 0
        
        # 检索任务状态
        status = get_task_status(execution_id)
        
        assert status is not None
        assert status['progress'] == 50
        assert status['stage'] == 'ai_fetching'
        
        # 更新任务状态
        from wechat_backend.repositories.task_status_repository import update_task_progress
        updated = update_task_progress(
            task_id=execution_id,
            progress=100,
            stage='completed'
        )
        
        assert updated is True
        
        # 验证更新
        updated_status = get_task_status(execution_id)
        assert updated_status['progress'] == 100
        assert updated_status['stage'] == 'completed'
        
        print("✅ 任务状态持久化测试通过")
    
    def test_snapshot_consistency(self, db_connection):
        """测试快照一致性验证"""
        execution_id = f"{TestConfig.TEST_EXECUTION_ID}_snapshot"
        user_id = TestConfig.TEST_USER_ID
        
        # 保存快照
        report_data = {
            "reportId": execution_id,
            "userId": user_id,
            "brandName": TestConfig.TEST_BRAND,
            "reportData": {"test": "data"}
        }
        
        save_report_snapshot(
            execution_id=execution_id,
            user_id=user_id,
            report_data=report_data
        )
        
        # 验证一致性
        from wechat_backend.repositories.report_snapshot_repository import get_snapshot_repository
        repo = get_snapshot_repository()
        
        is_valid, error_msg = repo.verify_consistency(execution_id)
        
        assert is_valid is True
        assert error_msg is None
        
        print("✅ 快照一致性验证测试通过")


class TestHistoricalQuery:
    """历史查询测试"""
    
    def test_get_user_history(self, db_connection):
        """测试获取用户历史报告"""
        user_id = TestConfig.TEST_USER_ID
        
        # 保存多个报告
        for i in range(5):
            execution_id = f"{TestConfig.TEST_EXECUTION_ID}_hist_{i}"
            report_data = {
                "reportId": execution_id,
                "userId": user_id,
                "brandName": f"品牌{i}",
                "reportData": {"index": i}
            }
            
            save_report_snapshot(
                execution_id=execution_id,
                user_id=user_id,
                report_data=report_data
            )
        
        # 获取用户历史
        from wechat_backend.repositories.report_snapshot_repository import get_snapshot_repository
        repo = get_snapshot_repository()
        
        history = repo.get_user_history(user_id, limit=10)
        
        assert len(history) >= 5
        assert all(h['user_id'] == user_id for h in history)
        
        print("✅ 获取用户历史报告测试通过")


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    def test_concurrent_save_operations(self, db_connection):
        """测试并发保存操作"""
        import concurrent.futures
        
        user_id = TestConfig.TEST_USER_ID
        
        def save_report(i):
            execution_id = f"{TestConfig.TEST_EXECUTION_ID}_perf_{i}"
            report_data = {
                "reportId": execution_id,
                "userId": user_id,
                "brandName": f"品牌{i}",
                "reportData": {"index": i}
            }
            
            save_report_snapshot(
                execution_id=execution_id,
                user_id=user_id,
                report_data=report_data
            )
            return True
        
        # 并发保存 10 个报告
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(save_report, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert all(results)
        
        # 验证保存成功
        repo = get_snapshot_repository()
        history = repo.get_user_history(user_id, limit=20)
        
        assert len(history) >= 10
        
        print("✅ 并发保存操作性能测试通过")


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
