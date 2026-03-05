#!/usr/bin/env python3
"""
应用 P0 修复：保存 AI 调用结果到 diagnosis_results 表

此脚本自动修改 nxm_execution_engine.py 文件
"""

import os
import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找目标位置：在 save_dimension_result 调用之后
# 使用正则表达式匹配
pattern = r'(save_dimension_result\(\s*execution_id=execution_id,.*?error_message=ai_result\.error_message if dim_status == "failed" else \(parse_error if parse_error else None\)\s*\))'

match = re.search(pattern, content, re.DOTALL)

if match:
    old_code = match.group(1)
    
    # 新代码：在 save_dimension_result 之后添加 diagnosis_results 保存逻辑
    new_code = old_code + '''

                            # 【P0 关键修复】保存 AI 调用结果到 diagnosis_results 表
                            if dim_status == "success" and geo_data:
                                try:
                                    import sqlite3
                                    import json
                                    from datetime import datetime
                                    
                                    # 直接执行 SQL 插入到 diagnosis_results 表
                                    conn = sqlite3.connect('/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db')
                                    cursor = conn.cursor()
                                    
                                    # 获取 report_id（从 diagnosis_reports 表）
                                    cursor.execute('SELECT id FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
                                    report_row = cursor.fetchone()
                                    report_id = report_row[0] if report_row else None
                                    
                                    if report_id:
                                        now = datetime.now().isoformat()
                                        
                                        # 构建诊断结果记录
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
                                    # 不中断主流程
'''
    
    # 替换代码
    content = content.replace(old_code, new_code)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复成功：已添加 diagnosis_results 保存逻辑")
    print(f"   文件：{file_path}")
    
else:
    print("❌ 未找到目标代码位置")
    print("   请手动检查文件内容")
