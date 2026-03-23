#!/usr/bin/env python3
"""
品牌分布计算修复验证测试

验证点：
1. _clean_brand_name 方法正确清理品牌名称
2. _calculate_brand_distribution 多层降级策略正常工作
3. 确保始终返回有效的品牌分布数据

作者：系统架构组
日期：2026-03-17
版本：1.0.0
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python/wechat_backend'))

from wechat_backend.diagnosis_report_service import DiagnosisReportService
from wechat_backend.logging_config import api_logger


def test_clean_brand_name():
    """测试品牌名称清理功能"""
    print("\n" + "="*80)
    print("测试 1: 品牌名称清理功能")
    print("="*80)
    
    service = DiagnosisReportService()
    
    test_cases = [
        # (输入，期望输出)
        ('特斯拉 (Tesla)', '特斯拉'),
        ('比亚迪（BYD）', '比亚迪'),
        ('特斯拉汽车品牌', '特斯拉'),
        ('比亚迪股份有限公司', '比亚迪'),
        ('Apple Inc.', 'Apple'),
        ('小米科技有限责任公司', '小米'),
        ('  华为   ', '华为'),
        ('Tesla [US]', 'Tesla'),
        ('蔚来【NIO】', '蔚来'),
        ('', ''),
        (None, ''),
        ('   ', ''),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected in test_cases:
        try:
            result = service._clean_brand_name(input_val)
            if result == expected:
                print(f"  ✅ '{input_val}' -> '{result}'")
                passed += 1
            else:
                print(f"  ❌ '{input_val}' -> '{result}' (期望：'{expected}')")
                failed += 1
        except Exception as e:
            print(f"  ❌ '{input_val}' -> 异常：{e}")
            failed += 1
    
    print(f"\n结果：通过 {passed}/{len(test_cases)} 个测试")
    return failed == 0


def test_brand_distribution_with_extracted_brand():
    """测试优先使用 extracted_brand"""
    print("\n" + "="*80)
    print("测试 2: 优先使用 extracted_brand")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 模拟结果，包含 extracted_brand
    mock_results = [
        {
            'id': 1,
            'brand': '特斯拉',  # 配置中的品牌
            'extracted_brand': '特斯拉 (Tesla)',  # 从 AI 响应中提取的品牌（带括号）
            'response': '特斯拉是一家电动汽车公司'
        },
        {
            'id': 2,
            'brand': '比亚迪',
            'extracted_brand': '比亚迪（BYD）',
            'response': '比亚迪是新能源汽车领导者'
        },
        {
            'id': 3,
            'brand': '蔚来',
            'extracted_brand': '蔚来汽车',  # 带后缀
            'response': '蔚来是高端电动汽车品牌'
        }
    ]
    
    expected_brands = ['特斯拉', '比亚迪', '蔚来']
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    print(f"调试信息：{result['_debug_info']}")
    
    # 验证
    assert '特斯拉' in result['data'], "❌ 应该包含'特斯拉'"
    assert '比亚迪' in result['data'], "❌ 应该包含'比亚迪'"
    assert '蔚来' in result['data'], "❌ 应该包含'蔚来'"
    
    # 验证品牌名称已被清理（不带括号和后缀）
    assert result['data']['特斯拉'] == 1, "❌ '特斯拉'计数应该为 1"
    assert result['data']['比亚迪'] == 1, "❌ '比亚迪'计数应该为 1"
    assert result['data']['蔚来'] == 1, "❌ '蔚来'计数应该为 1"
    
    # 验证 extracted_brand 使用统计
    assert result['_debug_info']['extracted_brand_count'] == 3, "❌ 应该全部使用 extracted_brand"
    
    print("\n✅ 测试通过：正确优先使用 extracted_brand 并清理品牌名称")
    return True


def test_brand_distribution_fallback_to_brand():
    """测试降级到 brand 字段"""
    print("\n" + "="*80)
    print("测试 3: 降级到 brand 字段")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 模拟结果，extracted_brand 为空
    mock_results = [
        {
            'id': 1,
            'brand': '特斯拉',
            'extracted_brand': None,
            'response': '介绍电动汽车品牌'
        },
        {
            'id': 2,
            'brand': '比亚迪',
            'extracted_brand': '',
            'response': '新能源汽车对比'
        },
        {
            'id': 3,
            'brand': '蔚来汽车',  # 带后缀
            'extracted_brand': None,
            'response': '高端汽车品牌'
        }
    ]
    
    expected_brands = ['特斯拉', '比亚迪', '蔚来']
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    print(f"调试信息：{result['_debug_info']}")
    
    # 验证
    assert '特斯拉' in result['data'], "❌ 应该包含'特斯拉'"
    assert '比亚迪' in result['data'], "❌ 应该包含'比亚迪'"
    assert '蔚来' in result['data'], "❌ 应该包含'蔚来'（已清理后缀）"
    
    # 验证降级统计
    assert result['_debug_info']['fallback_to_brand_count'] == 3, "❌ 应该全部降级到 brand"
    
    print("\n✅ 测试通过：正确降级到 brand 字段并清理品牌名称")
    return True


def test_brand_distribution_fallback_to_response():
    """测试降级到 response 内容提取"""
    print("\n" + "="*80)
    print("测试 4: 降级到 response 内容提取")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 模拟结果，extracted_brand 和 brand 都为空
    # 每个 result 应该只提取一个品牌（第一个匹配的预期品牌）
    mock_results = [
        {
            'id': 1,
            'brand': None,
            'extracted_brand': None,
            'response': '特斯拉在电动汽车市场处于领先地位'  # 只提到特斯拉
        },
        {
            'id': 2,
            'brand': None,
            'extracted_brand': None,
            'response': '比亚迪和特斯拉是主要竞争对手，比亚迪销量领先'  # 提到比亚迪和特斯拉，应该匹配第一个
        },
        {
            'id': 3,
            'brand': None,
            'extracted_brand': None,
            'response': '蔚来是新兴的电动汽车品牌'  # 只提到蔚来
        }
    ]
    
    expected_brands = ['特斯拉', '比亚迪', '蔚来']
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    print(f"调试信息：{result['_debug_info']}")
    
    # 验证：每个 result 只贡献一个品牌计数
    # result 1: 特斯拉 (1 次)
    # result 2: 特斯拉 (1 次，因为特斯拉在预期品牌列表中排在比亚迪前面，先匹配到)
    # result 3: 蔚来 (1 次)
    # 所以特斯拉=2, 蔚来=1, 比亚迪=0
    # 这是预期行为 - 每个 result 只匹配第一个找到的预期品牌
    assert '特斯拉' in result['data'], "❌ 应该包含'特斯拉'"
    assert '蔚来' in result['data'], "❌ 应该包含'蔚来'"
    
    # 验证降级统计 - 所有 3 个结果都降级到 response 提取
    assert result['_debug_info']['fallback_to_response_count'] == 3, "❌ 应该全部降级到 response 提取"
    
    print("\n✅ 测试通过：正确从 response 中提取品牌名称")
    print("   注意：每个 result 只匹配第一个找到的预期品牌，这是预期行为")
    return True


def test_brand_distribution_empty_results():
    """测试空 results 的兜底数据"""
    print("\n" + "="*80)
    print("测试 5: 空 results 的兜底数据")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 空 results
    mock_results = []
    expected_brands = ['特斯拉', '比亚迪', '蔚来']
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    
    # 验证
    assert '特斯拉' in result['data'], "❌ 应该包含'特斯拉'"
    assert '比亚迪' in result['data'], "❌ 应该包含'比亚迪'"
    assert '蔚来' in result['data'], "❌ 应该包含'蔚来'"
    
    # 验证计数为 0
    assert result['data']['特斯拉'] == 0, "❌ '特斯拉'计数应该为 0"
    assert result['data']['比亚迪'] == 0, "❌ '比亚迪'计数应该为 0"
    assert result['data']['蔚来'] == 0, "❌ '蔚来'计数应该为 0"
    
    print("\n✅ 测试通过：空 results 时正确创建兜底数据")
    return True


def test_brand_distribution_always_has_data():
    """测试确保 distribution 永远不为空"""
    print("\n" + "="*80)
    print("测试 6: 确保 distribution 永远不为空")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 极端情况：results 为空且 expected_brands 也为空
    mock_results = []
    expected_brands = []
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    
    # 验证
    assert result['data'], "❌ distribution 不应该为空"
    assert len(result['data']) > 0, "❌ distribution 应该至少有一个品牌"
    assert 'Unknown' in result['data'], "❌ 极端情况下应该包含'Unknown'"
    
    print("\n✅ 测试通过：极端情况下也能保证 distribution 有数据")
    return True


def test_brand_distribution_mixed_sources():
    """测试混合品牌来源"""
    print("\n" + "="*80)
    print("测试 7: 混合品牌来源")
    print("="*80)
    
    service = DiagnosisReportService()
    
    # 混合来源的结果
    mock_results = [
        # extracted_brand 可用
        {'id': 1, 'brand': '特斯拉', 'extracted_brand': '特斯拉 (Tesla)', 'response': '...'},
        # extracted_brand 为空，降级到 brand
        {'id': 2, 'brand': '比亚迪', 'extracted_brand': None, 'response': '...'},
        # extracted_brand 和 brand 都为空，降级到 response
        {'id': 3, 'brand': None, 'extracted_brand': None, 'response': '蔚来是...'},
        # 所有都失败，使用 Unknown
        {'id': 4, 'brand': None, 'extracted_brand': None, 'response': '某电动汽车品牌'},
    ]
    
    expected_brands = ['特斯拉', '比亚迪', '蔚来']
    
    result = service._calculate_brand_distribution(mock_results, expected_brands)
    
    print(f"\n品牌分布结果：{result['data']}")
    print(f"总数量：{result['total_count']}")
    print(f"品牌来源分布：{result['_debug_info']['brand_source_distribution']}")
    
    # 验证
    assert '特斯拉' in result['data'], "❌ 应该包含'特斯拉'"
    assert '比亚迪' in result['data'], "❌ 应该包含'比亚迪'"
    assert '蔚来' in result['data'], "❌ 应该包含'蔚来'"
    assert 'Unknown' in result['data'], "❌ 应该包含'Unknown'"
    
    # 验证来源分布
    source_dist = result['_debug_info']['brand_source_distribution']
    assert source_dist['extracted_brand'] == 1, "❌ 应该有 1 个来自 extracted_brand"
    assert source_dist['brand'] == 1, "❌ 应该有 1 个来自 brand"
    assert source_dist['response_keyword'] == 1, "❌ 应该有 1 个来自 response_keyword"
    assert source_dist['unknown'] == 1, "❌ 应该有 1 个来自 unknown"
    
    print("\n✅ 测试通过：正确处理混合品牌来源")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("品牌分布计算修复验证测试")
    print("版本：1.0.0 (P0 关键修复)")
    print("="*80)
    
    tests = [
        ("品牌名称清理", test_clean_brand_name),
        ("优先使用 extracted_brand", test_brand_distribution_with_extracted_brand),
        ("降级到 brand 字段", test_brand_distribution_fallback_to_brand),
        ("降级到 response 提取", test_brand_distribution_fallback_to_response),
        ("空 results 兜底", test_brand_distribution_empty_results),
        ("distribution 永远不为空", test_brand_distribution_always_has_data),
        ("混合品牌来源", test_brand_distribution_mixed_sources),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  开始测试：{test_name}")
            if test_func():
                passed += 1
                print(f"✅ 测试通过：{test_name}")
            else:
                print(f"❌ 测试失败：{test_name}")
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常：{test_name}")
            print(f"   错误：{str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"测试总结：")
    print(f"  通过：{passed}/{len(tests)}")
    print(f"  失败：{failed}/{len(tests)}")
    print("="*80)
    
    if failed == 0:
        print("\n✅ 所有测试通过！品牌分布计算修复验证成功！")
        print("\n关键改进：")
        print("1. ✅ 新增 _clean_brand_name 方法，清理括号和后缀")
        print("2. ✅ 4 层降级策略：extracted_brand → brand → response → Unknown")
        print("3. ✅ 确保 distribution 永远不为空")
        print("4. ✅ 添加详细的调试信息，便于前端降级")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败，请修复问题")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
