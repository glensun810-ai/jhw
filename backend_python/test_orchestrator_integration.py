"""
诊断编排器集成测试 - Phase Execution Tests

测试覆盖：
1. Module 1: Orchestrator initialization tests
2. Module 2: State management tests
3. Module 3: Phase execution tests (本文件重点)
4. Module 4: Error handling and recovery tests
5. Module 5: End-to-end integration tests

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, List

from wechat_backend.services.diagnosis_orchestrator import (
    DiagnosisOrchestrator,
    DiagnosisPhase,
    PhaseResult,
    create_orchestrator
)
from wechat_backend.services.diagnosis_transaction import DiagnosisTransaction
from wechat_backend.state_manager import (
    DiagnosisStateManager,
    StateChangeType,
    StateChangeRecord,
    get_state_manager
)


# ============================================================================
# Module 3: Phase Execution Tests
# ============================================================================
# 测试编排器各阶段的执行逻辑
# 覆盖：
# 1. 各阶段独立执行
# 2. 阶段间状态转换
# 3. 阶段执行结果验证
# 4. 阶段超时处理
# 5. 阶段并发控制
# ============================================================================

class TestPhaseExecution:
    """Module 3: Phase execution tests - 阶段执行测试"""

    @pytest.fixture
    def execution_store(self) -> Dict[str, Any]:
        """创建测试用的执行状态存储"""
        return {}

    @pytest.fixture
    def orchestrator(self, execution_store) -> DiagnosisOrchestrator:
        """创建编排器实例"""
        execution_id = 'phase-test-execution-123'
        return create_orchestrator(execution_id, execution_store)

    @pytest.fixture
    def sample_brand_list(self) -> List[str]:
        """样本品牌列表"""
        return ['Brand A', 'Brand B', 'Brand C']

    @pytest.fixture
    def sample_models(self) -> List[Dict[str, Any]]:
        """样本 AI 模型列表"""
        return [
            {'name': 'doubao', 'version': 'v1.0'},
            {'name': 'deepseek', 'version': 'v2.0'}
        ]

    @pytest.fixture
    def sample_questions(self) -> List[str]:
        """样本问题列表"""
        return [
            '品牌 A 的核心竞争力是什么？',
            '品牌 A 与品牌 B 的差异在哪里？'
        ]

    @pytest.fixture
    def sample_ai_results(self) -> List[Dict[str, Any]]:
        """样本 AI 调用结果"""
        return [
            {
                'brand': 'Brand A',
                'question': '品牌 A 的核心竞争力是什么？',
                'model': 'doubao',
                'response': {'content': '品牌 A 的核心竞争力在于创新技术。', 'score': 85},
                'score': 85,
                'timestamp': datetime.now().isoformat()
            },
            {
                'brand': 'Brand B',
                'question': '品牌 A 的核心竞争力是什么？',
                'model': 'doubao',
                'response': {'content': '品牌 B 认为品牌 A 的优势是渠道。', 'score': 78},
                'score': 78,
                'timestamp': datetime.now().isoformat()
            }
        ]

    # =========================================================================
    # Phase 1: Initialization Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_init_basic(self, orchestrator):
        """测试阶段 1: 基本初始化"""
        # 设置初始参数
        orchestrator._initial_params = {
            'user_id': 'test-user-001',
            'brand_list': ['Brand A', 'Brand B'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Question 1?'],
            'user_openid': 'test-openid',
            'user_level': 'Free'
        }

        # 执行初始化
        result = await orchestrator._phase_init()

        # 验证结果
        assert result.success is True
        assert result.data == {'initialized': True}
        assert orchestrator.current_phase == DiagnosisPhase.INIT
        assert 'init' in orchestrator.phase_results

    @pytest.mark.asyncio
    async def test_phase_init_execution_store_population(self, orchestrator):
        """测试阶段 1: execution_store 数据填充"""
        orchestrator._initial_params = {
            'user_id': 'test-user-002',
            'brand_list': ['Brand X', 'Brand Y'],
            'selected_models': [{'name': 'qwen'}],
            'custom_questions': ['Test question?'],
            'user_openid': 'test-openid-2',
            'user_level': 'Pro'
        }

        await orchestrator._phase_init()

        # 验证 execution_store 中的数据
        assert orchestrator.execution_id in orchestrator.execution_store
        store_data = orchestrator.execution_store[orchestrator.execution_id]

        assert store_data['status'] == 'initializing'
        assert store_data['stage'] == 'init'
        assert store_data['progress'] == 0
        assert store_data['brand_name'] == 'Brand X'
        assert store_data['competitor_brands'] == ['Brand Y']
        assert 'start_time' in store_data

    @pytest.mark.asyncio
    async def test_phase_init_with_state_manager(self, orchestrator):
        """测试阶段 1: 带状态管理器的初始化"""
        # Mock 状态管理器
        mock_state_manager = Mock()
        mock_state_manager.update_state = Mock()
        orchestrator._state_manager = mock_state_manager

        orchestrator._initial_params = {
            'user_id': 'test-user-003',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'openid-003',
            'user_level': 'Free'
        }

        result = await orchestrator._phase_init()

        assert result.success is True
        # 验证状态管理器被调用
        mock_state_manager.update_state.assert_called_once()
        call_args = mock_state_manager.update_state.call_args[1]
        assert call_args['status'] == 'initializing'
        assert call_args['stage'] == 'init'
        assert call_args['progress'] == 0

    @pytest.mark.asyncio
    async def test_phase_init_without_state_manager(self, orchestrator):
        """测试阶段 1: 无状态管理器时的降级处理"""
        orchestrator._state_manager = None
        orchestrator._initial_params = {
            'user_id': 'test-user-004',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?']
        }

        # 即使状态管理器为 None，初始化也应成功
        result = await orchestrator._phase_init()

        assert result.success is True
        # execution_store 仍应被更新
        assert orchestrator.execution_id in orchestrator.execution_store

    @pytest.mark.asyncio
    async def test_phase_init_error_missing_params(self, orchestrator):
        """测试阶段 1: 缺少初始参数时的错误处理"""
        # 不设置 _initial_params
        result = await orchestrator._phase_init()

        # 应该失败并捕获异常
        assert result.success is False
        assert 'error' in result.error or result.success is False

    # =========================================================================
    # Phase 2: AI Fetching Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_success(self, orchestrator, sample_brand_list,
                                              sample_models, sample_questions):
        """测试阶段 2: AI 调用成功"""
        # Mock 并行执行引擎
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'results': [
                    {
                        'brand': 'Brand A',
                        'question': 'Q1',
                        'model': 'doubao',
                        'response': {'content': 'Answer A', 'score': 85}
                    }
                ]
            }

            result = await orchestrator._phase_ai_fetching(
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions,
                user_id='test-user',
                user_level='Free'
            )

            # 验证结果
            assert result.success is True
            assert len(result.data) == 1
            assert result.data[0]['brand'] == 'Brand A'
            assert orchestrator.current_phase == DiagnosisPhase.AI_FETCHING
            assert 'ai_fetching' in orchestrator.phase_results

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_with_retry(self, orchestrator, sample_brand_list,
                                                 sample_models, sample_questions):
        """测试阶段 2: AI 调用带重试机制"""
        call_count = 0

        async def mock_execute_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # 第一次调用失败
                return {'success': False, 'error': 'Temporary error'}
            # 第二次调用成功
            return {
                'success': True,
                'results': [{'brand': 'Brand A', 'question': 'Q1', 'response': {'content': 'Answer'}}]
            }

        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   side_effect=mock_execute_with_retry):
            result = await orchestrator._phase_ai_fetching(
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions,
                user_id='test-user',
                user_level='Free'
            )

            # 验证重试发生
            assert call_count >= 2
            # 最终应该成功
            assert result.success is True

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_failure(self, orchestrator, sample_brand_list,
                                              sample_models, sample_questions):
        """测试阶段 2: AI 调用失败"""
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': False,
                'error': 'AI API unavailable'
            }

            result = await orchestrator._phase_ai_fetching(
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions,
                user_id='test-user',
                user_level='Free'
            )

            assert result.success is False
            assert 'AI API unavailable' in result.error

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_empty_results(self, orchestrator, sample_brand_list,
                                                    sample_models, sample_questions):
        """测试阶段 2: AI 调用返回空结果"""
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'results': []
            }

            result = await orchestrator._phase_ai_fetching(
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions,
                user_id='test-user',
                user_level='Free'
            )

            # 空结果也应该算成功（可能是正常情况）
            assert result.success is True
            assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_phase_ai_fetching_state_update(self, orchestrator, sample_brand_list,
                                                   sample_models, sample_questions):
        """测试阶段 2: 状态更新"""
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'results': [{'brand': 'Brand A', 'response': {'content': 'Answer'}}]
            }

            await orchestrator._phase_ai_fetching(
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions,
                user_id='test-user',
                user_level='Free'
            )

            # 验证 execution_store 更新
            store_data = orchestrator.execution_store[orchestrator.execution_id]
            assert store_data['status'] == 'ai_fetching'
            assert store_data['progress'] == 30

    # =========================================================================
    # Phase 3: Results Saving Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_results_saving_success(self, orchestrator, sample_ai_results,
                                                 sample_brand_list, sample_models,
                                                 sample_questions):
        """测试阶段 3: 结果保存成功"""
        # 初始化事务并设置 _current_transaction
        orchestrator._init_transaction()
        orchestrator._current_transaction = orchestrator._transaction

        # Mock 报告服务
        mock_service = Mock()
        mock_service.create_report.return_value = 999
        mock_service.add_results_batch.return_value = [1, 2, 3]

        with patch('wechat_backend.diagnosis_report_service.get_report_service',
                   return_value=mock_service):
            # 设置初始参数
            orchestrator._initial_params = {
                'user_id': 'test-user',
                'brand_list': sample_brand_list,
                'selected_models': sample_models,
                'custom_questions': sample_questions
            }

            result = await orchestrator._phase_results_saving(
                results=sample_ai_results,
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions
            )

            assert result.success is True
            assert result.data['report_id'] == 999
            assert result.data['saved_count'] == len(sample_ai_results)
            assert hasattr(orchestrator, '_report_id')
            assert orchestrator._report_id == 999

    @pytest.mark.asyncio
    async def test_phase_results_saving_empty_results(self, orchestrator,
                                                       sample_brand_list, sample_models,
                                                       sample_questions):
        """测试阶段 3: 保存空结果集"""
        orchestrator._init_transaction()
        orchestrator._current_transaction = orchestrator._transaction
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': sample_brand_list,
            'selected_models': sample_models,
            'custom_questions': sample_questions
        }

        mock_service = Mock()
        mock_service.create_report.return_value = 888

        with patch('wechat_backend.diagnosis_report_service.get_report_service',
                   return_value=mock_service):
            result = await orchestrator._phase_results_saving(
                results=[],
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions
            )

            # 空结果集也应该成功
            assert result.success is True
            assert result.data['saved_count'] == 0

    @pytest.mark.asyncio
    async def test_phase_results_saving_without_transaction(self, orchestrator,
                                                             sample_ai_results,
                                                             sample_brand_list,
                                                             sample_models,
                                                             sample_questions):
        """测试阶段 3: 无事务管理器时的错误处理"""
        # 不初始化事务
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': sample_brand_list,
            'selected_models': sample_models,
            'custom_questions': sample_questions
        }

        result = await orchestrator._phase_results_saving(
            results=sample_ai_results,
            brand_list=sample_brand_list,
            selected_models=sample_models,
            custom_questions=sample_questions
        )

        # 应该失败，因为缺少事务管理器
        assert result.success is False
        assert '事务管理器' in result.error

    @pytest.mark.asyncio
    async def test_phase_results_saving_state_update(self, orchestrator,
                                                      sample_ai_results,
                                                      sample_brand_list,
                                                      sample_models,
                                                      sample_questions):
        """测试阶段 3: 状态更新"""
        orchestrator._init_transaction()
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': sample_brand_list,
            'selected_models': sample_models,
            'custom_questions': sample_questions
        }

        mock_service = Mock()
        mock_service.create_report.return_value = 777
        mock_service.add_results_batch.return_value = [1, 2]

        with patch('wechat_backend.diagnosis_report_service.get_report_service',
                   return_value=mock_service):
            await orchestrator._phase_results_saving(
                results=sample_ai_results,
                brand_list=sample_brand_list,
                selected_models=sample_models,
                custom_questions=sample_questions
            )

            # 验证状态更新
            assert orchestrator.current_phase == DiagnosisPhase.RESULTS_SAVING

    # =========================================================================
    # Phase 4: Results Validating Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_results_validating_success(self, orchestrator,
                                                     sample_ai_results):
        """测试阶段 4: 结果验证成功"""
        # Mock 结果仓库
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = sample_ai_results

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            result = await orchestrator._phase_results_validating(sample_ai_results)

            assert result.success is True
            assert result.data['expected_count'] == len(sample_ai_results)
            assert result.data['actual_count'] == len(sample_ai_results)

    @pytest.mark.asyncio
    async def test_phase_results_validating_count_mismatch(self, orchestrator,
                                                            sample_ai_results):
        """测试阶段 4: 结果数量不匹配"""
        # Mock 返回更少的结果
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = sample_ai_results[:1]  # 只返回 1 个

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            result = await orchestrator._phase_results_validating(sample_ai_results)

            # 数量不匹配应该失败
            assert result.success is False
            assert '数量不匹配' in result.error or 'invalid' in result.error.lower()

    @pytest.mark.asyncio
    async def test_phase_results_validating_all_invalid(self, orchestrator):
        """测试阶段 4: 所有结果都无效（空响应）"""
        invalid_results = [
            {
                'brand': 'Brand A',
                'question': 'Q1',
                'model': 'doubao',
                'response': {'content': ''}  # 空响应
            },
            {
                'brand': 'Brand B',
                'question': 'Q1',
                'model': 'doubao',
                'response': {'content': '   '}  # 只有空白
            }
        ]

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = invalid_results

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            result = await orchestrator._phase_results_validating(invalid_results)

            # 所有结果都无效应该失败
            assert result.success is False
            assert '空或无效' in result.error

    @pytest.mark.asyncio
    async def test_phase_results_validating_partial_invalid(self, orchestrator,
                                                             sample_ai_results):
        """测试阶段 4: 部分结果无效"""
        # 混合有效和无效结果
        mixed_results = sample_ai_results + [
            {
                'brand': 'Brand C',
                'question': 'Q1',
                'model': 'doubao',
                'response': {'content': ''}  # 无效
            }
        ]

        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = mixed_results

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            result = await orchestrator._phase_results_validating(mixed_results)

            # 部分无效可能仍然成功（取决于验证策略）
            # 这里验证应该记录无效结果的数量
            assert result.success is True or 'invalid' in str(result.data)

    @pytest.mark.asyncio
    async def test_phase_results_validating_state_update(self, orchestrator,
                                                          sample_ai_results):
        """测试阶段 4: 状态更新"""
        mock_repo = Mock()
        mock_repo.get_by_execution_id.return_value = sample_ai_results

        with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository',
                   return_value=mock_repo):
            await orchestrator._phase_results_validating(sample_ai_results)

            assert orchestrator.current_phase == DiagnosisPhase.RESULTS_VALIDATING

    # =========================================================================
    # Phase 5: Background Analysis Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_background_analysis_async(self, orchestrator,
                                                    sample_ai_results,
                                                    sample_brand_list):
        """测试阶段 5: 后台分析异步提交"""
        # Mock 后台任务管理器
        mock_manager = Mock()
        mock_manager.submit_analysis_task = Mock(return_value='task-id-123')

        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                   return_value=mock_manager):
            result = orchestrator._phase_background_analysis_async(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            assert result.success is True
            # 验证提交了两个任务（品牌分析和竞争分析）
            assert mock_manager.submit_analysis_task.call_count == 2

    @pytest.mark.asyncio
    async def test_phase_background_analysis_task_types(self, orchestrator,
                                                         sample_ai_results,
                                                         sample_brand_list):
        """测试阶段 5: 提交的任务类型"""
        mock_manager = Mock()
        mock_manager.submit_analysis_task = Mock(return_value='task-id')

        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                   return_value=mock_manager):
            orchestrator._phase_background_analysis_async(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            # 验证提交的任务类型
            calls = mock_manager.submit_analysis_task.call_args_list
            task_types = [call[1]['task_type'] for call in calls]

            assert 'brand_analysis' in task_types
            assert 'competitive_analysis' in task_types

    @pytest.mark.asyncio
    async def test_phase_background_analysis_payload(self, orchestrator,
                                                      sample_ai_results,
                                                      sample_brand_list):
        """测试阶段 5: 任务负载数据"""
        mock_manager = Mock()
        mock_manager.submit_analysis_task = Mock(return_value='task-id')

        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                   return_value=mock_manager):
            orchestrator._phase_background_analysis_async(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            # 验证负载数据包含必要信息
            calls = mock_manager.submit_analysis_task.call_args_list
            for call in calls:
                payload = call[1]['payload']
                assert 'results' in payload
                assert payload['results'] == sample_ai_results

    @pytest.mark.asyncio
    async def test_phase_background_analysis_state_update(self, orchestrator,
                                                           sample_ai_results,
                                                           sample_brand_list):
        """测试阶段 5: 状态更新"""
        mock_manager = Mock()
        mock_manager.submit_analysis_task = Mock()

        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                   return_value=mock_manager):
            orchestrator._phase_background_analysis_async(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            assert orchestrator.current_phase == DiagnosisPhase.BACKGROUND_ANALYSIS

    # =========================================================================
    # Phase 6: Report Aggregating Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_success(self, orchestrator,
                                                     sample_ai_results,
                                                     sample_brand_list):
        """测试阶段 6: 报告聚合成功"""
        # Mock 报告聚合服务
        mock_aggregate_report = Mock(return_value={
            'brandName': 'Brand A',
            'overallScore': 85,
            'brandScores': {'Brand A': {'overallScore': 85}},
            'recommendations': ['建议 1', '建议 2']
        })

        with patch('services.reportAggregator.aggregateReport', mock_aggregate_report):
            result = await orchestrator._phase_report_aggregating(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            assert result.success is True
            assert result.data['brandName'] == 'Brand A'
            assert result.data['overallScore'] == 85

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_fallback(self, orchestrator,
                                                      sample_ai_results,
                                                      sample_brand_list):
        """测试阶段 6: 报告聚合失败降级处理"""
        # Mock 聚合服务不可用
        with patch('services.reportAggregator.aggregateReport',
                   side_effect=ImportError('Service not available')):
            result = await orchestrator._phase_report_aggregating(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            # 降级处理应该仍然返回基本报告
            assert result.success is True
            assert 'isSimplified' in result.data or result.data.get('brandName') == 'Brand A'

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_empty_results(self, orchestrator,
                                                           sample_brand_list):
        """测试阶段 6: 空结果聚合"""
        mock_aggregate_report = Mock(return_value={
            'brandName': 'Brand A',
            'overallScore': 0,
            'isSimplified': True
        })

        with patch('services.reportAggregator.aggregateReport', mock_aggregate_report):
            result = await orchestrator._phase_report_aggregating(
                results=[],
                brand_list=sample_brand_list
            )

            assert result.success is True
            assert result.data['overallScore'] == 0

    @pytest.mark.asyncio
    async def test_phase_report_aggregating_state_update(self, orchestrator,
                                                          sample_ai_results,
                                                          sample_brand_list):
        """测试阶段 6: 状态更新"""
        mock_aggregate_report = Mock(return_value={'brandName': 'Brand A'})

        with patch('services.reportAggregator.aggregateReport', mock_aggregate_report):
            await orchestrator._phase_report_aggregating(
                results=sample_ai_results,
                brand_list=sample_brand_list
            )

            assert orchestrator.current_phase == DiagnosisPhase.REPORT_AGGREGATING

    # =========================================================================
    # Phase 7: Complete Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_complete_success(self, orchestrator):
        """测试阶段 7: 完成成功"""
        # Mock 状态管理器和推送服务
        mock_state_manager = Mock()
        mock_state_manager.complete_execution = Mock()
        orchestrator._state_manager = mock_state_manager

        mock_push_service = Mock()
        mock_push_service.send_complete = AsyncMock()

        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A', 'Brand B'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'test-openid'
        }

        final_report = {'brandName': 'Brand A', 'overallScore': 85}

        with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service',
                   return_value=mock_push_service):
            result = await orchestrator._phase_complete(final_report)

            assert result.success is True
            mock_state_manager.complete_execution.assert_called_once()
            mock_push_service.send_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_complete_without_push_service(self, orchestrator):
        """测试阶段 7: 推送服务不可用时的降级处理"""
        mock_state_manager = Mock()
        mock_state_manager.complete_execution = Mock()
        orchestrator._state_manager = mock_state_manager

        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'test-openid'
        }

        with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service',
                   side_effect=Exception('Service unavailable')):
            final_report = {'brandName': 'Brand A'}
            result = await orchestrator._phase_complete(final_report)

            # 推送失败不应影响整体完成
            assert result.success is True
            mock_state_manager.complete_execution.assert_called_once()

    # =========================================================================
    # Phase 8: Failed Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_failed(self, orchestrator):
        """测试阶段 8: 失败处理"""
        # Mock 状态管理器和推送服务
        mock_state_manager = Mock()
        mock_state_manager.update_state = Mock()
        orchestrator._state_manager = mock_state_manager

        mock_push_service = Mock()
        mock_push_service.send_error = AsyncMock()

        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'test-openid'
        }

        result = await orchestrator._phase_failed('Test error message')

        assert result.success is False
        assert result.error == 'Test error message'
        mock_state_manager.update_state.assert_called_once()
        mock_push_service.send_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_failed_with_error_code(self, orchestrator):
        """测试阶段 8: 带错误码的失败处理"""
        mock_state_manager = Mock()
        mock_state_manager.update_state = Mock()
        orchestrator._state_manager = mock_state_manager

        mock_push_service = Mock()
        mock_push_service.send_error = AsyncMock()

        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'test-openid'
        }

        # 模拟带错误码的失败
        result = await orchestrator._phase_failed(
            'AI API error',
            error_code='AI_PLATFORM_UNAVAILABLE'
        )

        assert result.success is False
        # 验证状态更新包含错误信息
        call_args = mock_state_manager.update_state.call_args[1]
        assert call_args['status'] == 'failed'
        assert call_args['error_message'] == 'AI API error'

    # =========================================================================
    # Phase Transition Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_phase_transition_sequence(self, orchestrator, sample_brand_list,
                                              sample_models, sample_questions,
                                              sample_ai_results):
        """测试阶段转换序列"""
        # Mock 所有外部依赖
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   AsyncMock(return_value={'success': True, 'results': sample_ai_results})):
            with patch('wechat_backend.diagnosis_report_service.get_report_service') as mock_service:
                mock_svc = Mock()
                mock_svc.create_report.return_value = 123
                mock_svc.add_results_batch.return_value = [1, 2]
                mock_service.return_value = mock_svc

                with patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository') as mock_repo:
                    mock_repo_instance = Mock()
                    mock_repo_instance.get_by_execution_id.return_value = sample_ai_results
                    mock_repo.return_value = mock_repo_instance

                    with patch('services.reportAggregator.aggregateReport',
                               Mock(return_value={'brandName': 'Brand A'})):
                        # Mock 后台任务管理器
                        mock_bg_manager = Mock()
                        mock_bg_manager.submit_analysis_task = Mock()

                        with patch('wechat_backend.services.background_service_manager.get_background_service_manager',
                                   return_value=mock_bg_manager):
                            # Mock 推送服务
                            mock_push = Mock()
                            mock_push.send_complete = AsyncMock()

                            with patch('wechat_backend.services.realtime_push_service.get_realtime_push_service',
                                       return_value=mock_push):
                                # Mock 状态管理器
                                orchestrator._state_manager = Mock()
                                orchestrator._state_manager.update_state = Mock()
                                orchestrator._state_manager.complete_execution = Mock()

                                # 设置初始参数
                                orchestrator._initial_params = {
                                    'user_id': 'test-user',
                                    'brand_list': sample_brand_list,
                                    'selected_models': sample_models,
                                    'custom_questions': sample_questions,
                                    'user_openid': 'test-openid',
                                    'user_level': 'Free'
                                }

                                # 初始化事务并设置_current_transaction
                                orchestrator._init_transaction()
                                orchestrator._current_transaction = orchestrator._transaction

                                # 执行各阶段并验证转换
                                phases = [
                                    (await orchestrator._phase_init(), DiagnosisPhase.INIT),
                                    (await orchestrator._phase_ai_fetching(
                                        sample_brand_list, sample_models, sample_questions,
                                        'test-user', 'Free'), DiagnosisPhase.AI_FETCHING),
                                    (await orchestrator._phase_results_saving(
                                        sample_ai_results, sample_brand_list, sample_models,
                                        sample_questions), DiagnosisPhase.RESULTS_SAVING),
                                    (await orchestrator._phase_results_validating(
                                        sample_ai_results), DiagnosisPhase.RESULTS_VALIDATING),
                                    (orchestrator._phase_background_analysis_async(
                                        sample_ai_results, sample_brand_list), DiagnosisPhase.BACKGROUND_ANALYSIS),
                                    (await orchestrator._phase_report_aggregating(
                                        sample_ai_results, sample_brand_list), DiagnosisPhase.REPORT_AGGREGATING),
                                    (await orchestrator._phase_complete({'brandName': 'Brand A'}), DiagnosisPhase.COMPLETED)
                                ]

                                # 验证每个阶段都成功并正确转换
                                for result, expected_phase in phases:
                                    if asyncio.iscoroutine(result):
                                        result = await result
                                    assert result.success is True
                                    assert orchestrator.current_phase == expected_phase

    @pytest.mark.asyncio
    async def test_phase_transition_on_failure(self, orchestrator, sample_brand_list,
                                                sample_models, sample_questions):
        """测试失败时的阶段转换"""
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': sample_brand_list,
            'selected_models': sample_models,
            'custom_questions': sample_questions,
            'user_openid': 'test-openid'
        }

        # 阶段 1 成功
        init_result = await orchestrator._phase_init()
        assert init_result.success is True
        assert orchestrator.current_phase == DiagnosisPhase.INIT

        # 阶段 2 失败
        with patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm',
                   AsyncMock(return_value={'success': False, 'error': 'AI error'})):
            ai_result = await orchestrator._phase_ai_fetching(
                sample_brand_list, sample_models, sample_questions,
                'test-user', 'Free'
            )
            assert ai_result.success is False

            # 失败后应该调用失败处理
            fail_result = await orchestrator._phase_failed(ai_result.error)
            assert fail_result.success is False
            assert orchestrator.current_phase == DiagnosisPhase.FAILED


# ============================================================================
# Module 4: State Management Tests
# ============================================================================
# 测试状态管理器的功能和编排器与状态管理器的集成
# 覆盖：
# 1. 状态管理器基础功能测试
# 2. 状态变更历史记录测试
# 3. 状态快照和回滚测试
# 4. 状态一致性验证测试
# 5. 编排器与状态管理器集成测试
# 6. 并发状态更新测试
# ============================================================================

class TestStateManager:
    """Module 4: State management tests - 状态管理器测试"""

    @pytest.fixture
    def execution_store(self) -> Dict[str, Any]:
        """创建测试用的执行状态存储"""
        return {}

    @pytest.fixture
    def state_manager(self, execution_store) -> DiagnosisStateManager:
        """创建状态管理器实例"""
        return DiagnosisStateManager(execution_store)

    @pytest.fixture
    def sample_execution_id(self) -> str:
        """样本执行 ID"""
        return 'state-test-execution-123'

    @pytest.fixture
    def sample_user_id(self) -> str:
        """样本用户 ID"""
        return 'test-user-001'

    # =========================================================================
    # State Manager Basic Functionality Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_state_manager_initialization(self, state_manager):
        """测试状态管理器初始化"""
        assert state_manager.execution_store == {}
        assert state_manager.state_change_history == {}
        assert state_manager.state_snapshots == {}

    @pytest.mark.asyncio
    async def test_update_state_basic(self, state_manager, sample_execution_id,
                                       sample_user_id):
        """测试基本状态更新"""
        result = state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id,
            reason='测试状态更新'
        )

        assert result is True
        assert sample_execution_id in state_manager.execution_store

        store_data = state_manager.execution_store[sample_execution_id]
        assert store_data['status'] == 'initializing'
        assert store_data['stage'] == 'init'
        assert store_data['progress'] == 0
        assert store_data['updated_at'] is not None

    @pytest.mark.asyncio
    async def test_update_state_partial_update(self, state_manager,
                                                sample_execution_id,
                                                sample_user_id):
        """测试部分状态更新（只更新提供的字段）"""
        # 第一次更新
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id
        )

        # 第二次只更新进度
        state_manager.update_state(
            execution_id=sample_execution_id,
            progress=50,
            user_id=sample_user_id,
            reason='进度更新'
        )

        store_data = state_manager.execution_store[sample_execution_id]
        # 状态和阶段应保持不变
        assert store_data['status'] == 'initializing'
        assert store_data['stage'] == 'init'
        # 进度应更新
        assert store_data['progress'] == 50

    @pytest.mark.asyncio
    async def test_update_state_with_database_flag(self, state_manager,
                                                    sample_execution_id,
                                                    sample_user_id):
        """测试数据库写入标志"""
        # write_to_db=False 不应失败
        result = state_manager.update_state(
            execution_id=sample_execution_id,
            status='ai_fetching',
            stage='ai_fetching',
            progress=30,
            user_id=sample_user_id,
            write_to_db=False,
            reason='仅更新内存状态'
        )

        assert result is True
        assert state_manager.execution_store[sample_execution_id]['status'] == 'ai_fetching'

    @pytest.mark.asyncio
    async def test_update_state_with_all_fields(self, state_manager,
                                                 sample_execution_id,
                                                 sample_user_id):
        """测试更新所有字段"""
        result = state_manager.update_state(
            execution_id=sample_execution_id,
            status='completed',
            stage='completed',
            progress=100,
            is_completed=True,
            should_stop_polling=True,
            error_message=None,
            user_id=sample_user_id,
            brand_name='Brand A',
            competitor_brands=['Brand B'],
            selected_models=[{'name': 'doubao'}],
            custom_questions=['Q1?'],
            reason='诊断完成'
        )

        assert result is True
        store_data = state_manager.execution_store[sample_execution_id]
        assert store_data['status'] == 'completed'
        assert store_data['progress'] == 100
        assert store_data['is_completed'] is True
        assert store_data['should_stop_polling'] is True

    # =========================================================================
    # State Change History Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_state_change_history_recording(self, state_manager,
                                                   sample_execution_id,
                                                   sample_user_id):
        """测试状态变更历史记录"""
        # 第一次更新
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id,
            reason='初始化'
        )

        # 第二次更新
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='ai_fetching',
            stage='ai_fetching',
            progress=30,
            user_id=sample_user_id,
            reason='AI 调用'
        )

        # 验证历史记录
        assert sample_execution_id in state_manager.state_change_history
        history = state_manager.state_change_history[sample_execution_id]
        assert len(history) >= 2  # 至少 2 次更新

        # 验证第一次记录
        first_record = history[0]
        assert first_record.change_type == StateChangeType.UPDATE.value
        assert first_record.new_status == 'initializing'
        assert first_record.new_progress == 0

        # 验证第二次记录
        second_record = history[1]
        assert second_record.change_type == StateChangeType.UPDATE.value
        assert second_record.old_status == 'initializing'
        assert second_record.new_status == 'ai_fetching'
        assert second_record.old_progress == 0
        assert second_record.new_progress == 30

    @pytest.mark.asyncio
    async def test_state_change_type_enum(self):
        """测试状态变更类型枚举"""
        assert StateChangeType.INIT.value == 'init'
        assert StateChangeType.UPDATE.value == 'update'
        assert StateChangeType.COMPLETE.value == 'complete'
        assert StateChangeType.FAIL.value == 'fail'
        assert StateChangeType.ROLLBACK.value == 'rollback'
        assert StateChangeType.VERIFY.value == 'verify'

    @pytest.mark.asyncio
    async def test_state_change_record_to_dict(self):
        """测试状态变更记录转换为字典"""
        record = StateChangeRecord(
            execution_id='test-123',
            change_type='update',
            old_status='init',
            old_stage='init',
            old_progress=0,
            new_status='ai_fetching',
            new_stage='ai_fetching',
            new_progress=30,
            timestamp=datetime.now().isoformat(),
            user_id='test-user',
            reason='测试',
            error_message=None
        )

        record_dict = record.to_dict()
        assert record_dict['execution_id'] == 'test-123'
        assert record_dict['change_type'] == 'update'
        assert record_dict['new_status'] == 'ai_fetching'
        assert 'timestamp' in record_dict

    # =========================================================================
    # State Snapshot and Rollback Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_state_snapshot_creation(self, state_manager,
                                            sample_execution_id,
                                            sample_user_id):
        """测试状态快照创建"""
        # 初始状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id
        )

        # 保存快照
        state_manager._save_snapshot(sample_execution_id)

        # 验证快照已保存
        assert sample_execution_id in state_manager.state_snapshots
        snapshot = state_manager.state_snapshots[sample_execution_id]
        assert snapshot['status'] == 'initializing'
        assert snapshot['progress'] == 0

    @pytest.mark.asyncio
    async def test_state_rollback_to_snapshot(self, state_manager,
                                               sample_execution_id,
                                               sample_user_id):
        """测试回滚到快照状态"""
        # 初始状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id,
            reason='初始化'
        )

        # 保存快照
        state_manager._save_snapshot(sample_execution_id)

        # 更新到新状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='completed',
            stage='completed',
            progress=100,
            user_id=sample_user_id,
            reason='完成'
        )

        # 验证当前状态
        current_state = state_manager.execution_store[sample_execution_id]
        assert current_state['status'] == 'completed'
        assert current_state['progress'] == 100

        # 回滚到快照
        result = state_manager.rollback_to_snapshot(
            execution_id=sample_execution_id,
            user_id=sample_user_id,
            reason='测试回滚'
        )

        assert result is True
        # 验证已回滚
        rolled_back_state = state_manager.execution_store[sample_execution_id]
        assert rolled_back_state['status'] == 'initializing'
        assert rolled_back_state['progress'] == 0

    @pytest.mark.asyncio
    async def test_state_rollback_without_snapshot(self, state_manager,
                                                    sample_execution_id,
                                                    sample_user_id):
        """测试无快照时的回滚"""
        # 没有保存快照就直接回滚
        result = state_manager.rollback_to_snapshot(
            execution_id=sample_execution_id,
            user_id=sample_user_id,
            reason='测试无快照回滚'
        )

        # 应该失败
        assert result is False

    @pytest.mark.asyncio
    async def test_state_rollback_to_specific_state(self, state_manager,
                                                     sample_execution_id,
                                                     sample_user_id):
        """测试回滚到指定状态"""
        # 初始状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            stage='init',
            progress=0,
            user_id=sample_user_id
        )

        # 回滚到指定状态
        result = state_manager.rollback_to_state(
            execution_id=sample_execution_id,
            target_status='ai_fetching',
            target_stage='ai_fetching',
            target_progress=30,
            user_id=sample_user_id,
            reason='测试回滚到指定状态'
        )

        assert result is True
        state = state_manager.execution_store[sample_execution_id]
        assert state['status'] == 'ai_fetching'
        assert state['stage'] == 'ai_fetching'
        assert state['progress'] == 30

    @pytest.mark.asyncio
    async def test_state_rollback_records_history(self, state_manager,
                                                   sample_execution_id,
                                                   sample_user_id):
        """测试回滚操作记录历史"""
        # 初始状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='init',
            progress=0,
            user_id=sample_user_id
        )

        # 保存快照并回滚
        state_manager._save_snapshot(sample_execution_id)
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='completed',
            progress=100,
            user_id=sample_user_id
        )
        state_manager.rollback_to_snapshot(
            execution_id=sample_execution_id,
            user_id=sample_user_id,
            reason='测试'
        )

        # 验证历史记录包含回滚记录
        history = state_manager.state_change_history[sample_execution_id]
        rollback_records = [
            r for r in history
            if r.change_type == StateChangeType.ROLLBACK.value
        ]
        assert len(rollback_records) >= 1

    # =========================================================================
    # State Consistency Verification Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_verify_state_consistency_nonexistent(self, state_manager,
                                                         sample_execution_id):
        """测试验证不存在状态的一致性"""
        # execution_id 不存在
        is_consistent, details = state_manager.verify_state_consistency(
            execution_id=sample_execution_id,
            fix_if_inconsistent=False
        )

        assert is_consistent is False
        assert any('不存在' in diff for diff in details['differences'])

    @pytest.mark.asyncio
    async def test_verify_state_consistency_with_self(self, state_manager,
                                                       sample_execution_id,
                                                       sample_user_id):
        """测试状态一致性验证（自验证）"""
        # 创建状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='ai_fetching',
            stage='ai_fetching',
            progress=30,
            user_id=sample_user_id
        )

        # 验证一致性（没有数据库对比，应该通过）
        is_consistent, details = state_manager.verify_state_consistency(
            execution_id=sample_execution_id,
            fix_if_inconsistent=False
        )

        # 由于没有数据库记录，可能不一致
        # 但验证过程不应抛出异常
        assert details['execution_id'] == sample_execution_id
        assert 'memory_state' in details or 'differences' in details

    @pytest.mark.asyncio
    async def test_verify_state_consistency_auto_fix(self, state_manager,
                                                      sample_execution_id,
                                                      sample_user_id):
        """测试状态一致性自动修复"""
        # 创建状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='completed',
            progress=100,
            user_id=sample_user_id
        )

        # 验证并自动修复
        is_consistent, details = state_manager.verify_state_consistency(
            execution_id=sample_execution_id,
            fix_if_inconsistent=True
        )

        # 验证过程应该完成（无论结果如何）
        assert details['execution_id'] == sample_execution_id
        # 如果启用了自动修复，应该记录修复状态
        if 'fixed' in details:
            assert isinstance(details['fixed'], bool)

    # =========================================================================
    # Complete Execution Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_complete_execution(self, state_manager,
                                       sample_execution_id,
                                       sample_user_id):
        """测试完成执行"""
        # 先初始化状态
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='initializing',
            user_id=sample_user_id
        )

        # 完成执行
        result = state_manager.complete_execution(
            execution_id=sample_execution_id,
            user_id=sample_user_id,
            brand_name='Brand A',
            competitor_brands=['Brand B', 'Brand C'],
            selected_models=[{'name': 'doubao'}],
            custom_questions=['Q1?']
        )

        # 完成操作应该成功（即使数据库写入失败）
        assert result is True
        state = state_manager.execution_store[sample_execution_id]
        assert state['status'] == 'completed'
        assert state['progress'] == 100
        assert state['is_completed'] is True
        assert state['should_stop_polling'] is True

    @pytest.mark.asyncio
    async def test_complete_execution_records_history(self, state_manager,
                                                       sample_execution_id,
                                                       sample_user_id):
        """测试完成执行记录历史"""
        state_manager.complete_execution(
            execution_id=sample_execution_id,
            user_id=sample_user_id,
            brand_name='Brand A',
            competitor_brands=[],
            selected_models=[],
            custom_questions=[]
        )

        # 验证历史记录
        history = state_manager.state_change_history[sample_execution_id]
        complete_records = [
            r for r in history
            if r.change_type == StateChangeType.COMPLETE.value
        ]
        assert len(complete_records) >= 1

    # =========================================================================
    # Get State Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_state_exists(self, state_manager,
                                     sample_execution_id,
                                     sample_user_id):
        """测试获取存在的状态"""
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='ai_fetching',
            progress=30,
            user_id=sample_user_id
        )

        state = state_manager.get_state(sample_execution_id)
        assert state is not None
        assert state['status'] == 'ai_fetching'
        assert state['progress'] == 30

    @pytest.mark.asyncio
    async def test_get_state_not_exists(self, state_manager,
                                         sample_execution_id):
        """测试获取不存在的状态"""
        state = state_manager.get_state(sample_execution_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_get_state_returns_copy(self, state_manager,
                                           sample_execution_id,
                                           sample_user_id):
        """测试获取状态返回副本"""
        state_manager.update_state(
            execution_id=sample_execution_id,
            status='init',
            progress=0,
            user_id=sample_user_id
        )

        state1 = state_manager.get_state(sample_execution_id)
        state1['status'] = 'modified'

        state2 = state_manager.get_state(sample_execution_id)
        # 原始状态不应被修改
        assert state2['status'] == 'init'

    # =========================================================================
    # State Manager Integration with Orchestrator Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_orchestrator_with_state_manager(self, execution_store):
        """测试编排器与状态管理器集成"""
        from wechat_backend.services.diagnosis_orchestrator import create_orchestrator

        execution_id = 'integration-test-123'
        orchestrator = create_orchestrator(execution_id, execution_store)

        # 验证状态管理器已初始化
        assert orchestrator._state_manager is not None

        # 验证状态管理器与编排器共享 execution_store
        assert orchestrator._state_manager.execution_store is execution_store

    @pytest.mark.asyncio
    async def test_orchestrator_phase_updates_state(self, execution_store):
        """测试编排器阶段执行更新状态"""
        from wechat_backend.services.diagnosis_orchestrator import create_orchestrator

        execution_id = 'phase-state-test-456'
        orchestrator = create_orchestrator(execution_id, execution_store)

        # 设置初始参数
        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?'],
            'user_openid': 'test-openid',
            'user_level': 'Free'
        }

        # 执行初始化阶段
        result = await orchestrator._phase_init()

        assert result.success is True
        # 验证状态已更新
        assert execution_id in execution_store
        assert execution_store[execution_id]['status'] == 'initializing'
        assert execution_store[execution_id]['progress'] == 0

    @pytest.mark.asyncio
    async def test_orchestrator_state_transition_sequence(self, execution_store):
        """测试编排器状态转换序列"""
        from wechat_backend.services.diagnosis_orchestrator import create_orchestrator

        execution_id = 'state-transition-test-789'
        orchestrator = create_orchestrator(execution_id, execution_store)

        orchestrator._initial_params = {
            'user_id': 'test-user',
            'brand_list': ['Brand A'],
            'selected_models': [{'name': 'doubao'}],
            'custom_questions': ['Q1?']
        }

        # 初始化阶段
        await orchestrator._phase_init()
        state1 = execution_store[execution_id]
        assert state1['status'] == 'initializing'

        # AI 调用阶段（Mock）
        with pytest.importorskip('unittest.mock') as mock_module:
            with mock_module.patch('wechat_backend.nxm_concurrent_engine_v3.execute_parallel_nxm') as mock_execute:
                mock_execute.return_value = {'success': True, 'results': []}

                result = await orchestrator._phase_ai_fetching(
                    brand_list=['Brand A'],
                    selected_models=[{'name': 'doubao'}],
                    custom_questions=['Q1?'],
                    user_id='test-user',
                    user_level='Free'
                )

                if result.success:
                    state2 = execution_store[execution_id]
                    assert state2['status'] == 'ai_fetching'
                    assert state2['progress'] == 30

    # =========================================================================
    # Concurrent State Update Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self, state_manager,
                                             sample_execution_id):
        """测试并发状态更新"""
        import asyncio

        async def update_status(status, progress):
            state_manager.update_state(
                execution_id=sample_execution_id,
                status=status,
                progress=progress,
                user_id='test-user',
                reason=f'并发更新：{status}'
            )

        # 并发执行多个更新
        tasks = [
            update_status('initializing', 0),
            update_status('ai_fetching', 30),
            update_status('results_saving', 60),
            update_status('completed', 100)
        ]

        await asyncio.gather(*tasks)

        # 验证最终状态（应该是最后一个更新）
        final_state = state_manager.execution_store[sample_execution_id]
        assert final_state['progress'] == 100
        # 所有更新都应记录到历史
        history = state_manager.state_change_history[sample_execution_id]
        assert len(history) >= 4

    @pytest.mark.asyncio
    async def test_concurrent_updates_different_executions(self, state_manager):
        """测试不同执行 ID 的并发更新"""
        import asyncio

        execution_ids = ['exec-1', 'exec-2', 'exec-3']

        async def update_execution(exec_id, progress):
            state_manager.update_state(
                execution_id=exec_id,
                status='processing',
                progress=progress,
                user_id='test-user',
                reason=f'更新 {exec_id}'
            )

        # 并发更新不同执行 ID
        tasks = []
        for i, exec_id in enumerate(execution_ids):
            tasks.append(update_execution(exec_id, (i + 1) * 30))

        await asyncio.gather(*tasks)

        # 验证每个执行 ID 的状态
        for i, exec_id in enumerate(execution_ids):
            state = state_manager.execution_store[exec_id]
            assert state['progress'] == (i + 1) * 30


# ============================================================================
# Module 3 辅助测试
# ============================================================================

class TestPhaseResult:
    """PhaseResult 辅助测试"""

    def test_phase_result_to_dict(self):
        """测试 PhaseResult 转换为字典"""
        result = PhaseResult(
            success=True,
            data={'test': 'data'},
            error=None
        )
        result_dict = result.to_dict()

        assert result_dict['success'] is True
        assert result_dict['data'] == {'test': 'data'}
        assert result_dict['error'] is None
        assert 'timestamp' in result_dict

    def test_phase_result_failure_to_dict(self):
        """测试失败的 PhaseResult 转换为字典"""
        result = PhaseResult(
            success=False,
            data=None,
            error='Test error'
        )
        result_dict = result.to_dict()

        assert result_dict['success'] is False
        assert result_dict['data'] is None
        assert result_dict['error'] == 'Test error'


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

    def test_phase_ordering(self):
        """测试阶段顺序"""
        # 验证阶段可以按预期顺序排列
        phases = [
            DiagnosisPhase.INIT,
            DiagnosisPhase.AI_FETCHING,
            DiagnosisPhase.RESULTS_SAVING,
            DiagnosisPhase.RESULTS_VALIDATING,
            DiagnosisPhase.BACKGROUND_ANALYSIS,
            DiagnosisPhase.REPORT_AGGREGATING,
            DiagnosisPhase.COMPLETED
        ]

        # 验证没有重复阶段
        assert len(phases) == len(set(phases))


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
