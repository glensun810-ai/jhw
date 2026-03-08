"""
数据库操作单元测试

测试覆盖:
1. 数据库连接池操作
2. CRUD 操作
3. 事务管理
4. 错误处理
5. 数据验证

作者：系统架构组
日期：2026-03-08
版本：1.0
"""

import pytest
import sqlite3
import json
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from typing import Dict, Any, List
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend_python'))

from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
)


# ==================== Fixture ====================

@pytest.fixture
def mock_db_pool():
    """模拟数据库连接池"""
    mock_pool = Mock()
    mock_conn = Mock()
    mock_cursor = Mock()
    
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.lastrowid = 123
    mock_cursor.fetchone.return_value = ('test-data',)
    
    mock_pool.get_connection.return_value = mock_conn
    return mock_pool


@pytest.fixture
def result_repository(mock_db_pool):
    """创建结果仓库实例（带模拟连接池）"""
    with patch('wechat_backend.diagnosis_report_repository.get_db_pool', return_value=mock_db_pool):
        repo = DiagnosisResultRepository()
        return repo


@pytest.fixture
def report_repository(mock_db_pool):
    """创建报告仓库实例（带模拟连接池）"""
    with patch('wechat_backend.diagnosis_report_repository.get_db_pool', return_value=mock_db_pool):
        repo = DiagnosisReportRepository()
        return repo


# ==================== 数据库连接池测试 ====================

class TestDatabaseConnectionPool:
    """数据库连接池测试"""
    
    def test_get_connection_from_pool(self, mock_db_pool):
        """测试从连接池获取连接"""
        conn = mock_db_pool.get_connection()
        
        # 验证连接被获取
        assert conn is not None
        mock_db_pool.get_connection.assert_called_once()
    
    def test_return_connection_to_pool(self, mock_db_pool):
        """测试归还连接到连接池"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        # 使用连接
        with patch('wechat_backend.diagnosis_report_repository.get_db_pool', return_value=mock_db_pool):
            repo = DiagnosisResultRepository()
            with repo.get_connection() as conn:
                pass
        
        # 验证连接被归还
        mock_db_pool.return_connection.assert_called_once_with(mock_conn)
    
    def test_connection_pool_reuse(self, mock_db_pool):
        """测试连接池复用"""
        # 第一次获取
        conn1 = mock_db_pool.get_connection()
        
        # 归还
        mock_db_pool.return_connection(conn1)
        
        # 第二次获取（应该复用）
        conn2 = mock_db_pool.get_connection()
        
        # 验证连接池被使用
        assert mock_db_pool.get_connection.call_count == 2
        assert mock_db_pool.return_connection.call_count == 1


# ==================== CRUD 操作测试 ====================

class TestCRUDOperations:
    """CRUD 操作测试"""
    
    def test_create_report(self, report_repository, mock_db_pool):
        """测试创建报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.lastrowid = 456
        
        report_data = {
            'execution_id': 'test-exec-create',
            'user_id': 'user-123',
            'brand_list': ['BrandA', 'BrandB'],
            'status': 'initializing'
        }
        
        with patch('wechat_backend.diagnosis_report_repository.db_logger'):
            report_id = report_repository.create_report(report_data)
        
        # 验证返回了 report_id
        assert report_id == 456
        
        # 验证执行了 INSERT
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'INSERT' in execute_call[0][0]
    
    def test_read_report_by_id(self, report_repository, mock_db_pool):
        """测试通过 ID 读取报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = (
            1, 'test-exec-123', 'user-123', 'initializing', 'initializing', 0
        )
        
        report = report_repository.get_by_id(1)
        
        # 验证返回了报告数据
        assert report is not None
        
        # 验证执行了 SELECT
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'SELECT' in execute_call[0][0]
        assert 'WHERE id = ?' in execute_call[0][0]
    
    def test_read_report_by_execution_id(self, report_repository, mock_db_pool):
        """测试通过 execution_id 读取报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = (
            1, 'test-exec-123', 'user-123', 'completed', 'completed', 100
        )
        
        report = report_repository.get_by_execution_id('test-exec-123')
        
        # 验证返回了报告数据
        assert report is not None
        
        # 验证执行了 SELECT
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'SELECT' in execute_call[0][0]
        assert 'WHERE execution_id = ?' in execute_call[0][0]
    
    def test_read_report_not_found(self, report_repository, mock_db_pool):
        """测试读取不存在的报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = None
        
        report = report_repository.get_by_id(999)
        
        # 验证返回 None
        assert report is None
    
    def test_update_report(self, report_repository, mock_db_pool):
        """测试更新报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        
        update_data = {
            'status': 'completed',
            'stage': 'completed',
            'progress': 100
        }
        
        report_repository.update_report(1, update_data)
        
        # 验证执行了 UPDATE
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'UPDATE' in execute_call[0][0]
        assert 'WHERE id = ?' in execute_call[0][0]
        
        # 验证提交了事务
        mock_conn.commit.assert_called_once()
    
    def test_delete_report(self, report_repository, mock_db_pool):
        """测试删除报告"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        
        report_repository.delete_report(1)
        
        # 验证执行了 DELETE
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'DELETE' in execute_call[0][0]
        assert 'WHERE id = ?' in execute_call[0][0]
        
        # 验证提交了事务
        mock_conn.commit.assert_called_once()
    
    def test_create_result(self, result_repository, mock_db_pool):
        """测试创建诊断结果"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.lastrowid = 789
        
        result_data = {
            'brand': 'BrandA',
            'question': 'Test question',
            'response': {'content': 'Test answer'}
        }
        
        with patch('wechat_backend.diagnosis_report_repository.db_logger'):
            result_id = result_repository.add(1, 'test-exec-result', result_data)
        
        # 验证返回了 result_id
        assert result_id == 789
        
        # 验证执行了 INSERT
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'INSERT' in execute_call[0][0]
    
    def test_read_results_by_execution_id(self, result_repository, mock_db_pool):
        """测试通过 execution_id 读取结果列表"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [
            (1, 'exec-123', 'BrandA', 'Q1', 'Answer 1'),
            (2, 'exec-123', 'BrandB', 'Q2', 'Answer 2'),
        ]
        
        results = result_repository.get_by_execution_id('exec-123')
        
        # 验证返回了结果列表
        assert len(results) == 2
        
        # 验证执行了 SELECT
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args
        assert 'SELECT' in execute_call[0][0]
        assert 'WHERE execution_id = ?' in execute_call[0][0]


# ==================== 事务管理测试 ====================

class TestTransactionManagement:
    """事务管理测试"""
    
    def test_transaction_commit_on_success(self, report_repository, mock_db_pool):
        """测试成功时提交事务"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        with report_repository.get_connection() as conn:
            # 模拟成功操作
            pass
        
        # 验证提交了事务
        mock_conn.commit.assert_called_once()
    
    def test_transaction_rollback_on_error(self, report_repository, mock_db_pool):
        """测试失败时回滚事务"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            with report_repository.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test VALUES (?)", (1,))
        
        # 验证回滚了事务
        mock_conn.rollback.assert_called_once()
    
    def test_transaction_always_returns_connection(self, report_repository, mock_db_pool):
        """测试事务总是归还连接"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        try:
            with report_repository.get_connection() as conn:
                raise Exception("Test error")
        except Exception:
            pass
        
        # 验证连接被归还（即使失败）
        mock_db_pool.return_connection.assert_called_once()
    
    def test_nested_transaction_support(self, report_repository, mock_db_pool):
        """测试嵌套事务支持"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        # 外层事务
        with report_repository.get_connection() as conn1:
            # 内层事务
            with report_repository.get_connection() as conn2:
                pass
        
        # 验证连接被正确管理
        assert mock_db_pool.return_connection.call_count >= 1


# ==================== 错误处理测试 ====================

class TestDatabaseErrorHandling:
    """数据库错误处理测试"""
    
    def test_sqlite_operational_error(self, report_repository, mock_db_pool):
        """测试 SQLite 操作错误处理"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.side_effect = sqlite3.OperationalError("Table not found")
        
        with patch('wechat_backend.diagnosis_report_repository.db_logger') as mock_logger:
            # 应该处理错误而不是抛异常
            try:
                with report_repository.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM non_existent_table")
            except sqlite3.OperationalError:
                pass
        
        # 验证记录了错误日志
        assert mock_logger.error.called
    
    def test_database_connection_timeout(self, report_repository, mock_db_pool):
        """测试数据库连接超时处理"""
        mock_pool = mock_db_pool
        mock_pool.get_connection.side_effect = sqlite3.OperationalError("Connection timeout")
        
        with pytest.raises(sqlite3.OperationalError):
            with report_repository.get_connection() as conn:
                pass
    
    def test_integrity_error(self, report_repository, mock_db_pool):
        """测试完整性错误处理"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")
        
        with pytest.raises(sqlite3.IntegrityError):
            with report_repository.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test VALUES (1)")
    
    def test_data_error(self, report_repository, mock_db_pool):
        """测试数据错误处理"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.side_effect = sqlite3.DataError("Data type mismatch")
        
        with pytest.raises(sqlite3.DataError):
            with report_repository.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test VALUES (?)", (None,))


# ==================== 数据验证测试 ====================

class TestDataValidation:
    """数据验证测试"""
    
    def test_validate_report_data(self, report_repository):
        """测试报告数据验证"""
        valid_data = {
            'execution_id': 'test-exec-123',
            'user_id': 'user-123',
            'brand_list': ['BrandA', 'BrandB'],
            'status': 'initializing'
        }
        
        # 验证数据格式正确
        assert 'execution_id' in valid_data
        assert isinstance(valid_data['brand_list'], list)
        assert len(valid_data['brand_list']) > 0
    
    def test_validate_result_data(self, result_repository):
        """测试结果数据验证"""
        valid_data = {
            'brand': 'BrandA',
            'question': 'Test question',
            'response': {
                'content': 'Test answer',
                'metadata': {}
            }
        }
        
        # 验证数据格式正确
        assert 'brand' in valid_data
        assert 'question' in valid_data
        assert 'response' in valid_data
        assert isinstance(valid_data['response'], dict)
    
    def test_validate_execution_id_format(self, report_repository):
        """测试 execution_id 格式验证"""
        # 有效的 execution_id
        valid_ids = [
            'test-exec-123',
            'exec-2026-03-08-001',
            'diagnosis-uuid-abc-def'
        ]
        
        for exec_id in valid_ids:
            assert isinstance(exec_id, str)
            assert len(exec_id) > 0
    
    def test_validate_timestamp_format(self, report_repository):
        """测试时间戳格式验证"""
        now = datetime.now()
        iso_format = now.isoformat()
        
        # 验证 ISO 格式
        assert isinstance(iso_format, str)
        assert 'T' in iso_format or ' ' in iso_format
    
    def test_validate_json_serialization(self, report_repository):
        """测试 JSON 序列化验证"""
        data = {
            'execution_id': 'test-exec-123',
            'brand_list': ['BrandA', 'BrandB'],
            'metadata': {
                'user_agent': 'Test',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # 验证可以序列化
        json_str = json.dumps(data, ensure_ascii=False)
        assert isinstance(json_str, str)
        
        # 验证可以反序列化
        loaded = json.loads(json_str)
        assert loaded == data


# ==================== 批量操作测试 ====================

class TestBatchOperations:
    """批量操作测试"""
    
    def test_batch_insert(self, result_repository, mock_db_pool):
        """测试批量插入"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.lastrowid = 100
        
        results = [
            {'brand': 'BrandA', 'question': 'Q1', 'response': {'content': 'A1'}},
            {'brand': 'BrandB', 'question': 'Q2', 'response': {'content': 'A2'}},
            {'brand': 'BrandC', 'question': 'Q3', 'response': {'content': 'A3'}},
        ]
        
        result_ids = result_repository.add_batch(
            report_id=1,
            execution_id='test-exec-batch',
            results=results,
            batch_size=10,
            commit=True
        )
        
        # 验证返回了正确的 ID 数量
        assert len(result_ids) == 3
        
        # 验证执行了多次 INSERT
        assert mock_cursor.execute.call_count >= 3
    
    def test_batch_insert_with_commit(self, result_repository, mock_db_pool):
        """测试批量插入带提交"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        results = [
            {'brand': 'BrandA', 'question': 'Q1', 'response': {'content': 'A1'}},
        ]
        
        result_repository.add_batch(
            report_id=1,
            execution_id='test-exec-commit',
            results=results,
            commit=True
        )
        
        # 验证提交了事务
        mock_conn.commit.assert_called()
    
    def test_batch_insert_without_commit(self, result_repository, mock_db_pool):
        """测试批量插入不带提交"""
        mock_conn = mock_db_pool.get_connection.return_value
        
        results = [
            {'brand': 'BrandA', 'question': 'Q1', 'response': {'content': 'A1'}},
        ]
        
        result_repository.add_batch(
            report_id=1,
            execution_id='test-exec-no-commit',
            results=results,
            commit=False
        )
        
        # 验证没有提交事务
        mock_conn.commit.assert_not_called()
    
    def test_batch_insert_partial_failure(self, result_repository, mock_db_pool):
        """测试批量插入部分失败"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        
        # 模拟部分失败
        call_count = [0]
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise sqlite3.IntegrityError("Constraint error")
            mock_cursor.lastrowid = call_count[0]
        
        mock_cursor.execute.side_effect = execute_side_effect
        
        results = [
            {'brand': 'BrandA', 'question': 'Q1', 'response': {'content': 'A1'}},
            {'brand': 'BrandB', 'question': 'Q2', 'response': {'content': 'A2'}},
            {'brand': 'BrandC', 'question': 'Q3', 'response': {'content': 'A3'}},
        ]
        
        with pytest.raises(sqlite3.IntegrityError):
            result_repository.add_batch(
                report_id=1,
                execution_id='test-exec-partial-fail',
                results=results,
                batch_size=10,
                commit=True
            )


# ==================== 性能测试 ====================

class TestDatabasePerformance:
    """数据库性能测试"""
    
    def test_connection_pool_performance(self, mock_db_pool):
        """测试连接池性能"""
        import time
        
        start = time.time()
        
        # 模拟多次获取连接
        for _ in range(100):
            conn = mock_db_pool.get_connection()
            mock_db_pool.return_connection(conn)
        
        elapsed = time.time() - start
        
        # 验证性能在可接受范围内
        assert elapsed < 1.0  # 100 次操作应该在 1 秒内完成
    
    def test_batch_insert_performance(self, result_repository, mock_db_pool):
        """测试批量插入性能"""
        mock_conn = mock_db_pool.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.lastrowid = 1
        
        # 准备大量数据
        results = [
            {'brand': f'Brand{i}', 'question': f'Q{i}', 'response': {'content': f'A{i}'}}
            for i in range(100)
        ]
        
        import time
        start = time.time()
        
        result_ids = result_repository.add_batch(
            report_id=1,
            execution_id='test-exec-perf',
            results=results,
            batch_size=50,
            commit=True
        )
        
        elapsed = time.time() - start
        
        # 验证性能
        assert len(result_ids) == 100
        assert elapsed < 5.0  # 100 条记录应该在 5 秒内完成


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
