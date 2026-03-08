#!/usr/bin/env python3
"""
诊断结果类型定义模块

提供强类型定义和运行时验证，确保诊断结果字段完整性。

设计原则：
1. 使用 TypedDict 定义必填字段
2. 提供运行时验证函数
3. 在开发和测试环境启用严格验证

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

from typing import TypedDict, Optional, Dict, Any, List, Literal
from datetime import datetime


class GeoData(TypedDict, total=False):
    """GEO 数据结构（可选字段）"""
    rank: int
    sentiment: float
    url: str
    title: str
    snippet: str
    platform: str
    _error: Optional[str]


class ResponseContent(TypedDict, required=True):
    """AI 响应内容结构"""
    content: Optional[str]
    latency: Optional[float]
    metadata: Dict[str, Any]


class DiagnosisResult(TypedDict, required=True):
    """
    诊断结果的类型定义（强制字段完整性）
    
    所有诊断结果必须包含以下字段，确保数据流完整性。
    """
    # === 必填字段 ===
    brand: str                    # ✅ 品牌名称（核心字段）
    question: str                 # ✅ 问题内容
    model: str                    # ✅ 使用的 AI 模型
    response: ResponseContent     # ✅ AI 响应内容
    tokens_used: int              # ✅ Token 消耗量（核心字段）
    
    # === 可选字段 ===
    prompt_tokens: int            # 输入 token 数
    completion_tokens: int        # 输出 token 数
    cached_tokens: int            # 缓存 token 数
    geo_data: Optional[GeoData]   # GEO 数据
    error: Optional[str]          # 错误信息
    error_type: Optional[str]     # 错误类型
    is_objective: bool            # 是否客观回答
    latency: Optional[float]      # 延迟（秒）
    timestamp: str                # 时间戳


class DiagnosisResultPartial(TypedDict, total=False):
    """
    部分诊断结果（用于容错场景）
    
    允许字段缺失，但会在验证时标记为低质量数据。
    """
    brand: Optional[str]
    question: Optional[str]
    model: Optional[str]
    response: Optional[Dict[str, Any]]
    tokens_used: Optional[int]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    cached_tokens: Optional[int]
    geo_data: Optional[Dict[str, Any]]
    error: Optional[str]
    error_type: Optional[str]
    is_objective: Optional[bool]


class ValidationResult(TypedDict, required=True):
    """验证结果结构"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: int
    missing_fields: List[str]


# 字段验证配置
VALIDATION_CONFIG = {
    'required_fields': ['brand', 'question', 'model', 'response', 'tokens_used'],
    'optional_fields': ['prompt_tokens', 'completion_tokens', 'cached_tokens', 'geo_data', 'error', 'error_type'],
    'brand_min_length': 1,
    'question_min_length': 1,
    'tokens_min_value': 0,
    'enable_strict_validation': True,  # 开发/测试环境启用
}


def validate_diagnosis_result(result: Dict[str, Any], strict: bool = True) -> ValidationResult:
    """
    验证诊断结果字段完整性
    
    参数：
        result: 待验证的结果字典
        strict: 是否启用严格验证（严格模式下缺少必填字段会失败）
    
    返回：
        ValidationResult: 验证结果
    
    示例：
        >>> result = {'brand': '特斯拉', 'question': '...', 'model': 'qwen', 'response': {...}, 'tokens_used': 100}
        >>> validation = validate_diagnosis_result(result)
        >>> assert validation['is_valid'] == True
    """
    errors = []
    warnings = []
    missing_fields = []
    
    # 1. 检查必填字段
    for field in VALIDATION_CONFIG['required_fields']:
        if field not in result:
            missing_fields.append(field)
            errors.append(f"缺少必填字段：{field}")
        elif result[field] is None:
            missing_fields.append(field)
            errors.append(f"字段值为 None：{field}")
    
    # 2. 特别验证 brand 字段
    if 'brand' in result and result['brand']:
        brand = result['brand']
        if not isinstance(brand, str):
            errors.append(f"brand 字段类型错误：期望 str，实际 {type(brand).__name__}")
        elif len(brand) < VALIDATION_CONFIG['brand_min_length']:
            errors.append(f"brand 字段长度不足：'{brand}'")
    
    # 3. 特别验证 tokens_used 字段
    if 'tokens_used' in result:
        tokens = result['tokens_used']
        if not isinstance(tokens, (int, float)):
            errors.append(f"tokens_used 字段类型错误：期望 int，实际 {type(tokens).__name__}")
        elif tokens < VALIDATION_CONFIG['tokens_min_value']:
            warnings.append(f"tokens_used 值为负数：{tokens}")
    
    # 4. 验证 question 字段
    if 'question' in result and result['question']:
        question = result['question']
        if not isinstance(question, str):
            errors.append(f"question 字段类型错误：期望 str，实际 {type(question).__name__}")
        elif len(question) < VALIDATION_CONFIG['question_min_length']:
            warnings.append(f"question 字段过短")
    
    # 5. 验证 response 字段
    if 'response' in result:
        response = result['response']
        if not isinstance(response, dict):
            errors.append(f"response 字段类型错误：期望 dict，实际 {type(response).__name__}")
        elif 'content' not in response:
            warnings.append("response 缺少 content 字段")
    
    # 6. 检查可选字段的完整性（仅警告）
    for field in VALIDATION_CONFIG['optional_fields']:
        if field not in result and field not in missing_fields:
            warnings.append(f"缺少可选字段：{field}")
    
    # 7. 计算质量评分
    quality_score = _calculate_quality_score(result, missing_fields, errors, warnings)
    
    # 8. 严格模式下，缺少必填字段直接判定为无效
    is_valid = len(errors) == 0
    if strict and missing_fields:
        is_valid = False
    
    return {
        'is_valid': is_valid,
        'errors': errors,
        'warnings': warnings,
        'quality_score': quality_score,
        'missing_fields': missing_fields
    }


def _calculate_quality_score(
    result: Dict[str, Any],
    missing_fields: List[str],
    errors: List[str],
    warnings: List[str]
) -> int:
    """
    计算数据质量评分（0-100）
    
    评分规则：
    - 基础分 100 分
    - 缺少必填字段：每个扣 20 分
    - 有错误：每个扣 15 分
    - 有警告：每个扣 5 分
    - 有 geo_data：加 5 分
    - tokens_used > 0：加 5 分
    """
    score = 100
    
    # 扣分项
    score -= len(missing_fields) * 20
    score -= len(errors) * 15
    score -= len(warnings) * 5
    
    # 加分项
    if result.get('geo_data'):
        score += 5
    if result.get('tokens_used', 0) > 0:
        score += 5
    
    # 确保分数在 0-100 范围内
    return max(0, min(100, score))


def validate_diagnosis_results_batch(
    results: List[Dict[str, Any]],
    strict: bool = True,
    min_valid_ratio: float = 0.8
) -> Dict[str, Any]:
    """
    批量验证诊断结果
    
    参数：
        results: 结果列表
        strict: 是否严格验证
        min_valid_ratio: 最小有效比例阈值
    
    返回：
        包含验证统计的字典
    
    示例：
        >>> batch_result = validate_diagnosis_results_batch(results, strict=True)
        >>> assert batch_result['valid_count'] / batch_result['total_count'] >= 0.8
    """
    if not results:
        return {
            'total_count': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'valid_ratio': 0.0,
            'is_acceptable': True,
            'details': []
        }
    
    valid_count = 0
    invalid_count = 0
    details = []
    
    for i, result in enumerate(results):
        validation = validate_diagnosis_result(result, strict=strict)
        
        if validation['is_valid']:
            valid_count += 1
        else:
            invalid_count += 1
        
        details.append({
            'index': i,
            'is_valid': validation['is_valid'],
            'errors': validation['errors'],
            'quality_score': validation['quality_score']
        })
    
    total_count = len(results)
    valid_ratio = valid_count / total_count if total_count > 0 else 0.0
    
    return {
        'total_count': total_count,
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'valid_ratio': valid_ratio,
        'is_acceptable': valid_ratio >= min_valid_ratio,
        'details': details
    }


# 便捷函数：装饰器
def require_valid_result(func):
    """
    装饰器：验证函数返回的结果字段完整性
    
    用法：
        @require_valid_result
        def execute_task(...):
            return {'brand': '...', 'question': '...', ...}
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 验证单个结果
        if isinstance(result, dict) and 'data' in result:
            validation = validate_diagnosis_result(result['data'], strict=True)
            if not validation['is_valid']:
                from wechat_backend.logging_config import api_logger
                api_logger.error(
                    f"[字段验证] 结果验证失败：{validation['errors']}",
                    extra={'function': func.__name__, 'result': result}
                )
                raise ValueError(f"诊断结果验证失败：{validation['errors']}")
        
        # 验证结果列表
        elif isinstance(result, dict) and 'results' in result:
            batch_validation = validate_diagnosis_results_batch(result['results'], strict=True)
            if not batch_validation['is_acceptable']:
                from wechat_backend.logging_config import api_logger
                api_logger.error(
                    f"[字段验证] 批量验证失败：有效率={batch_validation['valid_ratio']:.2%}",
                    extra={'function': func.__name__, 'validation': batch_validation}
                )
                raise ValueError(f"批量诊断结果验证失败：有效率过低")
        
        return result
    
    return wrapper


# 导出公共 API
__all__ = [
    'DiagnosisResult',
    'DiagnosisResultPartial',
    'GeoData',
    'ResponseContent',
    'ValidationResult',
    'validate_diagnosis_result',
    'validate_diagnosis_results_batch',
    'require_valid_result',
    'VALIDATION_CONFIG'
]
