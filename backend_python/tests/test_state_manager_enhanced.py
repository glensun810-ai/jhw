"""
增强状态管理器单元测试

测试覆盖：
1. 状态变更日志记录
2. 状态验证方法
3. 强制回滚方法
4. 状态查询方法

@author: 系统架构组
@date: 2026-03-02
@version: 2.0.0
"""

import pytest
import sqlite3
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from wechat_backend.state_manager import (
    DiagnosisStateManager,
    StateChangeType,
    StateChangeRecord,
    get_state_manager,
    reset_state_manager
)


class TestStateChangeRecord:
    """StateChangeRecord 单元测试"""

    def test_state_change_record_creation(self):
        """测试状态变更记录创建"""
        record = StateChangeRecord(
            execution_id='test-123',
            change_type='update',
            old_status='init',
            old_stage='init',
            old_progress=0,
            new_status='running',
            new_stage='ai_fetching',
            new_progress=30,
            timestamp='2026-03-02T10:00:00',
            user_id='test-user',
            reason='测试更新'
        )
        
        assert record.execution_id == 'test-123'
        assert record.change_type == 'update'
        assert record.new_status == 'running'
        assert record.new_progress == 30
        assert record.reason == '测试更新'

    def test_state_change_record_to_dict(self):
        """测试转换为字典"""
        record = StateChangeRecord(
            execution_id='test-123',
            change_type='update',
            old_status='init',
            old_stage='init',
            old_progress=0,
            new_status='running',
            new_stage='ai_fetching',
            new_progress=30,
            timestamp='2026-03-02T10:00:00',
            user_id='test-user'
        )
        
        record_dict = record.to_dict()
        
        assert isinstance(record_dict, dict)
        assert record_dict['execution_id'] == 'test-123'
        assert record_dict['change_type'] == 'update'
        assert 'timestamp' in record_dict

    def test_state_change_record_to_json(self):
        """测试转换为 JSON"""
        record = StateChangeRecord(
            execution_id='test-123',
            change_type='update',
            old_status='init',
            old_stage='init',
            old_progress=0,
            new_status='running',
            new_stage='ai_fetching',
            new_progress=30,
            timestamp='2026-03-02T10:00:00',
            user_id='test-user'
        )
        
        json_str = record.to_json()
        
        assert isinstance(json_str, str)
        assert 'test-123' in json_str
        assert 'update' in json_str


class TestDiagnosisStateManager:
    """DiagnosisStateManager 增强版单元测试"""

    @pytest.fixture
    def execution_store(self):
        """创建测试用的执行状态存储"""
        return {}

    @pytest.fixture
    def state_manager(self, execution_store):
        """创建状态管理器实例"""
        reset_state_manager()
        return get_state_manager(execution_store)

    def test_init(self, state_manager, execution_store):
        """测试初始化"""
        assert state_manager.execution_store is execution_store
        assert state_manager.state_change_history == {}
        assert state_manager.state_snapshots == {}

    def test_update_state_records_history(self, state_manager):
        """测试状态更新记录历史"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 更新状态（Mock 数据库操作）
        with patch.object(state_manager, '_persist_state_change_to_db'):
            result = state_manager.update_state(
                execution_id=execution_id,
                status='running',
                stage='ai_fetching',
                progress=30,
                user_id='test-user',
                reason='测试更新'
            )
        
        assert result is True
        assert execution_id in state_manager.state_change_history
        assert len(state_manager.state_change_history[execution_id]) >= 1
        
        # 验证记录内容
        record = state_manager.state_change_history[execution_id][-1]
        assert record.change_type == StateChangeType.UPDATE.value
        assert record.new_status == 'running'
        assert record.new_progress == 30
        assert record.reason == '测试更新'

    def test_update_state_saves_snapshot(self, state_manager):
        """测试状态更新保存快照"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 更新状态
        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=30
            )
        
        # 验证快照已保存
        assert execution_id in state_manager.state_snapshots
        assert state_manager.state_snapshots[execution_id]['status'] == 'init'
        assert state_manager.state_snapshots[execution_id]['progress'] == 0

    def test_verify_state_consistency_consistent(self, state_manager):
        """测试状态验证 - 一致情况"""
        execution_id = 'test-123'
        
        # 初始化内存状态
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': False
        }
        
        # Mock 数据库返回一致的状态
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': 0
        }
        
        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )
        
        assert is_consistent is True
        assert len(details['differences']) == 0
        assert details['fixed'] is False

    def test_verify_state_consistency_inconsistent(self, state_manager):
        """测试状态验证 - 不一致情况"""
        execution_id = 'test-123'
        
        # 初始化内存状态
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': False
        }
        
        # Mock 数据库返回不一致的状态
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',  # 不一致
            'stage': 'completed',  # 不一致
            'progress': 100,  # 不一致
            'is_completed': 1
        }
        
        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )
        
        assert is_consistent is False
        assert len(details['differences']) > 0
        assert 'status' in details['differences'][0]

    def test_verify_state_consistency_auto_fix(self, state_manager):
        """测试状态验证 - 自动修复"""
        execution_id = 'test-123'
        
        # 初始化内存状态（错误状态）
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': False
        }
        
        # Mock 数据库返回正确状态
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': 1
        }
        
        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=True
            )
        
        # 注意：验证函数返回的是修复前的一致性状态
        # 修复后内存状态已更新，但返回值反映的是修复前的状态
        assert details['fixed'] is True
        # 验证内存状态已修复
        assert state_manager.execution_store[execution_id]['status'] == 'completed'
        assert state_manager.execution_store[execution_id]['progress'] == 100

    def test_rollback_to_snapshot(self, state_manager):
        """测试回滚到快照"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 更新状态（会保存快照）
        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=30
            )
        
        # 验证当前状态
        assert state_manager.execution_store[execution_id]['status'] == 'running'
        assert state_manager.execution_store[execution_id]['progress'] == 30
        
        # 回滚
        with patch.object(state_manager, '_persist_state_change_to_db'):
            result = state_manager.rollback_to_snapshot(
                execution_id=execution_id,
                user_id='test-user',
                reason='测试回滚'
            )
        
        assert result is True
        # 验证状态已回滚
        assert state_manager.execution_store[execution_id]['status'] == 'init'
        assert state_manager.execution_store[execution_id]['progress'] == 0
        # 验证快照已删除
        assert execution_id not in state_manager.state_snapshots

    def test_rollback_to_snapshot_no_snapshot(self, state_manager):
        """测试回滚 - 无快照情况"""
        execution_id = 'test-123'
        
        # 不保存快照，直接回滚
        result = state_manager.rollback_to_snapshot(execution_id=execution_id)
        
        assert result is False

    def test_rollback_to_state(self, state_manager):
        """测试回滚到指定状态"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30
        }
        
        # Mock 数据库
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {'id': 1}
        mock_repo.update_status = Mock()
        
        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            with patch.object(state_manager, '_persist_state_change_to_db'):
                result = state_manager.rollback_to_state(
                    execution_id=execution_id,
                    target_status='failed',
                    target_stage='failed',
                    target_progress=100,
                    reason='测试回滚到指定状态'
                )
        
        assert result is True
        # 验证状态已回滚
        assert state_manager.execution_store[execution_id]['status'] == 'failed'
        assert state_manager.execution_store[execution_id]['stage'] == 'failed'
        assert state_manager.execution_store[execution_id]['progress'] == 100

    def test_get_state_history(self, state_manager):
        """测试获取状态历史"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 多次更新状态
        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(execution_id=execution_id, status='running', progress=30)
            state_manager.update_state(execution_id=execution_id, status='completed', progress=100)
        
        # 获取历史
        history = state_manager.get_state_history(execution_id=execution_id, limit=10)
        
        assert len(history) >= 2
        assert isinstance(history, list)
        assert all('execution_id' in record for record in history)

    def test_get_state_change_summary(self, state_manager):
        """测试获取状态变更摘要"""
        execution_id = 'test-123'
        
        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 更新状态
        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(execution_id=execution_id, status='running', progress=30)
        
        # 获取摘要
        summary = state_manager.get_state_change_summary(execution_id=execution_id)
        
        assert summary['execution_id'] == execution_id
        assert summary['total_changes'] >= 1
        assert summary['first_change'] is not None
        assert summary['last_change'] is not None
        assert summary['current_status'] == 'running'

    def test_complete_execution(self, state_manager):
        """测试完成执行"""
        execution_id = 'test-123'

        # 初始化状态
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        # Mock 数据库 - 返回一致的状态
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': 1
        }
        mock_repo.update_status = Mock()

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            with patch('wechat_backend.state_manager.save_diagnosis_report'):
                with patch('wechat_backend.repositories.task_status_repository.save_task_status'):
                    result = state_manager.complete_execution(
                        execution_id=execution_id,
                        user_id='test-user',
                        brand_name='Test Brand',
                        competitor_brands=[],
                        selected_models=[],
                        custom_questions=[]
                    )

        assert result is True
        assert state_manager.execution_store[execution_id]['status'] == 'completed'
        assert state_manager.execution_store[execution_id]['progress'] == 100
        assert state_manager.execution_store[execution_id]['is_completed'] is True

    def test_get_state(self, state_manager):
        """测试获取状态"""
        execution_id = 'test-123'
        
        # 初始化状态
        expected_state = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30
        }
        state_manager.execution_store[execution_id] = expected_state.copy()
        
        # 获取状态
        state = state_manager.get_state(execution_id=execution_id)
        
        assert state is not None
        assert state['status'] == 'running'
        assert state['progress'] == 30
        # 验证返回的是拷贝
        assert state is not state_manager.execution_store[execution_id]

    def test_get_state_not_found(self, state_manager):
        """测试获取不存在状态"""
        state = state_manager.get_state(execution_id='non-existent')
        
        assert state is None


class TestStateChangeType:
    """StateChangeType 枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert StateChangeType.INIT.value == 'init'
        assert StateChangeType.UPDATE.value == 'update'
        assert StateChangeType.COMPLETE.value == 'complete'
        assert StateChangeType.FAIL.value == 'fail'
        assert StateChangeType.ROLLBACK.value == 'rollback'
        assert StateChangeType.VERIFY.value == 'verify'


class TestGlobalStateManager:
    """全局状态管理器测试"""

    def test_get_state_manager_singleton(self):
        """测试单例模式"""
        store1 = {}
        store2 = {}
        
        reset_state_manager()
        manager1 = get_state_manager(store1)
        manager2 = get_state_manager(store2)
        
        # 应该返回同一个实例
        assert manager1 is manager2

    def test_reset_state_manager(self):
        """测试重置状态管理器"""
        store = {}
        
        reset_state_manager()
        manager1 = get_state_manager(store)
        
        reset_state_manager()
        manager2 = get_state_manager(store)
        
        # 重置后应该创建新实例
        assert manager1 is not manager2


@pytest.mark.integration
class TestDiagnosisStateManagerIntegration:
    """状态管理器集成测试"""

    def test_full_state_lifecycle(self):
        """测试完整状态生命周期"""
        execution_store = {}
        reset_state_manager()
        state_manager = get_state_manager(execution_store)
        
        execution_id = 'integration-test-123'
        
        # 1. 初始化状态
        execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }
        
        # 2. 更新状态（Mock 数据库）
        with patch.object(state_manager, '_persist_state_change_to_db'):
            with patch('wechat_backend.state_manager.save_diagnosis_report'):
                state_manager.update_state(
                    execution_id=execution_id,
                    status='running',
                    stage='ai_fetching',
                    progress=30,
                    reason='开始 AI 调用'
                )
        
        # 3. 验证状态
        state = state_manager.get_state(execution_id)
        assert state['status'] == 'running'
        assert state['progress'] == 30
        
        # 4. 再次更新
        with patch.object(state_manager, '_persist_state_change_to_db'):
            with patch('wechat_backend.state_manager.save_diagnosis_report'):
                state_manager.update_state(
                    execution_id=execution_id,
                    status='completed',
                    progress=100,
                    reason='诊断完成'
                )
        
        # 5. 验证历史
        history = state_manager.get_state_history(execution_id=execution_id)
        assert len(history) >= 2
        
        # 6. 验证摘要
        summary = state_manager.get_state_change_summary(execution_id=execution_id)
        assert summary['total_changes'] >= 2
        assert summary['current_status'] == 'completed'


# ==================== 【验收标准专项测试】 ====================

class TestAcceptanceCriteria:
    """
    验收标准专项测试
    
    验收标准:
    ✅ 所有状态变更都有日志记录
    ✅ 能验证内存和数据库状态一致性
    ✅ 能回滚到指定状态
    """

    @pytest.fixture
    def execution_store(self):
        """创建测试用的执行状态存储"""
        return {}

    @pytest.fixture
    def state_manager(self, execution_store):
        """创建状态管理器实例"""
        reset_state_manager()
        return get_state_manager(execution_store)

    # ==================== 验收标准 1: 所有状态变更都有日志记录 ====================

    def test_acceptance_all_changes_logged_init(self, state_manager):
        """验收测试：初始化状态有日志记录"""
        execution_id = 'accept-test-1'
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                stage='ai_fetching',
                progress=10,
                user_id='user-123',
                reason='初始化 AI 调用'
            )

        # 验证日志记录
        history = state_manager.get_state_history(execution_id)
        assert len(history) >= 1
        record = history[-1]
        assert record['change_type'] == 'update'
        assert record['user_id'] == 'user-123'
        assert record['reason'] == '初始化 AI 调用'
        assert record['new_status'] == 'running'

    def test_acceptance_all_changes_logged_multiple_updates(self, state_manager):
        """验收测试：多次更新都有日志记录"""
        execution_id = 'accept-test-2'
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            # 第一次更新
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=30,
                reason='步骤 1'
            )
            # 第二次更新
            state_manager.update_state(
                execution_id=execution_id,
                status='analyzing',
                progress=60,
                reason='步骤 2'
            )
            # 第三次更新
            state_manager.update_state(
                execution_id=execution_id,
                status='completed',
                progress=100,
                reason='步骤 3'
            )

        # 验证所有更新都有记录
        history = state_manager.get_state_history(execution_id)
        assert len(history) >= 3

        # 验证每条记录的内容
        reasons = [record['reason'] for record in history]
        assert '步骤 1' in reasons
        assert '步骤 2' in reasons
        assert '步骤 3' in reasons

    def test_acceptance_all_changes_logged_fail_state(self, state_manager):
        """验收测试：失败状态也有日志记录"""
        execution_id = 'accept-test-3'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 50
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(
                execution_id=execution_id,
                status='failed',
                stage='failed',
                progress=0,
                error_message='测试错误',
                reason='AI 调用失败'
            )

        history = state_manager.get_state_history(execution_id)
        assert len(history) >= 1
        record = history[-1]
        assert record['change_type'] == 'update'
        assert record['new_status'] == 'failed'
        # 验证错误信息在日志记录中（通过 reason 或单独字段）
        assert record['reason'] == 'AI 调用失败'

    def test_acceptance_all_changes_logged_rollback(self, state_manager):
        """验收测试：回滚操作也有日志记录"""
        execution_id = 'accept-test-4'
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            # 先更新
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=50
            )
            # 回滚
            state_manager.rollback_to_snapshot(
                execution_id=execution_id,
                user_id='admin',
                reason='测试回滚日志'
            )

        history = state_manager.get_state_history(execution_id)
        # 至少有更新和回滚两条记录
        assert len(history) >= 2

        # 验证最后一条是回滚记录
        last_record = history[-1]
        assert last_record['change_type'] == 'rollback'
        assert last_record['user_id'] == 'admin'
        assert last_record['reason'] == '测试回滚日志'

    def test_acceptance_all_changes_logged_verify(self, state_manager):
        """验收测试：验证操作也有日志记录"""
        execution_id = 'accept-test-5'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 50
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 50,
            'is_completed': 0
        }

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            state_manager.verify_state_consistency(execution_id=execution_id)

        history = state_manager.get_state_history(execution_id)
        assert len(history) >= 1
        record = history[-1]
        assert record['change_type'] == 'verify'
        assert '验证' in record['reason']

    # ==================== 验收标准 2: 能验证内存和数据库状态一致性 ====================

    def test_acceptance_verify_consistent(self, state_manager):
        """验收测试：验证一致性的情况"""
        execution_id = 'verify-test-1'
        state_manager.execution_store[execution_id] = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': True
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': 1
        }

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )

        assert is_consistent is True
        assert len(details['differences']) == 0
        assert details['memory_state'] is not None
        assert details['db_state'] is not None

    def test_acceptance_verify_inconsistent_status(self, state_manager):
        """验收测试：验证状态不一致"""
        execution_id = 'verify-test-2'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 50,
            'is_completed': False
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',  # 不一致
            'stage': 'completed',
            'progress': 100,
            'is_completed': 1
        }

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )

        assert is_consistent is False
        assert any('status' in diff for diff in details['differences'])

    def test_acceptance_verify_inconsistent_progress(self, state_manager):
        """验收测试：验证进度不一致"""
        execution_id = 'verify-test-3'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': False
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 80,  # 不一致
            'is_completed': 0
        }

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )

        assert is_consistent is False
        assert any('progress' in diff for diff in details['differences'])

    def test_acceptance_verify_auto_fix(self, state_manager):
        """验收测试：验证并自动修复"""
        execution_id = 'verify-test-4'
        # 设置错误的内存状态
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 20,
            'is_completed': False
        }

        # 数据库是正确的状态
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100,
            'is_completed': 1
        }

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=True
            )

        # 验证修复后内存状态与数据库一致
        assert details['fixed'] is True
        assert state_manager.execution_store[execution_id]['status'] == 'completed'
        assert state_manager.execution_store[execution_id]['progress'] == 100

    def test_acceptance_verify_db_not_found(self, state_manager):
        """验收测试：验证时数据库不存在"""
        execution_id = 'verify-test-5'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'progress': 50
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = None

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            is_consistent, details = state_manager.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=False
            )

        assert is_consistent is False
        assert any('数据库' in diff for diff in details['differences'])

    def test_acceptance_verify_memory_not_found(self, state_manager):
        """验收测试：验证时内存不存在"""
        execution_id = 'non-existent'

        is_consistent, details = state_manager.verify_state_consistency(
            execution_id=execution_id,
            fix_if_inconsistent=False
        )

        assert is_consistent is False
        assert any('内存' in diff for diff in details['differences'])

    # ==================== 验收标准 3: 能回滚到指定状态 ====================

    def test_acceptance_rollback_to_snapshot(self, state_manager):
        """验收测试：回滚到快照"""
        execution_id = 'rollback-test-1'
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            # 更新到新状态
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=50
            )

            # 验证当前状态
            assert state_manager.execution_store[execution_id]['status'] == 'running'

            # 回滚到快照
            result = state_manager.rollback_to_snapshot(
                execution_id=execution_id,
                reason='测试回滚到快照'
            )

        assert result is True
        # 验证回到初始状态
        assert state_manager.execution_store[execution_id]['status'] == 'init'
        assert state_manager.execution_store[execution_id]['progress'] == 0

    def test_acceptance_rollback_to_specified_state(self, state_manager):
        """验收测试：回滚到指定状态"""
        execution_id = 'rollback-test-2'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'stage': 'ai_fetching',
            'progress': 50
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {'id': 1}
        mock_repo.update_status = Mock()

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            with patch.object(state_manager, '_persist_state_change_to_db'):
                result = state_manager.rollback_to_state(
                    execution_id=execution_id,
                    target_status='failed',
                    target_stage='failed',
                    target_progress=0,
                    reason='测试回滚到失败状态'
                )

        assert result is True
        assert state_manager.execution_store[execution_id]['status'] == 'failed'
        assert state_manager.execution_store[execution_id]['stage'] == 'failed'
        assert state_manager.execution_store[execution_id]['progress'] == 0

    def test_acceptance_rollback_to_previous_stage(self, state_manager):
        """验收测试：回滚到上一阶段"""
        execution_id = 'rollback-test-3'
        state_manager.execution_store[execution_id] = {
            'status': 'analyzing',
            'stage': 'analyzing',
            'progress': 80
        }

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = {'id': 1}
        mock_repo.update_status = Mock()

        with patch('wechat_backend.state_manager.DiagnosisReportRepository', return_value=mock_repo):
            with patch.object(state_manager, '_persist_state_change_to_db'):
                result = state_manager.rollback_to_state(
                    execution_id=execution_id,
                    target_status='running',
                    target_stage='ai_fetching',
                    target_progress=50,
                    reason='回滚到 AI 调用阶段'
                )

        assert result is True
        assert state_manager.execution_store[execution_id]['status'] == 'running'
        assert state_manager.execution_store[execution_id]['stage'] == 'ai_fetching'
        assert state_manager.execution_store[execution_id]['progress'] == 50

    def test_acceptance_rollback_no_snapshot(self, state_manager):
        """验收测试：无快照时回滚失败"""
        execution_id = 'rollback-test-4'
        state_manager.execution_store[execution_id] = {
            'status': 'running',
            'progress': 50
        }

        result = state_manager.rollback_to_snapshot(execution_id=execution_id)

        assert result is False

    def test_acceptance_rollback_invalid_execution_id(self, state_manager):
        """验收测试：回滚不存在的 execution_id"""
        result = state_manager.rollback_to_state(
            execution_id='non-existent',
            target_status='init',
            target_stage='init',
            target_progress=0
        )

        assert result is False

    def test_acceptance_rollback_logs_reason(self, state_manager):
        """验收测试：回滚日志记录原因"""
        execution_id = 'rollback-test-5'
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                progress=50
            )

            state_manager.rollback_to_snapshot(
                execution_id=execution_id,
                user_id='admin',
                reason='系统异常，需要回滚'
            )

        history = state_manager.get_state_history(execution_id)
        last_record = history[-1]
        assert last_record['change_type'] == 'rollback'
        assert last_record['reason'] == '系统异常，需要回滚'
        assert last_record['user_id'] == 'admin'

    def test_acceptance_full_rollback_workflow(self, state_manager):
        """验收测试：完整回滚流程"""
        execution_id = 'rollback-test-6'

        # 1. 初始化
        state_manager.execution_store[execution_id] = {
            'status': 'init',
            'stage': 'init',
            'progress': 0
        }

        with patch.object(state_manager, '_persist_state_change_to_db'):
            # 2. 多次更新
            state_manager.update_state(
                execution_id=execution_id,
                status='running',
                stage='ai_fetching',
                progress=30,
                reason='开始 AI 调用'
            )
            state_manager.update_state(
                execution_id=execution_id,
                status='analyzing',
                stage='analyzing',
                progress=70,
                reason='开始分析'
            )
            state_manager.update_state(
                execution_id=execution_id,
                status='completed',
                stage='completed',
                progress=100,
                reason='诊断完成'
            )

            # 3. 发现问题，回滚到分析阶段
            result = state_manager.rollback_to_state(
                execution_id=execution_id,
                target_status='analyzing',
                target_stage='analyzing',
                target_progress=70,
                reason='发现结果异常，重新分析'
            )

        assert result is True
        assert state_manager.execution_store[execution_id]['status'] == 'analyzing'
        assert state_manager.execution_store[execution_id]['progress'] == 70

        # 4. 验证历史记录包含所有操作
        history = state_manager.get_state_history(execution_id)
        change_types = [record['change_type'] for record in history]
        assert 'update' in change_types
        assert 'rollback' in change_types


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
