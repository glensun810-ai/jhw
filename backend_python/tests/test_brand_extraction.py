#!/usr/bin/env python3
"""
品牌提取逻辑单元测试

直接测试 _extract_recommended_brand 方法是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wechat_backend.nxm_concurrent_engine_v3 import NxMParallelExecutor

def test_brand_extraction():
    """测试品牌提取逻辑"""
    print("=" * 70)
    print("品牌提取逻辑单元测试")
    print("=" * 70)
    print()
    
    # 创建测试实例
    executor = NxMParallelExecutor(execution_id="test_001", max_concurrent=1)
    
    # 测试用例
    test_cases = [
        {
            "name": "排名列表格式",
            "content": """好的，基于我的了解，以下是我为您推荐的深圳新能源汽车改装门店：

1. **车艺尚** - 作为一家专注于高端车型个性化定制与升级服务的企业
2. **电车之家** - 作为深圳较早涉足新能源汽车改装领域的店铺
3. **车改大师** - 位于深圳市南山区，这家店以其专业的服务""",
            "main_brand": "趣车良品",
            "expected": "车艺尚"
        },
        {
            "name": "推荐语句格式",
            "content": """我推荐车艺尚这家店，他们在新能源汽车改装方面很有经验。
另外电车之家也不错，可以考虑。""",
            "main_brand": "趣车良品",
            "expected": "车艺尚"
        },
        {
            "name": "品牌提及格式",
            "content": """深圳有很多改装店，比如车艺尚改装、电车之家服务、车改大师中心
都是不错的选择。""",
            "main_brand": "趣车良品",
            "expected": "车艺尚"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[测试 {i}/{len(test_cases)}] {test_case['name']}")
        print("-" * 50)
        
        result = executor._extract_recommended_brand(
            test_case['content'],
            test_case['main_brand']
        )
        
        expected = test_case['expected']
        
        if result == expected:
            print(f"✅ 通过！提取到品牌：{result}")
            passed += 1
        else:
            print(f"❌ 失败！期望：{expected}, 实际：{result}")
            failed += 1
    
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"通过：{passed}/{len(test_cases)}")
    print(f"失败：{failed}/{len(test_cases)}")
    
    if passed == len(test_cases):
        print("\n🎉 所有测试通过！品牌提取逻辑正常工作！")
        return True
    else:
        print("\n❌ 有测试失败，请检查品牌提取逻辑")
        return False

if __name__ == '__main__':
    success = test_brand_extraction()
    sys.exit(0 if success else 1)
