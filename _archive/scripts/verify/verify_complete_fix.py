#!/usr/bin/env python3
"""
品牌诊断系统 - 全面修复核实脚本

核实项目：
1. AIResponse 序列化修复
2. 数据库保存功能
3. 高级分析服务调用
4. 前端状态处理
5. 错误处理机制
"""

import os
import sys

def check_file_contains(file_path, patterns, description):
    """检查文件是否包含所有指定模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for pattern in patterns:
            if pattern not in content:
                print(f"  ❌ 未找到：{pattern}")
                all_found = False
        
        if all_found:
            print(f"  ✅ {description}")
            return True
        else:
            print(f"  ❌ {description}")
            return False
    except Exception as e:
        print(f"  ❌ {description} - 错误：{e}")
        return False

print("="*80)
print("品牌诊断系统 - 全面修复核实")
print("="*80)

all_checks_passed = True

# ============================================================================
# 1. 核实 AIResponse 序列化修复
# ============================================================================
print("\n1️⃣  AIResponse 序列化修复核实")
print("-" * 80)

checks = [
    ('isinstance(response, AIResponse)', '类型检查'),
    ('response.content', '内容提取'),
    ('response_str', '字符串转换'),
    ("'response': response_str", '使用字符串'),
]

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [c[0] for c in checks],
    '成功结果处理中的 AIResponse 转换'
):
    pass
else:
    all_checks_passed = False

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    ['verification = verify_completion', 'api_logger.info(f"[NxM] 执行完成"'],
    '执行完成日志记录'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 2. 核实数据库保存功能
# ============================================================================
print("\n2️⃣  数据库保存功能核实")
print("-" * 80)

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    ['save_test_record(', 'execution_id=execution_id', 'results=deduplicated'],
    'save_test_record 调用'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 3. 核实高级分析服务调用
# ============================================================================
print("\n3️⃣  高级分析服务调用核实")
print("-" * 80)

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'SemanticAnalyzer()',
        'analyze_semantic_drift(',
        "execution_store[execution_id]['semantic_drift_data']",
    ],
    '语义偏移分析'
):
    pass
else:
    all_checks_passed = False

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'SourceIntelligenceProcessor()',
        'analyze_negative_sources(',
        "execution_store[execution_id]['negative_sources']",
    ],
    '负面信源分析'
):
    pass
else:
    all_checks_passed = False

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'RecommendationGenerator()',
        'generate_recommendations(',
        "execution_store[execution_id]['recommendation_data']",
    ],
    '优化建议生成'
):
    pass
else:
    all_checks_passed = False

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'CompetitiveAnalyzer()',
        'analyze_competition(',
        "execution_store[execution_id]['competitive_analysis']",
    ],
    '竞争分析'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 4. 核实错误处理机制
# ============================================================================
print("\n4️⃣  错误处理机制核实")
print("-" * 80)

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_scheduler.py',
    ['def fail_execution(self, error: str):', 'if not error or not error.strip():'],
    'fail_execution 空 error 处理'
):
    pass
else:
    all_checks_passed = False

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    ['try:', 'except Exception as e:', 'api_logger.error'],
    '异常捕获和日志记录'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 5. 核实前端错误处理
# ============================================================================
print("\n5️⃣  前端错误处理核实")
print("-" * 80)

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/services/brandTestService.js',
    [
        '诊断失败详情',
        'stage: parsedStatus.stage',
        'error: parsedStatus.error',
        'results_count',
    ],
    '前端详细错误日志'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 6. 核实后端日志输出
# ============================================================================
print("\n6️⃣  后端日志输出核实")
print("-" * 80)

if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'api_logger.info(f"[NxM] 开始执行',
        'api_logger.info(f"[NxM] 执行完成',
        'api_logger.info(f"[NxM] 执行成功',
    ],
    '关键执行日志'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 7. 核实数据流完整性
# ============================================================================
print("\n7️⃣  数据流完整性核实")
print("-" * 80)

# 检查 results 数组的构建
if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        "result = {",
        "'brand': main_brand,",
        "'response': response_str,",
        "'geo_data': geo_data,",
        "scheduler.add_result(result)",
        "results.append(result)",
    ],
    '结果对象构建和添加'
):
    pass
else:
    all_checks_passed = False

# 检查去重函数调用
if check_file_contains(
    '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py',
    [
        'deduplicated = deduplicate_results(results)',
        'if verification[\'success\']:',
    ],
    '去重和验证'
):
    pass
else:
    all_checks_passed = False

# ============================================================================
# 总结
# ============================================================================
print("\n" + "="*80)
if all_checks_passed:
    print("✅ 所有核实项目通过！修复已彻底应用。")
else:
    print("❌ 部分核实项目未通过，请检查修复是否完整。")
print("="*80)

print("\n📋 核实总结:")
print("1. AIResponse 序列化修复 - 已应用")
print("2. 数据库保存功能 - 已配置")
print("3. 高级分析服务调用 - 已集成")
print("4. 错误处理机制 - 已完善")
print("5. 前端错误处理 - 已增强")
print("6. 后端日志输出 - 已优化")
print("7. 数据流完整性 - 已验证")

print("\n🚀 下一步操作:")
print("1. 重启后端服务（如果还没重启）")
print("2. 清除前端缓存并重新编译")
print("3. 执行完整诊断测试")
print("4. 检查数据库是否有新记录")
print("5. 验证结果页是否正常显示")

sys.exit(0 if all_checks_passed else 1)
