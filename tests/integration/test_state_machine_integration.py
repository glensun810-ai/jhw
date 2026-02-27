"""
状态机集成测试

测试覆盖：
1. 状态流转与超时集成
2. 状态持久化一致性
3. 状态机与死信队列集成
4. 非法状态流转处理

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine, DiagnosisState
from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue


class TestStateMachineIntegration:
    """状态机集成测试"""
    
    @pytest.mark.asyncio
    async def test_state_transitions_with_timeout(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试状态机与超时机制的集成"""
        
        from wechat_backend.v2.services.timeout_service import TimeoutManager
        
        # 创建状态机
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 初始化状态
        state_machine.transition('succeed')
        
        # 创建超时管理器
        timeout_manager = TimeoutManager()
        
        # 定义超时回调
        async def on_timeout(exec_id):
            state_machine.transition('timeout')
        
        # 启动超时计时器（1 秒超时用于测试）
        timeout_manager.start_timer(
            execution_id=sample_execution_id,
            on_timeout=on_timeout,
            timeout_seconds=1
        )
        
        # 等待超时
        await asyncio.sleep(2)
        
        # 验证状态变为超时
        assert state_machine.current_state == DiagnosisState.TIMEOUT
        
        # 验证数据库状态
        repo = DiagnosisRepository(test_db_path)
        db_record = repo.get_by_execution_id(sample_execution_id)
        assert db_record['status'] == 'timeout'
        assert db_record['should_stop_polling'] is True
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_service_boundaries(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试状态在不同服务间的持久化一致性"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        # 诊断服务更新状态
        diagnosis_service = DiagnosisService(db_path=test_db_path)
        
        # 模拟创建任务
        repo = DiagnosisRepository(test_db_path)
        repo.create_report(
            execution_id=sample_execution_id,
            user_id='test_user',
            brand_name='测试品牌',
            config=sample_diagnosis_config
        )
        
        # 更新为运行中
        await diagnosis_service.update_status(
            sample_execution_id,
            status='ai_fetching',
            progress=50
        )
        
        # 通过状态机直接读取
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        assert state_machine.current_state == DiagnosisState.AI_FETCHING
        assert state_machine.progress == 50
        
        # 通过状态机更新
        state_machine.transition('all_complete', progress=100)
        
        # 通过服务读取
        status = await diagnosis_service.get_status(sample_execution_id)
        assert status['status'] == 'analyzing'
        assert status['progress'] == 100
    
    def test_state_machine_with_dead_letter_integration(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试状态机与死信队列的集成"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 模拟失败
        try:
            raise Exception("模拟致命错误")
        except Exception as e:
            # 添加到死信队列
            dlq = DeadLetterQueue(test_db_path)
            dlq.add_to_dead_letter(
                execution_id=sample_execution_id,
                task_type='state_machine',
                error=e,
                task_context={'state': 'analyzing'}
            )
            
            # 更新状态为失败
            state_machine.transition('fail', error_message=str(e))
        
        # 验证状态
        assert state_machine.current_state == DiagnosisState.FAILED
        
        # 验证死信队列
        dead_letters = dlq.list_dead_letters(execution_id=sample_execution_id)
        assert len(dead_letters) == 1
        assert dead_letters[0]['error_type'] == 'Exception'
    
    def test_state_machine_illegal_transition(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试非法状态流转处理"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 尝试非法流转（从 initializing 直接到 completed）
        result = state_machine.transition('complete')
        
        # 验证流转失败
        assert result is False
        
        # 验证状态未变
        assert state_machine.current_state == DiagnosisState.INITIALIZING
    
    @pytest.mark.asyncio
    async def test_state_machine_valid_transitions(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试合法状态流转"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 初始化 -> AI 获取
        result = state_machine.transition('succeed')
        assert result is True
        assert state_machine.current_state == DiagnosisState.AI_FETCHING
        
        # AI 获取 -> 分析
        result = state_machine.transition('all_complete')
        assert result is True
        assert state_machine.current_state == DiagnosisState.ANALYZING
        
        # 分析 -> 完成
        result = state_machine.transition('succeed')
        assert result is True
        assert state_machine.current_state == DiagnosisState.COMPLETED
        
        # 验证数据库状态
        repo = DiagnosisRepository(test_db_path)
        db_record = repo.get_by_execution_id(sample_execution_id)
        assert db_record['status'] == 'completed'
        assert db_record['should_stop_polling'] is True
    
    def test_state_machine_partial_success(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试部分成功状态流转"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 流转到 AI 获取
        state_machine.transition('succeed')
        
        # 部分完成
        result = state_machine.transition('partial_succeed')
        assert result is True
        assert state_machine.current_state == DiagnosisState.PARTIAL_SUCCESS
        
        # 验证数据库
        repo = DiagnosisRepository(test_db_path)
        db_record = repo.get_by_execution_id(sample_execution_id)
        assert db_record['status'] == 'partial_success'
        assert db_record['should_stop_polling'] is True
    
    def test_state_machine_progress_update(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试进度更新"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 更新进度
        state_machine.transition('succeed', progress=30)
        assert state_machine.progress == 30
        
        state_machine.transition('all_complete', progress=60)
        assert state_machine.progress == 60
        
        state_machine.transition('succeed', progress=100)
        assert state_machine.progress == 100
        
        # 验证数据库进度
        repo = DiagnosisRepository(test_db_path)
        db_record = repo.get_by_execution_id(sample_execution_id)
        assert db_record['progress'] == 100
    
    def test_state_machine_metadata_persistence(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试元数据持久化"""
        
        state_machine = DiagnosisStateMachine(
            execution_id=sample_execution_id,
            db_path=test_db_path
        )
        
        # 添加元数据
        state_machine.transition('succeed', results_count=10, error_message=None)
        
        # 验证元数据
        assert state_machine.metadata['results_count'] == 10
        
        # 验证数据库
        repo = DiagnosisRepository(test_db_path)
        db_record = repo.get_by_execution_id(sample_execution_id)
        metadata = db_record.get('metadata')
        if metadata:
            assert '"results_count": 10' in metadata or "'results_count': 10" in metadata
