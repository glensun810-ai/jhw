"""
诊断状态机单元测试

测试覆盖率目标：> 90%

测试范围:
1. 正常流转测试：所有合法的状态流转路径
2. 非法流转测试：非法事件应该返回 False
3. 持久化测试：状态更新后数据库记录正确
4. 边界条件测试：进度更新、终态判断等

作者：系统架构组
日期：2026-02-27
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from wechat_backend.v2.state_machine.states import DiagnosisState
from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine
from wechat_backend.v2.exceptions import DiagnosisStateError


# ==================== Fixture ====================

@pytest.fixture
def mock_repository():
    """模拟数据仓库"""
    repo = Mock()
    repo.update_state = Mock(return_value=True)
    return repo


@pytest.fixture
def state_machine(mock_repository):
    """创建状态机实例（带模拟仓库）"""
    return DiagnosisStateMachine(
        execution_id='test-execution-123',
        repository=mock_repository,
    )


# ==================== 初始化测试 ====================

class TestStateMachineInitialization:
    """状态机初始化测试"""
    
    def test_init_with_valid_execution_id(self, mock_repository):
        """测试使用有效的 execution_id 初始化"""
        sm = DiagnosisStateMachine(
            execution_id='test-123',
            repository=mock_repository,
        )
        
        assert sm.execution_id == 'test-123'
        assert sm.get_current_state() == DiagnosisState.INITIALIZING
        assert sm.get_progress() == 0
        assert sm.should_stop_polling() is False
        assert sm.is_terminal_state() is False
    
    def test_init_with_empty_execution_id(self, mock_repository):
        """测试使用空的 execution_id 初始化"""
        with pytest.raises(ValueError, match='execution_id 必须是非空字符串'):
            DiagnosisStateMachine(
                execution_id='',
                repository=mock_repository,
            )
    
    def test_init_with_none_execution_id(self, mock_repository):
        """测试使用 None 的 execution_id 初始化"""
        with pytest.raises(ValueError, match='execution_id 必须是非空字符串'):
            DiagnosisStateMachine(
                execution_id=None,
                repository=mock_repository,
            )
    
    def test_init_without_repository(self):
        """测试不使用 repository 初始化"""
        sm = DiagnosisStateMachine(execution_id='test-123')
        
        assert sm.execution_id == 'test-123'
        assert sm.get_current_state() == DiagnosisState.INITIALIZING
        # 没有 repository 时，persist_state 应该不抛异常
        sm.persist_state()  # 应该只记录警告日志


# ==================== 正常流转测试 ====================

class TestNormalTransitions:
    """正常状态流转测试"""
    
    def test_initializing_to_ai_fetching(self, state_machine, mock_repository):
        """测试 INITIALIZING -> AI_FETCHING"""
        result = state_machine.transition('succeed', progress=10)
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.AI_FETCHING
        assert state_machine.get_progress() == 10
        assert state_machine.should_stop_polling() is False
        
        # 验证持久化被调用
        mock_repository.update_state.assert_called_once()
    
    def test_ai_fetching_to_analyzing_all_complete(self, state_machine, mock_repository):
        """测试 AI_FETCHING -> ANALYZING (all_complete)"""
        # 先流转到 AI_FETCHING
        state_machine.transition('succeed', progress=10)
        
        # 再流转到 ANALYZING
        result = state_machine.transition('all_complete', progress=90)
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.ANALYZING
        assert state_machine.get_progress() == 90
    
    def test_ai_fetching_to_analyzing_partial_complete(self, state_machine, mock_repository):
        """测试 AI_FETCHING -> ANALYZING (partial_complete)"""
        state_machine.transition('succeed', progress=10)
        result = state_machine.transition('partial_complete', progress=80)
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.ANALYZING
        assert state_machine.get_progress() == 80
    
    def test_analyzing_to_completed(self, state_machine, mock_repository):
        """测试 ANALYZING -> COMPLETED"""
        state_machine.transition('succeed', progress=10)  # INITIALIZING -> AI_FETCHING
        state_machine.transition('all_complete', progress=90)  # AI_FETCHING -> ANALYZING
        
        result = state_machine.transition('succeed', progress=100)
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.COMPLETED
        assert state_machine.get_progress() == 100
        assert state_machine.should_stop_polling() is True
        assert state_machine.is_terminal_state() is True
    
    def test_analyzing_to_partial_success(self, state_machine, mock_repository):
        """测试 ANALYZING -> PARTIAL_SUCCESS"""
        state_machine.transition('succeed', progress=10)
        state_machine.transition('all_complete', progress=90)
        
        result = state_machine.transition('partial_succeed', progress=95)
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.PARTIAL_SUCCESS
        assert state_machine.should_stop_polling() is True
        assert state_machine.is_terminal_state() is True
    
    def test_full_success_path(self, state_machine, mock_repository):
        """测试完整成功路径"""
        # INITIALIZING -> AI_FETCHING
        state_machine.transition('succeed', progress=10)
        assert state_machine.get_current_state() == DiagnosisState.AI_FETCHING
        
        # AI_FETCHING -> ANALYZING
        state_machine.transition('all_complete', progress=90)
        assert state_machine.get_current_state() == DiagnosisState.ANALYZING
        
        # ANALYZING -> COMPLETED
        state_machine.transition('succeed', progress=100)
        assert state_machine.get_current_state() == DiagnosisState.COMPLETED
        assert state_machine.get_progress() == 100


# ==================== 失败流转测试 ====================

class TestFailureTransitions:
    """失败状态流转测试"""
    
    def test_initializing_to_failed(self, state_machine, mock_repository):
        """测试 INITIALIZING -> FAILED"""
        result = state_machine.transition('fail')
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.FAILED
        assert state_machine.should_stop_polling() is True
        assert state_machine.is_terminal_state() is True
    
    def test_ai_fetching_to_failed_all_fail(self, state_machine, mock_repository):
        """测试 AI_FETCHING -> FAILED (all_fail)"""
        state_machine.transition('succeed', progress=10)
        result = state_machine.transition('all_fail')
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.FAILED
        assert state_machine.should_stop_polling() is True
    
    def test_ai_fetching_to_timeout(self, state_machine, mock_repository):
        """测试 AI_FETCHING -> TIMEOUT"""
        state_machine.transition('succeed', progress=10)
        result = state_machine.transition('timeout')
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.TIMEOUT
        assert state_machine.should_stop_polling() is True
    
    def test_analyzing_to_failed(self, state_machine, mock_repository):
        """测试 ANALYZING -> FAILED"""
        state_machine.transition('succeed', progress=10)
        state_machine.transition('all_complete', progress=90)
        result = state_machine.transition('fail')
        
        assert result is True
        assert state_machine.get_current_state() == DiagnosisState.FAILED


# ==================== 非法流转测试 ====================

class TestIllegalTransitions:
    """非法状态流转测试"""
    
    def test_invalid_event(self, state_machine, mock_repository):
        """测试非法事件"""
        result = state_machine.transition('invalid_event')
        
        assert result is False
        assert state_machine.get_current_state() == DiagnosisState.INITIALIZING
    
    def test_terminal_state_transition_attempt(self, state_machine, mock_repository):
        """测试终态尝试流转"""
        # 先流转到终态
        state_machine.transition('succeed', progress=10)
        state_machine.transition('all_complete', progress=90)
        state_machine.transition('succeed', progress=100)
        
        assert state_machine.get_current_state() == DiagnosisState.COMPLETED
        
        # 尝试从终态流转
        result = state_machine.transition('succeed', progress=100)
        
        assert result is False
        assert state_machine.get_current_state() == DiagnosisState.COMPLETED
    
    def test_skip_state(self, state_machine, mock_repository):
        """测试跳过状态（非法）"""
        # 尝试从 INITIALIZING 直接到 ANALYZING（跳过 AI_FETCHING）
        result = state_machine.transition('all_complete')
        
        assert result is False
        assert state_machine.get_current_state() == DiagnosisState.INITIALIZING


# ==================== 进度更新测试 ====================

class TestProgressUpdate:
    """进度更新测试"""
    
    def test_update_progress_valid(self, state_machine, mock_repository):
        """测试有效的进度更新"""
        state_machine.update_progress(50)
        assert state_machine.get_progress() == 50
    
    def test_update_progress_zero(self, state_machine, mock_repository):
        """测试进度为 0"""
        state_machine.update_progress(0)
        assert state_machine.get_progress() == 0
    
    def test_update_progress_hundred(self, state_machine, mock_repository):
        """测试进度为 100"""
        state_machine.update_progress(100)
        assert state_machine.get_progress() == 100
    
    def test_update_progress_negative(self, state_machine):
        """测试负数进度"""
        with pytest.raises(ValueError, match='进度必须在 0-100 之间'):
            state_machine.update_progress(-1)
    
    def test_update_progress_exceed_100(self, state_machine):
        """测试进度超过 100"""
        with pytest.raises(ValueError, match='进度必须在 0-100 之间'):
            state_machine.update_progress(101)
    
    def test_update_progress_invalid_type(self, state_machine):
        """测试进度类型错误"""
        with pytest.raises(ValueError, match='进度必须是整数'):
            state_machine.update_progress("50")  # type: ignore
    
    def test_progress_decrease_warning(self, state_machine, mock_repository, caplog):
        """测试进度减少（应该记录警告）"""
        state_machine.update_progress(50)
        state_machine.update_progress(30)  # 减少
        
        assert state_machine.get_progress() == 30
        # 应该记录警告日志
        assert 'progress_decreased' in caplog.text


# ==================== 终态判断测试 ====================

class TestTerminalState:
    """终态判断测试"""
    
    @pytest.mark.parametrize(
        'state,expected_is_terminal,expected_should_stop',
        [
            (DiagnosisState.INITIALIZING, False, False),
            (DiagnosisState.AI_FETCHING, False, False),
            (DiagnosisState.ANALYZING, False, False),
            (DiagnosisState.COMPLETED, True, True),
            (DiagnosisState.PARTIAL_SUCCESS, True, True),
            (DiagnosisState.FAILED, True, True),
            (DiagnosisState.TIMEOUT, True, True),
        ]
    )
    def test_state_properties(
        self,
        state: DiagnosisState,
        expected_is_terminal: bool,
        expected_should_stop: bool,
    ):
        """测试各状态的属性"""
        assert state.is_terminal == expected_is_terminal
        assert state.should_stop_polling == expected_should_stop


# ==================== 持久化测试 ====================

class TestPersistence:
    """持久化测试"""
    
    def test_persist_state_calls_repository(self, state_machine, mock_repository):
        """测试 persist_state 调用 repository"""
        state_machine.transition('succeed', progress=10)
        
        # 验证 update_state 被调用
        assert mock_repository.update_state.called
        
        # 验证调用参数
        call_args = mock_repository.update_state.call_args
        assert call_args[1]['status'] == 'ai_fetching'
        assert call_args[1]['progress'] == 10
        assert call_args[1]['stage'] == 'ai_fetching'
    
    def test_persist_state_without_repository(self, caplog):
        """测试没有 repository 时的持久化"""
        sm = DiagnosisStateMachine(execution_id='test-123')
        sm.persist_state()  # 不应该抛异常
        
        # 应该记录警告日志
        assert 'no_repository' in caplog.text
    
    def test_persist_state_repository_error(self, mock_repository, caplog):
        """测试 repository 抛错时的处理"""
        from wechat_backend.v2.exceptions import DatabaseError
        
        mock_repository.update_state.side_effect = Exception("DB error")
        sm = DiagnosisStateMachine(execution_id='test-123', repository=mock_repository)
        
        with pytest.raises(DatabaseError, match='状态持久化失败'):
            sm.persist_state()


# ==================== 元数据测试 ====================

class TestMetadata:
    """元数据测试"""
    
    def test_transition_with_metadata(self, state_machine, mock_repository):
        """测试带元数据的流转"""
        state_machine.transition(
            'succeed',
            progress=10,
            error_message='Test error',
            results_count=5,
        )
        
        metadata = state_machine.get_metadata()
        assert metadata['error_message'] == 'Test error'
        assert metadata['results_count'] == 5
        assert 'last_event' in metadata
        assert 'last_transition_time' in metadata
    
    def test_get_metadata_returns_copy(self, state_machine):
        """测试 get_metadata 返回副本"""
        metadata1 = state_machine.get_metadata()
        metadata1['test'] = 'value'
        
        metadata2 = state_machine.get_metadata()
        assert 'test' not in metadata2


# ==================== 工具方法测试 ====================

class TestUtilityMethods:
    """工具方法测试"""
    
    def test_to_dict(self, state_machine):
        """测试 to_dict 方法"""
        state_machine.transition('succeed', progress=10)
        
        result = state_machine.to_dict()
        
        assert result['execution_id'] == 'test-execution-123'
        assert result['status'] == 'ai_fetching'
        assert result['stage'] == 'ai_fetching'
        assert result['progress'] == 10
        assert result['is_completed'] is False
        assert result['should_stop_polling'] is False
        assert result['is_terminal'] is False
        assert 'metadata' in result
    
    def test_str_representation(self, state_machine):
        """测试字符串表示"""
        result = str(state_machine)
        
        assert 'test-execution-123' in result
        assert 'initializing' in result
    
    def test_repr_representation(self, state_machine):
        """测试详细字符串表示"""
        result = repr(state_machine)
        
        assert 'test-execution-123' in result
        assert 'INITIALIZING' in result
    
    def test_reset(self, state_machine, mock_repository):
        """测试 reset 方法"""
        state_machine.transition('succeed', progress=10)
        state_machine.reset()
        
        assert state_machine.get_current_state() == DiagnosisState.INITIALIZING
        assert state_machine.get_progress() == 0
        assert state_machine.get_metadata() == {}


# ==================== 状态枚举测试 ====================

class TestDiagnosisStateEnum:
    """状态枚举测试"""
    
    def test_state_values(self):
        """测试状态值"""
        assert DiagnosisState.INITIALIZING.value == 'initializing'
        assert DiagnosisState.AI_FETCHING.value == 'ai_fetching'
        assert DiagnosisState.ANALYZING.value == 'analyzing'
        assert DiagnosisState.COMPLETED.value == 'completed'
        assert DiagnosisState.PARTIAL_SUCCESS.value == 'partial_success'
        assert DiagnosisState.FAILED.value == 'failed'
        assert DiagnosisState.TIMEOUT.value == 'timeout'
    
    def test_is_terminal_property(self):
        """测试 is_terminal 属性"""
        assert DiagnosisState.INITIALIZING.is_terminal is False
        assert DiagnosisState.AI_FETCHING.is_terminal is False
        assert DiagnosisState.ANALYZING.is_terminal is False
        assert DiagnosisState.COMPLETED.is_terminal is True
        assert DiagnosisState.PARTIAL_SUCCESS.is_terminal is True
        assert DiagnosisState.FAILED.is_terminal is True
        assert DiagnosisState.TIMEOUT.is_terminal is True
    
    def test_should_stop_polling_property(self):
        """测试 should_stop_polling 属性"""
        assert DiagnosisState.INITIALIZING.should_stop_polling is False
        assert DiagnosisState.AI_FETCHING.should_stop_polling is False
        assert DiagnosisState.ANALYZING.should_stop_polling is False
        assert DiagnosisState.COMPLETED.should_stop_polling is True
        assert DiagnosisState.PARTIAL_SUCCESS.should_stop_polling is True
        assert DiagnosisState.FAILED.should_stop_polling is True
        assert DiagnosisState.TIMEOUT.should_stop_polling is True
    
    def test_is_completed_property(self):
        """测试 is_completed 属性"""
        assert DiagnosisState.INITIALIZING.is_completed is False
        assert DiagnosisState.AI_FETCHING.is_completed is False
        assert DiagnosisState.ANALYZING.is_completed is False
        assert DiagnosisState.COMPLETED.is_completed is True
        assert DiagnosisState.PARTIAL_SUCCESS.is_completed is True
        assert DiagnosisState.FAILED.is_completed is False
        assert DiagnosisState.TIMEOUT.is_completed is False


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=wechat_backend.v2.state_machine', '--cov-report=html'])
