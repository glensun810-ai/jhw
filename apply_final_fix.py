#!/usr/bin/env python3
"""
应用 P0 修复并清理冗余代码
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换冗余注释和添加 P0 修复
old_code = '''                            # 此处 brand 参数应调整，因为改为客观提问，品牌不在请求中指定。
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
                            )

                            # 实时更新进度'''

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
                            if dim_status == "success" and geo_data:
                                try:
                                    import sqlite3
                                    import json
                                    from datetime import datetime
                                    
                                    conn = sqlite3.connect('/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db')
                                    cursor = conn.cursor()
                                    
                                    cursor.execute('SELECT id FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
                                    report_row = cursor.fetchone()
                                    report_id = report_row[0] if report_row else None
                                    
                                    if report_id:
                                        now = datetime.now().isoformat()
                                        response_content = str(ai_result.content) if hasattr(ai_result, 'data') else str(ai_result)
                                        
                                        cursor.execute("""
                                            INSERT INTO diagnosis_results (
                                                report_id, execution_id, brand, question, model,
                                                response_content, response_latency, geo_data,
                                                quality_score, quality_level, status
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            report_id, execution_id, main_brand, question, model_name,
                                            response_content,
                                            ai_result.latency if hasattr(ai_result, 'latency') else None,
                                            json.dumps(geo_data, ensure_ascii=False),
                                            dim_score,
                                            'high' if dim_score and dim_score >= 80 else 'medium',
                                            'success'
                                        ))
                                        
                                        conn.commit()
                                        conn.close()
                                        api_logger.info(f"[NxM] ✅ diagnosis_results 保存成功：{execution_id}")
                                    else:
                                        conn.close()
                                        api_logger.warning(f"[NxM] ⚠️ 未找到 report_id: {execution_id}")
                                except Exception as save_err:
                                    api_logger.error(f"[NxM] ⚠️ diagnosis_results 保存失败：{execution_id}, 错误：{save_err}")

                            # 实时更新进度'''

if old_code in content:
    content = content.replace(old_code, new_code)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ P0 修复已应用")
    print("✅ 冗余注释已清理")
else:
    print("❌ 未找到目标代码")
    # 显示找到的内容
    import re
    match = re.search(r'# 此处 brand 参数应调整', content)
    if match:
        print(f"   找到部分匹配，位置：{match.start()}")
    else:
        print("   未找到任何匹配")
