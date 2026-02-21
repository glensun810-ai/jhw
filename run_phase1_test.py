#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 阶段 1 测试准备检查脚本

import os

print("=" * 70)
print("📋 阶段 1 测试准备检查")
print("=" * 70)
print()

# 检查工具类文件
tools = [
    "utils/timeEstimator.js",
    "utils/remainingTimeCalculator.js",
    "utils/progressValidator.js",
    "utils/stageEstimator.js",
    "utils/networkMonitor.js",
    "utils/progressNotifier.js",
    "utils/taskWeightProcessor.js",
    "utils/testHelper.js"
]

print("1️⃣ 检查工具类文件:")
for tool in tools:
    path = f"/Users/sgl/PycharmProjects/PythonProject/{tool}"
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {tool} ({size} 字节)")
    else:
        print(f"  ❌ {tool} (不存在)")

print()

# 检查修改文件
modified = [
    "pages/detail/index.js",
    "pages/detail/index.wxml",
    "pages/detail/index.wxss"
]

print("2️⃣ 检查修改文件:")
for mod in modified:
    path = f"/Users/sgl/PycharmProjects/PythonProject/{mod}"
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {mod} ({size} 字节)")
    else:
        print(f"  ❌ {mod} (不存在)")

print()

# 检查测试文档
docs = [
    "TEST_INDEX.md",
    "TEST_EXECUTION_GUIDE.md",
    "test_phase1_report.md"
]

print("3️⃣ 检查测试文档:")
for doc in docs:
    path = f"/Users/sgl/PycharmProjects/PythonProject/{doc}"
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {doc} ({size} 字节)")
    else:
        print(f"  ❌ {doc} (不存在)")

print()
print("=" * 70)
print("✅ 测试准备检查完成")
print("=" * 70)
