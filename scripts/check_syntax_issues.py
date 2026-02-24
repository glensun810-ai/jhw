#!/usr/bin/env python3
"""
排查同类语法问题
检查所有 JS 文件中是否有函数定义被删除但函数体残留的问题
"""

import re
import os

# 搜索所有 JS 文件中的语法问题
js_files = []
for root, dirs, files in os.walk('pages'):
    for file in files:
        if file.endswith('.js'):
            js_files.append(os.path.join(root, file))

print(f"检查 {len(js_files)} 个 JS 文件...")

issues = []
for js_file in js_files:
    with open(js_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 检查每行
    for i, line in enumerate(lines):
        # 检查函数注释后直接跟 const/let/var（可能是残留代码）
        if i > 0 and '*/' in lines[i-1] and (line.strip().startswith('const ') or line.strip().startswith('let ') or line.strip().startswith('var ')):
            # 检查前一行是否是函数注释
            if i > 1 and '/**' in lines[i-2]:
                # 检查前面是否有函数定义
                has_function_def = False
                for j in range(max(0, i-10), i):
                    if 'function' in lines[j] or ':' in lines[j]:
                        has_function_def = True
                        break
                
                if not has_function_def:
                    issues.append({
                        'file': js_file,
                        'line': i + 1,
                        'content': line.strip()[:80]
                    })

if issues:
    print(f"\n⚠️ 发现 {len(issues)} 个潜在问题:")
    for issue in issues[:20]:
        print(f"  - {issue['file']}:{issue['line']}")
        print(f"    {issue['content']}")
else:
    print("\n✅ 未发现同类语法问题")
