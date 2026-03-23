#!/usr/bin/env python3
"""
品牌分析工作流程验证测试

验证点：
1. 用户只提交主品牌时，系统能自动从 AI 回答中提取 TOP3 作为竞品
2. 用户提交主品牌 + 竞品时，系统使用用户指定的竞品
3. 品牌分析正确执行露出、排名、情感等维度的对比

测试方式：
- 单元测试：模拟 AI 回答，验证品牌提取逻辑
- 集成测试：完整执行诊断流程，验证端到端功能

作者：系统架构组
日期：2026-03-17
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python/wechat_backend'))

from wechat_backend.services.brand_analysis_service import BrandAnalysisService
from wechat_backend.logging_config import api_logger


def test_single_brand_scenario():
    """
    测试场景 1：用户只提交主品牌
    
    预期行为：
    1. 从 AI 回答中提取 TOP3 品牌作为竞品
    2. 分析用户品牌与竞品的对比
    """
    print("\n" + "="*80)
    print("测试场景 1：用户只提交主品牌")
    print("="*80)
    
    # 模拟 AI 回答（包含多个品牌提及）
    mock_ai_responses = [
        {
            'question': '介绍一下新能源汽车品牌',
            'response': '''
            新能源汽车品牌排行榜：
            1. 特斯拉 - 全球领先的电动汽车制造商
            2. 比亚迪 - 中国最大的新能源汽车品牌
            3. 蔚来 - 高端智能电动汽车品牌
            4. 小鹏 - 智能网联汽车代表
            5. 理想 - 增程式电动车先行者
            
            其中特斯拉在品牌影响力和技术创新方面处于领先地位。
            '''
        },
        {
            'question': '新能源汽车品牌的特点',
            'response': '''
            主要新能源汽车品牌特点：
            - 特斯拉：自动驾驶技术领先，续航里程长
            - 比亚迪：电池技术自研，性价比高
            - 蔚来：用户服务好，换电模式创新
            - 小米汽车：生态整合能力强
            '''
        },
        {
            'question': '推荐新能源汽车品牌',
            'response': '''
            推荐购买的新能源汽车品牌 TOP3：
            1. 特斯拉 Model Y - 综合性能最佳
            2. 比亚迪 汉 EV - 性价比最高
            3. 蔚来 ET5 - 豪华感最强
            '''
        }
    ]
    
    # 创建品牌分析服务（不指定竞品）
    service = BrandAnalysisService()
    
    # 执行品牌分析（只传入用户品牌，不传竞品）
    result = service.analyze_brand_mentions(
        results=mock_ai_responses,
        user_brand='特斯拉',
        competitor_brands=None,  # 不指定竞品，让系统自动提取
        execution_id='test_single_brand'
    )
    
    # 验证结果
    print("\n✅ 分析结果:")
    print(f"   用户品牌：{result['user_brand_analysis']['brand']}")
    print(f"   提及率：{result['user_brand_analysis']['mention_rate']:.1%}")
    print(f"   平均排名：{result['user_brand_analysis']['average_rank']}")
    print(f"   是否 TOP3: {result['user_brand_analysis']['is_top3']}")
    
    print(f"\n   自动提取的竞品数量：{len(result['competitor_analysis'])}")
    for comp in result['competitor_analysis']:
        print(f"   - {comp['brand']}: 提及率={comp['mention_rate']:.1%}, 排名={comp['average_rank']}")
    
    print(f"\n   TOP3 品牌列表：{[b['name'] for b in result['top3_brands']]}")
    
    # 断言验证
    assert len(result['competitor_analysis']) > 0, "❌ 应该自动提取竞品品牌"
    assert len(result['top3_brands']) > 0, "❌ 应该提取到 TOP3 品牌"
    assert result['user_brand_analysis']['is_top3'], "❌ 特斯拉应该在 TOP3 中"
    
    print("\n✅ 测试通过：系统正确提取了竞品品牌并完成分析")
    return True


def test_multi_brand_scenario():
    """
    测试场景 2：用户提交主品牌 + 竞品
    
    预期行为：
    1. 使用用户指定的竞品进行分析
    2. 仍然从 AI 回答中提取 TOP3 品牌（用于参考）
    """
    print("\n" + "="*80)
    print("测试场景 2：用户提交主品牌 + 竞品")
    print("="*80)
    
    # 模拟 AI 回答（包含多个品牌提及）
    mock_ai_responses = [
        {
            'question': '介绍一下新能源汽车品牌',
            'response': '''
            新能源汽车品牌排行榜：
            1. 特斯拉 - 全球领先的电动汽车制造商
            2. 比亚迪 - 中国最大的新能源汽车品牌
            3. 蔚来 - 高端智能电动汽车品牌
            4. 小鹏 - 智能网联汽车代表
            5. 理想 - 增程式电动车先行者
            '''
        },
        {
            'question': '比较特斯拉和比亚迪',
            'response': '''
            特斯拉 vs 比亚迪对比：
            - 特斯拉：技术创新领先，品牌影响力强
            - 比亚迪：产业链完整，成本控制好
            - 两者都是新能源汽车行业的领军企业
            '''
        }
    ]
    
    # 创建品牌分析服务
    service = BrandAnalysisService()
    
    # 执行品牌分析（传入用户指定的竞品）
    result = service.analyze_brand_mentions(
        results=mock_ai_responses,
        user_brand='特斯拉',
        competitor_brands=['比亚迪', '蔚来'],  # 用户指定竞品
        execution_id='test_multi_brand'
    )
    
    # 验证结果
    print("\n✅ 分析结果:")
    print(f"   用户品牌：{result['user_brand_analysis']['brand']}")
    print(f"   提及率：{result['user_brand_analysis']['mention_rate']:.1%}")
    print(f"   平均排名：{result['user_brand_analysis']['average_rank']}")
    print(f"   是否 TOP3: {result['user_brand_analysis']['is_top3']}")
    
    print(f"\n   用户指定的竞品分析：")
    for comp in result['competitor_analysis']:
        print(f"   - {comp['brand']}: 提及率={comp['mention_rate']:.1%}, 排名={comp['average_rank']}")
    
    print(f"\n   自动提取的 TOP3 品牌（参考）：{[b['name'] for b in result['top3_brands']]}")
    
    # 断言验证
    competitor_names = [comp['brand'] for comp in result['competitor_analysis']]
    assert '比亚迪' in competitor_names, "❌ 应该分析用户指定的竞品'比亚迪'"
    assert '蔚来' in competitor_names, "❌ 应该分析用户指定的竞品'蔚来'"
    
    print("\n✅ 测试通过：系统正确使用了用户指定的竞品")
    return True


def test_brand_extraction_accuracy():
    """
    测试场景 3：验证品牌提取准确性
    
    预期行为：
    1. 正确识别 TOP3 品牌
    2. 正确提取品牌排名
    3. 正确处理品牌名称变体
    """
    print("\n" + "="*80)
    print("测试场景 3：验证品牌提取准确性")
    print("="*80)
    
    mock_ai_responses = [
        {
            'question': '智能手机品牌排名',
            'response': '''
            2026 年智能手机品牌排行榜 TOP3：
            第一名：苹果 iPhone - 高端市场领导者
            第二名：华为 - 技术创新代表
            第三名：小米 - 性价比之王
            
            其他知名品牌：OPPO、vivo、荣耀、三星
            '''
        }
    ]
    
    service = BrandAnalysisService()
    
    result = service.analyze_brand_mentions(
        results=mock_ai_responses,
        user_brand='华为',
        competitor_brands=None,
        execution_id='test_extraction_accuracy'
    )
    
    print("\n✅ 提取结果:")
    print(f"   TOP3 品牌：{[b['name'] for b in result['top3_brands']]}")
    print(f"   竞品分析数量：{len(result['competitor_analysis'])}")
    
    # 验证 TOP3 提取
    top3_names = [b['name'].lower() for b in result['top3_brands']]
    assert '苹果' in str(top3_names) or 'iphone' in str(top3_names), "❌ 应该提取到苹果/iPhone"
    assert '华为' in str(top3_names), "❌ 应该提取到华为"
    assert '小米' in str(top3_names), "❌ 应该提取到小米"
    
    print("\n✅ 测试通过：品牌提取准确")
    return True


def test_no_competitors_found():
    """
    测试场景 4：AI 回答中未提及其他品牌
    
    预期行为：
    1. 竞品列表为空
    2. 分析仍然完成，但包含降级结果
    """
    print("\n" + "="*80)
    print("测试场景 4：AI 回答中未提及其他品牌")
    print("="*80)
    
    mock_ai_responses = [
        {
            'question': '介绍一下特斯拉',
            'response': '''
            特斯拉是一家美国电动汽车及能源公司，
            由埃隆·马斯克创立。主要车型包括 Model S、
            Model 3、Model X 和 Model Y。
            '''
        }
    ]
    
    service = BrandAnalysisService()
    
    result = service.analyze_brand_mentions(
        results=mock_ai_responses,
        user_brand='特斯拉',
        competitor_brands=None,
        execution_id='test_no_competitors'
    )
    
    print("\n✅ 分析结果:")
    print(f"   用户品牌提及率：{result['user_brand_analysis']['mention_rate']:.1%}")
    print(f"   竞品数量：{len(result['competitor_analysis'])}")
    print(f"   TOP3 品牌数量：{len(result['top3_brands'])}")
    
    # 即使没有竞品，分析也应该完成
    assert result is not None, "❌ 分析结果不应该为 None"
    assert 'user_brand_analysis' in result, "❌ 应该包含用户品牌分析"
    
    print("\n✅ 测试通过：无竞品时分析仍然完成")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("品牌分析工作流程验证测试")
    print("测试目标：验证竞品品牌可选流程的正确性")
    print("="*80)
    
    tests = [
        ("单品牌场景", test_single_brand_scenario),
        ("多品牌场景", test_multi_brand_scenario),
        ("提取准确性", test_brand_extraction_accuracy),
        ("无竞品场景", test_no_competitors_found),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  开始测试：{test_name}")
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"\n❌ 测试失败：{test_name}")
            print(f"   错误：{str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n❌ 测试异常：{test_name}")
            print(f"   错误：{str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"测试总结：通过 {passed}/{len(tests)} 个测试")
    if failed > 0:
        print(f"         失败 {failed}/{len(tests)} 个测试")
    print("="*80)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
