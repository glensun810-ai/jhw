#!/usr/bin/env python3
"""
P0 修复：保存 AI 调用结果到 diagnosis_results 表
"""

# 读取文件
file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找插入点
new_lines = []
inserted = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # 查找插入点：在 save_dimension_result 调用之后
    if 'save_dimension_result(' in line and not inserted:
        # 继续读取直到找到闭合括号
        while i < len(lines) and ');' not in lines[i]:
            i += 1
            if i < len(lines):
                new_lines.append(lines[i])
        
        # 插入新代码
        new_code = '''
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

'''
        new_lines.append(new_code)
        inserted = True
        print(f"✅ 已在第 {len(new_lines)} 行插入 diagnosis_results 保存逻辑")

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

if inserted:
    print("✅ 修复完成")
else:
    print("❌ 未找到插入点")
