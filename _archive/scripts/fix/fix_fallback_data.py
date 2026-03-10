#!/usr/bin/env python3
"""
Fix AI failure fallback data in nxm_execution_engine.py
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: Add fallback data for failed AI calls
old_fail_result = """                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            # 仍然添加结果，但标记为失败
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }
                            scheduler.add_result(result)
                            results.append(result)"""

new_fail_result = """                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            
                            # 【P1 修复】降级策略：即使失败也保留已有数据，确保前端可展示
                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response or f'AI 调用失败：{str(e) if "e" in locals() else "未知错误"}',  # ✅ 保留错误信息
                                'geo_data': geo_data or {  # ✅ 提供默认 geo_data
                                    '_error': 'AI 调用或解析失败',
                                    'brand_mentioned': False,
                                    'rank': -1,
                                    'sentiment': 0.0,
                                    'cited_sources': []
                                },
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }
                            scheduler.add_result(result)
                            results.append(result)"""

content = content.replace(old_fail_result, new_fail_result)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed AI failure fallback data!")
print("Changes:")
print("  - response: Now includes error message instead of None")
print("  - geo_data: Now includes default values for all fields")
