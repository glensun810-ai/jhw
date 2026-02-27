"""
死信队列 API 集成测试

测试死信队列管理 API 的完整功能。

作者：系统架构组
日期：2026-02-27
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any

# Flask 测试客户端
from flask import Flask

from wechat_backend.v2.api.dead_letter_api import dead_letter_bp, dlq
from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue


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
def app(temp_db):
    """创建 Flask 应用"""
    # 使用临时数据库创建新的 DLQ 实例
    import wechat_backend.v2.api.dead_letter_api as api_module
    api_module.dlq = DeadLetterQueue(db_path=temp_db)
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(dead_letter_bp)
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def sample_dead_letter(client) -> Dict[str, Any]:
    """添加示例死信并返回 ID"""
    response = client.post(
        '/api/v2/dead-letters/1/resolve',
        json={'handled_by': 'test', 'resolution_notes': 'test'},
    )
    
    # 先添加一个死信
    # 注意：这里需要通过服务层添加，API 没有直接添加的接口
    from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
    dlq_instance = DeadLetterQueue()
    
    dead_letter_id = dlq_instance.add_to_dead_letter(
        execution_id='test-exec-123',
        task_type='ai_call',
        error=TimeoutError('Test timeout'),
        task_context={'brand': '测试品牌'},
        priority=5,
    )
    
    return {'id': dead_letter_id}


# ==================== 列表 API 测试 ====================

class TestListAPI:
    """列表 API 测试"""
    
    def test_list_empty(self, client):
        """测试空列表"""
        response = client.get('/api/v2/dead-letters')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'data' in data
        assert 'pagination' in data
        assert len(data['data']) == 0
        assert data['pagination']['total'] == 0
    
    def test_list_with_data(self, client):
        """测试有数据的列表"""
        # 添加死信
        from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
        dlq_instance = DeadLetterQueue()
        
        for i in range(5):
            dlq_instance.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={'index': i},
            )
        
        response = client.get('/api/v2/dead-letters')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data['data']) == 5
        assert data['pagination']['total'] == 5
        assert data['pagination']['limit'] == 100
    
    def test_list_with_pagination(self, client):
        """测试分页"""
        # 添加 15 个死信
        from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
        dlq_instance = DeadLetterQueue()
        
        for i in range(15):
            dlq_instance.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
        
        # 第一页
        response = client.get('/api/v2/dead-letters?limit=10&offset=0')
        data = json.loads(response.data)
        assert len(data['data']) == 10
        assert data['pagination']['has_more'] is True
        
        # 第二页
        response = client.get('/api/v2/dead-letters?limit=10&offset=10')
        data = json.loads(response.data)
        assert len(data['data']) == 5
        assert data['pagination']['has_more'] is False
    
    def test_list_with_limit_validation(self, client):
        """测试 limit 验证"""
        response = client.get('/api/v2/dead-letters?limit=1001')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


# ==================== 详情 API 测试 ====================

class TestGetDetailAPI:
    """详情 API 测试"""
    
    def test_get_existing(self, client, sample_dead_letter):
        """测试获取存在的死信"""
        dead_letter_id = sample_dead_letter['id']
        
        response = client.get(f'/api/v2/dead-letters/{dead_letter_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['id'] == dead_letter_id
        assert data['execution_id'] == 'test-exec-123'
        assert data['task_type'] == 'ai_call'
    
    def test_get_nonexistent(self, client):
        """测试获取不存在的死信"""
        response = client.get('/api/v2/dead-letters/999999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


# ==================== 解决 API 测试 ====================

class TestResolveAPI:
    """解决 API 测试"""
    
    def test_resolve_success(self, client, sample_dead_letter):
        """测试成功解决"""
        dead_letter_id = sample_dead_letter['id']
        
        response = client.post(
            f'/api/v2/dead-letters/{dead_letter_id}/resolve',
            json={
                'handled_by': 'api_test',
                'resolution_notes': 'Fixed via API',
            },
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'resolved'
        
        # 验证状态已更新
        response = client.get(f'/api/v2/dead-letters/{dead_letter_id}')
        data = json.loads(response.data)
        assert data['status'] == 'resolved'
        assert data['handled_by'] == 'api_test'
    
    def test_resolve_with_empty_body(self, client, sample_dead_letter):
        """测试空请求体"""
        dead_letter_id = sample_dead_letter['id']
        
        response = client.post(
            f'/api/v2/dead-letters/{dead_letter_id}/resolve',
            json={},
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'resolved'


# ==================== 忽略 API 测试 ====================

class TestIgnoreAPI:
    """忽略 API 测试"""
    
    def test_ignore_success(self, client, sample_dead_letter):
        """测试成功忽略"""
        dead_letter_id = sample_dead_letter['id']
        
        response = client.post(
            f'/api/v2/dead-letters/{dead_letter_id}/ignore',
            json={
                'handled_by': 'api_test',
                'resolution_notes': 'Not critical',
            },
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ignored'


# ==================== 重试 API 测试 ====================

class TestRetryAPI:
    """重试 API 测试"""
    
    def test_retry_success(self, client, sample_dead_letter):
        """测试成功重试"""
        dead_letter_id = sample_dead_letter['id']
        
        response = client.post(
            f'/api/v2/dead-letters/{dead_letter_id}/retry',
            json={'handled_by': 'system'},
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'processing'
        
        # 验证状态已更新
        response = client.get(f'/api/v2/dead-letters/{dead_letter_id}')
        data = json.loads(response.data)
        assert data['status'] == 'processing'


# ==================== 统计 API 测试 ====================

class TestStatisticsAPI:
    """统计 API 测试"""
    
    def test_statistics_empty(self, client):
        """测试空队列统计"""
        response = client.get('/api/v2/dead-letters/statistics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total'] == 0
        assert 'by_status' in data
        assert 'by_task_type' in data
    
    def test_statistics_with_data(self, client):
        """测试有数据的统计"""
        # 添加不同状态的死信
        from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
        dlq_instance = DeadLetterQueue()
        
        for i in range(10):
            dead_letter_id = dlq_instance.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call' if i % 2 == 0 else 'analysis',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
            
            if i < 3:
                dlq_instance.mark_as_resolved(dead_letter_id)
        
        response = client.get('/api/v2/dead-letters/statistics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total'] == 10
        assert data['by_status']['pending'] == 7
        assert data['by_status']['resolved'] == 3
        assert data['last_24h'] == 10


# ==================== 清理 API 测试 ====================

class TestCleanupAPI:
    """清理 API 测试"""
    
    def test_cleanup_success(self, client, sample_dead_letter):
        """测试成功清理"""
        dead_letter_id = sample_dead_letter['id']
        
        # 先标记为已解决
        client.post(
            f'/api/v2/dead-letters/{dead_letter_id}/resolve',
            json={},
        )
        
        # 清理
        response = client.post(
            '/api/v2/dead-letters/cleanup',
            json={'days': 30},
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'deleted' in data
        assert 'message' in data
    
    def test_cleanup_invalid_days(self, client):
        """测试无效的 days 参数"""
        response = client.post(
            '/api/v2/dead-letters/cleanup',
            json={'days': 400},
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
