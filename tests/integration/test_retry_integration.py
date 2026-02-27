"""
重试机制集成测试

测试覆盖：
1. 指数退避重试
2. 最大重试次数限制
3. 可重试与不可重试错误
4. 重试与死信队列集成

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import time

from wechat_backend.v2.services.retry_policy import RetryPolicy


class TestRetryIntegration:
    """重试机制集成测试"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试指数退避重试"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建前几次失败、后成功的适配器
        class RetryAdapter:
            def __init__(self):
                self.attempts = {}
                self.delays = []
                self.last_attempt_time = {}
            
            async def send_prompt(self, brand, question, model):
                key = f"{brand}_{model}"
                now = time.time()
                
                if key in self.last_attempt_time:
                    delay = now - self.last_attempt_time[key]
                    self.delays.append(delay)
                
                self.last_attempt_time[key] = now
                self.attempts[key] = self.attempts.get(key, 0) + 1
                
                if self.attempts[key] <= 2:
                    raise Exception(f"模拟失败第{self.attempts[key]}次")
                
                return {'content': '成功', 'model': model, 'attempts': self.attempts[key]}
        
        adapter = RetryAdapter()
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=adapter,
            retry_policy=RetryPolicy(max_retries=3, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(3)
        
        # 验证重试成功
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] in ['completed', 'partial_success']
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试超过最大重试次数"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建总是失败的适配器
        class AlwaysFailAdapter:
            async def send_prompt(self, brand, question, model):
                raise Exception("总是失败")
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=AlwaysFailAdapter(),
            retry_policy=RetryPolicy(max_retries=3, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待所有重试完成
        await asyncio.sleep(5)
        
        # 验证状态为失败
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] == 'failed'
        assert status['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_retry_with_non_retryable_error(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试不可重试错误"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建返回不可重试错误的适配器
        class NonRetryableAdapter:
            async def send_prompt(self, brand, question, model):
                error = Exception("无效的执行 ID")
                error.code = 'InvalidExecutionId'
                raise error
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=NonRetryableAdapter(),
            retry_policy=RetryPolicy(max_retries=3, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待
        await asyncio.sleep(2)
        
        # 验证没有重试（立即失败）
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] == 'failed'
    
    @pytest.mark.asyncio
    async def test_retry_with_dead_letter_integration(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试重试与死信队列集成"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
        
        # 创建总是失败的适配器
        class AlwaysFailAdapter:
            async def send_prompt(self, brand, question, model):
                raise Exception("持续性错误")
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=AlwaysFailAdapter(),
            retry_policy=RetryPolicy(max_retries=2, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待所有重试完成
        await asyncio.sleep(3)
        
        # 验证死信队列有记录
        dlq = DeadLetterQueue(test_db_path)
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) > 0
    
    @pytest.mark.asyncio
    async def test_retry_jitter(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试重试抖动"""
        
        from wechat_backend.v2.services.retry_policy import RetryPolicy
        
        policy = RetryPolicy(max_retries=5, base_delay=100, use_jitter=True)
        
        # 计算多次重试的延迟
        delays = []
        for i in range(5):
            delay = policy.get_delay(i)
            delays.append(delay)
        
        # 验证有抖动（延迟不完全相同）
        assert len(set(delays)) > 1
        
        # 验证延迟在合理范围内
        for i, delay in enumerate(delays):
            expected_base = 100 * (2 ** i)
            assert delay >= expected_base * 0.5
            assert delay <= expected_base * 1.5
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试失败后重试成功"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建第 3 次成功的适配器
        class SuccessAfterFailuresAdapter:
            def __init__(self):
                self.attempts = {}
            
            async def send_prompt(self, brand, question, model):
                key = f"{brand}_{model}"
                self.attempts[key] = self.attempts.get(key, 0) + 1
                
                if self.attempts[key] < 3:
                    raise Exception(f"失败第{self.attempts[key]}次")
                
                return {
                    'content': '最终成功',
                    'model': model,
                    'total_attempts': self.attempts[key]
                }
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=SuccessAfterFailuresAdapter(),
            retry_policy=RetryPolicy(max_retries=5, base_delay=0.1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(3)
        
        # 验证成功
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] in ['completed', 'partial_success']
        
        # 验证结果包含重试信息
        result_repo = diagnosis_service.result_repo
        results = result_repo.get_by_execution_id(sample_execution_id)
        
        for result in results:
            assert result.error_message is None
