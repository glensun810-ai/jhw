#!/usr/bin/env python3
"""
修复后端 /test/status API，返回完整的 results_summary 数据
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到第 2583 行（message 行），在后面添加 results_summary 查询
new_lines = []
for i, line in enumerate(lines, 1):
    new_lines.append(line)
    if i == 2583 and "'message':" in line and "server restarted" in line:
        # 在这行后面添加 results_summary 查询代码
        indent = "                "
        new_lines.append(indent + "\n")
        new_lines.append(indent + "# 【P0 修复】从数据库获取完整的 results_summary\n")
        new_lines.append(indent + "from wechat_backend.database_core import get_connection\n")
        new_lines.append(indent + "import gzip, json\n")
        new_lines.append(indent + "conn = get_connection()\n")
        new_lines.append(indent + "cursor = conn.cursor()\n")
        new_lines.append(indent + "cursor.execute(\"\"\"\n")
        new_lines.append(indent + "    SELECT results_summary, is_summary_compressed\n")
        new_lines.append(indent + "    FROM test_records\n")
        new_lines.append(indent + "    WHERE id = (\n")
        new_lines.append(indent + "        SELECT MAX(id) FROM test_records \n")
        new_lines.append(indent + "        WHERE json_extract(results_summary, '$.execution_id') = ?\n")
        new_lines.append(indent + "    )\n")
        new_lines.append(indent + "\"\"\", (task_id,))\n")
        new_lines.append(indent + "db_row = cursor.fetchone()\n")
        new_lines.append(indent + "conn.close()\n")
        new_lines.append(indent + "\n")
        new_lines.append(indent + "# 解析 results_summary\n")
        new_lines.append(indent + "if db_row:\n")
        new_lines.append(indent + "    summary_raw, summary_comp = db_row\n")
        new_lines.append(indent + "    try:\n")
        new_lines.append(indent + "        if summary_comp and summary_raw:\n")
        new_lines.append(indent + "            summary = json.loads(gzip.decompress(summary_raw).decode('utf-8'))\n")
        new_lines.append(indent + "        elif summary_raw:\n")
        new_lines.append(indent + "            summary = json.loads(summary_raw)\n")
        new_lines.append(indent + "        else:\n")
        new_lines.append(indent + "            summary = {}\n")
        new_lines.append(indent + "        \n")
        new_lines.append(indent + "        # 提取关键字段\n")
        new_lines.append(indent + "        response_data['detailed_results'] = summary.get('detailed_results', [])\n")
        new_lines.append(indent + "        response_data['brand_scores'] = summary.get('brand_scores', {})\n")
        new_lines.append(indent + "        response_data['competitive_analysis'] = summary.get('competitive_analysis', {})\n")
        new_lines.append(indent + "        response_data['negative_sources'] = summary.get('negative_sources', [])\n")
        new_lines.append(indent + "        response_data['semantic_drift_data'] = summary.get('semantic_drift_data', {})\n")
        new_lines.append(indent + "        response_data['recommendation_data'] = summary.get('recommendation_data', {})\n")
        new_lines.append(indent + "        response_data['overall_score'] = summary.get('overall_score', 0)\n")
        new_lines.append(indent + "        print(f'✅ 从数据库加载 results_summary: {len(summary)} 字段')\n")
        new_lines.append(indent + "    except Exception as e:\n")
        new_lines.append(indent + "        print(f'❌ 解析 results_summary 失败：{e}')\n")
        new_lines.append(indent + "        response_data['detailed_results'] = []\n")
        new_lines.append(indent + "        response_data['brand_scores'] = {}\n")
        new_lines.append(indent + "        response_data['competitive_analysis'] = {}\n")

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ 修复成功：数据库降级查询返回完整数据')
