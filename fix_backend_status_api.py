#!/usr/bin/env python3
"""
修复后端 /test/status API，返回完整的 results_summary 数据
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复后端 API 返回数据
old_api = '''# 尝试从全局存储获取任务状态
    if task_id in execution_store:
        task_status = execution_store[task_id]

        # 按照 API 契约返回任务状态信息
        response_data = {
            'task_id': task_id,
            'progress': task_status.get('progress', 0),
            'stage': task_status.get('stage', 'init'),  # 【任务 C：前端同步】确保返回当前的 stage 描述
            'status': task_status.get('status', 'init'),
            'results': task_status.get('results', []),
            'is_completed': task_status.get('status') == 'completed',
            'created_at': task_status.get('start_time', None)
        }

        # 返回任务状态信息
        return jsonify(response_data), 200
    else:'''

new_api = '''# 尝试从全局存储获取任务状态
    if task_id in execution_store:
        task_status = execution_store[task_id]

        # 按照 API 契约返回任务状态信息
        response_data = {
            'task_id': task_id,
            'progress': task_status.get('progress', 0),
            'stage': task_status.get('stage', 'init'),
            'status': task_status.get('status', 'init'),
            'results': task_status.get('results', []),
            'detailed_results': task_status.get('results', []),  # 添加 detailed_results
            'is_completed': task_status.get('status') == 'completed',
            'created_at': task_status.get('start_time', None)
        }

        # 返回任务状态信息
        return jsonify(response_data), 200
    else:'''

if old_api in content:
    content = content.replace(old_api, new_api)
    print('✅ 修复 1 成功：execution_store 返回 detailed_results')
else:
    print('❌ 修复 1 失败：未找到匹配内容')

# 修复数据库降级查询，返回完整的 results_summary
old_db = '''db_task_status = get_db_task_status(task_id)
            if db_task_status:
                # 从数据库构建响应
                response_data = {
                    'task_id': task_id,
                    'progress': 100 if db_task_status.is_completed else 50,
                    'stage': db_task_status.stage.value,
                    'status': 'completed' if db_task_status.is_completed else 'unknown',
                    'is_completed': db_task_status.is_completed,
                    'created_at': db_task_status.created_at,
                    'from_database': True,  # 标记数据来源
                    'message': 'Task found in database (server restarted)'
                }

                # 如果任务已完成，尝试获取结果
                if db_task_status.is_completed:
                    deep_result = get_deep_intelligence_result(task_id)
                    if deep_result:
                        response_data['has_result'] = True'''

new_db = '''db_task_status = get_db_task_status(task_id)
            if db_task_status:
                # 【P0 修复】从数据库获取完整的 results_summary
                from wechat_backend.database_core import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT results_summary, detailed_results, is_summary_compressed, is_detailed_compressed
                    FROM test_records
                    WHERE id = (
                        SELECT MAX(id) FROM test_records 
                        WHERE json_extract(results_summary, '$.execution_id') = ?
                    )
                ''', (task_id,))
                db_row = cursor.fetchone()
                conn.close()
                
                response_data = {
                    'task_id': task_id,
                    'progress': 100 if db_task_status.is_completed else 50,
                    'stage': db_task_status.stage.value,
                    'status': 'completed' if db_task_status.is_completed else 'unknown',
                    'is_completed': db_task_status.is_completed,
                    'created_at': db_task_status.created_at,
                    'from_database': True,
                    'message': 'Task found in database'
                }

                # 解析 results_summary
                if db_row:
                    summary_raw, detailed_raw, summary_comp, detailed_comp = db_row
                    try:
                        if summary_comp and summary_raw:
                            import gzip
                            summary = json.loads(gzip.decompress(summary_raw).decode('utf-8'))
                        elif summary_raw:
                            summary = json.loads(summary_raw)
                        else:
                            summary = {}
                        
                        # 提取关键字段
                        response_data['detailed_results'] = summary.get('detailed_results', [])
                        response_data['brand_scores'] = summary.get('brand_scores', {})
                        response_data['competitive_analysis'] = summary.get('competitive_analysis', {})
                        response_data['negative_sources'] = summary.get('negative_sources', [])
                        response_data['semantic_drift_data'] = summary.get('semantic_drift_data', {})
                        response_data['recommendation_data'] = summary.get('recommendation_data', {})
                        response_data['overall_score'] = summary.get('overall_score', 0)
                        
                        print(f'✅ 从数据库加载 results_summary: {len(summary)} 字段')
                    except Exception as e:
                        print(f'❌ 解析 results_summary 失败：{e}')
                        response_data['detailed_results'] = []
                        response_data['brand_scores'] = {}
                        response_data['competitive_analysis'] = {}'''

if old_db in content:
    content = content.replace(old_db, new_db)
    print('✅ 修复 2 成功：数据库降级查询返回完整数据')
else:
    print('❌ 修复 2 失败：未找到匹配内容')

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
