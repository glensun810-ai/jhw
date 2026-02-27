"""
并发场景集成测试

测试覆盖：
1. 并发诊断任务
2. 并发状态轮询
3. 数据库并发写入
4. 资源竞争处理

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import asyncio
import random


class TestConcurrentScenarios:
    """并发场景测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_diagnosis_tasks(
        self,
        test_db_path,
        sample_diagnosis_config
    ):
        """测试并发执行多个诊断任务"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        async def run_diagnosis(task_id):
            exec_id = f"concurrent_test_{task_id}"
            
            # 使用随机延迟的 AI 适配器
            class RandomDelayAdapter:
                async def send_prompt(self, brand, question, model):
                    delay = random.uniform(0.05, 0.2)
                    await asyncio.sleep(delay)
                    return {'content': f'Response for {brand}', 'latency_ms': int(delay*1000)}
            
            service = DiagnosisService(
                db_path=test_db_path,
                ai_adapter=RandomDelayAdapter()
            )
            
            await service.start_diagnosis(
                execution_id=exec_id,
                config=sample_diagnosis_config
            )
            
            # 等待完成
            max_wait = 10
            waited = 0
            while waited < max_wait:
                status = await service.get_status(exec_id)
                if status['should_stop_polling']:
                    break
                await asyncio.sleep(0.5)
                waited += 0.5
            
            return exec_id
        
        # 启动 10 个并发任务
        tasks = [run_diagnosis(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有任务完成
        assert len(results) == 10
        
        # 验证没有任务卡死
        service = DiagnosisService(db_path=test_db_path)
        for exec_id in results:
            status = await service.get_status(exec_id)
            assert status['should_stop_polling'] is True
            assert status['status'] in ['completed', 'partial_success']
    
    @pytest.mark.asyncio
    async def test_concurrent_status_polling(
        self,
        test_db_path,
        setup_completed_diagnosis
    ):
        """测试并发状态轮询"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        service = DiagnosisService(db_path=test_db_path)
        exec_id = setup_completed_diagnosis['execution_id']
        
        async def poll_status():
            results = []
            for _ in range(10):
                status = await service.get_status(exec_id)
                results.append(status)
                await asyncio.sleep(0.05)
            return results
        
        # 10 个并发轮询
        tasks = [poll_status() for _ in range(5)]
        all_results = await asyncio.gather(*tasks)
        
        # 验证所有轮询结果一致
        for results in all_results:
            for status in results:
                assert status['execution_id'] == exec_id
                assert status['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_database_concurrent_writes(
        self,
        test_db_path,
        sample_execution_id
    ):
        """测试数据库并发写入"""
        
        from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
        from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
        
        repo = DiagnosisResultRepository(test_db_path)
        
        async def write_result(idx):
            result = DiagnosisResult(
                report_id=1,
                execution_id=sample_execution_id,
                brand=f"品牌{idx}",
                question="测试问题",
                model="deepseek",
                response={'content': f'响应{idx}'}
            )
            return repo.create(result)
        
        # 50 个并发写入
        tasks = [write_result(i) for i in range(50)]
        ids = await asyncio.gather(*tasks)
        
        # 验证所有写入成功
        assert len(ids) == 50
        assert len(set(ids)) == 50  # 所有 ID 唯一
        
        # 验证数据库中有 50 条记录
        results = repo.get_by_execution_id(sample_execution_id)
        assert len(results) == 50
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(
        self,
        test_db_path,
        sample_execution_id,
        sample_diagnosis_config
    ):
        """测试并发状态更新"""
        
        from wechat_backend.v2.services.diagnosis_service import DiagnosisService
        
        service = DiagnosisService(db_path=test_db_path)
        
        # 创建任务
        repo = service.diagnosis_repo
        repo.create_report(
            execution_id=sample_execution_id,
            user_id='test_user',
            brand_name='测试品牌',
            config=sample_diagnosis_config
        )
        
        # 并发更新状态
        async def update_status(status, progress):
            await service.update_status(
                sample_execution_id,
                status=status,
                progress=progress
            )
        
        tasks = [
            update_status('initializing', 10),
            update_status('ai_fetching', 30),
            update_status('ai_fetching', 50),
            update_status('analyzing', 70),
            update_status('analyzing', 90),
        ]
        
        await asyncio.gather(*tasks)
        
        # 验证最终状态
        final_status = await service.get_status(sample_execution_id)
        assert final_status['progress'] >= 10
