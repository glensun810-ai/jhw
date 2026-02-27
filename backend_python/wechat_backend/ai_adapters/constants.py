"""
AI 适配器常量配置

提取所有魔法数字为具名常量，便于维护和配置管理。

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

from dataclasses import dataclass


# ==================== 重试配置 ====================

class RetryConfig:
    """重试配置常量"""
    # 最大重试次数
    MAX_RETRIES = 3
    # 初始重试延迟（秒）
    INITIAL_RETRY_DELAY = 1.0
    # 最大重试延迟（秒）
    MAX_RETRY_DELAY = 10.0
    # 重试延迟乘数（指数退避）
    RETRY_DELAY_MULTIPLIER = 2.0
    # 重试延迟抖动因子（0-1）
    RETRY_JITTER_FACTOR = 0.1


# ==================== 超时配置 ====================

class TimeoutConfig:
    """超时配置常量"""
    # 连接超时（秒）
    CONNECTION_TIMEOUT = 10
    # 读取超时（秒）
    READ_TIMEOUT = 30
    # 总请求超时（秒）
    TOTAL_TIMEOUT = 60
    # 流式响应超时（秒）
    STREAM_TIMEOUT = 120


# ==================== 请求频率限制 ====================

class RateLimitConfig:
    """请求频率限制配置"""
    # 每分钟最大请求数
    MAX_REQUESTS_PER_MINUTE = 60
    # 每小时最大请求数
    MAX_REQUESTS_PER_HOUR = 1000
    # 每日最大请求数
    MAX_REQUESTS_PER_DAY = 10000
    # 请求间隔（秒）
    REQUEST_INTERVAL = 1.0


# ==================== 响应配置 ====================

class ResponseConfig:
    """响应配置常量"""
    # 最大响应长度（字符）
    MAX_RESPONSE_LENGTH = 10000
    # 最小响应长度（字符）
    MIN_RESPONSE_LENGTH = 10
    # JSON 解析超时（秒）
    JSON_PARSE_TIMEOUT = 5
    # 响应内容截断长度
    RESPONSE_TRUNCATE_LENGTH = 1000


# ==================== 错误处理配置 ====================

class ErrorConfig:
    """错误处理配置常量"""
    # 错误日志最大长度
    MAX_ERROR_LOG_LENGTH = 500
    # 堆栈跟踪最大层数
    MAX_TRACEBACK_DEPTH = 10
    # 错误消息最大长度
    MAX_ERROR_MESSAGE_LENGTH = 1000
    # 可重试错误类型
    RETRYABLE_ERROR_TYPES = frozenset([
        'RATE_LIMIT_EXCEEDED',
        'SERVER_ERROR',
        'SERVICE_UNAVAILABLE',
        'TIMEOUT',
    ])


# ==================== 健康检查配置 ====================

class HealthCheckConfig:
    """健康检查配置常量"""
    # 健康检查间隔（秒）
    CHECK_INTERVAL = 30
    # 连续失败阈值
    FAILURE_THRESHOLD = 3
    # 恢复成功阈值
    RECOVERY_THRESHOLD = 2
    # 熔断器开启阈值（失败率）
    CIRCUIT_BREAKER_THRESHOLD = 0.5
    # 熔断器恢复时间（秒）
    CIRCUIT_BREAKER_RECOVERY_TIME = 60


# ==================== 模型配置 ====================

class ModelConfig:
    """模型配置常量"""
    # 默认模型名称
    DEFAULT_MODEL_NAME = 'default'
    # 模型名称最大长度
    MAX_MODEL_NAME_LENGTH = 50
    # 支持的模型数量上限
    MAX_MODELS_PER_PLATFORM = 10


# ==================== 数据验证配置 ====================

class ValidationConfig:
    """数据验证配置常量"""
    # API Key 最小长度
    MIN_API_KEY_LENGTH = 10
    # API Key 最大长度
    MAX_API_KEY_LENGTH = 200
    # 提示词最大长度（字符）
    MAX_PROMPT_LENGTH = 10000
    # 提示词最小长度（字符）
    MIN_PROMPT_LENGTH = 1
    # 执行 ID 最大长度
    MAX_EXECUTION_ID_LENGTH = 100


# ==================== 日志配置 ====================

class LogConfig:
    """日志配置常量"""
    # 日志消息最大长度
    MAX_LOG_MESSAGE_LENGTH = 1000
    # 详细日志模式
    VERBOSE_LOG = False
    # 日志采样率（0-1）
    LOG_SAMPLE_RATE = 0.1
    # 慢请求阈值（秒）
    SLOW_REQUEST_THRESHOLD = 5.0


# ==================== 缓存配置 ====================

class CacheConfig:
    """缓存配置常量"""
    # 缓存有效期（秒）
    CACHE_TTL = 300
    # 缓存最大条目数
    MAX_CACHE_ENTRIES = 1000
    # 缓存清理间隔（秒）
    CACHE_CLEANUP_INTERVAL = 600


@dataclass
class AdapterConstants:
    """适配器常量聚合类"""
    # 重试配置
    retry: RetryConfig = RetryConfig()
    # 超时配置
    timeout: TimeoutConfig = TimeoutConfig()
    # 频率限制
    rate_limit: RateLimitConfig = RateLimitConfig()
    # 响应配置
    response: ResponseConfig = ResponseConfig()
    # 错误处理
    error: ErrorConfig = ErrorConfig()
    # 健康检查
    health_check: HealthCheckConfig = HealthCheckConfig()
    # 模型配置
    model: ModelConfig = ModelConfig()
    # 数据验证
    validation: ValidationConfig = ValidationConfig()
    # 日志配置
    log: LogConfig = LogConfig()
    # 缓存配置
    cache: CacheConfig = CacheConfig()


# 全局常量实例
CONSTANTS = AdapterConstants()
