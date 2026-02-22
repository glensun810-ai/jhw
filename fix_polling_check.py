#!/usr/bin/env python3
"""
修复轮询判断逻辑
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换判断逻辑
old_check = '''if (res.statusCode === 200) {'''
new_check = '''// 【P0 修复】getTaskStatusApi 返回的是 res.data，不是完整 res
        // 检查是否有有效数据
        if (res && (res.progress !== undefined || res.stage)) {'''

if old_check in content:
    content = content.replace(old_check, new_check)
    print('✅ 替换成功：修改轮询判断逻辑')
else:
    print('❌ 替换失败：未找到匹配内容')
    # 尝试查找当前内容
    if 'res.statusCode' in content:
        print('  找到 res.statusCode，尝试其他匹配...')
    else:
        print('  未找到 res.statusCode')

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
