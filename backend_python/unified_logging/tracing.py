"""
增强链路追踪模块

提供完整的分布式链路追踪功能，包括:
- Span 和 Trace 数据模型
- 链路追踪上下文传播
- 父子 Span 关系管理
- 链路追踪导出器
- 日志采样策略

使用示例:
    from backend_python.unified_logging.tracing import (
        TraceContext,
        Span,
        TracingSampler,
        start_span,
    )
    
    # 方式 1: 手动管理 Span
    trace = TraceContext.new_trace()
    with Span(trace, 'operation_name') as span:
        span.set_attribute('key', 'value')
        logger.info('Processing', trace_id=trace.trace_id, span_id=span.span_id)
    
    # 方式 2: 使用装饰器
    @start_span('process_request')
    def process_request(request):
        ...
    
    # 方式 3: 使用采样器
    sampler = TracingSampler(sample_rate=0.1)
    if sampler.should_sample():
        # 记录详细日志
        ...
"""

import uuid
import time
import threading
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import contextvars
import json


# ============================================================================
# 枚举和常量
# ============================================================================

class SpanStatus(Enum):
    """Span 状态"""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


class SamplingDecision(Enum):
    """采样决策"""
    DROP = "DROP"
    RECORD = "RECORD"
    RECORD_AND_SAMPLE = "RECORD_AND_SAMPLE"


# 链路追踪上下文变量
_tracing_context = contextvars.ContextVar('tracing_context', default=None)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class TraceContext:
    """
    链路追踪上下文
    
    属性:
        trace_id: 追踪 ID (全局唯一)
        parent_trace_id: 父追踪 ID (可选)
        flags: 追踪标志
    """
    trace_id: str
    parent_trace_id: Optional[str] = None
    flags: int = 1
    
    @classmethod
    def new_trace(cls, trace_id: str = None) -> 'TraceContext':
        """创建新的追踪上下文"""
        return cls(
            trace_id=trace_id or str(uuid.uuid4()),
            parent_trace_id=None,
            flags=1
        )
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional['TraceContext']:
        """从 HTTP 请求头恢复追踪上下文"""
        trace_id = headers.get('X-Trace-ID') or headers.get('x-trace-id')
        if not trace_id:
            return None
        
        parent_trace_id = headers.get('X-Parent-Trace-ID') or headers.get('x-parent-trace-id')
        flags = int(headers.get('X-Trace-Flags', '1'))
        
        return cls(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            flags=flags
        )
    
    def to_headers(self) -> Dict[str, str]:
        """转换为 HTTP 请求头"""
        headers = {
            'X-Trace-ID': self.trace_id,
            'X-Trace-Flags': str(self.flags),
        }
        if self.parent_trace_id:
            headers['X-Parent-Trace-ID'] = self.parent_trace_id
        return headers
    
    def create_child(self) -> 'TraceContext':
        """创建子追踪上下文"""
        return TraceContext(
            trace_id=self.trace_id,
            parent_trace_id=self.trace_id,
            flags=self.flags
        )


@dataclass
class Span:
    """
    Span 数据模型
    
    表示链路追踪中的一个操作单元。
    
    属性:
        trace_id: 所属追踪 ID
        span_id: Span ID
        parent_span_id: 父 Span ID
        name: Span 名称
        start_time: 开始时间
        end_time: 结束时间
        status: 状态
        attributes: 属性字典
        events: 事件列表
    """
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_span_id: Optional[str] = None
    name: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def start(self):
        """开始 Span"""
        self.start_time = time.time()
        return self
    
    def end(self, status: SpanStatus = None):
        """结束 Span"""
        self.end_time = time.time()
        if status:
            self.status = status
        return self
    
    def set_attribute(self, key: str, value: Any):
        """设置属性"""
        self.attributes[key] = value
        return self
    
    def set_attributes(self, attributes: Dict[str, Any]):
        """批量设置属性"""
        self.attributes.update(attributes)
        return self
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """添加事件"""
        event = {
            'timestamp': time.time(),
            'name': name,
            'attributes': attributes or {}
        }
        self.events.append(event)
        return self
    
    def record_exception(self, exception: Exception):
        """记录异常"""
        self.set_attribute('error.type', type(exception).__name__)
        self.set_attribute('error.message', str(exception))
        self.status = SpanStatus.ERROR
        return self
    
    def duration_ms(self) -> Optional[float]:
        """获取持续时间 (毫秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms(),
            'status': self.status.value,
            'attributes': self.attributes,
            'events': self.events,
        }
    
    def __enter__(self):
        self.start()
        # 设置当前 Span 到上下文
        _tracing_context.set(self)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.record_exception(exc_val)
            self.end(SpanStatus.ERROR)
        else:
            self.end(SpanStatus.OK)
        # 恢复上下文
        _tracing_context.set(None)
        return False


# ============================================================================
# 采样器
# ============================================================================

class TracingSampler:
    """
    链路追踪采样器
    
    用于控制链路追踪的采样率，降低高并发场景下的存储和性能开销。
    
    使用示例:
        # 固定比例采样
        sampler = TracingSampler(sample_rate=0.1)  # 10% 采样
        
        # 基于规则的采样
        sampler = TracingSampler(
            sample_rate=0.1,
            always_sample_paths=['/api/important'],
            never_sample_paths=['/health', '/metrics']
        )
        
        if sampler.should_sample(path='/api/chat'):
            # 记录详细日志
            ...
    """
    
    def __init__(
        self,
        sample_rate: float = 0.1,
        always_sample_paths: List[str] = None,
        never_sample_paths: List[str] = None,
        seed: int = None,
    ):
        """
        初始化采样器
        
        Args:
            sample_rate: 采样率 (0.0-1.0)
            always_sample_paths: 始终采样的路径列表
            never_sample_paths: 永不采样的路径列表
            seed: 随机种子
        """
        self.sample_rate = max(0.0, min(1.0, sample_rate))
        self.always_sample_paths = always_sample_paths or []
        self.never_sample_paths = never_sample_paths or []
        self._random = random.Random(seed)
        self._lock = threading.Lock()
    
    def should_sample(
        self,
        trace_id: str = None,
        path: str = None,
        **kwargs
    ) -> bool:
        """
        判断是否应该采样
        
        Args:
            trace_id: 追踪 ID (用于一致性哈希)
            path: 请求路径
            **kwargs: 其他参数
        
        Returns:
            是否采样
        """
        # 检查永不采样路径
        if path and self._match_paths(path, self.never_sample_paths):
            return False
        
        # 检查始终采样路径
        if path and self._match_paths(path, self.always_sample_paths):
            return True
        
        # 基于 trace_id 的一致性采样
        if trace_id:
            return self._consistent_sample(trace_id)
        
        # 随机采样
        return self._random.random() < self.sample_rate
    
    def _match_paths(self, path: str, patterns: List[str]) -> bool:
        """匹配路径模式"""
        for pattern in patterns:
            if pattern.startswith('*'):
                if path.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if path.startswith(pattern[:-1]):
                    return True
            elif path == pattern:
                return True
        return False
    
    def _consistent_sample(self, trace_id: str) -> bool:
        """基于 trace_id 的一致性采样"""
        # 使用 trace_id 的哈希值进行采样
        hash_value = hash(trace_id) % 10000
        threshold = int(self.sample_rate * 10000)
        return hash_value < threshold
    
    def get_sampling_decision(
        self,
        trace_id: str = None,
        path: str = None,
        **kwargs
    ) -> SamplingDecision:
        """
        获取采样决策
        
        Returns:
            SamplingDecision 枚举
        """
        if self.should_sample(trace_id, path, **kwargs):
            return SamplingDecision.RECORD_AND_SAMPLE
        return SamplingDecision.DROP


# ============================================================================
# 链路追踪工具函数
# ============================================================================

def get_current_span() -> Optional[Span]:
    """获取当前 Span"""
    return _tracing_context.get()


def get_current_trace_id() -> Optional[str]:
    """获取当前追踪 ID"""
    span = get_current_span()
    if span:
        return span.trace_id
    
    # 从日志上下文获取
    from unified_logging.unified_logger import _trace_context
    context = _trace_context.get()
    if context and 'trace_id' in context:
        return context['trace_id']
    
    return None


def get_current_span_id() -> Optional[str]:
    """获取当前 Span ID"""
    span = get_current_span()
    if span:
        return span.span_id
    
    from unified_logging.unified_logger import _trace_context
    context = _trace_context.get()
    if context and 'span_id' in context:
        return context['span_id']
    
    return None


def start_span(
    name: str,
    trace_id: str = None,
    parent_span_id: str = None,
    attributes: Dict[str, Any] = None,
) -> Span:
    """
    创建并启动新的 Span
    
    Args:
        name: Span 名称
        trace_id: 追踪 ID (自动生成如果未提供)
        parent_span_id: 父 Span ID
        attributes: 初始属性
    
    Returns:
        Span 实例
    """
    # 获取或创建追踪 ID
    if trace_id is None:
        current_span = get_current_span()
        if current_span:
            trace_id = current_span.trace_id
        else:
            from unified_logging.unified_logger import _trace_context
            context = _trace_context.get()
            trace_id = context.get('trace_id') if context else None
        
        if trace_id is None:
            trace_id = str(uuid.uuid4())
    
    # 获取父 Span ID
    if parent_span_id is None:
        current_span = get_current_span()
        if current_span:
            parent_span_id = current_span.span_id
    
    # 创建 Span
    span = Span(
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        name=name,
    )
    
    if attributes:
        span.set_attributes(attributes)
    
    return span.start()


def span_decorator(name: str = None):
    """
    Span 装饰器
    
    使用示例:
        @span_decorator('process_request')
        def process_request(request):
            ...
        
        @span_decorator()  # 自动使用函数名
        def handle_data(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__
        
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span = start_span(span_name)
            try:
                # 设置函数属性
                span.set_attribute('function', func.__qualname__)
                
                # 设置 tracing context
                _tracing_context.set(span)

                result = func(*args, **kwargs)
                span.end(SpanStatus.OK)
                return result
            except Exception as e:
                span.record_exception(e)
                span.end(SpanStatus.ERROR)
                raise
            finally:
                # 清理上下文
                _tracing_context.set(None)

        return wrapper
    
    return decorator


# ============================================================================
# 结构化日志增强
# ============================================================================

@dataclass
class LogRecord:
    """
    增强的日志记录
    
    包含完整的结构化日志信息。
    """
    timestamp: str
    level: str
    logger: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    service: str = ""
    module: str = ""
    function: str = ""
    line: int = 0
    thread: str = ""
    process: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        data = {
            'timestamp': self.timestamp,
            'level': self.level,
            'logger': self.logger,
            'message': self.message,
            'service': self.service,
            'module': self.module,
            'function': self.function,
            'line': self.line,
            'thread': self.thread,
            'process': self.process,
            'attributes': self.attributes,
        }
        
        # 添加链路追踪信息
        if self.trace_id:
            data['trace_id'] = self.trace_id
        if self.span_id:
            data['span_id'] = self.span_id
        if self.parent_span_id:
            data['parent_span_id'] = self.parent_span_id
        
        return json.dumps(data, ensure_ascii=False, default=str)


def create_log_record(
    level: str,
    message: str,
    logger_name: str = "",
    **attributes
) -> LogRecord:
    """
    创建日志记录
    
    Args:
        level: 日志级别
        message: 日志消息
        logger_name: 日志器名称
        **attributes: 额外属性
    
    Returns:
        LogRecord 实例
    """
    # 获取链路追踪信息
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()
    parent_span_id = None
    
    current_span = get_current_span()
    if current_span:
        parent_span_id = current_span.parent_span_id
    
    return LogRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        level=level,
        message=message,
        logger=logger_name,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        service='wechat_backend',
        attributes=attributes,
    )


# ============================================================================
# HTTP 链路追踪传播器
# ============================================================================

class HTTPTracePropagator:
    """
    HTTP 链路追踪传播器
    
    用于在 HTTP 请求之间传播链路追踪上下文。
    
    使用示例:
        propagator = HTTPTracePropagator()
        
        # 服务端：从请求头提取追踪上下文
        trace_context = propagator.extract(request.headers)
        
        # 客户端：注入追踪上下文到请求头
        headers = propagator.inject(trace_context)
        requests.get(url, headers=headers)
    """
    
    def __init__(self, header_prefix: str = 'X-'):
        self.header_prefix = header_prefix
    
    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """从 HTTP 请求头提取追踪上下文"""
        return TraceContext.from_headers(headers)
    
    def inject(self, trace_context: TraceContext) -> Dict[str, str]:
        """注入追踪上下文到 HTTP 请求头"""
        return trace_context.to_headers()
    
    def fields(self) -> List[str]:
        """获取传播器使用的字段列表"""
        return [
            f'{self.header_prefix}Trace-ID',
            f'{self.header_prefix}Parent-Trace-ID',
            f'{self.header_prefix}Trace-Flags',
        ]


# ============================================================================
# 导出器接口
# ============================================================================

class SpanExporter:
    """Span 导出器接口"""
    
    def export(self, spans: List[Span]) -> bool:
        """导出 Spans"""
        raise NotImplementedError
    
    def shutdown(self):
        """关闭导出器"""
        pass


class ConsoleSpanExporter(SpanExporter):
    """控制台 Span 导出器"""
    
    def export(self, spans: List[Span]) -> bool:
        for span in spans:
            print(f"[Span] {span.name} - trace_id={span.trace_id}, "
                  f"span_id={span.span_id}, duration={span.duration_ms():.2f}ms")
        return True


class LoggingSpanExporter(SpanExporter):
    """日志 Span 导出器"""
    
    def __init__(self, logger=None):
        self.logger = logger or __import__('logging').getLogger(__name__)
    
    def export(self, spans: List[Span]) -> bool:
        for span in spans:
            self.logger.info(
                f"Span ended: {span.name}",
                extra={'span': span.to_dict()}
            )
        return True


# ============================================================================
# 便捷函数
# ============================================================================

def trace_context_manager(trace_id: str = None) -> TraceContext:
    """
    创建追踪上下文管理器
    
    使用示例:
        with trace_context_manager() as trace:
            logger.info('In trace context', trace_id=trace.trace_id)
    """
    return TraceContext.new_trace(trace_id)


def span_context_manager(
    name: str,
    trace_id: str = None,
    attributes: Dict[str, Any] = None,
) -> Span:
    """
    创建 Span 上下文管理器
    
    使用示例:
        with span_context_manager('operation') as span:
            span.set_attribute('key', 'value')
            logger.info('Processing')
    """
    span = start_span(name, trace_id=trace_id, attributes=attributes)
    return span


# 导出所有符号
__all__ = [
    # 数据模型
    'TraceContext',
    'Span',
    'SpanStatus',
    'LogRecord',
    # 采样器
    'TracingSampler',
    'SamplingDecision',
    # 工具函数
    'get_current_span',
    'get_current_trace_id',
    'get_current_span_id',
    'start_span',
    'span_decorator',
    'create_log_record',
    # 传播器
    'HTTPTracePropagator',
    # 导出器
    'SpanExporter',
    'ConsoleSpanExporter',
    'LoggingSpanExporter',
    # 上下文管理器
    'trace_context_manager',
    'span_context_manager',
    # 常量
    '_tracing_context',
]
