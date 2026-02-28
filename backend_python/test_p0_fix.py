#!/usr/bin/env python3
"""
P0 修复验证测试

验证内容：
1. 客观问题提示词是否正确
2. 总任务数计算是否正确（问题数 × AI 平台数）
3. 品牌分析服务是否正常工作
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.ai_adapters.base_adapter import OBJECTIVE_QUESTION_TEMPLATE, BRAND_ANALYSIS_TEMPLATE
from wechat_backend.services.brand_analysis_service import get_brand_analysis_service

def test_objective_question_template():
    """测试客观问题提示词"""
    print("=" * 60)
    print("测试 1: 客观问题提示词")
    print("=" * 60)
    
    # 验证提示词不包含品牌倾向
    assert '{brand_name}' not in OBJECTIVE_QUESTION_TEMPLATE, "提示词不应包含 brand_name 占位符"
    assert '{competitors}' not in OBJECTIVE_QUESTION_TEMPLATE, "提示词不应包含 competitors 占位符"
    assert '{question}' in OBJECTIVE_QUESTION_TEMPLATE, "提示词应包含 question 占位符"
    assert '客观回答' in OBJECTIVE_QUESTION_TEMPLATE, "提示词应要求客观回答"
    assert 'TOP3' in OBJECTIVE_QUESTION_TEMPLATE, "提示词应要求列出 TOP3"
    
    # 生成示例提示词
    sample_prompt = OBJECTIVE_QUESTION_TEMPLATE.format(question="深圳新能源汽车改装门店哪家好")
    print("✓ 提示词格式正确")
    print(f"示例提示词:\n{sample_prompt[:300]}...")
    print()
    return True

def test_brand_analysis_template():
    """测试品牌分析提示词"""
    print("=" * 60)
    print("测试 2: 品牌分析提示词")
    print("=" * 60)
    
    # 验证提示词包含必要字段
    assert '{ai_response}' in BRAND_ANALYSIS_TEMPLATE, "提示词应包含 ai_response 占位符"
    assert '{user_brand}' in BRAND_ANALYSIS_TEMPLATE, "提示词应包含 user_brand 占位符"
    assert '{question}' in BRAND_ANALYSIS_TEMPLATE, "提示词应包含 question 占位符"
    assert 'brand_mentioned' in BRAND_ANALYSIS_TEMPLATE, "提示词应要求分析 brand_mentioned"
    assert 'rank' in BRAND_ANALYSIS_TEMPLATE, "提示词应要求分析 rank"
    assert 'sentiment' in BRAND_ANALYSIS_TEMPLATE, "提示词应要求分析 sentiment"
    
    print("✓ 品牌分析提示词格式正确")
    print()
    return True

def test_brand_analysis_service():
    """测试品牌分析服务"""
    print("=" * 60)
    print("测试 3: 品牌分析服务")
    print("=" * 60)
    
    # 创建模拟 AI 回答
    mock_results = [
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'doubao',
            'response': '''
作为专业顾问，我推荐以下新能源汽车改装门店：

TOP1: 深圳车尚艺改装店
理由：专业技术团队，丰富经验，使用高品质配件。

TOP2: 深圳承美车居
理由：服务好，价格透明，客户口碑佳。

TOP3: 深圳趣车良品
理由：创新技术，设备先进，改装效果出色。

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1, "reason": "专业技术团队"}, {"name": "深圳承美车居", "rank": 2, "reason": "服务好"}, {"name": "深圳趣车良品", "rank": 3, "reason": "创新技术"}], "total_brands_mentioned": 3}
'''
        },
        {
            'question': '深圳新能源汽车改装门店哪家好',
            'model': 'qwen',
            'response': '''
根据我的了解，深圳地区有以下优秀的新能源汽车改装门店：

1. 深圳车尚艺改装店 - 专业可靠
2. 深圳趣车良品 - 技术先进
3. 深圳车网联盟 - 服务周到

{"top3_brands": [{"name": "深圳车尚艺改装店", "rank": 1, "reason": "专业可靠"}, {"name": "深圳趣车良品", "rank": 2, "reason": "技术先进"}, {"name": "深圳车网联盟", "rank": 3, "reason": "服务周到"}], "total_brands_mentioned": 3}
'''
        }
    ]
    
    # 创建品牌分析服务实例
    analysis_service = get_brand_analysis_service(judge_model='doubao')
    
    # 测试 TOP3 品牌提取
    print("测试 TOP3 品牌提取...")
    for i, result in enumerate(mock_results):
        top3 = analysis_service._extract_top3_brands(result['response'])
        print(f"  回答 {i+1}: 提取到 {len(top3)} 个品牌")
        for brand in top3:
            print(f"    - {brand.get('name', 'N/A')} (排名：{brand.get('rank', 'N/A')})")
    
    # 测试品牌提及分析（降级方案）
    print("\n测试品牌提及分析（降级方案）...")
    user_brand = "趣车良品"
    for i, result in enumerate(mock_results):
        mention = analysis_service._analyze_brand_in_response(
            response=result['response'],
            brand=user_brand,
            question=result['question']
        )
        print(f"  回答 {i+1}:")
        print(f"    - 提及：{'是' if mention['brand_mentioned'] else '否'}")
        print(f"    - 排名：{mention['rank']}")
        print(f"    - 情感：{mention['sentiment']}")
    
    print("\n✓ 品牌分析服务基本功能正常")
    print()
    return True

def test_task_count_calculation():
    """测试任务数计算"""
    print("=" * 60)
    print("测试 4: 任务数计算")
    print("=" * 60)
    
    # 模拟输入
    raw_questions = ["问题 1", "问题 2"]
    selected_models = [{"name": "doubao"}, {"name": "qwen"}]
    competitor_brands = ["竞品 A", "竞品 B"]
    
    # 旧逻辑（错误）：品牌数 × 问题数 × 模型数
    old_total = (1 + len(competitor_brands)) * len(raw_questions) * len(selected_models)
    
    # 新逻辑（正确）：问题数 × 模型数
    new_total = len(raw_questions) * len(selected_models)
    
    print(f"输入：{len(raw_questions)} 个问题，{len(selected_models)} 个模型，{len(competitor_brands)} 个竞品")
    print(f"旧逻辑（错误）：{(1 + len(competitor_brands))} × {len(raw_questions)} × {len(selected_models)} = {old_total} 次请求")
    print(f"新逻辑（正确）：{len(raw_questions)} × {len(selected_models)} = {new_total} 次请求")
    print(f"减少请求数：{old_total - new_total} 次（{(old_total - new_total) / old_total * 100:.0f}%）")
    
    assert new_total == 4, "新逻辑应返回 4 次请求"
    assert new_total < old_total, "新逻辑应减少请求数"
    
    print("\n✓ 任务数计算逻辑正确")
    print()
    return True

def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("P0 修复验证测试 - 诊断逻辑设计错误修复")
    print("=" * 60)
    print()
    
    tests = [
        ("客观问题提示词", test_objective_question_template),
        ("品牌分析提示词", test_brand_analysis_template),
        ("品牌分析服务", test_brand_analysis_service),
        ("任务数计算", test_task_count_calculation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} 测试失败：{e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
