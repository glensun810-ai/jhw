#!/usr/bin/env python3
"""
精确编辑 views.py 的数据库查询部分
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 2: 添加导入语句
old_import = "from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result"
new_import = "from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result\n            from wechat_backend.database_core import get_connection\n            import gzip, json"

if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print('✅ 修复 2: 添加导入语句')
else:
    print('❌ 修复 2 失败：未找到导入语句')

# 修复 3: 添加 results_summary 查询
old_message = "'message': 'Task found in database (server restarted)'"
new_message = """'message': 'Task found in database (server restarted)'
                }

                # 【P0 修复】从数据库获取完整的 results_summary
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    SELECT results_summary, is_summary_compressed
                    FROM test_records
                    WHERE id = (
                        SELECT MAX(id) FROM test_records 
                        WHERE json_extract(results_summary, '$.execution_id') = ?
                    )
                \"\"\", (task_id,))
                db_row = cursor.fetchone()
                conn.close()
                
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
                        response_data['competitive_analysis'] = {}

                # 如果任务已完成，尝试获取结果
                if db_task_status.is_completed:
                    deep_result = get_deep_intelligence_result(task_id)
                    if deep_result:
                        response_data['has_result'] = True"""

if old_message in content:
    content = content.replace(old_message, new_message, 1)
    print('✅ 修复 3: 添加 results_summary 查询')
else:
    print('❌ 修复 3 失败：未找到 message 行')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
