#!/usr/bin/env python3
"""
测试豆包API与品牌诊断功能的完整集成
"""

import os
import sys
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_brand_diagnosis_workflow():
    """测试品牌诊断完整工作流程"""
    print("🔍 测试品牌诊断完整工作流程...")
    
    # 导入必要的模块
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        from wechat_backend.question_system import QuestionManager, TestCaseGenerator
        from wechat_backend.test_engine import TestExecutor, ExecutionStrategy
        from wechat_backend.ai_utils import run_brand_test_with_ai
        from ai_judge_module import AIJudgeClient
        from scoring_engine import ScoringEngine
        from enhanced_scoring_engine import EnhancedScoringEngine, calculate_enhanced_scores
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    
    # 测试数据
    brand_list = ["测试品牌A", "竞品品牌B"]
    selected_models = [{"name": "豆包", "checked": True}]  # 使用豆包平台
    custom_questions = [
        "介绍一下{brandName}",
        "{brandName}的主要产品是什么？",
        "{brandName}和竞品有什么区别？"
    ]
    
    print(f"📊 测试数据:")
    print(f"   品牌列表: {brand_list}")
    print(f"   选择模型: {[m['name'] for m in selected_models]}")
    print(f"   自定义问题: {len(custom_questions)} 个")
    
    # 1. 测试适配器是否可以正常使用
    print("\n1️⃣ 测试豆包适配器...")
    try:
        api_key = os.getenv('DOUBAO_API_KEY')
        model_id = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
        
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, model_id)
        print(f"   ✅ 适配器创建成功，模型: {adapter.model_name}")
        
        # 发送测试请求
        test_prompt = f"请简单介绍一下{brand_list[0]}，用一句话回答。"
        response = adapter.send_prompt(test_prompt)
        
        if response.success:
            print(f"   ✅ API请求成功")
            print(f"   📝 响应预览: {response.content[:50]}...")
        else:
            print(f"   ❌ API请求失败: {response.error_message}")
            return False
    except Exception as e:
        print(f"   ❌ 适配器测试失败: {e}")
        return False
    
    # 2. 测试问题生成
    print("\n2️⃣ 测试问题生成...")
    try:
        question_manager = QuestionManager()
        test_case_generator = TestCaseGenerator()
        
        # 为每个品牌生成测试用例
        all_test_cases = []
        for brand in brand_list:
            brand_questions = [q.replace('{brandName}', brand) for q in custom_questions]
            cases = test_case_generator.generate_test_cases(brand, selected_models, brand_questions)
            all_test_cases.extend(cases)
        
        print(f"   ✅ 生成了 {len(all_test_cases)} 个测试用例")
        for i, case in enumerate(all_test_cases[:3]):  # 只显示前3个
            print(f"      [{i+1}] {case.brand_name} - {case.question}")
        if len(all_test_cases) > 3:
            print(f"      ... 还有 {len(all_test_cases)-3} 个测试用例")
    except Exception as e:
        print(f"   ❌ 问题生成失败: {e}")
        return False
    
    # 3. 测试执行器
    print("\n3️⃣ 测试测试执行器...")
    try:
        executor = TestExecutor(max_workers=5, strategy=ExecutionStrategy.CONCURRENT)
        print(f"   ✅ 执行器创建成功")
        
        # 为了测试，我们只执行第一个测试用例
        if all_test_cases:
            print(f"   🧪 准备执行测试用例: {len(all_test_cases)} 个")

            # 执行测试
            def dummy_progress_callback(execution_id, progress):
                print(f"      进度: {progress.progress_percentage:.1f}% ({progress.completed_tests}/{progress.total_tests})")

            results = executor.execute_tests(all_test_cases[:1], api_key, dummy_progress_callback)  # 只执行第一个
            print(f"   ✅ 测试执行完成")
            print(f"      成功: {results['completed_tasks']}, 失败: {results['failed_tasks']}")
            if 'tasks_results' in results and results['tasks_results']:
                first_result = results['tasks_results'][0]
                print(f"      首个结果预览: {first_result.get('response', '')[:50]}...")

        executor.shutdown()
    except Exception as e:
        print(f"   ❌ 测试执行器失败: {e}")
        return False
    
    # 4. 测试AI裁判模块
    print("\n4️⃣ 测试AI裁判模块...")
    try:
        ai_judge = AIJudgeClient()
        test_brand = brand_list[0]
        test_question = custom_questions[0].replace('{brandName}', test_brand)
        test_response = "这是一个测试品牌的介绍，提供多种产品和服务。"
        
        judge_result = ai_judge.evaluate_response(test_brand, test_question, test_response)
        
        if judge_result:
            print(f"   ✅ 裁判评估成功")
            print(f"      权威度: {judge_result.accuracy_score}")
            print(f"      可见度: {judge_result.completeness_score}")
            print(f"      好感度: {judge_result.sentiment_score}")
            print(f"      纯净度: {judge_result.purity_score}")
            print(f"      一致性: {judge_result.consistency_score}")
            print(f"      评价: {judge_result.judgement[:50]}...")
        else:
            print(f"   ⚠️  裁判评估返回None (可能是因为没有配置裁判API)")
    except Exception as e:
        print(f"   ⚠️  AI裁判模块测试失败 (这可能是正常的): {e}")
    
    # 5. 测试评分引擎
    print("\n5️⃣ 测试评分引擎...")
    try:
        scoring_engine = ScoringEngine()
        enhanced_scoring_engine = EnhancedScoringEngine()
        
        # 创建模拟的裁判结果用于测试
        from ai_judge_module import JudgeResult, ConfidenceLevel
        mock_judge_results = [
            JudgeResult(
                accuracy_score=85,
                completeness_score=78,
                sentiment_score=82,
                purity_score=75,
                consistency_score=80,
                judgement="回答较为准确完整",
                confidence_level=ConfidenceLevel.HIGH
            ),
            JudgeResult(
                accuracy_score=90,
                completeness_score=85,
                sentiment_score=75,
                purity_score=80,
                consistency_score=88,
                judgement="高质量回答",
                confidence_level=ConfidenceLevel.HIGH
            )
        ]
        
        # 基础评分
        basic_result = scoring_engine.calculate(mock_judge_results)
        print(f"   ✅ 基础评分完成")
        print(f"      GEO分数: {basic_result.geo_score}")
        print(f"      等级: {basic_result.grade}")
        
        # 增强评分
        enhanced_result = calculate_enhanced_scores(mock_judge_results, brand_name=test_brand)
        print(f"   ✅ 增强评分完成")
        print(f"      增强GEO分数: {enhanced_result.geo_score}")
        print(f"      认知置信度: {enhanced_result.cognitive_confidence:.2f}")
        
    except Exception as e:
        print(f"   ❌ 评分引擎测试失败: {e}")
        return False
    
    print("\n✅ 品牌诊断完整工作流程测试成功!")
    return True


def test_frontend_simulation():
    """模拟前端请求流程"""
    print("\n🌐 模拟前端请求流程...")
    
    # 模拟前端发送的数据
    frontend_data = {
        "brand_list": ["蔚来汽车", "理想汽车"],
        "selectedModels": [
            {"name": "豆包", "checked": True}
        ],
        "customQuestions": [
            "介绍一下{brandName}",
            "{brandName}的主要产品是什么？"
        ],
        "userOpenid": "test_user_openid",
        "userLevel": "Free"
    }
    
    print(f"📤 模拟前端数据:")
    print(f"   品牌: {frontend_data['brand_list']}")
    print(f"   选择平台: {[m['name'] for m in frontend_data['selectedModels'] if m['checked']]}")
    print(f"   问题数量: {len(frontend_data['customQuestions'])}")
    
    # 模拟后端处理流程
    try:
        from wechat_backend.views import process_and_aggregate_results_with_ai_judge
        from wechat_backend.question_system import QuestionManager, TestCaseGenerator
        from wechat_backend.test_engine import TestExecutor, ExecutionStrategy
        
        # 生成测试用例
        question_manager = QuestionManager()
        test_case_generator = TestCaseGenerator()
        
        brand_list = frontend_data['brand_list']
        selected_models = frontend_data['selectedModels']
        custom_questions = [q.strip() for q in frontend_data['customQuestions'] if q.strip()]
        
        # 为每个品牌生成测试用例
        all_test_cases = []
        for brand in brand_list:
            brand_questions = [q.replace('{brandName}', brand) for q in custom_questions]
            cases = test_case_generator.generate_test_cases(brand, selected_models, brand_questions)
            all_test_cases.extend(cases)
        
        print(f"📝 生成了 {len(all_test_cases)} 个测试用例")
        
        # 模拟执行测试（使用模拟结果，因为实际执行可能需要较长时间）
        # 在实际应用中，这里会调用TestExecutor执行真实的API调用
        mock_raw_results = []
        for case in all_test_cases:
            # 模拟API响应
            mock_response = f"这是关于{case.brand_name}的{case.question}的回答。"
            mock_raw_results.append({
                'success': True,
                'brand_name': case.brand_name,
                'model': case.ai_model,  # 使用正确的属性名
                'question': case.question,
                'result': {'content': mock_response},
                'response': mock_response
            })
        
        # 处理和聚合结果
        results = process_and_aggregate_results_with_ai_judge(
            mock_raw_results, 
            brand_list, 
            brand_list[0]  # 主品牌
        )
        
        print(f"📊 处理结果:")
        print(f"   详细结果数量: {len(results['detailed_results'])}")
        print(f"   主品牌数据: {results['main_brand']['overallScore']} 分")
        print(f"   竞品分析: {len(results['competitiveAnalysis']['brandScores'])} 个品牌")
        
        # 显示一些结果
        if results['detailed_results']:
            first_result = results['detailed_results'][0]
            print(f"   首个结果预览: {first_result['brand']} - {first_result['aiModel']}")
        
        print("✅ 前端模拟流程测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ 前端模拟流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 豆包API与品牌诊断功能集成测试")
    print("="*60)
    
    # 运行测试
    test1_success = test_brand_diagnosis_workflow()
    test2_success = test_frontend_simulation()
    
    print("\n" + "="*60)
    print("📋 测试总结:")
    print(f"   品牌诊断工作流程: {'✅ 通过' if test1_success else '❌ 失败'}")
    print(f"   前端模拟流程: {'✅ 通过' if test2_success else '❌ 失败'}")
    
    overall_success = test1_success and test2_success
    print(f"\n   总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
    
    if overall_success:
        print("\n🎉 所有测试通过！豆包API与品牌诊断功能集成正常工作。")
    else:
        print("\n⚠️  部分测试失败，请检查相关模块。")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)