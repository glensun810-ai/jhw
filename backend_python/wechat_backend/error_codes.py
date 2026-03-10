"""
统一错误码定义模块

P2-2 优化：统一错误码管理，解决错误码分散问题

错误码格式：XXXX-XXX
- 前 4 位：错误类别
- 后 3 位：具体错误

错误类别:
- 1000: 通用错误
- 2000: 诊断执行错误
- 3000: 数据库错误
- 4000: AI 服务错误
- 5000: 报告处理错误
- 6000: 数据验证错误
- 7000: 前端/客户端错误

使用示例:
    from wechat_backend.error_codes import ErrorCode, get_error_message
    
    # 抛出错误
    raise BusinessException(ErrorCode.REPORT_NOT_FOUND)
    
    # 获取错误消息
    msg = get_error_message(ErrorCode.REPORT_NOT_FOUND)
    
    # 获取带参数的错误消息
    msg = get_error_message(ErrorCode.AI_TIMEOUT, {'timeout': 30})
"""

from enum import Enum
from typing import Dict, Any, Optional


class ErrorCode(Enum):
    """
    统一错误码枚举
    
    格式：XXXX-XXX (类别 - 具体错误)
    """
    
    # ==================== 1000: 通用错误 ====================
    SUCCESS = ("1000-000", "成功", 200)
    UNKNOWN_ERROR = ("1000-001", "未知错误", 500)
    INVALID_PARAMETER = ("1000-002", "参数无效：{parameter}", 400)
    MISSING_PARAMETER = ("1000-003", "缺少必填参数：{parameter}", 400)
    UNAUTHORIZED = ("1000-004", "未授权访问", 401)
    FORBIDDEN = ("1000-005", "禁止访问", 403)
    NOT_FOUND = ("1000-006", "资源不存在", 404)
    METHOD_NOT_ALLOWED = ("1000-007", "方法不允许", 405)
    CONFLICT = ("1000-008", "资源冲突", 409)
    RATE_LIMIT_EXCEEDED = ("1000-009", "请求频率超限", 429)
    INTERNAL_ERROR = ("1000-010", "系统内部错误", 500)
    SERVICE_UNAVAILABLE = ("1000-011", "服务不可用", 503)
    REQUEST_TIMEOUT = ("1000-012", "请求超时", 408)
    PAYLOAD_TOO_LARGE = ("1000-013", "请求体过大", 413)
    UNSUPPORTED_MEDIA_TYPE = ("1000-014", "不支持的媒体类型", 415)
    
    # ==================== 2000: 诊断执行错误 ====================
    DIAGNOSIS_NOT_FOUND = ("2000-001", "诊断任务不存在", 404)
    DIAGNOSIS_ALREADY_EXISTS = ("2000-002", "诊断任务已存在", 409)
    DIAGNOSIS_EXECUTION_FAILED = ("2000-003", "诊断执行失败：{reason}", 500)
    DIAGNOSIS_TIMEOUT = ("2000-004", "诊断超时：{timeout}秒", 408)
    DIAGNOSIS_CANCELLED = ("2000-005", "诊断已取消", 499)
    DIAGNOSIS_IN_PROGRESS = ("2000-006", "诊断正在进行中", 202)
    DIAGNOSIS_NOT_COMPLETED = ("2000-007", "诊断尚未完成", 400)
    DIAGNOSIS_CONFIG_INVALID = ("2000-008", "诊断配置无效：{detail}", 400)
    DIAGNOSIS_BRAND_MISSING = ("2000-009", "品牌列表不能为空", 400)
    DIAGNOSIS_COMPETITOR_MISSING = ("2000-010", "竞品列表不能为空", 400)
    DIAGNOSIS_MODEL_MISSING = ("2000-011", "AI 模型列表不能为空", 400)
    DIAGNOSIS_QUESTION_MISSING = ("2000-012", "问题列表不能为空", 400)
    DIAGNOSIS_PARTIAL_SUCCESS = ("2000-013", "诊断部分成功：{success_count}/{total_count}", 207)
    DIAGNOSIS_SAVE_FAILED = ("2000-014", "诊断结果保存失败：{detail}", 500)
    DIAGNOSIS_INIT_FAILED = ("2000-015", "诊断初始化失败：{detail}", 500)
    DIAGNOSIS_RESULT_INVALID = ("2000-016", "诊断结果无效：{detail}", 400)
    DIAGNOSIS_RESULT_COUNT_MISMATCH = ("2000-017", "诊断结果数量不匹配：{expected}/{actual}", 400)
    DIAGNOSIS_REPORT_AGGREGATION_FAILED = ("2000-018", "诊断报告聚合失败：{detail}", 500)
    DIAGNOSIS_ANALYSIS_FAILED = ("2000-019", "诊断分析失败：{detail}", 500)

    # ==================== 3000: 数据库错误 ====================
    DATABASE_ERROR = ("3000-001", "数据库错误：{detail}", 500)
    DATABASE_CONNECTION_FAILED = ("3000-002", "数据库连接失败", 503)
    DATABASE_QUERY_FAILED = ("3000-003", "数据库查询失败：{detail}", 500)
    DATABASE_INSERT_FAILED = ("3000-004", "数据库插入失败：{detail}", 500)
    DATABASE_UPDATE_FAILED = ("3000-005", "数据库更新失败：{detail}", 500)
    DATABASE_DELETE_FAILED = ("3000-006", "数据库删除失败：{detail}", 500)
    DATABASE_CONSTRAINT_VIOLATION = ("3000-007", "数据库约束违反：{detail}", 400)
    DATABASE_NOT_NULL_VIOLATION = ("3000-008", "非空约束违反：{field}", 400)
    DATABASE_UNIQUE_VIOLATION = ("3000-009", "唯一约束违反：{field}", 409)
    DATABASE_FOREIGN_KEY_VIOLATION = ("3000-010", "外键约束违反：{field}", 400)
    DATABASE_CONNECTION_TIMEOUT = ("3000-011", "数据库连接超时", 408)
    DATABASE_CONNECTION_EXHAUSTED = ("3000-012", "数据库连接池耗尽", 503)
    DATABASE_TRANSACTION_FAILED = ("3000-013", "数据库事务失败：{detail}", 500)
    DATABASE_LOCK_TIMEOUT = ("3000-014", "数据库锁超时", 408)
    DATABASE_DEADLOCK = ("3000-015", "数据库死锁", 500)
    
    # ==================== 4000: AI 服务错误 ====================
    AI_SERVICE_ERROR = ("4000-001", "AI 服务错误：{detail}", 500)
    AI_SERVICE_UNAVAILABLE = ("4000-002", "AI 服务不可用", 503)
    AI_API_KEY_MISSING = ("4000-003", "AI API 密钥未配置", 500)
    AI_TIMEOUT = ("4000-004", "AI 请求超时：{timeout}秒", 408)
    AI_RATE_LIMIT_EXCEEDED = ("4000-005", "AI 请求频率超限", 429)
    AI_INVALID_RESPONSE = ("4000-006", "AI 返回无效响应：{detail}", 502)
    AI_EMPTY_RESPONSE = ("4000-007", "AI 返回空响应", 502)
    AI_RESPONSE_PARSE_FAILED = ("4000-008", "AI 响应解析失败：{detail}", 502)
    AI_MODEL_NOT_FOUND = ("4000-009", "AI 模型不存在：{model}", 400)
    AI_MODEL_UNAVAILABLE = ("4000-010", "AI 模型不可用：{model}", 503)
    AI_QUOTA_EXCEEDED = ("4000-011", "AI 配额已用尽", 429)
    AI_AUTH_FAILED = ("4000-012", "AI 认证失败", 401)
    AI_CONTENT_FILTERED = ("4000-013", "AI 内容被过滤", 400)
    AI_CONTEXT_LENGTH_EXCEEDED = ("4000-014", "AI 上下文长度超限", 400)
    
    # ==================== 5000: 报告处理错误 ====================
    REPORT_NOT_FOUND = ("5000-001", "报告不存在", 404)
    REPORT_ALREADY_EXISTS = ("5000-002", "报告已存在", 409)
    REPORT_GENERATION_FAILED = ("5000-003", "报告生成失败：{detail}", 500)
    REPORT_SAVE_FAILED = ("5000-004", "报告保存失败：{detail}", 500)
    REPORT_LOAD_FAILED = ("5000-005", "报告加载失败：{detail}", 500)
    REPORT_DELETE_FAILED = ("5000-006", "报告删除失败：{detail}", 500)
    REPORT_INVALID_FORMAT = ("5000-007", "报告格式无效：{detail}", 400)
    REPORT_INCOMPLETE = ("5000-008", "报告数据不完整：{missing_fields}", 400)
    REPORT_VALIDATION_FAILED = ("5000-009", "报告验证失败：{detail}", 400)
    REPORT_CHECKSUM_MISMATCH = ("5000-010", "报告校验和不匹配", 400)
    REPORT_EXPIRED = ("5000-011", "报告已过期", 410)
    REPORT_ARCHIVING_FAILED = ("5000-012", "报告归档失败：{detail}", 500)
    REPORT_SNAPSHOT_FAILED = ("5000-013", "报告快照创建失败：{detail}", 500)
    REPORT_LOW_QUALITY = ("5000-014", "报告质量过低：{quality_score}", 400)
    
    # ==================== 6000: 数据验证错误 ====================
    VALIDATION_ERROR = ("6000-001", "数据验证失败：{detail}", 400)
    VALIDATION_TYPE_MISMATCH = ("6000-002", "数据类型不匹配：{field}", 400)
    VALIDATION_LENGTH_MISMATCH = ("6000-003", "数据长度不匹配：{field}", 400)
    VALIDATION_RANGE_ERROR = ("6000-004", "数据范围错误：{field}", 400)
    VALIDATION_FORMAT_ERROR = ("6000-005", "数据格式错误：{field}", 400)
    VALIDATION_PATTERN_MISMATCH = ("6000-006", "数据模式不匹配：{field}", 400)
    VALIDATION_REQUIRED = ("6000-007", "必填字段缺失：{field}", 400)
    VALIDATION_DUPLICATE = ("6000-008", "数据重复：{field}", 409)
    VALIDATION_INVALID_ENUM = ("6000-009", "无效的枚举值：{field}", 400)
    VALIDATION_INVALID_JSON = ("6000-010", "无效的 JSON 格式：{detail}", 400)
    VALIDATION_SCHEMA_MISMATCH = ("6000-011", "数据模式不匹配：{detail}", 400)
    
    # ==================== 7000: 前端/客户端错误 ====================
    CLIENT_ERROR = ("7000-001", "客户端错误：{detail}", 400)
    CLIENT_NETWORK_ERROR = ("7000-002", "客户端网络错误", 503)
    CLIENT_TIMEOUT = ("7000-003", "客户端超时", 408)
    CLIENT_INVALID_REQUEST = ("7000-004", "客户端请求无效：{detail}", 400)
    CLIENT_VERSION_TOO_LOW = ("7000-005", "客户端版本过低", 426)
    CLIENT_UNSUPPORTED_FEATURE = ("7000-006", "客户端不支持的功能", 400)
    CLIENT_CACHE_ERROR = ("7000-007", "客户端缓存错误", 500)
    CLIENT_STORAGE_FULL = ("7000-008", "客户端存储空间不足", 507)
    CLIENT_PERMISSION_DENIED = ("7000-009", "客户端权限被拒绝", 403)
    CLIENT_SESSION_EXPIRED = ("7000-010", "客户端会话过期", 401)
    
    # ==================== 8000: 监控和告警错误 ====================
    MONITORING_ERROR = ("8000-001", "监控错误：{detail}", 500)
    MONITORING_THRESHOLD_EXCEEDED = ("8000-002", "监控阈值超限：{metric}", 500)
    MONITORING_DATA_LOSS = ("8000-003", "监控数据丢失", 500)
    ALERT_TRIGGERED = ("8000-004", "告警触发：{alert_name}", 500)
    METRIC_COLLECTION_FAILED = ("8000-005", "指标采集失败：{metric}", 500)
    
    def __init__(self, code: str, message: str, http_status: int):
        self.code = code
        self.message = message
        self.http_status = http_status
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'message': self.message,
            'http_status': self.http_status
        }


# 错误消息模板缓存
_error_message_cache: Dict[ErrorCode, str] = {}


def get_error_message(error_code: ErrorCode, params: Optional[Dict[str, Any]] = None) -> str:
    """
    获取错误消息
    
    Args:
        error_code: 错误码
        params: 参数用于格式化消息
        
    Returns:
        格式化后的错误消息
    """
    if params:
        try:
            return error_code.message.format(**params)
        except KeyError:
            return error_code.message
    return error_code.message


def get_error_by_code(code_str: str) -> Optional[ErrorCode]:
    """
    根据错误码字符串获取错误码枚举

    Args:
        code_str: 错误码字符串（如 "1000-001"）

    Returns:
        ErrorCode 枚举或 None
    """
    for error_code in ErrorCode:
        if error_code.code == code_str:
            return error_code
    return None


# 兼容别名
get_error_code = get_error_by_code


class BusinessException(Exception):
    """
    业务异常基类
    
    所有业务异常都应继承此类
    """
    
    def __init__(self, error_code: ErrorCode, params: Optional[Dict[str, Any]] = None,
                 detail: Optional[str] = None):
        """
        初始化业务异常
        
        Args:
            error_code: 错误码
            params: 参数用于格式化消息
            detail: 详细错误信息
        """
        self.error_code = error_code
        self.params = params
        self.detail = detail
        self.message = get_error_message(error_code, params)
        self.http_status = error_code.http_status
        
        # 构建完整的错误消息
        full_message = self.message
        if detail:
            full_message += f" - {detail}"
        
        super().__init__(full_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'error_code': self.error_code.code,
            'error_message': self.message,
            'http_status': self.http_status
        }
        if self.detail:
            result['detail'] = self.detail
        if self.params:
            result['params'] = self.params
        return result


# 便捷异常类
class ValidationException(BusinessException):
    """数据验证异常"""
    pass


class DatabaseException(BusinessException):
    """数据库异常"""
    pass


class AIServiceException(BusinessException):
    """AI 服务异常"""
    pass


class ReportException(BusinessException):
    """报告处理异常"""
    pass


class DiagnosisException(BusinessException):
    """诊断执行异常"""
    pass


class ClientException(BusinessException):
    """客户端异常"""
    pass


# ==================== 兼容别名（用于旧代码迁移） ====================
# 以下别名用于兼容使用旧错误码枚举的代码
# 所有别名都指向统一的 ErrorCode 枚举

# 诊断错误码别名
DiagnosisErrorCode = ErrorCode

# AI 平台错误码别名  
AIPlatformErrorCode = ErrorCode

# 数据库错误码别名
DatabaseErrorCode = ErrorCode

# 分析错误码别名
AnalyticsErrorCode = ErrorCode


# 导出所有符号
__all__ = [
    'ErrorCode',
    'get_error_message',
    'get_error_by_code',
    'get_error_code',  # 兼容别名
    'BusinessException',
    'ValidationException',
    'DatabaseException',
    'AIServiceException',
    'ReportException',
    'DiagnosisException',
    'ClientException',
    # 兼容别名
    'DiagnosisErrorCode',
    'AIPlatformErrorCode',
    'DatabaseErrorCode',
    'AnalyticsErrorCode',
]
