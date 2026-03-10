#!/usr/bin/env python3
"""
重新应用 P0 修复：保存 AI 结果到 diagnosis_results 表
同时清理冗余代码
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 清理冗余注释和重复调用
old_code = '''                            # 保存维度结果
                            # 此处 brand 参数应调整，因为改为客观提问，品牌不在请求中指定。
                            # 可能需要调整数据库结构或在聚合阶段处理。
                            # 这里暂时保留 brand 变量，但 P0 修复计划中提示词已移除 brand 引用。
                            # 需要上层代码确保 brand 变量的正确上下文或在此处使用占位。
                            save_dimension_result(
                                execution_id=execution_id,
                                dimension_name=f"{main_brand}-{model_name}", # P0 修复：使用 main_brand 作为维度维度标识
                                dimension_type="ai_analysis",
                                source=model_name,
                                status=dim_status,
                                score=dim_score,
                                data=geo_data if dim_status == "success" else None,
                                error_message=ai_result.error_message if dim_status == "failed" else (parse_error if parse_error else None)
                            )'''

new_code = '''                            # 保存维度结果（到 dimension_results 表）
                            save_dimension_result(
                                execution_id=execution_id,
                                dimension_name=f"{main_brand}-{model_name}",
                                dimension_type="ai_analysis",
                                source=model_name,
                                status=dim_status,
                                score=dim_score,
                                data=geo_data if dim_status == "success" else None,
                                error_message=ai_result.error_message if dim_status == "failed" else (parse_error if parse_error else None)
                            )

                            # 【P0 关键修复】保存 AI 调用结果到 diagnosis_results 表
                            # 问题：之前只保存到 dimension_results 表，diagnosis_results 表为空
                            # 修复：每次 AI 调用成功后，同时保存到 diagnosis_results 表
                            if dim_status == "success" and geo_data:
                                try:
                                    import sqlite3
                                    import json
                                    from datetime import datetime
                                    
                                    # 连接到数据库
                                    conn = sqlite3.connect('/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db')
                                    cursor = conn.cursor()
                                    
                                    # 获取 report_id
                                    cursor.execute('SELECT id FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
                                    report_row = cursor.fetchone()
                                    report_id = report_row[0] if report_row else None
                                    
                                    if report_id:
                                        now = datetime.now().isoformat()
                                        response_content = str(ai_result.content) if hasattr(ai_result, 'data') else str(ai_result)
                                        
                                        cursor.execute('''
                                            INSERT INTO diagnosis_results (
                                                report_id, execution_id,
                                                brand, question, model,
                                                response_content, response_latency,
                                                geo_data,
                                                quality_score, quality_level, quality_details,
                                                status, error_message,
                                                raw_response, response_metadata,
                                                tokens_used, prompt_tokens, completion_tokens, cached_tokens,
                                                finish_reason, request_id, model_version, reasoning_content,
                                                api_endpoint, service_tier,
                                                retry_count, is_fallback,
                                                created_at, updated_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            report_id,
                                            execution_id,
                                            main_brand,
                                            question,
                                            model_name,
                                            response_content,
                                            ai_result.latency if hasattr(ai_result, 'latency') else None,
                                            json.dumps(geo_data, ensure_ascii=False),
                                            dim_score,
                                            'high' if dim_score and dim_score >= 80 else 'medium' if dim_score and dim_score >= 60 else 'low',
                                            json.dumps({}),
                                            'success',
                                            None,
                                            json.dumps({}),
                                            json.dumps({}),
                                            0, 0, 0, 0,
                                            'stop',
                                            '',
                                            model_name,
                                            '',
                                            '',
                                            'default',
                                            0,
                                            0,
                                            now,
                                            now
                                        ))
                                        
                                        conn.commit()
                                        result_id = cursor.lastrowid
                                        conn.close()
                                        
                                        api_logger.info(f"[NxM] ✅ diagnosis_results 保存成功：execution_id={execution_id}, result_id={result_id}")
                                    else:
                                        api_logger.warning(f"[NxM] ⚠️ 未找到 report_id：execution_id={execution_id}")
                                        conn.close()
                                    
                                except Exception as save_err:
                                    api_logger.error(f"[NxM] ⚠️ diagnosis_results 保存失败：execution_id={execution_id}, 错误：{save_err}")
                                    # 不中断主流程'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ P0 修复已应用：diagnosis_results 保存逻辑")
else:
    print("⚠️ 未找到目标代码，尝试其他方式...")
    
    # 尝试在文件末尾添加
    if 'save_dimension_result(' in content:
        # 找到 save_dimension_result 调用
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            # 在 save_dimension_result 调用后添加修复代码
            if 'save_dimension_result(' in line and 'execution_id=execution_id' in lines[i+1] if i+1 < len(lines) else False:
                # 找到调用结束位置
                if line.strip().endswith(')'):
                    # 添加修复代码
                    new_lines.append('')
                    new_lines.append('                            # 【P0 关键修复】保存 AI 调用结果到 diagnosis_results 表')
                    new_lines.append('                            if dim_status == "success" and geo_data:')
                    new_lines.append('                                try:')
                    new_lines.append('                                    import sqlite3')
                    new_lines.append('                                    import json')
                    new_lines.append('                                    from datetime import datetime')
                    new_lines.append('                                    ')
                    new_lines.append('                                    conn = sqlite3.connect("/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db")')
                    new_lines.append('                                    cursor = conn.cursor()')
                    new_lines.append('                                    cursor.execute("SELECT id FROM diagnosis_reports WHERE execution_id = ?", (execution_id,))')
                    new_lines.append('                                    report_row = cursor.fetchone()')
                    new_lines.append('                                    report_id = report_row[0] if report_row else None')
                    new_lines.append('                                    ')
                    new_lines.append('                                    if report_id:')
                    new_lines.append('                                        now = datetime.now().isoformat()')
                    new_lines.append('                                        response_content = str(ai_result.content) if hasattr(ai_result, "data") else str(ai_result)')
                    new_lines.append('                                        ')
                    new_lines.append('                                        cursor.execute("INSERT INTO diagnosis_results (report_id, execution_id, brand, question, model, response_content, response_latency, geo_data, quality_score, quality_level, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",')
                    new_lines.append('                                            (report_id, execution_id, main_brand, question, model_name, response_content, ai_result.latency if hasattr(ai_result, "latency") else None, json.dumps(geo_data, ensure_ascii=False), dim_score, "high" if dim_score and dim_score >= 80 else "medium", "success"))')
                    new_lines.append('                                        conn.commit()')
                    new_lines.append('                                        conn.close()')
                    new_lines.append('                                        api_logger.info(f"[NxM] ✅ diagnosis_results 保存成功：{execution_id}")')
                    new_lines.append('                                except Exception as save_err:')
                    new_lines.append('                                    api_logger.error(f"[NxM] ⚠️ diagnosis_results 保存失败：{execution_id}, 错误：{save_err}")')
                    print("✅ 已添加 diagnosis_results 保存逻辑（简化版）")

    content = '\n'.join(new_lines)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成")
