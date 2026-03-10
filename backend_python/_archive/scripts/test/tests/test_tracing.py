"""
P1 结构化日志 + 链路追踪单元测试

测试范围:
1. TraceContext 数据模型
2. Span 数据模型和上下文管理
3. TracingSampler 采样器
4. HTTPTracePropagator 传播器
5. 链路追踪工具函数
6. 结构化日志增强
7. HTTP 中间件 (如果 Flask 可用)
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from unified_logging.tracing import (
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
    ConsoleSpanExporter,
    trace_context_manager,
    span_context_manager,
    _tracing_context,
)


class TestTraceContext:
    """测试 TraceContext"""
    
    def test_new_trace(self):
        """测试创建新追踪"""
        trace = TraceContext.new_trace()
        
        assert trace.trace_id is not None
        assert len(trace.trace_id) > 0
        assert trace.parent_trace_id is None
        assert trace.flags == 1
    
    def test_new_trace_with_id(self):
        """测试创建指定 ID 的追踪"""
        trace = TraceContext.new_trace(trace_id='custom-trace-id')
        
        assert trace.trace_id == 'custom-trace-id'
    
    def test_from_headers(self):
        """测试从 HTTP 头恢复追踪"""
        headers = {
            'X-Trace-ID': 'test-trace-123',
            'X-Parent-Trace-ID': 'parent-456',
            'X-Trace-Flags': '1',
        }
        
        trace = TraceContext.from_headers(headers)
        
        assert trace.trace_id == 'test-trace-123'
        assert trace.parent_trace_id == 'parent-456'
        assert trace.flags == 1
    
    def test_from_headers_missing(self):
        """测试缺少追踪 ID 的情况"""
        headers = {'Content-Type': 'application/json'}
        
        trace = TraceContext.from_headers(headers)
        
        assert trace is None
    
    def test_to_headers(self):
        """测试转换为 HTTP 头"""
        trace = TraceContext(
            trace_id='test-trace-123',
            parent_trace_id='parent-456',
            flags=1
        )
        
        headers = trace.to_headers()
        
        assert headers['X-Trace-ID'] == 'test-trace-123'
        assert headers['X-Parent-Trace-ID'] == 'parent-456'
        assert headers['X-Trace-Flags'] == '1'
    
    def test_create_child(self):
        """测试创建子追踪"""
        parent = TraceContext.new_trace(trace_id='parent-trace')
        child = parent.create_child()
        
        assert child.trace_id == parent.trace_id
        assert child.parent_trace_id == parent.trace_id


class TestSpan:
    """测试 Span"""
    
    def test_span_creation(self):
        """测试 Span 创建"""
        span = Span(trace_id='test-trace', name='test_operation')
        
        assert span.trace_id == 'test-trace'
        assert span.name == 'test_operation'
        assert span.span_id is not None
        assert span.parent_span_id is None
        assert span.status == SpanStatus.UNSET
    
    def test_span_start_end(self):
        """测试 Span 开始和结束"""
        span = Span(trace_id='test-trace', name='test_operation')
        
        span.start()
        assert span.start_time is not None
        
        time.sleep(0.01)
        
        span.end()
        assert span.end_time is not None
        assert span.duration_ms() >= 10
    
    def test_span_set_attribute(self):
        """测试设置属性"""
        span = Span(trace_id='test-trace', name='test_operation')
        
        span.set_attribute('key', 'value')
        span.set_attributes({'a': 1, 'b': 2})
        
        assert span.attributes['key'] == 'value'
        assert span.attributes['a'] == 1
        assert span.attributes['b'] == 2
    
    def test_span_add_event(self):
        """测试添加事件"""
        span = Span(trace_id='test-trace', name='test_operation')
        
        span.add_event('event1', {'key': 'value'})
        
        assert len(span.events) == 1
        assert span.events[0]['name'] == 'event1'
        assert span.events[0]['attributes']['key'] == 'value'
    
    def test_span_record_exception(self):
        """测试记录异常"""
        span = Span(trace_id='test-trace', name='test_operation')
        
        try:
            raise ValueError('Test error')
        except Exception as e:
            span.record_exception(e)
        
        assert span.attributes['error.type'] == 'ValueError'
        assert span.attributes['error.message'] == 'Test error'
        assert span.status == SpanStatus.ERROR
    
    def test_span_context_manager(self):
        """测试 Span 上下文管理器"""
        with Span(trace_id='test-trace', name='test_operation') as span:
            assert span.start_time is not None
            assert get_current_span() == span
        
        # 退出后上下文应该清空
        assert get_current_span() is None
    
    def test_span_context_manager_exception(self):
        """测试 Span 上下文管理器异常处理"""
        try:
            with Span(trace_id='test-trace', name='test_operation') as span:
                raise ValueError('Test error')
        except ValueError:
            pass
        
        # Span 应该记录异常并标记为 ERROR
        assert span.status == SpanStatus.ERROR
        assert span.end_time is not None
    
    def test_span_to_dict(self):
        """测试转换为字典"""
        span = Span(trace_id='test-trace', name='test_operation')
        span.start()
        span.set_attribute('key', 'value')
        time.sleep(0.01)
        span.end(SpanStatus.OK)  # 明确设置状态为 OK
        
        data = span.to_dict()
        
        assert data['trace_id'] == 'test-trace'
        assert data['name'] == 'test_operation'
        assert data['attributes']['key'] == 'value'
        assert data['duration_ms'] >= 10
        assert data['status'] == 'OK'


class TestTracingSampler:
    """测试采样器"""
    
    def test_always_sample(self):
        """测试 100% 采样"""
        sampler = TracingSampler(sample_rate=1.0)
        
        for _ in range(100):
            assert sampler.should_sample() is True
    
    def test_never_sample(self):
        """测试 0% 采样"""
        sampler = TracingSampler(sample_rate=0.0)
        
        for _ in range(100):
            assert sampler.should_sample() is False
    
    def test_partial_sample(self):
        """测试部分采样"""
        sampler = TracingSampler(sample_rate=0.5, seed=42)
        
        sampled = sum(1 for _ in range(1000) if sampler.should_sample())
        
        # 应该在 40%-60% 之间
        assert 400 <= sampled <= 600
    
    def test_always_sample_paths(self):
        """测试始终采样路径"""
        sampler = TracingSampler(
            sample_rate=0.0,
            always_sample_paths=['/api/important', '/api/payment/*']
        )
        
        assert sampler.should_sample(path='/api/important') is True
        assert sampler.should_sample(path='/api/payment/process') is True
        assert sampler.should_sample(path='/api/other') is False
    
    def test_never_sample_paths(self):
        """测试永不采样路径"""
        sampler = TracingSampler(
            sample_rate=1.0,
            never_sample_paths=['/health', '/metrics', '/static/*']
        )
        
        assert sampler.should_sample(path='/health') is False
        assert sampler.should_sample(path='/metrics') is False
        assert sampler.should_sample(path='/static/app.js') is False
        assert sampler.should_sample(path='/api/chat') is True
    
    def test_consistent_sampling(self):
        """测试一致性采样"""
        sampler = TracingSampler(sample_rate=0.5)
        
        trace_id = 'fixed-trace-id'
        
        # 同一 trace_id 应该始终得到相同的结果
        results = [sampler.should_sample(trace_id=trace_id) for _ in range(100)]
        
        assert all(r == results[0] for r in results)
    
    def test_sampling_decision(self):
        """测试采样决策"""
        sampler = TracingSampler(sample_rate=1.0)
        
        decision = sampler.get_sampling_decision()
        
        assert decision == SamplingDecision.RECORD_AND_SAMPLE


class TestHTTPTracePropagator:
    """测试 HTTP 传播器"""
    
    def test_extract(self):
        """测试提取追踪上下文"""
        propagator = HTTPTracePropagator()
        
        headers = {
            'X-Trace-ID': 'test-trace-123',
            'X-Parent-Trace-ID': 'parent-456',
        }
        
        trace = propagator.extract(headers)
        
        assert trace.trace_id == 'test-trace-123'
        assert trace.parent_trace_id == 'parent-456'
    
    def test_inject(self):
        """测试注入追踪上下文"""
        propagator = HTTPTracePropagator()
        
        trace = TraceContext(
            trace_id='test-trace-123',
            parent_trace_id='parent-456',
        )
        
        headers = propagator.inject(trace)
        
        assert headers['X-Trace-ID'] == 'test-trace-123'
        assert headers['X-Parent-Trace-ID'] == 'parent-456'
    
    def test_fields(self):
        """测试字段列表"""
        propagator = HTTPTracePropagator()
        
        fields = propagator.fields()
        
        assert 'X-Trace-ID' in fields
        assert 'X-Parent-Trace-ID' in fields
        assert 'X-Trace-Flags' in fields


class TestTracingUtils:
    """测试工具函数"""
    
    def setup_method(self):
        """每个测试前清理上下文"""
        _tracing_context.set(None)
    
    def teardown_method(self):
        """每个测试后清理上下文"""
        _tracing_context.set(None)
    
    def test_start_span(self):
        """测试创建 Span"""
        span = start_span('test_operation', trace_id='test-trace')
        
        assert span.trace_id == 'test-trace'
        assert span.name == 'test_operation'
        assert span.start_time is not None
    
    def test_get_current_span(self):
        """测试获取当前 Span"""
        with start_span('test_operation', trace_id='test-trace') as span:
            current = get_current_span()
            assert current == span
            assert get_current_trace_id() == 'test-trace'
            assert get_current_span_id() == span.span_id
        
        assert get_current_span() is None
    
    def test_span_decorator(self):
        """测试 Span 装饰器"""
        span_holder = {}
        
        @span_decorator('decorated_function')
        def my_function():
            span_holder['span'] = get_current_span()
            return 'result'
        
        result = my_function()
        
        assert result == 'result'
        # 装饰器执行期间应该有 Span
        assert span_holder.get('span') is not None
        # 执行完后上下文应该清空
        assert get_current_span() is None
    
    def test_span_decorator_auto_name(self):
        """测试自动命名的装饰器"""
        @span_decorator()
        def auto_named_function():
            return 'result'
        
        result = auto_named_function()
        
        assert result == 'result'
    
    def test_span_decorator_exception(self):
        """测试装饰器异常处理"""
        @span_decorator('error_function')
        def error_function():
            raise ValueError('Test error')
        
        try:
            error_function()
        except ValueError:
            pass
        
        assert get_current_span() is None
    
    def test_create_log_record(self):
        """测试创建日志记录"""
        with start_span('test_operation', trace_id='test-trace') as span:
            record = create_log_record(
                level='INFO',
                message='Test message',
                logger='test.logger',
                user_id='123'
            )
            
            assert record.level == 'INFO'
            assert record.message == 'Test message'
            assert record.trace_id == 'test-trace'
            assert record.span_id == span.span_id
            assert record.attributes['user_id'] == '123'
    
    def test_trace_context_manager(self):
        """测试追踪上下文管理器"""
        # TraceContext.new_trace() 返回 TraceContext 对象
        trace = trace_context_manager()
        assert trace.trace_id is not None
        
        trace2 = trace_context_manager('custom-id')
        assert trace2.trace_id == 'custom-id'
    
    def test_span_context_manager(self):
        """测试 Span 上下文管理器"""
        with span_context_manager('test_span') as span:
            assert span.name == 'test_span'
            assert span.start_time is not None
        
        assert span.end_time is not None


class TestLogRecord:
    """测试 LogRecord"""
    
    def test_log_record_creation(self):
        """测试日志记录创建"""
        record = LogRecord(
            timestamp='2026-02-19T10:00:00Z',
            level='INFO',
            logger='test.logger',
            message='Test message',
            trace_id='trace-123',
            span_id='span-456',
            service='test_service',
            attributes={'key': 'value'}
        )
        
        assert record.level == 'INFO'
        assert record.trace_id == 'trace-123'
        assert record.attributes['key'] == 'value'
    
    def test_log_record_to_json(self):
        """测试转换为 JSON"""
        record = LogRecord(
            timestamp='2026-02-19T10:00:00Z',
            level='INFO',
            logger='test.logger',
            message='Test message',
            trace_id='trace-123',
            span_id='span-456',
        )
        
        json_str = record.to_json()
        
        assert 'trace_id' in json_str
        assert 'trace-123' in json_str
        assert 'span_id' in json_str


class TestConsoleSpanExporter:
    """测试控制台导出器"""
    
    def test_export(self, capsys):
        """测试导出到控制台"""
        exporter = ConsoleSpanExporter()
        
        span = Span(trace_id='test-trace', name='test_operation')
        span.start()
        time.sleep(0.01)
        span.end()
        
        exporter.export([span])
        
        captured = capsys.readouterr()
        assert 'test_operation' in captured.out
        assert 'test-trace' in captured.out


class TestTracingIntegration:
    """集成测试"""
    
    def setup_method(self):
        _tracing_context.set(None)
    
    def teardown_method(self):
        _tracing_context.set(None)
    
    def test_nested_spans(self):
        """测试嵌套 Span"""
        with start_span('parent', trace_id='test-trace') as parent:
            with start_span('child') as child:
                assert child.parent_span_id == parent.span_id
                assert child.trace_id == parent.trace_id
        
        assert get_current_span() is None
    
    def test_span_propagation(self):
        """测试 Span 传播"""
        trace_id = 'propagation-test'
        
        with start_span('operation1', trace_id=trace_id) as span1:
            trace_id_1 = get_current_trace_id()
            span_id_1 = get_current_span_id()
        
        # 上下文应该清空
        assert get_current_span() is None
        
        # 新的 Span 应该使用相同的 trace_id
        with start_span('operation2', trace_id=trace_id) as span2:
            assert span2.trace_id == trace_id
            assert span2.parent_span_id is None  # 新的独立 Span
    
    def test_concurrent_spans(self):
        """测试并发 Span"""
        import threading
        
        results = {}
        
        def worker(worker_id):
            with start_span(f'worker_{worker_id}', trace_id=f'trace_{worker_id}') as span:
                time.sleep(0.01)
                results[worker_id] = {
                    'trace_id': get_current_trace_id(),
                    'span_id': get_current_span_id(),
                }
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 每个线程应该有独立的上下文
        for i in range(5):
            assert results[i]['trace_id'] == f'trace_{i}'
            assert results[i]['span_id'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
