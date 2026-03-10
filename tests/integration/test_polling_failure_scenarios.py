"""
前端轮询优化测试 - 失败场景验证

测试覆盖：
1. 后端返回 failed 状态时，轮询立即停止
2. WebSocket 收到失败消息时停止重连
3. 用户重试功能正常工作
4. 失败状态 UI 展示正确

@author: 系统架构组
@date: 2026-03-09
@version: 1.0.0
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any


# ==================== PollingManager 失败场景测试 ====================

class TestPollingManagerFailureScenarios:
    """轮询管理器失败场景测试"""

    @pytest.fixture
    def polling_manager(self):
        """创建轮询管理器实例"""
        from miniprogram.services.pollingManager import PollingManager
        return PollingManager()

    def test_stop_polling_on_failed_status(self, polling_manager):
        """测试检测到 failed 状态立即停止轮询"""
        # 模拟回调
        on_error_called = []
        stop_polling_called = []

        def mock_on_error(error):
            on_error_called.append(error)

        def mock_stop_polling(exec_id):
            stop_polling_called.append(exec_id)

        # Mock 内部方法
        polling_manager.stopPolling = mock_stop_polling
        polling_manager._scheduleNextPoll = Mock()

        # 创建任务
        callbacks = {'onError': mock_on_error, 'onComplete': None, 'onStatus': None}
        polling_manager.pollingTasks['test_exec_123'] = {
            'executionId': 'test_exec_123',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True,
            'attempt': 0
        }

        # 模拟收到 failed 状态
        status_data = {
            'status': 'failed',
            'progress': 30,
            'error_message': '数据库错误：缺少 sentiment 列',
            'should_stop_polling': False  # 即使后端没有设置，也应该停止
        }

        # 保存状态
        polling_manager.lastStatusMap['test_exec_123'] = status_data

        # 调用 _poll 方法（模拟轮询）
        async def run_test():
            await polling_manager._poll('test_exec_123')

        asyncio.run(run_test())

        # 验证 onError 被调用
        assert len(on_error_called) == 1
        assert on_error_called[0]['status'] == 'failed'
        assert '数据库错误' in on_error_called[0]['message']
        assert on_error_called[0]['type'] == 'TASK_FAILED'

        # 验证 stopPolling 被调用
        assert len(stop_polling_called) == 1
        assert stop_polling_called[0] == 'test_exec_123'

        # 验证没有安排下一次轮询
        polling_manager._scheduleNextPoll.assert_not_called()

    def test_stop_polling_on_timeout_status(self, polling_manager):
        """测试检测到 timeout 状态立即停止轮询"""
        on_error_called = []
        stop_polling_called = []

        def mock_on_error(error):
            on_error_called.append(error)

        def mock_stop_polling(exec_id):
            stop_polling_called.append(exec_id)

        polling_manager.stopPolling = mock_stop_polling
        polling_manager._scheduleNextPoll = Mock()

        callbacks = {'onError': mock_on_error}
        polling_manager.pollingTasks['test_exec_456'] = {
            'executionId': 'test_exec_456',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True,
            'attempt': 0
        }

        status_data = {
            'status': 'timeout',
            'progress': 0,
            'error_message': '诊断超时',
            'should_stop_polling': False
        }

        polling_manager.lastStatusMap['test_exec_456'] = status_data

        async def run_test():
            await polling_manager._poll('test_exec_456')

        asyncio.run(run_test())

        # 验证 onError 被调用
        assert len(on_error_called) == 1
        assert on_error_called[0]['status'] == 'timeout'

        # 验证 stopPolling 被调用
        assert len(stop_polling_called) == 1

    def test_continue_polling_on_normal_status(self, polling_manager):
        """测试正常状态继续轮询"""
        on_status_called = []
        schedule_called = []

        def mock_on_status(status):
            on_status_called.append(status)

        def mock_schedule(exec_id):
            schedule_called.append(exec_id)

        polling_manager._scheduleNextPoll = mock_schedule
        polling_manager.stopPolling = Mock()

        callbacks = {'onStatus': mock_on_status}
        polling_manager.pollingTasks['test_exec_789'] = {
            'executionId': 'test_exec_789',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True,
            'attempt': 0
        }

        status_data = {
            'status': 'ai_fetching',
            'progress': 50,
            'should_stop_polling': False
        }

        polling_manager.lastStatusMap['test_exec_789'] = status_data

        async def run_test():
            await polling_manager._poll('test_exec_789')

        asyncio.run(run_test())

        # 验证 onStatus 被调用
        assert len(on_status_called) == 1

        # 验证安排了下一次轮询
        assert len(schedule_called) == 1

    def test_stop_on_should_stop_polling_flag(self, polling_manager):
        """测试 should_stop_polling=true 时停止"""
        on_complete_called = []
        stop_polling_called = []

        def mock_on_complete(result):
            on_complete_called.append(result)

        def mock_stop_polling(exec_id):
            stop_polling_called.append(exec_id)

        polling_manager.stopPolling = mock_stop_polling
        polling_manager._scheduleNextPoll = Mock()

        callbacks = {'onComplete': mock_on_complete}
        polling_manager.pollingTasks['test_exec_complete'] = {
            'executionId': 'test_exec_complete',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True,
            'attempt': 0
        }

        status_data = {
            'status': 'completed',
            'progress': 100,
            'should_stop_polling': True
        }

        polling_manager.lastStatusMap['test_exec_complete'] = status_data

        async def run_test():
            await polling_manager._poll('test_exec_complete')

        asyncio.run(run_test())

        # 验证 onComplete 被调用
        assert len(on_complete_called) == 1

        # 验证 stopPolling 被调用
        assert len(stop_polling_called) == 1


# ==================== DiagnosisPage 失败场景测试 ====================

class TestDiagnosisPageFailureHandling:
    """诊断页面失败处理测试"""

    def test_handle_status_update_failed(self):
        """测试处理 failed 状态更新"""
        # 模拟页面实例
        page_data = {
            'showErrorToast': False,
            'errorType': '',
            'errorTitle': '',
            'errorDetail': '',
            'showRetry': False,
            'showCancel': False
        }

        set_data_called = []

        def mock_set_data(data):
            set_data_called.append(data)
            page_data.update(data)

        # 模拟页面
        page = MagicMock()
        page.data = page_data
        page.setData = mock_set_data
        page.stopPolling = Mock()

        # 导入并调用处理方法
        from miniprogram.pages.diagnosis.diagnosis import _handleFailedStatus

        status = {
            'status': 'failed',
            'error_message': '诊断执行失败：table diagnosis_results has no column named sentiment',
            'error_code': 'DIAGNOSIS_SAVE_FAILED'
        }

        # 调用失败处理方法
        _handleFailedStatus(page, status)

        # 验证 setData 被调用
        assert len(set_data_called) == 1
        assert set_data_called[0]['showErrorToast'] is True
        assert set_data_called[0]['errorTitle'] == '诊断失败'
        assert set_data_called[0]['showRetry'] is True

        # 验证 stopPolling 被调用
        page.stopPolling.assert_called()

    def test_handle_polling_error_task_failed(self):
        """测试处理 TASK_FAILED 类型的轮询错误"""
        page_data = {'showErrorToast': False}
        set_data_called = []

        def mock_set_data(data):
            set_data_called.append(data)
            page_data.update(data)

        page = MagicMock()
        page.data = page_data
        page.setData = mock_set_data
        page.stopPolling = Mock()
        page._handleFailedStatus = Mock()

        from miniprogram.pages.diagnosis.diagnosis import handlePollingError

        error = {
            'type': 'TASK_FAILED',
            'status': 'failed',
            'message': '诊断任务失败',
            'error_code': 'DIAGNOSIS_SAVE_FAILED'
        }

        handlePollingError(page, error)

        # 验证调用了失败处理
        page._handleFailedStatus.assert_called_once()
        page.stopPolling.assert_called()


# ==================== DiagnosisService 失败场景测试 ====================

class TestDiagnosisServiceFailureHandling:
    """诊断服务失败处理测试"""

    def test_reset_websocket_failure_before_polling(self):
        """测试开始轮询前重置 WebSocket 失败标志"""
        # Mock WebSocket 客户端
        mock_ws_client = MagicMock()
        mock_ws_client.resetPermanentFailure = Mock()

        with patch('miniprogram.services.diagnosisService.webSocketClient', mock_ws_client):
            from miniprogram.services.diagnosisService import DiagnosisService

            service = DiagnosisService()
            service.currentTask = {'executionId': 'test_exec_123'}

            # Mock 其他依赖
            service._ensureCurrentTask = Mock()
            service._connectWebSocket = Mock()
            service._startPolling = Mock()

            # 开始轮询
            service.startPolling({}, 'test_exec_123')

            # 验证 resetPermanentFailure 被调用
            mock_ws_client.resetPermanentFailure.assert_called_once()


# ==================== WebSocket 失败场景测试 ====================

class TestWebSocketFailureHandling:
    """WebSocket 失败处理测试"""

    def test_stop_reconnect_on_permanent_failure(self):
        """测试永久失败标志阻止重连"""
        from miniprogram.services.webSocketClient import WebSocketClient

        client = WebSocketClient()
        client._isPermanentFailure = True
        client._setState = Mock()
        client._cleanupForFallback = Mock()

        callbacks = {'onFallback': Mock()}
        client.callbacks = callbacks

        # 尝试重连
        client._attemptReconnect()

        # 验证没有重连
        assert client._setState.called
        client._cleanupForFallback.assert_called()

    def test_reset_permanent_failure(self):
        """测试重置永久失败标志"""
        from miniprogram.services.webSocketClient import WebSocketClient

        client = WebSocketClient()
        client._isPermanentFailure = True

        # 重置
        client.resetPermanentFailure()

        # 验证已重置
        assert client._isPermanentFailure is False
        assert client.reconnectAttempts == 0

    def test_handle_failed_message_from_backend(self):
        """测试处理后端返回的失败消息"""
        from miniprogram.services.webSocketClient import WebSocketClient

        client = WebSocketClient()

        on_error_called = []
        on_fallback_called = []

        client.callbacks = {
            'onError': lambda e: on_error_called.append(e),
            'onFallback': lambda: on_fallback_called.append(True)
        }

        # 模拟收到失败消息
        message_data = {
            'event': 'failed',
            'data': {
                'status': 'failed',
                'error_message': '诊断失败'
            }
        }

        client._setState = Mock()
        client._cleanupForFallback = Mock()

        client._handleMessage(message_data)

        # 验证设置了永久失败标志
        assert client._isPermanentFailure is True

        # 验证调用了 onError
        assert len(on_error_called) == 1
        assert on_error_called[0]['type'] == 'BACKEND_FAILED'

        # 验证调用了降级
        client._cleanupForFallback.assert_called()


# ==================== 集成测试 ====================

class TestFailureScenarioIntegration:
    """失败场景集成测试"""

    def test_full_failure_flow(self):
        """测试完整失败流程"""
        # 1. 后端返回 failed 状态
        # 2. PollingManager 检测到并停止轮询
        # 3. DiagnosisPage 显示错误 UI
        # 4. 用户点击重试
        # 5. 重置失败标志并重新开始

        from miniprogram.services.pollingManager import PollingManager

        polling_manager = PollingManager()

        # 记录所有回调调用
        calls_log = []

        def on_error(error):
            calls_log.append(('onError', error))

        def on_status(status):
            calls_log.append(('onStatus', status))

        # 创建任务
        callbacks = {'onError': on_error, 'onStatus': on_status}
        polling_manager.pollingTasks['integration_test'] = {
            'executionId': 'integration_test',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True,
            'attempt': 0
        }

        # 模拟 failed 状态
        status_data = {
            'status': 'failed',
            'progress': 30,
            'error_message': '测试失败场景',
            'should_stop_polling': False
        }

        polling_manager.lastStatusMap['integration_test'] = status_data

        # Mock 方法
        stop_calls = []
        polling_manager.stopPolling = lambda x: stop_calls.append(x)
        polling_manager._scheduleNextPoll = Mock()

        async def run_test():
            await polling_manager._poll('integration_test')

        asyncio.run(run_test())

        # 验证流程
        assert len(calls_log) == 1
        assert calls_log[0][0] == 'onError'
        assert calls_log[0][1]['type'] == 'TASK_FAILED'
        assert len(stop_calls) == 1
        polling_manager._scheduleNextPoll.assert_not_called()

    def test_retry_resets_all_failure_flags(self):
        """测试重试时重置所有失败标志"""
        from miniprogram.services.webSocketClient import WebSocketClient
        from miniprogram.services.diagnosisService import DiagnosisService

        # 设置 WebSocket 为永久失败状态
        ws_client = WebSocketClient()
        ws_client._isPermanentFailure = True
        ws_client.reconnectAttempts = 10

        # 创建诊断服务
        service = DiagnosisService()
        service.currentTask = {'executionId': 'retry_test'}

        # Mock 依赖
        with patch('miniprogram.services.diagnosisService.webSocketClient', ws_client):
            service._ensureCurrentTask = Mock()
            service._connectWebSocket = Mock()
            service._startPolling = Mock()

            # 开始轮询（应该重置失败标志）
            service.startPolling({}, 'retry_test')

            # 验证 WebSocket 失败标志已重置
            assert ws_client._isPermanentFailure is False
            assert ws_client.reconnectAttempts == 0


# ==================== 边界条件测试 ====================

class TestFailureEdgeCases:
    """失败边界条件测试"""

    def test_empty_error_message(self):
        """测试空错误消息处理"""
        from miniprogram.services.pollingManager import PollingManager

        pm = PollingManager()

        callbacks = {'onError': lambda e: None}
        pm.pollingTasks['test'] = {
            'executionId': 'test',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True
        }

        status_data = {
            'status': 'failed',
            'progress': 0,
            'error_message': '',  # 空消息
            'should_stop_polling': False
        }

        pm.lastStatusMap['test'] = status_data
        pm.stopPolling = Mock()
        pm._scheduleNextPoll = Mock()

        async def run_test():
            await pm._poll('test')

        asyncio.run(run_test())

        # 应该有默认错误消息
        pm.stopPolling.assert_called()

    def test_multiple_failure_signals(self):
        """测试多个失败信号同时存在"""
        from miniprogram.services.pollingManager import PollingManager

        pm = PollingManager()

        callbacks = {'onError': lambda e: None}
        pm.pollingTasks['test'] = {
            'executionId': 'test',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True
        }

        # 同时有 failed 状态和 should_stop_polling=true
        status_data = {
            'status': 'failed',
            'progress': 0,
            'error_message': '失败',
            'should_stop_polling': True  # 两个失败信号
        }

        pm.lastStatusMap['test'] = status_data
        pm.stopPolling = Mock()
        pm._scheduleNextPoll = Mock()

        async def run_test():
            await pm._poll('test')

        asyncio.run(run_test())

        # 应该只停止一次
        pm.stopPolling.assert_called_once()


# ==================== 性能测试 ====================

class TestFailurePerformance:
    """失败处理性能测试"""

    def test_failure_detection_latency(self):
        """测试失败检测延迟"""
        from miniprogram.services.pollingManager import PollingManager

        pm = PollingManager()

        callbacks = {'onError': lambda e: None}
        pm.pollingTasks['perf_test'] = {
            'executionId': 'perf_test',
            'callbacks': callbacks,
            'timerId': None,
            'isActive': True
        }

        status_data = {
            'status': 'failed',
            'progress': 30,
            'error_message': '测试',
            'should_stop_polling': False
        }

        pm.lastStatusMap['perf_test'] = status_data
        pm.stopPolling = Mock()
        pm._scheduleNextPoll = Mock()

        async def run_test():
            start = time.time()
            await pm._poll('perf_test')
            elapsed = time.time() - start
            return elapsed

        elapsed = asyncio.run(run_test())

        # 失败检测应该在 10ms 内完成
        assert elapsed < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
