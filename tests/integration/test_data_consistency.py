"""
数据一致性集成测试

测试覆盖：
1. 前端 - 后端 - 数据库一致性
2. 报告与原始结果一致性
3. 存根报告数据一致性
4. 跨服务数据一致性

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import json


class TestDataConsistency:
    """数据一致性测试"""
    
    @pytest.mark.asyncio
    async def test_frontend_backend_database_consistency(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试前端、后端、数据库三者数据一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        repo = DiagnosisRepository(test_db_path)
        
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 1. 获取后端状态
        backend_status = await diagnosis_service.get_status(exec_id)
        
        # 2. 获取数据库记录
        db_record = repo.get_by_execution_id(exec_id)
        
        # 3. 验证关键字段一致性
        critical_fields = ['status', 'progress', 'is_completed', 'should_stop_polling']
        
        for field in critical_fields:
            # 后端状态 vs 数据库
            backend_value = backend_status.get(field)
            db_value = db_record.get(field)
            
            # 处理布尔值转换
            if isinstance(db_value, int):
                db_value = bool(db_value)
            
            assert backend_value == db_value, \
                f"字段 {field} 在后端和数据库中不一致：{backend_value} != {db_value}"
    
    @pytest.mark.asyncio
    async def test_report_results_consistency(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试报告与原始结果数据一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        result_repo = DiagnosisResultRepository(test_db_path)
        
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 1. 获取报告
        report = await diagnosis_service.get_report(exec_id)
        
        # 2. 获取原始结果
        raw_results = result_repo.get_by_execution_id(exec_id)
        
        # 3. 验证结果数量一致
        assert len(report['results']) == len(raw_results)
        
        # 4. 验证每条结果内容一致
        for i, report_result in enumerate(report['results']):
            raw_result = raw_results[i]
            
            # 检查关键字段
            assert report_result['brand'] == raw_result.brand
            assert report_result['question'] == raw_result.question
            assert report_result['model'] == raw_result.model
            
            # 检查响应内容
            if 'response' in report_result and raw_result.response:
                assert report_result['response'].get('content') == \
                       raw_result.response.get('content')
    
    @pytest.mark.asyncio
    async def test_stub_report_data_consistency(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        flaky_ai_adapter
    ):
        """测试存根报告与部分数据一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.services.report_stub_service import ReportStubService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=flaky_ai_adapter
        )
        
        # 发起诊断（部分会失败）
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(10)
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证存根中的数据与真实结果一致
        if report['meta']['results_count'] > 0:
            assert report['meta']['successful_count'] <= report['meta']['results_count']
            
            # 验证数据完整度计算正确
            expected_completeness = round(
                report['meta']['successful_count'] / report['meta']['results_count'] * 100, 2
            )
            assert report['meta']['data_completeness'] == expected_completeness
    
    @pytest.mark.asyncio
    async def test_cross_service_data_consistency(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试跨服务数据一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.repositories.api_call_log_repository import APICallLogRepository
        from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
        
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 获取各服务数据
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        log_repo = APICallLogRepository(test_db_path)
        result_repo = DiagnosisResultRepository(test_db_path)
        
        report = await diagnosis_service.get_report(exec_id)
        logs = log_repo.get_by_execution_id(exec_id)
        results = result_repo.get_by_execution_id(exec_id)
        
        # 验证数量一致
        assert len(report['results']) == len(results)
        assert len(logs) == len(results)
    
    @pytest.mark.asyncio
    async def test_progress_consistency_during_execution(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试执行过程中进度一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        repo = DiagnosisRepository(test_db_path)
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 在执行过程中多次验证进度一致性
        for _ in range(5):
            await asyncio.sleep(0.5)
            
            # 获取服务状态
            service_status = await diagnosis_service.get_status(sample_execution_id)
            
            # 获取数据库状态
            db_record = repo.get_by_execution_id(sample_execution_id)
            
            if db_record is None:
                continue
            
            # 验证进度一致
            service_progress = service_status.get('progress', 0)
            db_progress = db_record.get('progress', 0)
            
            assert service_progress == db_progress, \
                f"进度不一致：服务={service_progress}, 数据库={db_progress}"
            
            if service_status.get('should_stop_polling'):
                break
    
    @pytest.mark.asyncio
    async def test_metadata_consistency(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试元数据一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 获取报告
        report = await diagnosis_service.get_report(exec_id)
        
        # 验证元数据字段
        assert 'meta' in report
        assert 'data_schema_version' in report['report']
        assert 'server_version' in report['report']
        
        # 验证校验和
        assert 'checksum' in report['report']
        assert report['report']['checksum'] is not None
