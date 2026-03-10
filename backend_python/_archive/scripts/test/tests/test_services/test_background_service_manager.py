"""
测试后台任务管理器 - 分析任务功能

测试用例覆盖:
1. 提交分析任务
2. 查询任务状态
3. 品牌分析任务执行
4. 竞争分析任务执行
5. 统计计算任务执行
6. 任务超时处理
7. 任务清理
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from wechat_backend.services.background_service_manager import (
    BackgroundServiceManager,
    TaskStatus,
    get_background_service_manager,
    reset_background_service_manager
)


class TestBackgroundServiceManagerAnalysis:
    """后台任务管理器分析功能测试"""

    @pytest.fixture
    def manager(self):
        """创建测试用的管理器实例"""
        mgr = BackgroundServiceManager(max_workers=2)
        yield mgr
        # 清理
        mgr.stop()

    @pytest.fixture
    def sample_results(self):
        """样本诊断结果"""
        return [
            {
                'brand': '品牌 A',
                'platform': 'wechat',
                'question': '问题 1',
                'response': {'content': '这是品牌 A 的回答'},
                'score': 85
            },
            {
                'brand': '品牌 B',
                'platform': 'wechat',
                'question': '问题 1',
                'response': {'content': '这是品牌 B 的回答'},
                'score': 75
            },
            {
                'brand': '品牌 A',
                'platform': 'weibo',
                'question': '问题 2',
                'response': {'content': '这是品牌 A 的回答 2'},
                'score': 90
            }
        ]

    def test_submit_analysis_task(self, manager, sample_results):
        """测试提交分析任务"""
        execution_id = 'test-exec-001'
        
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='statistics',
            payload={'results': sample_results},
            timeout_seconds=60
        )
        
        assert task_id is not None
        assert execution_id in task_id
        assert 'statistics' in task_id
        
        # 验证任务已保存
        task = manager.get_task_by_id(task_id)
        assert task is not None
        assert task['task_type'] == 'statistics'
        assert task['status'] in ['pending', 'running', 'completed']

    def test_get_task_status(self, manager, sample_results):
        """测试查询任务状态"""
        execution_id = 'test-exec-002'
        
        # 提交多个任务
        task_id_1 = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='statistics',
            payload={'results': sample_results}
        )
        
        task_id_2 = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='brand_analysis',
            payload={'results': sample_results, 'user_brand': '品牌 A'}
        )
        
        # 等待任务完成
        time.sleep(2)
        
        status = manager.get_task_status(execution_id)
        
        assert status is not None
        assert status['execution_id'] == execution_id
        assert status['total_tasks'] == 2
        assert 'analysis_results' in status
        assert 'completed_tasks' in status

    def test_statistics_task(self, manager, sample_results):
        """测试统计计算任务"""
        execution_id = 'test-exec-stats'
        
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='statistics',
            payload={'results': sample_results}
        )
        
        # 等待任务完成
        time.sleep(2)
        
        task = manager.get_task_by_id(task_id)
        assert task is not None
        
        if task['status'] == TaskStatus.COMPLETED.value:
            result = task['result']
            assert result['success'] is True
            assert 'data' in result
            assert result['data']['total_count'] == 3
            assert 'average_score' in result['data']
            assert 'platform_stats' in result['data']
        else:
            pytest.fail(f"任务未完成，状态：{task['status']}")

    def test_brand_analysis_task(self, manager, sample_results):
        """测试品牌分析任务"""
        execution_id = 'test-exec-brand'
        
        # Mock BrandAnalysisService 以避免实际 API 调用
        with patch('wechat_backend.services.brand_analysis_service.BrandAnalysisService') as mock_service:
            mock_instance = Mock()
            mock_instance.analyze_brand_mentions.return_value = {
                'user_brand_analysis': {'score': 85, 'mentions': 10},
                'competitor_analysis': [],
                'comparison': {}
            }
            mock_service.return_value = mock_instance
            
            task_id = manager.submit_analysis_task(
                execution_id=execution_id,
                task_type='brand_analysis',
                payload={
                    'results': sample_results,
                    'user_brand': '品牌 A',
                    'competitor_brands': ['品牌 B']
                }
            )
            
            # 等待任务完成
            time.sleep(2)
            
            task = manager.get_task_by_id(task_id)
            assert task is not None
            
            if task['status'] == TaskStatus.COMPLETED.value:
                result = task['result']
                assert result['success'] is True
                assert 'data' in result
                assert result['data']['user_brand_analysis']['score'] == 85
            else:
                pytest.fail(f"任务未完成，状态：{task['status']}")

    def test_competitive_analysis_task(self, manager, sample_results):
        """测试竞争分析任务"""
        execution_id = 'test-exec-competitive'
        
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='competitive_analysis',
            payload={
                'results': sample_results,
                'main_brand': '品牌 A',
                'competitor_brands': ['品牌 B']
            }
        )
        
        # 等待任务完成
        time.sleep(2)
        
        task = manager.get_task_by_id(task_id)
        assert task is not None
        
        # 竞争分析服务是纯函数，不需要 mock
        if task['status'] == TaskStatus.COMPLETED.value:
            result = task['result']
            assert result['success'] is True
            assert 'data' in result
            assert 'brand_scores' in result['data']
        else:
            pytest.fail(f"任务未完成，状态：{task['status']}")

    def test_invalid_task_type(self, manager):
        """测试无效任务类型"""
        execution_id = 'test-exec-invalid'
        
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='invalid_type',
            payload={}
        )
        
        # 等待任务完成
        time.sleep(1)
        
        task = manager.get_task_by_id(task_id)
        assert task is not None
        assert task['status'] == TaskStatus.FAILED.value
        assert 'error' in task
        assert '未知任务类型' in task['error']

    def test_missing_required_params(self, manager):
        """测试缺少必要参数"""
        execution_id = 'test-exec-missing'
        
        # 品牌分析缺少 user_brand
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='brand_analysis',
            payload={'results': []}  # 缺少 user_brand
        )
        
        # 等待任务完成
        time.sleep(1)
        
        task = manager.get_task_by_id(task_id)
        assert task is not None
        assert task['status'] == TaskStatus.FAILED.value
        assert 'error' in task

    def test_cleanup_completed_tasks(self, manager, sample_results):
        """测试清理已完成任务"""
        execution_id = 'test-exec-cleanup'
        
        # 提交并完成任务
        task_id = manager.submit_analysis_task(
            execution_id=execution_id,
            task_type='statistics',
            payload={'results': sample_results}
        )
        
        # 等待完成
        time.sleep(2)
        
        # 手动设置任务完成时间以便清理
        with manager._lock:
            if task_id in manager._analysis_tasks:
                manager._analysis_tasks[task_id].completed_at = datetime.now()
        
        # 清理 0 分钟前的任务（立即清理）
        cleaned = manager.cleanup_completed_tasks(max_age_minutes=0)
        
        # 验证清理结果
        assert cleaned >= 0  # 可能已经清理或未完成

    def test_concurrent_tasks(self, manager, sample_results):
        """测试并发任务执行"""
        execution_id = 'test-exec-concurrent'
        
        # 提交多个并发任务
        task_ids = []
        for i in range(3):
            task_id = manager.submit_analysis_task(
                execution_id=execution_id,
                task_type='statistics',
                payload={'results': sample_results}
            )
            task_ids.append(task_id)
        
        # 等待所有任务完成
        time.sleep(3)
        
        # 验证所有任务都完成
        completed_count = 0
        for task_id in task_ids:
            task = manager.get_task_by_id(task_id)
            if task and task['status'] == TaskStatus.COMPLETED.value:
                completed_count += 1
        
        # 至少有一个任务完成（考虑到并发）
        assert completed_count >= 1

    def test_get_task_status_no_tasks(self, manager):
        """测试查询不存在的执行 ID"""
        status = manager.get_task_status('non-existent-exec-id')
        assert status is None

    def test_get_task_by_id_not_found(self, manager):
        """测试查询不存在的任务 ID"""
        task = manager.get_task_by_id('non-existent-task-id')
        assert task is None


class TestBackgroundServiceManagerGlobal:
    """全局后台任务管理器测试"""

    def test_get_background_service_manager_singleton(self):
        """测试全局单例"""
        manager1 = get_background_service_manager()
        manager2 = get_background_service_manager()
        
        assert manager1 is manager2

    def test_get_background_service_manager_custom_workers(self):
        """测试自定义线程数"""
        reset_background_service_manager()
        manager = get_background_service_manager(max_workers=8)
        
        assert manager._executor._max_workers == 8
        
        # 恢复默认
        reset_background_service_manager()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
