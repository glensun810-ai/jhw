"""
诊断事务管理器测试模块

测试场景：
1. 正常提交事务
2. 异常触发回滚
3. 部分操作失败回滚
4. 并发事务隔离

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from wechat_backend.services.diagnosis_transaction import (
    DiagnosisTransaction,
    transaction_context,
    OperationType
)


class TestDiagnosisTransaction:
    """诊断事务管理器测试类"""

    def setup_method(self):
        """每个测试前的准备工作"""
        self.execution_id = str(uuid.uuid4())
        self.execution_store = {}
        self.user_id = "test_user"
        self.config = {
            'brand_name': '测试品牌',
            'competitor_brands': ['竞品 1', '竞品 2'],
            'selected_models': [{'name': 'gpt-4'}],
            'custom_questions': ['问题 1?', '问题 2?']
        }

    def teardown_method(self):
        """每个测试后的清理工作"""
        pass

    @patch('wechat_backend.services.diagnosis_transaction.get_report_service')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisReportRepository')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisResultRepository')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisAnalysisRepository')
    def test_transaction_commit_success(
        self,
        mock_analysis_repo,
        mock_result_repo,
        mock_report_repo,
        mock_report_service
    ):
        """测试事务提交成功"""
        # 准备 mock 对象
        mock_service = Mock()
        mock_service.create_report.return_value = 123
        mock_report_service.return_value = mock_service

        mock_report = Mock()
        mock_report.get.return_value = None
        mock_report_repo.return_value.get_by_id.return_value = mock_report

        mock_result = Mock()
        mock_result.return_value = [1, 2, 3]
        mock_report_service.add_results_batch = mock_result

        # 执行事务
        with DiagnosisTransaction(self.execution_id, self.execution_store) as tx:
            report_id = tx.create_report(user_id=self.user_id, config=self.config)
            
            results = [
                {'brand': '品牌 1', 'question': '问题 1', 'response': {'content': '回答 1'}},
                {'brand': '品牌 2', 'question': '问题 2', 'response': {'content': '回答 2'}}
            ]
            result_ids = tx.add_results_batch(report_id=report_id, results=results)

        # 验证事务状态
        assert tx.status == "committed"
        assert len(tx.operations) == 2  # create_report + add_results_batch
        
        # 验证操作日志
        op_log = tx.get_operation_log()
        assert op_log[0]['op_type'] == OperationType.CREATE_REPORT.value
        assert op_log[1]['op_type'] == OperationType.ADD_RESULTS_BATCH.value

        # 验证报告创建被调用
        mock_service.create_report.assert_called_once()
        
        # 验证结果保存被调用
        mock_report_service.add_results_batch.assert_called_once()

    @patch('wechat_backend.services.diagnosis_transaction.get_report_service')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisReportRepository')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisResultRepository')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisAnalysisRepository')
    def test_transaction_rollback_on_exception(
        self,
        mock_analysis_repo,
        mock_result_repo,
        mock_report_repo,
        mock_report_service
    ):
        """测试异常触发回滚"""
        # 准备 mock 对象
        mock_service = Mock()
        mock_service.create_report.return_value = 123
        mock_report_service.return_value = mock_service

        mock_report = Mock()
        mock_report.get.return_value = None
        mock_report_repo.return_value.get_by_id.return_value = mock_report

        # 模拟 add_results_batch 抛出异常
        mock_service.add_results_batch.side_effect = Exception("保存失败")

        # 执行事务（应该抛出异常）
        with pytest.raises(Exception, match="保存失败"):
            with DiagnosisTransaction(self.execution_id, self.execution_store) as tx:
                report_id = tx.create_report(user_id=self.user_id, config=self.config)
                
                results = [
                    {'brand': '品牌 1', 'question': '问题 1', 'response': {'content': '回答 1'}}
                ]
                tx.add_results_batch(report_id=report_id, results=results)
                # 这里会抛出异常

        # 验证事务状态
        assert tx.status == "failed"
        assert tx.error is not None
        
        # 验证回滚被调用
        # 注意：rollback 函数是 mock 的，所以不会真正执行数据库操作
        # 但我们可以通过操作日志验证回滚逻辑
        op_log = tx.get_operation_log()
        assert len(op_log) == 1  # 只有 create_report，add_results_batch 失败了

    def test_transaction_context_manager():
        """测试上下文管理器"""
        execution_id = str(uuid.uuid4())
        execution_store = {}

        with transaction_context(execution_id, execution_store) as tx:
            assert tx is not None
            assert tx.execution_id == execution_id
            assert tx.status == "active"

        assert tx.status == "committed"

    @patch('wechat_backend.services.diagnosis_transaction.get_report_service')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisReportRepository')
    def test_rollback_order(
        self,
        mock_report_repo,
        mock_report_service
    ):
        """测试回滚顺序（后进先出）"""
        # 准备 mock 对象
        mock_service = Mock()
        mock_service.create_report.return_value = 123
        mock_report_service.return_value = mock_service

        mock_report = Mock()
        mock_report.get.return_value = None
        mock_report_repo.return_value.get_by_id.return_value = mock_report

        rollback_order = []

        def mock_rollback_1():
            rollback_order.append(1)

        def mock_rollback_2():
            rollback_order.append(2)

        def mock_rollback_3():
            rollback_order.append(3)

        # 执行事务
        with DiagnosisTransaction(self.execution_id, self.execution_store) as tx:
            # 注册三个自定义操作
            tx.register_custom_operation("操作 1", {}, mock_rollback_1)
            tx.register_custom_operation("操作 2", {}, mock_rollback_2)
            tx.register_custom_operation("操作 3", {}, mock_rollback_3)
            
            # 手动触发回滚
            tx.rollback()

        # 验证回滚顺序（应该是 3, 2, 1）
        assert rollback_order == [3, 2, 1]

    @patch('wechat_backend.services.diagnosis_transaction.get_report_service')
    @patch('wechat_backend.services.diagnosis_transaction.DiagnosisReportRepository')
    def test_get_summary(
        self,
        mock_report_repo,
        mock_report_service
    ):
        """测试获取事务摘要"""
        mock_service = Mock()
        mock_service.create_report.return_value = 123
        mock_report_service.return_value = mock_service

        mock_report = Mock()
        mock_report.get.return_value = None
        mock_report_repo.return_value.get_by_id.return_value = mock_report

        with DiagnosisTransaction(self.execution_id, self.execution_store) as tx:
            tx.create_report(user_id=self.user_id, config=self.config)

        summary = tx.get_summary()
        
        assert summary['execution_id'] == self.execution_id
        assert summary['status'] == 'committed'
        assert summary['operation_count'] == 1
        assert summary['rolled_back_count'] == 0
        assert summary['started_at'] is not None
        assert summary['completed_at'] is not None


class TestDiagnosisOrchestratorTransaction:
    """诊断编排器事务集成测试"""

    @pytest.mark.asyncio
    @patch('wechat_backend.services.diagnosis_orchestrator.DiagnosisTransaction')
    @patch('wechat_backend.services.diagnosis_orchestrator.get_state_manager')
    async def test_orchestrator_with_transaction(
        self,
        mock_get_state_manager,
        mock_transaction
    ):
        """测试编排器使用事务管理"""
        from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator

        execution_id = str(uuid.uuid4())
        execution_store = {}
        
        orchestrator = DiagnosisOrchestrator(execution_id, execution_store)
        
        # Mock 事务管理器
        mock_tx = Mock()
        mock_tx.__enter__ = Mock(return_value=mock_tx)
        mock_tx.__exit__ = Mock(return_value=None)
        mock_transaction.return_value = mock_tx

        # Mock 状态管理器
        mock_state_mgr = Mock()
        mock_get_state_manager.return_value = mock_state_mgr

        # 执行诊断（会失败，因为其他依赖都是 mock 的）
        result = await orchestrator.execute_diagnosis(
            user_id='test_user',
            brand_list=['品牌 1'],
            selected_models=[{'name': 'gpt-4'}],
            custom_questions=['问题 1?']
        )

        # 验证事务上下文被使用
        mock_transaction.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
