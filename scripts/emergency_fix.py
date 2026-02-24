#!/usr/bin/env python3
"""
紧急修复脚本：修复所有错误的转义字符和缺失的导入
"""

import re
import os

print("=" * 60)
print("开始紧急修复")
print("=" * 60)

# 1. 修复 JS 文件中的错误转义
js_files_fixed = 0
for root, dirs, files in os.walk('pages'):
    for file in files:
        if file.endswith('.js'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复 console\.log\( 为 console.log(
            if 'console\\.log\\(' in content or 'console\\.error\\(' in content or 'console\\.warn\\(' in content:
                content = content.replace('console\\.log\\(', 'console.log(')
                content = content.replace('console\\.error\\(', 'console.error(')
                content = content.replace('console\\.warn\\(', 'console.warn(')
                content = content.replace('console\\.debug\\(', 'console.debug(')
                content = content.replace("\\'", "'")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                js_files_fixed += 1
                print(f"✅ {filepath}")

# 2. 修复 services 目录下的 JS 文件
for root, dirs, files in os.walk('services'):
    for file in files:
        if file.endswith('.js'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'console\\.log\\(' in content:
                content = content.replace('console\\.log\\(', 'console.log(')
                content = content.replace("\\'", "'")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                js_files_fixed += 1
                print(f"✅ {filepath}")

print(f"\n修复了 {js_files_fixed} 个 JS 文件")

# 3. 检查 results.js 是否缺少导入
results_js_path = 'pages/results/results.js'
with open(results_js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否有 loadDiagnosisResult 导入
if 'const { loadDiagnosisResult' not in content and 'loadDiagnosisResult(' in content:
    # 添加导入
    if "const { saveResult } = require('../../utils/saved-results-sync');" in content:
        content = content.replace(
            "const { saveResult } = require('../../utils/saved-results-sync');",
            "const { saveResult } = require('../../utils/saved-results-sync');\nconst { loadDiagnosisResult, loadLastDiagnosis } = require('../../utils/storage-manager');"
        )
        with open(results_js_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 修复 results.js 导入缺失")

print("\n" + "=" * 60)
print("修复完成")
print("=" * 60)
