#!/usr/bin/env python3
"""
直接修改 views.py，修复 /test/status API 返回完整数据
"""
import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: execution_store 返回 detailed_results
content = content.replace(
    "'results': task_status.get('results', []),\n            'is_completed': task_status.get('status') == 'completed',",
    "'results': task_status.get('results', []),\n            'detailed_results': task_status.get('results', []),  # 添加 detailed_results\n            'is_completed': task_status.get('status') == 'completed',"
)
print('✅ 修复 1: execution_store 返回 detailed_results')

# 修复 2: 数据库查询添加 results_summary
old_code = '''from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result

            db_task_status = get_db_task_status(task_id)
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

new_code = '''from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result
            from wechat_backend.database_core import get_connection
            import gzip, json

            db_task_status = get_db_task_status(task_id)
            if db_task_status:
                # 【P0 修复】从数据库获取完整的 results_summary
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT results_summary, is_summary_compressed
                    FROM test_records
                    WHERE id = (
                        SELECT MAX(id) FROM test_records 
                        WHERE json_extract(results_summary, '$.execution_id') = ?
                    )
                """, (task_id,))
                db_row = cursor.fetchone()
                conn.close()
                
                # 从数据库构建响应
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
                    summary_raw, summary_comp = db_row
                    try:
                        if summary_comp and summary_raw:
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
                        
                        api_logger.info(f'✅ 从数据库加载 results_summary: {len(summary)} 字段')
                    except Exception as e:
                        api_logger.error(f'❌ 解析 results_summary 失败：{e}')
                        response_data['detailed_results'] = []
                        response_data['brand_scores'] = {}
                        response_data['competitive_analysis'] = {}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 修复 2: 数据库查询返回完整 results_summary')
else:
    print('❌ 修复 2 失败：未找到匹配内容')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
