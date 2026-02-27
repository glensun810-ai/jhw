"""
报告存根服务单元测试

测试覆盖率目标：> 90%

测试范围:
1. StubReport 模型测试
2. ReportStubService 基本功能测试
3. 存根生成逻辑测试
4. 状态判断测试
5. 建议增强测试

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

from wechat_backend.v2.services.report_stub_service import ReportStubService
from wechat_backend.v2.models.report_stub import StubReport, ReportStatus
from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository


# ==================== Fixture ====================

@pytest.fixture
def mock_diagnosis_repo():
    """模拟诊断仓库"""
    repo = Mock(spec=DiagnosisRepository)
    repo.get_by_execution_id = Mock(return_value=None)
    repo.get_expected_results_count = Mock(return_value=0)
    repo.get_status_summary = Mock(return_value={})
    repo.get_by_user_id = Mock(return_value=[])
    return repo


@pytest.fixture
def mock_result_repo():
    """模拟诊断结果仓库"""
    repo = Mock(spec=DiagnosisResultRepository)
    repo.get_by_execution_id = Mock(return_value=[])
    return repo


@pytest.fixture
def stub_service(mock_diagnosis_repo, mock_result_repo):
    """创建报告存根服务实例"""
    return ReportStubService(
        diagnosis_repo=mock_diagnosis_repo,
        result_repo=mock_result_repo,
    )


@pytest.fixture
def sample_diagnosis_record() -> Dict[str, Any]:
    """示例诊断记录"""
    return {
        'id': 123,
        'execution_id': 'exec-123',
        'brand_name': '测试品牌',
        'status': 'completed',
        'stage': 'completed',
        'progress': 100,
        'is_completed': True,
        'should_stop_polling': True,
        'error_message': None,
        'error_details': None,
        'created_at': datetime.now().isoformat(),
        'completed_at': datetime.now().isoformat(),
        'expected_results_count': 6,
    }


@pytest.fixture
def sample_partial_results() -> List[Dict[str, Any]]:
    """示例部分结果"""
    return [
        {
            'brand': '测试品牌',
            'question': '问题 1',
            'model': 'deepseek',
            'response': {'content': '回答 1'},
            'geo_data': {'sentiment': 'positive', 'exposure': True},
            'keywords': ['质量', '好评'],
            'error_message': None,
        },
        {
            'brand': '测试品牌',
            'question': '问题 2',
            'model': 'doubao',
            'response': {'content': '回答 2'},
            'geo_data': {'sentiment': 'neutral', 'exposure': True},
            'keywords': ['产品', '服务'],
            'error_message': None,
        },
        {
            'brand': '竞品 A',
            'question': '问题 1',
            'model': 'qwen',
            'response': {},
            'geo_data': {},
            'keywords': [],
            'error_message': 'API 调用失败',
        },
    ]


# ==================== StubReport 模型测试 ====================

class TestStubReportModel:
    """StubReport 模型测试"""

    def test_create_basic_stub(self):
        """测试创建基本存根"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.FAILED,
            progress=0,
            stage='failed',
            created_at=datetime.now(),
            error_message='测试错误',
        )

        assert stub.execution_id == 'exec-123'
        assert stub.report_id is None
        assert stub.brand_name == '测试品牌'
        assert stub.status == ReportStatus.FAILED
        assert stub.is_stub is True
        assert stub.has_data is False

    def test_create_stub_with_partial_results(self, sample_partial_results):
        """测试创建带部分结果的存根"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.PARTIAL_SUCCESS,
            progress=75,
            stage='completed',
            created_at=datetime.now(),
            partial_results=sample_partial_results,
            results_count=len(sample_partial_results),
            successful_count=2,
            data_completeness=33.33,
            has_data=True,
        )

        assert stub.results_count == 3
        assert stub.successful_count == 2
        assert stub.data_completeness == 33.33
        assert stub.has_data is True

    def test_to_dict(self, sample_partial_results):
        """测试转换为字典"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.PARTIAL_SUCCESS,
            created_at=datetime.now(),
            partial_results=sample_partial_results,
            results_count=3,
            successful_count=2,
            data_completeness=33.33,
            has_data=True,
        )

        result = stub.to_dict()

        assert 'report' in result
        assert 'results' in result
        assert 'analysis' in result
        assert 'meta' in result
        assert result['report']['execution_id'] == 'exec-123'
        assert result['meta']['is_stub'] is True
        assert result['meta']['data_completeness'] == 33.33

    def test_calculate_brand_distribution(self, sample_partial_results):
        """测试品牌分布计算"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.PARTIAL_SUCCESS,
            created_at=datetime.now(),
            partial_results=sample_partial_results,
        )

        distribution = stub._calculate_brand_distribution()

        assert '测试品牌' in distribution
        assert '竞品 A' in distribution
        assert distribution['测试品牌'] > 0

    def test_calculate_sentiment_distribution(self, sample_partial_results):
        """测试情感分布计算"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.PARTIAL_SUCCESS,
            created_at=datetime.now(),
            partial_results=sample_partial_results,
        )

        distribution = stub._calculate_sentiment_distribution()

        assert 'positive' in distribution
        assert 'neutral' in distribution
        assert 'negative' in distribution

    def test_extract_keywords(self, sample_partial_results):
        """测试关键词提取"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.PARTIAL_SUCCESS,
            created_at=datetime.now(),
            partial_results=sample_partial_results,
        )

        keywords = stub._extract_keywords(top_n=5)

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        if keywords:
            assert 'word' in keywords[0]
            assert 'count' in keywords[0]

    def test_from_diagnosis_record_completed(self, sample_diagnosis_record):
        """测试从诊断记录创建（完成状态）"""
        stub = StubReport.from_diagnosis_record(
            execution_id='exec-123',
            diagnosis_record=sample_diagnosis_record,
            partial_results=[],
        )

        assert stub.status == ReportStatus.COMPLETED
        assert stub.report_id == 123
        assert stub.brand_name == '测试品牌'
        assert stub.is_stub is True

    def test_from_diagnosis_record_failed(self):
        """测试从诊断记录创建（失败状态）"""
        record = {
            'id': 123,
            'execution_id': 'exec-123',
            'brand_name': '测试品牌',
            'status': 'failed',
            'stage': 'ai_fetching',
            'progress': 30,
            'is_completed': True,
            'error_message': 'API 调用失败',
            'error_details': {'type': 'AuthenticationError'},
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
        }

        stub = StubReport.from_diagnosis_record(
            execution_id='exec-123',
            diagnosis_record=record,
            partial_results=[],
        )

        assert stub.status == ReportStatus.FAILED
        assert stub.error_message == 'API 调用失败'
        assert stub.retry_suggestion is not None

    def test_from_diagnosis_record_timeout(self):
        """测试从诊断记录创建（超时状态）"""
        record = {
            'id': 123,
            'execution_id': 'exec-123',
            'brand_name': '测试品牌',
            'status': 'timeout',
            'stage': 'ai_fetching',
            'progress': 50,
            'is_completed': True,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
        }

        stub = StubReport.from_diagnosis_record(
            execution_id='exec-123',
            diagnosis_record=record,
            partial_results=[],
        )

        assert stub.status == ReportStatus.TIMEOUT
        assert '超时' in stub.retry_suggestion

    def test_create_for_not_found(self):
        """测试创建"不存在"存根"""
        stub = StubReport.create_for_not_found(execution_id='exec-nonexistent')

        assert stub.status == ReportStatus.FAILED
        assert stub.stage == 'not_found'
        assert '未找到' in stub.error_message
        assert stub.has_data is False


# ==================== ReportStubService 测试 ====================

class TestReportStubService:
    """报告存根服务测试"""

    def test_get_stub_report_not_found(self, stub_service, mock_diagnosis_repo):
        """测试获取存根报告（记录不存在）"""
        mock_diagnosis_repo.get_by_execution_id.return_value = None

        stub = stub_service.get_stub_report(execution_id='exec-nonexistent')

        assert stub.status == ReportStatus.FAILED
        assert stub.stage == 'not_found'
        assert stub.has_data is False
        assert '未找到' in stub.error_message

    def test_get_stub_report_with_record(self, stub_service, mock_diagnosis_repo, sample_diagnosis_record):
        """测试获取存根报告（有诊断记录）"""
        mock_diagnosis_repo.get_by_execution_id.return_value = sample_diagnosis_record

        stub = stub_service.get_stub_report(execution_id='exec-123')

        assert stub is not None
        assert stub.execution_id == 'exec-123'
        assert stub.brand_name == '测试品牌'

    def test_get_stub_report_with_partial_results(
        self,
        stub_service,
        mock_diagnosis_repo,
        mock_result_repo,
        sample_diagnosis_record,
        sample_partial_results,
    ):
        """测试获取存根报告（带部分结果）"""
        mock_diagnosis_repo.get_by_execution_id.return_value = sample_diagnosis_record

        # 模拟返回结果对象
        mock_result = Mock()
        mock_result.to_dict = Mock(return_value=sample_partial_results[0])
        mock_result_repo.get_by_execution_id.return_value = [mock_result]

        stub = stub_service.get_stub_report(
            execution_id='exec-123',
            include_partial_results=True,
        )

        assert stub is not None
        assert stub.partial_results is not None

    def test_get_stub_for_failed_task(self, stub_service):
        """测试为失败任务创建存根"""
        stub = stub_service.get_stub_for_failed_task(
            execution_id='exec-123',
            error_message='任务创建失败',
            error_details={'reason': 'invalid_config'},
        )

        assert stub.status == ReportStatus.FAILED
        assert stub.error_message == '任务创建失败'
        assert stub.has_data is False
        assert stub.is_stub is True

    def test_get_stub_for_timeout(self, stub_service):
        """测试为超时任务创建存根"""
        stub = stub_service.get_stub_for_timeout(
            execution_id='exec-123',
            diagnosis_record=None,
            partial_results=[],
        )

        assert stub.status == ReportStatus.TIMEOUT
        assert '超时' in stub.error_message
        assert '减少选择的 AI 模型' in stub.retry_suggestion

    def test_get_stub_for_timeout_with_record(
        self,
        stub_service,
        sample_diagnosis_record,
        sample_partial_results,
    ):
        """测试为超时任务创建存根（有诊断记录）"""
        sample_diagnosis_record['status'] = 'timeout'

        stub = stub_service.get_stub_for_timeout(
            execution_id='exec-123',
            diagnosis_record=sample_diagnosis_record,
            partial_results=sample_partial_results,
        )

        assert stub.status == ReportStatus.TIMEOUT
        assert stub.partial_results is not None
        assert len(stub.partial_results) == 3

    def test_enhance_with_suggestions_timeout(self, stub_service):
        """测试超时场景的建议增强"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.TIMEOUT,
            created_at=datetime.now(),
            next_steps=[],  # 清空默认建议以便测试
        )

        enhanced = stub_service.enhance_with_suggestions(stub, user_history=[])

        assert len(enhanced.next_steps) > 0
        assert any('AI 模型' in s for s in enhanced.next_steps)

    def test_enhance_with_suggestions_failed(self, stub_service):
        """测试失败场景的建议增强"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.FAILED,
            created_at=datetime.now(),
            error_message='API key 无效',
        )

        enhanced = stub_service.enhance_with_suggestions(stub, user_history=[])

        assert any('API 密钥' in s or 'API key' in s for s in enhanced.next_steps)

    def test_enhance_with_suggestions_with_history(self, stub_service):
        """测试带用户历史的建议增强"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.FAILED,
            created_at=datetime.now(),
        )

        user_history = [
            {
                'status': 'completed',
                'created_at': '2026-02-27T10:00:00',
            }
        ]

        enhanced = stub_service.enhance_with_suggestions(stub, user_history=user_history)

        assert any('上次成功诊断' in s for s in enhanced.next_steps)

    def test_should_return_stub_true_when_none(self, stub_service):
        """测试无数据时应返回存根"""
        assert stub_service.should_return_stub(None) is True

    def test_should_return_stub_true_when_empty(self, stub_service):
        """测试空数据时应返回存根"""
        assert stub_service.should_return_stub({'results': [], 'analysis': {}}) is True

    def test_should_return_stub_true_when_failed(self, stub_service):
        """测试失败状态应返回存根"""
        report = {
            'report': {'status': 'failed'},
            'results': [],
            'analysis': {},
        }
        assert stub_service.should_return_stub(report) is True

    def test_should_return_stub_false_when_complete(self, stub_service):
        """测试完整报告不应返回存根"""
        report = {
            'report': {'status': 'completed'},
            'results': [{'brand': '测试品牌'}],
            'analysis': {'brand_distribution': {'测试品牌': 100}},
        }
        assert stub_service.should_return_stub(report) is False

    def test_get_user_history(self, stub_service, mock_diagnosis_repo):
        """测试获取用户历史"""
        mock_diagnosis_repo.get_by_user_id.return_value = [
            {'id': 1, 'brand_name': '品牌 1', 'status': 'completed'},
        ]

        history = stub_service.get_user_history(user_id='user-123', limit=5)

        assert isinstance(history, list)
        mock_diagnosis_repo.get_by_user_id.assert_called_once_with('user-123', limit=5)


# ==================== 边界条件测试 ====================

class TestBoundaryConditions:
    """边界条件测试"""

    def test_stub_with_zero_completeness(self):
        """测试零完整度存根"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.FAILED,
            created_at=datetime.now(),
            data_completeness=0.0,
        )

        assert stub.data_completeness == 0.0
        assert stub.has_data is False

    def test_stub_with_full_completeness(self):
        """测试完整度 100% 存根"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=123,
            brand_name='测试品牌',
            status=ReportStatus.COMPLETED,
            created_at=datetime.now(),
            data_completeness=100.0,
            has_data=True,
        )

        assert stub.data_completeness == 100.0
        assert stub.has_data is True

    def test_stub_with_empty_partial_results(self):
        """测试空部分结果存根"""
        stub = StubReport(
            execution_id='exec-123',
            report_id=None,
            brand_name='测试品牌',
            status=ReportStatus.FAILED,
            created_at=datetime.now(),
            partial_results=[],
        )

        assert stub.partial_results == []
        assert stub.results_count == 0
        assert stub._calculate_brand_distribution() == {}

    def test_stub_with_invalid_time_in_record(self):
        """测试诊断记录中时间格式无效"""
        record = {
            'id': 123,
            'execution_id': 'exec-123',
            'brand_name': '测试品牌',
            'status': 'failed',
            'created_at': 'invalid-date',
            'completed_at': 'also-invalid',
        }

        # 不应该抛出异常
        stub = StubReport.from_diagnosis_record(
            execution_id='exec-123',
            diagnosis_record=record,
            partial_results=[],
        )

        assert stub is not None
        assert isinstance(stub.created_at, datetime)


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""

    def test_full_stub_generation_flow(self):
        """测试完整的存根生成流程"""
        # 创建真实服务（使用模拟仓库）
        diagnosis_repo = Mock(spec=DiagnosisRepository)
        result_repo = Mock(spec=DiagnosisResultRepository)

        # 准备测试数据
        diagnosis_record = {
            'id': 123,
            'execution_id': 'exec-123',
            'brand_name': '测试品牌',
            'status': 'partial_success',
            'stage': 'completed',
            'progress': 75,
            'is_completed': True,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
        }

        diagnosis_repo.get_by_execution_id.return_value = diagnosis_record
        result_repo.get_by_execution_id.return_value = []

        service = ReportStubService(
            diagnosis_repo=diagnosis_repo,
            result_repo=result_repo,
        )

        # 执行测试
        stub = service.get_stub_report(execution_id='exec-123')

        # 验证结果
        assert stub is not None
        assert stub.execution_id == 'exec-123'
        assert stub.brand_name == '测试品牌'
        assert stub.status == ReportStatus.PARTIAL_SUCCESS
        assert stub.is_stub is True

        # 验证 to_dict
        result = stub.to_dict()
        assert result['report']['status'] == 'partial_success'
        assert result['meta']['is_stub'] is True
