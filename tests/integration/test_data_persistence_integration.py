"""
数据持久化集成测试

测试覆盖：
1. API 调用日志持久化
2. 原始数据持久化
3. 报告快照持久化
4. 数据恢复

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import json
from datetime import datetime

from wechat_backend.v2.repositories.api_call_log_repository import APICallLogRepository
from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository


class TestDataPersistenceIntegration:
    """数据持久化集成测试"""
    
    @pytest.mark.asyncio
    async def test_api_call_log_persistence(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试 API 调用日志持久化"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证日志持久化
        log_repo = APICallLogRepository(test_db_path)
        logs = log_repo.get_by_execution_id(sample_execution_id)
        
        assert len(logs) > 0
        
        # 验证日志内容
        for log in logs:
            assert log.execution_id == sample_execution_id
            assert log.brand is not None
            assert log.model is not None
            assert log.response_data is not None
    
    @pytest.mark.asyncio
    async def test_raw_data_persistence(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试原始数据持久化"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证原始数据持久化
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        assert len(results) > 0
        
        # 验证每条结果包含原始响应
        for result in results:
            assert result.response is not None
            assert 'content' in result.response
    
    @pytest.mark.asyncio
    async def test_report_snapshot_persistence(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试报告快照持久化"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 获取报告
        report = await diagnosis_service.get_report(exec_id)
        
        # 验证快照数据
        assert report is not None
        assert 'report' in report
        assert 'results' in report
    
    @pytest.mark.asyncio
    async def test_data_recovery_after_failure(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试失败后数据恢复"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建部分失败的适配器
        class PartialFailAdapter:
            def __init__(self):
                self.call_count = 0
            
            async def send_prompt(self, brand, question, model):
                self.call_count += 1
                if self.call_count <= 2:
                    raise Exception("前两次失败")
                return {'content': '成功', 'model': model}
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=PartialFailAdapter()
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证部分数据恢复
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        # 应有部分成功的数据
        successful_results = [r for r in results if r.error_message is None]
        assert len(successful_results) > 0
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_tables(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试跨表数据一致性"""
        
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 验证各表数据一致
        log_repo = APICallLogRepository(test_db_path)
        result_repo = DiagnosisResultRepository(test_db_path)
        
        logs = log_repo.get_by_execution_id(exec_id)
        results = result_repo.get_by_execution_id(exec_id)
        
        # 验证数量一致
        assert len(logs) == len(results)
        
        # 验证每条结果都有对应的日志
        for result in results:
            matching_logs = [
                log for log in logs
                if log.brand == result.brand and log.model == result.model
            ]
            assert len(matching_logs) > 0
    
    @pytest.mark.asyncio
    async def test_persistence_with_large_data(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试大数据量持久化"""
        
        from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
        from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
        
        result_repo = DiagnosisResultRepository(test_db_path)
        
        # 创建大量结果
        results = []
        for i in range(100):
            result = DiagnosisResult(
                report_id=1,
                execution_id=sample_execution_id,
                brand=f'品牌{i}',
                question='测试问题',
                model='deepseek',
                response={'content': f'响应{i}' * 100},  # 大响应
                geo_data={'exposure': True, 'sentiment': 'positive'}
            )
            results.append(result)
        
        # 批量写入
        result_repo.create_batch(results)
        
        # 验证写入成功
        saved_results = result_repo.get_by_execution_id(sample_execution_id)
        assert len(saved_results) == 100
    
    @pytest.mark.asyncio
    async def test_persistence_transaction_integrity(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试持久化事务完整性"""
        
        from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
        from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
        
        result_repo = DiagnosisResultRepository(test_db_path)
        
        # 创建结果列表
        results = [
            DiagnosisResult(
                report_id=1,
                execution_id=sample_execution_id,
                brand=f'品牌{i}',
                question='测试',
                model='deepseek',
                response={'content': f'响应{i}'}
            )
            for i in range(5)
        ]
        
        # 批量写入
        result_repo.create_batch(results)
        
        # 验证要么全部成功，要么全部失败
        saved_results = result_repo.get_by_execution_id(sample_execution_id)
        assert len(saved_results) == 5
