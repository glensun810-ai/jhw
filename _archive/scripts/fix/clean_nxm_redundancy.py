#!/usr/bin/env python3
"""
清理 nxm_execution_engine.py 中的冗余代码
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 清理重复的 save_dimension_result 调用
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
                            )
                            save_dimension_result(
                                execution_id=execution_id,
                                dimension_name=f"{main_brand}-{model_name}",
                                dimension_type="ai_analysis",
                                source=model_name,
                                status=dim_status,
                                score=dim_score,
                                data=geo_data if dim_status == "success" else None,
                                error_message=ai_result.error_message if dim_status == "failed" else (
                                    parse_error if parse_error else None)
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
                            )'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ 已清理重复的 save_dimension_result 调用")
else:
    print("⚠️ 未找到重复的 save_dimension_result 调用")

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 清理完成")
