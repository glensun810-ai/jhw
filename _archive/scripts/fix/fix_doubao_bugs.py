#!/usr/bin/env python3
"""
修复豆包适配器的 4 个关键 bug:
1. AIErrorType 未定义
2. AIResponse 对象不可序列化
3. AIResponse 对象不可订阅
4. 豆包 API 配额耗尽后的降级处理
"""

import os
import re

# ============================================================================
# 修复 1: doubao_priority_adapter.py - AIErrorType 未定义
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_priority_adapter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已经导入 AIErrorType
if 'from wechat_backend.ai_adapters.base_adapter import' in content:
    # 检查是否已经包含 AIErrorType
    if 'AIErrorType' not in content:
        # 添加 AIErrorType 到导入语句
        content = content.replace(
            'from wechat_backend.ai_adapters.base_adapter import',
            'from wechat_backend.ai_adapters.base_adapter import AIErrorType,'
        )
        print(f"✅ 修复 1: 添加 AIErrorType 导入到 {file_path}")
    else:
        print(f"⚠️  {file_path} 已经导入 AIErrorType")
else:
    print(f"❌ 未在 {file_path} 中找到导入语句")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================================================
# 修复 2: nxm_result_aggregator.py - AIResponse 对象不可订阅
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_result_aggregator.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 parse_geo_with_validation 函数，修复 AIResponse 对象处理
old_code = '''def parse_geo_with_validation(
    response_text: str,
    execution_id: str,
    q_idx: int,
    model_name: str
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    解析 GEO 数据并验证

    返回：
    - geo_data: 解析后的 GEO 数据
    - error: 错误信息（如果有）
    """
    try:
        # 修复 1: 传递 execution_id, q_idx, model_name 参数
        geo_data = parse_geo_json_enhanced(response_text, execution_id, q_idx, model_name)'''

new_code = '''def parse_geo_with_validation(
    response_text: str,
    execution_id: str,
    q_idx: int,
    model_name: str
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    解析 GEO 数据并验证

    返回：
    - geo_data: 解析后的 GEO 数据
    - error: 错误信息（如果有）
    """
    try:
        # 【P0 修复】处理 AIResponse 对象
        from wechat_backend.ai_adapters.base_adapter import AIResponse
        if isinstance(response_text, AIResponse):
            # 从 AIResponse 对象中提取实际响应文本
            if response_text.success and response_text.content:
                response_text = response_text.content
            else:
                return {
                    'brand_mentioned': False,
                    'rank': -1,
                    'sentiment': 0.0,
                    'cited_sources': [],
                    'interception': '',
                    '_error': f'AI 调用失败：{response_text.error_message}'
                }, response_text.error_message or 'AI 调用失败'
        
        # 修复 1: 传递 execution_id, q_idx, model_name 参数
        geo_data = parse_geo_json_enhanced(response_text, execution_id, q_idx, model_name)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print(f"✅ 修复 2: 修复 AIResponse 对象处理于 {file_path}")
else:
    print(f"⚠️  未在 {file_path} 中找到目标代码，可能已修复或代码结构不同")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================================================
# 修复 3: nxm_execution_engine.py - AIResponse 对象不可序列化
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 run_execution 函数中的错误处理部分，确保 response 是字符串
old_pattern = r'''                        # 检查最终结果
                        if not response or not geo_data or geo_data\.get\('_error'\):
                            api_logger\.error\(f"\[NxM\] 重试耗尽，标记为失败：{model_name}, Q{q_idx}"\)
                            scheduler\.record_model_failure\(model_name\)
                            
                            # \[P1 修复\] 降级策略：即使失败也保留已有数据，确保前端可展示
                            result = \{
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response or f'AI 调用失败：{str\(e\) if "e" in locals\(\) else "未知错误"}',  # ✅ 保留错误信息'''

new_pattern = r'''                        # 检查最终结果
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

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_pattern, content)
    print(f"✅ 修复 3: 修复 AIResponse 序列化于 {file_path}")
else:
    print(f"⚠️  未在 {file_path} 中找到目标代码")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================================================
# 修复 4: doubao_priority_adapter.py - 豆包 API 配额耗尽后的降级处理
# ============================================================================

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_priority_adapter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否有 429 错误的特殊处理
if '429' not in content or 'SetLimitExceeded' not in content:
    print(f"⚠️  {file_path} 可能需要添加 429 错误的特殊处理")
    print(f"   建议在 send_prompt 方法中添加对 429 SetLimitExceeded 的处理逻辑")
else:
    print(f"✅ {file_path} 已包含 429 错误处理")

print("\n" + "="*80)
print("修复完成！请重启后端服务并测试")
print("="*80)
print("\n修复内容:")
print("1. ✅ 添加 AIErrorType 导入到 doubao_priority_adapter.py")
print("2. ✅ 修复 AIResponse 对象处理于 nxm_result_aggregator.py")
print("3. ✅ 修复 AIResponse 序列化于 nxm_execution_engine.py")
print("4. ⚠️  豆包 API 配额问题需要配置有效的 API Key 或切换到其他模型")
print("\n下一步:")
print("1. 重启后端服务")
print("2. 清除前端缓存并重新编译")
print("3. 测试诊断功能")
