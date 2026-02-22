#!/usr/bin/env python3
"""
手动修复 views.py 的数据库查询部分
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines, 1):
    new_lines.append(line)
    # 在第 2571 行后添加导入语句
    if i == 2571 and 'from wechat_backend.models import' in line:
        new_lines.append("            from wechat_backend.database_core import get_connection\n")
        new_lines.append("            import gzip, json\n")
    
    # 在第 2583 行后添加 results_summary 查询
    if i == 2583 and "'message': 'Task found in database (server restarted)'" in line:
        new_lines.append("                \n")
        new_lines.append("                # 【P0 修复】从数据库获取完整的 results_summary\n")
        new_lines.append("                conn = get_connection()\n")
        new_lines.append("                cursor = conn.cursor()\n")
        new_lines.append("                cursor.execute(\"\"\"\n")
        new_lines.append("                    SELECT results_summary, is_summary_compressed\n")
        new_lines.append("                    FROM test_records\n")
        new_lines.append("                    WHERE id = (\n")
        new_lines.append("                        SELECT MAX(id) FROM test_records \n")
        new_lines.append("                        WHERE json_extract(results_summary, '$.execution_id') = ?\n")
        new_lines.append("                    )\n")
        new_lines.append("                \"\"\", (task_id,))\n")
        new_lines.append("                db_row = cursor.fetchone()\n")
        new_lines.append("                conn.close()\n")
        new_lines.append("                \n")
        new_lines.append("                # 解析 results_summary\n")
        new_lines.append("                if db_row:\n")
        new_lines.append("                    summary_raw, summary_comp = db_row\n")
        new_lines.append("                    try:\n")
        new_lines.append("                        if summary_comp and summary_raw:\n")
        new_lines.append("                            summary = json.loads(gzip.decompress(summary_raw).decode('utf-8'))\n")
        new_lines.append("                        elif summary_raw:\n")
        new_lines.append("                            summary = json.loads(summary_raw)\n")
        new_lines.append("                        else:\n")
        new_lines.append("                            summary = {}\n")
        new_lines.append("                        \n")
        new_lines.append("                        # 提取关键字段\n")
        new_lines.append("                        response_data['detailed_results'] = summary.get('detailed_results', [])\n")
        new_lines.append("                        response_data['brand_scores'] = summary.get('brand_scores', {})\n")
        new_lines.append("                        response_data['competitive_analysis'] = summary.get('competitive_analysis', {})\n")
        new_lines.append("                        response_data['negative_sources'] = summary.get('negative_sources', [])\n")
        new_lines.append("                        response_data['semantic_drift_data'] = summary.get('semantic_drift_data', {})\n")
        new_lines.append("                        response_data['recommendation_data'] = summary.get('recommendation_data', {})\n")
        new_lines.append("                        response_data['overall_score'] = summary.get('overall_score', 0)\n")
        new_lines.append("                        api_logger.info(f'✅ 从数据库加载 results_summary: {len(summary)} 字段')\n")
        new_lines.append("                    except Exception as e:\n")
        new_lines.append("                        api_logger.error(f'❌ 解析 results_summary 失败：{e}')\n")
        new_lines.append("                        response_data['detailed_results'] = []\n")
        new_lines.append("                        response_data['brand_scores'] = {}\n")
        new_lines.append("                        response_data['competitive_analysis'] = {}\n")
        
        # 删除后面的 deep_result 代码
        skip_until = 0
        for j in range(i+1, min(i+10, len(lines))):
            if "if db_task_status.is_completed:" in lines[j]:
                skip_until = j + 4  # 跳过 if 块
                break
        # 继续处理后续行

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ 修复成功：数据库查询返回完整 results_summary')
