"""
死信队列集成测试

测试覆盖：
1. 失败任务入队
2. 死信队列处理
3. 重试后恢复
4. 优先级处理

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
from datetime import datetime

from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue


class TestDeadLetterIntegration:
    """死信队列集成测试"""
    
    @pytest.mark.asyncio
    async def test_failed_task_added_to_dead_letter(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试失败任务加入死信队列"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 模拟失败
        error = Exception("模拟任务失败")
        
        dlq.add_to_dead_letter(
            execution_id=sample_execution_id,
            task_type='diagnosis',
            error=error,
            task_context={'brand': '测试品牌', 'stage': 'ai_fetching'}
        )
        
        # 验证入队
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 1
        assert dead_letters[0]['error_type'] == 'Exception'
        assert dead_letters[0]['status'] == 'pending'
    
    @pytest.mark.asyncio
    async def test_dead_letter_processing(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试死信队列处理"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 添加死信
        dlq.add_to_dead_letter(
            execution_id=sample_execution_id,
            task_type='diagnosis',
            error=Exception("测试错误"),
            task_context={}
        )
        
        # 处理死信
        dlq.mark_as_resolved(
            execution_id=sample_execution_id,
            handled_by='test_user',
            resolution_notes='测试处理'
        )
        
        # 验证状态
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 1
        assert dead_letters[0]['status'] == 'resolved'
        assert dead_letters[0]['handled_by'] == 'test_user'
    
    @pytest.mark.asyncio
    async def test_dead_letter_retry_recovery(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试死信队列重试恢复"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 添加死信
        dlq.add_to_dead_letter(
            execution_id=sample_execution_id,
            task_type='diagnosis',
            error=Exception("临时错误"),
            task_context={}
        )
        
        # 标记为重试
        dlq.mark_for_retry(sample_execution_id)
        
        # 验证状态
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 1
        assert dead_letters[0]['status'] == 'pending'
        assert dead_letters[0]['retry_count'] == 1
    
    @pytest.mark.asyncio
    async def test_dead_letter_priority(
        self,
        test_db_path
    ):
        """测试死信队列优先级"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 添加不同优先级的死信
        dlq.add_to_dead_letter(
            execution_id='exec_low',
            task_type='diagnosis',
            error=Exception("低优先级"),
            task_context={},
            priority=1
        )
        
        dlq.add_to_dead_letter(
            execution_id='exec_high',
            task_type='diagnosis',
            error=Exception("高优先级"),
            task_context={},
            priority=10
        )
        
        # 获取所有死信（应按优先级排序）
        dead_letters = dlq.list_dead_letters()
        
        # 验证高优先级在前
        assert dead_letters[0]['execution_id'] == 'exec_high'
        assert dead_letters[0]['priority'] == 10
    
    @pytest.mark.asyncio
    async def test_dead_letter_with_diagnosis_service(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试诊断服务与死信队列集成"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 创建总是失败的适配器
        class AlwaysFailAdapter:
            async def send_prompt(self, brand, question, model):
                raise Exception("AI 平台不可用")
        
        diagnosis_service = DiagnosisService(
            db_path=test_db_path,
            ai_adapter=AlwaysFailAdapter()
        )
        
        # 发起诊断
        await diagnosis_service.start_diagnosis(
            execution_id=sample_execution_id,
            config=sample_diagnosis_config
        )
        
        # 等待失败
        await asyncio.sleep(3)
        
        # 验证死信队列有记录
        dlq = DeadLetterQueue(test_db_path)
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) > 0
    
    @pytest.mark.asyncio
    async def test_dead_letter_cleanup(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试死信队列清理"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 添加死信
        dlq.add_to_dead_letter(
            execution_id=sample_execution_id,
            task_type='diagnosis',
            error=Exception("测试"),
            task_context={}
        )
        
        # 清理已解决的死信
        dlq.cleanup_resolved()
        
        # 验证未解决的死信仍在
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 1
        
        # 解决后清理
        dlq.mark_as_resolved(sample_execution_id, 'test', '测试清理')
        dlq.cleanup_resolved()
        
        # 验证已清理
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 0
    
    @pytest.mark.asyncio
    async def test_dead_letter_statistics(
        self,
        test_db_path
    ):
        """测试死信队列统计"""
        
        dlq = DeadLetterQueue(test_db_path)
        
        # 添加多个死信
        for i in range(5):
            dlq.add_to_dead_letter(
                execution_id=f'exec_{i}',
                task_type='diagnosis',
                error=Exception(f"错误{i}"),
                task_context={}
            )
        
        # 解决部分
        for i in range(2):
            dlq.mark_as_resolved(f'exec_{i}', 'test', '测试解决')
        
        # 获取统计
        stats = dlq.get_statistics()
        
        assert stats['total'] == 5
        assert stats['pending'] == 3
        assert stats['resolved'] == 2
