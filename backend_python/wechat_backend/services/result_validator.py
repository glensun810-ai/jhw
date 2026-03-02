"""
结果验证器 - ResultValidator

核心职责：
1. 验证诊断结果的完整性
2. 验证 AI 响应内容的有效性
3. 验证数据字段的完整性
4. 提供详细的验证报告和错误信息

设计原则：
1. 早期失败 - 发现问题立即返回，避免无效数据继续流转
2. 详细日志 - 记录所有验证细节，便于问题排查
3. 可配置 - 支持配置验证规则的严格程度
4. 可扩展 - 易于添加新的验证规则

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from wechat_backend.logging_config import api_logger, db_logger


class ValidationLevel(Enum):
    """验证严格程度"""
    STRICT = "strict"       # 严格模式：任何空响应都视为失败
    NORMAL = "normal"       # 普通模式：允许部分空响应（<50%）
    LENIENT = "lenient"     # 宽松模式：只要有有效响应即可


class ValidationStatus(Enum):
    """验证结果状态"""
    PASSED = "passed"           # 验证通过
    WARNING = "warning"         # 验证通过但有警告
    FAILED = "failed"           # 验证失败
    CRITICAL = "critical"       # 严重失败（所有数据无效）


@dataclass
class ValidationResult:
    """
    验证结果数据类
    
    Attributes:
        status: 验证状态
        message: 验证结果描述
        expected_count: 预期结果数量
        actual_count: 实际结果数量
        invalid_results: 无效结果列表
        missing_fields: 缺失字段列表
        warnings: 警告列表
        details: 详细验证信息
        timestamp: 验证时间戳
    """
    status: ValidationStatus
    message: str
    expected_count: int = 0
    actual_count: int = 0
    invalid_results: List[Dict[str, Any]] = field(default_factory=list)
    missing_fields: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'status': self.status.value,
            'message': self.message,
            'expected_count': self.expected_count,
            'actual_count': self.actual_count,
            'invalid_count': len(self.invalid_results),
            'invalid_results': self.invalid_results,
            'missing_fields_count': len(self.missing_fields),
            'missing_fields': self.missing_fields,
            'warnings': self.warnings,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
    
    @property
    def is_passed(self) -> bool:
        """验证是否通过"""
        return self.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]


class ResultValidator:
    """
    结果验证器
    
    核心功能：
    1. 数量验证 - 验证保存结果数量与预期是否匹配
    2. 质量验证 - 验证 AI 响应内容是否有效
    3. 完整性验证 - 验证数据字段是否完整
    4. 一致性验证 - 验证数据格式和类型是否正确
    """
    
    # 必要字段定义
    REQUIRED_FIELDS = ['brand', 'question', 'model', 'response']
    
    # 响应内容最小长度
    MIN_RESPONSE_LENGTH = 10
    
    # 错误关键词（出现这些词表示 AI 响应失败）
    ERROR_KEYWORDS = [
        'error', 'failed', 'failure', 'exception', 
        'timeout', 'rate limit', 'api error',
        '错误', '失败', '超时', '异常'
    ]
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL):
        """
        初始化验证器
        
        参数：
            validation_level: 验证严格程度
        """
        self.validation_level = validation_level
        api_logger.debug(f"[ResultValidator] 初始化完成，验证级别={validation_level.value}")
    
    def validate(
        self,
        execution_id: str,
        expected_results: List[Dict[str, Any]],
        validate_quality: bool = True,
        validate_completeness: bool = True
    ) -> ValidationResult:
        """
        执行完整验证流程
        
        参数：
            execution_id: 执行 ID
            expected_results: 预期的结果列表（用于数量验证）
            validate_quality: 是否验证质量
            validate_completeness: 是否验证完整性
        
        返回：
            ValidationResult: 验证结果
        """
        api_logger.info(f"[ResultValidator] 开始验证：{execution_id}")
        
        # 从数据库读取已保存的结果
        from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
        
        result_repo = DiagnosisResultRepository()
        saved_results = result_repo.get_by_execution_id(execution_id)
        
        # 1. 数量验证
        quantity_result = self._validate_quantity(
            execution_id,
            expected_count=len(expected_results),
            actual_count=len(saved_results)
        )
        
        if quantity_result.status == ValidationStatus.CRITICAL:
            return quantity_result
        
        # 2. 质量验证
        quality_result = None
        if validate_quality:
            quality_result = self._validate_quality(execution_id, saved_results)
            if quality_result.status == ValidationStatus.CRITICAL:
                return quality_result
        
        # 3. 完整性验证
        completeness_result = None
        if validate_completeness:
            completeness_result = self._validate_completeness(execution_id, saved_results)
            if completeness_result.status == ValidationStatus.CRITICAL:
                return completeness_result
        
        # 综合评估
        return self._aggregate_results(
            execution_id=execution_id,
            quantity_result=quantity_result,
            quality_result=quality_result,
            completeness_result=completeness_result,
            saved_results=saved_results
        )
    
    def _validate_quantity(
        self,
        execution_id: str,
        expected_count: int,
        actual_count: int
    ) -> ValidationResult:
        """
        验证结果数量
        
        参数：
            execution_id: 执行 ID
            expected_count: 预期结果数量
            actual_count: 实际结果数量
        
        返回：
            ValidationResult
        """
        if actual_count == 0 and expected_count > 0:
            # 严重错误：数据库中没有任何结果
            error_msg = f"数据库中无结果：期望={expected_count}, 实际=0"
            api_logger.error(f"[ResultValidator] {error_msg}: {execution_id}")
            return ValidationResult(
                status=ValidationStatus.CRITICAL,
                message=error_msg,
                expected_count=expected_count,
                actual_count=actual_count,
                details={'error_type': 'no_results'}
            )
        
        if actual_count != expected_count:
            # 错误：数量不匹配
            error_msg = f"结果数量不匹配：期望={expected_count}, 实际={actual_count}"
            api_logger.error(f"[ResultValidator] {error_msg}: {execution_id}")
            return ValidationResult(
                status=ValidationStatus.FAILED,
                message=error_msg,
                expected_count=expected_count,
                actual_count=actual_count,
                details={'error_type': 'count_mismatch'}
            )
        
        api_logger.info(
            f"[ResultValidator] 数量验证通过：{execution_id}, "
            f"数量={expected_count}"
        )
        return ValidationResult(
            status=ValidationStatus.PASSED,
            message=f"数量验证通过：{expected_count}条结果",
            expected_count=expected_count,
            actual_count=actual_count,
            details={'error_type': None}
        )
    
    def _validate_quality(
        self,
        execution_id: str,
        results: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        验证结果质量（检查空响应、错误响应）
        
        参数：
            execution_id: 执行 ID
            results: 结果列表
        
        返回：
            ValidationResult
        """
        if not results:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="无结果可验证质量",
                details={'error_type': 'no_results_for_quality_check'}
            )
        
        invalid_results = []
        error_patterns = [
            (r'error', 'API 错误'),
            (r'failed|failure', '执行失败'),
            (r'timeout', '请求超时'),
            (r'rate limit', '频率限制'),
            (r'错误', '中文错误'),
            (r'失败', '中文失败'),
        ]
        
        for idx, res in enumerate(results):
            response = res.get('response', {})
            content = response.get('content', '') if isinstance(response, dict) else ''
            
            # 检查空响应
            if not content or not content.strip():
                invalid_results.append({
                    'index': idx,
                    'brand': res.get('brand', 'unknown'),
                    'question': res.get('question', 'unknown'),
                    'model': res.get('model', 'unknown'),
                    'reason': 'empty_response'
                })
                continue
            
            # 检查响应长度
            if len(content.strip()) < self.MIN_RESPONSE_LENGTH:
                invalid_results.append({
                    'index': idx,
                    'brand': res.get('brand', 'unknown'),
                    'question': res.get('question', 'unknown'),
                    'model': res.get('model', 'unknown'),
                    'reason': 'response_too_short',
                    'content_length': len(content.strip())
                })
                continue
            
            # 检查错误关键词
            content_lower = content.lower()
            for pattern, error_type in error_patterns:
                if re.search(pattern, content_lower):
                    # 如果包含错误关键词，但内容较长，可能是错误描述
                    # 这里只记录警告，不视为无效
                    api_logger.debug(
                        f"[ResultValidator] 检测到错误关键词：{error_type}, "
                        f"execution_id={execution_id}, brand={res.get('brand')}"
                    )
                    break
        
        # 根据验证级别判断结果
        total_count = len(results)
        invalid_count = len(invalid_results)
        valid_rate = (total_count - invalid_count) / total_count if total_count > 0 else 0
        
        if invalid_count == total_count:
            # 所有结果都无效 - 严重错误
            error_msg = "所有 AI 响应均为空或无效"
            api_logger.error(f"[ResultValidator] {error_msg}: {execution_id}")
            return ValidationResult(
                status=ValidationStatus.CRITICAL,
                message=error_msg,
                invalid_results=invalid_results,
                details={'error_type': 'all_invalid', 'valid_rate': valid_rate}
            )
        
        # 根据验证级别判断
        if self.validation_level == ValidationLevel.STRICT:
            if invalid_count > 0:
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message=f"严格模式下发现 {invalid_count} 个无效响应",
                    invalid_results=invalid_results,
                    details={'error_type': 'strict_mode_failed', 'valid_rate': valid_rate}
                )
        elif self.validation_level == ValidationLevel.NORMAL:
            if valid_rate < 0.5:
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message=f"有效响应率过低：{valid_rate:.1%} < 50%",
                    invalid_results=invalid_results,
                    details={'error_type': 'low_valid_rate', 'valid_rate': valid_rate}
                )
            elif invalid_count > 0:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"发现 {invalid_count} 个无效响应（{valid_rate:.1%} 有效）",
                    invalid_results=invalid_results,
                    warnings=[f"{invalid_count} 个响应质量不达标"],
                    details={'error_type': 'partial_invalid', 'valid_rate': valid_rate}
                )
        else:  # LENIENT
            if invalid_count > 0:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"宽松模式：发现 {invalid_count} 个无效响应",
                    invalid_results=invalid_results,
                    warnings=[f"{invalid_count} 个响应质量不达标"],
                    details={'error_type': 'lenient_mode_warning', 'valid_rate': valid_rate}
                )
        
        api_logger.info(
            f"[ResultValidator] 质量验证通过：{execution_id}, "
            f"有效数={total_count - invalid_count}/{total_count}"
        )
        return ValidationResult(
            status=ValidationStatus.PASSED,
            message=f"质量验证通过：{total_count - invalid_count}/{total_count} 有效",
            invalid_results=invalid_results,
            details={'error_type': None, 'valid_rate': valid_rate}
        )
    
    def _validate_completeness(
        self,
        execution_id: str,
        results: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        验证结果完整性（检查必要字段）
        
        参数：
            execution_id: 执行 ID
            results: 结果列表
        
        返回：
            ValidationResult
        """
        if not results:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="无结果可验证完整性",
                details={'error_type': 'no_results_for_completeness_check'}
            )
        
        missing_fields = []
        
        for idx, res in enumerate(results):
            for field in self.REQUIRED_FIELDS:
                if field not in res or res[field] is None:
                    missing_fields.append({
                        'index': idx,
                        'brand': res.get('brand', 'unknown'),
                        'question': res.get('question', 'unknown'),
                        'missing_field': field
                    })
        
        if missing_fields:
            # 统计缺失字段分布
            field_counts = {}
            for mf in missing_fields:
                field = mf['missing_field']
                field_counts[field] = field_counts.get(field, 0) + 1
            
            api_logger.warning(
                f"[ResultValidator] 发现缺失字段：{execution_id}, "
                f"缺失数={len(missing_fields)}, 分布={field_counts}"
            )
            
            # 如果缺失关键字段（response），视为严重错误
            if 'response' in field_counts:
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    message=f"关键字段缺失：response 缺失 {field_counts.get('response')} 次",
                    missing_fields=missing_fields,
                    details={'error_type': 'missing_response_field', 'field_counts': field_counts}
                )
            
            # 其他字段缺失，返回警告
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message=f"发现 {len(missing_fields)} 处非关键字段缺失",
                missing_fields=missing_fields,
                warnings=[f"缺失字段：{', '.join(set(f['missing_field'] for f in missing_fields))}"],
                details={'error_type': 'missing_fields', 'field_counts': field_counts}
            )
        
        api_logger.info(f"[ResultValidator] 完整性验证通过：{execution_id}")
        return ValidationResult(
            status=ValidationStatus.PASSED,
            message="完整性验证通过：所有必要字段存在",
            details={'error_type': None}
        )
    
    def _aggregate_results(
        self,
        execution_id: str,
        quantity_result: ValidationResult,
        quality_result: Optional[ValidationResult],
        completeness_result: Optional[ValidationResult],
        saved_results: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        聚合所有验证结果
        
        参数：
            execution_id: 执行 ID
            quantity_result: 数量验证结果
            quality_result: 质量验证结果（可选）
            completeness_result: 完整性验证结果（可选）
            saved_results: 已保存的结果列表
        
        返回：
            ValidationResult: 综合验证结果
        """
        # 检查是否有严重错误
        for result in [quantity_result, quality_result, completeness_result]:
            if result and result.status == ValidationStatus.CRITICAL:
                return result
        
        # 检查是否有失败
        for result in [quantity_result, quality_result, completeness_result]:
            if result and result.status == ValidationStatus.FAILED:
                return result
        
        # 收集所有警告
        all_warnings = []
        if quality_result and quality_result.warnings:
            all_warnings.extend(quality_result.warnings)
        if completeness_result and completeness_result.warnings:
            all_warnings.extend(completeness_result.warnings)
        
        # 综合评估
        if all_warnings:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message=f"验证通过但有警告：{len(all_warnings)} 个问题",
                expected_count=quantity_result.expected_count,
                actual_count=quantity_result.actual_count,
                invalid_results=quality_result.invalid_results if quality_result else [],
                missing_fields=completeness_result.missing_fields if completeness_result else [],
                warnings=all_warnings,
                details={
                    'quantity': quantity_result.to_dict(),
                    'quality': quality_result.to_dict() if quality_result else None,
                    'completeness': completeness_result.to_dict() if completeness_result else None
                }
            )
        
        # 全部通过
        return ValidationResult(
            status=ValidationStatus.PASSED,
            message="所有验证通过",
            expected_count=quantity_result.expected_count,
            actual_count=quantity_result.actual_count,
            invalid_results=quality_result.invalid_results if quality_result else [],
            missing_fields=completeness_result.missing_fields if completeness_result else [],
            details={
                'quantity': quantity_result.to_dict(),
                'quality': quality_result.to_dict() if quality_result else None,
                'completeness': completeness_result.to_dict() if completeness_result else None
            }
        )
    
    def validate_single_result(
        self,
        result: Dict[str, Any],
        check_content: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        验证单个结果的完整性
        
        参数：
            result: 单个结果字典
            check_content: 是否检查内容质量
        
        返回：
            (is_valid, errors): 是否有效，错误列表
        """
        errors = []
        
        # 检查必要字段
        for field in self.REQUIRED_FIELDS:
            if field not in result or result[field] is None:
                errors.append(f"缺失必要字段：{field}")
        
        # 检查内容质量
        if check_content and 'response' in result:
            response = result.get('response', {})
            content = response.get('content', '') if isinstance(response, dict) else ''
            
            if not content or not content.strip():
                errors.append("响应内容为空")
            elif len(content.strip()) < self.MIN_RESPONSE_LENGTH:
                errors.append(f"响应内容过短：{len(content.strip())} < {self.MIN_RESPONSE_LENGTH}")
        
        return (len(errors) == 0, errors)


def get_result_validator(
    validation_level: ValidationLevel = ValidationLevel.NORMAL
) -> ResultValidator:
    """
    获取结果验证器实例
    
    参数：
        validation_level: 验证严格程度
    
    返回：
        ResultValidator 实例
    """
    return ResultValidator(validation_level=validation_level)
