"""
ResultValidator 单元测试

测试范围：
1. 数量验证 - 验证保存结果数量与预期是否匹配
2. 质量验证 - 验证 AI 响应内容是否有效
3. 完整性验证 - 验证数据字段是否完整
4. 不同验证级别的行为 - STRICT/NORMAL/LENIENT

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wechat_backend.services.result_validator import (
    ResultValidator,
    ValidationLevel,
    ValidationStatus,
    ValidationResult,
    get_result_validator,
    RetryConfig,
    RetryMetrics,
    VisibilityDelayError
)


class TestValidationResult(unittest.TestCase):
    """测试 ValidationResult 数据类"""
    
    def test_to_dict(self):
        """测试转换为字典格式"""
        result = ValidationResult(
            status=ValidationStatus.PASSED,
            message="测试通过",
            expected_count=10,
            actual_count=10,
            invalid_results=[{'index': 0, 'reason': 'empty'}],
            missing_fields=[{'field': 'brand'}],
            warnings=["警告 1"],
            details={'key': 'value'}
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['status'], 'passed')
        self.assertEqual(result_dict['message'], "测试通过")
        self.assertEqual(result_dict['expected_count'], 10)
        self.assertEqual(result_dict['actual_count'], 10)
        self.assertEqual(result_dict['invalid_count'], 1)
        self.assertEqual(len(result_dict['warnings']), 1)
        self.assertIn('key', result_dict['details'])
    
    def test_is_passed(self):
        """测试 is_passed 属性"""
        # PASSED 状态
        result1 = ValidationResult(status=ValidationStatus.PASSED, message="通过")
        self.assertTrue(result1.is_passed)
        
        # WARNING 状态
        result2 = ValidationResult(status=ValidationStatus.WARNING, message="警告")
        self.assertTrue(result2.is_passed)
        
        # FAILED 状态
        result3 = ValidationResult(status=ValidationStatus.FAILED, message="失败")
        self.assertFalse(result3.is_passed)
        
        # CRITICAL 状态
        result4 = ValidationResult(status=ValidationStatus.CRITICAL, message="严重失败")
        self.assertFalse(result4.is_passed)


class TestResultValidatorQuantity(unittest.TestCase):
    """测试数量验证"""

    def setUp(self):
        """测试前准备"""
        # 使用较快的重试配置以加快测试
        config = RetryConfig(max_retries=0, base_delay=0.01, max_delay=0.02, jitter=0)
        self.validator = ResultValidator(validation_level=ValidationLevel.NORMAL, retry_config=config)
        self.execution_id = "test_exec_001"
    
    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quantity_success(self, mock_repo_class):
        """测试数量验证成功"""
        # Mock 数据库返回
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'brand1', 'question': 'q1', 'model': 'gpt-4', 'response': {'content': 'test'}},
            {'brand': 'brand1', 'question': 'q2', 'model': 'gpt-4', 'response': {'content': 'test'}}
        ]
        mock_repo_class.return_value = mock_repo

        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = self.validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=False,
            validate_completeness=False
        )

        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(result.expected_count, 2)
        self.assertEqual(result.actual_count, 2)
        self.assertEqual(len(saved_results), 2)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quantity_mismatch(self, mock_repo_class):
        """测试数量不匹配"""
        # Mock 数据库返回（少一条）
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'brand1', 'question': 'q1', 'model': 'gpt-4', 'response': {'content': 'test'}}
        ]
        mock_repo_class.return_value = mock_repo

        expected_results = [
            {'brand': 'brand1', 'question': 'q1'},
            {'brand': 'brand1', 'question': 'q2'}
        ]

        # 使用较短的延迟以加快测试
        config = RetryConfig(max_retries=0, base_delay=0.01, max_delay=0.02, jitter=0)
        validator = ResultValidator(validation_level=ValidationLevel.NORMAL, retry_config=config)

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=False,
            validate_completeness=False
        )

        # 由于重试机制，数量不匹配会先触发可见性检查失败（CRITICAL）
        self.assertIn(result.status, [ValidationStatus.FAILED, ValidationStatus.CRITICAL])
        self.assertEqual(result.expected_count, 2)
        self.assertEqual(result.actual_count, 0)  # 可见性检查失败时返回 0

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quantity_zero(self, mock_repo_class):
        """测试数据库无结果（严重错误）"""
        # Mock 数据库返回空
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = []
        mock_repo_class.return_value = mock_repo

        expected_results = [
            {'brand': 'brand1', 'question': 'q1'},
            {'brand': 'brand1', 'question': 'q2'}
        ]
        
        # 使用较短的延迟以加快测试
        config = RetryConfig(max_retries=0, base_delay=0.01, max_delay=0.02, jitter=0)
        validator = ResultValidator(validation_level=ValidationLevel.NORMAL, retry_config=config)

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=False,
            validate_completeness=False
        )

        # 重试机制会先触发可见性检查失败（CRITICAL）
        self.assertEqual(result.status, ValidationStatus.CRITICAL)
        self.assertEqual(result.actual_count, 0)
        self.assertIn("可见性", result.message)


class TestResultValidatorQuality(unittest.TestCase):
    """测试质量验证"""

    def setUp(self):
        """测试前准备"""
        self.execution_id = "test_exec_002"

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quality_all_valid(self, mock_repo_class):
        """测试所有响应都有效"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': '这是一个有效的 AI 响应，内容足够长'}
            },
            {
                'brand': 'brand1',
                'question': 'q2',
                'model': 'gpt-4',
                'response': {'content': '这是另一个有效的 AI 响应，内容也足够长'}
            }
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=False
        )

        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(len(result.invalid_results), 0)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quality_empty_response(self, mock_repo_class):
        """测试空响应"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': ''}  # 空响应
            },
            {
                'brand': 'brand1',
                'question': 'q2',
                'model': 'gpt-4',
                'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}
            }
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=False
        )

        # 50% 有效，应该通过但有警告
        self.assertEqual(result.status, ValidationStatus.WARNING)
        self.assertEqual(len(result.invalid_results), 1)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quality_all_empty(self, mock_repo_class):
        """测试所有响应都为空（严重错误）"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'brand1', 'question': 'q1', 'model': 'gpt-4', 'response': {'content': ''}},
            {'brand': 'brand1', 'question': 'q2', 'model': 'gpt-4', 'response': {'content': ''}}
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=False
        )

        self.assertEqual(result.status, ValidationStatus.CRITICAL)
        self.assertIn("所有 AI 响应均为空或无效", result.message)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quality_strict_mode(self, mock_repo_class):
        """测试严格模式"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'brand1', 'question': 'q1', 'model': 'gpt-4', 'response': {'content': ''}},
            {'brand': 'brand1', 'question': 'q2', 'model': 'gpt-4', 'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}}
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.STRICT)
        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=False
        )

        # 严格模式下，有任何无效响应都应该失败
        self.assertEqual(result.status, ValidationStatus.FAILED)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_quality_lenient_mode(self, mock_repo_class):
        """测试宽松模式"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {'brand': 'brand1', 'question': 'q1', 'model': 'gpt-4', 'response': {'content': ''}},
            {'brand': 'brand1', 'question': 'q2', 'model': 'gpt-4', 'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}}
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.LENIENT)
        expected_results = [{'brand': 'brand1', 'question': 'q1'}, {'brand': 'brand1', 'question': 'q2'}]

        result, saved_results = validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=False
        )

        # 宽松模式下，只要有有效响应就通过（可能有警告）
        self.assertIn(result.status, [ValidationStatus.PASSED, ValidationStatus.WARNING])


class TestResultValidatorCompleteness(unittest.TestCase):
    """测试完整性验证"""

    def setUp(self):
        """测试前准备"""
        self.validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        self.execution_id = "test_exec_003"

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_completeness_all_fields_present(self, mock_repo_class):
        """测试所有必要字段都存在"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}
            }
        ]
        mock_repo_class.return_value = mock_repo

        expected_results = [{'brand': 'brand1', 'question': 'q1'}]

        result, saved_results = self.validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=True
        )

        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(len(result.missing_fields), 0)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_completeness_missing_non_critical(self, mock_repo_class):
        """测试缺失非关键字段"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                # 缺少 model 字段
                'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}
            }
        ]
        mock_repo_class.return_value = mock_repo
        
        expected_results = [{'brand': 'brand1', 'question': 'q1'}]

        result, saved_results = self.validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=True
        )

        # 非关键字段缺失，应该是警告
        self.assertEqual(result.status, ValidationStatus.WARNING)
        self.assertGreater(len(result.missing_fields), 0)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_validate_completeness_missing_response(self, mock_repo_class):
        """测试缺失 response 字段（关键字段）"""
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4'
                # 缺少 response 字段
            }
        ]
        mock_repo_class.return_value = mock_repo

        expected_results = [{'brand': 'brand1', 'question': 'q1'}]

        result, saved_results = self.validator.validate(
            execution_id=self.execution_id,
            expected_results=expected_results,
            validate_quality=False,
            validate_completeness=True
        )

        # 关键字段缺失，应该失败
        self.assertEqual(result.status, ValidationStatus.FAILED)
        self.assertIn("response", result.message)


class TestResultValidatorSingle(unittest.TestCase):
    """测试单个结果验证"""
    
    def test_validate_single_result_valid(self):
        """测试单个有效结果"""
        validator = ResultValidator()
        result = {
            'brand': 'brand1',
            'question': 'q1',
            'model': 'gpt-4',
            'response': {'content': '这是一个有效的 AI 响应内容'}
        }
        
        is_valid, errors = validator.validate_single_result(result)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_single_result_missing_fields(self):
        """测试缺失字段"""
        validator = ResultValidator()
        result = {
            'brand': 'brand1',
            # 缺少 question, model, response
        }
        
        is_valid, errors = validator.validate_single_result(result)
        
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('question' in e for e in errors))
    
    def test_validate_single_result_empty_content(self):
        """测试空内容"""
        validator = ResultValidator()
        result = {
            'brand': 'brand1',
            'question': 'q1',
            'model': 'gpt-4',
            'response': {'content': ''}
        }
        
        is_valid, errors = validator.validate_single_result(result, check_content=True)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('空' in e for e in errors))
    
    def test_validate_single_result_short_content(self):
        """测试内容过短"""
        validator = ResultValidator()
        result = {
            'brand': 'brand1',
            'question': 'q1',
            'model': 'gpt-4',
            'response': {'content': '太短'}
        }
        
        is_valid, errors = validator.validate_single_result(result, check_content=True)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('过短' in e for e in errors))


class TestGetResultValidator(unittest.TestCase):
    """测试工厂函数"""
    
    def test_get_result_validator_default(self):
        """测试获取默认验证器"""
        validator = get_result_validator()
        self.assertIsInstance(validator, ResultValidator)
        self.assertEqual(validator.validation_level, ValidationLevel.NORMAL)
    
    def test_get_result_validator_custom_level(self):
        """测试获取指定级别的验证器"""
        validator = get_result_validator(validation_level=ValidationLevel.STRICT)
        self.assertIsInstance(validator, ResultValidator)
        self.assertEqual(validator.validation_level, ValidationLevel.STRICT)


class TestResultValidatorIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_full_validation_flow_success(self, mock_repo_class):
        """测试完整验证流程（成功）"""
        # Mock 数据库返回
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': '这是一个有效的 AI 响应，内容足够长且有意义'}
            },
            {
                'brand': 'brand2',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': '这是另一个有效的 AI 响应，内容也足够长'}
            },
            {
                'brand': 'brand1',
                'question': 'q2',
                'model': 'gpt-4',
                'response': {'content': '第三个有效响应，满足所有验证条件'}
            }
        ]
        mock_repo_class.return_value = mock_repo
        
        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        expected_results = [
            {'brand': 'brand1', 'question': 'q1'},
            {'brand': 'brand2', 'question': 'q1'},
            {'brand': 'brand1', 'question': 'q2'}
        ]

        result, saved_results = validator.validate(
            execution_id="test_integration_001",
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=True
        )

        # 所有验证应该通过
        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(result.expected_count, 3)
        self.assertEqual(result.actual_count, 3)
        self.assertEqual(len(result.invalid_results), 0)
        self.assertEqual(len(result.missing_fields), 0)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_full_validation_flow_partial_failure(self, mock_repo_class):
        """测试完整验证流程（部分失败）"""
        # Mock 数据库返回（部分无效）
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = [
            {
                'brand': 'brand1',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': ''}  # 空响应
            },
            {
                'brand': 'brand2',
                'question': 'q1',
                'model': 'gpt-4',
                'response': {'content': '这是一个有效的响应内容，长度足够通过验证'}
            }
        ]
        mock_repo_class.return_value = mock_repo

        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        expected_results = [
            {'brand': 'brand1', 'question': 'q1'},
            {'brand': 'brand2', 'question': 'q1'}
        ]

        result, saved_results = validator.validate(
            execution_id="test_integration_002",
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=True
        )

        # 50% 有效，应该通过但有警告
        self.assertEqual(result.status, ValidationStatus.WARNING)
        self.assertEqual(len(result.invalid_results), 1)
        self.assertGreater(len(result.warnings), 0)


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""

    def test_retry_config_default(self):
        """测试默认重试配置"""
        validator = ResultValidator()
        
        self.assertEqual(validator.retry_config.max_retries, 3)
        self.assertEqual(validator.retry_config.base_delay, 0.1)
        self.assertEqual(validator.retry_config.max_delay, 2.0)
        self.assertEqual(validator.retry_config.exponential_base, 2.0)
        self.assertEqual(validator.retry_config.jitter, 0.1)
        self.assertEqual(validator.retry_config.timeout, 10.0)

    def test_retry_config_custom(self):
        """测试自定义重试配置"""
        custom_config = RetryConfig(
            max_retries=5,
            base_delay=0.2,
            max_delay=5.0,
            exponential_base=3.0,
            jitter=0.2,
            timeout=20.0
        )
        validator = ResultValidator(retry_config=custom_config)
        
        self.assertEqual(validator.retry_config.max_retries, 5)
        self.assertEqual(validator.retry_config.base_delay, 0.2)
        self.assertEqual(validator.retry_config.max_delay, 5.0)
        self.assertEqual(validator.retry_config.exponential_base, 3.0)

    def test_calculate_delay_exponential(self):
        """测试指数退避延迟计算"""
        validator = ResultValidator()
        
        # 第 1 次重试（attempt=0）
        delay0 = validator._calculate_delay(0)
        self.assertAlmostEqual(delay0, 0.1, delta=0.02)  # 0.1 ± 10%
        
        # 第 2 次重试（attempt=1）
        delay1 = validator._calculate_delay(1)
        self.assertAlmostEqual(delay1, 0.2, delta=0.04)  # 0.2 ± 10%
        
        # 第 3 次重试（attempt=2）
        delay2 = validator._calculate_delay(2)
        self.assertAlmostEqual(delay2, 0.4, delta=0.08)  # 0.4 ± 10%

    def test_calculate_delay_max_limit(self):
        """测试最大延迟限制"""
        validator = ResultValidator()
        
        # 大 attempt 值应该被限制在 max_delay
        delay = validator._calculate_delay(10)
        self.assertLessEqual(delay, validator.retry_config.max_delay)

    def test_is_retryable_error_true(self):
        """测试可重试错误识别（应该重试的情况）"""
        validator = ResultValidator()
        
        retryable_errors = [
            VisibilityDelayError("数据可见性延迟"),
            Exception("database is locked"),
            Exception("timeout"),
            Exception("connection reset"),
            Exception("network error"),
        ]
        
        for error in retryable_errors:
            self.assertTrue(
                validator._is_retryable_error(error),
                f"错误 '{error}' 应该被识别为可重试"
            )

    def test_is_retryable_error_false(self):
        """测试不可重试错误识别（不应该重试的情况）"""
        validator = ResultValidator()
        
        non_retryable_errors = [
            ValueError("无效的值"),
            TypeError("类型错误"),
            KeyError("缺失键"),
        ]
        
        for error in non_retryable_errors:
            self.assertFalse(
                validator._is_retryable_error(error),
                f"错误 '{error}' 不应该被识别为可重试"
            )

    def test_retry_metrics_collection(self):
        """测试重试指标收集"""
        validator = ResultValidator()
        
        # 模拟成功操作（无需重试）
        def success_operation():
            return "success"
        
        result, metrics = validator._retry_with_exponential_backoff(
            operation=success_operation,
            operation_name="测试操作",
            execution_id="test_001"
        )
        
        self.assertEqual(result, "success")
        self.assertTrue(metrics.successful)
        self.assertEqual(metrics.total_attempts, 1)
        self.assertEqual(len(metrics.error_messages), 0)

    def test_retry_with_eventual_success(self):
        """测试最终成功的重试"""
        validator = ResultValidator()
        
        # 模拟前两次失败，第三次成功的操作
        attempt_count = [0]
        
        def flaky_operation():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise VisibilityDelayError(f"第 {attempt_count[0]} 次失败")
            return "success after retries"
        
        result, metrics = validator._retry_with_exponential_backoff(
            operation=flaky_operation,
            operation_name="不稳定操作",
            execution_id="test_002"
        )
        
        self.assertEqual(result, "success after retries")
        self.assertTrue(metrics.successful)
        self.assertEqual(metrics.total_attempts, 3)
        self.assertEqual(len(metrics.error_messages), 2)  # 前两次失败的错误消息
        self.assertGreater(metrics.total_time, 0)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_visibility_delay_retry_success(self, mock_repo_class):
        """测试数据可见性延迟重试成功"""
        # Mock 数据库（前两次返回空，第三次返回数据）
        mock_repo = MagicMock()
        call_count = [0]
        
        def mock_get_by_execution_id(exec_id):
            call_count[0] += 1
            if call_count[0] < 3:
                return []  # 前两次返回空
            # 返回有效的数据（响应内容长度足够）
            return [{
                'brand': 'b1',
                'question': 'q1',
                'model': 'm1',
                'response': {'content': '这是一个有效的 AI 响应内容，长度足够通过质量验证'}
            }]
        
        mock_repo.get_by_execution_id.side_effect = mock_get_by_execution_id
        mock_repo_class.return_value = mock_repo
        
        # 使用较短的延迟以加快测试
        config = RetryConfig(max_retries=5, base_delay=0.05, max_delay=0.2, jitter=0)
        validator = ResultValidator(retry_config=config)
        
        expected_results = [{'brand': 'b1', 'question': 'q1'}]
        result, saved_results = validator.validate(
            execution_id="test_retry_001",
            expected_results=expected_results
        )
        
        # 应该最终成功
        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(len(saved_results), 1)
        self.assertIsNotNone(result.retry_metrics)
        self.assertTrue(result.retry_metrics.successful)
        self.assertGreater(result.retry_metrics.total_attempts, 1)

    @patch('wechat_backend.diagnosis_report_repository.DiagnosisResultRepository')
    def test_visibility_delay_retry_failure(self, mock_repo_class):
        """测试数据可见性延迟重试失败"""
        # Mock 数据库（始终返回空）
        mock_repo = MagicMock()
        mock_repo.get_by_execution_id.return_value = []
        mock_repo_class.return_value = mock_repo
        
        # 使用较短的延迟以加快测试
        config = RetryConfig(max_retries=2, base_delay=0.05, max_delay=0.2, jitter=0)
        validator = ResultValidator(retry_config=config)
        
        expected_results = [{'brand': 'b1', 'question': 'q1'}]
        result, saved_results = validator.validate(
            execution_id="test_retry_002",
            expected_results=expected_results
        )
        
        # 应该失败
        self.assertEqual(result.status, ValidationStatus.CRITICAL)
        self.assertEqual(saved_results, [])
        # 重试指标应该被存储
        self.assertIsNotNone(result.retry_metrics)
        self.assertFalse(result.retry_metrics.successful)
        # 应该有 3 次尝试 (max_retries + 1)
        self.assertEqual(result.retry_metrics.total_attempts, 3)
        self.assertIn('retry_metrics', result.to_dict())

    def test_retry_metrics_in_validation_result_dict(self):
        """测试重试指标包含在 ValidationResult 的字典输出中"""
        validator = ResultValidator()
        
        # 手动创建带重试指标的验证结果
        metrics = RetryMetrics(
            total_attempts=3,
            successful=True,
            total_time=0.5,
            delays=[0.1, 0.2],
            error_messages=["error1", "error2"]
        )
        
        result = ValidationResult(
            status=ValidationStatus.PASSED,
            message="测试通过",
            retry_metrics=metrics
        )
        
        result_dict = result.to_dict()
        
        self.assertIn('retry_metrics', result_dict)
        self.assertEqual(result_dict['retry_metrics']['total_attempts'], 3)
        self.assertTrue(result_dict['retry_metrics']['successful'])


if __name__ == '__main__':
    unittest.main()
