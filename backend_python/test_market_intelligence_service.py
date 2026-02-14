"""
测试市场情报服务功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.market_intelligence_service import MarketIntelligenceService
from wechat_backend.database import save_test_record
import json
from datetime import datetime, timedelta


def test_market_intelligence_service():
    """测试市场情报服务功能"""
    print("=== 测试市场情报服务功能 ===")
    
    service = MarketIntelligenceService()
    
    # 创建一些测试数据
    user_openid = "test_user_market_intel"
    
    # 创建多个品牌的测试记录
    brands_data = [
        {
            'brand_name': '品牌A',
            'questions_used': ['问题1', '问题2', '问题3'],
            'detailed_results': [
                {'brand': '品牌A', 'sentiment_score': 80, 'response': '正面评价'},
                {'brand': '品牌A', 'sentiment_score': 85, 'response': '正面评价'},
                {'brand': '品牌A', 'sentiment_score': 75, 'response': '中性评价'}
            ],
            'results_summary': {
                'brand_details': {
                    '品牌A': {'rank': 1, 'sentiment_score': 80}
                },
                'ranking_list': ['品牌A', '品牌B', '品牌C']
            }
        },
        {
            'brand_name': '品牌B',
            'questions_used': ['问题1', '问题2', '问题3'],
            'detailed_results': [
                {'brand': '品牌B', 'sentiment_score': 70, 'response': '中性评价'},
                {'brand': '品牌B', 'sentiment_score': 65, 'response': '略负面评价'},
                {'brand': '品牌B', 'sentiment_score': 75, 'response': '中性评价'}
            ],
            'results_summary': {
                'brand_details': {
                    '品牌B': {'rank': 2, 'sentiment_score': 70}
                },
                'ranking_list': ['品牌A', '品牌B', '品牌C']
            }
        },
        {
            'brand_name': '品牌C',
            'questions_used': ['问题1', '问题2', '问题3'],
            'detailed_results': [
                {'brand': '品牌C', 'sentiment_score': 60, 'response': '负面评价'},
                {'brand': '品牌C', 'sentiment_score': 65, 'response': '中性评价'},
                {'brand': '品牌C', 'sentiment_score': 55, 'response': '负面评价'}
            ],
            'results_summary': {
                'brand_details': {
                    '品牌C': {'rank': 3, 'sentiment_score': 60}
                },
                'ranking_list': ['品牌A', '品牌B', '品牌C']
            }
        }
    ]
    
    # 保存测试数据到数据库
    for brand_data in brands_data:
        save_test_record(
            user_openid=user_openid,
            brand_name=brand_data['brand_name'],
            ai_models_used=["qwen"],
            questions_used=brand_data['questions_used'],
            overall_score=brand_data['results_summary']['brand_details'][brand_data['brand_name']]['sentiment_score'],
            total_tests=len(brand_data['questions_used']),
            results_summary=brand_data['results_summary'],
            detailed_results=brand_data['detailed_results']
        )
    
    # 测试计算品类基准
    try:
        result = service.calculate_category_benchmarks(
            brand_name='品牌A',
            category=None,  # 暂时不用类别
            days=30
        )
        
        print(f"计算结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 验證結果
        benchmark_data = result.get('benchmark_data', {})
        my_brand_data = result.get('my_brand_data', {})
        all_brands_comparison = result.get('all_brands_comparison', [])
        
        print(f"\n品类基准数据:")
        print(f"  平均排名位置: {benchmark_data.get('avg_rank_position')}")
        print(f"  平均情感得分: {benchmark_data.get('avg_sentiment_score')}")
        
        print(f"\n我方品牌数据 (品牌A):")
        print(f"  排名位置: {my_brand_data.get('rank_position')}")
        print(f"  情感位置: {my_brand_data.get('sentiment_position')}")
        print(f"  心智占有率: {my_brand_data.get('mind_share')}%")
        print(f"  提及次数: {my_brand_data.get('mention_count')}")
        print(f"  总查询次数: {my_brand_data.get('total_queries')}")
        
        print(f"\n所有品牌对比:")
        for brand_comp in all_brands_comparison:
            print(f"  {brand_comp['brand_name']}: 平均排名={brand_comp['avg_rank']}, "
                  f"平均情感={brand_comp['avg_sentiment_score']}, 提及次数={brand_comp['mention_count']}")
        
        print("✓ 市场情报服务功能测试成功")
        return True
        
    except Exception as e:
        print(f"✗ 市场情报服务功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sparse_data_handling():
    """测试稀疏数据处理"""
    print("\n=== 测试稀疏数据处理 ===")
    
    service = MarketIntelligenceService()
    
    # 创建稀疏数据（部分品牌缺少某些数据）
    sparse_brands_data = [
        {
            'brand_name': '稀疏品牌A',
            'questions_used': ['问题1'],
            'detailed_results': [
                {'brand': '稀疏品牌A', 'sentiment_score': 90, 'response': '正面评价'}
            ],
            'results_summary': {
                'brand_details': {
                    '稀疏品牌A': {'rank': 1}
                },
                'ranking_list': ['稀疏品牌A', '稀疏品牌B']
            }
        },
        {
            'brand_name': '稀疏品牌B',
            'questions_used': ['问题1'],
            'detailed_results': [
                {'brand': '稀疏品牌B', 'sentiment_score': 40, 'response': '负面评价'}
            ],
            'results_summary': {
                'brand_details': {
                    '稀疏品牌B': {}  # 缺少排名和情感分数
                },
                'ranking_list': ['稀疏品牌A', '稀疏品牌B']
            }
        }
    ]
    
    # 保存稀疏数据
    user_openid = "test_user_sparse"
    for brand_data in sparse_brands_data:
        save_test_record(
            user_openid=user_openid,
            brand_name=brand_data['brand_name'],
            ai_models_used=["qwen"],
            questions_used=brand_data['questions_used'],
            overall_score=brand_data['results_summary']['brand_details'].get(brand_data['brand_name'], {}).get('sentiment_score', 0),
            total_tests=len(brand_data['questions_used']),
            results_summary=brand_data['results_summary'],
            detailed_results=brand_data['detailed_results']
        )
    
    try:
        result = service.calculate_category_benchmarks(
            brand_name='稀疏品牌A',
            category=None,
            days=30
        )
        
        print(f"稀疏数据处理结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
        
        # 驗證系統能夠處理稀疏數據而不崩潰
        benchmark_data = result.get('benchmark_data', {})
        my_brand_data = result.get('my_brand_data', {})
        
        print(f"  基准数据: {benchmark_data}")
        print(f"  我方品牌数据: {my_brand_data}")
        
        print("✓ 稀疏数据处理测试成功")
        return True
        
    except Exception as e:
        print(f"✗ 稀疏数据处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_data_handling():
    """测试空数据处理"""
    print("\n=== 测试空数据处理 ===")
    
    service = MarketIntelligenceService()
    
    try:
        result = service.calculate_category_benchmarks(
            brand_name='不存在的品牌',
            category=None,
            days=1  # 使用1天以确保没有历史数据
        )
        
        print(f"空数据处理结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 驗證系統能夠處理空數據而不崩潰
        my_brand_data = result.get('my_brand_data', {})
        
        if my_brand_data.get('brand_name') == '不存在的品牌':
            print("✓ 空数据处理测试成功")
            return True
        else:
            print("✗ 空数据处理测试失败")
            return False
        
    except Exception as e:
        print(f"✗ 空数据处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("开始运行市场情报服务测试套件...\n")
    
    tests = [
        test_market_intelligence_service,
        test_sparse_data_handling,
        test_empty_data_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n=== 测试总结 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有市场情报服务测试通过！")
        return True
    else:
        print("✗ 部分测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n🎉 市場情報服務測試完成！")
    else:
        print("\n⚠️  市場情報服務測試發現問題！")