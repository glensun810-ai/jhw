#!/usr/bin/env python3
"""
高优先级 Bug 自动修复脚本
修复 BUG-NEW-002 和 BUG-NEW-003

使用方法:
python3 fix_high_priority_bugs.py
"""

import re
from pathlib import Path

print("="*70)
print("高优先级 Bug 自动修复")
print("="*70)
print()

# BUG-NEW-003: 数据库连接关闭
print("🔧 修复 BUG-NEW-003: 数据库连接可能泄漏")
print()

views_file = Path('backend_python/wechat_backend/views.py')

if views_file.exists():
    print(f"📄 读取文件：{views_file}")
    content = views_file.read_text(encoding='utf-8')
    
    # 查找数据库连接模式
    pattern = r'conn = get_connection\(\)\n(\s+)cursor = conn\.cursor\(\)'
    
    matches = list(re.finditer(pattern, content))
    if matches:
        print(f"✅ 找到 {len(matches)} 处需要修复的数据库连接")
        
        # 统计修复数量
        fix_count = 0
        for match in reversed(matches):  # 从后往前替换，避免位置变化
            start = match.start()
            end = match.end()
            indent = match.group(1)
            
            # 创建修复后的代码
            fixed_code = f'''try:
{indent}    conn = get_connection()
{indent}    cursor = conn.cursor()'''
            
            # 替换
            content = content[:start] + fixed_code + content[end:]
            fix_count += 1
        
        # 查找所有 conn.close() 并添加到 finally
        close_pattern = r'(\s+)conn\.close\(\)'
        close_matches = list(re.finditer(close_pattern, content))
        
        if close_matches:
            print(f"✅ 找到 {len(close_matches)} 处 conn.close() 需要添加到 finally")
            
            for match in reversed(close_matches):
                indent = match.group(1)
                start = match.start()
                end = match.end()
                
                # 替换为 finally 块
                fixed_close = f'''finally:
{indent}    if conn:
{indent}        conn.close()'''
                
                content = content[:start] + fixed_close + content[end:]
        
        # 写回文件
        views_file.write_text(content, encoding='utf-8')
        
        print(f"✅ 已修复 {fix_count} 处数据库连接")
        print()
        print("⚠️  注意：请手动检查修复结果，确保 try-finally 结构正确")
    else:
        print("⚠️  未找到需要修复的数据库连接模式")
else:
    print(f"❌ 文件不存在：{views_file}")

print()
print("="*70)
print("BUG-NEW-002 修复需要手动集成异步引擎")
print("详见：docs/高优先级 Bug 修复指南.md")
print("="*70)
print()
print("✅ 自动修复完成！")
print()
print("下一步:")
print("1. 验证 BUG-NEW-003 修复：git diff backend_python/wechat_backend/views.py")
print("2. 手动修复 BUG-NEW-002：集成异步执行引擎")
print("3. 运行测试验证所有修复")
