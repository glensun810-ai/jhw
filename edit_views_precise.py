#!/usr/bin/env python3
"""
精确编辑 views.py，修复 /test/status API
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = 0

for i, line in enumerate(lines, 1):
    # 跳过已删除的代码
    if i < skip_until:
        continue
    
    # 修复 1: 第 2556 行，添加 detailed_results
    if i == 2556 and "'stage': task_status.get('stage', 'init')," in line:
        new_lines.append("            'stage': task_status.get('stage', 'init'),\n")
        new_lines.append("            'status': task_status.get('status', 'init'),\n")
        new_lines.append("            'results': task_status.get('results', []),\n")
        new_lines.append("            'detailed_results': task_status.get('results', []),  # 【P0 修复】添加 detailed_results\n")
        skip_until = i + 4  # 跳过原来的 4 行
        print(f'✅ 修复 1: 第 {i} 行添加 detailed_results')
        continue
    
    # 修复 2: 第 2571 行，添加导入
    if i == 2571 and 'from wechat_backend.models import' in line:
        new_lines.append(line)
        new_lines.append("            from wechat_backend.database_core import get_connection\n")
        new_lines.append("            import gzip, json\n")
        print(f'✅ 修复 2: 第 {i} 行添加导入语句')
        continue
    
    # 修复 3: 第 2583 行后添加 results_summary 查询
    if i == 2583 and "'message': 'Task found in database (server restarted)'" in line:
        new_lines.append(line)
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
        print(f'✅ 修复 3: 第 {i} 行后添加 results_summary 查询')
        
        # 跳过原来的 deep_result 代码
        skip_until = i + 6  # 跳过 if db_task_status.is_completed 块
        continue
    
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ 文件保存成功')
