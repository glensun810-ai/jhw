"""
HTTP 请求链路追踪中间件

为 Flask 应用提供自动链路追踪功能，包括:
- 自动提取/注入追踪上下文
- 自动创建 Span
- 记录请求/响应信息
- 性能指标采集

使用示例:
    from flask import Flask
    from backend_python.unified_logging.middleware import TraceMiddleware
    
    app = Flask(__name__)
    
    # 添加中间件
    TraceMiddleware(app)
    
    @app.route('/api/chat')
    def chat():
        # 自动包含 trace_id 和 span_id
        logger.info('Processing chat request')
        ...
"""

import time
import uuid
from typing import Optional, Callable, Dict, Any
from functools import wraps

try:
    from flask import Flask, request, g, has_request_context
    _FLASK_AVAILABLE = True
except ImportError:
    _FLASK_AVAILABLE = False
    Flask = None
    request = None
    g = None
    has_request_context = None

from .tracing import (
    TraceContext,
    Span,
    SpanStatus,
    HTTPTracePropagator,
    TracingSampler,
    get_current_span,
    start_span,
    _tracing_context,
)


class TraceMiddleware:
    """
    HTTP 请求链路追踪中间件
    
    功能:
    - 自动从请求头提取追踪上下文
    - 为每个请求创建 Span
    - 记录请求/响应信息
    - 支持采样
    - 支持自定义属性
    """
    
    def __init__(
        self,
        app: Flask = None,
        service_name: str = 'wechat_backend',
        sampler: TracingSampler = None,
        propagator: HTTPTracePropagator = None,
        skip_paths: list = None,
    ):
        """
        初始化中间件
        
        Args:
            app: Flask 应用
            service_name: 服务名称
            sampler: 采样器
            propagator: 追踪传播器
            skip_paths: 跳过追踪的路径列表
        """
        self.app = app
        self.service_name = service_name
        self.sampler = sampler or TracingSampler(sample_rate=1.0)
        self.propagator = propagator or HTTPTracePropagator()
        self.skip_paths = skip_paths or ['/health', '/metrics', '/favicon.ico']
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化 Flask 应用"""
        if not _FLASK_AVAILABLE:
            return
        
        self.app = app
        
        # 注册请求前钩子
        app.before_request(self._before_request)
        
        # 注册请求后钩子
        app.after_request(self._after_request)
        
        # 注册异常钩子
        app.teardown_request(self._teardown_request)
    
    def _should_skip(self, path: str) -> bool:
        """判断是否应该跳过追踪"""
        for skip_path in self.skip_paths:
            if skip_path.startswith('*'):
                if path.endswith(skip_path[1:]):
                    return True
            elif skip_path.endswith('*'):
                if path.startswith(skip_path[:-1]):
                    return True
            elif path == skip_path:
                return True
        return False
    
    def _before_request(self):
        """请求前处理"""
        if not _FLASK_AVAILABLE or not has_request_context():
            return
        
        path = request.path
        
        # 检查是否跳过
        if self._should_skip(path):
            return
        
        # 从请求头提取追踪上下文
        trace_context = self.propagator.extract(dict(request.headers))
        
        # 如果没有追踪上下文，创建新的
        if not trace_context:
            trace_context = TraceContext.new_trace(str(uuid.uuid4()))
        
        # 检查是否采样
        if not self.sampler.should_sample(
            trace_id=trace_context.trace_id,
            path=path,
        ):
            # 不采样，但仍设置追踪 ID 用于日志关联
            g.trace_context = trace_context
            g.span = None
            g.skip_tracing = True
            return
        
        g.trace_context = trace_context
        g.skip_tracing = False
        
        # 创建 Span
        span = start_span(
            name=f"{request.method} {path}",
            trace_id=trace_context.trace_id,
            attributes={
                'http.method': request.method,
                'http.url': request.url,
                'http.path': path,
                'service': self.service_name,
            }
        )
        
        g.span = span
        
        # 记录请求开始时间
        g.start_time = time.time()
        
        # 设置日志上下文
        from .unified_logger import _trace_context as log_context
        log_context.set({
            'trace_id': trace_context.trace_id,
            'span_id': span.span_id,
        })
    
    def _after_request(self, response):
        """请求后处理"""
        if not _FLASK_AVAILABLE or not has_request_context():
            return response
        
        # 检查是否跳过
        if getattr(g, 'skip_tracing', False):
            # 注入追踪 ID 到响应头 (即使不采样)
            trace_context = getattr(g, 'trace_context', None)
            if trace_context:
                headers = self.propagator.inject(trace_context)
                for key, value in headers.items():
                    response.headers[key] = value
            return response
        
        span = getattr(g, 'span', None)
        if not span:
            return response
        
        # 记录响应信息
        duration = (time.time() - getattr(g, 'start_time', time.time())) * 1000
        
        span.set_attributes({
            'http.status_code': response.status_code,
            'http.response_time_ms': duration,
        })
        
        # 根据状态码设置 Span 状态
        if response.status_code >= 500:
            span.status = SpanStatus.ERROR
        else:
            span.status = SpanStatus.OK
        
        # 结束 Span
        span.end()
        
        # 注入追踪 ID 到响应头
        trace_context = getattr(g, 'trace_context', None)
        if trace_context:
            headers = self.propagator.inject(trace_context)
            for key, value in headers.items():
                response.headers[key] = value
        
        return response
    
    def _teardown_request(self, exception):
        """请求结束处理"""
        if not _FLASK_AVAILABLE:
            return
        
        # 检查是否跳过
        if getattr(g, 'skip_tracing', False):
            return
        
        span = getattr(g, 'span', None)
        if not span:
            return
        
        # 如果有异常且 Span 未结束
        if exception and span.end_time is None:
            span.record_exception(exception)
            span.end(SpanStatus.ERROR)
        
        # 清理上下文
        _tracing_context.set(None)
    
    def get_current_trace_id(self) -> Optional[str]:
        """获取当前追踪 ID"""
        if _FLASK_AVAILABLE and has_request_context():
            trace_context = getattr(g, 'trace_context', None)
            if trace_context:
                return trace_context.trace_id
        return None
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前 Span"""
        if _FLASK_AVAILABLE and has_request_context():
            return getattr(g, 'span', None)
        return None


def trace_request(
    name: str = None,
    attributes: Dict[str, Any] = None,
):
    """
    请求追踪装饰器
    
    用于手动追踪特定请求或操作。
    
    使用示例:
        @app.route('/api/chat')
        @trace_request('handle_chat', attributes={'type': 'chat'})
        def handle_chat():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取或创建追踪 ID
            trace_id = None
            if _FLASK_AVAILABLE and has_request_context():
                trace_context = getattr(g, 'trace_context', None)
                if trace_context:
                    trace_id = trace_context.trace_id
            
            # 创建 Span
            span_name = name or func.__name__
            span = start_span(
                span_name,
                trace_id=trace_id,
                attributes=attributes or {},
            )
            
            try:
                result = func(*args, **kwargs)
                span.end(SpanStatus.OK)
                return result
            except Exception as e:
                span.record_exception(e)
                span.end(SpanStatus.ERROR)
                raise
        
        return wrapper
    
    return decorator


def inject_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    注入追踪上下文到请求头
    
    使用示例:
        headers = inject_trace_headers({})
        requests.get(url, headers=headers)
    """
    propagator = HTTPTracePropagator()
    
    # 获取当前追踪上下文
    if _FLASK_AVAILABLE and has_request_context():
        trace_context = getattr(g, 'trace_context', None)
        if trace_context:
            return propagator.inject(trace_context)
    
    # 从 tracing context 获取
    span = get_current_span()
    if span:
        trace_context = TraceContext(
            trace_id=span.trace_id,
            parent_span_id=span.span_id,
        )
        return propagator.inject(trace_context)
    
    return headers


def extract_trace_headers(headers: Dict[str, str]) -> Optional[TraceContext]:
    """
    从请求头提取追踪上下文
    
    使用示例:
        trace_context = extract_trace_headers(request.headers)
    """
    propagator = HTTPTracePropagator()
    return propagator.extract(headers)


# 便捷函数
def set_span_attribute(key: str, value: Any):
    """设置当前 Span 的属性"""
    span = get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Dict[str, Any] = None):
    """添加事件到当前 Span"""
    span = get_current_span()
    if span:
        span.add_event(name, attributes)


def record_span_exception(exception: Exception):
    """记录异常到当前 Span"""
    span = get_current_span()
    if span:
        span.record_exception(exception)


# 导出所有符号
__all__ = [
    'TraceMiddleware',
    'trace_request',
    'inject_trace_headers',
    'extract_trace_headers',
    'set_span_attribute',
    'add_span_event',
    'record_span_exception',
]
