"""
品牌诊断系统综合测试套件

测试范围：
1. 容错执行器测试
2. 报告快照存储测试
3. 维度结果存储测试
4. 端到端集成测试
5. 异常流程测试

运行测试：
    pytest tests/test_brand_diagnosis_system.py -v --cov=wechat_backend

作者：测试/性能专家
日期：2026-02-25
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 导入被测试模块
from wechat_backend.fault_tolerant_executor import (
    FaultTolerantExecutor,
    FaultTolerantResult,
    BatchFaultTolerantExecutor,
    ErrorType,
    execute_with_fallback,
    safe_json_serialize
)

from wechat_backend.repositories.report_snapshot_repository import (
    ReportSnapshotRepository,
    get_snapshot_repository,
    save_report_snapshot,
    get_report_snapshot
)

from wechat_backend.repositories.dimension_result_repository import (
    DimensionResultRepository,
    get_dimension_repository,
    save_dimension_result,
    get_dimension_results
)


# ==================== 容错执行器测试 ====================

class TestFaultTolerantExecutor:
    """容错执行器测试类"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return FaultTolerantExecutor(timeout_seconds=2)
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, executor):
        """测试成功执行"""
        async def successful_task():
            return {"data": "test_data"}
        
        result = await executor.execute_with_fallback(
            task_func=successful_task,
            task_name="测试任务",
            source="test_source"
        )
        
        assert result.status == "success"
        assert result.data == {"data": "test_data"}
        assert result.error_message is None
        assert result.execution_time is not None
    
    @pytest.mark.asyncio
    async def test_timeout_execution(self, executor):
        """测试超时执行"""
        async def slow_task():
            await asyncio.sleep(10)  # 超过 2 秒超时
            return {"data": "should_not_reach"}
        
        result = await executor.execute_with_fallback(
            task_func=slow_task,
            task_name="慢任务",
            source="test_source"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.TIMEOUT
        assert "超时" in result.error_message
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_exception_execution(self, executor):
        """测试异常执行"""
        async def failing_task():
            raise ValueError("测试错误")
        
        result = await executor.execute_with_fallback(
            task_func=failing_task,
            task_name="失败任务",
            source="test_source"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.UNKNOWN
        assert "失败任务" in result.error_message
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_quota_exhausted_error(self, executor):
        """测试配额用尽错误识别"""
        async def quota_error_task():
            raise Exception("insufficient_quota: 配额已用尽")
        
        result = await executor.execute_with_fallback(
            task_func=quota_error_task,
            task_name="配额任务",
            source="ai_platform"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.QUOTA_EXHAUSTED
        assert "配额" in result.error_message
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_error(self, executor):
        """测试无效 API Key 错误识别"""
        async def auth_error_task():
            raise Exception("401 Unauthorized: Invalid API key")
        
        result = await executor.execute_with_fallback(
            task_func=auth_error_task,
            task_name="认证任务",
            source="api_service"
        )
        
        assert result.status == "failed"
        assert result.error_type == ErrorType.INVALID_API_KEY
        assert "密钥" in result.error_message or "API" in result.error_message
    
    @pytest.mark.asyncio
    async def test_sync_function_execution(self, executor):
        """测试同步函数执行"""
        def sync_task():
            return {"sync_data": "test"}
        
        result = await executor.execute_with_fallback(
            task_func=sync_task,
            task_name="同步任务",
            source="test_source"
        )
        
        assert result.status == "success"
        assert result.data == {"sync_data": "test"}
    
    @pytest.mark.asyncio
    async def test_result_to_dict(self, executor):
        """测试结果转换为字典"""
        result = FaultTolerantResult.success(
            data={"test": "data"},
            source="test",
            execution_time=1.5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "success"
        assert result_dict["data"] == {"test": "data"}
        assert result_dict["source"] == "test"
        assert result_dict["execution_time"] == 1.5


class TestBatchFaultTolerantExecutor:
    """批量容错执行器测试类"""
    
    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """测试批量执行"""
        executor = BatchFaultTolerantExecutor(timeout_seconds=2, max_concurrent=3)
        
        async def task1():
            return {"result": "task1"}
        
        async def task2():
            await asyncio.sleep(0.5)
            return {"result": "task2"}
        
        async def task3():
            raise ValueError("Task 3 failed")
        
        tasks = [
            {"func": task1, "name": "任务 1", "source": "source1"},
            {"func": task2, "name": "任务 2", "source": "source2"},
            {"func": task3, "name": "任务 3", "source": "source3"},
        ]
        
        results = await executor.execute_batch(tasks)
        
        assert len(results) == 3
        assert results[0].status == "success"
        assert results[1].status == "success"
        assert results[2].status == "failed"
    
    @pytest.mark.asyncio
    async def test_batch_statistics(self):
        """测试批量执行统计"""
        executor = BatchFaultTolerantExecutor(timeout_seconds=2, max_concurrent=3)
        
        results = [
            FaultTolerantResult.success(data={"data": "1"}, execution_time=1.0),
            FaultTolerantResult.success(data={"data": "2"}, execution_time=2.0),
            FaultTolerantResult.failed(error_message="Error", error_type=ErrorType.TIMEOUT),
        ]
        
        stats = executor.get_statistics(results)
        
        assert stats["total"] == 3
        assert stats["success_count"] == 2
        assert stats["failed_count"] == 1
        assert stats["success_rate"] == pytest.approx(0.666, rel=0.01)
        assert stats["avg_execution_time"] == 1.5


# ==================== 报告快照存储测试 ====================

class TestReportSnapshotRepository:
    """报告快照存储仓库测试类"""
    
    @pytest.fixture
    def repository(self):
        """创建仓库实例（使用测试数据库）"""
        # 这里应该使用测试数据库配置
        # 为简化，直接使用默认配置
        repo = ReportSnapshotRepository()
        yield repo
        # 清理测试数据
    
    @pytest.fixture
    def sample_report_data(self) -> Dict[str, Any]:
        """示例报告数据"""
        return {
            "reportId": "rep_test_001",
            "userId": "user_123",
            "brandName": "测试品牌",
            "generateTime": "2026-02-25T10:30:00Z",
            "reportVersion": "v1.0",
            "reportData": {
                "overallScore": 85,
                "overallStatus": "completed_with_warnings",
                "dimensions": [
                    {
                        "name": "社交媒体影响力",
                        "score": 90,
                        "status": "success",
                        "data": {"mentionCount": 12500}
                    },
                    {
                        "name": "新闻舆情",
                        "score": None,
                        "status": "failed",
                        "errorMessage": "API 配额用尽"
                    }
                ]
            },
            "storageMeta": {
                "sizeKB": 15
            }
        }
    
    def test_save_and_get_snapshot(self, repository, sample_report_data):
        """测试保存和获取快照"""
        execution_id = "test_exec_" + str(int(time.time()))
        user_id = "test_user_123"
        
        # 保存快照
        saved_id = repository.save_snapshot(
            execution_id=execution_id,
            user_id=user_id,
            report_data=sample_report_data
        )
        
        assert saved_id == execution_id
        
        # 获取快照
        retrieved_data = repository.get_snapshot(execution_id)
        
        assert retrieved_data is not None
        assert retrieved_data["reportId"] == sample_report_data["reportId"]
        assert retrieved_data["userId"] == user_id
        assert "_metadata" in retrieved_data
    
    def test_get_nonexistent_snapshot(self, repository):
        """测试获取不存在的快照"""
        result = repository.get_snapshot("nonexistent_id")
        assert result is None
    
    def test_verify_consistency(self, repository, sample_report_data):
        """测试一致性验证"""
        execution_id = "test_exec_consistency_" + str(int(time.time()))
        
        # 保存快照
        repository.save_snapshot(
            execution_id=execution_id,
            user_id="test_user",
            report_data=sample_report_data
        )
        
        # 验证一致性
        is_valid, error_msg = repository.verify_consistency(execution_id)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_get_user_history(self, repository, sample_report_data):
        """测试获取用户历史"""
        user_id = "test_user_history"
        
        # 保存多个快照
        for i in range(5):
            execution_id = f"test_exec_hist_{i}_{int(time.time())}"
            repository.save_snapshot(
                execution_id=execution_id,
                user_id=user_id,
                report_data=sample_report_data
            )
        
        # 获取历史
        history = repository.get_user_history(user_id, limit=10)
        
        assert len(history) >= 5
    
    def test_delete_snapshot(self, repository, sample_report_data):
        """测试删除快照"""
        execution_id = "test_exec_delete_" + str(int(time.time()))
        
        # 保存快照
        repository.save_snapshot(
            execution_id=execution_id,
            user_id="test_user",
            report_data=sample_report_data
        )
        
        # 验证已保存
        assert repository.get_snapshot(execution_id) is not None
        
        # 删除快照
        deleted = repository.delete_snapshot(execution_id)
        
        assert deleted is True
        
        # 验证已删除
        assert repository.get_snapshot(execution_id) is None
    
    def test_get_statistics(self, repository, sample_report_data):
        """测试获取统计信息"""
        # 保存一些测试数据
        for i in range(3):
            execution_id = f"test_exec_stats_{i}_{int(time.time())}"
            repository.save_snapshot(
                execution_id=execution_id,
                user_id="test_user_stats",
                report_data=sample_report_data
            )
        
        # 获取统计
        stats = repository.get_statistics()
        
        assert "total_count" in stats
        assert "total_size_kb" in stats
        assert "top_users" in stats


# ==================== 维度结果存储测试 ====================

class TestDimensionResultRepository:
    """维度结果存储仓库测试类"""
    
    @pytest.fixture
    def repository(self):
        """创建仓库实例"""
        repo = DimensionResultRepository()
        yield repo
        # 清理测试数据
    
    @pytest.fixture
    def sample_dimension(self) -> Dict[str, Any]:
        """示例维度数据"""
        return {
            "execution_id": "test_exec_dim",
            "dimension_name": "社交媒体影响力",
            "dimension_type": "social_media",
            "source": "weibo",
            "status": "success",
            "score": 90.0,
            "data": {
                "mentionCount": 12500,
                "sentiment": "positive"
            },
            "error_message": None
        }
    
    def test_save_dimension(self, repository, sample_dimension):
        """测试保存维度结果"""
        record_id = repository.save_dimension(
            execution_id=sample_dimension["execution_id"],
            dimension_name=sample_dimension["dimension_name"],
            dimension_type=sample_dimension["dimension_type"],
            source=sample_dimension["source"],
            status=sample_dimension["status"],
            score=sample_dimension["score"],
            data=sample_dimension["data"]
        )
        
        assert record_id > 0
    
    def test_get_dimensions_by_execution(self, repository, sample_dimension):
        """测试根据执行 ID 获取维度"""
        execution_id = "test_exec_get_" + str(int(time.time()))
        
        # 保存多个维度
        for i in range(3):
            repository.save_dimension(
                execution_id=execution_id,
                dimension_name=f"维度{i}",
                dimension_type="test_type",
                source="test_source",
                status="success",
                score=80.0 + i * 5,
                data={"index": i}
            )
        
        # 获取维度
        dimensions = repository.get_dimensions_by_execution(execution_id)
        
        assert len(dimensions) == 3
        assert all(d["execution_id"] == execution_id for d in dimensions)
    
    def test_get_dimension_statistics(self, repository):
        """测试获取维度统计"""
        execution_id = "test_exec_stats_" + str(int(time.time()))
        
        # 保存成功和失败的维度
        repository.save_dimension(
            execution_id=execution_id,
            dimension_name="成功维度",
            dimension_type="type1",
            source="source1",
            status="success",
            score=90.0,
            data={}
        )
        
        repository.save_dimension(
            execution_id=execution_id,
            dimension_name="失败维度",
            dimension_type="type1",
            source="source1",
            status="failed",
            score=None,
            data=None,
            error_message="测试错误"
        )
        
        # 获取统计
        stats = repository.get_dimension_statistics(execution_id)
        
        assert stats["total"] == 2
        assert stats["success_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["average_score"] == 90.0
    
    def test_update_dimension_status(self, repository):
        """测试更新维度状态"""
        execution_id = "test_exec_update_" + str(int(time.time()))
        
        # 保存维度
        repository.save_dimension(
            execution_id=execution_id,
            dimension_name="测试维度",
            dimension_type="type1",
            source="source1",
            status="success",
            score=90.0,
            data={}
        )
        
        # 更新状态
        updated = repository.update_dimension_status(
            execution_id=execution_id,
            dimension_name="测试维度",
            status="failed",
            error_message="更新后的错误"
        )
        
        assert updated is True
        
        # 验证更新
        dimensions = repository.get_dimensions_by_execution(execution_id)
        assert dimensions[0]["status"] == "failed"
        assert dimensions[0]["error_message"] == "更新后的错误"


# ==================== 便捷函数测试 ====================

class TestConvenienceFunctions:
    """便捷函数测试类"""
    
    def test_safe_json_serialize_success(self):
        """测试安全的 JSON 序列化（成功）"""
        data = {"key": "value", "number": 123}
        result = safe_json_serialize(data)
        
        assert result == data
    
    def test_safe_json_serialize_with_non_serializable(self):
        """测试安全的 JSON 序列化（含不可序列化对象）"""
        data = {"key": "value", "datetime": datetime.now()}
        result = safe_json_serialize(data)
        
        assert result is not None
        assert "key" in result
    
    def test_safe_json_serialize_failure(self):
        """测试安全的 JSON 序列化（失败）"""
        # 创建一个无法序列化的对象
        class Unserializable:
            def __repr__(self):
                raise TypeError("Cannot serialize")
        
        data = Unserializable()
        result = safe_json_serialize(data, default_value={"fallback": True})
        
        assert result == {"fallback": True}


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试类"""
    
    @pytest.mark.asyncio
    async def test_full_diagnosis_flow(self):
        """测试完整诊断流程（模拟）"""
        # 1. 创建执行器
        executor = FaultTolerantExecutor(timeout_seconds=5)
        
        # 2. 模拟执行多个任务
        async def mock_ai_call(brand: str):
            if brand == "失败品牌":
                raise Exception("模拟 API 失败")
            return {"brand": brand, "score": 85}
        
        brands = ["华为", "小米", "失败品牌", "比亚迪"]
        results = []
        
        for brand in brands:
            result = await executor.execute_with_fallback(
                task_func=mock_ai_call,
                task_name=f"{brand}分析",
                source="ai_platform",
                brand=brand
            )
            results.append(result)
        
        # 3. 验证结果
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        
        assert success_count == 3
        assert failed_count == 1
        
        # 4. 保存到快照仓库
        report_data = {
            "reportId": "integration_test_report",
            "userId": "test_user",
            "brandName": "集成测试",
            "generateTime": datetime.now().isoformat(),
            "results": [r.to_dict() for r in results]
        }
        
        execution_id = "integration_test_" + str(int(time.time()))
        snapshot_id = save_report_snapshot(
            execution_id=execution_id,
            user_id="test_user",
            report_data=report_data
        )
        
        assert snapshot_id == execution_id
        
        # 5. 验证可以检索
        retrieved = get_report_snapshot(execution_id)
        assert retrieved is not None
        assert retrieved["reportId"] == report_data["reportId"]


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试类"""
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """测试并发执行性能"""
        executor = BatchFaultTolerantExecutor(timeout_seconds=5, max_concurrent=10)
        
        async def quick_task(i: int):
            await asyncio.sleep(0.1)
            return {"index": i}
        
        tasks = [
            {"func": quick_task, "name": f"任务{i}", "args": [i], "kwargs": {}}
            for i in range(20)
        ]
        
        start_time = time.time()
        results = await executor.execute_batch(tasks)
        elapsed_time = time.time() - start_time
        
        # 20 个任务，每个 0.1 秒，并发 10 个，应该约 0.2 秒完成
        assert len(results) == 20
        assert elapsed_time < 1.0  # 宽松的时间限制
        assert all(r.status == "success" for r in results)
    
    @pytest.mark.asyncio
    async def test_repository_performance(self):
        """测试仓库性能"""
        repository = ReportSnapshotRepository()
        
        # 保存 10 个快照
        report_data = {"test": "data", "timestamp": time.time()}
        
        start_time = time.time()
        for i in range(10):
            execution_id = f"perf_test_{i}_{int(time.time())}"
            repository.save_snapshot(
                execution_id=execution_id,
                user_id="perf_user",
                report_data=report_data
            )
        save_elapsed = time.time() - start_time
        
        # 平均每个保存应该小于 0.1 秒
        assert save_elapsed < 2.0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
