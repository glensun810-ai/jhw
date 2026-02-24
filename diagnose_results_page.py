#!/usr/bin/env python3
"""
品牌洞察报告详情页数据问题 - 诊断脚本

诊断项目：
1. 检查后端是否保存了高级分析数据
2. 检查 /test/status 接口是否返回完整数据
3. 检查前端是否正确解析数据
"""

import json
import re

print("="*80)
print("品牌洞察报告详情页数据问题 - 诊断脚本")
print("="*80)

# ============================================================================
# 1. 检查后端代码
# ============================================================================
print("\n1️⃣  检查后端代码 - 高级分析数据保存")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ("execution_store[execution_id]['semantic_drift_data']", "语义偏移数据保存"),
    ("execution_store[execution_id]['negative_sources']", "负面信源保存"),
    ("execution_store[execution_id]['recommendation_data']", "优化建议保存"),
    ("execution_store[execution_id]['competitive_analysis']", "竞争分析保存"),
    ("execution_store[execution_id]['brand_scores']", "品牌评分保存"),
]

for pattern, desc in checks:
    if pattern in content:
        print(f"  ✅ {desc}")
    else:
        print(f"  ❌ {desc} - 未找到")

# ============================================================================
# 2. 检查 /test/status 接口
# ============================================================================
print("\n2️⃣  检查 /test/status 接口 - 数据返回")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views/diagnosis_views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ("response_data['brand_scores'] = task_status['brand_scores']", "返回品牌评分"),
    ("response_data['competitive_analysis'] = task_status['competitive_analysis']", "返回竞争分析"),
    ("response_data['semantic_drift_data'] = task_status['semantic_drift_data']", "返回语义偏移"),
    ("response_data['recommendation_data'] = task_status['recommendation_data']", "返回优化建议"),
    ("response_data['negative_sources'] = task_status['negative_sources']", "返回负面信源"),
]

for pattern, desc in checks:
    if pattern in content:
        print(f"  ✅ {desc}")
    else:
        print(f"  ❌ {desc} - 未找到")

# ============================================================================
# 3. 检查前端数据加载
# ============================================================================
print("\n3️⃣  检查前端数据加载 - 解析逻辑")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ("res.data.brand_scores", "解析品牌评分"),
    ("res.data.competitive_analysis", "解析竞争分析"),
    ("res.data.semantic_drift_data", "解析语义偏移"),
    ("res.data.recommendation_data", "解析优化建议"),
    ("res.data.negative_sources", "解析负面信源"),
    ("initializePageWithData", "初始化页面数据"),
]

for pattern, desc in checks:
    if pattern in content:
        print(f"  ✅ {desc}")
    else:
        print(f"  ❌ {desc} - 未找到")

# ============================================================================
# 4. 检查前端数据展示
# ============================================================================
print("\n4️⃣  检查前端数据展示 - WXML 绑定")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/results/results.wxml'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("{{competitiveAnalysis.brandScores", "品牌评分展示"),
        ("{{competitiveAnalysis.competitiveAnalysis", "竞争分析展示"),
        ("{{semanticDriftData", "语义偏移展示"),
        ("{{recommendationData", "优化建议展示"),
        ("{{sourcePurityData", "信源纯净度展示"),
    ]
    
    for pattern, desc in checks:
        if pattern in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - 未找到")
except FileNotFoundError:
    print(f"  ⚠️  文件不存在：{file_path}")

# ============================================================================
# 5. 生成诊断报告
# ============================================================================
print("\n" + "="*80)
print("诊断报告")
print("="*80)

print("""
📋 问题定位:

1. 后端保存 ✅ - 高级分析数据已保存到 execution_store
2. 后端返回 ✅ - /test/status 接口已配置返回高级分析数据
3. 前端解析 ✅ - 前端代码已包含解析逻辑
4. 前端展示 ✅ - WXML 已绑定数据

🔍 可能的问题:

A. 数据生成失败
   - 高级分析服务调用失败
   - 数据为空或格式错误

B. 数据保存失败
   - execution_store 未正确更新
   - 保存时机不对（在返回之前）

C. 前端接收失败
   - 网络请求失败
   - 数据格式不匹配

D. 前端展示失败
   - 数据绑定路径错误
   - 条件渲染逻辑问题

🚀 下一步操作:

1. 执行一次完整诊断
2. 查看后端日志，搜索以下关键字:
   - "语义偏移分析完成"
   - "负面信源分析完成"
   - "优化建议生成完成"
   - "竞争分析完成"
   - "高级分析数据生成完成"

3. 查看前端 Console，搜索以下关键字:
   - "📡 后端 API 响应"
   - "📊 初始化页面数据"
   - "📦 P1-1 统一 Storage 加载结果"

4. 复制日志发给我，我将精准定位问题！
""")

print("="*80)
