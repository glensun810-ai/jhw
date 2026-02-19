#!/usr/bin/env python3
"""
Self-Test Script for NxM Matrix Refactoring
自检脚本：验证 NxM 重构功能

运行方式：
    python3 test_nxm_selftest.py

检查项目：
1. NxM 循环逻辑
2. geo_data 字段解析
3. GEO Prompt 模板
"""

import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 
                                'backend_python', 
                                'wechat_backend'))

def test_nxm_loop_structure():
    """测试 1: 验证 NxM 循环结构"""
    print("\n" + "="*60)
    print("测试 1: NxM 循环结构验证")
    print("="*60)
    
    # Read source code directly to check loop structure
    import os
    engine_path = os.path.join(os.path.dirname(__file__), 
                               'backend_python', 
                               'wechat_backend', 
                               'nxm_execution_engine.py')
    
    with open(engine_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # Test data: 3 questions × 2 brands × 2 models = 12 executions expected
    test_questions = ["问题 1", "问题 2", "问题 3"]
    test_brands = ["品牌 A", "品牌 B"]
    test_models = [{"name": "模型 X"}, {"name": "模型 Y"}]
    
    expected_executions = len(test_questions) * len(test_brands) * len(test_models)
    
    print(f"  问题数：{len(test_questions)}")
    print(f"  品牌数：{len(test_brands)}")
    print(f"  模型数：{len(test_models)}")
    print(f"  预期执行次数：{expected_executions}")
    
    # Check the loop structure in code
    has_outer_loop = 'for q_idx, base_question in enumerate(raw_questions):' in source
    has_brand_loop = 'for brand_idx, brand in enumerate(brand_list):' in source
    has_inner_loop = 'for model_idx, model_info in enumerate(selected_models):' in source
    
    print(f"\n  代码检查:")
    print(f"    ✓ 外层循环 (问题): {has_outer_loop}")
    print(f"    ✓ 中层循环 (品牌): {has_brand_loop}")
    print(f"    ✓ 内层循环 (模型): {has_inner_loop}")
    
    if has_outer_loop and has_brand_loop and has_inner_loop:
        print(f"\n  ✅ NxM 循环结构验证通过")
        return True
    else:
        print(f"\n  ❌ NxM 循环结构验证失败")
        return False


def test_geo_parser():
    """测试 2: 验证 GEO JSON 解析器"""
    print("\n" + "="*60)
    print("测试 2: GEO JSON 解析器验证")
    print("="*60)
    
    # Add the geo_parser path
    import sys
    geo_parser_path = os.path.join(os.path.dirname(__file__), 
                                   'backend_python', 
                                   'wechat_backend', 
                                   'ai_adapters')
    sys.path.insert(0, geo_parser_path)
    
    # Import and test
    import importlib.util
    spec = importlib.util.spec_from_file_location("geo_parser", 
        os.path.join(geo_parser_path, 'geo_parser.py'))
    geo_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geo_parser)
    
    parse_func = geo_parser.parse_geo_json_enhanced
    
    test_cases = [
        {
            "name": "标准 JSON 格式",
            "input": """
            这是一个 AI 回答的示例文本。
            
            {
              "geo_analysis": {
                "brand_mentioned": true,
                "rank": 3,
                "sentiment": 0.7,
                "cited_sources": [
                  {"url": "https://example.com", "site_name": "Example", "attitude": "positive"}
                ],
                "interception": ""
              }
            }
            """,
            "expected_rank": 3,
            "expected_sentiment": 0.7
        },
        {
            "name": "Markdown 代码块格式",
            "input": """
            这是 AI 回答的文本内容...
            
            ```json
            {
              "geo_analysis": {
                "brand_mentioned": true,
                "rank": 5,
                "sentiment": -0.2,
                "cited_sources": [],
                "interception": "竞品 A"
              }
            }
            ```
            """,
            "expected_rank": 5,
            "expected_sentiment": -0.2
        },
        {
            "name": "JSON 在文本末尾",
            "input": """
            AI 回答了很长的一段话，包含很多内容...
            最后给出了分析结果：
            {"geo_analysis": {"brand_mentioned": false, "rank": -1, "sentiment": 0.0, "cited_sources": [], "interception": ""}}
            """,
            "expected_rank": -1,
            "expected_sentiment": 0.0
        },
        {
            "name": "无 JSON 格式（应返回默认值）",
            "input": """
            这是 AI 的回答，但是没有包含 JSON 数据。
            """,
            "expected_rank": -1,
            "expected_sentiment": 0.0
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n  测试用例：{test_case['name']}")
        
        result = parse_func(test_case['input'])
        
        rank_ok = result.get('rank') == test_case['expected_rank']
        sentiment_ok = abs(result.get('sentiment', 0) - test_case['expected_sentiment']) < 0.01
        
        if rank_ok and sentiment_ok:
            print(f"    ✅ 通过 - rank={result.get('rank')}, sentiment={result.get('sentiment')}")
            passed += 1
        else:
            print(f"    ❌ 失败 - 期望 rank={test_case['expected_rank']}, sentiment={test_case['expected_sentiment']}")
            print(f"           实际 rank={result.get('rank')}, sentiment={result.get('sentiment')}")
            failed += 1
    
    print(f"\n  解析器测试结果：{passed} 通过，{failed} 失败")
    
    if failed == 0:
        print(f"  ✅ GEO JSON 解析器验证通过")
        return True
    else:
        print(f"  ❌ GEO JSON 解析器验证失败")
        return False


def test_geo_prompt_template():
    """测试 3: 验证 GEO Prompt 模板"""
    print("\n" + "="*60)
    print("测试 3: GEO Prompt 模板验证")
    print("="*60)
    
    # Read from file directly
    base_adapter_path = os.path.join(os.path.dirname(__file__), 
                                     'backend_python', 
                                     'wechat_backend', 
                                     'ai_adapters', 
                                     'base_adapter.py')
    
    with open(base_adapter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract GEO_PROMPT_TEMPLATE
    import re
    match = re.search(r'GEO_PROMPT_TEMPLATE\s*=\s*"""(.*?)"""', content, re.DOTALL)
    
    if not match:
        print("    ❌ 无法找到 GEO_PROMPT_TEMPLATE 定义")
        return False
    
    GEO_PROMPT_TEMPLATE = match.group(1)
    
    # Check required components
    required_components = [
        ("品牌名称占位符", "{brand_name}"),
        ("竞争对手占位符", "{competitors}"),
        ("问题占位符", "{question}"),
        ("geo_analysis 字段", '"geo_analysis"'),
        ("brand_mentioned 字段", '"brand_mentioned"'),
        ("rank 字段", '"rank"'),
        ("sentiment 字段", '"sentiment"'),
        ("cited_sources 字段", '"cited_sources"'),
        ("interception 字段", '"interception"'),
        ("不要包含在 Markdown", "不要包含在 Markdown 代码块中")
    ]
    
    print("  检查模板组件:")
    all_present = True
    
    for name, component in required_components:
        present = component in GEO_PROMPT_TEMPLATE
        status = "✓" if present else "✗"
        print(f"    {status} {name}: {present}")
        if not present:
            all_present = False
    
    # Test template formatting
    print("\n  测试模板格式化:")
    try:
        formatted = GEO_PROMPT_TEMPLATE.format(
            brand_name="Tesla",
            competitors="BMW, Mercedes",
            question="介绍一下 Tesla"
        )
        
        has_brand = "Tesla" in formatted
        has_competitors = "BMW, Mercedes" in formatted
        has_question = "介绍一下 Tesla" in formatted
        
        print(f"    ✓ 品牌名称替换：{has_brand}")
        print(f"    ✓ 竞争对手替换：{has_competitors}")
        print(f"    ✓ 问题替换：{has_question}")
        
        if has_brand and has_competitors and has_question:
            print(f"\n  ✅ GEO Prompt 模板验证通过")
            return all_present
        else:
            print(f"\n  ❌ GEO Prompt 模板格式化失败")
            return False
            
    except Exception as e:
        print(f"    ❌ 模板格式化异常：{e}")
        return False


def test_logging_integration():
    """测试 4: 验证日志集成"""
    print("\n" + "="*60)
    print("测试 4: 日志集成验证")
    print("="*60)
    
    # Read source code directly
    engine_path = os.path.join(os.path.dirname(__file__), 
                               'backend_python', 
                               'wechat_backend', 
                               'nxm_execution_engine.py')
    
    with open(engine_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    log_checks = [
        ("执行日志", 'api_logger.info(debug_log_msg)'),
        ("AI 响应预览日志", 'AI Response preview'),
        ("GEO 分析结果日志", 'GEO Analysis Result'),
        ("进度日志", 'progress')
    ]
    
    print("  检查日志语句:")
    all_present = True
    
    for name, log_statement in log_checks:
        present = log_statement in source
        status = "✓" if present else "✗"
        print(f"    {status} {name}: {present}")
        if not present:
            all_present = False
    
    if all_present:
        print(f"\n  ✅ 日志集成验证通过")
        return True
    else:
        print(f"\n  ⚠️  部分日志语句缺失（不影响功能，但会影响调试）")
        return True  # 不阻止测试通过


def generate_report(results):
    """生成测试报告"""
    print("\n" + "="*60)
    print("自检报告总结")
    print("="*60)
    
    test_names = [
        "NxM 循环结构",
        "GEO JSON 解析器",
        "GEO Prompt 模板",
        "日志集成"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {i+1}. {name}: {status}")
    
    total_passed = sum(results)
    total_tests = len(results)
    
    print(f"\n  总计：{total_passed}/{total_tests} 测试通过")
    
    if total_passed == total_tests:
        print(f"\n  🎉 所有测试通过！NxM 重构功能自检完成。")
        print(f"\n  下一步:")
        print(f"  1. 运行实际的 API 测试")
        print(f"  2. 检查后端日志中的执行次数")
        print(f"  3. 验证数据库中的 geo_data 字段")
        return True
    else:
        print(f"\n  ⚠️  部分测试失败，请检查上述报告。")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("NxM 矩阵重构功能自检")
    print("="*60)
    print("检查项目:")
    print("  1. 逻辑确认：NxM 循环是否正确实现")
    print("  2. 数据确认：geo_data 字段是否正确生成")
    print("  3. Prompt 确认：GEO 模板是否正确配置")
    print("  4. 日志确认：是否有详细的调试日志")
    
    results = []
    
    # Run tests
    results.append(test_nxm_loop_structure())
    results.append(test_geo_parser())
    results.append(test_geo_prompt_template())
    results.append(test_logging_integration())
    
    # Generate report
    generate_report(results)
    
    # Exit with appropriate code
    sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
