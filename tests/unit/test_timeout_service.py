"""
超时管理服务单元测试

测试覆盖率目标：> 90%

测试范围:
1. TimeoutManager 基本功能测试
2. 计时器启动、取消测试
3. 超时回调测试
4. 多线程安全测试
5. 边界条件测试

作者：系统架构组
日期：2026-02-27
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from threading import Thread
from wechat_backend.v2.services.timeout_service import TimeoutManager
from wechat_backend.v2.exceptions import DiagnosisTimeoutError
from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine


# ==================== Fixture ====================

@pytest.fixture
def timeout_manager():
    """创建超时管理器实例"""
    return TimeoutManager()


# ==================== 基本功能测试 ====================

class TestTimeoutManagerBasic:
    """超时管理器基本功能测试"""
    
    def test_init(self, timeout_manager):
        """测试初始化"""
        assert timeout_manager.MAX_EXECUTION_TIME == 600
        assert timeout_manager.get_active_timers_count() == 0
    
    def test_start_timer(self, timeout_manager):
        """测试启动计时器"""
        callback_called = False
        
        def on_timeout(execution_id):
            nonlocal callback_called
            callback_called = True
            assert execution_id == "test-123"
        
        # 启动 1 秒超时（用于测试）
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=1)
        
        assert timeout_manager.is_timer_active("test-123")
        assert timeout_manager.get_active_timers_count() == 1
        
        # 等待超时
        time.sleep(1.5)
        
        assert callback_called
        assert not timeout_manager.is_timer_active("test-123")
    
    def test_start_timer_with_custom_timeout(self, timeout_manager):
        """测试自定义超时时间"""
        callback_called = False
        
        def on_timeout(execution_id):
            nonlocal callback_called
            callback_called = True
        
        # 启动 2 秒超时
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=2)
        
        assert timeout_manager.is_timer_active("test-123")
        
        # 1 秒后检查，应该还活跃
        time.sleep(1)
        assert timeout_manager.is_timer_active("test-123")
        
        # 再等 1.5 秒，应该超时
        time.sleep(1.5)
        
        assert callback_called
        assert not timeout_manager.is_timer_active("test-123")
    
    def test_start_timer_with_default_timeout(self, timeout_manager):
        """测试使用默认超时时间"""
        def on_timeout(execution_id):
            pass
        
        timeout_manager.start_timer("test-123", on_timeout)
        
        # 应该使用默认的 600 秒
        remaining = timeout_manager.get_remaining_time("test-123")
        assert 590 <= remaining <= 600


# ==================== 取消计时器测试 ====================

class TestCancelTimer:
    """取消计时器测试"""
    
    def test_cancel_timer(self, timeout_manager):
        """测试取消计时器"""
        callback_called = False
        
        def on_timeout(execution_id):
            nonlocal callback_called
            callback_called = True
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=2)
        assert timeout_manager.is_timer_active("test-123")
        
        # 取消计时器
        result = timeout_manager.cancel_timer("test-123")
        assert result is True
        assert not timeout_manager.is_timer_active("test-123")
        assert timeout_manager.get_active_timers_count() == 0
        
        # 等待原超时时间
        time.sleep(2.5)
        
        # 回调不应被调用
        assert not callback_called
    
    def test_cancel_nonexistent_timer(self, timeout_manager):
        """测试取消不存在的计时器"""
        result = timeout_manager.cancel_timer("nonexistent-123")
        assert result is False
    
    def test_cancel_twice(self, timeout_manager):
        """测试重复取消计时器"""
        def on_timeout(execution_id):
            pass
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=5)
        
        # 第一次取消
        result1 = timeout_manager.cancel_timer("test-123")
        assert result1 is True
        
        # 第二次取消
        result2 = timeout_manager.cancel_timer("test-123")
        assert result2 is False


# ==================== 重复计时器测试 ====================

class TestDuplicateTimer:
    """重复计时器测试"""
    
    def test_duplicate_timer_raises_error(self, timeout_manager):
        """测试重复启动同一任务的计时器"""
        def on_timeout(execution_id):
            pass
        
        timeout_manager.start_timer("test-123", on_timeout)
        
        with pytest.raises(ValueError, match="Timer already exists"):
            timeout_manager.start_timer("test-123", on_timeout)
    
    def test_duplicate_timer_after_cleanup(self, timeout_manager):
        """测试清理后可以重新启动"""
        callback1_called = False
        callback2_called = False
        
        def on_timeout1(execution_id):
            nonlocal callback1_called
            callback1_called = True
        
        def on_timeout2(execution_id):
            nonlocal callback2_called
            callback2_called = True
        
        # 启动第一个计时器
        timeout_manager.start_timer("test-123", on_timeout1, timeout_seconds=1)
        
        # 等待超时
        time.sleep(1.5)
        
        assert callback1_called
        assert not timeout_manager.is_timer_active("test-123")
        
        # 现在可以重新启动
        timeout_manager.start_timer("test-123", on_timeout2, timeout_seconds=1)
        assert timeout_manager.is_timer_active("test-123")
        
        # 等待超时
        time.sleep(1.5)
        
        assert callback2_called


# ==================== 剩余时间测试 ====================

class TestRemainingTime:
    """剩余时间测试"""
    
    def test_get_remaining_time(self, timeout_manager):
        """测试获取剩余时间"""
        def on_timeout(execution_id):
            pass
        
        # 使用 10 秒超时
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=10)
        
        remaining = timeout_manager.get_remaining_time("test-123")
        # 应该接近 10 秒（默认 MAX_EXECUTION_TIME 是 600，但这里用的是 10）
        assert 8 <= remaining <= 10  # 允许少量时间误差
        
        # 等待 2 秒
        time.sleep(2)
        
        remaining2 = timeout_manager.get_remaining_time("test-123")
        assert remaining2 < remaining
        assert remaining2 >= 6  # 大约剩 8 秒
    
    def test_get_remaining_time_nonexistent(self, timeout_manager):
        """测试获取不存在的计时器的剩余时间"""
        remaining = timeout_manager.get_remaining_time("nonexistent-123")
        assert remaining == 0
    
    def test_get_remaining_time_after_timeout(self, timeout_manager):
        """测试超时后获取剩余时间"""
        callback_called = False
        
        def on_timeout(execution_id):
            nonlocal callback_called
            callback_called = True
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=1)
        time.sleep(1.5)
        
        assert callback_called
        remaining = timeout_manager.get_remaining_time("test-123")
        assert remaining == 0


# ==================== 多计时器测试 ====================

class TestMultipleTimers:
    """多计时器测试"""
    
    def test_multiple_timers_concurrent(self, timeout_manager):
        """测试多个计时器同时运行"""
        results = []
        
        def create_callback(task_id):
            def callback(execution_id):
                results.append(task_id)
            return callback
        
        # 启动三个不同超时时间的计时器
        timeout_manager.start_timer("task1", create_callback("task1"), timeout_seconds=1)
        timeout_manager.start_timer("task2", create_callback("task2"), timeout_seconds=2)
        timeout_manager.start_timer("task3", create_callback("task3"), timeout_seconds=3)
        
        assert timeout_manager.get_active_timers_count() == 3
        
        # 等待所有超时
        time.sleep(4)
        
        # 所有回调都应该被调用
        assert sorted(results) == ["task1", "task2", "task3"]
        assert timeout_manager.get_active_timers_count() == 0
    
    def test_cancel_one_of_multiple_timers(self, timeout_manager):
        """测试取消多个计时器中的一个"""
        results = []
        
        def create_callback(task_id):
            def callback(execution_id):
                results.append(task_id)
            return callback
        
        # 启动三个计时器
        timeout_manager.start_timer("task1", create_callback("task1"), timeout_seconds=1)
        timeout_manager.start_timer("task2", create_callback("task2"), timeout_seconds=2)
        timeout_manager.start_timer("task3", create_callback("task3"), timeout_seconds=3)
        
        # 取消 task2
        timeout_manager.cancel_timer("task2")
        
        assert timeout_manager.get_active_timers_count() == 2
        
        # 等待所有超时
        time.sleep(4)
        
        # 只有 task1 和 task3 应该被调用
        assert sorted(results) == ["task1", "task3"]


# ==================== 取消所有计时器测试 ====================

class TestCancelAllTimers:
    """取消所有计时器测试"""
    
    def test_cancel_all_timers(self, timeout_manager):
        """测试取消所有计时器"""
        callback_count = [0]
        
        def on_timeout(execution_id):
            callback_count[0] += 1
        
        # 启动 5 个计时器
        for i in range(5):
            timeout_manager.start_timer(f"task{i}", on_timeout, timeout_seconds=2)
        
        assert timeout_manager.get_active_timers_count() == 5
        
        # 取消所有
        count = timeout_manager.cancel_all_timers()
        assert count == 5
        assert timeout_manager.get_active_timers_count() == 0
        
        # 等待超时时间
        time.sleep(3)
        
        # 所有回调都不应被调用
        assert callback_count[0] == 0


# ==================== 线程安全测试 ====================

class TestThreadSafety:
    """线程安全测试"""
    
    def test_concurrent_start_timers(self, timeout_manager):
        """测试并发启动计时器"""
        errors = []
        
        def start_timer(task_id):
            try:
                timeout_manager.start_timer(f"task{task_id}", lambda eid: None, timeout_seconds=5)
            except Exception as e:
                errors.append(e)
        
        # 并发启动 10 个计时器
        threads = [Thread(target=start_timer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert timeout_manager.get_active_timers_count() == 10
    
    def test_concurrent_cancel_timers(self, timeout_manager):
        """测试并发取消计时器"""
        # 先启动 10 个计时器
        for i in range(10):
            timeout_manager.start_timer(f"task{i}", lambda eid: None, timeout_seconds=10)
        
        errors = []
        
        def cancel_timer(task_id):
            try:
                timeout_manager.cancel_timer(f"task{task_id}")
            except Exception as e:
                errors.append(e)
        
        # 并发取消所有计时器
        threads = [Thread(target=cancel_timer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert timeout_manager.get_active_timers_count() == 0


# ==================== 异常处理测试 ====================

class TestExceptionHandling:
    """异常处理测试"""
    
    def test_timeout_callback_exception(self, timeout_manager, caplog):
        """测试超时回调中的异常处理"""
        def on_timeout(execution_id):
            raise Exception("Test exception in callback")
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=1)
        time.sleep(1.5)
        
        # 应该记录错误日志
        assert "timeout_handler_error" in caplog.text
    
    def test_invalid_callback_type(self, timeout_manager):
        """测试无效的回调类型"""
        with pytest.raises(TypeError, match="on_timeout must be a callable"):
            timeout_manager.start_timer("test-123", "not_a_callable")  # type: ignore


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    @patch.object(DiagnosisStateMachine, '__init__', return_value=None)
    def test_timeout_handler_integration(self, mock_sm_init, timeout_manager):
        """测试超时处理器与状态机的集成"""
        # Mock 状态机
        mock_state_machine = MagicMock()
        mock_state_machine.get_progress.return_value = 50
        
        # 让 DiagnosisStateMachine() 返回 mock
        with patch.object(DiagnosisStateMachine, 'transition', return_value=True):
            with patch.object(DiagnosisStateMachine, 'get_progress', return_value=50):
                from wechat_backend.v2.services.diagnosis_service import DiagnosisService
                service = DiagnosisService()
                
                # 启动超时
                service.timeout_manager.start_timer(
                    "test-123",
                    service._handle_timeout,
                    timeout_seconds=1
                )
                
                # 等待超时
                time.sleep(1.5)
                
                # 验证状态机被创建
                assert mock_sm_init.called


# ==================== 清理测试 ====================

class TestCleanup:
    """清理测试"""
    
    def test_cleanup_on_timeout(self, timeout_manager):
        """测试超时后自动清理"""
        callback_called = False
        
        def on_timeout(execution_id):
            nonlocal callback_called
            callback_called = True
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=1)
        time.sleep(1.5)
        
        assert callback_called
        assert not timeout_manager.is_timer_active("test-123")
        assert timeout_manager.get_remaining_time("test-123") == 0
    
    def test_cleanup_on_cancel(self, timeout_manager):
        """测试取消后自动清理"""
        def on_timeout(execution_id):
            pass
        
        timeout_manager.start_timer("test-123", on_timeout, timeout_seconds=10)
        assert timeout_manager.is_timer_active("test-123")
        
        timeout_manager.cancel_timer("test-123")
        
        assert not timeout_manager.is_timer_active("test-123")
        assert timeout_manager.get_remaining_time("test-123") == 0


# ==================== 运行测试 ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=wechat_backend.v2.services.timeout_service', '--cov-report=html'])
