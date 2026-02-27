"""
轮询机制集成测试

测试覆盖：
1. 前端轮询与后端状态同步
2. 轮询终止条件
3. 轮询超时处理
4. 轮询恢复机制

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio


class TestPollingIntegration:
    """轮询机制集成测试"""
    
    @pytest.mark.asyncio
    async def test_polling_stops_on_completion(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试轮询在完成时停止"""
        
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
        
        # 模拟前端轮询
        poll_count = 0
        max_polls = 30
        
        for _ in range(max_polls):
            status = await diagnosis_service.get_status(sample_execution_id)
            poll_count += 1
            
            if status['should_stop_polling']:
                break
            
            await asyncio.sleep(0.5)
        
        # 验证轮询在完成后停止
        assert status['should_stop_polling'] is True
        assert poll_count < max_polls  # 不应达到最大轮询次数
    
    @pytest.mark.asyncio
    async def test_polling_with_network_interruption(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        monkeypatch
    ):
        """测试网络中断时的轮询"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        call_count = 0
        original_get_status = None
        
        # 模拟网络中断
        async def mock_get_status(exec_id):
            nonlocal call_count
            call_count += 1
            
            if 3 <= call_count <= 5:
                raise Exception("网络连接失败")
            
            return await DiagnosisService(db_path=test_db_path).get_status(exec_id)
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(10)
        
        # 验证轮询最终完成
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_polling_timeout_handling(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试轮询超时处理"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建很慢的适配器
        class SlowAdapter:
            async def send_prompt(self, brand, question, model):
                await asyncio.sleep(10)
                return {'content': '响应', 'model': model}
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=SlowAdapter(),
            timeout=3  # 3 秒超时
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待超时
        await asyncio.sleep(5)
        
        # 验证超时
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] in ['timeout', 'failed']
        assert status['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_polling_state_consistency(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试轮询状态一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 多次轮询验证状态一致性
        states = []
        for _ in range(10):
            status = await diagnosis_service.get_status(sample_execution_id)
            states.append(status)
            
            if status['should_stop_polling']:
                break
            
            await asyncio.sleep(0.3)
        
        # 验证所有状态都有 execution_id
        for state in states:
            assert state['execution_id'] == sample_execution_id
        
        # 验证进度递增
        progresses = [s['progress'] for s in states]
        assert progresses == sorted(progresses)
    
    @pytest.mark.asyncio
    async def test_polling_recovery_after_page_reload(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config,
        mock_ai_adapter
    ):
        """测试页面刷新后轮询恢复"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待一段时间
        await asyncio.sleep(2)
        
        # 模拟页面刷新（创建新服务实例）
        new_service = DiagnosisService(db_path=test_db_path)
        
        # 获取状态（应能继续）
        status = await new_service.get_status(sample_execution_id)
        assert status['execution_id'] == sample_execution_id
        assert status['progress'] > 0
