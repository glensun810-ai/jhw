#!/usr/bin/env python3
"""
P0 修复：保存 AI 调用结果到 diagnosis_results 表

问题：
- AI 调用结果只保存到 dimension_results 表
- diagnosis_results 表为空，导致前端无法获取详细结果

修复：
- 在每次 AI 调用成功后，同时保存到 diagnosis_results 表
"""

import re

# 读取文件
file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找要修改的位置
old_code = '''                        # 保存维度结果
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

new_code = '''                        # 保存维度结果
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
                                from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
                                
                                # 构建诊断结果记录
                                diagnosis_result = {
                                    'brand': main_brand,
                                    'question': question,
                                    'model': model_name,
                                    'response': {
                                        'content': str(ai_result.content) if hasattr(ai_result, 'data') else str(ai_result),
                                        'latency': ai_result.latency if hasattr(ai_result, 'latency') else None
                                    },
                                    'geo_data': geo_data,
                                    'status': 'success',
                                    'error': None,
                                    'quality_score': dim_score,
                                    'quality_level': 'high' if dim_score and dim_score >= 80 else 'medium' if dim_score and dim_score >= 60 else 'low'
                                }
                                
                                # 保存到 diagnosis_results 表
                                result_repo = DiagnosisResultRepository()
                                result_id = result_repo.add_by_execution_id(execution_id, diagnosis_result)
                                
                                api_logger.info(f"[NxM] ✅ diagnosis_results 保存成功：execution_id={execution_id}, result_id={result_id}")
                                
                            except Exception as save_err:
                                api_logger.error(f"[NxM] ⚠️ diagnosis_results 保存失败：execution_id={execution_id}, 错误：{save_err}")
                                # 不中断主流程

                        # 实时更新进度'''

if old_code in content:
    content = content.replace(old_code, new_code)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复成功：已添加 diagnosis_results 保存逻辑")
else:
    print("❌ 未找到要修改的代码位置")
    print("尝试使用 grep 查找...")
    
    # 尝试查找
    import subprocess
    result = subprocess.run(['grep', '-n', 'save_dimension_result', file_path], capture_output=True, text=True)
    print(f"grep 结果：{result.stdout}")
