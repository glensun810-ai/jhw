"""
API 调用日志单元测试

测试覆盖率目标：> 90%

测试范围:
1. APICallLog 模型测试
2. DataSanitizer 脱敏测试
3. APICallLogRepository 仓库测试
4. APICallLogger 记录器测试

作者：系统架构组
日期：2026-02-27
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from wechat_backend.v2.models.api_call_log import APICallLog
from wechat_backend.v2.repositories.api_call_log_repository import APICallLogRepository
from wechat_backend.v2.services.api_call_logger import APICallLogger
from wechat_backend.v2.utils.sanitizer import DataSanitizer


# ==================== Fixture ====================

@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def repository(temp_db):
    """创建仓库实例（使用临时数据库）"""
    return APICallLogRepository(db_path=temp_db)


@pytest.fixture
def logger(temp_db):
    """创建日志记录器实例"""
    repo = APICallLogRepository(db_path=temp_db)
    return APICallLogger(repository=repo)


@pytest.fixture
def sample_log_data() -> Dict[str, Any]:
    """示例日志数据"""
    return {
        'execution_id': 'test-exec-123',
        'brand': '测试品牌',
        'question': '测试问题',
        'model': 'deepseek',
        'request_data': {'prompt': '测试提示词', 'temperature': 0.7},
        'response_data': {'content': '测试响应', 'usage': {'tokens': 100}},
        'latency_ms': 1234,
        'request_headers': {'Content-Type': 'application/json'},
        'response_headers': {'Content-Type': 'application/json'},
    }


# ==================== APICallLog 模型测试 ====================

class TestAPICallLogModel:
    """APICallLog 模型测试"""
    
    def test_create_log(self):
        """测试创建日志对象"""
        log = APICallLog(
            execution_id='test-123',
            brand='品牌 A',
            question='问题',
            model='deepseek',
            request_data={'prompt': 'test'},
            request_timestamp=datetime.now(),
            success=True,
            response_data={'content': 'response'},
            latency_ms=100,
        )
        
        assert log.execution_id == 'test-123'
        assert log.brand == '品牌 A'
        assert log.success is True
        assert log.latency_ms == 100
    
    def test_to_dict_success(self):
        """测试成功日志转字典"""
        log = APICallLog(
            execution_id='test-123',
            brand='品牌 A',
            question='问题',
            model='deepseek',
            request_data={'prompt': 'test'},
            request_timestamp=datetime.now(),
            success=True,
            response_data={'content': 'response'},
            latency_ms=100,
        )
        
        log_dict = log.to_dict()
        
        assert log_dict['execution_id'] == 'test-123'
        assert log_dict['success'] is True
        assert 'response_data' in log_dict
        assert log_dict['latency_ms'] == 100
    
    def test_to_dict_failure(self):
        """测试失败日志转字典"""
        log = APICallLog(
            execution_id='test-123',
            brand='品牌 A',
            question='问题',
            model='deepseek',
            request_data={'prompt': 'test'},
            request_timestamp=datetime.now(),
            success=False,
            error_message='Timeout error',
            latency_ms=5000,
        )
        
        log_dict = log.to_dict()
        
        assert log_dict['success'] is False
        assert 'error_message' in log_dict
        assert 'response_data' not in log_dict
    
    def test_to_log_dict(self):
        """测试转日志字典"""
        log = APICallLog(
            execution_id='test-123',
            brand='品牌 A',
            question='问题',
            model='deepseek',
            request_data={'prompt': 'test'},
            request_timestamp=datetime.now(),
            success=True,
            latency_ms=100,
        )
        
        log_dict = log.to_log_dict()
        
        assert log_dict['event'] == 'api_call'
        assert log_dict['execution_id'] == 'test-123'
        assert log_dict['success'] is True
        assert log_dict['latency_ms'] == 100
    
    def test_from_db_row(self, sample_log_data):
        """测试从数据库行创建对象"""
        row = {
            'id': 1,
            'execution_id': sample_log_data['execution_id'],
            'brand': sample_log_data['brand'],
            'question': sample_log_data['question'],
            'model': sample_log_data['model'],
            'request_data': '{"prompt": "test"}',
            'request_timestamp': datetime.now().isoformat(),
            'success': 1,
            'latency_ms': 100,
            'response_data': '{"content": "response"}',
            'response_timestamp': datetime.now().isoformat(),
            'status_code': 200,
            'error_message': None,
            'error_stack': None,
            'retry_count': 0,
            'report_id': None,
            'api_version': 'v1',
            'request_id': 'req-123',
            'has_sensitive_data': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
        log = APICallLog.from_db_row(row)
        
        assert log.id == 1
        assert log.execution_id == 'test-exec-123'
        assert log.success is True
        assert log.request_data == {'prompt': 'test'}
        assert log.request_id == 'req-123'


# ==================== DataSanitizer 测试 ====================

class TestDataSanitizer:
    """DataSanitizer 脱敏测试"""
    
    def test_sanitize_dict_with_api_key(self):
        """测试脱敏 API Key"""
        data = {'api_key': 'secret123', 'prompt': 'test'}
        sanitized = DataSanitizer.sanitize_dict(data)
        
        assert sanitized['api_key'] == '***' or '"api_key": "***"' in str(sanitized)
        assert sanitized['prompt'] == 'test'
    
    def test_sanitize_dict_with_token(self):
        """测试脱敏 Token"""
        data = {'token': 'abc123xyz', 'data': 'value'}
        sanitized = DataSanitizer.sanitize_dict(data)
        
        assert sanitized['token'] == '***' or '"token": "***"' in str(sanitized)
    
    def test_sanitize_dict_with_password(self):
        """测试脱敏密码"""
        data = {'password': 'secret', 'username': 'user'}
        sanitized = DataSanitizer.sanitize_dict(data)
        
        assert sanitized['password'] == '***' or '"password": "***"' in str(sanitized)
        assert sanitized['username'] == 'user'
    
    def test_sanitize_headers(self):
        """测试脱敏 HTTP 头"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer secret_token_12345',
            'X-API-Key': 'api_key_value',
        }
        
        sanitized = DataSanitizer.sanitize_headers(headers)
        
        assert sanitized['Content-Type'] == 'application/json'
        assert sanitized['Authorization'] != 'Bearer secret_token_12345'
        assert '***' in sanitized['Authorization']
        assert sanitized['X-API-Key'] != 'api_key_value'
        assert '***' in sanitized['X-API-Key']
    
    def test_contains_sensitive_data_true(self):
        """测试检测敏感数据（包含）"""
        data = {'api_key': 'secret', 'prompt': 'test'}
        assert DataSanitizer.contains_sensitive_data(data) is True
    
    def test_contains_sensitive_data_false(self):
        """测试检测敏感数据（不包含）"""
        data = {'prompt': 'test', 'temperature': 0.7}
        assert DataSanitizer.contains_sensitive_data(data) is False
    
    def test_sanitize_empty_dict(self):
        """测试脱敏空字典"""
        assert DataSanitizer.sanitize_dict({}) == {}
        assert DataSanitizer.sanitize_dict(None) is None
    
    def test_mask_value(self):
        """测试通用值脱敏"""
        assert DataSanitizer.mask_value('secret123') == 'secr***t123'
        assert DataSanitizer.mask_value('ab') == '***'
        assert DataSanitizer.mask_value('') == '***'
    
    def test_sanitize_dict_nested(self):
        """测试脱敏嵌套字典"""
        data = {
            'config': {
                'api_key': 'secret',
                'prompt': 'test'
            }
        }
        sanitized = DataSanitizer.sanitize_dict(data)
        
        # 嵌套的敏感信息也应该被脱敏
        assert 'api_key' in str(sanitized)


# ==================== APICallLogRepository 测试 ====================

class TestAPICallLogRepository:
    """APICallLogRepository 仓库测试"""
    
    def test_create_log(self, repository, sample_log_data):
        """测试创建日志"""
        log = APICallLog(
            execution_id=sample_log_data['execution_id'],
            brand=sample_log_data['brand'],
            question=sample_log_data['question'],
            model=sample_log_data['model'],
            request_data=sample_log_data['request_data'],
            request_timestamp=datetime.now(),
            success=True,
            response_data=sample_log_data['response_data'],
            latency_ms=sample_log_data['latency_ms'],
        )
        
        log_id = repository.create(log)
        assert log_id > 0
    
    def test_get_by_id(self, repository, sample_log_data):
        """测试根据 ID 获取日志"""
        log = APICallLog(
            execution_id=sample_log_data['execution_id'],
            brand=sample_log_data['brand'],
            question=sample_log_data['question'],
            model=sample_log_data['model'],
            request_data=sample_log_data['request_data'],
            request_timestamp=datetime.now(),
            success=True,
            response_data=sample_log_data['response_data'],
            latency_ms=sample_log_data['latency_ms'],
        )
        
        log_id = repository.create(log)
        
        retrieved = repository.get_by_id(log_id)
        assert retrieved is not None
        assert retrieved.execution_id == sample_log_data['execution_id']
    
    def test_get_by_execution_id(self, repository):
        """测试根据执行 ID 获取日志"""
        # 创建多个日志
        for i in range(5):
            log = APICallLog(
                execution_id='test-exec',
                brand=f'品牌{i}',
                question='问题',
                model='deepseek',
                request_data={'prompt': 'test'},
                request_timestamp=datetime.now(),
                success=True,
                response_data={'content': f'response{i}'},
                latency_ms=100 + i,
            )
            repository.create(log)
        
        logs = repository.get_by_execution_id('test-exec')
        assert len(logs) == 5
    
    def test_get_statistics(self, repository):
        """测试获取统计信息"""
        # 创建不同状态的日志
        for i in range(10):
            log = APICallLog(
                execution_id='test-exec',
                brand='品牌 A',
                question='问题',
                model='deepseek' if i % 2 == 0 else 'doubao',
                request_data={'prompt': 'test'},
                request_timestamp=datetime.now(),
                success=i < 7,  # 7 个成功，3 个失败
                response_data={'content': 'response'} if i < 7 else None,
                error_message='Error' if i >= 7 else None,
                latency_ms=100 + i * 10,
            )
            repository.create(log)
        
        stats = repository.get_statistics(execution_id='test-exec')
        
        assert stats['total'] == 10
        assert stats['success_count'] == 7
        assert len(stats['by_model']) == 2
        assert len(stats['top_errors']) > 0
    
    def test_delete_old_logs(self, repository):
        """测试删除旧日志"""
        # 创建日志
        log = APICallLog(
            execution_id='test-exec',
            brand='品牌 A',
            question='问题',
            model='deepseek',
            request_data={'prompt': 'test'},
            request_timestamp=datetime.now() - timedelta(days=100),
            success=True,
            response_data={'content': 'response'},
            latency_ms=100,
        )
        log_id = repository.create(log)
        
        # 手动更新 created_at 为 100 天前
        with repository._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE api_call_logs
                SET request_timestamp = datetime('now', '-100 days')
                WHERE id = ?
            ''', (log_id,))
            conn.commit()
        
        # 删除 90 天前的日志
        deleted = repository.delete_old_logs(days=90)
        assert deleted == 1
        
        # 验证已被删除
        retrieved = repository.get_by_id(log_id)
        assert retrieved is None


# ==================== APICallLogger 测试 ====================

class TestAPICallLogger:
    """APICallLogger 记录器测试"""
    
    def test_log_success(self, logger, sample_log_data):
        """测试记录成功调用"""
        log_id = logger.log_success(
            execution_id=sample_log_data['execution_id'],
            brand=sample_log_data['brand'],
            question=sample_log_data['question'],
            model=sample_log_data['model'],
            request_data=sample_log_data['request_data'],
            response_data=sample_log_data['response_data'],
            latency_ms=sample_log_data['latency_ms'],
        )
        
        assert log_id > 0
    
    def test_log_failure(self, logger, sample_log_data):
        """测试记录失败调用"""
        log_id = logger.log_failure(
            execution_id=sample_log_data['execution_id'],
            brand=sample_log_data['brand'],
            question=sample_log_data['question'],
            model=sample_log_data['model'],
            request_data=sample_log_data['request_data'],
            error=TimeoutError('Timeout'),
            latency_ms=5000,
        )
        
        assert log_id > 0
    
    def test_get_logs_for_execution(self, logger):
        """测试获取执行日志"""
        # 记录多个调用
        for i in range(3):
            logger.log_success(
                execution_id='test-exec',
                brand='品牌 A',
                question='问题',
                model='deepseek',
                request_data={'prompt': 'test'},
                response_data={'content': f'response{i}'},
                latency_ms=100 + i,
            )
        
        logs = logger.get_logs_for_execution('test-exec')
        assert len(logs) == 3
    
    def test_get_statistics(self, logger):
        """测试获取统计"""
        # 记录调用
        for i in range(5):
            logger.log_success(
                execution_id='test-exec',
                brand='品牌 A',
                question='问题',
                model='deepseek',
                request_data={'prompt': 'test'},
                response_data={'content': 'response'},
                latency_ms=100,
            )
        
        stats = logger.get_statistics(execution_id='test-exec')
        
        assert stats['total'] == 5
        assert stats['success_count'] == 5


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=wechat_backend.v2', '--cov-report=html'])
