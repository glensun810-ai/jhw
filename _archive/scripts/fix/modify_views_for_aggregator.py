#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修改 views.py 使用增量聚合结果

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加增量聚合器引用
old_imports = '''from .realtime_analyzer import get_analyzer'''

new_imports = '''from .realtime_analyzer import get_analyzer
from .incremental_aggregator import get_aggregator'''

content = content.replace(old_imports, new_imports)

# 2. 修改 get_task_status_api 返回聚合结果
old_status_api = '''    #【P0 新增】添加实时统计信息
    analyzer = get_analyzer(task_id)
    if analyzer:
        realtime_progress = analyzer.get_realtime_progress()
        response_data['realtimeStats'] = realtime_progress
        response_data['completedTasks'] = realtime_progress['completed']
        response_data['totalTasks'] = realtime_progress['total']
        response_data['brandRankings'] = realtime_progress['brand_rankings']
        response_data['sov'] = realtime_progress['sov']
        response_data['avgSentiment'] = realtime_progress['avg_sentiment']
        
        api_logger.info(f"Returning realtime stats for task {task_id}: completed={realtime_progress['completed']}, sov={realtime_progress['sov']}%")

    # 返回任务状态信息
    return jsonify(response_data), 200'''

new_status_api = '''    #【P0 新增】添加实时统计信息
    analyzer = get_analyzer(task_id)
    if analyzer:
        realtime_progress = analyzer.get_realtime_progress()
        response_data['realtimeStats'] = realtime_progress
        response_data['completedTasks'] = realtime_progress['completed']
        response_data['totalTasks'] = realtime_progress['total']
        response_data['brandRankings'] = realtime_progress['brand_rankings']
        response_data['sov'] = realtime_progress['sov']
        response_data['avgSentiment'] = realtime_progress['avg_sentiment']
        
        api_logger.info(f"Returning realtime stats for task {task_id}: completed={realtime_progress['completed']}, sov={realtime_progress['sov']}%")
    
    #【P0 新增】添加聚合结果
    aggregator = get_aggregator(task_id)
    if aggregator:
        aggregated_results = aggregator.get_aggregated_results()
        response_data['aggregatedResults'] = aggregated_results
        response_data['healthScore'] = aggregated_results['summary']['healthScore']
        response_data['detailedResults'] = aggregated_results['detailed_results']
        
        api_logger.info(f"Returning aggregated results for task {task_id}: health_score={aggregated_results['summary']['healthScore']}, total_results={aggregated_results['total_results']}")

    # 返回任务状态信息
    return jsonify(response_data), 200'''

content = content.replace(old_status_api, new_status_api)

# 3. 修改 submit_brand_test 使用增量聚合结果替代批量处理
old_batch_processing = '''            # 更新到排名分析阶段
            update_task_stage(task_id, TaskStage.RANKING_ANALYSIS, 75, "正在进行排名分析...")

            processed_results = process_and_aggregate_results_with_ai_judge(results, brand_list, brand_list[0], None, None, None)

            # 更新到信源追踪阶段
            update_task_stage(task_id, TaskStage.SOURCE_TRACING, 90, "正在进行信源追踪分析...")

            # 使用真实的信源情报处理器
            try:
                def run_async_processing():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            process_brand_source_intelligence(brand_list[0], processed_results['detailed_results'])
                        )
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_processing)
                    source_intelligence_map = future.result(timeout=30)
            except Exception as e:
                api_logger.error(f"信源情报处理失败：{e}")
                source_intelligence_map = generate_mock_source_intelligence_map(brand_list[0])'''

new_batch_processing = '''            #【P0 优化】使用增量聚合结果 (替代批量处理)
            # 更新到排名分析阶段
            update_task_stage(task_id, TaskStage.RANKING_ANALYSIS, 75, "正在进行排名分析...")

            # 从增量聚合器获取结果
            aggregator = get_aggregator(task_id)
            if aggregator:
                processed_results = aggregator.get_aggregated_results()
                api_logger.info(f"Using incremental aggregated results: health_score={processed_results['summary']['healthScore']}, total_results={processed_results['total_results']}")
            else:
                # 降级使用批量处理
                api_logger.warning("Aggregator not found, falling back to batch processing")
                processed_results = process_and_aggregate_results_with_ai_judge(results, brand_list, brand_list[0], None, None, None)

            # 更新到信源追踪阶段
            update_task_stage(task_id, TaskStage.SOURCE_TRACING, 90, "正在进行信源追踪分析...")

            # 使用增量聚合结果中的 detailed_results
            detailed_results = processed_results.get('detailed_results', [])
            
            # 使用真实的信源情报处理器
            try:
                def run_async_processing():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            process_brand_source_intelligence(brand_list[0], detailed_results)
                        )
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_processing)
                    source_intelligence_map = future.result(timeout=30)
            except Exception as e:
                api_logger.error(f"信源情报处理失败：{e}")
                source_intelligence_map = generate_mock_source_intelligence_map(brand_list[0])'''

content = content.replace(old_batch_processing, new_batch_processing)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ views.py 已修改：使用增量聚合结果')
