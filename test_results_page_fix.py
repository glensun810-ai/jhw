"""
测试端到端的工作流程，确保结果页面能显示数据
"""

import os
import asyncio
from wechat_backend.question_system import TestCaseGenerator
from wechat_backend.test_engine import TestExecutor
from wechat_backend.views import process_and_aggregate_results_with_ai_judge


def test_end_to_end_workflow():
    """测试端到端工作流程"""
    print("=== 测试端到端工作流程 ===")
    
    # 设置API密钥
    os.environ['DEEPSEEK_API_KEY'] = 'sk-13908093890f46fb82c52a01c8dfc464'
    os.environ['QWEN_API_KEY'] = 'sk-5261a4dfdf964a5c9a6364128cc4c653'
    os.environ['ZHIPU_API_KEY'] = '504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh'
    
    try:
        # 1. 生成测试用例
        print("1. 生成测试用例...")
        generator = TestCaseGenerator()
        ai_models = [
            {"name": "DeepSeek", "checked": True},
            {"name": "通义千问", "checked": True}
        ]
        questions = [
            "介绍一下测试品牌",
            "测试品牌的主要产品是什么"
        ]
        brand_name = "测试品牌"
        
        test_cases = generator.generate_test_cases(brand_name, ai_models, questions)
        print(f"   生成了 {len(test_cases)} 个测试用例")
        
        # 2. 执行测试
        print("2. 执行测试...")
        executor = TestExecutor(max_workers=5)
        
        def progress_callback(exec_id, progress):
            print(f"   进度: {progress.progress_percentage}% ({progress.completed_tests}/{progress.total_tests})")
        
        # 使用部分测试用例进行快速测试
        subset_test_cases = test_cases[:2]  # 只测试前2个用例
        results = executor.execute_tests(subset_test_cases, "", progress_callback)
        
        print(f"   测试完成 - 成功: {results['completed_tasks']}, 失败: {results['failed_tasks']}")
        
        # 3. 处理和聚合结果
        print("3. 处理和聚合结果...")
        all_brands = [brand_name]
        main_brand = brand_name
        
        processed_results = process_and_aggregate_results_with_ai_judge(results, all_brands, main_brand)
        
        print(f"   处理完成 - 详细结果数: {len(processed_results['detailed_results'])}")
        print(f"   主品牌得分: {processed_results['main_brand']['overallScore']}")
        print(f"   品牌总数: {len(processed_results['competitiveAnalysis']['brandScores'])}")
        
        # 4. 检查结果是否包含必要的数据
        print("4. 验证结果数据...")
        has_data = len(processed_results['detailed_results']) > 0
        has_scores = processed_results['main_brand']['overallScore'] > 0
        has_brand_scores = len(processed_results['competitiveAnalysis']['brandScores']) > 0
        
        print(f"   有详细结果: {has_data}")
        print(f"   有主品牌得分: {has_scores}")
        print(f"   有品牌评分: {has_brand_scores}")
        
        if has_data and has_scores:
            print("   ✓ 结果页面将能显示数据!")
            # 显示第一个结果的结构
            if processed_results['detailed_results']:
                first_result = processed_results['detailed_results'][0]
                print(f"   示例结果字段: {list(first_result.keys())}")
        else:
            print("   ✗ 结果页面可能无法显示数据")
        
        # 关闭执行器
        executor.shutdown()
        
        return has_data and has_scores
        
    except Exception as e:
        print(f"端到端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_judge_fallback():
    """测试AI Judge的fallback功能"""
    print("\n=== 测试AI Judge Fallback功能 ===")
    
    try:
        from ai_judge_module import AIJudgeClient
        
        # 创建AI Judge实例（会自动使用fallback API key）
        judge = AIJudgeClient()
        
        if judge.ai_client:
            print("✓ AI Judge初始化成功")
            print(f"  使用的模型: {judge.judge_model}")
            print(f"  使用的平台: {judge.judge_platform}")
            
            # 测试评估功能
            result = judge.evaluate_response(
                '测试品牌', 
                '介绍一下测试品牌', 
                '这是一个测试品牌的介绍，包含产品信息和品牌历史。'
            )
            
            if result:
                print("✓ AI Judge评估成功")
                print(f"  准确度: {result.accuracy_score}")
                print(f"  完整度: {result.completeness_score}")
                print(f"  情感分: {result.sentiment_score}")
                print(f"  纯净度: {result.purity_score}")
                print(f"  一致性: {result.consistency_score}")
                print(f"  评价: {result.judgement[:50]}...")
                return True
            else:
                print("✗ AI Judge评估失败")
                return False
        else:
            print("✗ AI Judge初始化失败")
            return False
            
    except Exception as e:
        print(f"AI Judge测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始测试端到端工作流程，确保结果页面能显示数据...\n")
    
    # 测试AI Judge功能
    judge_ok = test_ai_judge_fallback()
    
    # 测试端到端流程
    workflow_ok = test_end_to_end_workflow()
    
    print(f"\n=== 测试总结 ===")
    print(f"AI Judge功能: {'✓' if judge_ok else '✗'}")
    print(f"端到端流程: {'✓' if workflow_ok else '✗'}")
    
    if judge_ok and workflow_ok:
        print("\n✅ 所有测试通过！结果页面现在应该能显示数据了。")
        print("   修复内容:")
        print("   1. AI Judge现在会自动使用可用的API密钥作为fallback")
        print("   2. 评估流程正常工作")
        print("   3. 结果聚合正常工作")
        print("   4. 数据结构完整")
        return True
    else:
        print("\n❌ 部分测试失败。")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)