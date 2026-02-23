#!/usr/bin/env python3
"""
P1-3 修复：应用 selectedModels 简化补丁到 views.py
"""

import re
from pathlib import Path

VIEWS_FILE = Path(__file__).parent / 'wechat_backend' / 'views.py'

def apply_patch():
    """应用 selectedModels 简化补丁"""
    
    if not VIEWS_FILE.exists():
        print(f"❌ 文件不存在：{VIEWS_FILE}")
        return False
    
    print(f"📄 读取文件：{VIEWS_FILE}")
    with open(VIEWS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义旧代码模式
    old_pattern = r'''        # 要求：如果 selectedModels 传入的是字典列表，代码需具备自动提取 id 字段的健壮性
        # 解析器加固：从 selectedModels 对象数组中提取 id 或 value，转化为纯字符串列表
        parsed_selected_models = \[\]
        for model in selected_models:
            if isinstance\(model, dict\):
                # 如果是对象，提取其核心标识符
                model_name = model\.get\('name'\) or model\.get\('id'\) or model\.get\('value'\) or model\.get\('label'\)
                if model_name:
                    parsed_selected_models\.append\(\{'name': model_name, 'checked': model\.get\('checked', True\)\}\)
                else:
                    # 如果对象中没有合适的标识符，尝试使用第一个可用的键值
                    for key, value in model\.items\(\):
                        if key in \['name', 'id', 'value', 'label'\] and isinstance\(value, str\):
                            parsed_selected_models\.append\(\{'name': value, 'checked': model\.get\('checked', True\)\}\)
                            break
            elif isinstance\(model, str\):
                # 如果是字符串，直接使用
                parsed_selected_models\.append\(\{'name': model, 'checked': True\}\)
            else:
                # 其他类型，跳过或报错
                api_logger\.warning\(f"Unsupported model format: \{model\}, type: \{type\(model\)\}"\)

        # 更新 selected_models 为解析后的格式
        selected_models = parsed_selected_models

        # 审计要求：在后端打印关键调试日志
        original_model_names = \[model\.get\('name', model\) if isinstance\(model, dict\) else model for model in data\['selectedModels'\]\]
        converted_model_names = \[model\['name'\] for model in selected_models\]
        api_logger\.info\(f"\[Sprint 1\] 转换后的模型列表：\{converted_model_names\} \(原始：\{original_model_names\}\)"\)

        if not selected_models:
            return jsonify\(\{"status": "error", "error": 'No valid AI models found after parsing', "code": 400\}\), 400'''
    
    # 定义新代码
    new_code = '''        # P1-3 修复：简化 selectedModels 处理，前端已发送字符串数组
        # 验证并规范化模型名称（支持字符串和对象两种格式，向后兼容）
        parsed_selected_models = []
        for model in selected_models:
            if isinstance(model, str):
                # P1-3 修复：直接使用字符串
                model_name = model.lower().strip()
                if model_name:
                    parsed_selected_models.append(model_name)
            elif isinstance(model, dict):
                # 兼容旧格式：从对象提取名称
                model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
                if model_name:
                    parsed_selected_models.append(str(model_name).lower().strip())
            else:
                api_logger.warning(f"Unsupported model format: {model}, type: {type(model)}")

        # 更新 selected_models 为解析后的字符串列表
        selected_models = parsed_selected_models

        # 审计要求：在后端打印关键调试日志
        api_logger.info(f"[Sprint 1] 模型列表：{selected_models} (原始：{data['selectedModels']})")

        if not selected_models:
            return jsonify({"status": "error", "error": 'No valid AI models found after parsing', "code": 400}), 400'''
    
    # 尝试简单替换
    old_code_simple = '''        # 要求：如果 selectedModels 传入的是字典列表，代码需具备自动提取 id 字段的健壮性
        # 解析器加固：从 selectedModels 对象数组中提取 id 或 value，转化为纯字符串列表
        parsed_selected_models = []
        for model in selected_models:
            if isinstance(model, dict):
                # 如果是对象，提取其核心标识符
                model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
                if model_name:
                    parsed_selected_models.append({'name': model_name, 'checked': model.get('checked', True)})
                else:
                    # 如果对象中没有合适的标识符，尝试使用第一个可用的键值
                    for key, value in model.items():
                        if key in ['name', 'id', 'value', 'label'] and isinstance(value, str):
                            parsed_selected_models.append({'name': value, 'checked': model.get('checked', True)})
                            break
            elif isinstance(model, str):
                # 如果是字符串，直接使用
                parsed_selected_models.append({'name': model, 'checked': True})
            else:
                # 其他类型，跳过或报错
                api_logger.warning(f"Unsupported model format: {model}, type: {type(model)}")

        # 更新 selected_models 为解析后的格式
        selected_models = parsed_selected_models

        # 审计要求：在后端打印关键调试日志
        original_model_names = [model.get('name', model) if isinstance(model, dict) else model for model in data['selectedModels']]
        converted_model_names = [model['name'] for model in selected_models]
        api_logger.info(f"[Sprint 1] 转换后的模型列表：{converted_model_names} (原始：{original_model_names})")

        if not selected_models:
            return jsonify({"status": "error", "error": 'No valid AI models found after parsing', "code": 400}), 400'''
    
    print("🔍 查找目标代码...")
    if old_code_simple in content:
        print("✅ 找到目标代码，开始替换...")
        content = content.replace(old_code_simple, new_code)
        
        print("💾 保存文件...")
        with open(VIEWS_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 补丁应用成功！")
        return True
    else:
        print("❌ 未找到目标代码，可能已修复或代码已变更")
        return False

if __name__ == '__main__':
    print("="*60)
    print("P1-3 修复：应用 selectedModels 简化补丁")
    print("="*60)
    print()
    
    success = apply_patch()
    
    if success:
        print("\n✅ 补丁应用完成")
        print("\n请执行以下验证命令:")
        print("  cd backend_python && python3 -c \"import wechat_backend.views; print('✅ 导入成功')\"")
    else:
        print("\n❌ 补丁应用失败，请手动修复")
