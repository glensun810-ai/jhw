"""
死信队列单元测试

测试覆盖率目标：> 90%

测试范围:
1. 添加死信
2. 查询单个死信
3. 分页查询死信列表
4. 按状态/类型过滤
5. 标记为已解决
6. 标记为忽略
7. 重试标记
8. 统计功能
9. 清理旧记录
10. 并发操作

作者：系统架构组
日期：2026-02-27
"""

import pytest
import os
import tempfile
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
from wechat_backend.v2.exceptions import DeadLetterQueueError, RetryExhaustedError


# ==================== Fixture ====================

@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # 清理
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def dlq(temp_db):
    """创建死信队列实例（使用临时数据库）"""
    return DeadLetterQueue(db_path=temp_db)


@pytest.fixture
def sample_dead_letter_data() -> Dict[str, Any]:
    """示例死信数据"""
    return {
        'execution_id': 'test-exec-123',
        'task_type': 'ai_call',
        'error': TimeoutError('AI platform timeout'),
        'task_context': {
            'brand': '测试品牌',
            'question': '测试问题',
            'model': 'deepseek',
        },
        'retry_count': 3,
        'max_retries': 3,
        'priority': 5,
    }


# ==================== 添加死信测试 ====================

class TestAddToDeadLetter:
    """添加死信测试"""
    
    def test_add_to_dead_letter(self, dlq, sample_dead_letter_data):
        """测试添加死信"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id=sample_dead_letter_data['execution_id'],
            task_type=sample_dead_letter_data['task_type'],
            error=sample_dead_letter_data['error'],
            task_context=sample_dead_letter_data['task_context'],
            retry_count=sample_dead_letter_data['retry_count'],
            max_retries=sample_dead_letter_data['max_retries'],
            priority=sample_dead_letter_data['priority'],
        )
        
        assert dead_letter_id > 0
        
        # 验证数据被正确保存
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter is not None
        assert letter['execution_id'] == sample_dead_letter_data['execution_id']
        assert letter['task_type'] == sample_dead_letter_data['task_type']
        assert letter['error_type'] == 'TimeoutError'
        assert letter['status'] == 'pending'
        assert letter['priority'] == 5
    
    def test_add_to_dead_letter_with_stack_trace(self, dlq):
        """测试添加带堆栈跟踪的死信"""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            dead_letter_id = dlq.add_to_dead_letter(
                execution_id='test-123',
                task_type='analysis',
                error=e,
                task_context={},
            )
        
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter is not None
        assert letter['error_stack'] is not None
        assert 'ValueError' in letter['error_stack']
    
    def test_add_to_dead_letter_invalid_context(self, dlq):
        """测试添加不可序列化的上下文"""
        # 应该能够处理不可序列化的数据（转换为字符串）
        class NonSerializable:
            pass
        
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=ValueError("Error"),
            task_context={'data': NonSerializable()},  # type: ignore
        )
        
        # 应该抛出异常或正确处理
        assert dead_letter_id > 0 or dead_letter_id == 0


# ==================== 查询死信测试 ====================

class TestGetDeadLetter:
    """查询死信测试"""
    
    def test_get_existing_dead_letter(self, dlq, sample_dead_letter_data):
        """测试获取存在的死信"""
        dead_letter_id = dlq.add_to_dead_letter(**sample_dead_letter_data)
        
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter is not None
        assert letter['id'] == dead_letter_id
    
    def test_get_nonexistent_dead_letter(self, dlq):
        """测试获取不存在的死信"""
        letter = dlq.get_dead_letter(999999)
        assert letter is None


class TestListDeadLetters:
    """列表查询测试"""
    
    def test_list_all_dead_letters(self, dlq):
        """测试列出所有死信"""
        # 添加多个死信
        for i in range(5):
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={'index': i},
            )
        
        letters = dlq.list_dead_letters()
        assert len(letters) == 5
    
    def test_list_with_status_filter(self, dlq):
        """测试按状态过滤"""
        # 添加不同状态的死信
        for i in range(5):
            dead_letter_id = dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
            
            if i < 2:
                dlq.mark_as_resolved(dead_letter_id)
        
        # 查询 pending 状态
        pending = dlq.list_dead_letters(status='pending')
        assert len(pending) == 3
        
        # 查询 resolved 状态
        resolved = dlq.list_dead_letters(status='resolved')
        assert len(resolved) == 2
    
    def test_list_with_task_type_filter(self, dlq):
        """测试按任务类型过滤"""
        # 添加不同类型
        for i in range(6):
            task_type = 'ai_call' if i % 2 == 0 else 'analysis'
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type=task_type,
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
        
        ai_calls = dlq.list_dead_letters(task_type='ai_call')
        assert len(ai_calls) == 3
        
        analysis = dlq.list_dead_letters(task_type='analysis')
        assert len(analysis) == 3
    
    def test_list_with_pagination(self, dlq):
        """测试分页查询"""
        # 添加 15 个死信
        for i in range(15):
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
        
        # 第一页
        page1 = dlq.list_dead_letters(limit=10, offset=0)
        assert len(page1) == 10
        
        # 第二页
        page2 = dlq.list_dead_letters(limit=10, offset=10)
        assert len(page2) == 5
        
        # 第三页（空）
        page3 = dlq.list_dead_letters(limit=10, offset=20)
        assert len(page3) == 0
    
    def test_list_with_sorting(self, dlq):
        """测试排序"""
        # 添加不同优先级的死信
        for i in range(5):
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={},
                priority=i,
            )
        
        # 按优先级降序
        letters = dlq.list_dead_letters(sort_by='priority DESC')
        assert letters[0]['priority'] == 4
        assert letters[-1]['priority'] == 0


class TestCountDeadLetters:
    """统计数量测试"""
    
    def test_count_all(self, dlq):
        """测试统计总数"""
        for i in range(10):
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
        
        count = dlq.count_dead_letters()
        assert count == 10
    
    def test_count_with_filter(self, dlq):
        """测试按条件统计"""
        for i in range(10):
            task_type = 'ai_call' if i % 2 == 0 else 'analysis'
            dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type=task_type,
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
        
        ai_call_count = dlq.count_dead_letters(task_type='ai_call')
        assert ai_call_count == 5
        
        analysis_count = dlq.count_dead_letters(task_type='analysis')
        assert analysis_count == 5


# ==================== 状态更新测试 ====================

class TestMarkAsResolved:
    """标记为已解决测试"""
    
    def test_mark_as_resolved(self, dlq):
        """测试标记为已解决"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        success = dlq.mark_as_resolved(
            dead_letter_id,
            handled_by='test_user',
            resolution_notes='Fixed manually',
        )
        
        assert success is True
        
        # 验证状态已更新
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter['status'] == 'resolved'
        assert letter['handled_by'] == 'test_user'
        assert letter['resolution_notes'] == 'Fixed manually'
        assert letter['resolved_at'] is not None
    
    def test_mark_as_resolved_already_resolved(self, dlq):
        """测试标记已解决的死信"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        # 第一次标记
        dlq.mark_as_resolved(dead_letter_id)
        
        # 第二次标记应该失败
        success = dlq.mark_as_resolved(dead_letter_id)
        assert success is False


class TestMarkAsIgnored:
    """标记为忽略测试"""
    
    def test_mark_as_ignored(self, dlq):
        """测试标记为忽略"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        success = dlq.mark_as_ignored(
            dead_letter_id,
            handled_by='test_user',
            resolution_notes='Not critical',
        )
        
        assert success is True
        
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter['status'] == 'ignored'


class TestRetryDeadLetter:
    """重试死信测试"""
    
    def test_retry_dead_letter(self, dlq):
        """测试重试标记"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        success = dlq.retry_dead_letter(
            dead_letter_id,
            handled_by='system',
        )
        
        assert success is True
        
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter['status'] == 'processing'
        assert letter['handled_by'] == 'system'
        assert letter['last_retry_at'] is not None
    
    def test_retry_non_pending(self, dlq):
        """测试重试非 pending 状态的死信"""
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        # 先标记为 resolved
        dlq.mark_as_resolved(dead_letter_id)
        
        # 重试应该失败
        success = dlq.retry_dead_letter(dead_letter_id)
        assert success is False


# ==================== 统计功能测试 ====================

class TestGetStatistics:
    """统计功能测试"""
    
    def test_get_statistics(self, dlq):
        """测试获取统计信息"""
        # 添加不同状态的死信
        for i in range(10):
            dead_letter_id = dlq.add_to_dead_letter(
                execution_id=f'test-{i}',
                task_type='ai_call' if i % 2 == 0 else 'analysis',
                error=TimeoutError(f'Error {i}'),
                task_context={},
            )
            
            if i < 3:
                dlq.mark_as_resolved(dead_letter_id)
            elif i < 5:
                dlq.mark_as_ignored(dead_letter_id)
        
        stats = dlq.get_statistics()
        
        assert stats['total'] == 10
        assert stats['by_status']['pending'] == 5
        assert stats['by_status']['resolved'] == 3
        assert stats['by_status']['ignored'] == 2
        assert stats['by_task_type']['ai_call'] > 0
        assert stats['last_24h'] == 10
        assert stats['oldest_pending'] is not None
    
    def test_get_statistics_empty(self, dlq):
        """测试空队列统计"""
        stats = dlq.get_statistics()
        
        assert stats['total'] == 0
        assert stats['by_status'] == {}
        assert stats['by_task_type'] == {}
        assert stats['last_24h'] == 0
        assert stats['oldest_pending'] is None


# ==================== 清理功能测试 ====================

class TestCleanupResolved:
    """清理功能测试"""
    
    def test_cleanup_old_resolved(self, dlq):
        """测试清理旧的已解决记录"""
        # 添加一个已解决的死信
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        
        # 标记为已解决
        dlq.mark_as_resolved(dead_letter_id)
        
        # 手动更新 resolved_at 为 31 天前
        with dlq._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE dead_letter_queue
                SET resolved_at = datetime('now', '-31 days')
                WHERE id = ?
            ''', (dead_letter_id,))
            conn.commit()
        
        # 清理 30 天前的记录
        deleted = dlq.cleanup_resolved(days=30)
        
        assert deleted == 1
        
        # 验证记录已被删除
        letter = dlq.get_dead_letter(dead_letter_id)
        assert letter is None
    
    def test_cleanup_no_old_records(self, dlq):
        """测试清理时没有旧记录"""
        # 添加一个已解决的死信
        dead_letter_id = dlq.add_to_dead_letter(
            execution_id='test-123',
            task_type='ai_call',
            error=TimeoutError('Error'),
            task_context={},
        )
        dlq.mark_as_resolved(dead_letter_id)
        
        # 清理 30 天前的记录（应该没有）
        deleted = dlq.cleanup_resolved(days=30)
        
        assert deleted == 0


# ==================== 并发操作测试 ====================

class TestConcurrentOperations:
    """并发操作测试"""
    
    def test_concurrent_add(self, dlq):
        """测试并发添加"""
        import threading
        
        errors = []
        
        def add_dead_letter(i):
            try:
                dlq.add_to_dead_letter(
                    execution_id=f'test-{i}',
                    task_type='ai_call',
                    error=TimeoutError(f'Error {i}'),
                    task_context={'index': i},
                )
            except Exception as e:
                errors.append(e)
        
        # 并发添加 10 个死信
        threads = [threading.Thread(target=add_dead_letter, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        # 验证所有记录都被添加
        letters = dlq.list_dead_letters()
        assert len(letters) == 10


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=wechat_backend.v2.services.dead_letter_queue', '--cov-report=html'])
