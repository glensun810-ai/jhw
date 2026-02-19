#!/usr/bin/env python3
"""Step 1: 页面注册检查脚本"""
import json
import os

with open('app.json', 'r') as f:
    app_config = json.load(f)

print("=" * 70)
print("STEP 1: 页面注册检查")
print("=" * 70)
print()

pages = app_config.get('pages', [])
print(f"app.json 中定义了 {len(pages)} 个页面:\n")

issues = []
problem_pages = [
    'pages/config-manager/config-manager',
    'pages/permission-manager/permission-manager',
    'pages/data-manager/data-manager',
    'pages/user-guide/user-guide',
    'pages/personal-history/personal-history'
]

for page in pages:
    js_file = f'{page}.js'
    json_file = f'{page}.json'
    wxml_file = f'{page}.wxml'
    wxss_file = f'{page}.wxss'
    
    js_exists = os.path.exists(js_file)
    json_exists = os.path.exists(json_file)
    wxml_exists = os.path.exists(wxml_file)
    wxss_exists = os.path.exists(wxss_file)
    
    has_page_function = False
    if js_exists:
        with open(js_file, 'r') as f:
            content = f.read()
            has_page_function = 'Page({' in content or 'Page( {' in content
    
    is_problem_page = page in problem_pages
    status = "✅" if (js_exists and json_exists and wxml_exists and wxss_exists and has_page_function) else "❌"
    
    marker = " ← 问题页面" if is_problem_page else ""
    print(f"{status} {page}{marker}")
    
    if not js_exists:
        print(f"   └─ ❌ 缺少：{js_file}")
        issues.append(f"{page}: 缺少 .js 文件")
    elif not has_page_function:
        print(f"   └─ ❌ {js_file} 中没有 Page({{}}) 定义")
        issues.append(f"{page}: .js 文件中没有 Page({{}})")
    
    if not json_exists:
        print(f"   └─ ⚠️  缺少：{json_file}")
    if not wxml_exists:
        print(f"   └─ ⚠️  缺少：{wxml_file}")
    if not wxss_exists:
        print(f"   └─ ⚠️  缺少：{wxss_file}")

print()
print("=" * 70)

if issues:
    print(f"❌ 发现 {len(issues)} 个问题:")
    for issue in issues:
        print(f"   - {issue}")
    print()
    print("建议：从 app.json 中删除以上问题页面路径")
else:
    print("✅ 所有页面注册正常，文件完整，Page({}) 定义存在")

print("=" * 70)
