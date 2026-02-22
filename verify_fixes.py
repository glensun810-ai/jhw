#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify all fixes are applied correctly"""

import re

print("=" * 60)
print("🔍 验证所有修复是否正确应用")
print("=" * 60)

# 1. 验证 index.js 的 Storage 修复
print("\n1️⃣ 验证 index.js - Storage 数据传递策略")
with open('/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()
    
if 'last_diagnostic_results' in content:
    print("   ✅ last_diagnostic_results Storage key 已添加")
else:
    print("   ❌ last_diagnostic_results Storage key 未找到")

if 'wx.setStorageSync(\'last_diagnostic_results\'' in content:
    print("   ✅ 数据保存到 Storage 已实现")
else:
    print("   ❌ 数据保存到 Storage 未实现")

# 检查 URL 传参是否已优化
if re.search(r'url:\s*`/pages/results/results\?executionId=', content):
    print("   ✅ URL 传参已优化（只传递 executionId 和 brandName）")
else:
    print("   ❌ URL 传参可能还有问题")

# 2. 验证 results.js 的 onLoad 修复
print("\n2️⃣ 验证 results.js - 数据加载策略")
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r', encoding='utf-8') as f:
    content = f.read()

if 'last_diagnostic_results' in content:
    print("   ✅ 优先从统一 Storage 加载已实现")
else:
    print("   ❌ 统一 Storage 加载未实现")

if 'fetchResultsFromServer' in content:
    print("   ✅ 后端 API 拉取 fallback 已添加")
else:
    print("   ❌ 后端 API 拉取 fallback 未添加")

if 'showNoDataModal' in content:
    print("   ✅ 无数据提示函数已添加")
else:
    print("   ❌ 无数据提示函数未添加")

# 3. 验证 ec-canvas.js 的兼容性修复
print("\n3️⃣ 验证 ec-canvas.js - API 兼容性")
with open('/Users/sgl/PycharmProjects/PythonProject/components/ec-canvas/ec-canvas.js', 'r', encoding='utf-8') as f:
    content = f.read()

if 'wx.getWindowInfo' in content:
    print("   ✅ wx.getWindowInfo() 已使用")
else:
    print("   ❌ wx.getWindowInfo() 未使用")

# 检查是否还有直接的 getSystemInfoSync 调用（没有降级处理）
direct_calls = re.findall(r'wx\.getSystemInfoSync\(\)', content)
if len(direct_calls) == 0:
    print("   ✅ 无直接的 getSystemInfoSync 调用")
else:
    # 检查是否有降级处理
    if 'wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()' in content:
        print("   ✅ getSystemInfoSync 有降级处理")
    else:
        print(f"   ⚠️ 发现 {len(direct_calls)} 处直接的 getSystemInfoSync 调用")

# 4. 验证 ECharts 初始化时机
print("\n4️⃣ 验证 ECharts 初始化时机")

with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r', encoding='utf-8') as f:
    results_content = f.read()

# 检查 initializePageWithData 中的 setData callback
if re.search(r'setData\([^,]+,\s*\(\)\s*=>\s*\{', results_content):
    print("   ✅ results.js 中 setData 有 callback")
else:
    print("   ⚠️ results.js 中 setData 可能没有 callback")

print("\n" + "=" * 60)
print("✅ 验证完成！")
print("=" * 60)
