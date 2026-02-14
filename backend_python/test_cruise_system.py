"""
测试自动化巡航系统功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.cruise_controller import CruiseController
from wechat_backend.database import save_test_record
import json
from datetime import datetime, timedelta


def test_cruise_controller_initialization():
    """测试巡航控制器初始化"""
    print("=== 测试巡航控制器初始化 ===")
    
    try:
        controller = CruiseController()
        print("✓ 巡航控制器初始化成功")
        return True
    except Exception as e:
        print(f"✗ 巡航控制器初始化失败: {e}")
        return False


def test_schedule_and_cancel_task():
    """测试调度和取消任务"""
    print("\n=== 测试调度和取消任务 ===")
    
    controller = CruiseController()
    
    try:
        # 调度一个任务
        job_id = controller.schedule_diagnostic_task(
            user_openid="test_user_123",
            brand_name="测试品牌",
            interval_hours=1,
            ai_models=["qwen", "doubao"]
        )
        
        print(f"✓ 成功调度任务，作业ID: {job_id}")
        
        # 获取已调度的任务
        scheduled_tasks = controller.get_scheduled_tasks()
        print(f"✓ 当前有 {len(scheduled_tasks)} 个已调度任务")
        
        # 取消任务
        controller.cancel_scheduled_task(job_id)
        print("✓ 成功取消任务")
        
        return True
    except Exception as e:
        print(f"✗ 任务调度/取消测试失败: {e}")
        return False


def test_compare_results():
    """测试结果比较功能"""
    print("\n=== 测试结果比较功能 ===")
    
    controller = CruiseController()
    
    # 创建模拟的当前和先前结果
    current_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 3,  # 当前排名
                    'sentiment_score': 70  # 当前情感分数
                }
            }
        },
        'evidence_chain': []  # 当前没有负面证据
    }
    
    previous_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 1,  # 之前排名
                    'sentiment_score': 80  # 之前情感分数
                }
            }
        },
        'evidence_chain': [
            {'negative_fragment': '质量问题', 'risk_level': 'High'}
        ]  # 之前有负面证据
    }
    
    try:
        comparison = controller.compare_results(current_result, previous_result)
        
        print(f"比较结果: {comparison}")
        
        # 验证是否正确检测到排名下降
        if comparison['is_alert'] and '排名下降了 2 名' in comparison['alert_reasons']:
            print("✓ 正确检测到排名下降并触发警报")
        else:
            print("✗ 未能正确检测排名下降")
            
        # 验证是否正确检测到情感分数下降
        if '情感分数下降了 10.00 分' in comparison['alert_reasons']:
            print("✓ 正确检测到情感分数下降")
        else:
            print("✗ 未能正确检测情感分数下降")
            
        # 验证是否正确检测到负面评价减少
        if '负面评价数增加了 -1 个' in str(comparison['changes']):  # 从1个减少到0个
            print("✓ 正确检测到负面评价数变化")
        else:
            print("✗ 未能正确检测负面评价数变化")
        
        return True
    except Exception as e:
        print(f"✗ 结果比较测试失败: {e}")
        return False


def test_trend_data_retrieval():
    """测试趋势数据检索"""
    print("\n=== 测试趋势数据检索 ===")
    
    controller = CruiseController()
    
    # 创建一些测试数据
    user_openid = "test_user_trends"
    brand_name = "趋势测试品牌"
    
    # 创建几个测试记录
    for i in range(3):
        test_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 创建模拟的详细结果
        detailed_results = [
            {
                'brand': brand_name,
                'sentiment_score': 70 + i*5,  # 每次递增情感分数
                'response': f'这是第{i+1}次测试的响应'
            }
        ]
        
        # 创建模拟的结果摘要
        results_summary = {
            'completed': 1,
            'avg_score': 80 + i*2,
            'ranking_list': [brand_name]
        }
        
        save_test_record(
            user_openid=user_openid,
            brand_name=brand_name,
            ai_models_used=["qwen"],
            questions_used=["测试问题"],
            overall_score=80 + i*2,
            total_tests=1,
            results_summary=results_summary,
            detailed_results=detailed_results
        )
    
    try:
        # 获取趋势数据
        trend_data = controller.get_trend_data(brand_name, days=7)
        
        print(f"获取到 {len(trend_data)} 条趋势数据")
        
        for i, data_point in enumerate(trend_data):
            print(f"  数据点 {i+1}: {data_point['timestamp']}, "
                  f"综合分数: {data_point['overall_score']}, "
                  f"情感分数: {data_point['sentiment_score']}, "
                  f"排名: {data_point['rank']}")
        
        if len(trend_data) > 0:
            print("✓ 成功获取趋势数据")
            return True
        else:
            print("✗ 未能获取趋势数据")
            return False
    except Exception as e:
        print(f"✗ 趋势数据检索测试失败: {e}")
        return False


def test_alert_triggering_on_rank_drop():
    """测试排名下降2名时触发警报"""
    print("\n=== 专项测试：排名下降2名时触发警报 ===")
    
    controller = CruiseController()
    
    # 模拟前一次排名为第1名，当前排名为第3名（下降2名）
    current_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 3,  # 当前排名
                    'sentiment_score': 75
                }
            }
        },
        'evidence_chain': []
    }
    
    previous_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 1,  # 之前排名
                    'sentiment_score': 75
                }
            }
        },
        'evidence_chain': []
    }
    
    try:
        comparison = controller.compare_results(current_result, previous_result)
        
        print(f"排名变化: {comparison['changes'].get('rank_change', 'N/A')}")
        print(f"是否触发警报: {comparison['is_alert']}")
        print(f"警报原因: {comparison['alert_reasons']}")
        
        if comparison['is_alert'] and '排名下降了 2 名' in comparison['alert_reasons']:
            print("✓ 正确在排名下降2名时触发警报")
            return True
        else:
            print("✗ 未能在排名下降2名时正确触发警报")
            return False
    except Exception as e:
        print(f"✗ 排名下降警报测试失败: {e}")
        return False


def test_no_alert_when_rank_stable():
    """测试排名稳定时不触发警报"""
    print("\n=== 专项测试：排名稳定时不触发警报 ===")
    
    controller = CruiseController()
    
    # 模拟前后排名相同
    current_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 2,  # 当前排名
                    'sentiment_score': 75
                }
            }
        },
        'evidence_chain': []
    }
    
    previous_result = {
        'exposure_analysis': {
            'brand_details': {
                '测试品牌': {
                    'rank': 2,  # 之前排名
                    'sentiment_score': 75
                }
            }
        },
        'evidence_chain': []
    }
    
    try:
        comparison = controller.compare_results(current_result, previous_result)
        
        print(f"排名变化: {comparison['changes'].get('rank_change', 'N/A')}")
        print(f"是否触发警报: {comparison['is_alert']}")
        print(f"警报原因: {comparison['alert_reasons']}")
        
        if not comparison['is_alert']:
            print("✓ 正确在排名稳定时不触发警报")
            return True
        else:
            print("✗ 在排名稳定时错误地触发了警报")
            return False
    except Exception as e:
        print(f"✗ 排名稳定测试失败: {e}")
        return False


def run_all_cruise_tests():
    """运行所有巡航系统测试"""
    print("开始运行自动化巡航系统测试套件...\n")
    
    tests = [
        test_cruise_controller_initialization,
        test_schedule_and_cancel_task,
        test_compare_results,
        test_trend_data_retrieval,
        test_alert_triggering_on_rank_drop,
        test_no_alert_when_rank_stable
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n=== 测试总结 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有巡航系统测试通过！")
        return True
    else:
        print("✗ 部分测试失败")
        return False


if __name__ == "__main__":
    run_all_cruise_tests()