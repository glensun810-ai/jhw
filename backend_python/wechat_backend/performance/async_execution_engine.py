#!/usr/bin/env python3
"""
性能优化：异步并发执行引擎

功能：
1. 使用 asyncio 并发执行 AI 调用
2. 信号量控制并发数
3. 即时进度更新
4. 性能提升 60-70%

使用示例:
    from wechat_backend.performance.async_execution_engine import execute_async
    
    result = await execute_async(
        execution_id='xxx',
        questions=['问题 1', '问题 2'],
        models=['doubao', 'deepseek'],
        max_concurrent=3
    )
"""

import asyncio
import time
from typing import List, Dict, Any, Callable
from wechat_backend.logging_config import api_logger


class AsyncExecutionEngine:
    """异步执行引擎"""
    
    def __init__(self, max_concurrent: int = 3):
        """
        初始化异步执行引擎
        
        Args:
            max_concurrent: 最大并发数（默认 3）
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.results = []
        self.completed = 0
        self.total = 0
        self.progress_callback = None
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    async def execute_task(
        self,
        task_id: str,
        question: str,
        model_name: str,
        execute_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行单个任务（带并发控制）
        
        Args:
            task_id: 任务 ID
            question: 问题
            model_name: 模型名称
            execute_func: 执行函数
            **kwargs: 其他参数
        
        Returns:
            执行结果
        """
        async with self.semaphore:
            start_time = time.time()
            api_logger.info(f"[Async] 开始执行任务 {task_id}: {model_name}")
            
            try:
                # 执行任务（假设是同步函数，使用 run_in_executor）
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: execute_func(question, model_name, **kwargs)
                )
                
                elapsed = time.time() - start_time
                api_logger.info(f"[Async] 任务 {task_id} 完成，耗时：{elapsed:.2f}秒")
                
                # 更新进度
                self.completed += 1
                if self.progress_callback:
                    await self.progress_callback(
                        completed=self.completed,
                        total=self.total,
                        task_id=task_id,
                        result=result
                    )
                
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                api_logger.error(f"[Async] 任务 {task_id} 失败，耗时：{elapsed:.2f}秒，错误：{e}")
                
                # 仍然更新进度
                self.completed += 1
                if self.progress_callback:
                    await self.progress_callback(
                        completed=self.completed,
                        total=self.total,
                        task_id=task_id,
                        error=str(e)
                    )
                
                return {
                    'success': False,
                    'error': str(e),
                    'task_id': task_id
                }
    
    async def execute_all(
        self,
        tasks: List[Dict[str, Any]],
        execute_func: Callable,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        并发执行所有任务
        
        Args:
            tasks: 任务列表，每个任务包含 question, model_name 等
            execute_func: 执行函数
            **kwargs: 其他参数
        
        Returns:
            所有任务的结果
        """
        self.total = len(tasks)
        self.completed = 0
        self.results = []
        
        api_logger.info(f"[Async] 开始并发执行 {self.total} 个任务，最大并发数：{self.max_concurrent}")
        start_time = time.time()
        
        # 创建所有任务
        async_tasks = []
        for i, task in enumerate(tasks):
            task_id = task.get('task_id', f'task_{i}')
            question = task.get('question', '')
            model_name = task.get('model_name', '')
            
            async_task = self.execute_task(
                task_id=task_id,
                question=question,
                model_name=model_name,
                execute_func=execute_func,
                **kwargs
            )
            async_tasks.append(async_task)
        
        # 并发执行所有任务
        self.results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        api_logger.info(
            f"[Async] 所有任务执行完成，总耗时：{elapsed:.2f}秒，"
            f"平均每个任务：{elapsed/len(tasks):.2f}秒"
        )
        
        return self.results


async def execute_async(
    questions: List[str],
    models: List[str],
    execute_func: Callable,
    max_concurrent: int = 3,
    progress_callback: Callable = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    并发执行所有问题和模型的组合
    
    Args:
        questions: 问题列表
        models: 模型列表
        execute_func: 执行函数
        max_concurrent: 最大并发数
        progress_callback: 进度回调函数
        **kwargs: 其他参数
    
    Returns:
        所有执行结果
    
    Example:
        results = await execute_async(
            questions=['问题 1', '问题 2', '问题 3'],
            models=['doubao', 'deepseek'],
            execute_func=call_ai_api,
            max_concurrent=3
        )
    """
    # 创建任务列表
    tasks = []
    for q_idx, question in enumerate(questions):
        for m_idx, model in enumerate(models):
            tasks.append({
                'task_id': f'q{q_idx}_m{m_idx}',
                'question': question,
                'model_name': model,
                'question_index': q_idx,
                'model_index': m_idx
            })
    
    # 创建执行引擎
    engine = AsyncExecutionEngine(max_concurrent=max_concurrent)
    engine.set_progress_callback(progress_callback)
    
    # 执行所有任务
    results = await engine.execute_all(
        tasks=tasks,
        execute_func=execute_func,
        **kwargs
    )
    
    return results


def calculate_speedup(
    sync_time: float,
    async_time: float,
    num_tasks: int
) -> Dict[str, float]:
    """
    计算性能提升
    
    Args:
        sync_time: 同步执行时间
        async_time: 异步执行时间
        num_tasks: 任务数量
    
    Returns:
        性能提升统计
    """
    return {
        'sync_time': sync_time,
        'async_time': async_time,
        'speedup_ratio': sync_time / async_time if async_time > 0 else 0,
        'time_saved': sync_time - async_time,
        'time_saved_percent': ((sync_time - async_time) / sync_time * 100) if sync_time > 0 else 0,
        'avg_task_time_sync': sync_time / num_tasks if num_tasks > 0 else 0,
        'avg_task_time_async': async_time / num_tasks if num_tasks > 0 else 0
    }


if __name__ == '__main__':
    # 测试异步执行引擎
    import time
    
    print("="*60)
    print("性能优化：异步并发执行引擎测试")
    print("="*60)
    print()
    
    # 模拟同步 AI 调用（耗时 2 秒）
    def mock_ai_call(question, model, **kwargs):
        time.sleep(2)  # 模拟 AI 调用延迟
        return {
            'question': question,
            'model': model,
            'success': True,
            'answer': f'这是 {model} 对 "{question}" 的回答'
        }
    
    # 进度回调
    async def on_progress(completed, total, task_id, **kwargs):
        print(f"[进度] {completed}/{total} ({completed/total*100:.0f}%) - 任务 {task_id}")
    
    # 测试参数
    questions = ['问题 1', '问题 2', '问题 3']
    models = ['doubao', 'deepseek']
    
    print(f"测试场景：{len(questions)} 个问题 × {len(models)} 个模型 = {len(questions)*len(models)} 次 AI 调用")
    print()
    
    # 同步执行（模拟）
    print("📊 同步执行（模拟）:")
    sync_start = time.time()
    for q in questions:
        for m in models:
            mock_ai_call(q, m)
    sync_time = time.time() - sync_start
    print(f"同步执行耗时：{sync_time:.2f}秒")
    print()
    
    # 异步执行
    print("🚀 异步并发执行（最大并发数=3）:")
    async_start = time.time()
    results = asyncio.run(execute_async(
        questions=questions,
        models=models,
        execute_func=mock_ai_call,
        max_concurrent=3,
        progress_callback=on_progress
    ))
    async_time = time.time() - async_start
    print(f"异步执行耗时：{async_time:.2f}秒")
    print()
    
    # 性能对比
    print("📈 性能对比:")
    stats = calculate_speedup(sync_time, async_time, len(questions)*len(models))
    print(f"  同步耗时：{stats['sync_time']:.2f}秒")
    print(f"  异步耗时：{stats['async_time']:.2f}秒")
    print(f"  性能提升：{stats['speedup_ratio']:.1f}x")
    print(f"  时间节省：{stats['time_saved']:.2f}秒 ({stats['time_saved_percent']:.0f}%)")
    print()
    print("✅ 测试完成")
