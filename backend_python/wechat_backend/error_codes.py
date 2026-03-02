"""
统一错误码定义模块

所有错误码必须在此文件中定义，禁止在业务代码中硬编码错误码。

错误码命名规范：
- 格式：{MODULE}_{ERROR_TYPE}_{SPECIFIC_ERROR}
- 示例：DIAGNOSIS_AI_PLATFORM_TIMEOUT

错误码分类：
- 1xxx: 通用错误
- 2xxx: 诊断相关错误
- 3xxx: AI 平台相关错误
- 4xxx: 数据库相关错误
- 5xxx: 统计分析相关错误
- 6xxx: 安全相关错误

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = 'info'               # 信息提示，不影响功能
    WARNING = 'warning'         # 警告，可能影响部分功能
    ERROR = 'error'             # 错误，影响当前操作
    CRITICAL = 'critical'       # 严重错误，系统级故障


@dataclass
class ErrorCodeDefinition:
    """错误码定义"""
    code: str                   # 错误码
    message: str                # 默认消息
    severity: ErrorSeverity     # 严重程度
    http_status: int            # HTTP 状态码
    category: str               # 错误分类
    retryable: bool = False     # 是否可重试
    user_message: Optional[str] = None  # 用户友好消息
    action_suggestion: Optional[str] = None  # 操作建议
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'code': self.code,
            'message': self.message,
            'severity': self.severity.value,
            'http_status': self.http_status,
            'category': self.category,
            'retryable': self.retryable,
            'user_message': self.user_message,
            'action_suggestion': self.action_suggestion,
        }


# ==================== 通用错误 (1xxx) ====================

class CommonErrorCode(Enum):
    """通用错误码"""
    UNKNOWN_ERROR = ErrorCodeDefinition(
        code='UNKNOWN_ERROR',
        message='系统未知错误',
        severity=ErrorSeverity.CRITICAL,
        http_status=500,
        category='COMMON',
        retryable=False,
        user_message='系统繁忙，请稍后重试',
        action_suggestion='refresh'
    )
    
    VALIDATION_ERROR = ErrorCodeDefinition(
        code='VALIDATION_ERROR',
        message='输入验证失败',
        severity=ErrorSeverity.WARNING,
        http_status=400,
        category='COMMON',
        retryable=False,
        user_message='输入信息有误，请检查后重试',
        action_suggestion='fix_input'
    )
    
    TIMEOUT_ERROR = ErrorCodeDefinition(
        code='TIMEOUT_ERROR',
        message='操作超时',
        severity=ErrorSeverity.ERROR,
        http_status=408,
        category='COMMON',
        retryable=True,
        user_message='操作超时，请稍后重试',
        action_suggestion='retry'
    )
    
    NOT_FOUND_ERROR = ErrorCodeDefinition(
        code='NOT_FOUND_ERROR',
        message='资源未找到',
        severity=ErrorSeverity.WARNING,
        http_status=404,
        category='COMMON',
        retryable=False,
        user_message='请求的资源不存在',
        action_suggestion='navigate_home'
    )
    
    UNAUTHORIZED_ERROR = ErrorCodeDefinition(
        code='UNAUTHORIZED_ERROR',
        message='未授权访问',
        severity=ErrorSeverity.WARNING,
        http_status=401,
        category='COMMON',
        retryable=False,
        user_message='请先登录',
        action_suggestion='login'
    )
    
    FORBIDDEN_ERROR = ErrorCodeDefinition(
        code='FORBIDDEN_ERROR',
        message='权限不足',
        severity=ErrorSeverity.WARNING,
        http_status=403,
        category='COMMON',
        retryable=False,
        user_message='您没有执行此操作的权限',
        action_suggestion='contact_admin'
    )
    
    RATE_LIMIT_ERROR = ErrorCodeDefinition(
        code='RATE_LIMIT_ERROR',
        message='请求过于频繁',
        severity=ErrorSeverity.WARNING,
        http_status=429,
        category='COMMON',
        retryable=True,
        user_message='请求过于频繁，请稍后再试',
        action_suggestion='wait_retry'
    )


# ==================== 诊断相关错误 (2xxx) ====================

class DiagnosisErrorCode(Enum):
    """诊断系统错误码"""
    
    # 诊断执行错误 (2001-2099)
    DIAGNOSIS_INIT_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_INIT_FAILED',
        message='诊断初始化失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断初始化失败，请稍后重试',
        action_suggestion='retry'
    )
    
    DIAGNOSIS_EXECUTION_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_EXECUTION_FAILED',
        message='诊断执行失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断执行失败，已保存当前进度',
        action_suggestion='view_history'
    )
    
    DIAGNOSIS_TIMEOUT = ErrorCodeDefinition(
        code='DIAGNOSIS_TIMEOUT',
        message='诊断任务执行超时',
        severity=ErrorSeverity.ERROR,
        http_status=408,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断任务执行时间过长，已保存当前进度',
        action_suggestion='view_history'
    )
    
    DIAGNOSIS_STATE_ERROR = ErrorCodeDefinition(
        code='DIAGNOSIS_STATE_ERROR',
        message='诊断状态异常',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='DIAGNOSIS',
        retryable=False,
        user_message='诊断状态异常，请刷新页面后重试',
        action_suggestion='refresh'
    )
    
    DIAGNOSIS_INCOMPLETE = ErrorCodeDefinition(
        code='DIAGNOSIS_INCOMPLETE',
        message='诊断结果不完整',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断结果不完整，已保存当前进度',
        action_suggestion='view_history'
    )
    
    # 结果验证错误 (2100-2199)
    DIAGNOSIS_RESULT_COUNT_MISMATCH = ErrorCodeDefinition(
        code='DIAGNOSIS_RESULT_COUNT_MISMATCH',
        message='诊断结果数量不匹配',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断结果数量异常，正在重新验证',
        action_suggestion='wait'
    )
    
    DIAGNOSIS_RESULT_INVALID = ErrorCodeDefinition(
        code='DIAGNOSIS_RESULT_INVALID',
        message='诊断结果无效',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='部分诊断结果无效，正在重新获取',
        action_suggestion='wait'
    )
    
    DIAGNOSIS_RESULT_EMPTY = ErrorCodeDefinition(
        code='DIAGNOSIS_RESULT_EMPTY',
        message='诊断结果为空',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='未获取到有效诊断结果',
        action_suggestion='retry'
    )
    
    # 数据持久化错误 (2200-2299)
    DIAGNOSIS_SAVE_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_SAVE_FAILED',
        message='诊断结果保存失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='诊断结果保存失败，正在重试',
        action_suggestion='wait'
    )
    
    DIAGNOSIS_ROLLBACK_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_ROLLBACK_FAILED',
        message='诊断回滚失败',
        severity=ErrorSeverity.CRITICAL,
        http_status=500,
        category='DIAGNOSIS',
        retryable=False,
        user_message='诊断回滚失败，请联系管理员',
        action_suggestion='contact_admin'
    )
    
    # 后台分析错误 (2300-2399)
    DIAGNOSIS_ANALYSIS_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_ANALYSIS_FAILED',
        message='后台分析失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='后台分析失败，已保存基础诊断结果',
        action_suggestion='view_report'
    )
    
    DIAGNOSIS_ANALYSIS_TIMEOUT = ErrorCodeDefinition(
        code='DIAGNOSIS_ANALYSIS_TIMEOUT',
        message='后台分析超时',
        severity=ErrorSeverity.WARNING,
        http_status=408,
        category='DIAGNOSIS',
        retryable=False,
        user_message='后台分析超时，已生成基础报告',
        action_suggestion='view_report'
    )
    
    # 报告聚合错误 (2400-2499)
    DIAGNOSIS_REPORT_AGGREGATION_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_REPORT_AGGREGATION_FAILED',
        message='报告聚合失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='报告生成失败，正在重试',
        action_suggestion='wait'
    )
    
    DIAGNOSIS_REPORT_SAVE_FAILED = ErrorCodeDefinition(
        code='DIAGNOSIS_REPORT_SAVE_FAILED',
        message='最终报告保存失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DIAGNOSIS',
        retryable=True,
        user_message='报告保存失败，正在重试',
        action_suggestion='wait'
    )


# ==================== AI 平台相关错误 (3xxx) ====================

class AIPlatformErrorCode(Enum):
    """AI 平台相关错误码"""
    
    # 配置错误 (3001-3099)
    AI_CONFIG_MISSING = ErrorCodeDefinition(
        code='AI_CONFIG_MISSING',
        message='AI 配置缺失',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='AI_PLATFORM',
        retryable=False,
        user_message='AI 配置不完整，请检查设置',
        action_suggestion='check_config'
    )
    
    AI_API_KEY_MISSING = ErrorCodeDefinition(
        code='AI_API_KEY_MISSING',
        message='API Key 缺失',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='AI_PLATFORM',
        retryable=False,
        user_message='缺少 API Key，请检查配置',
        action_suggestion='check_config'
    )
    
    # 调用错误 (3100-3199)
    AI_PLATFORM_UNAVAILABLE = ErrorCodeDefinition(
        code='AI_PLATFORM_UNAVAILABLE',
        message='AI 平台不可用',
        severity=ErrorSeverity.ERROR,
        http_status=503,
        category='AI_PLATFORM',
        retryable=True,
        user_message='AI 平台暂时不可用，请稍后重试',
        action_suggestion='retry'
    )
    
    AI_PLATFORM_TIMEOUT = ErrorCodeDefinition(
        code='AI_PLATFORM_TIMEOUT',
        message='AI 平台调用超时',
        severity=ErrorSeverity.ERROR,
        http_status=408,
        category='AI_PLATFORM',
        retryable=True,
        user_message='AI 平台响应超时，正在重试',
        action_suggestion='wait'
    )
    
    AI_PLATFORM_RATE_LIMIT = ErrorCodeDefinition(
        code='AI_PLATFORM_RATE_LIMIT',
        message='AI 平台请求频率限制',
        severity=ErrorSeverity.WARNING,
        http_status=429,
        category='AI_PLATFORM',
        retryable=True,
        user_message='请求过于频繁，请稍后再试',
        action_suggestion='wait_retry'
    )
    
    AI_PLATFORM_QUOTA_EXHAUSTED = ErrorCodeDefinition(
        code='AI_PLATFORM_QUOTA_EXHAUSTED',
        message='AI 配额已用尽',
        severity=ErrorSeverity.WARNING,
        http_status=429,
        category='AI_PLATFORM',
        retryable=False,
        user_message='当前 AI 平台的可用配额已用尽',
        action_suggestion='switch_platform'
    )
    
    # 响应错误 (3200-3299)
    AI_RESPONSE_INVALID = ErrorCodeDefinition(
        code='AI_RESPONSE_INVALID',
        message='AI 响应格式无效',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='AI_PLATFORM',
        retryable=True,
        user_message='AI 响应格式异常，正在重试',
        action_suggestion='wait'
    )
    
    AI_RESPONSE_EMPTY = ErrorCodeDefinition(
        code='AI_RESPONSE_EMPTY',
        message='AI 响应为空',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='AI_PLATFORM',
        retryable=True,
        user_message='未获取到有效 AI 响应',
        action_suggestion='retry'
    )
    
    AI_RESPONSE_PARSE_FAILED = ErrorCodeDefinition(
        code='AI_RESPONSE_PARSE_FAILED',
        message='AI 响应解析失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='AI_PLATFORM',
        retryable=True,
        user_message='AI 响应解析失败，正在重试',
        action_suggestion='wait'
    )
    
    # 模型错误 (3300-3399)
    AI_MODEL_NOT_FOUND = ErrorCodeDefinition(
        code='AI_MODEL_NOT_FOUND',
        message='AI 模型不存在',
        severity=ErrorSeverity.ERROR,
        http_status=404,
        category='AI_PLATFORM',
        retryable=False,
        user_message='所选 AI 模型不存在',
        action_suggestion='switch_model'
    )
    
    AI_MODEL_UNAVAILABLE = ErrorCodeDefinition(
        code='AI_MODEL_UNAVAILABLE',
        message='AI 模型不可用',
        severity=ErrorSeverity.ERROR,
        http_status=503,
        category='AI_PLATFORM',
        retryable=True,
        user_message='所选 AI 模型暂时不可用',
        action_suggestion='switch_model'
    )


# ==================== 数据库相关错误 (4xxx) ====================

class DatabaseErrorCode(Enum):
    """数据库相关错误码"""
    
    # 连接错误 (4001-4099)
    DB_CONNECTION_FAILED = ErrorCodeDefinition(
        code='DB_CONNECTION_FAILED',
        message='数据库连接失败',
        severity=ErrorSeverity.CRITICAL,
        http_status=503,
        category='DATABASE',
        retryable=True,
        user_message='数据库连接失败，请稍后重试',
        action_suggestion='retry'
    )
    
    DB_CONNECTION_TIMEOUT = ErrorCodeDefinition(
        code='DB_CONNECTION_TIMEOUT',
        message='数据库连接超时',
        severity=ErrorSeverity.ERROR,
        http_status=408,
        category='DATABASE',
        retryable=True,
        user_message='数据库连接超时，正在重试',
        action_suggestion='wait'
    )
    
    # 操作错误 (4100-4199)
    DB_QUERY_FAILED = ErrorCodeDefinition(
        code='DB_QUERY_FAILED',
        message='数据库查询失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DATABASE',
        retryable=True,
        user_message='数据库查询失败，正在重试',
        action_suggestion='wait'
    )
    
    DB_INSERT_FAILED = ErrorCodeDefinition(
        code='DB_INSERT_FAILED',
        message='数据库插入失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DATABASE',
        retryable=True,
        user_message='数据保存失败，正在重试',
        action_suggestion='wait'
    )
    
    DB_UPDATE_FAILED = ErrorCodeDefinition(
        code='DB_UPDATE_FAILED',
        message='数据库更新失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DATABASE',
        retryable=True,
        user_message='数据更新失败，正在重试',
        action_suggestion='wait'
    )
    
    DB_DELETE_FAILED = ErrorCodeDefinition(
        code='DB_DELETE_FAILED',
        message='数据库删除失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DATABASE',
        retryable=True,
        user_message='数据删除失败，正在重试',
        action_suggestion='wait'
    )
    
    # 事务错误 (4200-4299)
    DB_TRANSACTION_FAILED = ErrorCodeDefinition(
        code='DB_TRANSACTION_FAILED',
        message='数据库事务失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='DATABASE',
        retryable=True,
        user_message='数据库事务失败，正在回滚',
        action_suggestion='wait'
    )
    
    DB_ROLLBACK_FAILED = ErrorCodeDefinition(
        code='DB_ROLLBACK_FAILED',
        message='数据库回滚失败',
        severity=ErrorSeverity.CRITICAL,
        http_status=500,
        category='DATABASE',
        retryable=False,
        user_message='数据库回滚失败，请联系管理员',
        action_suggestion='contact_admin'
    )
    
    # 数据完整性错误 (4300-4399)
    DB_DATA_INTEGRITY_ERROR = ErrorCodeDefinition(
        code='DB_DATA_INTEGRITY_ERROR',
        message='数据完整性错误',
        severity=ErrorSeverity.CRITICAL,
        http_status=500,
        category='DATABASE',
        retryable=False,
        user_message='数据完整性错误，请联系管理员',
        action_suggestion='contact_admin'
    )
    
    DB_CONSTRAINT_VIOLATION = ErrorCodeDefinition(
        code='DB_CONSTRAINT_VIOLATION',
        message='数据库约束冲突',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='DATABASE',
        retryable=False,
        user_message='数据约束冲突，请检查输入',
        action_suggestion='fix_input'
    )


# ==================== 统计分析相关错误 (5xxx) ====================

class AnalyticsErrorCode(Enum):
    """统计分析相关错误码"""
    
    # 数据错误 (5001-5099)
    ANALYTICS_DATA_INVALID = ErrorCodeDefinition(
        code='ANALYTICS_DATA_INVALID',
        message='分析数据无效',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='ANALYTICS',
        retryable=False,
        user_message='分析数据格式错误',
        action_suggestion='fix_input'
    )
    
    ANALYTICS_DATA_INCOMPLETE = ErrorCodeDefinition(
        code='ANALYTICS_DATA_INCOMPLETE',
        message='分析数据不完整',
        severity=ErrorSeverity.WARNING,
        http_status=400,
        category='ANALYTICS',
        retryable=False,
        user_message='分析数据不完整，结果可能不准确',
        action_suggestion='continue_with_warning'
    )
    
    # 配置错误 (5100-5199)
    ANALYTICS_CONFIG_INVALID = ErrorCodeDefinition(
        code='ANALYTICS_CONFIG_INVALID',
        message='分析配置无效',
        severity=ErrorSeverity.ERROR,
        http_status=400,
        category='ANALYTICS',
        retryable=False,
        user_message='分析配置参数错误',
        action_suggestion='fix_config'
    )
    
    # 处理错误 (5200-5299)
    ANALYTICS_PROCESSING_FAILED = ErrorCodeDefinition(
        code='ANALYTICS_PROCESSING_FAILED',
        message='分析处理失败',
        severity=ErrorSeverity.ERROR,
        http_status=500,
        category='ANALYTICS',
        retryable=True,
        user_message='分析处理失败，正在重试',
        action_suggestion='wait'
    )
    
    ANALYTICS_TIMEOUT = ErrorCodeDefinition(
        code='ANALYTICS_TIMEOUT',
        message='分析处理超时',
        severity=ErrorSeverity.WARNING,
        http_status=408,
        category='ANALYTICS',
        retryable=False,
        user_message='分析处理超时，已生成基础报告',
        action_suggestion='view_report'
    )


# ==================== 安全相关错误 (6xxx) ====================

class SecurityErrorCode(Enum):
    """安全相关错误码"""
    
    # 认证错误 (6001-6099)
    SECURITY_AUTHENTICATION_FAILED = ErrorCodeDefinition(
        code='SECURITY_AUTHENTICATION_FAILED',
        message='认证失败',
        severity=ErrorSeverity.WARNING,
        http_status=401,
        category='SECURITY',
        retryable=False,
        user_message='认证失败，请重新登录',
        action_suggestion='login'
    )
    
    SECURITY_TOKEN_EXPIRED = ErrorCodeDefinition(
        code='SECURITY_TOKEN_EXPIRED',
        message='Token 已过期',
        severity=ErrorSeverity.WARNING,
        http_status=401,
        category='SECURITY',
        retryable=False,
        user_message='登录已过期，请重新登录',
        action_suggestion='login'
    )
    
    SECURITY_TOKEN_INVALID = ErrorCodeDefinition(
        code='SECURITY_TOKEN_INVALID',
        message='Token 无效',
        severity=ErrorSeverity.WARNING,
        http_status=401,
        category='SECURITY',
        retryable=False,
        user_message='认证令牌无效',
        action_suggestion='login'
    )
    
    # 授权错误 (6100-6199)
    SECURITY_AUTHORIZATION_FAILED = ErrorCodeDefinition(
        code='SECURITY_AUTHORIZATION_FAILED',
        message='授权失败',
        severity=ErrorSeverity.WARNING,
        http_status=403,
        category='SECURITY',
        retryable=False,
        user_message='您没有执行此操作的权限',
        action_suggestion='contact_admin'
    )
    
    # 输入安全错误 (6200-6299)
    SECURITY_INPUT_VALIDATION_FAILED = ErrorCodeDefinition(
        code='SECURITY_INPUT_VALIDATION_FAILED',
        message='输入验证失败',
        severity=ErrorSeverity.WARNING,
        http_status=400,
        category='SECURITY',
        retryable=False,
        user_message='输入包含不安全内容',
        action_suggestion='fix_input'
    )
    
    SECURITY_XSS_DETECTED = ErrorCodeDefinition(
        code='SECURITY_XSS_DETECTED',
        message='检测到 XSS 攻击',
        severity=ErrorSeverity.CRITICAL,
        http_status=400,
        category='SECURITY',
        retryable=False,
        user_message='输入包含不安全内容',
        action_suggestion='fix_input'
    )
    
    SECURITY_SQL_INJECTION_DETECTED = ErrorCodeDefinition(
        code='SECURITY_SQL_INJECTION_DETECTED',
        message='检测到 SQL 注入攻击',
        severity=ErrorSeverity.CRITICAL,
        http_status=400,
        category='SECURITY',
        retryable=False,
        user_message='输入包含非法内容',
        action_suggestion='fix_input'
    )
    
    # 频率限制 (6300-6399)
    SECURITY_RATE_LIMIT_EXCEEDED = ErrorCodeDefinition(
        code='SECURITY_RATE_LIMIT_EXCEEDED',
        message='请求频率超限',
        severity=ErrorSeverity.WARNING,
        http_status=429,
        category='SECURITY',
        retryable=True,
        user_message='请求过于频繁，请稍后再试',
        action_suggestion='wait_retry'
    )


# ==================== 工具函数 ====================

def get_error_code(code_or_enum) -> ErrorCodeDefinition:
    """
    获取错误码定义
    
    Args:
        code_or_enum: 错误码字符串或枚举值
        
    Returns:
        ErrorCodeDefinition: 错误码定义
    """
    if isinstance(code_or_enum, Enum):
        return code_or_enum.value
    
    # 从所有枚举类中查找
    for enum_class in [CommonErrorCode, DiagnosisErrorCode, AIPlatformErrorCode, 
                       DatabaseErrorCode, AnalyticsErrorCode, SecurityErrorCode]:
        if hasattr(enum_class, code_or_enum):
            return getattr(enum_class, code_or_enum).value
    
    # 返回未知错误
    return CommonErrorCode.UNKNOWN_ERROR.value


def get_retryable_errors() -> Dict[str, ErrorCodeDefinition]:
    """
    获取所有可重试的错误码
    
    Returns:
        Dict[str, ErrorCodeDefinition]: 可重试的错误码字典
    """
    retryable = {}
    for enum_class in [CommonErrorCode, DiagnosisErrorCode, AIPlatformErrorCode, 
                       DatabaseErrorCode, AnalyticsErrorCode, SecurityErrorCode]:
        for item in enum_class:
            if item.value.retryable:
                retryable[item.value.code] = item.value
    return retryable


def get_error_by_category(category: str) -> Dict[str, ErrorCodeDefinition]:
    """
    按分类获取错误码
    
    Args:
        category: 错误分类（COMMON, DIAGNOSIS, AI_PLATFORM, DATABASE, ANALYTICS, SECURITY）
        
    Returns:
        Dict[str, ErrorCodeDefinition]: 错误码字典
    """
    category_map = {
        'COMMON': CommonErrorCode,
        'DIAGNOSIS': DiagnosisErrorCode,
        'AI_PLATFORM': AIPlatformErrorCode,
        'DATABASE': DatabaseErrorCode,
        'ANALYTICS': AnalyticsErrorCode,
        'SECURITY': SecurityErrorCode,
    }
    
    enum_class = category_map.get(category.upper())
    if not enum_class:
        return {}
    
    return {item.value.code: item.value for item in enum_class}
