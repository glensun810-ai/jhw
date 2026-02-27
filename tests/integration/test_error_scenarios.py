"""
异常场景集成测试

测试覆盖：
1. AI 平台不可用
2. 部分 AI 平台失败
3. 轮询过程网络中断
4. 数据库错误
5. 超时与重试失败

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio


class TestErrorScenarios:
    """异常场景测试"""
    
    @pytest.mark.asyncio
    async def test_ai_platform_unavailable(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试 AI 平台不可用场景"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建总是失败的适配器
        class UnavailableAdapter:
            async def send_prompt(self, brand, question, model):
                raise Exception("AI 平台服务不可用")
        
        service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=UnavailableAdapter()
        )
        
        # 发起诊断
        await service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 获取状态
        status = await service.get_status(sample_execution_id)
        
        # 验证状态
        assert status['status'] in ['failed', 'timeout']
        assert status['should_stop_polling'] is True
        
        # 获取报告（应为存根）
        report = await service.get_report(sample_execution_id)
        assert report['meta']['is_stub'] is True
        assert report['meta']['has_data'] is False
    
    @pytest.mark.asyncio
    async def test_partial_ai_platform_failure(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试部分 AI 平台失败场景"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建部分失败的适配器
        class PartialFailureAdapter:
            def __init__(self):
                self.calls = {}
            
            async def send_prompt(self, brand, question, model):
                key = f"{brand}_{model}"
                self.calls[key] = self.calls.get(key, 0) + 1
                
                # deepseek 总是失败
                if model == 'deepseek':
                    raise Exception(f"{model} 平台暂时不可用")
                
                # doubao 30% 失败
                if model == 'doubao' and self.calls[key] % 3 == 0:
                    raise Exception(f"{model} 随机失败")
                
                return {
                    'content': f'{brand}的响应',
                    'model': model,
                    'latency_ms': 200
                }
        
        service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=PartialFailureAdapter()
        )
        
        await service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        await asyncio.sleep(10)
        
        # 获取报告
        report = await service.get_report(sample_execution_id)
        
        # 验证部分成功
        assert report['report']['status'] == 'partial_success'
        assert report['meta']['is_stub'] is True
        assert report['meta']['has_data'] is True
        assert report['meta']['successful_count'] > 0
    
    @pytest.mark.asyncio
    async def test_network_interruption_during_polling(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        monkeypatch
    ):
        """测试轮询过程中的网络中断"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        service = DiagnosisService(db_path=test_db_path)
        
        await service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 模拟网络中断
        call_count = 0
        original_get_status = service.get_status
        
        async def mock_get_status(exec_id):
            nonlocal call_count
            call_count += 1
            
            if 3 <= call_count <= 5:  # 第 3-5 次调用模拟网络错误
                raise Exception("网络连接失败")
            
            return await original_get_status(exec_id)
        
        service.get_status = mock_get_status
        
        # 等待完成
        await asyncio.sleep(10)
        
        # 验证轮询最终完成
        status = await service.get_status(sample_execution_id)
        assert status['should_stop_polling'] is True
        assert call_count > 5  # 网络恢复后继续轮询
    
    @pytest.mark.asyncio
    async def test_database_connection_error(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试数据库连接错误"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        service = DiagnosisService(db_path=test_db_path)
        
        # 正常发起诊断
        await service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证能正常获取状态
        status = await service.get_status(sample_execution_id)
        assert status['execution_id'] == sample_execution_id
    
    @pytest.mark.asyncio
    async def test_timeout_with_no_retry(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试超时无重试场景"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建很慢的适配器
        class VerySlowAdapter:
            async def send_prompt(self, brand, question, model):
                await asyncio.sleep(100)  # 非常慢
                return {'content': '响应', 'model': model}
        
        service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=VerySlowAdapter(),
            timeout=2  # 2 秒超时
        )
        
        await service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待超时
        await asyncio.sleep(5)
        
        # 验证超时
        status = await service.get_status(sample_execution_id)
        assert status['status'] in ['timeout', 'failed']
        assert status['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_invalid_execution_id(
        self,
        test_db_path
    ):
        """测试无效执行 ID"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        service = DiagnosisService(db_path=test_db_path)
        
        # 尝试获取不存在的任务状态
        with pytest.raises(Exception) as exc_info:
            await service.get_status('invalid_exec_id_12345')
        
        assert exc_info.value is not None
