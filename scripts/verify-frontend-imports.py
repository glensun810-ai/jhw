#!/usr/bin/env python3
"""
前端模块导入验证脚本
验证所有前端模块导入是否正确
"""

import os
import re

print('='*60)
print('前端模块导入验证')
print('='*60)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 检查关键文件
critical_files = [
    'utils/helperUtils.js',
    'utils/logger.js',
    'services/dataProcessorService.js',
    'services/brandTestService.js',
    'pages/index/index.js',
    'pages/results/results.js',
]

print('\n【检查关键文件】')
for filepath in critical_files:
    full_path = os.path.join(project_root, filepath)
    if os.path.exists(full_path):
        print(f'  ✅ {filepath}')
    else:
        print(f'  ❌ {filepath} (缺失)')

# 检查 index.js 的导入
print('\n【检查 index.js 导入】')
index_js_path = os.path.join(project_root, 'pages/index/index.js')
if os.path.exists(index_js_path):
    with open(index_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取所有 require 语句
    requires = re.findall(r"require\(['\"](.*?)['\"]\)", content)
    
    print(f'  发现 {len(requires)} 个导入')
    
    # 验证每个导入
    for require_path in requires[:10]:  # 只显示前 10 个
        if require_path.startswith('../../utils/'):
            utils_file = require_path.replace('../../utils/', 'utils/')
            if not utils_file.endswith('.js'):
                utils_file += '.js'
            full_path = os.path.join(project_root, utils_file)
            if os.path.exists(full_path):
                print(f'    ✅ {require_path}')
            else:
                print(f'    ❌ {require_path} (文件不存在)')

print('\n' + '='*60)
print('验证完成')
print('='*60)
print('\n如果所有检查都通过，但微信开发者工具仍报错:')
print('1. 运行：./clean-wechat-cache.sh')
print('2. 重启微信开发者工具')
print('3. 工具 → 清除缓存 → 清除全部缓存')
print('4. 点击 "编译" 重新编译')
