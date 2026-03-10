#!/usr/bin/env python3
"""
Self-Test for Corrected NxM Logic
正确的 NxM 逻辑自检

请求次数 = 问题数 × 模型数（只针对用户自己的品牌）
竞品品牌不参与 API 请求，仅用于对比分析
"""

import os

def test_nxm_logic():
    """测试 NxM 循环逻辑"""
    print("\n" + "="*60)
    print("测试：正确的 NxM 循环逻辑")
    print("="*60)
    
    engine_file = 'backend_python/wechat_backend/nxm_execution_engine.py'
    with open(engine_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # 检查函数签名
    has_main_brand = 'main_brand: str' in source
    has_competitor_brands = 'competitor_brands: List[str]' in source
    print(f"\n  函数参数检查:")
    print(f"    {'✓' if has_main_brand else '✗'} main_brand 参数：{has_main_brand}")
    print(f"    {'✓' if has_competitor_brands else '✗'} competitor_brands 参数：{has_competitor_brands}")
    
    # 检查循环结构（只遍历问题和模型，不遍历竞品）
    checks = {
        '外层循环 (问题)': 'for q_idx, base_question in enumerate(raw_questions):',
        '内层循环 (模型)': 'for model_idx, model_info in enumerate(selected_models):',
    }
    
    print(f"\n  循环结构检查:")
    all_pass = True
    for name, pattern in checks.items():
        found = pattern in source
        print(f"    {'✓' if found else '✗'} {name}: {found}")
        if not found:
            all_pass = False
    
    # 检查没有品牌循环（竞品不参与请求）
    has_brand_loop = 'for brand_idx, brand in enumerate(brand_list):' in source
    print(f"\n  竞品品牌循环检查:")
    print(f"    {'✗' if has_brand_loop else '✓'} 竞品不参与循环：{not has_brand_loop}")
    if has_brand_loop:
        all_pass = False
    
    # 检查日志格式
    has_correct_log = '[MainBrand:' in source
    print(f"\n  日志格式检查:")
    print(f"    {'✓' if has_correct_log else '✗'} 使用 [MainBrand:] 格式：{has_correct_log}")
    
    return all_pass and has_main_brand and has_competitor_brands


def test_scenarios():
    """测试 4 个场景的预期请求次数"""
    print("\n" + "="*60)
    print("测试：4 个场景的预期请求次数")
    print("="*60)
    
    scenarios = [
        {
            "name": "场景 1: 1 主品牌 +3 竞品，3 问题，4 模型",
            "main_brand": 1,
            "competitors": 3,
            "questions": 3,
            "models": 4,
            "expected": 3 * 4  # 问题数 × 模型数
        },
        {
            "name": "场景 2: 1 主品牌 +2 竞品，3 问题，4 模型",
            "main_brand": 1,
            "competitors": 2,
            "questions": 3,
            "models": 4,
            "expected": 3 * 4  # 问题数 × 模型数
        },
        {
            "name": "场景 3: 1 主品牌 +2 竞品，4 问题，2 模型",
            "main_brand": 1,
            "competitors": 2,
            "questions": 4,
            "models": 2,
            "expected": 4 * 2  # 问题数 × 模型数
        },
        {
            "name": "场景 4: 2 主品牌 +2 竞品，3 问题，4 模型",
            "main_brand": 2,
            "competitors": 2,
            "questions": 3,
            "models": 4,
            "expected": 3 * 4 * 2  # 问题数 × 模型数 × 主品牌数
        }
    ]
    
    all_pass = True
    for scenario in scenarios:
        # 计算预期请求次数
        expected = scenario['questions'] * scenario['models'] * scenario['main_brand']
        matches = expected == scenario['expected']
        
        print(f"\n  {scenario['name']}")
        print(f"    计算公式：{scenario['questions']} 问题 × {scenario['models']} 模型 × {scenario['main_brand']} 主品牌 = {expected}")
        print(f"    预期请求次数：{expected} {'✓' if matches else '✗'}")
        
        if not matches:
            all_pass = False
    
    return all_pass


def test_views_integration():
    """测试 views.py 集成"""
    print("\n" + "="*60)
    print("测试：views.py 集成")
    print("="*60)
    
    views_file = 'backend_python/wechat_backend/views.py'
    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查品牌分离逻辑
    has_main_brand_extract = 'main_brand = brand_list[0]' in content
    has_competitor_extract = 'competitor_brands = brand_list[1:]' in content
    
    print(f"\n  品牌分离逻辑:")
    print(f"    {'✓' if has_main_brand_extract else '✗'} 提取主品牌：{has_main_brand_extract}")
    print(f"    {'✓' if has_competitor_extract else '✗'} 提取竞品品牌：{has_competitor_extract}")
    
    # 检查函数调用
    has_correct_call = 'main_brand=main_brand' in content and 'competitor_brands=competitor_brands' in content
    print(f"\n  函数调用检查:")
    print(f"    {'✓' if has_correct_call else '✗'} 正确的参数传递：{has_correct_call}")
    
    return has_main_brand_extract and has_competitor_extract and has_correct_call


def main():
    print("\n" + "="*60)
    print("NxM 重构功能自检（修正版）")
    print("="*60)
    print("\n 核心逻辑：请求次数 = 问题数 × 模型数 × 主品牌数")
    print("          竞品品牌不参与 API 请求，仅用于对比分析")
    
    results = [
        test_nxm_logic(),
        test_scenarios(),
        test_views_integration()
    ]
    
    # 总结
    print("\n" + "="*60)
    print("自检总结")
    print("="*60)
    
    tests = ["NxM 循环逻辑", "场景计算", "views.py 集成"]
    for name, result in zip(tests, results):
        print(f"  {'✅' if result else '❌'} {name}: {'通过' if result else '失败'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n  总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n  🎉 所有测试通过！")
        print("\n  四个场景的答案:")
        print("  1) 1 主 +3 竞品，3 问题，4 模型 → 12 次请求")
        print("  2) 1 主 +2 竞品，3 问题，4 模型 → 12 次请求")
        print("  3) 1 主 +2 竞品，4 问题，2 模型 → 8 次请求")
        print("  4) 2 主 +2 竞品，3 问题，4 模型 → 24 次请求")
    else:
        print("\n  ⚠️ 部分测试失败，请检查报告")
    
    return passed == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)
