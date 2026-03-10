#!/usr/bin/env python3
"""更新 nxm_execution_engine.py 的剩余部分"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修改的行
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 修改 1: results_summary 构建
    if "'brands': []," in line and "品牌信息需要后置分析" in lines[i-1]:
        # 替换多行
        new_lines.append("                        # 品牌信息（来自后置分析）\n")
        new_lines.append("                        'brands': [main_brand] + [c['brand'] for c in brand_analysis.get('competitor_analysis', [])] if brand_analysis else [],\n")
        new_lines.append("                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),\n")
        new_lines.append("                        'user_brand_analysis': brand_analysis.get('user_brand_analysis') if brand_analysis else None,\n")
        new_lines.append("                        'comparison': brand_analysis.get('comparison') if brand_analysis else None,\n")
        i += 1  # 跳过原来的 'brands': [], 行
        continue
    
    # 修改 2: 返回结果中的 aggregated
    if "'aggregated': [], # 待后置分析" in line:
        new_lines.append("                    'aggregated': aggregated,\n")
        new_lines.append("                    'brand_analysis': brand_analysis,\n")
        i += 1
        continue
    
    # 其他行保持不变
    new_lines.append(line)
    i += 1

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ 修改完成！")
