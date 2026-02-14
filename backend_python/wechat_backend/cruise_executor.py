"""
巡航执行器 - 执行定时诊断任务
"""
import json
from datetime import datetime
from typing import List, Dict, Any
from .logging_config import api_logger
from .database import save_test_record
from .test_engine import TestExecutor, ExecutionStrategy
from .question_system import QuestionManager, TestCaseGenerator
from .ai_utils import get_ai_client
from .recommendation_generator import RecommendationGenerator
from .cruise_controller import CruiseController


def run_diagnostic_task(
    user_openid: str,
    brand_name: str,
    ai_models: List[str],
    questions: List[str] = None
) -> Dict[str, Any]:
    """
    执行诊断任务

    Args:
        user_openid: 用户openid
        brand_name: 品牌名称
        ai_models: AI模型列表
        questions: 问题列表

    Returns:
        Dict: 任务执行结果
    """
    logger = api_logger
    logger.info(f"Running diagnostic task for brand: {brand_name}, user: {user_openid}")

    try:
        # 如果没有提供自定义问题，使用默认问题
        if not questions or len(questions) == 0:
            questions = [
                f"介绍一下{brand_name}",
                f"{brand_name}的主要产品是什么",
                f"{brand_name}和竞品有什么区别"
            ]

        # 创建测试执行器
        executor = TestExecutor(max_workers=3, strategy=ExecutionStrategy.CONCURRENT)

        # 创建测试用例
        test_case_generator = TestCaseGenerator()
        all_test_cases = []

        for model in ai_models:
            for question in questions:
                # 为每个模型和问题组合创建测试用例
                test_case = {
                    'brand_name': brand_name,
                    'question': question,
                    'model': model,
                    'api_key': ''  # 实际应用中应从配置获取
                }
                all_test_cases.append(test_case)

        # 执行测试
        def progress_callback(exec_id, progress):
            logger.debug(f"Progress for {exec_id}: {progress.progress_percentage}%")

        # 这里需要模拟执行测试的过程
        # 实际实现中，这将调用AI模型并收集结果
        results = []
        for test_case in all_test_cases:
            # 模拟AI调用
            result = {
                'success': True,
                'brand': test_case['brand_name'],
                'aiModel': test_case['model'],
                'question': test_case['question'],
                'response': f"这是一个关于{brand_name}的模拟响应",
                'score': 85,  # 模拟分数
                'sentiment_score': 75  # 模拟情感分数
            }
            results.append(result)

        # 计算整体指标
        overall_score = sum(r.get('score', 0) for r in results) / len(results) if results else 0
        total_tests = len(results)

        # 保存测试记录
        record_id = save_test_record(
            user_openid=user_openid,
            brand_name=brand_name,
            ai_models_used=ai_models,
            questions_used=questions,
            overall_score=overall_score,
            total_tests=total_tests,
            results_summary={'completed': total_tests, 'avg_score': overall_score},
            detailed_results=results
        )

        logger.info(f"Diagnostic task completed for brand: {brand_name}, record_id: {record_id}")

        # 创建巡航控制器实例以进行比较
        cruise_controller = CruiseController()
        comparison_result = cruise_controller.compare_with_previous_result(record_id, brand_name)

        result = {
            'status': 'success',
            'record_id': record_id,
            'brand_name': brand_name,
            'overall_score': overall_score,
            'total_tests': total_tests,
            'timestamp': datetime.now().isoformat(),
            'comparison_result': comparison_result
        }

        # 如果有警报，记录日志
        if comparison_result.get('is_alert', False):
            logger.warning(f"ALERT triggered for brand {brand_name}: {comparison_result.get('alert_reasons', [])}")

        return result

    except Exception as e:
        logger.error(f"Error running diagnostic task for brand {brand_name}: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'brand_name': brand_name,
            'timestamp': datetime.now().isoformat()
        }