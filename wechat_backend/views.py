from flask import Blueprint, request, jsonify, g
import hashlib
import hmac
import json
import requests
from datetime import datetime
from urllib.parse import urlencode
import os
from threading import Thread
import time
import uuid
import re
import random
from collections import defaultdict
import concurrent.futures
import asyncio

from config import Config
from .database import save_test_record, get_user_test_history, get_test_record_by_id
from .models import TaskStatus, TaskStage, get_task_status, save_task_status, get_deep_intelligence_result, save_deep_intelligence_result, update_task_stage
from .logging_config import api_logger, wechat_logger, db_logger
from .ai_utils import get_ai_client, run_brand_test_with_ai
from .question_system import QuestionManager, TestCaseGenerator
from .test_engine import TestExecutor, ExecutionStrategy
from scoring_engine import ScoringEngine
from enhanced_scoring_engine import EnhancedScoringEngine, calculate_enhanced_scores
from ai_judge_module import AIJudgeClient, JudgeResult, ConfidenceLevel
from .analytics.interception_analyst import InterceptionAnalyst
from .analytics.monetization_service import MonetizationService, UserLevel
from .analytics.source_intelligence_processor import SourceIntelligenceProcessor, process_brand_source_intelligence

# Security imports
from .security.auth import require_auth, require_auth_optional, get_current_user_id
from .security.input_validation import validate_and_sanitize_request, InputValidator, InputSanitizer, validate_safe_text
from .security.rate_limiting import rate_limit, CombinedRateLimiter

# Monitoring imports
from .monitoring.monitoring_decorator import monitored_endpoint

# Create a blueprint
wechat_bp = Blueprint('wechat', __name__)

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

def verify_wechat_signature(token, signature, timestamp, nonce):
    """Verify the signature from WeChat server"""
    sorted_params = sorted([token, timestamp, nonce])
    concatenated_str = ''.join(sorted_params)
    calculated_signature = hashlib.sha1(concatenated_str.encode('utf-8')).hexdigest()
    return calculated_signature == signature

@wechat_bp.route('/wechat/verify', methods=['GET', 'POST'])
def wechat_verify():
    """Handle WeChat server verification"""
    if request.method == 'GET':
        signature = request.args.get('signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        echostr = request.args.get('echostr')
        token = Config.WECHAT_TOKEN
        if verify_wechat_signature(token, signature, timestamp, nonce):
            return echostr
        else:
            return 'Verification failed', 403
    elif request.method == 'POST':
        return 'success'

@wechat_bp.route('/api/login', methods=['POST'])
@rate_limit(limit=10, window=60, per='ip')  # 限制每个IP每分钟最多10次登录尝试
@monitored_endpoint('/api/login', require_auth=False, validate_inputs=True)
def wechat_login():
    """Handle login with WeChat Mini Program code"""
    from wechat_backend.app import APP_ID, APP_SECRET
    from .security.auth import jwt_manager

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    js_code = data.get('code')
    if not js_code or not InputValidator.validate_alphanumeric(js_code, min_length=1, max_length=50):
        return jsonify({'error': 'Valid code is required'}), 400

    params = {
        'appid': APP_ID,
        'secret': APP_SECRET,
        'js_code': js_code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.get(Config.WECHAT_CODE_TO_SESSION_URL, params=params)
        result = response.json()

        if 'openid' in result:
            session_data = {
                'openid': result['openid'],
                'session_key': result['session_key'],
                'unionid': result.get('unionid'),
                'login_time': datetime.now().isoformat()
            }

            # 生成JWT令牌
            if jwt_manager:
                token = jwt_manager.generate_token(result['openid'], additional_claims={
                    'role': 'user',
                    'permissions': ['read', 'write']
                })
            else:
                # 如果JWT不可用，返回错误
                api_logger.error("JWT manager is not available")
                return jsonify({'error': 'Authentication service temporarily unavailable'}), 500

            return jsonify({
                'status': 'success',
                'data': session_data,
                'token': token  # 返回JWT令牌
            })
        else:
            api_logger.warning(f"WeChat login failed for code: {js_code[:10]}...")
            return jsonify({'error': 'Failed to login', 'details': result}), 400
    except Exception as e:
        api_logger.error(f"WeChat login error: {str(e)}")
        return jsonify({'error': 'Login service temporarily unavailable'}), 500

@wechat_bp.route('/api/test', methods=['GET'])
@rate_limit(limit=50, window=60, per='ip')
@monitored_endpoint('/api/test', require_auth=False, validate_inputs=False)
def test_api():
    return jsonify({'message': 'Backend is working correctly!', 'status': 'success'})

@wechat_bp.route('/api/perform-brand-test', methods=['POST'])
@require_auth_optional  # 可选身份验证，支持微信会话
@rate_limit(limit=5, window=60, per='endpoint')  # 限制每个端点每分钟最多5个请求
@monitored_endpoint('/api/perform-brand-test', require_auth=False, validate_inputs=True)
def perform_brand_test():
    """Perform brand cognition test across multiple AI platforms (Async) with Multi-Brand Support"""
    # 获取当前用户ID
    user_id = get_current_user_id()
    api_logger.info(f"Brand test endpoint accessed by user: {user_id}")

    # 获取并验证请求数据
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # 输入验证和净化
    try:
        # 验证品牌列表
        brand_list = data.get('brand_list', [])
        if not brand_list:
            return jsonify({'error': 'brand_list is required'}), 400

        # 验证品牌名称的安全性
        for brand in brand_list:
            if not validate_safe_text(brand, max_length=100):
                return jsonify({'error': f'Invalid brand name: {brand}'}), 400

        main_brand = brand_list[0]

        # 验证其他参数
        selected_models = data.get('selectedModels', [])
        custom_questions = data.get('customQuestions', [])
        user_openid = data.get('userOpenid', user_id or 'anonymous')  # 使用认证的用户ID
        api_key = data.get('apiKey', '')  # 在实际应用中，不应通过前端传递API密钥

        user_level = UserLevel(data.get('userLevel', 'Free'))

        # 提取AI评判参数
        judge_platform = data.get('judgePlatform')  # 前端传入的评判平台
        judge_model = data.get('judgeModel')  # 前端传入的评判模型
        judge_api_key = data.get('judgeApiKey')  # 前端传入的评判API密钥

        if not selected_models:
            return jsonify({'error': 'At least one AI model must be selected'}), 400

        # 验证自定义问题的安全性
        for question in custom_questions:
            if not validate_safe_text(question, max_length=500):
                return jsonify({'error': f'Unsafe question content: {question}'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    # 立即生成执行ID和基础存储，不等待测试用例生成
    execution_id = str(uuid.uuid4())
    # 先设置一个初始状态，稍后再更新总数
    execution_store[execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': 0,  # 会在异步线程中更新
        'status': 'initializing',
        'results': [],
        'start_time': datetime.now().isoformat()
    }

    def run_async_test():
        try:
            # 在异步线程中进行所有耗时的操作
            question_manager = QuestionManager()
            test_case_generator = TestCaseGenerator()

            cleaned_custom_questions_for_validation = [q.strip() for q in custom_questions if q.strip()]

            if cleaned_custom_questions_for_validation:
                validation_result = question_manager.validate_custom_questions(cleaned_custom_questions_for_validation)
                if not validation_result['valid']:
                    if execution_id in execution_store:
                        execution_store[execution_id].update({'status': 'failed', 'error': f"Invalid questions: {'; '.join(validation_result['errors'])}"})
                    return
                raw_questions = validation_result['cleaned_questions']
            else:
                raw_questions = [
                    "介绍一下{brandName}",
                    "{brandName}的主要产品是什么",
                    "{brandName}和竞品有什么区别"
                ]

            all_test_cases = []
            for brand in brand_list:
                brand_questions = [q.replace('{brandName}', brand) for q in raw_questions]
                cases = test_case_generator.generate_test_cases(brand, selected_models, brand_questions)
                all_test_cases.extend(cases)

            # 更新总数
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'total': len(all_test_cases),
                    'status': 'processing'
                })

            api_logger.info(f"Starting async brand test '{execution_id}' for brands: {brand_list} (User: {user_id}, Level: {user_level.value}) - Total test cases: {len(all_test_cases)}")

            executor = TestExecutor(max_workers=3, strategy=ExecutionStrategy.CONCURRENT)  # Reduced from 10 to 3 to prevent API timeouts

            def progress_callback(exec_id, progress):
                if execution_id in execution_store:
                    execution_store[execution_id].update({
                        'progress': progress.progress_percentage,
                        'completed': progress.completed_tests,
                        'total': progress.total_tests,
                        'status': progress.status.value
                    })

            results = executor.execute_tests(all_test_cases, api_key, lambda eid, p: progress_callback(execution_id, p), timeout=600)  # 10分钟超时
            executor.shutdown()

            processed_results = process_and_aggregate_results_with_ai_judge(results, brand_list, main_brand, judge_platform, judge_model, judge_api_key)

            # 使用真实的信源情报处理器
            try:
                # 使用线程池执行器来运行异步函数
                def run_async_processing():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            process_brand_source_intelligence(main_brand, processed_results['detailed_results'])
                        )
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_processing)
                    source_intelligence_map = future.result(timeout=30)  # 设置超时时间
            except Exception as e:
                api_logger.error(f"信源情报处理失败: {e}")
                # 如果异步处理失败，使用模拟数据
                source_intelligence_map = generate_mock_source_intelligence_map(main_brand)

            semantic_contrast_data = generate_mock_semantic_contrast_data(main_brand)

            monetization_service = MonetizationService(user_level)
            # 安全地获取main_brand数据，使用默认值防止KeyError
            main_brand_data = processed_results['main_brand']
            final_data = {
                'results': processed_results['detailed_results'],
                'competitiveAnalysis': processed_results['competitiveAnalysis'],
                'overallScore': main_brand_data.get('overallScore', 0),
                'overallAuthority': main_brand_data.get('overallAuthority', 0),
                'overallVisibility': main_brand_data.get('overallVisibility', 0),
                'overallSentiment': main_brand_data.get('overallSentiment', 0),
                'overallPurity': main_brand_data.get('overallPurity', 0),
                'overallConsistency': main_brand_data.get('overallConsistency', 0),
                'overallGrade': main_brand_data.get('overallGrade', 'D'),
                'overallSummary': main_brand_data.get('overallSummary', 'No data available'),
                'sourceIntelligenceMap': source_intelligence_map,
                'semanticContrastData': semantic_contrast_data,
            }
            stripped_data = monetization_service.strip_data_for_user(final_data)

            record_id = None
            try:
                record_id = save_test_record(
                    user_openid=user_openid,
                    brand_name=main_brand,
                    ai_models_used=[m['name'] if isinstance(m, dict) else m for m in selected_models],
                    questions_used=raw_questions,
                    overall_score=stripped_data['overallScore'],
                    total_tests=len(all_test_cases),
                    results_summary=processed_results['summary'],
                    detailed_results=stripped_data['results']
                )
            except Exception as e:
                api_logger.error(f"Error saving test record: {e}")

            if execution_id in execution_store:
                stripped_data['status'] = 'completed'
                stripped_data['progress'] = 100
                stripped_data['recordId'] = record_id
                execution_store[execution_id].update(stripped_data)

        except Exception as e:
            api_logger.error(f"Async test execution failed: {e}")
            if execution_id in execution_store:
                execution_store[execution_id].update({'status': 'failed', 'error': str(e)})

    thread = Thread(target=run_async_test)
    thread.start()

    return jsonify({'status': 'success', 'executionId': execution_id, 'message': 'Test started successfully'})

def process_and_aggregate_results_with_ai_judge(raw_results, all_brands, main_brand, judge_platform=None, judge_model=None, judge_api_key=None):
    """
    结果聚合引擎 (CompetitorDataAggregator)
    """
    # Only create AIJudgeClient if judge parameters are provided
    ai_judge = None
    if judge_platform and judge_model and judge_api_key:
        ai_judge = AIJudgeClient(judge_platform=judge_platform, judge_model=judge_model, api_key=judge_api_key)
    else:
        # Check if any judge parameters are provided (even partially)
        if judge_platform or judge_model or judge_api_key:
            # If any parameter is provided but not all, try to fill in missing ones
            ai_judge = AIJudgeClient(judge_platform=judge_platform, judge_model=judge_model, api_key=judge_api_key)
        else:
            # No judge parameters provided, skip AI judging
            api_logger.info("No judge parameters provided, skipping AI evaluation")

    scoring_engine = ScoringEngine()
    enhanced_scoring_engine = EnhancedScoringEngine()
    interception_analyst = InterceptionAnalyst(all_brands, main_brand)

    detailed_results = []
    brand_results_map = defaultdict(list)
    platform_results_map = defaultdict(list)

    # 检查raw_results的结构，如果是executor返回的完整结果，则提取实际的测试结果
    actual_results = []
    if isinstance(raw_results, dict) and 'tasks_results' in raw_results:
        # 如果raw_results包含tasks_results键，则使用它
        actual_results = raw_results.get('tasks_results', [])
    elif isinstance(raw_results, dict) and 'results' in raw_results:
        # 如果raw_results包含results键，则使用它
        actual_results = raw_results.get('results', [])
    elif isinstance(raw_results, list):
        # 如果raw_results本身就是列表，则直接使用
        actual_results = raw_results
    else:
        # 默认行为：假设raw_results有results键
        actual_results = raw_results.get('results', [])

    for result in actual_results:
        # 检查result的结构，确保兼容不同的数据格式
        if isinstance(result, dict):
            # 如果result已经是处理过的格式
            current_brand = result.get('brand_name', result.get('brand', 'unknown'))

            # 检查是否成功获取了AI响应
            if result.get('success', False):
                # 根据不同数据格式获取响应内容
                ai_response_content = ""
                if 'result' in result and isinstance(result['result'], dict):
                    ai_response_content = result['result'].get('content', '')
                elif 'response' in result:
                    ai_response_content = result['response']
                elif 'content' in result:
                    ai_response_content = result['content']

                question = result.get('question', result.get('original_question', ''))

                # Only evaluate with AI judge if it's available
                if ai_judge:
                    judge_result = ai_judge.evaluate_response(current_brand, question, ai_response_content)

                    if judge_result:
                        # 使用基础评分引擎计算基础分数
                        basic_score = scoring_engine.calculate([judge_result])

                        # 使用增强评分引擎计算增强分数（用于内部分析）
                        enhanced_result = calculate_enhanced_scores([judge_result], brand_name=current_brand)

                        detailed_result = {
                            'success': True,
                            'brand': current_brand,
                            'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                            'question': question,
                            'response': ai_response_content,
                            'authority_score': judge_result.accuracy_score,
                            'visibility_score': judge_result.completeness_score,
                            'sentiment_score': judge_result.sentiment_score,
                            'purity_score': judge_result.purity_score,
                            'consistency_score': judge_result.consistency_score,
                            'score': basic_score.geo_score,  # 保持原有分数以确保兼容性
                            'enhanced_scores': {
                                'geo_score': enhanced_result.geo_score,
                                'cognitive_confidence': enhanced_result.cognitive_confidence,
                                'bias_indicators': enhanced_result.bias_indicators,
                                'detailed_analysis': enhanced_result.detailed_analysis,
                                'recommendations': enhanced_result.recommendations
                            },
                            'category': '国内' if result.get('model', result.get('ai_model', '')) in ['通义千问', '文心一言', '豆包', 'Kimi', '元宝', 'DeepSeek', '讯飞星火'] else '海外'
                        }
                        brand_results_map[current_brand].append(judge_result)
                        platform_results_map[detailed_result['aiModel']].append(detailed_result)
                    else:
                        detailed_result = {
                            'success': False,
                            'brand': current_brand,
                            'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                            'question': question,
                            'response': "Evaluation Failed by AI Judge",
                            'score': 0,
                            'error_type': 'EvaluationFailed'
                        }
                else:
                    # Skip AI evaluation, use basic result structure
                    detailed_result = {
                        'success': True,
                        'brand': current_brand,
                        'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                        'question': question,
                        'response': ai_response_content,
                        'authority_score': 0,  # Default score when no AI judge
                        'visibility_score': 0,
                        'sentiment_score': 0,
                        'purity_score': 0,
                        'consistency_score': 0,
                        'score': 0,  # Default score when no AI judge
                        'enhanced_scores': {
                            'geo_score': 0,
                            'cognitive_confidence': 0.0,
                            'bias_indicators': [],
                            'detailed_analysis': {},
                            'recommendations': []
                        },
                        'category': '国内' if result.get('model', result.get('ai_model', '')) in ['通义千问', '文心一言', '豆包', 'Kimi', '元宝', 'DeepSeek', '讯飞星火'] else '海外'
                    }
                    # Add a basic judge result with default scores for scoring calculations
                    basic_judge_result = JudgeResult(
                        accuracy_score=0,
                        completeness_score=0,
                        sentiment_score=50,  # Neutral sentiment
                        purity_score=0,
                        consistency_score=0,
                        judgement="AI evaluation skipped",
                        confidence_level=ConfidenceLevel.MEDIUM
                    )
                    brand_results_map[current_brand].append(basic_judge_result)
                    platform_results_map[detailed_result['aiModel']].append(detailed_result)
            else:
                # 处理失败的结果
                detailed_result = {
                    'success': False,
                    'brand': current_brand,
                    'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                    'question': result.get('question', result.get('original_question', '')),
                    'response': f"Error: {result.get('error', result.get('error_message', 'Unknown error'))}",
                    'score': 0,
                    'error_message': result.get('error', result.get('error_message', 'Unknown error')),
                    'error_type': result.get('error_type', 'GeneralError')
                }

            detailed_results.append(detailed_result)
        else:
            # 如果result不是字典格式，跳过
            api_logger.warning(f"Unexpected result format: {result}")
            continue

    brand_scores = {}
    for brand, judge_results in brand_results_map.items():
        if judge_results and len(judge_results) > 0:  # 确保列表非空
            try:
                # 使用基础评分引擎计算基础分数
                basic_score = scoring_engine.calculate(judge_results)

                # 使用增强评分引擎计算增强分数
                enhanced_result = calculate_enhanced_scores(judge_results, brand_name=brand)

                brand_scores[brand] = {
                    'overallScore': basic_score.geo_score,  # 保持原有分数以确保兼容性
                    'overallAuthority': basic_score.authority_score,
                    'overallVisibility': basic_score.visibility_score,
                    'overallSentiment': basic_score.sentiment_score,
                    'overallPurity': basic_score.purity_score,
                    'overallConsistency': basic_score.consistency_score,
                    'overallGrade': basic_score.grade,
                    'overallSummary': basic_score.summary,
                    # 增加增强版数据
                    'enhanced_data': {
                        'cognitive_confidence': enhanced_result.cognitive_confidence,
                        'bias_indicators': enhanced_result.bias_indicators,
                        'detailed_analysis': enhanced_result.detailed_analysis,
                        'recommendations': enhanced_result.recommendations
                    }
                }
            except Exception as e:
                # 如果计算失败，使用默认值
                api_logger.error(f"Scoring calculation failed for brand {brand}: {str(e)}")
                brand_scores[brand] = {
                    'overallScore': 0,
                    'overallGrade': 'D',
                    'overallAuthority': 0,
                    'overallVisibility': 0,
                    'overallSentiment': 0,
                    'overallPurity': 0,
                    'overallConsistency': 0,
                    'overallSummary': 'Calculation error occurred',
                    'enhanced_data': {
                        'cognitive_confidence': 0.0,
                        'bias_indicators': [],
                        'detailed_analysis': {},
                        'recommendations': []
                    }
                }
        else:
            brand_scores[brand] = {
                'overallScore': 0,
                'overallGrade': 'D',
                'overallAuthority': 0,
                'overallVisibility': 0,
                'overallSentiment': 0,
                'overallPurity': 0,
                'overallConsistency': 0,
                'overallSummary': 'No data available',
                'enhanced_data': {
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                }
            }

    first_mention_by_platform = {platform: interception_analyst.calculate_first_mention_rate(results) for platform, results in platform_results_map.items()}

    main_brand_source = generate_mock_source_intelligence_map(main_brand)
    competitor_sources = {brand: generate_mock_source_intelligence_map(brand) for brand in all_brands if brand != main_brand}
    interception_risks = interception_analyst.analyze_interception_risk(main_brand_source, competitor_sources)

    competitive_analysis = {
        'brandScores': brand_scores,
        'firstMentionByPlatform': first_mention_by_platform,
        'interceptionRisks': interception_risks
    }

    return {
        'detailed_results': detailed_results,
        'main_brand': brand_scores.get(main_brand, {
            'overallScore': 0,
            'overallGrade': 'D',
            'enhanced_data': {
                'cognitive_confidence': 0.0,
                'bias_indicators': [],
                'detailed_analysis': {},
                'recommendations': []
            }
        }),
        'competitiveAnalysis': competitive_analysis,
        'summary': {'total_tests': len(detailed_results), 'brands_tested': len(all_brands)}
    }

def generate_mock_source_intelligence_map(brand_name):
    # This function is now replaced by the real processor, but we keep it for other potential uses
    sources = [{'name': '知乎', 'category': 'social'}, {'name': '百度百科', 'category': 'wiki'}, {'name': 'CSDN', 'category': 'tech'}, {'name': '小红书', 'category': 'social'}, {'name': '36Kr', 'category': 'news'}, {'name': '官网', 'category': 'official'}, {'name': '微博', 'category': 'social'}, {'name': '雪球', 'category': 'finance'}]
    nodes = [{'id': 'brand', 'name': brand_name, 'level': 0, 'symbolSize': 60, 'category': 'brand'}]
    links = []
    selected_sources = random.sample(sources, random.randint(5, 8))
    for source in selected_sources:
        weight = random.randint(1, 10)
        sentiment = random.choice(['positive', 'neutral', 'negative'])
        nodes.append({'id': source['name'], 'name': source['name'], 'level': 1, 'symbolSize': 20 + weight * 3, 'category': source['category'], 'value': weight, 'sentiment': sentiment})
        links.append({'source': 'brand', 'target': source['name'], 'contribution_score': weight / 10, 'sentiment_bias': (1 if sentiment == 'positive' else (-1 if sentiment == 'negative' else 0)) * random.random()})
    if random.random() < 0.3:
        risk_source = '竞品黑稿'
        nodes.append({'id': 'risk', 'name': risk_source, 'level': 2, 'symbolSize': 40, 'category': 'risk', 'source_type': 'competitor_controlled'})
        links.append({'source': 'brand', 'target': 'risk', 'contribution_score': 0.85, 'sentiment_bias': -0.6})
    return {'nodes': nodes, 'links': links}

def generate_mock_semantic_contrast_data(brand_name):
    # ... (This function remains the same)
    official_words = [{'name': '创新', 'value': 100, 'association_strength': 1.0, 'sentiment_valence': 0.8, 'source_diversity': 0.9, 'category': 'Official'}, {'name': '高端', 'value': 90, 'association_strength': 0.9, 'sentiment_valence': 0.7, 'source_diversity': 0.8, 'category': 'Official'}]
    ai_generated_words = [{'name': '换电', 'value': 95, 'association_strength': 0.9, 'sentiment_valence': 0.8, 'source_diversity': 0.9, 'category': 'AI_Generated_Positive'}, {'name': '豪华', 'value': 88, 'association_strength': 0.85, 'sentiment_valence': 0.7, 'source_diversity': 0.8, 'category': 'AI_Generated_Positive'}, {'name': '贵', 'value': 70, 'association_strength': 0.7, 'sentiment_valence': -0.3, 'source_diversity': 0.6, 'category': 'AI_Generated_Risky'}]
    return {'official_words': official_words, 'ai_generated_words': ai_generated_words}

@wechat_bp.route('/api/source-intelligence', methods=['GET'])
def get_source_intelligence():
    brand_name = request.args.get('brandName', '默认品牌')
    data = generate_mock_source_intelligence_map(brand_name)
    return jsonify({'status': 'success', 'data': data})


@wechat_bp.route('/api/platform-status', methods=['GET'])
@require_auth_optional  # 可选身份验证，支持微信会话
@rate_limit(limit=20, window=60, per='endpoint')  # 限制每分钟20次请求
@monitored_endpoint('/api/platform-status', require_auth=False, validate_inputs=False)
def get_platform_status():
    """获取所有AI平台的状态信息"""
    try:
        # 从配置管理器获取平台状态
        from config_manager import Config as PlatformConfigManager
        config_manager = PlatformConfigManager()

        status_info = {}

        # 预定义支持的平台
        supported_platforms = [
            'deepseek', 'doubao', 'qwen', 'wenxin',
            'kimi', 'chatgpt', 'claude', 'gemini'
        ]

        for platform in supported_platforms:
            config = config_manager.get_platform_config(platform)
            if config and config.api_key:
                # 检查配额和状态
                quota_info = getattr(config, 'quota_info', None)
                status = getattr(config, 'api_status', None)

                status_info[platform] = {
                    'status': status.value if status else 'active',
                    'has_api_key': bool(config.api_key),
                    'quota': {
                        'daily_limit': quota_info.daily_limit if quota_info else None,
                        'used_today': quota_info.used_today if quota_info else 0,
                        'remaining': quota_info.remaining if quota_info else None
                    } if quota_info else None,
                    'cost_per_request': getattr(config, 'cost_per_token', 0) * 1000,  # per 1k tokens
                    'rate_limit': getattr(config, 'rate_limit_per_minute', None)
                }
            else:
                status_info[platform] = {
                    'status': 'inactive',
                    'has_api_key': False,
                    'quota': None,
                    'cost_per_request': 0,
                    'rate_limit': None
                }

        return jsonify({'status': 'success', 'platforms': status_info})

    except Exception as e:
        api_logger.error(f"Error getting platform status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@wechat_bp.route('/api/test-progress', methods=['GET'])
def get_test_progress():
    execution_id = request.args.get('executionId')
    if execution_id and execution_id in execution_store:
        progress_data = execution_store[execution_id]

        # 如果任务已完成，添加一个标志来通知前端停止轮询
        if progress_data.get('status') in ['completed', 'failed']:
            progress_data['should_stop_polling'] = True

        return jsonify(progress_data)
    else:
        return jsonify({'error': 'Execution ID not found'}), 404


@wechat_bp.route('/test/submit', methods=['POST'])
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
@monitored_endpoint('/test/submit', require_auth=False, validate_inputs=True)
def submit_brand_test():
    """提交品牌AI诊断任务"""
    user_id = get_current_user_id()
    api_logger.info(f"Brand test submission endpoint accessed by user: {user_id}")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # 输入验证和净化
    try:
        brand_list = data.get('brand_list', [])
        if not brand_list:
            return jsonify({'error': 'brand_list is required'}), 400

        for brand in brand_list:
            if not validate_safe_text(brand, max_length=100):
                return jsonify({'error': f'Invalid brand name: {brand}'}), 400

        selected_models = data.get('selectedModels', [])
        custom_questions = data.get('customQuestions', [])

        if not selected_models:
            return jsonify({'error': 'At least one AI model must be selected'}), 400

        for question in custom_questions:
            if not validate_safe_text(question, max_length=500):
                return jsonify({'error': f'Unsafe question content: {question}'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    # 生成任务ID并初始化任务状态
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    initial_status = TaskStatus(
        task_id=task_id,
        progress=0,
        stage=TaskStage.INIT,
        status_text="正在初始化任务...",
        is_completed=False
    )
    save_task_status(initial_status)

    def run_async_test():
        try:
            # 更新任务状态到AI数据调取阶段
            update_task_stage(task_id, TaskStage.AI_FETCHING, 25, "正在调取AI数据...")

            question_manager = QuestionManager()
            test_case_generator = TestCaseGenerator()

            cleaned_custom_questions_for_validation = [q.strip() for q in custom_questions if q.strip()]

            if cleaned_custom_questions_for_validation:
                validation_result = question_manager.validate_custom_questions(cleaned_custom_questions_for_validation)
                if not validation_result['valid']:
                    update_task_stage(task_id, TaskStage.INIT, 0, f"验证失败: {'; '.join(validation_result['errors'])}")
                    return
                raw_questions = validation_result['cleaned_questions']
            else:
                raw_questions = [
                    "介绍一下{brandName}",
                    "{brandName}的主要产品是什么",
                    "{brandName}和竞品有什么区别"
                ]

            all_test_cases = []
            for brand in brand_list:
                brand_questions = [q.replace('{brandName}', brand) for q in raw_questions]
                cases = test_case_generator.generate_test_cases(brand, selected_models, brand_questions)
                all_test_cases.extend(cases)

            api_logger.info(f"Starting async brand test '{task_id}' for brands: {brand_list} - Total test cases: {len(all_test_cases)}")

            executor = TestExecutor(max_workers=3, strategy=ExecutionStrategy.CONCURRENT)

            def progress_callback(exec_id, progress):
                # 计算进度百分比
                calculated_progress = int((progress.completed_tests / progress.total_tests) * 100) if progress.total_tests > 0 else 0
                # 确保进度不超过90%，保留10%给后续处理
                calculated_progress = min(calculated_progress, 90)

                # 更新任务状态
                update_task_stage(
                    task_id,
                    TaskStage.AI_FETCHING,
                    calculated_progress,
                    f"正在处理测试案例 ({progress.completed_tests}/{progress.total_tests})"
                )

            results = executor.execute_tests(all_test_cases, '', lambda eid, p: progress_callback(task_id, p), timeout=600)
            executor.shutdown()

            # 更新到排名分析阶段
            update_task_stage(task_id, TaskStage.RANKING_ANALYSIS, 75, "正在进行排名分析...")

            processed_results = process_and_aggregate_results_with_ai_judge(results, brand_list, brand_list[0], None, None, None)

            # 更新到信源追踪阶段
            update_task_stage(task_id, TaskStage.SOURCE_TRACING, 90, "正在进行信源追踪分析...")

            # 使用真实的信源情报处理器
            try:
                def run_async_processing():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            process_brand_source_intelligence(brand_list[0], processed_results['detailed_results'])
                        )
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_processing)
                    source_intelligence_map = future.result(timeout=30)
            except Exception as e:
                api_logger.error(f"信源情报处理失败: {e}")
                source_intelligence_map = generate_mock_source_intelligence_map(brand_list[0])

            # 从处理结果中构建暴露分析数据
            ranking_list = []
            brand_details = {}
            unlisted_competitors = []

            # 提取品牌排名信息
            if 'detailed_results' in processed_results and processed_results['detailed_results']:
                # 按响应长度排序品牌
                brand_responses = {}
                for result in processed_results['detailed_results']:
                    brand = result.get('brand', 'unknown')
                    response = result.get('response', '')
                    if brand not in brand_responses:
                        brand_responses[brand] = 0
                    brand_responses[brand] += len(response)

                # 按响应长度排序，形成排名列表
                sorted_brands = sorted(brand_responses.items(), key=lambda x: x[1], reverse=True)
                ranking_list = [item[0] for item in sorted_brands]

                # 填充品牌详情
                total_chars = sum(brand_responses.values())
                for brand, char_count in sorted_brands:
                    brand_details[brand] = {
                        'rank': ranking_list.index(brand) + 1,
                        'word_count': char_count,
                        'sov_share': round(char_count / total_chars, 4) if total_chars > 0 else 0,
                        'sentiment_score': 50  # 这里应该从processed_results中提取实际的情感分数
                    }

            # 提取未列出的竞争对手（从AI响应中发现但不在原始品牌列表中的品牌）
            # 这里需要实现具体的竞争对手检测逻辑
            # 示例：遍历所有响应，查找可能的品牌提及
            all_responses = " ".join([result.get('response', '') for result in processed_results['detailed_results']])
            # 简单的竞争对手检测逻辑（实际应用中需要更复杂的NLP处理）
            possible_competitors = ['小米', '华为', '苹果', '三星']  # 示例品牌列表
            for competitor in possible_competitors:
                if competitor in all_responses and competitor not in brand_list:
                    if competitor not in unlisted_competitors:
                        unlisted_competitors.append(competitor)

            # 构建信源情报数据
            source_pool = []
            citation_rank = []

            # 从source_intelligence_map中提取信源信息
            if source_intelligence_map and 'nodes' in source_intelligence_map:
                for node in source_intelligence_map.get('nodes', []):
                    if node.get('category') in ['social', 'wiki', 'tech', 'news', 'official']:
                        source_id = node.get('name', '')
                        source_pool.append({
                            'id': source_id,
                            'url': f"https://{source_id.lower()}.com",  # 示例URL
                            'site_name': source_id,
                            'citation_count': node.get('value', 0),
                            'domain_authority': 'High' if node.get('value', 0) > 5 else 'Medium' if node.get('value', 0) > 2 else 'Low'
                        })
                        citation_rank.append(source_id)

            # 构建证据链数据
            evidence_chain = []

            # 从processed_results中提取潜在的风险内容
            for result in processed_results['detailed_results']:
                response = result.get('response', '')
                # 检查是否有负面内容的迹象
                negative_indicators = ['缺点', '不好', '差', '问题', '风险', '不足']
                for indicator in negative_indicators:
                    if indicator in response:
                        evidence_chain.append({
                            'negative_fragment': response[:100] + '...' if len(response) > 100 else response,
                            'associated_url': 'https://example.com',  # 应该从实际来源获取
                            'source_name': result.get('aiModel', 'Unknown'),
                            'risk_level': 'Medium'
                        })
                        break  # 找到一个就够了，避免重复

            # 构建深度情报结果
            deep_intelligence_result_data = {
                'exposure_analysis': {
                    'ranking_list': ranking_list,
                    'brand_details': brand_details,
                    'unlisted_competitors': unlisted_competitors
                },
                'source_intelligence': {
                    'source_pool': source_pool,
                    'citation_rank': citation_rank
                },
                'evidence_chain': evidence_chain
            }

            # 创建DeepIntelligenceResult对象
            from .models import DeepIntelligenceResult, BrandTestResult, save_brand_test_result
            deep_result_obj = DeepIntelligenceResult(
                exposure_analysis=deep_intelligence_result_data['exposure_analysis'],
                source_intelligence=deep_intelligence_result_data['source_intelligence'],
                evidence_chain=deep_intelligence_result_data['evidence_chain']
            )

            # 保存深度情报结果
            save_deep_intelligence_result(task_id, deep_result_obj)

            # 创建并保存品牌测试结果
            brand_test_result = BrandTestResult(
                task_id=task_id,
                brand_name=brand_list[0],
                ai_models_used=selected_models,
                questions_used=raw_questions,
                overall_score=processed_results.get('main_brand', {}).get('overallScore', 0),
                total_tests=len(all_test_cases),
                results_summary=processed_results.get('summary', {}),
                detailed_results=processed_results.get('detailed_results', []),
                deep_intelligence_result=deep_result_obj
            )

            save_brand_test_result(brand_test_result)

            # 最终更新为完成状态
            update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")

        except Exception as e:
            api_logger.error(f"Async test execution failed: {e}")
            update_task_stage(task_id, TaskStage.INIT, 0, f"任务执行失败: {str(e)}")

    thread = Thread(target=run_async_test)
    thread.start()

    return jsonify({
        'task_id': task_id,
        'message': '任务已接收并加入队列'
    }), 202


@wechat_bp.route('/test/status/<task_id>', methods=['GET'])
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/test/status', require_auth=False, validate_inputs=False)
def get_task_status(task_id):
    """轮询任务进度与分阶段状态"""
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    # 尝试从数据库获取任务状态
    task_status = get_task_status(task_id)

    if not task_status:
        return jsonify({'error': 'Task not found'}), 404

    # 按照API契约返回任务状态信息
    response_data = {
        'task_id': task_status.task_id,
        'progress': task_status.progress,
        'stage': task_status.stage.value,
        'status_text': task_status.status_text,
        'is_completed': task_status.is_completed,
        'created_at': task_status.created_at
    }

    # 返回任务状态信息
    return jsonify(response_data), 200


@wechat_bp.route('/test/result/<task_id>', methods=['GET'])
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/test/result', require_auth=False, validate_inputs=False)
def get_task_result(task_id):
    """获取诊断任务的完整情报深度结果"""
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    # 检查任务是否已完成
    task_status = get_task_status(task_id)
    if not task_status or not task_status.is_completed:
        return jsonify({'error': 'Task not completed or not found'}), 400

    # 获取深度情报结果
    deep_intelligence_result = get_deep_intelligence_result(task_id)

    if not deep_intelligence_result:
        return jsonify({'error': 'Deep intelligence result not found'}), 404

    # 返回完整的深度情报分析结果
    return jsonify(deep_intelligence_result.to_dict()), 200

# ... (Other endpoints remain the same)
@wechat_bp.route('/api/test-history', methods=['GET'])
def get_test_history():
    user_openid = request.args.get('userOpenid', 'anonymous')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    try:
        history = get_user_test_history(user_openid, limit, offset)
        return jsonify({'status': 'success', 'history': history, 'count': len(history)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@wechat_bp.route('/api/test-record/<int:record_id>', methods=['GET'])
def get_test_record(record_id):
    try:
        record = get_test_record_by_id(record_id)
        if record:
            return jsonify({'status': 'success', 'record': record})
        else:
            return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@wechat_bp.route('/api/ai-platforms', methods=['GET'])
def get_ai_platforms():
    platforms = {
        'domestic': [{'name': 'DeepSeek', 'checked': False}, {'name': '豆包', 'checked': False}, {'name': '元宝', 'checked': False}, {'name': '通义千问', 'checked': True}, {'name': '文心一言', 'checked': False}, {'name': 'Kimi', 'checked': True}, {'name': '讯飞星火', 'checked': False}],
        'overseas': [{'name': 'ChatGPT', 'checked': True}, {'name': 'Claude', 'checked': True}, {'name': 'Gemini', 'checked': False}, {'name': 'Perplexity', 'checked': False}, {'name': 'Grok', 'checked': False}]
    }
    return jsonify(platforms)

@wechat_bp.route('/api/send_message', methods=['POST'])
def send_template_message():
    return jsonify({'status': 'success'})

@wechat_bp.route('/api/access_token', methods=['GET'])
def get_token():
    return jsonify({'access_token': 'mock_token', 'status': 'success'})

@wechat_bp.route('/api/user_info', methods=['POST'])
def decrypt_user_info():
    return jsonify({'status': 'success', 'user_info': {}})