#!/usr/bin/env python3
"""
修复 nxm_execution_engine.py 的 try-except 缩进问题
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修复第 132-200 行的缩进
fixed_lines = []
in_try_block = False
try_indent_level = 24  # 4 级缩进 * 6 = 24 空格

for i, line in enumerate(lines):
    # 检测 try: 块开始（第 111 行左右）
    if 'try:' in line and line.strip() == 'try:' and i > 100 and i < 120:
        in_try_block = True
        fixed_lines.append(line)
        continue
    
    # 检测 except 块（第 200 行左右）
    if 'except Exception as e:' in line and i > 195 and i < 210:
        in_try_block = False
        fixed_lines.append(line)
        continue
    
    # 在 try 块内，修复缩进
    if in_try_block and i > 130 and i < 200:
        # 计算当前缩进
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        
        # 如果缩进是 24（6 级），需要增加到 28（7 级）
        if current_indent == 24 and stripped and not stripped.startswith('#'):
            fixed_lines.append(' ' * 28 + stripped)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ 缩进修复完成")
