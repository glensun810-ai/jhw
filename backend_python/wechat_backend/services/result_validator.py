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
@version: 2.0.0  # 2026-03-05: 优化重试机制
"""

import re
import time
import random
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
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


class VisibilityDelayError(Exception):
    """
    数据可见性延迟异常
    
    当数据库 COMMIT 后数据短暂不可见时抛出此异常
    触发重试机制
    """
    pass


@dataclass
class RetryConfig:
    """
    重试配置数据类

    Attributes:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避底数
        jitter: 是否添加抖动 (0-1 之间的值，表示抖动幅度)
        timeout: 总超时时间（秒）
        retryable_errors: 可重试的错误类型列表
    """
    max_retries: int = 10  # 【P0 关键修复 - 2026-03-12 第 5 次】从 3 增加到 10，确保 WAL 可见性
    base_delay: float = 0.2  # 【P0 关键修复】从 100ms 增加到 200ms
    max_delay: float = 3.0   # 【P0 关键修复】从 2 秒增加到 3 秒
    exponential_base: float = 2.0
    jitter: float = 0.1      # 10% 抖动
    timeout: float = 30.0    # 【P0 关键修复】从 10 秒增加到 30 秒
    retryable_errors: List[str] = field(default_factory=lambda: [
        'database_locked',
        'timeout',
        'connection_error',
        'visibility_delay',
        '数据库锁定',
        '数据可见性',
    ])


@dataclass
class RetryMetrics:
    """
    重试指标数据类

    Attributes:
        total_attempts: 总尝试次数
        successful: 是否成功
        total_time: 总耗时（秒）
        delays: 每次重试的延迟列表
        error_messages: 错误消息列表
        final_error: 最终错误消息
    """
    total_attempts: int = 0
    successful: bool = False
    total_time: float = 0.0
    delays: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    final_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total_attempts': self.total_attempts,
            'successful': self.successful,
            'total_time': round(self.total_time, 3),
            'delays': [round(d, 3) for d in self.delays],
            'error_messages': self.error_messages,
            'final_error': self.final_error,
            'avg_delay': round(sum(self.delays) / len(self.delays), 3) if self.delays else 0,
        }


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
        retry_metrics: 重试指标（可选）
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
    retry_metrics: Optional[RetryMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
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
        
        # 添加重试指标（如果存在）
        if self.retry_metrics:
            result['retry_metrics'] = self.retry_metrics.to_dict()
        
        return result

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
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.NORMAL, retry_config: Optional[RetryConfig] = None):
        """
        初始化验证器

        参数：
            validation_level: 验证严格程度
            retry_config: 重试配置（可选，默认使用标准配置）
        """
        self.validation_level = validation_level
        self.retry_config = retry_config or RetryConfig()
        self._retry_metrics: Dict[str, RetryMetrics] = {}  # 存储每次验证的重试指标
        api_logger.debug(f"[ResultValidator] 初始化完成，验证级别={validation_level.value}, 重试配置=max_retries={self.retry_config.max_retries}")

    def _retry_with_exponential_backoff(
        self,
        operation: Callable[[], Any],
        operation_name: str,
        execution_id: str,
        is_retryable_error: Optional[Callable[[Exception], bool]] = None
    ) -> Tuple[Any, RetryMetrics]:
        """
        使用指数退避策略执行带重试的操作

        参数：
            operation: 要执行的操作
            operation_name: 操作名称（用于日志）
            execution_id: 执行 ID
            is_retryable_error: 判断错误是否可重试的函数

        返回：
            (result, metrics): 操作结果和重试指标
        """
        metrics = RetryMetrics()
        start_time = time.time()

        for attempt in range(self.retry_config.max_retries + 1):
            metrics.total_attempts = attempt + 1

            try:
                # 检查总超时
                elapsed = time.time() - start_time
                if elapsed > self.retry_config.timeout:
                    metrics.final_error = f"总超时：{elapsed:.2f}s > {self.retry_config.timeout}s"
                    api_logger.error(
                        f"[ResultValidator] ❌ {operation_name} 总超时：{execution_id}, "
                        f"{elapsed:.2f}s > {self.retry_config.timeout}s"
                    )
                    break

                # 执行操作
                result = operation()

                # 成功
                metrics.successful = True
                metrics.total_time = time.time() - start_time

                if attempt > 0:
                    api_logger.info(
                        f"[ResultValidator] ✅ {operation_name} 重试成功：{execution_id}, "
                        f"attempt={attempt + 1}/{self.retry_config.max_retries + 1}, "
                        f"time={metrics.total_time:.3f}s"
                    )

                return result, metrics

            except Exception as e:
                error_msg = str(e)
                metrics.error_messages.append(error_msg)

                # 判断是否可重试
                retryable = self._is_retryable_error(e, is_retryable_error)

                if attempt < self.retry_config.max_retries and retryable:
                    # 计算延迟时间（指数退避 + 抖动）
                    delay = self._calculate_delay(attempt)
                    metrics.delays.append(delay)

                    api_logger.warning(
                        f"[ResultValidator] ⚠️ {operation_name} 失败，{delay:.3f}s 后重试：{execution_id}, "
                        f"attempt={attempt + 1}/{self.retry_config.max_retries + 1}, "
                        f"error={error_msg}"
                    )

                    time.sleep(delay)
                else:
                    # 不重试
                    api_logger.error(
                        f"[ResultValidator] ❌ {operation_name} 失败：{execution_id}, "
                        f"已重试 {attempt + 1} 次，最终错误：{error_msg}"
                    )
                    metrics.final_error = error_msg
                    break

        # 所有重试失败
        metrics.total_time = time.time() - start_time
        return None, metrics

    def _calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间（指数退避 + 抖动）

        参数：
            attempt: 当前尝试次数（从 0 开始）

        返回：
            delay: 延迟时间（秒）
        """
        # 指数退避
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)

        # 限制最大延迟
        delay = min(delay, self.retry_config.max_delay)

        # 添加抖动（确保不超过最大延迟）
        if self.retry_config.jitter > 0:
            jitter_range = delay * self.retry_config.jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.01, min(delay, self.retry_config.max_delay))  # 确保在合理范围内

        return delay

    def _is_retryable_error(
        self,
        error: Exception,
        custom_checker: Optional[Callable[[Exception], bool]] = None
    ) -> bool:
        """
        判断错误是否可重试

        参数：
            error: 异常对象
            custom_checker: 自定义判断函数

        返回：
            是否可重试
        """
        # 使用自定义检查器
        if custom_checker:
            return custom_checker(error)

        # VisibilityDelayError 总是可重试
        if isinstance(error, VisibilityDelayError):
            return True

        # 默认检查逻辑
        error_str = str(error).lower()

        # 可重试的错误模式
        retryable_patterns = [
            'database is locked',
            'locked',
            'timeout',
            'timed out',
            'connection reset',
            'connection refused',
            'network',
            'busy',
            'temporary',
            'visibility',
            '数据可见性',
        ]

        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        return False

    def get_retry_metrics(self, execution_id: str) -> Optional[RetryMetrics]:
        """
        获取指定执行 ID 的重试指标

        参数：
            execution_id: 执行 ID

        返回：
            RetryMetrics 或 None
        """
        return self._retry_metrics.get(execution_id)

    def clear_retry_metrics(self):
        """清除所有重试指标"""
        self._retry_metrics.clear()
    
    def validate(
        self,
        execution_id: str,
        expected_results: List[Dict[str, Any]],
        validate_quality: bool = True,
        validate_completeness: bool = True
    ) -> Tuple[ValidationResult, List[Dict[str, Any]]]:
        """
        执行完整验证流程（优化重试机制版本）

        参数：
            execution_id: 执行 ID
            expected_results: 预期的结果列表（用于数量验证）
            validate_quality: 是否验证质量
            validate_completeness: 是否验证完整性

        返回：
            Tuple[ValidationResult, List[Dict[str, Any]]]: 验证结果 + 数据库中的实际结果列表
            【P0 关键修复 - 2026-03-03】返回数据库数据，确保后续环节使用统一数据源
        """
        api_logger.info(f"[ResultValidator] 开始验证：{execution_id}")

        # 从数据库读取已保存的结果
        from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository

        result_repo = DiagnosisResultRepository()

        # 【P0 关键修复 - 2026-03-05】使用优化的重试机制，处理连接池可见性延迟
        # SQLite WAL 模式下，COMMIT 后数据可能短暂不可见，需要重试读取
        expected_count = len(expected_results)
        
        def fetch_results():
            """获取结果的闭包函数"""
            saved_results = result_repo.get_by_execution_id(execution_id)
            actual_count = len(saved_results)
            
            if actual_count < expected_count:
                raise VisibilityDelayError(
                    f"数据可见性延迟：expected={expected_count}, actual={actual_count}"
                )
            
            return saved_results
        
        # 执行带重试的获取操作
        saved_results, retry_metrics = self._retry_with_exponential_backoff(
            operation=fetch_results,
            operation_name="数据可见性检查",
            execution_id=execution_id
        )
        
        # 存储重试指标
        self._retry_metrics[execution_id] = retry_metrics
        
        # 重试失败处理
        if saved_results is None:
            api_logger.error(
                f"[ResultValidator] ❌ 数据可见性检查失败：{execution_id}, "
                f"expected={expected_count}, actual=0, "
                f"已重试 {retry_metrics.total_attempts} 次，"
                f"总耗时={retry_metrics.total_time:.3f}s"
            )
            return ValidationResult(
                status=ValidationStatus.CRITICAL,
                message=f"数据可见性检查失败：{retry_metrics.final_error}",
                expected_count=expected_count,
                actual_count=0,
                retry_metrics=retry_metrics,
                details={
                    'error_type': 'visibility_check_failed',
                    'retry_metrics': retry_metrics.to_dict()
                }
            ), []
        
        # 记录成功结果
        actual_count = len(saved_results)
        if retry_metrics.successful and retry_metrics.total_attempts > 1:
            api_logger.info(
                f"[ResultValidator] ✅ 数据可见性检查通过：{execution_id}, "
                f"attempt={retry_metrics.total_attempts}/{self.retry_config.max_retries + 1}, "
                f"count={actual_count}, time={retry_metrics.total_time:.3f}s"
            )

        # 1. 数量验证
        quantity_result = self._validate_quantity(
            execution_id,
            expected_count=expected_count,
            actual_count=len(saved_results)
        )

        if quantity_result.status == ValidationStatus.CRITICAL:
            # 【P0 关键修复 - 2026-03-03】返回空列表
            return quantity_result, []

        # 2. 质量验证
        quality_result = None
        if validate_quality:
            quality_result = self._validate_quality(execution_id, saved_results)
            if quality_result.status == ValidationStatus.CRITICAL:
                # 【P0 关键修复 - 2026-03-03】返回空列表
                return quality_result, []

        # 3. 完整性验证
        completeness_result = None
        if validate_completeness:
            completeness_result = self._validate_completeness(execution_id, saved_results)
            if completeness_result.status == ValidationStatus.CRITICAL:
                # 【P0 关键修复 - 2026-03-03】返回空列表
                return completeness_result, []

        # 综合评估
        # 【P0 关键修复 - 2026-03-03】返回验证结果和数据库中的实际数据
        validation_result = self._aggregate_results(
            execution_id=execution_id,
            quantity_result=quantity_result,
            quality_result=quality_result,
            completeness_result=completeness_result,
            saved_results=saved_results,
            retry_metrics=retry_metrics
        )
        return validation_result, saved_results
    
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
        saved_results: List[Dict[str, Any]],
        retry_metrics: Optional[RetryMetrics] = None
    ) -> ValidationResult:
        """
        聚合所有验证结果

        参数：
            execution_id: 执行 ID
            quantity_result: 数量验证结果
            quality_result: 质量验证结果（可选）
            completeness_result: 完整性验证结果（可选）
            saved_results: 已保存的结果列表
            retry_metrics: 重试指标（可选）

        返回：
            ValidationResult: 综合验证结果
        """
        # 检查是否有严重错误
        for result in [quantity_result, quality_result, completeness_result]:
            if result and result.status == ValidationStatus.CRITICAL:
                # 添加重试指标
                if retry_metrics:
                    result.retry_metrics = retry_metrics
                return result

        # 检查是否有失败
        for result in [quantity_result, quality_result, completeness_result]:
            if result and result.status == ValidationStatus.FAILED:
                # 添加重试指标
                if retry_metrics:
                    result.retry_metrics = retry_metrics
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
                retry_metrics=retry_metrics,
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
            retry_metrics=retry_metrics,
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
