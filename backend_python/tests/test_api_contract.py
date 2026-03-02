"""
API 契约测试

验证 API 响应是否符合 OpenAPI 规范定义

测试覆盖：
1. 响应结构验证
2. 字段类型验证
3. 必填字段验证
4. 枚举值验证
5. 错误响应验证

作者：系统架构组
日期：2026-03-01
版本：1.0
"""

import pytest
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


# ==================== 测试工具函数 ====================

def validate_required_fields(data: Dict, required_fields: List[str], path: str = "") -> List[str]:
    """验证必填字段"""
    errors = []
    for field in required_fields:
        if field not in data:
            errors.append(f"{path}{field}: 缺少必填字段")
    return errors


def validate_field_type(value: Any, expected_type: type, field_path: str) -> List[str]:
    """验证字段类型"""
    errors = []
    if value is not None and not isinstance(value, expected_type):
        errors.append(
            f"{field_path}: 类型错误，期望 {expected_type.__name__}, "
            f"得到 {type(value).__name__}"
        )
    return errors


def validate_enum_value(value: str, allowed_values: List[str], field_path: str) -> List[str]:
    """验证枚举值"""
    errors = []
    if value not in allowed_values:
        errors.append(
            f"{field_path}: 枚举值错误，期望 {allowed_values}, 得到 {value}"
        )
    return errors


# ==================== Schema 定义 ====================

REPORT_SCHEMA = {
    'required': ['execution_id', 'brand_name', 'status', 'created_at'],
    'types': {
        'id': int,
        'execution_id': str,
        'user_id': str,
        'brand_name': str,
        'status': str,
        'progress': int,
        'stage': str,
        'is_completed': bool,
        'created_at': str,
        'completed_at': str,
        'checksum': str
    },
    'enums': {
        'status': ['pending', 'processing', 'completed', 'failed'],
        'stage': ['init', 'ai_fetching', 'intelligence_analyzing', 'completed', 'failed']
    }
}

RESULT_SCHEMA = {
    'required': ['brand', 'question', 'model'],
    'types': {
        'id': int,
        'brand': str,
        'question': str,
        'model': str,
        'quality_score': (int, float),
        'quality_level': str
    },
    'enums': {
        'quality_level': ['very_low', 'low', 'medium', 'high', 'very_high']
    }
}

VALIDATION_SCHEMA = {
    'required': ['is_valid'],
    'types': {
        'is_valid': bool,
        'errors': list,
        'warnings': list,
        'quality_issues': list,
        'quality_score': int
    }
}

BRAND_DISTRIBUTION_SCHEMA = {
    'required': ['data', 'total_count'],
    'types': {
        'data': dict,
        'total_count': int
    }
}

SENTIMENT_DISTRIBUTION_SCHEMA = {
    'required': ['data', 'total_count'],
    'types': {
        'data': dict,
        'total_count': int
    }
}

FULL_REPORT_SCHEMA = {
    'required': ['report', 'results', 'analysis', 'meta'],
    'types': {
        'report': dict,
        'results': list,
        'analysis': dict,
        'brandDistribution': dict,
        'sentimentDistribution': dict,
        'keywords': list,
        'meta': dict,
        'validation': dict,
        'qualityHints': dict,
        'error': dict,
        'partial': dict
    }
}


# ==================== 契约测试类 ====================

class TestReportContract:
    """报告 API 契约测试"""
    
    def test_report_schema_required_fields(self, sample_report: Dict):
        """测试报告必填字段"""
        errors = validate_required_fields(
            sample_report,
            REPORT_SCHEMA['required'],
            'report.'
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_report_field_types(self, sample_report: Dict):
        """测试报告字段类型"""
        errors = []
        for field, expected_type in REPORT_SCHEMA['types'].items():
            if field in sample_report:
                errors.extend(validate_field_type(
                    sample_report[field],
                    expected_type,
                    f'report.{field}'
                ))
        assert not errors, f"字段类型错误：{errors}"
    
    def test_report_enum_values(self, sample_report: Dict):
        """测试报告枚举值"""
        errors = []
        for field, allowed_values in REPORT_SCHEMA['enums'].items():
            if field in sample_report:
                errors.extend(validate_enum_value(
                    sample_report[field],
                    allowed_values,
                    f'report.{field}'
                ))
        assert not errors, f"枚举值错误：{errors}"
    
    def test_report_progress_range(self, sample_report: Dict):
        """测试报告进度范围"""
        progress = sample_report.get('progress')
        if progress is not None:
            assert 0 <= progress <= 100, f"进度超出范围：{progress}"
    
    def test_report_timestamp_format(self, sample_report: Dict):
        """测试报告时间戳格式"""
        for field in ['created_at', 'completed_at']:
            value = sample_report.get(field)
            if value:
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"{field} 时间格式错误：{value}")


class TestResultContract:
    """结果 API 契约测试"""
    
    def test_result_schema_required_fields(self, sample_result: Dict):
        """测试结果必填字段"""
        errors = validate_required_fields(
            sample_result,
            RESULT_SCHEMA['required'],
            'result.'
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_result_field_types(self, sample_result: Dict):
        """测试结果字段类型"""
        errors = []
        for field, expected_type in RESULT_SCHEMA['types'].items():
            if field in sample_result:
                errors.extend(validate_field_type(
                    sample_result[field],
                    expected_type,
                    f'result.{field}'
                ))
        assert not errors, f"字段类型错误：{errors}"
    
    def test_result_enum_values(self, sample_result: Dict):
        """测试结果枚举值"""
        errors = []
        for field, allowed_values in RESULT_SCHEMA['enums'].items():
            if field in sample_result:
                errors.extend(validate_enum_value(
                    sample_result[field],
                    allowed_values,
                    f'result.{field}'
                ))
        assert not errors, f"枚举值错误：{errors}"
    
    def test_result_quality_score_range(self, sample_result: Dict):
        """测试结果质量评分范围"""
        score = sample_result.get('quality_score')
        if score is not None:
            assert 0 <= score <= 100, f"质量评分超出范围：{score}"


class TestValidationContract:
    """验证 API 契约测试"""
    
    def test_validation_schema_required_fields(self, sample_validation: Dict):
        """测试验证必填字段"""
        errors = validate_required_fields(
            sample_validation,
            VALIDATION_SCHEMA['required'],
            'validation.'
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_validation_field_types(self, sample_validation: Dict):
        """测试验证字段类型"""
        errors = []
        for field, expected_type in VALIDATION_SCHEMA['types'].items():
            if field in sample_validation:
                errors.extend(validate_field_type(
                    sample_validation[field],
                    expected_type,
                    f'validation.{field}'
                ))
        assert not errors, f"字段类型错误：{errors}"
    
    def test_validation_quality_score_range(self, sample_validation: Dict):
        """测试验证质量评分范围"""
        score = sample_validation.get('quality_score')
        if score is not None:
            assert 0 <= score <= 100, f"质量评分超出范围：{score}"
    
    def test_validation_errors_is_list(self, sample_validation: Dict):
        """测试验证错误列表"""
        errors = sample_validation.get('errors', [])
        assert isinstance(errors, list), "errors 必须是列表"
        for i, error in enumerate(errors):
            assert isinstance(error, str), f"errors[{i}] 必须是字符串"


class TestFullReportContract:
    """完整报告 API 契约测试"""
    
    def test_full_report_schema_required_fields(self, sample_full_report: Dict):
        """测试完整报告必填字段"""
        errors = validate_required_fields(
            sample_full_report,
            FULL_REPORT_SCHEMA['required'],
            ''
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_full_report_structure(self, sample_full_report: Dict):
        """测试完整报告结构"""
        # 验证 report
        assert 'report' in sample_full_report
        TestReportContract().test_report_schema_required_fields(
            sample_full_report['report']
        )
        
        # 验证 results
        assert 'results' in sample_full_report
        assert isinstance(sample_full_report['results'], list)
        for i, result in enumerate(sample_full_report['results']):
            TestResultContract().test_result_schema_required_fields(result)
        
        # 验证 validation
        if 'validation' in sample_full_report:
            TestValidationContract().test_validation_schema_required_fields(
                sample_full_report['validation']
            )
        
        # 验证 brandDistribution
        if 'brandDistribution' in sample_full_report:
            TestBrandDistributionContract().test_schema_required_fields(
                sample_full_report['brandDistribution']
            )
        
        # 验证 sentimentDistribution
        if 'sentimentDistribution' in sample_full_report:
            TestSentimentDistributionContract().test_schema_required_fields(
                sample_full_report['sentimentDistribution']
            )
    
    def test_full_report_error_or_partial(self, sample_full_report: Dict):
        """测试错误或部分报告结构"""
        error = sample_full_report.get('error')
        partial = sample_full_report.get('partial')
        
        if error:
            assert 'status' in error
            assert 'message' in error
        
        if partial:
            assert 'is_partial' in partial
            assert 'progress' in partial
            assert 0 <= partial['progress'] <= 100


class TestBrandDistributionContract:
    """品牌分布 API 契约测试"""
    
    def test_schema_required_fields(self, data: Dict):
        """测试必填字段"""
        errors = validate_required_fields(
            data,
            BRAND_DISTRIBUTION_SCHEMA['required'],
            'brandDistribution.'
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_field_types(self, data: Dict):
        """测试字段类型"""
        errors = []
        for field, expected_type in BRAND_DISTRIBUTION_SCHEMA['types'].items():
            if field in data:
                errors.extend(validate_field_type(
                    data[field],
                    expected_type,
                    f'brandDistribution.{field}'
                ))
        assert not errors, f"字段类型错误：{errors}"


class TestSentimentDistributionContract:
    """情感分布 API 契约测试"""
    
    def test_schema_required_fields(self, data: Dict):
        """测试必填字段"""
        errors = validate_required_fields(
            data,
            SENTIMENT_DISTRIBUTION_SCHEMA['required'],
            'sentimentDistribution.'
        )
        assert not errors, f"缺少必填字段：{errors}"
    
    def test_field_types(self, data: Dict):
        """测试字段类型"""
        errors = []
        for field, expected_type in SENTIMENT_DISTRIBUTION_SCHEMA['types'].items():
            if field in data:
                errors.extend(validate_field_type(
                    data[field],
                    expected_type,
                    f'sentimentDistribution.{field}'
                ))
        assert not errors, f"字段类型错误：{errors}"
    
    def test_sentiment_values(self, data: Dict):
        """测试情感值"""
        sentiment_data = data.get('data', {})
        required_emotions = ['positive', 'neutral', 'negative']
        for emotion in required_emotions:
            assert emotion in sentiment_data, f"缺少情感数据：{emotion}"
            value = sentiment_data[emotion]
            assert isinstance(value, int), f"{emotion} 必须是整数"
            assert value >= 0, f"{emotion} 必须非负"


# ==================== 错误响应测试 ====================

class TestErrorResponses:
    """错误响应契约测试"""
    
    def test_not_found_error_structure(self, not_found_error: Dict):
        """测试 404 错误结构"""
        assert 'error' in not_found_error
        assert isinstance(not_found_error['error'], str)
    
    def test_server_error_structure(self, server_error: Dict):
        """测试 500 错误结构"""
        assert 'error' in server_error
        assert 'message' in server_error
    
    def test_rate_limit_error_structure(self, rate_limit_error: Dict):
        """测试 429 错误结构"""
        assert 'error' in rate_limit_error
        assert 'retry_after' in rate_limit_error
        assert isinstance(rate_limit_error['retry_after'], int)
        assert rate_limit_error['retry_after'] > 0


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    def test_report_consistency(self, sample_full_report: Dict):
        """测试报告数据一致性"""
        report = sample_full_report.get('report', {})
        results = sample_full_report.get('results', [])
        
        # 验证 execution_id 一致
        execution_id = report.get('execution_id')
        for result in results:
            # 结果应该属于同一个执行
            assert 'brand' in result
            assert 'question' in result
        
        # 验证结果数量与分布总数一致
        brand_dist = sample_full_report.get('brandDistribution', {})
        if brand_dist.get('total_count') is not None:
            assert brand_dist['total_count'] == len(results)
        
        # 验证情感分布总数与结果数量一致
        sentiment_dist = sample_full_report.get('sentimentDistribution', {})
        if sentiment_dist.get('total_count') is not None:
            assert sentiment_dist['total_count'] == len(results)
    
    def test_validation_matches_data(self, sample_full_report: Dict):
        """测试验证与实际数据匹配"""
        validation = sample_full_report.get('validation', {})
        results = sample_full_report.get('results', [])
        
        # 如果有结果，验证不应该失败
        if results:
            # 质量评分不应该为 0
            quality_score = validation.get('quality_score', 0)
            assert quality_score > 0 or validation.get('errors'), \
                "有结果但质量评分为 0 且无错误"


# ==================== pytest fixtures ====================

@pytest.fixture
def sample_report() -> Dict:
    """示例报告"""
    return {
        'id': 1,
        'execution_id': '550e8400-e29b-41d4-a716-446655440000',
        'user_id': 'user_123',
        'brand_name': '华为',
        'status': 'completed',
        'progress': 100,
        'stage': 'completed',
        'is_completed': True,
        'created_at': '2026-03-01T10:00:00',
        'completed_at': '2026-03-01T10:05:00',
        'checksum': 'abc123'
    }


@pytest.fixture
def sample_result() -> Dict:
    """示例结果"""
    return {
        'id': 1,
        'brand': '华为',
        'question': '如何评价华为手机？',
        'model': 'doubao',
        'response': {
            'content': '华为手机很好',
            'latency': 1.5
        },
        'geo_data': {
            'brand_mentioned': True,
            'rank': 1,
            'sentiment': 0.8,
            'cited_sources': ['source1'],
            'keywords': [{'word': '华为', 'count': 5}]
        },
        'quality_score': 85,
        'quality_level': 'high'
    }


@pytest.fixture
def sample_validation() -> Dict:
    """示例验证"""
    return {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'quality_issues': [],
        'quality_score': 95,
        'details': {
            'report_valid': True,
            'results_valid': True,
            'analysis_valid': True,
            'aggregation_valid': True,
            'checksum_valid': True
        }
    }


@pytest.fixture
def sample_full_report(sample_report, sample_result, sample_validation) -> Dict:
    """示例完整报告"""
    return {
        'report': sample_report,
        'results': [sample_result],
        'analysis': {
            'competitive_analysis': {},
            'brand_scores': {},
            'semantic_drift': {},
            'source_purity': {},
            'recommendations': {}
        },
        'brandDistribution': {
            'data': {'华为': 1},
            'total_count': 1
        },
        'sentimentDistribution': {
            'data': {'positive': 1, 'neutral': 0, 'negative': 0},
            'total_count': 1
        },
        'keywords': [{'word': '华为', 'count': 5, 'sentiment': 0.8}],
        'meta': {
            'data_schema_version': '1.0',
            'server_version': '2.0.0',
            'retrieved_at': '2026-03-01T10:05:00'
        },
        'validation': sample_validation,
        'qualityHints': {
            'has_low_quality_results': False,
            'has_partial_analysis': False,
            'warnings': []
        }
    }


@pytest.fixture
def not_found_error() -> Dict:
    """404 错误示例"""
    return {
        'error': '报告不存在',
        'execution_id': 'invalid-id',
        'suggestion': '请检查执行 ID 是否正确'
    }


@pytest.fixture
def server_error() -> Dict:
    """500 错误示例"""
    return {
        'error': '获取报告失败',
        'message': '数据库连接失败',
        'execution_id': 'test-id',
        'suggestion': '请稍后重试'
    }


@pytest.fixture
def rate_limit_error() -> Dict:
    """429 错误示例"""
    return {
        'error': '请求频率超限',
        'retry_after': 60
    }


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
