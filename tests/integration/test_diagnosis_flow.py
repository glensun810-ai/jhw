"""
核心诊断流程集成测试

测试覆盖：
1. 完整诊断流程（成功场景）
2. 部分成功场景
3. 失败场景
4. 重试机制集成
5. 数据验证

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import json
from datetime import datetime

from wechat_backend.v2.services.diagnosis_service import DiagnosisService
from wechat_backend.v2.services.retry_policy import RetryPolicy
from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
from wechat_backend.v2.repositories.api_call_log_repository import APICallLogRepository


class TestDiagnosisFlow:
    """核心诊断流程集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_diagnosis_flow_success(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        mock_ai_adapter
    ):
        """测试完整诊断流程 - 成功场景"""
        
        # 1. 准备服务
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        # 2. 发起诊断
        task_info = await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        assert task_info['execution_id'] == sample_execution_id
        assert task_info['report_id'] is not None
        
        # 3. 等待完成（轮询）
        max_wait = 30  # 最多等待 30 秒
        start_time = datetime.now()
        status = None
        
        while (datetime.now() - start_time).seconds < max_wait:
            status = await diagnosis_service.get_status(sample_execution_id)
            
            if status['should_stop_polling']:
                break
            
            await asyncio.sleep(1)
        
        # 4. 验证状态
        assert status is not None
        assert status['status'] == 'completed'
        assert status['progress'] == 100
        assert status['should_stop_polling'] is True
        
        # 5. 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        assert report['report']['execution_id'] == sample_execution_id
        assert report['report']['status'] == 'completed'
        assert len(report['results']) > 0
        
        # 6. 验证数据库记录
        repo = DiagnosisRepository(test_db_path)
        db_report = repo.get_by_execution_id(sample_execution_id)
        assert db_report['status'] == 'completed'
        
        # 7. 验证结果表
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        expected_count = len(sample_diagnosis_config['brand_list']) * len(
            [m for m in sample_diagnosis_config['selectedModels'] if m['checked']]
        )
        assert len(results) == expected_count
        
        # 8. 验证日志表
        log_repo = APICallLogRepository(test_db_path)
        logs = log_repo.get_by_execution_id(sample_execution_id)
        assert len(logs) == expected_count
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_with_partial_success(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        flaky_ai_adapter
    ):
        """测试部分成功场景"""
        
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
        await asyncio.sleep(10)  # 等待足够时间
        
        # 获取状态
        status = await diagnosis_service.get_status(sample_execution_id)
        
        # 验证状态为部分成功或完成
        assert status['status'] in ['partial_success', 'completed']
        
        # 获取报告
        report = await diagnosis_service.get_report(sample_execution_id)
        
        # 验证部分结果存在
        if report['report']['status'] == 'partial_success':
            assert report['meta']['is_stub'] is True
            assert report['meta']['has_data'] is True
            assert report['meta']['successful_count'] > 0
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_with_retry(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试重试机制集成"""
        
        # 创建一个前两次失败、第三次成功的适配器
        class RetryTestAdapter:
            def __init__(self):
                self.attempts = {}
            
            async def send_prompt(self, brand, question, model):
                key = f"{brand}_{model}"
                self.attempts[key] = self.attempts.get(key, 0) + 1
                
                if self.attempts[key] <= 2:
                    raise Exception(f"模拟失败，第{self.attempts[key]}次尝试")
                
                return {
                    'content': f'成功响应，第{self.attempts[key]}次',
                    'model': model,
                    'latency_ms': 100
                }
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=RetryTestAdapter(),
            retry_policy=RetryPolicy(max_retries=3, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证所有调用最终成功
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        for result in results:
            assert result.error_message is None
        
        # 验证死信队列没有记录
        dlq = DeadLetterQueue(test_db_path)
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 0
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_with_all_failures(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        failing_ai_adapter
    ):
        """测试全部失败场景"""
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=failing_ai_adapter
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 获取状态
        status = await diagnosis_service.get_status(sample_execution_id)
        
        # 验证状态为失败
        assert status['status'] == 'failed'
        assert status['should_stop_polling'] is True
        
        # 获取报告（应为存根）
        report = await diagnosis_service.get_report(sample_execution_id)
        assert report['meta']['is_stub'] is True
        assert report['meta']['has_data'] is False
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_state_transitions(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        mock_ai_adapter
    ):
        """测试诊断流程中的状态流转"""
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 轮询并记录状态变化
        states = []
        max_polls = 20
        
        for _ in range(max_polls):
            status = await diagnosis_service.get_status(sample_execution_id)
            states.append(status['status'])
            
            if status['should_stop_polling']:
                break
            
            await asyncio.sleep(0.5)
        
        # 验证状态流转顺序
        assert 'initializing' in states
        assert 'ai_fetching' in states
        assert 'completed' in states
        
        # 验证最终状态
        assert states[-1] == 'completed'
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_with_custom_questions(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        mock_ai_adapter
    ):
        """测试自定义问题的诊断流程"""
        
        # 添加自定义问题
        sample_diagnosis_config['custom_question'] = '自定义测试问题'
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证结果包含自定义问题
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        for result in results:
            assert result.question == '自定义测试问题'
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_with_multiple_brands(
        self,
        test_db_path,
        sample_execution_id,
        mock_ai_adapter
    ):
        """测试多品牌诊断流程"""
        
        config = {
            'brand_list': ['品牌 A', '品牌 B', '品牌 C', '品牌 D'],
            'selectedModels': [
                {'name': 'deepseek', 'checked': True}
            ],
            'custom_question': '测试问题',
            'competitor_brands': [],
            'userOpenid': 'test_user',
            'userLevel': 'Premium'
        }
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证所有品牌都有结果
        result_repo = DiagnosisResultRepository(test_db_path)
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        brands_in_results = set(r.brand for r in results)
        assert brands_in_results == set(config['brand_list'])
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_report_data_integrity(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试诊断报告数据完整性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        exec_id = setup_completed_diagnosis['execution_id']
        
        # 获取报告
        report = await diagnosis_service.get_report(exec_id)
        
        # 验证报告结构
        assert 'report' in report
        assert 'results' in report
        assert 'analysis' in report
        assert 'meta' in report
        
        # 验证基本信息
        assert report['report']['execution_id'] == exec_id
        assert report['report']['status'] == 'completed'
        
        # 验证结果数量
        assert len(report['results']) > 0
        
        # 验证每条结果的必要字段
        for result in report['results']:
            assert 'brand' in result
            assert 'question' in result
            assert 'model' in result
            assert 'response' in result
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_api_call_logging(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id,
        mock_ai_adapter
    ):
        """测试 API 调用日志记录"""
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=mock_ai_adapter
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证日志记录
        log_repo = APICallLogRepository(test_db_path)
        logs = log_repo.get_by_execution_id(sample_execution_id)
        
        assert len(logs) > 0
        
        # 验证每条日志的字段
        for log in logs:
            assert log.execution_id == sample_execution_id
            assert log.brand is not None
            assert log.question is not None
            assert log.model is not None
            assert log.response_data is not None
    
    @pytest.mark.asyncio
    async def test_diagnosis_flow_timeout_handling(
        self,
        test_db_path,
        sample_diagnosis_config,
        sample_execution_id
    ):
        """测试超时处理"""
        
        # 创建一个很慢的适配器
        class SlowAdapter:
            async def send_prompt(self, brand, question, model):
                await asyncio.sleep(10)  # 很慢
                return {'content': '响应', 'model': model}
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=SlowAdapter(),
            timeout=2  # 2 秒超时
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待超时
        await asyncio.sleep(5)
        
        # 获取状态
        status = await diagnosis_service.get_status(sample_execution_id)
        
        # 验证超时状态
        assert status['status'] in ['timeout', 'failed']
        assert status['should_stop_polling'] is True
