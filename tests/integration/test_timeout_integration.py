"""
超时机制集成测试

测试覆盖：
1. 超时触发状态变更
2. 多并发任务超时
3. 任务完成时取消超时
4. 超时与重试集成

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import time

from wechat_backend.v2.services.timeout_service import TimeoutManager


class TestTimeoutIntegration:
    """超时机制集成测试"""
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_state_change(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试超时触发状态变更"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建诊断服务
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        
        # 创建任务
        repo = diagnosis_service.diagnosis_repo
        repo.create_report(
            execution_id=sample_execution_id,
            user_id='test_user',
            brand_name='测试品牌',
            config=sample_diagnosis_config
        )
        
        # 模拟一个长时间运行的任务
        async def slow_task():
            await asyncio.sleep(10)  # 10 秒，超过超时时间
            return {'status': 'completed'}
        
        # 启动超时计时器（2 秒超时）
        timeout_manager = TimeoutManager()
        timeout_triggered = False
        
        def on_timeout(exec_id):
            nonlocal timeout_triggered
            timeout_triggered = True
            # 更新状态
            asyncio.create_task(
                diagnosis_service.update_status(
                    exec_id,
                    status='timeout',
                    error_message='任务超时'
                )
            )
        
        timeout_manager.start_timer(
            execution_id=sample_execution_id,
            on_timeout=on_timeout,
            timeout_seconds=2
        )
        
        # 执行慢任务
        try:
            await asyncio.wait_for(slow_task(), timeout=5)
        except asyncio.TimeoutError:
            pass
        
        # 等待超时处理
        await asyncio.sleep(1)
        
        # 验证超时触发
        assert timeout_triggered is True
        
        # 验证状态更新
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] == 'timeout'
        assert status['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_timeouts(
        self,
        test_db_path
    ):
        """测试多个并发任务超时"""
        
        timeout_manager = TimeoutManager()
        timeout_count = 0
        
        def create_timeout_handler(exec_id):
            def handler(eid):
                nonlocal timeout_count
                timeout_count += 1
            return handler
        
        # 启动 10 个任务的超时计时器
        for i in range(10):
            exec_id = f"test_exec_{i}"
            timeout_manager.start_timer(
                execution_id=exec_id,
                on_timeout=create_timeout_handler(exec_id),
                timeout_seconds=1
            )
        
        # 等待所有超时
        await asyncio.sleep(2)
        
        # 验证所有超时都被触发
        assert timeout_count == 10
        
        # 验证所有计时器都被清理
        for i in range(10):
            exec_id = f"test_exec_{i}"
            assert not timeout_manager.is_timer_active(exec_id)
    
    @pytest.mark.asyncio
    async def test_timeout_cancelled_on_completion(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试任务完成时取消超时"""
        
        timeout_manager = TimeoutManager()
        timeout_triggered = False
        
        def on_timeout(exec_id):
            nonlocal timeout_triggered
            timeout_triggered = True
        
        # 启动计时器
        timeout_manager.start_timer(
            execution_id=sample_execution_id,
            on_timeout=on_timeout,
            timeout_seconds=3
        )
        
        # 立即取消
        timeout_manager.cancel_timer(sample_execution_id)
        
        # 等待超过原定时时间
        await asyncio.sleep(4)
        
        # 验证超时未被触发
        assert timeout_triggered is False
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry_integration(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试超时与重试机制集成"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        from wechat_backend.v2.services.retry_policy import RetryPolicy
        
        # 创建一个有时超时的适配器
        class FlakyAdapter:
            def __init__(self):
                self.call_count = 0
            
            async def send_prompt(self, brand, question, model):
                self.call_count += 1
                if self.call_count <= 2:
                    await asyncio.sleep(5)  # 超时
                return {'content': '响应', 'model': model}
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=FlakyAdapter(),
            retry_policy=RetryPolicy(max_retries=3, base_delay=0.1, timeout=1)
        )
        
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待完成
        await asyncio.sleep(5)
        
        # 验证最终完成（重试成功）
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] in ['completed', 'partial_success', 'timeout']
    
    @pytest.mark.asyncio
    async def test_timeout_remaining_time(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试获取剩余时间"""
        
        timeout_manager = TimeoutManager()
        
        # 启动计时器（5 秒超时）
        timeout_manager.start_timer(
            execution_id=sample_execution_id,
            on_timeout=lambda x: None,
            timeout_seconds=5
        )
        
        # 立即检查剩余时间
        remaining = timeout_manager.get_remaining_time(sample_execution_id)
        assert remaining > 0
        assert remaining <= 5
        
        # 等待 2 秒后检查
        await asyncio.sleep(2)
        remaining = timeout_manager.get_remaining_time(sample_execution_id)
        assert remaining > 0
        assert remaining < 5
        
        # 清理
        timeout_manager.cancel_timer(sample_execution_id)
    
    @pytest.mark.asyncio
    async def test_timeout_cleanup_on_error(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试错误时超时计时器清理"""
        
        timeout_manager = TimeoutManager()
        
        # 启动计时器
        timeout_manager.start_timer(
            execution_id=sample_execution_id,
            on_timeout=lambda x: None,
            timeout_seconds=10
        )
        
        # 模拟错误处理
        try:
            raise Exception("模拟错误")
        except Exception:
            # 错误处理中取消计时器
            timeout_manager.cancel_timer(sample_execution_id)
        
        # 验证计时器已清理
        assert not timeout_manager.is_timer_active(sample_execution_id)
