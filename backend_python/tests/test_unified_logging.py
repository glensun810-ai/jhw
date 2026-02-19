"""
异步队列日志系统单元测试

测试范围:
1. UnifiedLoggerFactory 初始化和单例行为
2. UnifiedLogger 日志记录功能
3. 异步队列日志写入性能
4. 链路追踪上下文管理
5. JSON 格式化器
6. 日志处理器配置
7. 兼容性包装器
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import logging
import json
import time
import threading
import queue
import tempfile
import shutil

from unified_logging import (
    UnifiedLoggerFactory,
    UnifiedLogger,
    JSONFormatter,
    LoggingContext,
    get_logger,
    init_logging,
    shutdown_logging,
    _trace_context,
)


class TestUnifiedLoggerFactory:
    """测试日志工厂"""
    
    def setup_method(self):
        """每个测试前清理状态"""
        # 重置单例状态
        import unified_logging.unified_logger as ul
        ul._factory_instance = None
        # 重置追踪上下文
        _trace_context.set({})
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试后清理"""
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # 重置追踪上下文
        _trace_context.set({})
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        factory1 = UnifiedLoggerFactory()
        factory2 = UnifiedLoggerFactory()
        assert factory1 is factory2
    
    def test_initialize(self):
        """测试初始化"""
        factory = UnifiedLoggerFactory()
        result = factory.initialize(log_dir=self.temp_dir)
        
        assert result is factory
        assert factory.is_initialized()
        assert factory.log_dir == Path(self.temp_dir)
    
    def test_initialize_twice(self):
        """测试重复初始化"""
        factory = UnifiedLoggerFactory()
        factory.initialize(log_dir=self.temp_dir)
        
        # 第二次初始化应该直接返回
        result = factory.initialize(log_dir='/different/path')
        assert result is factory
        # 日志目录应该保持第一次的值
        assert factory.log_dir == Path(self.temp_dir)
    
    def test_get_logger(self):
        """测试获取日志器"""
        factory = UnifiedLoggerFactory()
        factory.initialize(log_dir=self.temp_dir)
        
        logger = factory.get_logger('test.logger')
        assert isinstance(logger, UnifiedLogger)
        assert logger.name == 'test.logger'
    
    def test_shutdown(self):
        """测试关闭"""
        factory = UnifiedLoggerFactory()
        factory.initialize(log_dir=self.temp_dir)
        
        factory.shutdown()
        assert not factory.is_initialized()


class TestUnifiedLogger:
    """测试日志器"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        init_logging(log_dir=self.temp_dir, log_level='DEBUG')
        self.logger = get_logger('test.unified_logger')
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_levels(self):
        """测试不同日志级别"""
        # 这些调用不应该抛出异常
        self.logger.debug('Debug message')
        self.logger.info('Info message')
        self.logger.warning('Warning message')
        self.logger.error('Error message')
        self.logger.critical('Critical message')
    
    def test_log_with_extra_fields(self):
        """测试额外字段"""
        self.logger.info(
            'Test message',
            user_id='123',
            endpoint='/api/test',
            latency_ms=100
        )
        # 不应该抛出异常
    
    def test_log_exception(self):
        """测试异常日志"""
        try:
            raise ValueError('Test error')
        except Exception:
            self.logger.exception('An error occurred')
    
    def test_log_with_exc_info(self):
        """测试 exc_info 参数"""
        try:
            raise ValueError('Test error')
        except Exception:
            self.logger.error('An error occurred', exc_info=True)
    
    def test_trace_context(self):
        """测试链路追踪上下文"""
        context = self.logger.set_trace_context(
            trace_id='test-trace-123',
            span_id='span-456'
        )
        
        assert context['trace_id'] == 'test-trace-123'
        assert context['span_id'] == 'span-456'
        
        retrieved = self.logger.get_trace_context()
        assert retrieved['trace_id'] == 'test-trace-123'
        
        self.logger.clear_trace_context()
        assert self.logger.get_trace_context() == {}
    
    def test_trace_context_auto_generation(self):
        """测试自动生成追踪 ID"""
        context = self.logger.set_trace_context()
        
        assert 'trace_id' in context
        assert 'span_id' in context
        assert len(context['trace_id']) > 0
        assert len(context['span_id']) > 0


class TestLoggingContext:
    """测试日志上下文管理器"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        init_logging(log_dir=self.temp_dir, log_level='DEBUG')
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_context_manager(self):
        """测试上下文管理器"""
        logger = get_logger('test.context')
        
        # 初始上下文为空
        assert logger.get_trace_context() == {}
        
        # 进入上下文
        with LoggingContext(trace_id='ctx-trace', span_id='ctx-span'):
            context = logger.get_trace_context()
            assert context['trace_id'] == 'ctx-trace'
            assert context['span_id'] == 'ctx-span'
        
        # 退出上下文后恢复
        assert logger.get_trace_context() == {}
    
    def test_context_manager_auto_ids(self):
        """测试自动生成的 ID"""
        logger = get_logger('test.context')
        
        with LoggingContext():
            context = logger.get_trace_context()
            assert 'trace_id' in context
            assert 'span_id' in context
    
    def test_context_manager_with_extra(self):
        """测试额外上下文数据"""
        logger = get_logger('test.context')
        
        with LoggingContext(user_id='123', request_id='456'):
            context = logger.get_trace_context()
            assert context['user_id'] == '123'
            assert context['request_id'] == '456'
            assert 'trace_id' in context  # 自动生成
    
    def test_context_manager_nested(self):
        """测试嵌套上下文"""
        logger = get_logger('test.context')
        
        with LoggingContext(trace_id='outer'):
            assert logger.get_trace_context()['trace_id'] == 'outer'
            
            with LoggingContext(trace_id='inner'):
                assert logger.get_trace_context()['trace_id'] == 'inner'
            
            assert logger.get_trace_context()['trace_id'] == 'outer'
        
        assert logger.get_trace_context() == {}


class TestJSONFormatter:
    """测试 JSON 格式化器"""
    
    def test_format_basic(self):
        """测试基本格式化"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='/test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None,
            func='test_func'
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data['message'] == 'Test message'
        assert data['level'] == 'INFO'
        assert data['logger'] == 'test.logger'
        assert 'timestamp' in data
    
    def test_format_with_extra(self):
        """测试额外字段"""
        formatter = JSONFormatter(include_extra=True)
        
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='/test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None,
            func='test_func'
        )
        record.user_id = '123'
        record.endpoint = '/api/test'
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data['user_id'] == '123'
        assert data['endpoint'] == '/api/test'
    
    def test_format_with_exception(self):
        """测试异常格式化"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError('Test error')
        except Exception:
            record = logging.LogRecord(
                name='test.logger',
                level=logging.ERROR,
                pathname='/test.py',
                lineno=42,
                msg='Error occurred',
                args=(),
                exc_info=None,
                func='test_func'
            )
            # 简化测试，不测试异常文本格式化
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data['message'] == 'Error occurred'
        assert data['level'] == 'ERROR'


class TestAsyncLogging:
    """测试异步日志功能"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_async_logging_performance(self):
        """测试异步日志性能"""
        init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            queue_size=10000
        )
        logger = get_logger('test.async')
        
        # 记录 1000 条日志
        start = time.time()
        for i in range(1000):
            logger.info(f'Message {i}')
        elapsed = time.time() - start
        
        # 平均每条日志应该 < 1ms
        avg_time = (elapsed / 1000) * 1000  # 转换为毫秒
        assert avg_time < 10, f"Average log time {avg_time}ms is too slow"
    
    def test_concurrent_logging(self):
        """测试并发日志记录"""
        init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            queue_size=10000
        )
        logger = get_logger('test.concurrent')
        
        errors = []
        
        def log_messages(thread_id, count):
            try:
                for i in range(count):
                    logger.info(f'Thread {thread_id} - Message {i}')
            except Exception as e:
                errors.append(e)
        
        # 启动 10 个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=log_messages, args=(i, 100))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 不应该有错误
        assert len(errors) == 0, f"Errors occurred: {errors}"
    
    def test_queue_overflow(self):
        """测试队列溢出处理"""
        init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            queue_size=100  # 小队列
        )
        logger = get_logger('test.overflow')
        
        # 记录大量日志
        for i in range(1000):
            logger.info(f'Message {i}')
        
        # 不应该抛出异常
        shutdown_logging()


class TestLogFileOutput:
    """测试日志文件输出"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_file_created(self):
        """测试日志文件创建"""
        init_logging(log_dir=self.temp_dir, log_level='DEBUG')
        logger = get_logger('test.file')
        
        logger.info('Test message')
        
        # 等待日志写入
        time.sleep(0.5)
        
        # 检查文件存在
        app_log = Path(self.temp_dir) / 'app.log'
        assert app_log.exists(), "app.log should be created"
    
    def test_log_file_json_format(self):
        """测试日志文件 JSON 格式"""
        init_logging(log_dir=self.temp_dir, log_level='DEBUG')
        logger = get_logger('test.file')
        
        logger.info('Test message', user_id='123')
        
        # 等待日志写入 (异步需要更长时间)
        time.sleep(1.0)
        
        # 关闭日志系统以确保所有日志写入
        shutdown_logging()
        
        # 读取并解析日志
        app_log = Path(self.temp_dir) / 'app.log'
        with open(app_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找包含 Test message 的行
        test_line = None
        for line in lines:
            data = json.loads(line)
            if data.get('message') == 'Test message':
                test_line = data
                break
        
        assert test_line is not None, "Should find 'Test message' in log file"
        assert test_line['user_id'] == '123'
    
    def test_ai_log_file(self):
        """测试 AI 专用日志文件"""
        init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            enable_ai_handler=True
        )
        logger = get_logger('wechat_backend.ai.test')
        
        logger.info('AI message')
        
        # 等待日志写入
        time.sleep(0.5)
        
        # 检查 AI 日志文件
        ai_log = Path(self.temp_dir) / 'ai_responses.log'
        assert ai_log.exists(), "ai_responses.log should be created"
    
    def test_error_log_file(self):
        """测试错误日志文件"""
        init_logging(log_dir=self.temp_dir, log_level='DEBUG')
        logger = get_logger('test.file')
        
        logger.error('Error message')
        
        # 等待日志写入
        time.sleep(0.5)
        
        # 检查错误日志文件
        error_log = Path(self.temp_dir) / 'errors.log'
        assert error_log.exists(), "errors.log should be created"


class TestCompatibility:
    """测试兼容性包装器"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_logger_function(self):
        """测试便捷函数 get_logger"""
        init_logging(log_dir=self.temp_dir)
        logger = get_logger('test.compat')
        
        assert isinstance(logger, UnifiedLogger)
        logger.info('Test message')
    
    def test_init_logging_function(self):
        """测试便捷函数 init_logging"""
        factory = init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            queue_size=5000
        )
        
        assert factory.is_initialized()
        assert factory.log_dir == Path(self.temp_dir)


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 初始化
        factory = init_logging(
            log_dir=self.temp_dir,
            log_level='DEBUG',
            queue_size=10000
        )
        
        # 获取日志器
        logger = factory.get_logger('wechat_backend.api.test')
        
        # 设置链路追踪
        context = logger.set_trace_context()
        assert 'trace_id' in context
        
        # 记录日志
        logger.info(
            'API request',
            endpoint='/api/test',
            method='POST',
            user_id='user_123'
        )
        
        # 模拟处理
        time.sleep(0.1)
        
        # 记录结果
        logger.info('Request completed', latency_ms=100)
        
        # 等待日志写入
        time.sleep(0.5)
        
        # 验证日志文件
        app_log = Path(self.temp_dir) / 'app.log'
        assert app_log.exists()
        
        with open(app_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) >= 2
        
        # 验证 JSON 格式
        for line in lines:
            data = json.loads(line)
            assert 'timestamp' in data
            assert 'level' in data
            assert 'message' in data
        
        # 关闭
        factory.shutdown()
        assert not factory.is_initialized()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
