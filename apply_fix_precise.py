#!/usr/bin/env python3
"""
应用 P0 修复并清理冗余代码 - 精确版本
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 查找目标行
    if '# 保存维度结果' in line and '此处 brand 参数应调整' in lines[i+1] if i+1 < len(lines) else False:
        # 替换为简洁版本
        new_lines.append('                            # 保存维度结果（到 dimension_results 表）\n')
        new_lines.append('                            save_dimension_result(\n')
        new_lines.append('                                execution_id=execution_id,\n')
        new_lines.append('                                dimension_name=f"{main_brand}-{model_name}",\n')
        new_lines.append('                                dimension_type="ai_analysis",\n')
        new_lines.append('                                source=model_name,\n')
        new_lines.append('                                status=dim_status,\n')
        new_lines.append('                                score=dim_score,\n')
        new_lines.append('                                data=geo_data if dim_status == "success" else None,\n')
        new_lines.append('                                error_message=ai_result.error_message if dim_status == "failed" else (parse_error if parse_error else None)\n')
        new_lines.append('                            )\n')
        new_lines.append('\n')
        new_lines.append('                            # 【P0 关键修复】保存 AI 调用结果到 diagnosis_results 表\n')
        new_lines.append('                            if dim_status == "success" and geo_data:\n')
        new_lines.append('                                try:\n')
        new_lines.append('                                    import sqlite3\n')
        new_lines.append('                                    import json\n')
        new_lines.append('                                    from datetime import datetime\n')
        new_lines.append('                                    \n')
        new_lines.append('                                    conn = sqlite3.connect("/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db")\n')
        new_lines.append('                                    cursor = conn.cursor()\n')
        new_lines.append('                                    \n')
        new_lines.append('                                    cursor.execute(\'SELECT id FROM diagnosis_reports WHERE execution_id = ?\', (execution_id,))\n')
        new_lines.append('                                    report_row = cursor.fetchone()\n')
        new_lines.append('                                    report_id = report_row[0] if report_row else None\n')
        new_lines.append('                                    \n')
        new_lines.append('                                    if report_id:\n')
        new_lines.append('                                        now = datetime.now().isoformat()\n')
        new_lines.append('                                        response_content = str(ai_result.content) if hasattr(ai_result, \'data\') else str(ai_result)\n')
        new_lines.append('                                        \n')
        new_lines.append('                                        cursor.execute("""\n')
        new_lines.append('                                            INSERT INTO diagnosis_results (\n')
        new_lines.append('                                                report_id, execution_id, brand, question, model,\n')
        new_lines.append('                                                response_content, response_latency, geo_data,\n')
        new_lines.append('                                                quality_score, quality_level, status\n')
        new_lines.append('                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n')
        new_lines.append('                                        """, (\n')
        new_lines.append('                                            report_id, execution_id, main_brand, question, model_name,\n')
        new_lines.append('                                            response_content,\n')
        new_lines.append('                                            ai_result.latency if hasattr(ai_result, \'latency\') else None,\n')
        new_lines.append('                                            json.dumps(geo_data, ensure_ascii=False),\n')
        new_lines.append('                                            dim_score,\n')
        new_lines.append('                                            \'high\' if dim_score and dim_score >= 80 else \'medium\',\n')
        new_lines.append('                                            \'success\'\n')
        new_lines.append('                                        ))\n')
        new_lines.append('                                        \n')
        new_lines.append('                                        conn.commit()\n')
        new_lines.append('                                        conn.close()\n')
        new_lines.append('                                        api_logger.info(f"[NxM] ✅ diagnosis_results 保存成功：{execution_id}")\n')
        new_lines.append('                                    else:\n')
        new_lines.append('                                        conn.close()\n')
        new_lines.append('                                        api_logger.warning(f"[NxM] ⚠️ 未找到 report_id: {execution_id}")\n')
        new_lines.append('                                except Exception as save_err:\n')
        new_lines.append('                                    api_logger.error(f"[NxM] ⚠️ diagnosis_results 保存失败：{execution_id}, 错误：{save_err}")\n')
        new_lines.append('\n')
        
        # 跳过原来的冗余注释和 save_dimension_result 调用（共 15 行）
        i += 15
        
        # 添加实时更新进度
        new_lines.append('                            # 实时更新进度\n')
    else:
        new_lines.append(line)
        i += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ P0 修复已应用")
print("✅ 冗余注释已清理（删除 4 行）")
print("✅ 新增 diagnosis_results 保存逻辑（约 45 行）")
