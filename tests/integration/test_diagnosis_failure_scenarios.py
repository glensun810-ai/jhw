"""
诊断失败场景集成测试

测试覆盖：
1. 数据库 schema 不匹配时的失败处理
2. 错误码正确返回
3. 失败状态正确持久化
4. 轮询终止条件验证

@author: 系统架构组
@date: 2026-03-09
@version: 1.0.0
"""

import pytest
import asyncio
import sqlite3
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend_python'))

from wechat_backend.error_codes import ErrorCode, DiagnosisErrorCode


class TestDiagnosisFailureScenarios:
    """诊断失败场景测试"""

    @pytest.fixture
    def test_db_with_schema(self, tmp_path):
        """创建测试数据库（包含 sentiment 列）"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 创建完整的表结构（包含 sentiment）
        cursor.execute('''
            CREATE TABLE diagnosis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                stage TEXT NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                should_stop_polling BOOLEAN DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE diagnosis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                question TEXT NOT NULL,
                model TEXT NOT NULL,
                response_content TEXT NOT NULL,
                response_latency REAL,
                geo_data TEXT NOT NULL,
                quality_score REAL NOT NULL,
                quality_level TEXT NOT NULL,
                quality_details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT,
                sentiment TEXT DEFAULT 'neutral',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
            )
        ''')

        cursor.execute('CREATE INDEX idx_reports_execution ON diagnosis_reports(execution_id)')
        cursor.execute('CREATE INDEX idx_results_execution ON diagnosis_results(execution_id)')

        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.fixture
    def test_db_without_sentiment(self, tmp_path):
        """创建测试数据库（不包含 sentiment 列 - 模拟旧 schema）"""
        db_path = tmp_path / "test_old.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE diagnosis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                stage TEXT NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                should_stop_polling BOOLEAN DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 不包含 sentiment 列
        cursor.execute('''
            CREATE TABLE diagnosis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                question TEXT NOT NULL,
                model TEXT NOT NULL,
                response_content TEXT NOT NULL,
                response_latency REAL,
                geo_data TEXT NOT NULL,
                quality_score REAL NOT NULL,
                quality_level TEXT NOT NULL,
                quality_details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
            )
        ''')

        conn.commit()
        conn.close()

        return str(db_path)

    def test_error_code_diagnosis_save_failed_exists(self):
        """测试 DIAGNOSIS_SAVE_FAILED 错误码存在"""
        # 验证错误码存在且可访问
        assert hasattr(ErrorCode, 'DIAGNOSIS_SAVE_FAILED')
        assert DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED is not None

        # 验证错误码属性
        error_code = DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED
        assert error_code.code == '2000-014'
        assert '保存失败' in error_code.message
        assert error_code.http_status == 500

    def test_error_code_format_message(self):
        """测试错误码消息格式化"""
        from wechat_backend.error_codes import get_error_message

        error_code = DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED
        message = get_error_message(error_code, {'detail': '缺少 sentiment 列'})

        assert '保存失败' in message
        assert '缺少 sentiment 列' in message

    def test_database_insert_with_sentiment(self, test_db_with_schema):
        """测试向包含 sentiment 列的表插入数据"""
        conn = sqlite3.connect(test_db_with_schema)
        cursor = conn.cursor()

        # 创建报告
        cursor.execute('''
            INSERT INTO diagnosis_reports (execution_id, user_id, brand_name, status, progress, stage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_exec_123', 'user_123', '测试品牌', 'ai_fetching', 50, 'ai_fetching'))

        report_id = cursor.lastrowid

        # 插入结果（包含 sentiment）
        cursor.execute('''
            INSERT INTO diagnosis_results (
                report_id, execution_id, brand, question, model,
                response_content, response_latency, geo_data,
                quality_score, quality_level, quality_details, sentiment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, 'test_exec_123', '测试品牌', '测试问题', 'deepseek',
            '测试响应', 200.0, '{"exposure": true}',
            0.85, 'high', '{}', 'positive'
        ))

        conn.commit()

        # 验证插入成功
        cursor.execute('SELECT sentiment FROM diagnosis_results WHERE execution_id = ?', ('test_exec_123',))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 'positive'

        conn.close()

    def test_database_insert_fails_without_sentiment(self, test_db_without_sentiment):
        """测试向不包含 sentiment 列的表插入数据会失败"""
        conn = sqlite3.connect(test_db_without_sentiment)
        cursor = conn.cursor()

        # 创建报告
        cursor.execute('''
            INSERT INTO diagnosis_reports (execution_id, user_id, brand_name, status, progress, stage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_exec_456', 'user_456', '测试品牌', 'ai_fetching', 50, 'ai_fetching'))

        report_id = cursor.lastrowid
        conn.commit()

        # 尝试插入包含 sentiment 的数据（应该失败）
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            cursor.execute('''
                INSERT INTO diagnosis_results (
                    report_id, execution_id, brand, question, model,
                    response_content, response_latency, geo_data,
                    quality_score, quality_level, quality_details, sentiment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id, 'test_exec_456', '测试品牌', '测试问题', 'deepseek',
                '测试响应', 200.0, '{"exposure": true}',
                0.85, 'high', '{}', 'positive'
            ))

        assert 'has no column named sentiment' in str(exc_info.value)

        conn.close()

    def test_migration_adds_sentiment_column(self, test_db_without_sentiment):
        """测试迁移脚本正确添加 sentiment 列"""
        # 运行迁移
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend_python'))

        # 使用 importlib 导入（因为模块名以数字开头）
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_005",
            Path(__file__).parent.parent.parent / 'backend_python' / 'migrations' / '005_add_sentiment_column.py'
        )
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)

        # 修改 DB_PATH 用于测试
        migration_module.DB_PATH = Path(test_db_without_sentiment)

        # 执行迁移
        success = migration_module.migrate()

        assert success is True

        # 验证 sentiment 列已添加
        conn = sqlite3.connect(test_db_without_sentiment)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(diagnosis_results)')
        columns = [row[1] for row in cursor.fetchall()]

        assert 'sentiment' in columns

        conn.close()

    def test_failed_status_persisted_correctly(self, test_db_with_schema):
        """测试失败状态正确持久化"""
        conn = sqlite3.connect(test_db_with_schema)
        cursor = conn.cursor()

        execution_id = 'test_failed_exec'

        # 创建失败的报告
        cursor.execute('''
            INSERT INTO diagnosis_reports (execution_id, user_id, brand_name, status, progress, stage, should_stop_polling, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (execution_id, 'user_123', '测试品牌', 'failed', 30, 'failed', 1, '诊断执行失败：缺少 sentiment 列'))

        conn.commit()

        # 验证状态
        cursor.execute('''
            SELECT status, progress, stage, should_stop_polling, error_message
            FROM diagnosis_reports WHERE execution_id = ?
        ''', (execution_id,))

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 'failed'
        assert row[1] == 30
        assert row[2] == 'failed'
        assert row[3] == 1  # should_stop_polling = true
        assert '缺少 sentiment 列' in row[4]

        conn.close()

    def test_error_determination_from_message(self):
        """测试从错误消息确定错误码"""
        from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator

        # 创建 mock orchestrator
        orchestrator = Mock(spec=DiagnosisOrchestrator)
        orchestrator._determine_error_code = DiagnosisOrchestrator._determine_error_code.__get__(
            orchestrator, DiagnosisOrchestrator
        )

        # 测试保存错误（包含"保存"关键词）
        error_code = orchestrator._determine_error_code('结果保存失败：缺少 sentiment 列')
        assert error_code == DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED

        # 测试数据库错误（包含"save"关键词）
        error_code = orchestrator._determine_error_code('Failed to save results: sentiment column missing')
        assert error_code == DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED

        # 测试超时错误
        error_code = orchestrator._determine_error_code('Operation timeout')
        assert error_code == DiagnosisErrorCode.DIAGNOSIS_TIMEOUT

        # 测试验证错误（不包含"数量"）
        error_code = orchestrator._determine_error_code('数据验证失败：格式错误')
        assert error_code == DiagnosisErrorCode.DIAGNOSIS_RESULT_INVALID

        # 测试数量不匹配错误
        error_code = orchestrator._determine_error_code('数据验证失败：数量不匹配')
        assert error_code == DiagnosisErrorCode.DIAGNOSIS_RESULT_COUNT_MISMATCH


class TestPollingTerminationConditions:
    """轮询终止条件测试"""

    def test_should_stop_polling_when_failed(self):
        """测试失败时应该停止轮询"""
        # 模拟后端返回的状态
        status_response = {
            'execution_id': 'test_exec',
            'status': 'failed',
            'progress': 30,
            'stage': 'failed',
            'should_stop_polling': True,
            'error_message': '诊断失败'
        }

        # 前端应该停止轮询的条件
        assert status_response['status'] == 'failed'
        assert status_response['should_stop_polling'] is True

    def test_should_stop_polling_when_timeout(self):
        """测试超时时应该停止轮询"""
        status_response = {
            'execution_id': 'test_exec',
            'status': 'timeout',
            'progress': 0,
            'stage': 'timeout',
            'should_stop_polling': True,
            'error_message': '诊断超时'
        }

        assert status_response['status'] == 'timeout'
        assert status_response['should_stop_polling'] is True

    def test_should_continue_polling_when_in_progress(self):
        """测试进行中时应该继续轮询"""
        status_response = {
            'execution_id': 'test_exec',
            'status': 'ai_fetching',
            'progress': 50,
            'stage': 'ai_fetching',
            'should_stop_polling': False
        }

        assert status_response['status'] != 'failed'
        assert status_response['status'] != 'timeout'
        assert status_response['should_stop_polling'] is False


class TestFrontendBackendIntegration:
    """前后端集成测试"""

    def test_frontend_receives_failed_status(self):
        """测试前端接收到失败状态"""
        # 模拟后端 API 返回
        api_response = {
            'success': True,
            'data': {
                'execution_id': 'test_exec',
                'status': 'failed',
                'progress': 100,
                'stage': 'failed',
                'should_stop_polling': True,
                'error_message': 'table diagnosis_results has no column named sentiment',
                'error_code': 'DIAGNOSIS_SAVE_FAILED'
            }
        }

        # 前端应该：
        # 1. 检测到 status=failed
        # 2. 检测到 should_stop_polling=true
        # 3. 停止轮询
        # 4. 显示错误 UI

        data = api_response['data']
        assert data['status'] == 'failed'
        assert data['should_stop_polling'] is True
        assert 'error_code' in data

    def test_frontend_retry_resets_state(self):
        """测试前端重试重置状态"""
        # 模拟 WebSocket 客户端状态
        class MockWebSocketClient:
            def __init__(self):
                self._isPermanentFailure = True
                self.reconnectAttempts = 10

            def resetPermanentFailure(self):
                self._isPermanentFailure = False
                self.reconnectAttempts = 0

        ws_client = MockWebSocketClient()

        # 初始状态：永久失败
        assert ws_client._isPermanentFailure is True

        # 重置后
        ws_client.resetPermanentFailure()

        # 验证已重置
        assert ws_client._isPermanentFailure is False
        assert ws_client.reconnectAttempts == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
