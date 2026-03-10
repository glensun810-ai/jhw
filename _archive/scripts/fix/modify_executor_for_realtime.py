#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修改 executor.py 集成实时分析器

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/test_engine/executor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加实时分析器引用
old_imports = '''from .progress_tracker import ProgressTracker, TestProgress
from ..logging_config import api_logger
from ..database import save_test_record'''

new_imports = '''from .progress_tracker import ProgressTracker, TestProgress
from ..logging_config import api_logger
from ..database import save_test_record
from ..realtime_analyzer import get_analyzer, create_analyzer'''

content = content.replace(old_imports, new_imports)

# 2. 在 execute_tests 方法中初始化分析器
old_init = '''        # Create progress tracking for this execution
        progress = self.progress_tracker.create_execution(
            execution_id=execution_id,
            total_tests=total_tests,
            metadata={
                'start_time': datetime.now().isoformat(),
                'total_tests': total_tests,
                'api_key_provided': bool(api_key)
            }
        )'''

new_init = '''        # Create progress tracking for this execution
        progress = self.progress_tracker.create_execution(
            execution_id=execution_id,
            total_tests=total_tests,
            metadata={
                'start_time': datetime.now().isoformat(),
                'total_tests': total_tests,
                'api_key_provided': bool(api_key)
            }
        )
        
        #【P0 新增】创建实时分析器
        # 从 test_cases 中提取主品牌和所有品牌
        main_brand = test_cases[0].brand_name if test_cases else 'unknown'
        all_brands = list(set(case.brand_name for case in test_cases))
        analyzer = create_analyzer(execution_id, main_brand, all_brands)
        api_logger.info(f"Created RealtimeAnalyzer for execution {execution_id} - Brand: {main_brand}, All brands: {all_brands}")'''

content = content.replace(old_init, new_init)

# 3. 修改回调函数，添加实时分析
old_callback = '''        # Define callback for progress updates and checkpoint saving
        def progress_callback(task: TestTask, result: Dict[str, Any]):
            if result.get('success', False):
                self.progress_tracker.update_completed(execution_id, result)
            
            # 实现分批次保存：每完成一个测试（无论成功或失败）都立即保存到数据库
            try:
                # 提取模型名称，将其格式化为一致的格式
                model_name = task.ai_model'''

new_callback = '''        # Define callback for progress updates and checkpoint saving
        def progress_callback(task: TestTask, result: Dict[str, Any]):
            if result.get('success', False):
                self.progress_tracker.update_completed(execution_id, result)
            
            #【P0 新增】实时分析结果
            try:
                # 准备分析数据
                analysis_data = {
                    'brand_name': task.brand_name,
                    'ai_model': task.ai_model,
                    'question': task.question,
                    'response': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                    'success': result.get('success', False)
                }
                
                # 调用分析器
                if analyzer:
                    analysis = analyzer.analyze_result(analysis_data)
                    api_logger.info(f"Realtime analysis completed for {task.brand_name}/{task.ai_model}: sentiment={analysis['sentiment']}, rank={analysis['rank']}")
            except Exception as e:
                api_logger.error(f"Realtime analysis failed: {e}")
            
            # 实现分批次保存：每完成一个测试（无论成功或失败）都立即保存到数据库
            try:
                # 提取模型名称，将其格式化为一致的格式
                model_name = task.ai_model'''

content = content.replace(old_callback, new_callback)

# 4. 在进度回调中获取实时统计
old_progress_call = '''            # Call the external progress update callback if provided
            current_progress = self.progress_tracker.get_progress(execution_id)
            if on_progress_update:
                on_progress_update(execution_id, current_progress)'''

new_progress_call = '''            #【P0 新增】获取实时统计并添加到进度中
            current_progress = self.progress_tracker.get_progress(execution_id)
            
            if analyzer:
                realtime_progress = analyzer.get_realtime_progress()
                # 将实时统计添加到进度对象中
                current_progress.realtime_stats = realtime_progress
                current_progress.brand_rankings = realtime_progress['brand_rankings']
                current_progress.sov = realtime_progress['sov']
                current_progress.avg_sentiment = realtime_progress['avg_sentiment']
                
                api_logger.info(f"Realtime progress: completed={current_progress.completed_tests}/{current_progress.total_tests}, sov={current_progress.sov}%, brands={len(current_progress.brand_rankings)}")
            
            # Call the external progress update callback if provided
            if on_progress_update:
                on_progress_update(execution_id, current_progress)'''

content = content.replace(old_progress_call, new_progress_call)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ executor.py 已修改：集成实时分析器')
