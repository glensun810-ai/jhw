from flask import Blueprint, request, jsonify
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

from config import Config
from .database import save_test_record, get_user_test_history, get_test_record_by_id
from .logging_config import api_logger, wechat_logger, db_logger
from .ai_utils import get_ai_client, run_brand_test_with_ai
from .question_system import QuestionManager, TestCaseGenerator
from .test_engine import TestExecutor, ExecutionStrategy
from scoring_engine import ScoringEngine
from ai_judge_module import AIJudgeClient, JudgeResult, ConfidenceLevel
from .analytics.interception_analyst import InterceptionAnalyst
from .analytics.monetization_service import MonetizationService, UserLevel
try:
    from .analytics.source_intelligence_processor import SourceIntelligenceProcessor # 引入信源情报处理器
except ImportError:
    SourceIntelligenceProcessor = None
    print("Warning: SourceIntelligenceProcessor not available due to missing dependencies")

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
def wechat_login():
    """Handle login with WeChat Mini Program code"""
    from wechat_backend.app import APP_ID, APP_SECRET
    data = request.get_json()
    js_code = data.get('code')
    if not js_code:
        return jsonify({'error': 'Code is required'}), 400
    params = {
        'appid': APP_ID,
        'secret': APP_SECRET,
        'js_code': js_code,
        'grant_type': 'authorization_code'
    }
    response = requests.get(Config.WECHAT_CODE_TO_SESSION_URL, params=params)
    result = response.json()
    if 'openid' in result:
        session_data = {
            'openid': result['openid'],
            'session_key': result['session_key'],
            'unionid': result.get('unionid'),
            'login_time': datetime.now().isoformat()
        }
        return jsonify({'status': 'success', 'data': session_data})
    else:
        return jsonify({'error': 'Failed to login', 'details': result}), 400

@wechat_bp.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({'message': 'Backend is working correctly!', 'status': 'success'})

@wechat_bp.route('/api/perform-brand-test', methods=['POST'])
def perform_brand_test():
    """Perform brand cognition test across multiple AI platforms (Async) with Multi-Brand Support"""
    api_logger.info("Brand test endpoint accessed")
    data = request.get_json()
    
    brand_list = data.get('brand_list', [])
    if not brand_list:
        return jsonify({'error': 'brand_list is required'}), 400
    
    main_brand = brand_list[0]
    
    selected_models = data.get('selectedModels', [])
    custom_questions = data.get('customQuestions', [])
    user_openid = data.get('userOpenid', 'anonymous')
    api_key = data.get('apiKey', '')
    
    user_level = UserLevel(data.get('userLevel', 'Free'))

    if not selected_models:
        return jsonify({'error': 'At least one AI model must be selected'}), 400

    execution_id = str(uuid.uuid4())
    api_logger.info(f"Starting async brand test '{execution_id}' for brands: {brand_list} (User Level: {user_level.value})")

    question_manager = QuestionManager()
    test_case_generator = TestCaseGenerator()

    cleaned_custom_questions_for_validation = [q.strip() for q in custom_questions if q.strip()]

    if cleaned_custom_questions_for_validation:
        validation_result = question_manager.validate_custom_questions(cleaned_custom_questions_for_validation)
        if not validation_result['valid']:
            return jsonify({'error': f"Invalid questions: {'; '.join(validation_result['errors'])}"}), 400
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

    execution_store[execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': len(all_test_cases),
        'status': 'pending',
        'results': [],
        'start_time': datetime.now().isoformat()
    }

    def run_async_test():
        try:
            executor = TestExecutor(max_workers=10, strategy=ExecutionStrategy.CONCURRENT)
            
            def progress_callback(exec_id, progress):
                if execution_id in execution_store:
                    execution_store[execution_id].update({
                        'progress': progress.progress_percentage,
                        'completed': progress.completed_tests,
                        'total': progress.total_tests,
                        'status': progress.status.value
                    })

            results = executor.execute_tests(all_test_cases, api_key, lambda eid, p: progress_callback(execution_id, p))
            executor.shutdown()

            processed_results = process_and_aggregate_results_with_ai_judge(results, brand_list, main_brand)
            
            # 使用真实的信源情报处理器
            if SourceIntelligenceProcessor:
                source_processor = SourceIntelligenceProcessor()
                source_intelligence_map = source_processor.process(main_brand, processed_results['detailed_results'])
            else:
                # 如果模块不可用，使用模拟数据
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

def process_and_aggregate_results_with_ai_judge(raw_results, all_brands, main_brand):
    """
    结果聚合引擎 (CompetitorDataAggregator)
    """
    ai_judge = AIJudgeClient()
    scoring_engine = ScoringEngine()
    interception_analyst = InterceptionAnalyst(all_brands, main_brand)
    
    detailed_results = []
    brand_results_map = defaultdict(list)
    platform_results_map = defaultdict(list)
    
    for result in raw_results['results']:
        current_brand = result.get('brand_name', 'unknown')
        
        if result.get('success'):
            ai_response_content = result['result'].get('content', '')
            judge_result = ai_judge.evaluate_response(current_brand, result.get('question', ''), ai_response_content)
            
            if judge_result:
                individual_score = scoring_engine.calculate([judge_result]).geo_score
                
                detailed_result = {
                    'success': True,
                    'brand': current_brand,
                    'aiModel': result.get('model', 'unknown'),
                    'question': result.get('question', ''),
                    'response': ai_response_content,
                    'authority_score': judge_result.accuracy_score,
                    'visibility_score': judge_result.completeness_score,
                    'sentiment_score': judge_result.sentiment_score,
                    'purity_score': judge_result.purity_score,
                    'consistency_score': judge_result.consistency_score,
                    'score': individual_score,
                    'category': '国内' if result.get('model', '') in ['通义千问', '文心一言', '豆包', 'Kimi', '元宝', 'DeepSeek', '讯飞星火'] else '海外'
                }
                brand_results_map[current_brand].append(judge_result)
                platform_results_map[detailed_result['aiModel']].append(detailed_result)
            else:
                detailed_result = {'success': False, 'brand': current_brand, 'aiModel': result.get('model', 'unknown'), 'question': result.get('question', ''), 'response': "Evaluation Failed by AI Judge", 'score': 0, 'error_type': 'EvaluationFailed'}
        else:
            detailed_result = {
                'success': False,
                'brand': current_brand,
                'aiModel': result.get('model', 'unknown'),
                'question': result.get('question', ''),
                'response': f"Error: {result.get('error', 'Unknown error')}",
                'score': 0,
                'error_message': result.get('error'),
                'error_type': result.get('error_type')
            }
        
        detailed_results.append(detailed_result)

    brand_scores = {}
    for brand, judge_results in brand_results_map.items():
        if judge_results and len(judge_results) > 0:  # 确保列表非空
            try:
                final_score = scoring_engine.calculate(judge_results)
                brand_scores[brand] = {
                    'overallScore': final_score.geo_score,
                    'overallAuthority': final_score.authority_score,
                    'overallVisibility': final_score.visibility_score,
                    'overallSentiment': final_score.sentiment_score,
                    'overallPurity': final_score.purity_score,
                    'overallConsistency': final_score.consistency_score,
                    'overallGrade': final_score.grade,
                    'overallSummary': final_score.summary
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
                    'overallSummary': 'Calculation error occurred'
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
                'overallSummary': 'No data available'
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
        'main_brand': brand_scores.get(main_brand, {'overallScore': 0, 'overallGrade': 'D'}),
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
        return jsonify(progress_data)
    else:
        return jsonify({'error': 'Execution ID not found'}), 404

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