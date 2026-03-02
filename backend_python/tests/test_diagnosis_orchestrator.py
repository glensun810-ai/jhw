"""
诊断编排器单元测试

测试覆盖：
1. 编排器初始化
2. 各阶段执行逻辑
3. 状态管理
4. 错误处理
5. 完整流程集成测试

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from wechat_backend.services.diagnosis_orchestrator import (
    DiagnosisOrchestrator,
    DiagnosisPhase,
    PhaseResult,
    create_orchestrator
)


class TestPhaseResult:
    """PhaseResult 单元测试"""

    def test_phase_result_success(self):
        """测试成功结果"""
        result = PhaseResult(success=True, data={'key': 'value'})
        
        assert result.success is True
        assert result.data == {'key': 'value'}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_phase_result_failure(self):
        """测试失败结果"""
        result = PhaseResult(success=False, error='Test error')
        
        assert result.success is False
        assert result.data is None
        assert result.error == 'Test error'

    def test_phase_result_to_dict(self):
        """测试转换为字典"""
        result = PhaseResult(success=True, data={'test': 'data'})
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['data'] == {'test': 'data'}
        assert result_dict['error'] is None
        assert 'timestamp' in result_dict


class TestDiagnosisOrchestrator:
    """DiagnosisOrchestrator 单元测试"""

    @pytest.fixture
    def execution_store(self):
        """创建测试用的执行状态存储"""
        return {}

    @pytest.fixture
    def orchestrator(self, execution_store):
        """创建编排器实例"""
        execution_id = 'test-execution-123'
        return create_orchestrator(execution_id, execution_store)

    # ========== Module 2: 初始化测试 ==========

    def test_init(self, orchestrator, execution_store):
        """测试初始化 - 基本属性"""
        assert orchestrator.execution_id == 'test-execution-123'
        assert orchestrator.execution_store is execution_store
        assert orchestrator.current_phase == DiagnosisPhase.INIT
        assert orchestrator.phase_results == {}
        assert isinstance(orchestrator.start_time, datetime)

    def test_init_error_logger(self, execution_store):
        """测试初始化 - 错误日志记录器"""
        orchestrator = create_orchestrator('test-err-log-123', execution_store)
        
        assert hasattr(orchestrator, '_error_logger')
        assert orchestrator._error_logger is not None
        # 验证错误记录器具有必要的方法
        assert hasattr(orchestrator._error_logger, 'log_error')

    def test_init_retry_handler(self, execution_store):
        """测试初始化 - 重试处理器"""
        orchestrator = create_orchestrator('test-retry-123', execution_store)
        
        assert hasattr(orchestrator, '_retry_handler')
        assert orchestrator._retry_handler is not None
        # 验证重试处理器具有必要的方法
        assert hasattr(orchestrator._retry_handler, 'execute_with_retry_async')

    def test_init_state_manager(self, execution_store):
        """测试初始化 - 状态管理器"""
        orchestrator = create_orchestrator('test-state-123', execution_store)
        
        assert hasattr(orchestrator, '_state_manager')
        # 状态管理器可能为 None（如果导入失败）
        if orchestrator._state_manager is not None:
            assert hasattr(orchestrator._state_manager, 'update_state')

    def test_init_state_manager_failure(self):
        """测试初始化 - 状态管理器失败场景"""
        execution_store = {}
        
        # Mock 状态管理器导入失败
        with patch('wechat_backend.state_manager.get_state_manager',
                   side_effect=ImportError('State manager not available')):
            orchestrator = create_orchestrator('test-state-fail-123', execution_store)
            
            # 状态管理器应该为 None
            assert orchestrator._state_manager is None
            # 其他属性仍应正常初始化
            assert orchestrator.execution_id == 'test-state-fail-123'

    def test_init_transaction_manager(self, execution_store):
        """测试初始化 - 事务管理器"""
        orchestrator = create_orchestrator('test-tx-123', execution_store)
        
        # 验证事务管理器初始化方法存在
        assert hasattr(orchestrator, '_init_transaction')
        assert hasattr(orchestrator, '_transaction_context')
        
        # 调用初始化方法
        orchestrator._init_transaction()
        
        # 验证事务已创建
        assert hasattr(orchestrator, '_transaction')
        assert orchestrator._transaction is not None
        assert orchestrator._transaction.execution_id == 'test-tx-123'

    def test_init_multiple_instances_isolation(self, execution_store):
        """测试初始化 - 多个实例隔离"""
        orchestrator1 = create_orchestrator('exec-001', execution_store)
        orchestrator2 = create_orchestrator('exec-002', execution_store)
        
        # 验证不同实例有不同的 execution_id
        assert orchestrator1.execution_id == 'exec-001'
        assert orchestrator2.execution_id == 'exec-002'
        assert orchestrator1.execution_id != orchestrator2.execution_id
        
        # 验证不同实例的 phase_results 独立
        orchestrator1.phase_results['init'] = PhaseResult(success=True, data={'test': 'data1'})
        assert 'init' not in orchestrator2.phase_results
        assert orchestrator2.phase_results == {}

    def test_init_execution_store_shared(self):
        """测试初始化 - 执行状态存储共享"""
        shared_store = {}
        
        orchestrator1 = create_orchestrator('exec-001', shared_store)
        orchestrator2 = create_orchestrator('exec-002', shared_store)
        
        # 验证共享同一个存储
        assert orchestrator1.execution_store is shared_store
        assert orchestrator2.execution_store is shared_store
        assert orchestrator1.execution_store is orchestrator2.execution_store

    def test_init_start_time_accuracy(self, execution_store):
        """测试初始化 - 开始时间精度"""
        before_init = datetime.now()
        orchestrator = create_orchestrator('test-time-123', execution_store)
        after_init = datetime.now()
        
        # 验证开始时间在初始化时间范围内
        assert before_init <= orchestrator.start_time <= after_init
        # 验证 start_time 是 datetime 实例
        assert isinstance(orchestrator.start_time, datetime)

    def test_init_phase_enum_value(self, execution_store):
        """测试初始化 - 阶段枚举值"""
        orchestrator = create_orchestrator('test-phase-123', execution_store)
        
        # 验证初始阶段为 INIT
        assert orchestrator.current_phase == DiagnosisPhase.INIT
        assert orchestrator.current_phase.value == 'init'

    def test_create_orchestrator(self, execution_store):
        """测试工厂函数"""
        orchestrator = create_orchestrator('test-123', execution_store)

        assert isinstance(orchestrator, DiagnosisOrchestrator)
        assert orchestrator.execution_id == 'test-123'

    def test_create_orchestrator_with_different_ids(self, execution_store):
        """测试工厂函数 - 不同 ID"""
        test_ids = [
            'simple-id-123',
            'uuid-like-id-abc-def-456',
            'user-specific-789',
            '特殊字符 -test-001'
        ]
        
        for test_id in test_ids:
            orchestrator = create_orchestrator(test_id, execution_store)
            assert orchestrator.execution_id == test_id
            assert isinstance(orchestrator, DiagnosisOrchestrator)

    def test_create_orchestrator_with_empty_store(self):
        """测试工厂函数 - 空存储"""
        empty_store = {}
        orchestrator = create_orchestrator('test-empty-store', empty_store)
        
        assert orchestrator.execution_store == {}
        assert len(orchestrator.execution_store) == 0

    def test_create_orchestrator_with_prepopulated_store(self):
        """测试工厂函数 - 预填充存储"""
        prepopulated_store = {
            'existing-key': 'existing-value',
            'another-execution': {'status': 'running'}
        }
        orchestrator = create_orchestrator('test-prepopulated', prepopulated_store)
        
        assert 'existing-key' in orchestrator.execution_store
        assert 'another-execution' in orchestrator.execution_store
        assert orchestrator.execution_store['existing-key'] == 'existing-value'

    @pytest.mark.asyncio
    async def test_phase_init_success(self, orchestrator):
        """测试阶段 1: 初始化成功"""
        # 设置初始参数
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A', 'Brand B'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Question 1?']
        }

        result = await orchestrator._phase_init()

        assert result.success is True
        assert orchestrator.current_phase == DiagnosisPhase.INIT
        assert 'init' in orchestrator.phase_results
        assert orchestrator.execution_store['test-execution-123']['status'] == 'initializing'

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_success(self, orchestrator):
        """测试阶段 2: AI 调用成功"""
        # Mock 并行执行引擎 - 修复 Mock 路径
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm', 
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'results': [
                    {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao', 'response': {'content': 'Answer'}}
                ]
            }

            result = await orchestrator._phase_ai_fetching(
                brand_list=['Brand A', 'Brand B'],
                selected_models=[{'name': 'doubao'}],
                custom_questions=['Question 1?'],
                user_id='test-user',
                user_level='Free'
            )

            assert result.success is True
            assert len(result.data) == 1
            assert orchestrator.current_phase == DiagnosisPhase.AI_FETCHING

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_failure(self, orchestrator):
        """测试阶段 2: AI 调用失败"""
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': False,
                'error': 'AI API error'
            }

            result = await orchestrator._phase_ai_fetching(
                brand_list=['Brand A'],
                selected_models=[{'name': 'doubao'}],
                custom_questions=['Question 1?'],
                user_id='test-user',
                user_level='Free'
            )

            assert result.success is False
            assert 'AI API error' in result.error

    @pytest.mark.asyncio
    async def test_phase_results_saving_success(self, orchestrator):
        """测试阶段 3: 结果保存成功"""
        # Mock 报告服务 - 修复 Mock 路径
        mock_service = Mock()
        mock_service.create_report.return_value = 123
        mock_service.add_results_batch.return_value = [1, 2, 3]

        with patch('wechat_backend.diagnosis_report_service.get_report_service',
                   return_value=mock_service):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao', 'response': {'content': 'Answer'}}
            ]

            result = await orchestrator._phase_results_saving(
                results=results,
                brand_list=['Brand A', 'Brand B'],
                selected_models=[{'name': 'doubao'}],
                custom_questions=['Question 1?']
            )

            assert result.success is True
            assert result.data['report_id'] == 123
            assert result.data['saved_count'] == 1
            assert orchestrator._report_id == 123

    @pytest.mark.asyncio
    async def test_phase_results_validating_success(self, orchestrator):
        """测试阶段 4: 结果验证成功"""
        # Mock 结果仓库 - 修复 Mock 路径
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'Brand A',
                'question': 'Q1',
                'model': 'doubao',
                'response': {'content': 'Valid answer'}
            }
        ]

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao', 'response': {'content': 'Answer'}}
            ]

            result = await orchestrator._phase_results_validating(results)

            assert result.success is True
            assert result.data['expected_count'] == 1
            assert result.data['actual_count'] == 1

    @pytest.mark.asyncio
    async def test_phase_results_validating_count_mismatch(self, orchestrator):
        """测试阶段 4: 结果数量不匹配"""
        # Mock 结果仓库 - 返回数量不匹配
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'Brand A', 'question': 'Q1'}  # 只有 1 个，期望 2 个
        ]

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            results = [
                {'brand': 'Brand A', 'question': 'Q1'},
                {'brand': 'Brand B', 'question': 'Q1'}  # 期望 2 个
            ]

            result = await orchestrator._phase_results_validating(results)

            assert result.success is False
            assert '数量不匹配' in result.error

    @pytest.mark.asyncio
    async def test_phase_results_validating_all_invalid(self, orchestrator):
        """测试阶段 4: 所有结果都无效"""
        # Mock 结果仓库 - 所有结果都为空响应
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'Brand A',
                'question': 'Q1',
                'model': 'doubao',
                'response': {'content': ''}  # 空响应
            }
        ]

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao', 'response': {'content': ''}}
            ]

            result = await orchestrator._phase_results_validating(results)

            assert result.success is False
            assert '所有 AI 响应均为空或无效' in result.error

    def test_phase_background_analysis_async(self, orchestrator):
        """测试阶段 5: 后台分析异步提交"""
        # Mock 后台任务管理器 - 修复 Mock 路径
        mock_manager = Mock()
        mock_manager.submit_analysis_task = Mock()

        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                   return_value=mock_manager):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao'}
            ]

            result = orchestrator._phase_background_analysis_async(
                results=results,
                brand_list=['Brand A', 'Brand B']
            )

            assert result.success is True
            # 验证提交了两个任务
            assert mock_manager.submit_analysis_task.call_count == 2

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_success(self, orchestrator):
        """测试阶段 6: 报告聚合成功"""
        # Mock 报告聚合服务 - 使用 sys.path 添加项目根目录
        import sys
        sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject')
        
        mock_aggregate_report = Mock(return_value={
            'brandName': 'Brand A',
            'overallScore': 85,
            'brandScores': {'Brand A': {'overallScore': 85}}
        })

        with patch('services.reportAggregator.aggregateReport',
                   mock_aggregate_report):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao'}
            ]

            result = await orchestrator._phase_report_aggregating(
                results=results,
                brand_list=['Brand A', 'Brand B']
            )

            assert result.success is True
            assert result.data['brandName'] == 'Brand A'
            assert result.data['overallScore'] == 85

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_fallback(self, orchestrator):
        """测试阶段 6: 报告聚合失败降级处理"""
        # Mock 报告聚合服务抛出异常
        import sys
        sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject')
        
        with patch('services.reportAggregator.aggregateReport',
                   side_effect=ImportError('Service not available')):
            results = [
                {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao', 'score': 80}
            ]

            result = await orchestrator._phase_report_aggregating(
                results=results,
                brand_list=['Brand A', 'Brand B']
            )

            assert result.success is True  # 降级处理仍算成功
            assert result.data.get('isSimplified') is True

    @pytest.mark.asyncio
    async def test_phase_complete_success(self, orchestrator):
        """测试阶段 7: 完成成功"""
        # Mock 状态管理器和推送服务 - 修复 Mock 路径
        mock_state_manager = Mock()
        mock_state_manager.complete_execution = Mock()
        orchestrator._state_manager = mock_state_manager

        mock_push_service = Mock()
        mock_push_service.send_complete = AsyncMock()

        with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service',
                   return_value=mock_push_service):
            orchestrator._initial_params = {
                'user_id': 'test-user',
                'brand_list': ['Brand A', 'Brand B'],
                'selected_models': [{'name': 'doubao'}],
                'custom_questions': ['Question 1?'],
                'user_openid': 'test-openid'
            }

            final_report = {'brandName': 'Brand A', 'overallScore': 85}
            result = await orchestrator._phase_complete(final_report)

            assert result.success is True
            mock_state_manager.complete_execution.assert_called_once()
            mock_push_service.send_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_failed(self, orchestrator):
        """测试阶段 8: 失败处理"""
        # Mock 状态管理器和推送服务 - 修复 Mock 路径
        mock_state_manager = Mock()
        mock_state_manager.update_state = Mock()
        orchestrator._state_manager = mock_state_manager

        mock_push_service = Mock()
        mock_push_service.send_error = AsyncMock()

        with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service',
                   return_value=mock_push_service):
            orchestrator._initial_params = {
                'user_id': 'test-user',
                'brand_list': ['Brand A'],
                'selected_models': [{'name': 'doubao'}],
                'custom_questions': ['Question 1?'],
                'user_openid': 'test-openid'
            }

            result = await orchestrator._phase_failed('Test error message')

            assert result.success is False
            assert result.error == 'Test error message'
            mock_state_manager.update_state.assert_called_once()
            mock_push_service.send_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_diagnosis_complete_flow(self, orchestrator):
        """测试完整诊断流程"""
        # Mock 所有阶段
        orchestrator._phase_init = AsyncMock(return_value=PhaseResult(success=True))
        orchestrator._phase_ai_fetching = AsyncMock(return_value=PhaseResult(
            success=True,
            data=[{'brand': 'Brand A', 'question': 'Q1'}]
        ))
        orchestrator._phase_results_saving = AsyncMock(return_value=PhaseResult(success=True))
        orchestrator._phase_results_validating = AsyncMock(return_value=PhaseResult(success=True))
        orchestrator._phase_background_analysis_async = Mock(return_value=PhaseResult(success=True))
        orchestrator._phase_report_aggregating = AsyncMock(return_value=PhaseResult(
            success=True,
            data={'brandName': 'Brand A', 'overallScore': 85}
        ))
        orchestrator._phase_complete = AsyncMock(return_value=PhaseResult(success=True))

        # 设置初始参数
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A', 'Brand B'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Question 1?'],
            'user_openid': 'test-openid',
            'user_level': 'Free'
        }

        # 执行完整流程
        result = await orchestrator.execute_diagnosis(
            user_id='test-user',
            brand_list=['Brand A', 'Brand B'],
            selected_models=[{'name': 'doubao'}],
            custom_questions=['Question 1?'],
            user_openid='test-openid',
            user_level='Free'
        )

        assert result['success'] is True
        assert result['execution_id'] == 'test-execution-123'
        assert 'report' in result
        assert 'total_time' in result

    @pytest.mark.asyncio
    async def test_execute_diagnosis_failure_handling(self, orchestrator):
        """测试失败处理"""
        # Mock 阶段 2 失败
        orchestrator._phase_init = AsyncMock(return_value=PhaseResult(success=True))
        orchestrator._phase_ai_fetching = AsyncMock(return_value=PhaseResult(
            success=False,
            error='AI API error'
        ))
        orchestrator._phase_failed = AsyncMock(return_value=PhaseResult(success=False))

        # 设置初始参数
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Question 1?']
        }

        # 执行流程
        result = await orchestrator.execute_diagnosis(
            user_id='test-user',
            brand_list=['Brand A'],
            selected_models=[{'name': 'doubao'}],
            custom_questions=['Question 1?']
        )

        assert result['success'] is False
        assert 'error' in result
        orchestrator._phase_failed.assert_called_once()

    def test_get_phase_status(self, orchestrator):
        """测试获取阶段状态"""
        # 添加一些模拟的阶段结果
        orchestrator.phase_results['init'] = PhaseResult(success=True, data={'initialized': True})
        orchestrator.phase_results['ai_fetching'] = PhaseResult(
            success=True,
            data=[{'brand': 'Brand A'}]
        )

        status = orchestrator.get_phase_status()

        assert status['execution_id'] == 'test-execution-123'
        assert 'current_phase' in status
        assert 'phase_results' in status
        assert 'total_time' in status
        assert len(status['phase_results']) == 2


class TestDiagnosisPhase:
    """DiagnosisPhase 枚举测试"""

    def test_phase_values(self):
        """测试阶段枚举值"""
        assert DiagnosisPhase.INIT.value == 'init'
        assert DiagnosisPhase.AI_FETCHING.value == 'ai_fetching'
        assert DiagnosisPhase.RESULTS_SAVING.value == 'results_saving'
        assert DiagnosisPhase.RESULTS_VALIDATING.value == 'results_validating'
        assert DiagnosisPhase.BACKGROUND_ANALYSIS.value == 'background_analysis'
        assert DiagnosisPhase.REPORT_AGGREGATING.value == 'report_aggregating'
        assert DiagnosisPhase.COMPLETED.value == 'completed'
        assert DiagnosisPhase.FAILED.value == 'failed'


# 集成测试标记
@pytest.mark.integration
class TestDiagnosisOrchestratorIntegration:
    """诊断编排器集成测试"""

    @pytest.mark.asyncio
    async def test_full_diagnosis_with_mocks(self):
        """完整诊断流程集成测试（全 Mock）"""
        import sys
        sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject')
        
        execution_store = {}
        orchestrator = create_orchestrator('integration-test-123', execution_store)

        # Mock 所有外部依赖
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   AsyncMock(return_value={
                       'success': True,
                       'results': [
                           {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao',
                            'response': {'content': 'Answer A'}, 'score': 85}
                       ]
                   })):
            with patch('wechat_backend.diagnosis_report_service.get_report_service') as mock_service:
                mock_service_instance = Mock()
                mock_service_instance.create_report.return_value = 456
                mock_service_instance.add_results_batch.return_value = [789]
                mock_service.return_value = mock_service_instance

                with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository') as mock_repo:
                    mock_repo_instance = Mock()
                    mock_repo_instance.get_by_execution_id.return_value = [
                        {'brand': 'Brand A', 'question': 'Q1', 'model': 'doubao',
                         'response': {'content': 'Answer A'}}
                    ]
                    mock_repo.return_value = mock_repo_instance

                    with patch('services.reportAggregator.aggregateReport',
                               Mock(return_value={
                                   'brandName': 'Brand A',
                                   'overallScore': 85,
                                   'brandScores': {'Brand A': {'overallScore': 85}}
                               })):
                        with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service') as mock_push:
                            mock_push_instance = Mock()
                            mock_push_instance.send_complete = AsyncMock()
                            mock_push.return_value = mock_push_instance

                            # Mock 状态管理器
                            orchestrator._state_manager = Mock()
                            orchestrator._state_manager.update_state = Mock()
                            orchestrator._state_manager.complete_execution = Mock()

                            # 设置初始参数
                            orchestrator._initial_params = {
                                'user_id': 'test-user',
                                'brand_list': ['Brand A', 'Brand B'],
                                'selected_models': [{'name': 'doubao'}],
                                'custom_questions': ['Question 1?'],
                                'user_openid': 'test-openid',
                                'user_level': 'Free'
                            }

                            # 执行完整流程
                            result = await orchestrator.execute_diagnosis(
                                user_id='test-user',
                                brand_list=['Brand A', 'Brand B'],
                                selected_models=[{'name': 'doubao'}],
                                custom_questions=['Question 1?'],
                                user_openid='test-openid',
                                user_level='Free'
                            )

                            # 验证结果
                            assert result['success'] is True
                            assert result['execution_id'] == 'integration-test-123'
                            assert 'report' in result
                            assert result['report']['brandName'] == 'Brand A'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
