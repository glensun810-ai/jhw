"""
报告存根集成测试

测试覆盖：
1. 失败时返回存根报告
2. 部分成功时返回部分数据
3. 存根报告数据完整性
4. 存根报告可用性

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio

from wechat_backend.v2.services.report_stub_service import ReportStubService


class TestReportStubIntegration:
    """报告存根集成测试"""
    
    @pytest.mark.asyncio
    async def test_stub_report_on_failure(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        failing_ai_adapter
    ):
        """测试失败时返回存根报告"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=failing_ai_adapter
        )
        
        # 发起诊断（会失败）
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待失败
        await asyncio.sleep(3)
        
        # 获取报告（应为存根）
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证存根标记
        assert report['meta']['is_stub'] is True
        assert report['meta']['has_data'] is False
        assert 'error_message' in report['meta']
    
    @pytest.mark.asyncio
    async def test_stub_report_with_partial_data(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        flaky_ai_adapter
    ):
        """测试部分成功时返回部分数据"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=flaky_ai_adapter  # 30% 失败率
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(10)
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证部分数据
        if report['report']['status'] == 'partial_success':
            assert report['meta']['is_stub'] is True
            assert report['meta']['has_data'] is True
            assert report['meta']['successful_count'] > 0
            assert len(report['results']) > 0
    
    @pytest.mark.asyncio
    async def test_stub_report_data_completeness(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试存根报告数据完整度计算"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建部分失败的适配器
        class PartialAdapter:
            def __init__(self):
                self.success_count = 0
                self.fail_count = 0
            
            async def send_prompt(self, brand, question, model):
                if self.success_count < 3:
                    self.success_count += 1
                    return {'content': '成功', 'model': model}
                else:
                    self.fail_count += 1
                    raise Exception("失败")
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=PartialAdapter()
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        await asyncio.sleep(5)
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证完整度
        meta = report['meta']
        if meta['results_count'] > 0:
            completeness = meta['successful_count'] / meta['results_count'] * 100
            assert meta['data_completeness'] == round(completeness, 2)
    
    @pytest.mark.asyncio
    async def test_stub_report_with_api_logs(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        failing_ai_adapter
    ):
        """测试存根报告包含 API 日志"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=failing_ai_adapter
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待失败
        await asyncio.sleep(3)
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证包含 API 调用信息
        assert report['meta']['api_call_count'] > 0
        assert 'success_rate' in report['meta']
    
    @pytest.mark.asyncio
    async def test_stub_report_checksum(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试存根报告校验和"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 获取报告
        report = await diagnosis_service.get_report(exec_id)
        
        # 验证校验和存在
        assert 'checksum' in report['report']
        assert report['report']['checksum'] is not None
    
    @pytest.mark.asyncio
    async def test_stub_report_error_details(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试存根报告错误详情"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建带详细错误的适配器
        class DetailedErrorAdapter:
            async def send_prompt(self, brand, question, model):
                error = Exception(f"{model} 平台错误：详细错误信息")
                error.code = 'AI_PLATFORM_ERROR'
                raise error
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=DetailedErrorAdapter()
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        await asyncio.sleep(3)
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证错误详情
        assert 'error_message' in report['meta']
        assert report['meta']['error_message'] is not None
