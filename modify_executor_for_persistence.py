#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修改 executor.py 集成持久化服务

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/test_engine/executor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加持久化服务引用
old_imports = '''from ..incremental_aggregator import get_aggregator, create_aggregator'''

new_imports = '''from ..incremental_aggregator import get_aggregator, create_aggregator
from ..realtime_persistence import get_persistence_service, create_persistence_service, remove_persistence_service'''

content = content.replace(old_imports, new_imports)

# 2. 在 execute_tests 方法中初始化持久化服务
old_init = '''        #【P0 新增】创建增量聚合器
        questions = list(set(case.question for case in test_cases))
        aggregator = create_aggregator(execution_id, main_brand, all_brands, questions)
        api_logger.info(f"Created IncrementalAggregator for execution {execution_id} - Questions: {len(questions)}")'''

new_init = '''        #【P0 新增】创建增量聚合器
        questions = list(set(case.question for case in test_cases))
        aggregator = create_aggregator(execution_id, main_brand, all_brands, questions)
        api_logger.info(f"Created IncrementalAggregator for execution {execution_id} - Questions: {len(questions)}")
        
        #【阶段 3】创建持久化服务
        persistence_service = create_persistence_service(execution_id, user_openid)
        api_logger.info(f"Created RealtimePersistence for execution {execution_id}")'''

content = content.replace(old_init, new_init)

# 3. 在回调函数中添加持久化保存
old_callback_save = '''                #【P0 新增】增量聚合结果
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

new_callback_save = '''                #【P0 新增】增量聚合结果
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
                
                #【阶段 3】实时持久化保存
                if persistence_service:
                    # 准备持久化数据
                    persistence_data = {
                        'brand': task.brand_name,
                        'aiModel': task.ai_model,
                        'model': task.ai_model,
                        'question': task.question,
                        'question_text': task.question,
                        'response': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                        'content': result.get('result', {}).get('content', '') if isinstance(result.get('result'), dict) else '',
                        'status': 'success' if result.get('success', False) else 'failed',
                        'error': result.get('error', '') if not result.get('success', False) else ''
                    }
                    
                    # 保存到数据库
                    saved = persistence_service.save_task_result(persistence_data)
                    if saved:
                        api_logger.info(f"Persisted task result: {task.brand_name}/{task.ai_model}/{task.question}")
            except Exception as e:
                api_logger.error(f"Realtime analysis/aggregation/persistence failed: {e}")'''

content = content.replace(old_callback_save, new_callback_save)

# 4. 在进度回调中添加聚合结果持久化
old_progress_call = '''            #【P0 新增】添加聚合结果到进度对象
            if aggregator:
                aggregated_results = aggregator.get_aggregated_results()
                current_progress.aggregated_results = aggregated_results
                current_progress.health_score = aggregated_results['summary']['healthScore']
                
                api_logger.info(f"Aggregated results: health_score={current_progress.health_score}, sov={aggregated_results['summary']['sov']}%")
            
            # Call the external progress update callback if provided
            if on_progress_update:
                on_progress_update(execution_id, current_progress)'''

new_progress_call = '''            #【P0 新增】添加聚合结果到进度对象
            if aggregator:
                aggregated_results = aggregator.get_aggregated_results()
                current_progress.aggregated_results = aggregated_results
                current_progress.health_score = aggregated_results['summary']['healthScore']
                
                #【阶段 3】定期保存聚合结果 (每保存 3 个任务保存一次聚合结果)
                if persistence_service and current_progress.completed_tests % 3 == 0:
                    persistence_service.save_aggregated_results(aggregated_results)
                    persistence_service.save_brand_rankings(aggregated_results['brand_rankings'])
                    api_logger.info(f"Persisted aggregated results: health_score={aggregated_results['summary']['healthScore']}")
                
                api_logger.info(f"Aggregated results: health_score={current_progress.health_score}, sov={aggregated_results['summary']['sov']}%")
            
            # Call the external progress update callback if provided
            if on_progress_update:
                on_progress_update(execution_id, current_progress)'''

content = content.replace(old_progress_call, new_progress_call)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ executor.py 已修改：集成持久化服务')
