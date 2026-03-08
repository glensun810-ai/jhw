#!/usr/bin/env python3
"""
诊断结果验证器模块

提供运行时字段验证和数据完整性检查，确保诊断结果质量。

核心功能：
1. 单结果验证
2. 批量结果验证
3. 验证装饰器
4. 验证报告生成

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from functools import wraps
from wechat_backend.logging_config import api_logger


class ResultValidator:
    """
    诊断结果验证器
    
    提供完整的字段验证和数据质量检查功能。
    
    用法：
        validator = ResultValidator()
        is_valid, errors = validator.validate(result)
    """
    
    # 必填字段列表
    REQUIRED_FIELDS = [
        'brand',      # 品牌名称（核心字段）
        'question',   # 问题内容
        'model',      # AI 模型名称
        'response',   # AI 响应内容
        'tokens_used' # Token 消耗量（核心字段）
    ]
    
    # 可选但推荐的字段
    RECOMMENDED_FIELDS = [
        'prompt_tokens',
        'completion_tokens',
        'cached_tokens',
        'geo_data',
        'error',
        'error_type',
        'is_objective'
    ]
    
    # 字段类型映射
    FIELD_TYPES = {
        'brand': str,
        'question': str,
        'model': str,
        'response': dict,
        'tokens_used': (int, float),
        'prompt_tokens': (int, float),
        'completion_tokens': (int, float),
        'cached_tokens': (int, float),
        'geo_data': (dict, type(None)),
        'error': (str, type(None)),
        'error_type': (str, type(None)),
        'is_objective': bool
    }
    
    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器
        
        参数：
            strict_mode: 是否启用严格模式（严格模式下缺少必填字段会失败）
        """
        self.strict_mode = strict_mode
        self._validation_stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def validate(
        self,
        result: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        验证单个诊断结果
        
        参数：
            result: 待验证的结果字典
            execution_id: 执行 ID（用于日志）
        
        返回：
            (is_valid, errors, warnings): 验证是否通过、错误列表、警告列表
        
        示例：
            >>> validator = ResultValidator()
            >>> is_valid, errors, warnings = validator.validate(result, execution_id='xxx')
            >>> if not is_valid:
            ...     print(f"验证失败：{errors}")
        """
        self._validation_stats['total_validations'] += 1
        
        errors = []
        warnings = []
        start_time = time.time()
        
        # 1. 检查必填字段
        for field in self.REQUIRED_FIELDS:
            if field not in result:
                errors.append(f"缺少必填字段：{field}")
            elif result[field] is None:
                errors.append(f"字段值为 None：{field}")
        
        # 2. 特别验证 brand 字段（核心字段）
        if 'brand' in result:
            brand = result['brand']
            if brand is not None:
                if not isinstance(brand, str):
                    errors.append(f"brand 字段类型错误：期望 str，实际 {type(brand).__name__}")
                elif len(brand.strip()) == 0:
                    errors.append(f"brand 字段为空字符串")
                elif len(brand) > 100:
                    warnings.append(f"brand 字段过长：{len(brand)} 字符")
        
        # 3. 特别验证 tokens_used 字段（核心字段）
        if 'tokens_used' in result:
            tokens = result['tokens_used']
            if tokens is not None:
                if not isinstance(tokens, (int, float)):
                    errors.append(f"tokens_used 字段类型错误：期望 int，实际 {type(tokens).__name__}")
                elif tokens < 0:
                    errors.append(f"tokens_used 字段为负数：{tokens}")
                elif tokens == 0:
                    warnings.append(f"tokens_used 为 0（可能未正确统计）")
        
        # 4. 验证 question 字段
        if 'question' in result and result['question'] is not None:
            question = result['question']
            if not isinstance(question, str):
                errors.append(f"question 字段类型错误：期望 str，实际 {type(question).__name__}")
            elif len(question.strip()) == 0:
                warnings.append(f"question 字段为空字符串")
        
        # 5. 验证 response 字段
        if 'response' in result and result['response'] is not None:
            response = result['response']
            if not isinstance(response, dict):
                errors.append(f"response 字段类型错误：期望 dict，实际 {type(response).__name__}")
            elif 'content' not in response:
                warnings.append("response 缺少 content 字段")
        
        # 6. 验证字段类型
        for field, expected_type in self.FIELD_TYPES.items():
            if field in result and result[field] is not None:
                if not isinstance(result[field], expected_type):
                    actual_type = type(result[field]).__name__
                    expected_type_name = expected_type if isinstance(expected_type, str) else expected_type.__name__
                    warnings.append(f"{field} 字段类型不匹配：期望 {expected_type_name}，实际 {actual_type}")
        
        # 7. 检查推荐字段（仅警告）
        if self.strict_mode:
            for field in self.RECOMMENDED_FIELDS:
                if field not in result and field not in self.REQUIRED_FIELDS:
                    warnings.append(f"缺少推荐字段：{field}")
        
        # 8. 记录验证日志
        elapsed = time.time() - start_time
        is_valid = len(errors) == 0
        
        self._log_validation(
            execution_id=execution_id,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            elapsed=elapsed
        )
        
        # 更新统计
        if is_valid:
            self._validation_stats['passed'] += 1
        else:
            self._validation_stats['failed'] += 1
        
        if warnings:
            self._validation_stats['warnings'] += 1
        
        return is_valid, errors, warnings
    
    def validate_batch(
        self,
        results: List[Dict[str, Any]],
        execution_id: Optional[str] = None,
        min_valid_ratio: float = 0.8
    ) -> Dict[str, Any]:
        """
        批量验证诊断结果
        
        参数：
            results: 结果列表
            execution_id: 执行 ID
            min_valid_ratio: 最小有效比例阈值
        
        返回：
            包含验证统计的字典
        
        示例：
            >>> validator = ResultValidator()
            >>> batch_result = validator.validate_batch(results, execution_id='xxx')
            >>> assert batch_result['valid_ratio'] >= 0.8
        """
        if not results:
            return {
                'total_count': 0,
                'valid_count': 0,
                'invalid_count': 0,
                'valid_ratio': 0.0,
                'is_acceptable': True,
                'errors': ['结果列表为空'],
                'details': []
            }
        
        valid_count = 0
        invalid_count = 0
        all_errors = []
        details = []
        
        for i, result in enumerate(results):
            is_valid, errors, warnings = self.validate(result, execution_id)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.extend([f"[{i}] {e}" for e in errors])
            
            details.append({
                'index': i,
                'is_valid': is_valid,
                'error_count': len(errors),
                'warning_count': len(warnings),
                'errors': errors
            })
        
        total_count = len(results)
        valid_ratio = valid_count / total_count if total_count > 0 else 0.0
        
        return {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'valid_ratio': valid_ratio,
            'is_acceptable': valid_ratio >= min_valid_ratio,
            'errors': all_errors,
            'details': details
        }
    
    def _log_validation(
        self,
        execution_id: Optional[str],
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        elapsed: float
    ):
        """记录验证日志"""
        log_extra = {
            'is_valid': is_valid,
            'error_count': len(errors),
            'warning_count': len(warnings),
            'elapsed_ms': f"{elapsed * 1000:.2f}"
        }
        
        if execution_id:
            log_extra['execution_id'] = execution_id
        
        if not is_valid:
            log_extra['errors'] = errors
            api_logger.error(f"[ResultValidator] 验证失败：{errors[0] if errors else '未知错误'}", extra=log_extra)
        elif warnings:
            log_extra['warnings'] = warnings
            api_logger.warning(f"[ResultValidator] 验证通过但有警告：{warnings[0]}", extra=log_extra)
        else:
            api_logger.debug(f"[ResultValidator] 验证通过 ({elapsed * 1000:.2f}ms)", extra=log_extra)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计"""
        stats = self._validation_stats.copy()
        total = stats['total_validations']
        stats['pass_rate'] = stats['passed'] / total if total > 0 else 0.0
        return stats


# 装饰器函数
def validate_result_fields(func):
    """
    装饰器：验证函数返回的结果字段完整性
    
    用法：
        @validate_result_fields
        def execute_nxm_test(...):
            return {'results': [...]}
    
    功能：
        1. 自动验证返回结果中的每个诊断记录
        2. 验证失败时记录详细错误日志
        3. 可选择是否抛出异常
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 提取 execution_id（用于日志）
        execution_id = kwargs.get('execution_id') or kwargs.get('task_id')
        
        validator = ResultValidator(strict_mode=True)
        
        # 验证单个结果
        if isinstance(result, dict) and 'data' in result:
            is_valid, errors, warnings = validator.validate(result['data'], execution_id)
            if not is_valid:
                api_logger.error(
                    f"[@validate_result_fields] 结果验证失败",
                    extra={
                        'function': func.__name__,
                        'execution_id': execution_id,
                        'errors': errors
                    }
                )
                # 在生产环境可以选择只记录日志而不抛出异常
                # raise ValueError(f"诊断结果验证失败：{errors}")
        
        # 验证结果列表
        elif isinstance(result, dict) and 'results' in result:
            batch_result = validator.validate_batch(result['results'], execution_id)
            if not batch_result['is_acceptable']:
                api_logger.error(
                    f"[@validate_result_fields] 批量验证失败",
                    extra={
                        'function': func.__name__,
                        'execution_id': execution_id,
                        'valid_ratio': batch_result['valid_ratio'],
                        'errors': batch_result['errors']
                    }
                )
                # raise ValueError(f"批量诊断结果验证失败：有效率过低")
            
            # 记录验证统计
            api_logger.info(
                f"[@validate_result_fields] 批量验证完成",
                extra={
                    'function': func.__name__,
                    'execution_id': execution_id,
                    'total': batch_result['total_count'],
                    'valid': batch_result['valid_count'],
                    'valid_ratio': f"{batch_result['valid_ratio']:.2%}"
                }
            )
        
        return result
    
    return wrapper


# 便捷验证函数
def quick_validate(result: Dict[str, Any]) -> bool:
    """
    快速验证（仅检查核心字段）
    
    用法：
        if quick_validate(result):
            # 结果有效
    """
    validator = ResultValidator(strict_mode=False)
    is_valid, _, _ = validator.validate(result)
    return is_valid


def assert_valid_result(result: Dict[str, Any], execution_id: Optional[str] = None):
    """
    断言结果有效（用于测试）
    
    用法：
        assert_valid_result(result, execution_id='xxx')
    
    抛出：
        AssertionError: 如果结果无效
    """
    validator = ResultValidator(strict_mode=True)
    is_valid, errors, _ = validator.validate(result, execution_id)
    if not is_valid:
        raise AssertionError(f"结果验证失败：{errors}")


# 单例实例
_default_validator = ResultValidator(strict_mode=True)


def get_validator(strict_mode: bool = True) -> ResultValidator:
    """获取验证器实例"""
    if strict_mode:
        return _default_validator
    return ResultValidator(strict_mode=strict_mode)


# 导出公共 API
__all__ = [
    'ResultValidator',
    'validate_result_fields',
    'quick_validate',
    'assert_valid_result',
    'get_validator'
]
