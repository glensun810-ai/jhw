#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修改 executor.py 集成增量聚合器

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/test_engine/executor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加增量聚合器引用
old_imports = '''from ..realtime_analyzer import get_analyzer, create_analyzer'''

new_imports = '''from ..realtime_analyzer import get_analyzer, create_analyzer
from ..incremental_aggregator import get_aggregator, create_aggregator'''

content = content.replace(old_imports, new_imports)

# 2. 在 execute_tests 方法中初始化增量聚合器
old_init = '''        #【P0 新增】创建实时分析器
        # 从 test_cases 中提取主品牌和所有品牌
        main_brand = test_cases[0].brand_name if test_cases else 'unknown'
        all_brands = list(set(case.brand_name for case in test_cases))
        analyzer = create_analyzer(execution_id, main_brand, all_brands)
        api_logger.info(f"Created RealtimeAnalyzer for execution {execution_id} - Brand: {main_brand}, All brands: {all_brands}")'''

new_init = '''        #【P0 新增】创建实时分析器
        # 从 test_cases 中提取主品牌和所有品牌
        main_brand = test_cases[0].brand_name if test_cases else 'unknown'
        all_brands = list(set(case.brand_name for case in test_cases))
        analyzer = create_analyzer(execution_id, main_brand, all_brands)
        api_logger.info(f"Created RealtimeAnalyzer for execution {execution_id} - Brand: {main_brand}, All brands: {all_brands}")
        
        #【P0 新增】创建增量聚合器
        questions = list(set(case.question for case in test_cases))
        aggregator = create_aggregator(execution_id, main_brand, all_brands, questions)
        api_logger.info(f"Created IncrementalAggregator for execution {execution_id} - Questions: {len(questions)}")'''

content = content.replace(old_init, new_init)

# 3. 在回调函数中添加增量聚合
old_callback_analysis = '''            #【P0 新增】实时分析结果
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
                api_logger.error(f"Realtime analysis failed: {e}")'''

new_callback_analysis = '''            #【P0 新增】实时分析结果
            try:
                # 准备分析数据
                analysis_data = {
                    'brand_name': task.brand_name,
                    'ai_model': task.ai_model,
                    'question': task.question,
                    'response': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                    'success': result.get('success', False)
                }
                
                # 调用实时分析器
                if analyzer:
                    analysis = analyzer.analyze_result(analysis_data)
                    api_logger.info(f"Realtime analysis completed for {task.brand_name}/{task.ai_model}: sentiment={analysis['sentiment']}, rank={analysis['rank']}")
                
                #【P0 新增】增量聚合结果
                if aggregator:
                    # 准备聚合数据
                    aggregator_data = {
                        'brand': task.brand_name,
                        'aiModel': task.ai_model,
                        'model': task.ai_model,
                        'question': task.question,
                        'question_text': task.question,
                        'response': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                        'content': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                        'status': 'success' if result.get('success', False) else 'failed'
                    }
                    
                    # 调用增量聚合器
                    aggregated = aggregator.add_result(aggregator_data)
                    api_logger.info(f"Incremental aggregation completed for {task.brand_name}/{task.ai_model}: total_results={aggregated['total_results']}, sov={aggregated['summary']['sov']}%")
            except Exception as e:
                api_logger.error(f"Realtime analysis/aggregation failed: {e}")'''

content = content.replace(old_callback_analysis, new_callback_analysis)

# 4. 在进度回调中添加聚合结果
old_progress_call = '''            #【P0 新增】获取实时统计并添加到进度中
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
            
            #【P0 新增】添加聚合结果到进度对象
            if aggregator:
                aggregated_results = aggregator.get_aggregated_results()
                current_progress.aggregated_results = aggregated_results
                current_progress.health_score = aggregated_results['summary']['healthScore']
                
                api_logger.info(f"Aggregated results: health_score={current_progress.health_score}, sov={aggregated_results['summary']['sov']}%")
            
            # Call the external progress update callback if provided
            if on_progress_update:
                on_progress_update(execution_id, current_progress)'''

content = content.replace(old_progress_call, new_progress_call)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ executor.py 已修改：集成增量聚合器')
