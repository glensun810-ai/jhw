#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 代码静态检查脚本

import re

print("=" * 70)
print("🔍 代码静态检查")
print("=" * 70)
print()

# 检查 detail/index.js
file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ("TimeEstimator 引用", r"const TimeEstimator = require\('../../utils/timeEstimator'\)"),
    ("RemainingTimeCalculator 引用", r"const RemainingTimeCalculator"),
    ("ProgressValidator 引用", r"const ProgressValidator"),
    ("StageEstimator 引用", r"const StageEstimator"),
    ("NetworkMonitor 引用", r"const NetworkMonitor"),
    ("ProgressNotifier 引用", r"const ProgressNotifier"),
    ("TaskWeightProcessor 引用", r"const TaskWeightProcessor"),
    ("timeEstimator 实例", r"this\.timeEstimator = new TimeEstimator\(\)"),
    ("remainingTimeCalc 实例", r"this\.remainingTimeCalc = new RemainingTimeCalculator\(\)"),
    ("progressValidator 实例", r"this\.progressValidator = new ProgressValidator\(\)"),
    ("stageEstimator 实例", r"this\.stageEstimator = new StageEstimator\(\)"),
    ("networkMonitor 实例", r"this\.networkMonitor = new NetworkMonitor\(\)"),
    ("progressNotifier 实例", r"this\.progressNotifier = new ProgressNotifier\(\)"),
    ("taskWeightProcessor 实例", r"this\.taskWeightProcessor = new TaskWeightProcessor\(\)"),
    ("updateProgressDetails 方法", r"updateProgressDetails: function"),
    ("updatePollingInterval 方法", r"updatePollingInterval: function"),
    ("generateProgressExplanation 方法", r"generateProgressExplanation: function"),
    ("cancelDiagnosis 方法", r"cancelDiagnosis: function"),
    ("getNetworkQuality 方法", r"getNetworkQuality: function"),
    ("requestMessageSubscription 方法", r"requestMessageSubscription: function")
]

print("📄 检查 pages/detail/index.js:")
passed = 0
failed = 0

for name, pattern in checks:
    if re.search(pattern, content):
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        failed += 1

print()
print(f"检查结果：{passed} 通过，{failed} 失败")
print()

# 检查 WXML
wxml_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.wxml'

with open(wxml_path, 'r', encoding='utf-8') as f:
    wxml_content = f.read()

wxml_checks = [
    ("网络质量显示", r"network-quality-display"),
    ("订阅按钮", r"subscribe-btn"),
    ("取消按钮", r"cancel-diagnosis-btn"),
    ("进度警告", r"progress-warning"),
    ("阶段说明", r"stage-description"),
    ("进度解释", r"progress-explanation"),
    ("剩余时间平滑", r"smoothedRemainingTime")
]

print("📄 检查 pages/detail/index.wxml:")
wxml_passed = 0
wxml_failed = 0

for name, pattern in wxml_checks:
    if re.search(pattern, wxml_content):
        print(f"  ✅ {name}")
        wxml_passed += 1
    else:
        print(f"  ❌ {name}")
        wxml_failed += 1

print()
print(f"检查结果：{wxml_passed} 通过，{wxml_failed} 失败")
print()

# 总结
print("=" * 70)
total_passed = passed + wxml_passed
total_failed = failed + wxml_failed
print(f"📊 总计：{total_passed} 通过，{total_failed} 失败")

if total_failed == 0:
    print("✅ 所有检查通过！可以开始测试")
else:
    print("⚠️ 部分检查失败，请修复后再开始测试")

print("=" * 70)
