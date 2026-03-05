#!/usr/bin/env python3
"""
清理 nxm_execution_engine.py 中重复的 save_dimension_result 调用
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并删除重复的 save_dimension_result 调用
new_lines = []
skip_until_line = -1
removed_count = 0

for i, line in enumerate(lines):
    line_num = i + 1
    
    # 跳过需要删除的行
    if line_num <= skip_until_line:
        continue
    
    # 检查是否是重复的 save_dimension_result 调用
    if 'save_dimension_result(' in line and line_num > 475 and line_num < 500:
        # 检查是否已经有过一次调用
        if any('save_dimension_result(' in l and l.strip().startswith('save_dimension_result(') 
               for l in lines[max(0, i-20):i]):
            # 这是重复调用，删除它
            # 找到这个调用的结束位置
            j = i
            while j < len(lines) and ');' not in lines[j]:
                j += 1
            skip_until_line = j + 1  # 跳过结束行
            removed_count += 1
            print(f"✅ 已删除第 {line_num} 行的重复调用")
            continue
    
    new_lines.append(line)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✅ 清理完成，共删除 {removed_count} 个重复调用")
