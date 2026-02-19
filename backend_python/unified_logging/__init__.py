"""
统一日志模块

提供异步队列日志写入功能，解决性能瓶颈问题。

主要组件:
- UnifiedLoggerFactory: 单例工厂，负责初始化和获取日志器
- UnifiedLogger: 统一日志器，提供便捷的日志记录接口
- JSONFormatter: JSON 格式化器，输出结构化日志
- LoggingContext: 日志上下文管理器，支持链路追踪
- tracing: 链路追踪模块
- middleware: HTTP 链路追踪中间件

使用示例:
    # 应用启动时初始化
    from backend_python.unified_logging import UnifiedLoggerFactory
    
    logger_factory = UnifiedLoggerFactory()
    logger_factory.initialize()
    
    # 业务代码中使用
    logger = logger_factory.get_logger('wechat_backend.api')
    logger.info('API 请求', endpoint='/api/ai/chat', user_id='user_001')
    
    # 应用关闭时
    logger_factory.shutdown()
"""

from .unified_logger import (
    UnifiedLoggerFactory,
    UnifiedLogger,
    JSONFormatter,
    LoggingContext,
    get_logger,
    init_logging,
    shutdown_logging,
    _trace_context,
)

from .config_loader import (
    load_config,
    init_logging_from_config,
    ConfigManager,
    ConfigChange,
    ConfigState,
)

# 链路追踪模块
from .tracing import (
    TraceContext,
    Span,
    SpanStatus,
    TracingSampler,
    SamplingDecision,
    LogRecord,
    get_current_span,
    get_current_trace_id,
    get_current_span_id,
    start_span,
    span_decorator,
    create_log_record,
    HTTPTracePropagator,
    SpanExporter,
    ConsoleSpanExporter,
    LoggingSpanExporter,
    trace_context_manager,
    span_context_manager,
    _tracing_context,
)

# HTTP 中间件
from .middleware import (
    TraceMiddleware,
    trace_request,
    inject_trace_headers,
    extract_trace_headers,
    set_span_attribute,
    add_span_event,
    record_span_exception,
)

# 生命周期管理
from .lifecycle import (
    LogLifecycleManager,
    LogRotator,
    LogCompressor,
    LogCleaner,
    LogScheduler,
    LogFileInfo,
    LifecycleStats,
    RotationStrategy,
    CompressionAlgorithm,
)

# 外部服务集成
from .integrations import (
    SentryIntegration,
    ELKIntegration,
    PrometheusIntegration,
    ExternalServicesManager,
    IntegrationStatus,
    IntegrationConfig,
    init_sentry,
    init_elk,
    init_prometheus,
    _SENTRY_AVAILABLE,
    _ELASTICSEARCH_AVAILABLE,
    _PROMETHEUS_AVAILABLE,
)

__all__ = [
    # 核心组件
    'UnifiedLoggerFactory',
    'UnifiedLogger',
    'JSONFormatter',
    'LoggingContext',
    'get_logger',
    'init_logging',
    'shutdown_logging',
    # 配置管理
    'load_config',
    'init_logging_from_config',
    'ConfigManager',
    'ConfigChange',
    'ConfigState',
    # 链路追踪
    'TraceContext',
    'Span',
    'SpanStatus',
    'TracingSampler',
    'SamplingDecision',
    'LogRecord',
    'get_current_span',
    'get_current_trace_id',
    'get_current_span_id',
    'start_span',
    'span_decorator',
    'create_log_record',
    'HTTPTracePropagator',
    'SpanExporter',
    'ConsoleSpanExporter',
    'LoggingSpanExporter',
    'trace_context_manager',
    'span_context_manager',
    '_tracing_context',
    # HTTP 中间件
    'TraceMiddleware',
    'trace_request',
    'inject_trace_headers',
    'extract_trace_headers',
    'set_span_attribute',
    'add_span_event',
    'record_span_exception',
    # 生命周期管理
    'LogLifecycleManager',
    'LogRotator',
    'LogCompressor',
    'LogCleaner',
    'LogScheduler',
    'LogFileInfo',
    'LifecycleStats',
    'RotationStrategy',
    'CompressionAlgorithm',
    # 外部服务集成
    'SentryIntegration',
    'ELKIntegration',
    'PrometheusIntegration',
    'ExternalServicesManager',
    'IntegrationStatus',
    'IntegrationConfig',
    'init_sentry',
    'init_elk',
    'init_prometheus',
    '_SENTRY_AVAILABLE',
    '_ELASTICSEARCH_AVAILABLE',
    '_PROMETHEUS_AVAILABLE',
    # 内部变量
    '_trace_context',
]
