#!/usr/bin/env python3
"""
修复诊断结果保存问题：AIResponse 对象无法 JSON 序列化

问题根因：
1. results 数组中的 response 字段是 AIResponse 对象
2. deduplicate_results 尝试 JSON 序列化时失败
3. 触发异常，导致 stage=failed

修复方案：
1. 在添加到 results 之前，将 AIResponse 对象转换为字符串
2. 确保所有保存到 execution_store 的数据都是 JSON 可序列化的
"""

import re

# ============================================================================
# 修复 1: nxm_execution_engine.py - 转换 AIResponse 为字符串
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找构建成功结果的地方，确保 response 是字符串
old_success_result = '''                        else:
                            scheduler.record_model_success(model_name)

                            # 构建结果
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data,
                                'timestamp': datetime.now().isoformat()
                            }

                            scheduler.add_result(result)
                            results.append(result)'''

new_success_result = '''                        else:
                            scheduler.record_model_success(model_name)

                            # 【P0 修复】确保 response 是字符串而不是 AIResponse 对象
                            from wechat_backend.ai_adapters.base_adapter import AIResponse
                            response_str = response
                            if isinstance(response, AIResponse):
                                # 提取 AIResponse 中的内容
                                if response.success and response.content:
                                    response_str = response.content
                                elif response.error_message:
                                    response_str = f'AI 调用失败：{response.error_message}'
                                else:
                                    response_str = str(response)
                            
                            # 构建结果（确保所有字段都是 JSON 可序列化的）
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response_str,  # ✅ 字符串
                                'geo_data': geo_data,
                                'timestamp': datetime.now().isoformat()
                            }

                            scheduler.add_result(result)
                            results.append(result)'''

if old_success_result in content:
    content = content.replace(old_success_result, new_success_result)
    print("✅ 修复 1: nxm_execution_engine.py - 成功结果处理")
else:
    print("⚠️  修复 1: 未找到目标代码，可能已修复或代码结构不同")

# 查找构建失败结果的地方，确保 response 是字符串
old_fail_result = '''                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            
                            # 【P0 修复】确保 response 是字符串而不是 AIResponse 对象
                            from wechat_backend.ai_adapters.base_adapter import AIResponse
                            response_str = response
                            if isinstance(response, AIResponse):
                                if response.success and response.content:
                                    response_str = response.content
                                else:
                                    response_str = f'AI 调用失败：{response.error_message or "未知错误"}'
                            elif not response:
                                response_str = f'AI 调用失败：{str(e) if "e" in locals() else "未知错误"}'
                            
                            # 【P1 修复】降级策略：即使失败也保留已有数据，确保前端可展示
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response_str,  # ✅ 使用字符串'''

new_fail_result = '''                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            
                            # 【P0 修复】确保 response 是字符串而不是 AIResponse 对象
                            from wechat_backend.ai_adapters.base_adapter import AIResponse
                            response_str = response
                            if isinstance(response, AIResponse):
                                # 提取 AIResponse 中的内容
                                if response.success and response.content:
                                    response_str = response.content
                                elif response.error_message:
                                    response_str = f'AI 调用失败：{response.error_message}'
                                else:
                                    response_str = str(response)
                            elif not response:
                                response_str = f'AI 调用失败：{str(e) if "e" in locals() else "未知错误"}'
                            
                            # 【P1 修复】降级策略：即使失败也保留已有数据，确保前端可展示
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response_str,  # ✅ 字符串'''

if old_fail_result in content:
    content = content.replace(old_fail_result, new_fail_result)
    print("✅ 修复 2: nxm_execution_engine.py - 失败结果处理")
else:
    print("⚠️  修复 2: 未找到目标代码，可能已修复或代码结构不同")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "="*80)
print("修复完成！请重启后端服务并测试")
print("="*80)
print("\n修复内容:")
print("1. ✅ 成功结果：AIResponse 对象 → 字符串")
print("2. ✅ 失败结果：AIResponse 对象 → 字符串")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 清除前端缓存并重新编译")
print("3. 测试诊断功能")
