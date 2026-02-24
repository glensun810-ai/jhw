#!/usr/bin/env python3
"""
修复 except 块的缩进问题
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到第 202 行 (索引 201) 的 "except Exception as e:"
# 修复其后的所有代码缩进

in_except_block = False
except_line_num = 0

for i in range(200, min(250, len(lines))):
    if 'except Exception as e:' in lines[i]:
        in_except_block = True
        except_line_num = i
        # 这行本身需要 24 空格缩进
        lines[i] = ' ' * 24 + 'except Exception as e:\n'
        continue
    
    if in_except_block:
        # 计算当前行的缩进
        stripped = lines[i].lstrip()
        if stripped:  # 非空行
            current_indent = len(lines[i]) - len(stripped)
            # 需要 28 空格缩进 (7 级)
            if current_indent < 28 and not stripped.startswith('except'):
                lines[i] = ' ' * 28 + stripped
        # 检查是否是下一个块的开始
        if stripped.startswith('except') or stripped.startswith('finally') or (stripped.startswith('for ') and current_indent == 24):
            in_except_block = False

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ except 块缩进修复完成")
