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
from wechat_backend.database import save_test_record, get_user_test_history, get_test_record_by_id
from wechat_backend.models import TaskStatus, TaskStage, get_task_status, save_task_status, get_deep_intelligence_result, save_deep_intelligence_result, update_task_stage
from wechat_backend.realtime_analyzer import get_analyzer
from wechat_backend.incremental_aggregator import get_aggregator
from wechat_backend.logging_config import api_logger, wechat_logger, db_logger
from wechat_backend.ai_adapters.base_adapter import AIPlatformType, AIClient, AIResponse, GEO_PROMPT_TEMPLATE, parse_geo_json
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.nxm_execution_engine import execute_nxm_test, verify_nxm_execution
from wechat_backend.question_system import QuestionManager, TestCaseGenerator
from wechat_backend.test_engine import TestExecutor, ExecutionStrategy
from scoring_engine import ScoringEngine
from enhanced_scoring_engine import EnhancedScoringEngine, calculate_enhanced_scores
from ai_judge_module import AIJudgeClient, JudgeResult, ConfidenceLevel
from wechat_backend.analytics.interception_analyst import InterceptionAnalyst
from wechat_backend.analytics.monetization_service import MonetizationService, UserLevel
from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor, process_brand_source_intelligence
from wechat_backend.recommendation_generator import RecommendationGenerator, RecommendationPriority, RecommendationType
from wechat_backend.cruise_controller import CruiseController
from wechat_backend.market_intelligence_service import MarketIntelligenceService

# SSE Service imports
from wechat_backend.services.sse_service import (
    get_sse_manager,
    create_sse_response,
    send_progress_update,
    send_intelligence_update,
    send_task_complete,
    send_error
)

# Security imports
from wechat_backend.security.auth import require_auth, require_auth_optional, get_current_user_id
from wechat_backend.security.input_validation import validate_and_sanitize_request, InputValidator, InputSanitizer, validate_safe_text
from wechat_backend.security.sql_protection import sql_protector
from wechat_backend.security.rate_limiting import rate_limit, CombinedRateLimiter

# Monitoring imports
from wechat_backend.monitoring.monitoring_decorator import monitored_endpoint

# Create a blueprint
wechat_bp = Blueprint('wechat', __name__)

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

def verify_wechat_signature(token, signature, timestamp, nonce):
    """Verify the signature from WeChat server"""
    # 微信签名算法：将token、timestamp、nonce三个参数进行字典序排序，然后拼接成字符串，再进行SHA1加密
    params = [token, timestamp, nonce]
    params.sort()  # 字典序排序
    concatenated_str = ''.join(params)
    calculated_signature = hashlib.sha1(concatenated_str.encode('utf-8')).hexdigest()
    return calculated_signature == signature

@wechat_bp.route('/wechat/verify', methods=['GET', 'POST'])
def wechat_verify():
    """Handle WeChat server verification"""
    # 记录请求信息用于调试
    from wechat_backend.logging_config import api_logger
    api_logger.info(f"WeChat verification request: {request.method}, URL: {request.url}, Args: {request.args}")
    
    if request.method == 'GET':
        signature = request.args.get('signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        echostr = request.args.get('echostr')
        
        api_logger.info(f"Received signature: {signature}, timestamp: {timestamp}, nonce: {nonce}")
        
        token = Config.WECHAT_TOKEN
        api_logger.info(f"Using token: {token}")
        
        if verify_wechat_signature(token, signature, timestamp, nonce):
            api_logger.info("Signature verification passed")
            return echostr
        else:
            api_logger.error(f"Signature verification failed. Expected signature for token={token}, timestamp={timestamp}, nonce={nonce}")
            # 计算预期的签名用于调试
            params = [token, timestamp, nonce]
            params.sort()
            concatenated_str = ''.join(params)
            expected_signature = hashlib.sha1(concatenated_str.encode('utf-8')).hexdigest()
            api_logger.error(f"Expected signature: {expected_signature}, received: {signature}")
            return 'Verification failed', 403
    elif request.method == 'POST':
        api_logger.info("Received POST request to wechat/verify endpoint")
        return 'success'

@wechat_bp.route('/api/login', methods=['POST'])
@rate_limit(limit=10, window=60, per='ip')  # 限制每个IP每分钟最多10次登录尝试
@monitored_endpoint('/api/login', require_auth=False, validate_inputs=True)
def wechat_login():
    """Handle login with WeChat Mini Program code"""
    from wechat_backend.app import APP_ID, APP_SECRET
    from wechat_backend.security.auth import jwt_manager

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

@wechat_bp.route('/api/test', methods=['GET', 'OPTIONS'])
# @rate_limit(limit=50, window=60, per='ip')  # 临时禁用
# @monitored_endpoint('/api/test', require_auth=False, validate_inputs=False)  # 临时禁用
def test_api():
    # 处理CORS预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-WX-OpenID,X-OpenID,X-Wechat-OpenID')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response, 200
    return jsonify({'message': 'Backend is working correctly!', 'status': 'success'})

@wechat_bp.route('/api/perform-brand-test', methods=['POST', 'OPTIONS'])
@require_auth_optional  # 恢复认证装饰器
@rate_limit(limit=5, window=60, per='endpoint')  # 限制每个端点每分钟最多5个请求
@monitored_endpoint('/api/perform-brand-test', require_auth=False, validate_inputs=True)
def perform_brand_test():
    """Perform brand cognition test across multiple AI platforms (Async) with Multi-Brand Support"""
    # 【调试】记录请求信息
    api_logger.info(f"[DEBUG] perform_brand_test called with method: {request.method}")
    api_logger.info(f"[DEBUG] Headers: {dict(request.headers)}")
    api_logger.info(f"[DEBUG] Headers: {dict(request.headers)}")
    
    # 【修复】处理CORS预检请求(OPTIONS)
    if request.method == 'OPTIONS':
        api_logger.info("[DEBUG] Handling OPTIONS preflight request")
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-WX-OpenID,X-OpenID,X-Wechat-OpenID')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200
    
    # 获取当前用户ID（如果没有装饰器，手动设置默认值）
    try:
        user_id = get_current_user_id()
    except:
        user_id = 'anonymous'

    # 要求：使用 request.get_json(force=True)
    data = request.get_json(force=True)

    # 添加调试日志：在获取 data 后，立即添加打印
    print(f"DEBUG: Received JSON Data: {data}")
    if data is None:
        return jsonify({"status": "error", "error": "Empty or invalid JSON", "code": 400}), 400

    # 输入验证和净化
    try:
        # 重构校验逻辑 (InputValidator)：确保它不再寻找 customQuestions
        # 验证品牌列表是否存在且为 list 类型
        if 'brand_list' not in data:
            return jsonify({"status": "error", "error": 'Missing brand_list in request data', "code": 400, 'received_fields': list(data.keys())}), 400
        if not isinstance(data['brand_list'], list):
            return jsonify({"status": "error", "error": 'brand_list must be a list', "code": 400, 'received': type(data['brand_list']).__name__, 'received_value': data['brand_list']}), 400
        brand_list = data['brand_list']
        if not brand_list:
            return jsonify({"status": "error", "error": 'brand_list cannot be empty', "code": 400, 'received': brand_list}), 400

        # 验证品牌名称的安全性
        for brand in brand_list:
            if not isinstance(brand, str):
                return jsonify({"status": "error", "error": f'Each brand in brand_list must be a string, got {type(brand)}', "code": 400, 'problematic_value': brand}), 400
            if not validate_safe_text(brand, max_length=100):
                return jsonify({"status": "error", "error": f'Invalid brand name: {brand}', "code": 400}), 400

        # 审计要求：在后端打印关键调试日志
        api_logger.info(f"[Sprint 1] 接收到品牌列表: {brand_list}")

        main_brand = brand_list[0]

        # 验证其他参数 - 确保 selectedModels 只要是 list 类型即通过
        if 'selectedModels' not in data:
            return jsonify({"status": "error", "error": 'Missing selectedModels in request data', "code": 400, 'received_fields': list(data.keys())}), 400
        if not isinstance(data['selectedModels'], list):
            return jsonify({"status": "error", "error": 'selectedModels must be a list', "code": 400, 'received': type(data['selectedModels']).__name__, 'received_value': data['selectedModels']}), 400
        selected_models = data['selectedModels']
        if not selected_models:
            return jsonify({"status": "error", "error": 'At least one AI model must be selected', "code": 400, 'received': selected_models}), 400

        # 要求：如果 selectedModels 传入的是字典列表，代码需具备自动提取 id 字段的健壮性
        # 解析器加固：从 selectedModels 对象数组中提取 id 或 value，转化为纯字符串列表
        parsed_selected_models = []
        for model in selected_models:
            if isinstance(model, dict):
                # 如果是对象，提取其核心标识符
                model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
                if model_name:
                    parsed_selected_models.append({'name': model_name, 'checked': model.get('checked', True)})
                else:
                    # 如果对象中没有合适的标识符，尝试使用第一个可用的键值
                    for key, value in model.items():
                        if key in ['name', 'id', 'value', 'label'] and isinstance(value, str):
                            parsed_selected_models.append({'name': value, 'checked': model.get('checked', True)})
                            break
            elif isinstance(model, str):
                # 如果是字符串，直接使用
                parsed_selected_models.append({'name': model, 'checked': True})
            else:
                # 其他类型，跳过或报错
                api_logger.warning(f"Unsupported model format: {model}, type: {type(model)}")

        # 更新 selected_models 为解析后的格式
        selected_models = parsed_selected_models

        # 审计要求：在后端打印关键调试日志
        original_model_names = [model.get('name', model) if isinstance(model, dict) else model for model in data['selectedModels']]
        converted_model_names = [model['name'] for model in selected_models]
        api_logger.info(f"[Sprint 1] 转换后的模型列表: {converted_model_names} (原始: {original_model_names})")

        if not selected_models:
            return jsonify({"status": "error", "error": 'No valid AI models found after parsing', "code": 400}), 400

        # 重构校验逻辑：custom_question 只要是 string 类型即通过
        custom_questions = []
        if 'custom_question' in data:
            # 优先处理新的 custom_question 字段（字符串）
            if not isinstance(data['custom_question'], str):
                return jsonify({"status": "error", "error": 'custom_question must be a string', "code": 400, 'received': type(data['custom_question']).__name__, 'received_value': data['custom_question']}), 400
            
            # 智能分割多个问题（按问号、句号、换行或空格分割）
            question_text = data['custom_question'].strip()
            if question_text:
                # 使用正则表达式分割多个问题
                import re
                # 按中文问号、英文问号、句号、换行或空格分割
                raw_questions = re.split(r'[？?.\n\s]+', question_text)
                # 过滤空字符串并添加问号
                custom_questions = [q.strip() + ('?' if not q.strip().endswith('?') else '') for q in raw_questions if q.strip()]
                
                # 记录分割后的问题
                api_logger.info(f"[QuestionSplit] 原始问题：{question_text}")
                api_logger.info(f"[QuestionSplit] 分割后问题数：{len(custom_questions)}")
                for i, q in enumerate(custom_questions):
                    api_logger.info(f"[QuestionSplit] 问题{i+1}: {q}")
            else:
                custom_questions = []
        elif 'customQuestions' in data:
            # 保持对旧格式的兼容（数组格式）
            if not isinstance(data['customQuestions'], list):
                return jsonify({"status": "error", "error": 'customQuestions must be a list', "code": 400, 'received': type(data['customQuestions']).__name__, 'received_value': data['customQuestions']}), 400
            custom_questions = data['customQuestions']
        else:
            # 如果两个字段都没有提供，使用空数组
            custom_questions = []

        # 使用认证的用户ID，如果未认证则使用anonymous
        user_openid = data.get('userOpenid') or (user_id if user_id != 'anonymous' else 'anonymous')
        api_key = data.get('apiKey', '')  # 在实际应用中，不应通过前端传递API密钥

        user_level = UserLevel(data.get('userLevel', 'Free'))

        # 提取AI评判参数
        judge_platform = data.get('judgePlatform')  # 前端传入的评判平台
        judge_model = data.get('judgeModel')  # 前端传入的评判模型
        judge_api_key = data.get('judgeApiKey')  # 前端传入的评判API密钥

        # Provider可用性检查：验证所选模型是否已配置API Key并在AIAdapterFactory中注册
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType

        # 添加运行时调试信息
        api_logger.info(f"=== Runtime Adapter Status Check ===")
        api_logger.info(f"Selected models: {selected_models}")
        api_logger.info(f"All registered adapters: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
        api_logger.info(f"MODEL_NAME_MAP: {AIAdapterFactory.MODEL_NAME_MAP}")
        api_logger.info(f"=== End Runtime Adapter Status Check ===")
        
        for model in selected_models:
            model_name = model['name'] if isinstance(model, dict) else model
            # 使用AIAdapterFactory的标准化方法
            normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)

            # 检查平台是否可用（已注册且API密钥已配置）
            if not AIAdapterFactory.is_platform_available(normalized_model_name):
                # 打印出当前所有已注册的 Keys 并在报错中返回给前端
                registered_keys = [pt.value for pt in AIAdapterFactory._adapters.keys()]
                api_logger.error(f"Model {model_name} (normalized to {normalized_model_name}) not registered or not configured. Available models: {registered_keys}")
                return jsonify({
                    "status": "error",
                    "error": f'Model {model_name} not registered or not configured in AIAdapterFactory',
                    "code": 400,
                    "available_models": registered_keys,
                    "received_model": model_name,
                    "normalized_to": normalized_model_name
                }), 400

            # 检查API Key是否已配置
            from wechat_backend.config_manager import config_manager
            api_key = config_manager.get_api_key(normalized_model_name)
            if not api_key:
                return jsonify({"status": "error", "error": f'Model {model_name} not configured - missing API key', "code": 400, 'message': 'API Key 缺失'}), 400

        # 验证自定义问题的安全性
        for question in custom_questions:
            if not isinstance(question, str):
                return jsonify({'error': f'Each question in customQuestions must be a string, got {type(question)}'}), 400
            if not validate_safe_text(question, max_length=500):
                return jsonify({'error': f'Unsafe question content: {question}'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': f'Invalid input data: {str(e)}'}), 400

    # 立即生成执行ID和基础存储，不等待测试用例生成
    execution_id = str(uuid.uuid4())
    # 先设置一个初始状态，稍后再更新总数
    execution_store[execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': 0,  # 会在异步线程中更新
        'status': 'initializing',
        'stage': 'init',  # 设置初始阶段为 'init' 以匹配前端期望
        'results': [],
        'start_time': datetime.now().isoformat()
    }

    def run_async_test():
        """
        重构后的 NxM 执行逻辑
        外层循环遍历问题，内层循环遍历模型
        
        请求次数 = 问题数 × 模型数（只针对用户自己的品牌）
        竞品品牌仅用于对比分析，不参与 API 请求
        """
        try:
            # 在异步线程中进行所有耗时的操作
            api_logger.info(f"[AsyncTest] Initializing QuestionManager for execution_id: {execution_id}")
            question_manager = QuestionManager()
            api_logger.info(f"[AsyncTest] Successfully initialized managers for execution_id: {execution_id}")

            cleaned_custom_questions_for_validation = [q.strip() for q in custom_questions if q.strip()]

            if cleaned_custom_questions_for_validation:
                api_logger.info(f"[AsyncTest] Validating custom questions for execution_id: {execution_id}, questions: {cleaned_custom_questions_for_validation}")
                validation_result = question_manager.validate_custom_questions(cleaned_custom_questions_for_validation)
                api_logger.info(f"[AsyncTest] Question validation result for execution_id: {execution_id}, result: {validation_result}")

                if not validation_result['valid']:
                    api_logger.error(f"[AsyncTest] Question validation failed for execution_id: {execution_id}, errors: {validation_result['errors']}")
                    if execution_id in execution_store:
                        execution_store[execution_id].update({'status': 'failed', 'error': f"Invalid questions: {'; '.join(validation_result['errors'])}"})
                    return
                raw_questions = validation_result['cleaned_questions']
                api_logger.info(f"[AsyncTest] Successfully validated questions for execution_id: {execution_id}, raw_questions: {raw_questions}")
            else:
                raw_questions = [
                    "介绍一下{brandName}",
                    "{brandName}的主要产品是什么",
                    "{brandName}和竞品有什么区别"
                ]
                api_logger.info(f"[AsyncTest] Using default questions for execution_id: {execution_id}")

            # 分离主品牌和竞品品牌
            # brand_list[0] 是用户自己的品牌，其余是竞品品牌
            main_brand = brand_list[0] if brand_list else ""
            competitor_brands = brand_list[1:] if len(brand_list) > 1 else []
            
            api_logger.info(f"Main brand: {main_brand}, Competitor brands: {competitor_brands}")

            # 使用 NxM 执行引擎执行测试
            api_logger.info(f"Starting NxM execution engine for '{execution_id}'")

            # 调用 NxM 执行函数
            result = execute_nxm_test(
                execution_id=execution_id,
                main_brand=main_brand,                # 用户自己的品牌
                competitor_brands=competitor_brands,   # 竞品品牌列表（仅用于对比分析）
                selected_models=selected_models,
                raw_questions=raw_questions,
                user_id=user_id or "anonymous",
                user_level=user_level.value,
                execution_store=execution_store
            )

            if result.get('success'):
                api_logger.info(f"NxM execution completed successfully for '{execution_id}', formula: {result.get('formula')}")
            else:
                api_logger.error(f"NxM execution failed for '{execution_id}': {result.get('error')}")

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            api_logger.error(f"Async test execution failed for execution_id {execution_id}: {e}\nTraceback: {error_traceback}")
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'status': 'failed',
                    'error': f"{str(e)}\nTraceback: {error_traceback}"
                })
    thread = Thread(target=run_async_test)
    thread.start()

    return jsonify({'status': 'success', 'execution_id': execution_id, 'message': 'Test started successfully'})

import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


@wechat_bp.route('/api/mvp/deepseek-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/deepseek-test', require_auth=False, validate_inputs=True)
def mvp_deepseek_test():
    """
    DeepSeek MVP测试接口 - 同步顺序执行，确保每个问题都拿到结果
    参考豆包MVP成功经验，使用30秒超时
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        # 提取参数
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 初始化状态
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': len(questions),
            'status': 'processing',
            'stage': 'ai_testing',
            'results': [],
            'start_time': datetime.now().isoformat(),
            'platform': 'deepseek'
        }
        
        api_logger.info(f"[DeepSeek MVP] Starting brand test for {main_brand} with {len(questions)} questions")
        
        # DeepSeek配置（从环境变量或配置管理器获取）
        api_key = os.getenv('DEEPSEEK_API_KEY') or config_manager.get_api_key('deepseek')
        model_id = os.getenv('DEEPSEEK_MODEL_ID') or config_manager.get_platform_model('deepseek') or 'deepseek-chat'
        
        if not api_key:
            raise ValueError("DeepSeek API密钥未配置")
        
        api_logger.info(f"[DeepSeek MVP] Using model_id: {model_id}")
        
        # 顺序执行每个问题（同步执行，确保拿到结果）
        results = []
        for idx, question in enumerate(questions):
            try:
                # 更新进度
                progress = int((idx / len(questions)) * 100)
                execution_store[execution_id].update({
                    'progress': progress,
                    'completed': idx,
                    'status': f'Processing question {idx + 1}/{len(questions)}'
                })
                
                # 替换品牌占位符
                actual_question = question.replace('{brandName}', main_brand)
                if len(brand_list) > 1:
                    actual_question = actual_question.replace('{competitorBrand}', brand_list[1])
                
                api_logger.info(f"[DeepSeek MVP] Q{idx + 1}: {actual_question[:50]}...")
                
                # 调用DeepSeek API
                adapter = AIAdapterFactory.create(AIPlatformType.DEEPSEEK, api_key, model_id)
                
                start_time = time.time()
                ai_response = adapter.send_prompt(actual_question, timeout=30)  # DeepSeek使用30秒超时
                latency = time.time() - start_time
                
                # 导入AI响应记录器（增强版V2）
                from utils.ai_response_logger_v2 import log_ai_response
                
                if ai_response.success:
                    result_item = {
                        'question': actual_question,
                        'response': ai_response.content,
                        'platform': 'DeepSeek',
                        'model': model_id,
                        'latency': round(latency * 1000),  # 转换为毫秒
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.info(f"[DeepSeek MVP] Q{idx + 1} success in {latency:.2f}s, response length: {len(ai_response.content)}")
                    
                    # 自动记录成功的AI响应
                    try:
                        log_ai_response(
                            question=actual_question,
                            response=ai_response.content,
                            platform='DeepSeek',
                            model=model_id,
                            brand=main_brand,
                            competitor=brand_list[1] if len(brand_list) > 1 else None,
                            industry='汽车改装',
                            question_category='品牌搜索',
                            latency_ms=round(latency * 1000),
                            tokens_used=getattr(ai_response, 'tokens_used', None),
                            prompt_tokens=getattr(ai_response, 'prompt_tokens', None),
                            completion_tokens=getattr(ai_response, 'completion_tokens', None),
                            success=True,
                            temperature=0.7,
                            max_tokens=1000,
                            timeout_seconds=30,
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            session_id=request.headers.get('X-Session-ID'),
                            user_id=getattr(g, 'user_id', None),
                            raw_response=getattr(ai_response, 'metadata', None),
                            metadata={
                                'source': 'deepseek_mvp_test_v2',
                                'api_version': 'v1',
                                'response_length': len(ai_response.content) if ai_response.content else 0
                            }
                        )
                        api_logger.info(f"[DeepSeek MVP] Q{idx + 1} AI响应已记录到训练数据集")
                    except Exception as log_error:
                        api_logger.warning(f"[DeepSeek MVP] Q{idx + 1} 记录AI响应失败: {log_error}")
                else:
                    result_item = {
                        'question': actual_question,
                        'response': f'API调用失败: {ai_response.error_message}',
                        'platform': 'DeepSeek',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': False,
                        'error': ai_response.error_message,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.warning(f"[DeepSeek MVP] Q{idx + 1} failed: {ai_response.error_message}")
                    
                    # 记录失败的调用
                    try:
                        log_ai_response(
                            question=actual_question,
                            response='',
                            platform='DeepSeek',
                            model=model_id,
                            brand=main_brand,
                            latency_ms=round(latency * 1000),
                            success=False,
                            error_message=ai_response.error_message,
                            error_type=getattr(ai_response, 'error_type', 'unknown'),
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            metadata={'source': 'deepseek_mvp_test_v2', 'error_phase': 'api_call'}
                        )
                    except Exception:
                        pass
                
                results.append(result_item)
                execution_store[execution_id]['results'].append(result_item)
                
            except Exception as e:
                api_logger.error(f"[DeepSeek MVP] Q{idx + 1} exception: {str(e)}")
                results.append({
                    'question': actual_question if 'actual_question' in locals() else question,
                    'response': f'处理异常: {str(e)}',
                    'platform': 'DeepSeek',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 完成
        execution_store[execution_id].update({
            'progress': 100,
            'completed': len(questions),
            'status': 'completed',
            'stage': 'completed',
            'is_completed': True
        })
        
        api_logger.info(f"[DeepSeek MVP] Test completed for {main_brand}, {len([r for r in results if r.get('success')])}/{len(results)} successful")
        
        return jsonify({
            'status': 'success',
            'execution_id': execution_id,
            'message': 'DeepSeek test completed',
            'results': results
        })
        
    except Exception as e:
        api_logger.error(f"[DeepSeek MVP] Test failed: {str(e)}")
        return jsonify({'error': f'Test failed: {str(e)}'}), 500


@wechat_bp.route('/api/mvp/qwen-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/qwen-test', require_auth=False, validate_inputs=True)
def mvp_qwen_test():
    """
    通义千问(Qwen) MVP测试接口 - 同步顺序执行，确保每个问题都拿到结果
    参考豆包MVP成功经验，使用45秒超时
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        # 提取参数
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 初始化状态
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': len(questions),
            'status': 'processing',
            'stage': 'ai_testing',
            'results': [],
            'start_time': datetime.now().isoformat(),
            'platform': 'qwen'
        }
        
        api_logger.info(f"[Qwen MVP] Starting brand test for {main_brand} with {len(questions)} questions")
        
        # Qwen配置（从环境变量或配置管理器获取）
        api_key = os.getenv('QWEN_API_KEY') or config_manager.get_api_key('qwen')
        model_id = os.getenv('QWEN_MODEL_ID') or config_manager.get_platform_model('qwen') or 'qwen-max'
        
        if not api_key:
            raise ValueError("通义千问API密钥未配置")
        
        api_logger.info(f"[Qwen MVP] Using model_id: {model_id}")
        
        # 顺序执行每个问题（同步执行，确保拿到结果）
        results = []
        for idx, question in enumerate(questions):
            try:
                # 更新进度
                progress = int((idx / len(questions)) * 100)
                execution_store[execution_id].update({
                    'progress': progress,
                    'completed': idx,
                    'status': f'Processing question {idx + 1}/{len(questions)}'
                })
                
                # 替换品牌占位符
                actual_question = question.replace('{brandName}', main_brand)
                if len(brand_list) > 1:
                    actual_question = actual_question.replace('{competitorBrand}', brand_list[1])
                
                api_logger.info(f"[Qwen MVP] Q{idx + 1}: {actual_question[:50]}...")
                
                # 调用Qwen API
                adapter = AIAdapterFactory.create(AIPlatformType.QWEN, api_key, model_id)
                
                start_time = time.time()
                ai_response = adapter.send_prompt(actual_question, timeout=45)  # Qwen使用45秒超时
                latency = time.time() - start_time
                
                # 导入AI响应记录器（增强版V2）
                from utils.ai_response_logger_v2 import log_ai_response
                
                if ai_response.success:
                    result_item = {
                        'question': actual_question,
                        'response': ai_response.content,
                        'platform': '通义千问',
                        'model': model_id,
                        'latency': round(latency * 1000),  # 转换为毫秒
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.info(f"[Qwen MVP] Q{idx + 1} success in {latency:.2f}s, response length: {len(ai_response.content)}")
                    
                    # 自动记录成功的AI响应
                    try:
                        log_ai_response(
                            question=actual_question,
                            response=ai_response.content,
                            platform='通义千问',
                            model=model_id,
                            brand=main_brand,
                            competitor=brand_list[1] if len(brand_list) > 1 else None,
                            industry='汽车改装',
                            question_category='品牌搜索',
                            latency_ms=round(latency * 1000),
                            tokens_used=getattr(ai_response, 'tokens_used', None),
                            prompt_tokens=getattr(ai_response, 'prompt_tokens', None),
                            completion_tokens=getattr(ai_response, 'completion_tokens', None),
                            success=True,
                            temperature=0.7,
                            max_tokens=1000,
                            timeout_seconds=45,
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            session_id=request.headers.get('X-Session-ID'),
                            user_id=getattr(g, 'user_id', None),
                            raw_response=getattr(ai_response, 'metadata', None),
                            metadata={
                                'source': 'qwen_mvp_test_v2',
                                'api_version': 'v1',
                                'response_length': len(ai_response.content) if ai_response.content else 0
                            }
                        )
                        api_logger.info(f"[Qwen MVP] Q{idx + 1} AI响应已记录到训练数据集")
                    except Exception as log_error:
                        api_logger.warning(f"[Qwen MVP] Q{idx + 1} 记录AI响应失败: {log_error}")
                else:
                    result_item = {
                        'question': actual_question,
                        'response': f'API调用失败: {ai_response.error_message}',
                        'platform': '通义千问',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': False,
                        'error': ai_response.error_message,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.warning(f"[Qwen MVP] Q{idx + 1} failed: {ai_response.error_message}")
                    
                    # 记录失败的调用
                    try:
                        log_ai_response(
                            question=actual_question,
                            response='',
                            platform='通义千问',
                            model=model_id,
                            brand=main_brand,
                            latency_ms=round(latency * 1000),
                            success=False,
                            error_message=ai_response.error_message,
                            error_type=getattr(ai_response, 'error_type', 'unknown'),
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            metadata={'source': 'qwen_mvp_test_v2', 'error_phase': 'api_call'}
                        )
                    except Exception:
                        pass
                
                results.append(result_item)
                execution_store[execution_id]['results'].append(result_item)
                
            except Exception as e:
                api_logger.error(f"[Qwen MVP] Q{idx + 1} exception: {str(e)}")
                results.append({
                    'question': actual_question if 'actual_question' in locals() else question,
                    'response': f'处理异常: {str(e)}',
                    'platform': '通义千问',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 完成
        execution_store[execution_id].update({
            'progress': 100,
            'completed': len(questions),
            'status': 'completed',
            'stage': 'completed',
            'is_completed': True
        })
        
        api_logger.info(f"[Qwen MVP] Test completed for {main_brand}, {len([r for r in results if r.get('success')])}/{len(results)} successful")
        
        return jsonify({
            'status': 'success',
            'execution_id': execution_id,
            'message': 'Qwen test completed',
            'results': results
        })
        
    except Exception as e:
        api_logger.error(f"[Qwen MVP] Test failed: {str(e)}")
        return jsonify({'error': f'Test failed: {str(e)}'}), 500


@wechat_bp.route('/api/mvp/zhipu-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/zhipu-test', require_auth=False, validate_inputs=True)
def mvp_zhipu_test():
    """
    智谱AI(Zhipu) MVP测试接口 - 同步顺序执行，确保每个问题都拿到结果
    参考豆包MVP成功经验，使用45秒超时
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        # 提取参数
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 初始化状态
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': len(questions),
            'status': 'processing',
            'stage': 'ai_testing',
            'results': [],
            'start_time': datetime.now().isoformat(),
            'platform': 'zhipu'
        }
        
        api_logger.info(f"[Zhipu MVP] Starting brand test for {main_brand} with {len(questions)} questions")
        
        # Zhipu配置（从环境变量或配置管理器获取）
        api_key = os.getenv('ZHIPU_API_KEY') or config_manager.get_api_key('zhipu')
        model_id = os.getenv('ZHIPU_MODEL_ID') or config_manager.get_platform_model('zhipu') or 'glm-4'
        
        if not api_key:
            raise ValueError("智谱AI API密钥未配置")
        
        api_logger.info(f"[Zhipu MVP] Using model_id: {model_id}")
        
        # 顺序执行每个问题（同步执行，确保拿到结果）
        results = []
        for idx, question in enumerate(questions):
            try:
                # 更新进度
                progress = int((idx / len(questions)) * 100)
                execution_store[execution_id].update({
                    'progress': progress,
                    'completed': idx,
                    'status': f'Processing question {idx + 1}/{len(questions)}'
                })
                
                # 替换品牌占位符
                actual_question = question.replace('{brandName}', main_brand)
                if len(brand_list) > 1:
                    actual_question = actual_question.replace('{competitorBrand}', brand_list[1])
                
                api_logger.info(f"[Zhipu MVP] Q{idx + 1}: {actual_question[:50]}...")
                
                # 调用Zhipu API
                adapter = AIAdapterFactory.create(AIPlatformType.ZHIPU, api_key, model_id)
                
                start_time = time.time()
                ai_response = adapter.send_prompt(actual_question, timeout=45)  # Zhipu使用45秒超时
                latency = time.time() - start_time
                
                # 导入AI响应记录器（增强版V2）
                from utils.ai_response_logger_v2 import log_ai_response
                
                if ai_response.success:
                    result_item = {
                        'question': actual_question,
                        'response': ai_response.content,
                        'platform': '智谱AI',
                        'model': model_id,
                        'latency': round(latency * 1000),  # 转换为毫秒
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.info(f"[Zhipu MVP] Q{idx + 1} success in {latency:.2f}s, response length: {len(ai_response.content)}")
                    
                    # 自动记录成功的AI响应
                    try:
                        log_ai_response(
                            question=actual_question,
                            response=ai_response.content,
                            platform='智谱AI',
                            model=model_id,
                            brand=main_brand,
                            competitor=brand_list[1] if len(brand_list) > 1 else None,
                            industry='汽车改装',
                            question_category='品牌搜索',
                            latency_ms=round(latency * 1000),
                            tokens_used=getattr(ai_response, 'tokens_used', None),
                            prompt_tokens=getattr(ai_response, 'prompt_tokens', None),
                            completion_tokens=getattr(ai_response, 'completion_tokens', None),
                            success=True,
                            temperature=0.7,
                            max_tokens=1000,
                            timeout_seconds=45,
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            session_id=request.headers.get('X-Session-ID'),
                            user_id=getattr(g, 'user_id', None),
                            raw_response=getattr(ai_response, 'metadata', None),
                            metadata={
                                'source': 'zhipu_mvp_test_v2',
                                'api_version': 'v1',
                                'response_length': len(ai_response.content) if ai_response.content else 0
                            }
                        )
                        api_logger.info(f"[Zhipu MVP] Q{idx + 1} AI响应已记录到训练数据集")
                    except Exception as log_error:
                        api_logger.warning(f"[Zhipu MVP] Q{idx + 1} 记录AI响应失败: {log_error}")
                else:
                    result_item = {
                        'question': actual_question,
                        'response': f'API调用失败: {ai_response.error_message}',
                        'platform': '智谱AI',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': False,
                        'error': ai_response.error_message,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.warning(f"[Zhipu MVP] Q{idx + 1} failed: {ai_response.error_message}")
                    
                    # 记录失败的调用
                    try:
                        log_ai_response(
                            question=actual_question,
                            response='',
                            platform='智谱AI',
                            model=model_id,
                            brand=main_brand,
                            latency_ms=round(latency * 1000),
                            success=False,
                            error_message=ai_response.error_message,
                            error_type=getattr(ai_response, 'error_type', 'unknown'),
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            metadata={'source': 'zhipu_mvp_test_v2', 'error_phase': 'api_call'}
                        )
                    except Exception:
                        pass
                
                results.append(result_item)
                execution_store[execution_id]['results'].append(result_item)
                
            except Exception as e:
                api_logger.error(f"[Zhipu MVP] Q{idx + 1} exception: {str(e)}")
                results.append({
                    'question': actual_question if 'actual_question' in locals() else question,
                    'response': f'处理异常: {str(e)}',
                    'platform': '智谱AI',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 完成
        execution_store[execution_id].update({
            'progress': 100,
            'completed': len(questions),
            'status': 'completed',
            'stage': 'completed',
            'is_completed': True
        })
        
        api_logger.info(f"[Zhipu MVP] Test completed for {main_brand}, {len([r for r in results if r.get('success')])}/{len(results)} successful")
        
        return jsonify({
            'status': 'success',
            'execution_id': execution_id,
            'message': 'Zhipu test completed',
            'results': results
        })
        
    except Exception as e:
        api_logger.error(f"[Zhipu MVP] Test failed: {str(e)}")
        return jsonify({'error': f'Test failed: {str(e)}'}), 500


@wechat_bp.route('/api/mvp/brand-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/brand-test', require_auth=False, validate_inputs=True)
def mvp_brand_test():
    """
    MVP专用品牌测试接口 - 同步顺序执行，确保每个问题都拿到结果
    简化版：只调用豆包API，不使用复杂的评分和分析流程
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        # 提取参数
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 初始化状态
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': len(questions),
            'status': 'processing',
            'stage': 'ai_testing',
            'results': [],
            'start_time': datetime.now().isoformat()
        }
        
        api_logger.info(f"[MVP] Starting brand test for {main_brand} with {len(questions)} questions")
        
        # 顺序执行每个问题（同步执行，确保拿到结果）
        results = []
        for idx, question in enumerate(questions):
            try:
                # 更新进度
                progress = int((idx / len(questions)) * 100)
                execution_store[execution_id].update({
                    'progress': progress,
                    'completed': idx,
                    'status': f'Processing question {idx + 1}/{len(questions)}'
                })
                
                # 替换品牌占位符
                actual_question = question.replace('{brandName}', main_brand)
                if len(brand_list) > 1:
                    actual_question = actual_question.replace('{competitorBrand}', brand_list[1])
                
                api_logger.info(f"[MVP] Q{idx + 1}: {actual_question[:50]}...")
                
                # 调用豆包API
                from wechat_backend.ai_adapters.factory import AIAdapterFactory
                from wechat_backend.ai_adapters.base_adapter import AIPlatformType
                
                # 获取豆包配置
                from wechat_backend.config_manager import config_manager
                api_key = config_manager.get_api_key('doubao')
                # 优先从环境变量获取模型ID，其次从配置管理器，最后使用默认模型
                import os
                model_id = os.getenv('DOUBAO_MODEL_ID') or config_manager.get_platform_model('doubao') or 'doubao-pro-32k'
                
                api_logger.info(f"[MVP] Using Doubao model_id: {model_id}, env: {os.getenv('DOUBAO_MODEL_ID')}")
                
                if not api_key:
                    raise ValueError("豆包API密钥未配置")
                
                # 创建适配器并调用（MVP使用更长的超时时间）
                adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, model_id)
                
                start_time = time.time()
                ai_response = adapter.send_prompt(actual_question, timeout=90)  # MVP专用：90秒超时
                latency = time.time() - start_time
                
                # 导入AI响应记录器（增强版V2）
                from utils.ai_response_logger_v2 import log_ai_response
                
                if ai_response.success:
                    result_item = {
                        'question': actual_question,
                        'response': ai_response.content,
                        'platform': '豆包',
                        'model': model_id,
                        'latency': round(latency * 1000),  # 转换为毫秒
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.info(f"[MVP] Q{idx + 1} success in {latency:.2f}s, response length: {len(ai_response.content)}")
                    
                    # 自动记录成功的AI响应（增强版V2，用于后续模型训练和分析）
                    try:
                        log_ai_response(
                            # 核心内容
                            question=actual_question,
                            response=ai_response.content,
                            platform='豆包',
                            model=model_id,
                            
                            # 业务信息
                            brand=main_brand,
                            competitor=brand_list[1] if len(brand_list) > 1 else None,
                            industry='汽车改装',  # 可根据实际情况调整
                            question_category='品牌搜索',  # 可根据问题类型动态设置
                            
                            # 性能指标
                            latency_ms=round(latency * 1000),
                            tokens_used=getattr(ai_response, 'tokens_used', None),
                            prompt_tokens=getattr(ai_response, 'prompt_tokens', None),
                            completion_tokens=getattr(ai_response, 'completion_tokens', None),
                            
                            # 执行状态
                            success=True,
                            
                            # 请求配置
                            temperature=0.7,
                            max_tokens=1000,
                            timeout_seconds=90,
                            
                            # 上下文信息
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            session_id=request.headers.get('X-Session-ID'),
                            user_id=getattr(g, 'user_id', None),
                            
                            # 原始响应数据（用于调试）
                            raw_response=getattr(ai_response, 'metadata', None),
                            
                            # 元数据
                            metadata={
                                'source': 'mvp_brand_test_v2',
                                'api_version': 'v1',
                                'response_length': len(ai_response.content) if ai_response.content else 0
                            }
                        )
                        api_logger.info(f"[MVP] Q{idx + 1} AI响应已记录到训练数据集（V2增强版）")
                    except Exception as log_error:
                        # 记录失败不应影响主流程
                        api_logger.warning(f"[MVP] Q{idx + 1} 记录AI响应失败: {log_error}")
                else:
                    result_item = {
                        'question': actual_question,
                        'response': f'API调用失败: {ai_response.error_message}',
                        'platform': '豆包',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': False,
                        'error': ai_response.error_message,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.warning(f"[MVP] Q{idx + 1} failed: {ai_response.error_message}")
                    
                    # 记录失败的调用（增强版V2）
                    try:
                        log_ai_response(
                            question=actual_question,
                            response='',
                            platform='豆包',
                            model=model_id,
                            brand=main_brand,
                            latency_ms=round(latency * 1000),
                            success=False,
                            error_message=ai_response.error_message,
                            error_type=getattr(ai_response, 'error_type', 'unknown'),
                            execution_id=execution_id,
                            question_index=idx + 1,
                            total_questions=len(questions),
                            metadata={'source': 'mvp_brand_test_v2', 'error_phase': 'api_call'}
                        )
                    except Exception:
                        pass  # 忽略记录失败的错误
                
                results.append(result_item)
                execution_store[execution_id]['results'].append(result_item)
                
            except Exception as e:
                api_logger.error(f"[MVP] Q{idx + 1} exception: {str(e)}")
                results.append({
                    'question': actual_question if 'actual_question' in locals() else question,
                    'response': f'处理异常: {str(e)}',
                    'platform': '豆包',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 完成
        execution_store[execution_id].update({
            'progress': 100,
            'completed': len(questions),
            'status': 'completed',
            'stage': 'completed',
            'is_completed': True
        })
        
        api_logger.info(f"[MVP] Test completed for {main_brand}, {len([r for r in results if r.get('success')])}/{len(results)} successful")
        
        return jsonify({
            'status': 'success',
            'execution_id': execution_id,
            'message': 'Test completed',
            'results': results
        })
        
    except Exception as e:
        api_logger.error(f"[MVP] Test failed: {str(e)}")
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

def process_and_aggregate_results_with_ai_judge(raw_results, all_brands, main_brand, judge_platform=None, judge_model=None, judge_api_key=None):
    """
    结果聚合引擎 (CompetitorDataAggregator)
    """
    # Initialize old_handler to None to prevent UnboundLocalError
    old_handler = None
    try:
        # Set a timeout to prevent hanging in AI platform calls
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)  # 2-minute timeout for the entire function
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

        # 导入误解分析器
        try:
            from .intelligence_services.misunderstanding_analyzer import MisunderstandingAnalyzer
            misunderstanding_analyzer = MisunderstandingAnalyzer()
            api_logger.info("Misunderstanding analyzer loaded successfully")
        except ImportError:
            api_logger.warning("Misunderstanding analyzer not available")
            misunderstanding_analyzer = None

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
            try:
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

                        # 数据清洗：如果响应内容为空，填充默认值
                        if not ai_response_content:
                            ai_response_content = "暂无分析结论"

                        question = result.get('question', result.get('original_question', ''))

                        # Only evaluate with AI judge if it's available
                        if ai_judge:
                            # Add timeout protection for individual AI judge calls
                            try:
                                # Temporarily disable the global alarm for this call
                                signal.alarm(0)

                                # Set a shorter timeout for individual evaluations
                                old_handler_eval = signal.signal(signal.SIGALRM, timeout_handler)
                                signal.alarm(30)  # 30-second timeout for individual evaluation

                                judge_result = ai_judge.evaluate_response(current_brand, question, ai_response_content)

                                # Reset the alarm to the original timeout
                                signal.alarm(0)
                                signal.signal(signal.SIGALRM, old_handler)
                                signal.alarm(120)  # Resume the 2-minute timeout for the whole function
                            except TimeoutError:
                                # Reset the alarm to the original timeout
                                signal.alarm(0)
                                signal.signal(signal.SIGALRM, old_handler)
                                signal.alarm(120)  # Resume the 2-minute timeout for the whole function

                                api_logger.error(f"AI judge evaluation timed out for brand {current_brand}")
                                judge_result = None
                            except Exception as e:
                                # Reset the alarm to the original timeout
                                signal.alarm(0)
                                signal.signal(signal.SIGALRM, old_handler)
                                signal.alarm(120)  # Resume the 2-minute timeout for the whole function

                                api_logger.error(f"AI judge evaluation failed for brand {current_brand}: {str(e)}")
                                judge_result = None

                            if judge_result:
                                # 使用基础评分引擎计算基础分数
                                basic_score = scoring_engine.calculate([judge_result])

                                # 使用增强评分引擎计算增强分数（用于内部分析）
                                enhanced_result = calculate_enhanced_scores([judge_result], brand_name=current_brand)

                                # 【任务 A：集成自动评分引擎】
                                # 在 AI 生成回复后立即调用 evaluator.py 计算质量指标
                                try:
                                    from gco_validator.scoring import ResponseEvaluator
                                    evaluator = ResponseEvaluator()
                                    scoring_result = evaluator.evaluate_response(ai_response_content, question, current_brand)

                                    # 记录评分日志
                                    api_logger.info(f"[Evaluator] {current_brand} 评分：{scoring_result.overall_score}分 (准确度:{scoring_result.accuracy}, 完整度:{scoring_result.completeness})")
                                except Exception as eval_error:
                                    api_logger.error(f"Evaluation failed for {current_brand}: {str(eval_error)}")
                                    # 如果评分失败，使用默认值
                                    scoring_result = None

                                # 使用误解分析器进行分析
                                misunderstanding_result = None
                                if misunderstanding_analyzer:
                                    try:
                                        misunderstanding_result = misunderstanding_analyzer.analyze(
                                            brand_name=current_brand,
                                            question_text=question,
                                            ai_answer=ai_response_content,
                                            judge_result=judge_result
                                        )
                                        api_logger.info(f"Misunderstanding analysis completed for {current_brand}: {misunderstanding_result.has_issue}")
                                    except Exception as e:
                                        api_logger.error(f"Error in misunderstanding analysis: {e}")
                                        # 如果分析失败，创建默认结果
                                        misunderstanding_result = None

                                # 数据清洗：确保分数字段存在且为数字
                                authority_score = getattr(judge_result, 'accuracy_score', 0)
                                if not isinstance(authority_score, (int, float)):
                                    authority_score = 0

                                visibility_score = getattr(judge_result, 'completeness_score', 0)
                                if not isinstance(visibility_score, (int, float)):
                                    visibility_score = 0

                                sentiment_score = getattr(judge_result, 'sentiment_score', 0)
                                if not isinstance(sentiment_score, (int, float)):
                                    sentiment_score = 0

                                purity_score = getattr(judge_result, 'purity_score', 0)
                                if not isinstance(purity_score, (int, float)):
                                    purity_score = 0

                                consistency_score = getattr(judge_result, 'consistency_score', 0)
                                if not isinstance(consistency_score, (int, float)):
                                    consistency_score = 0

                                score = getattr(basic_score, 'geo_score', 0)
                                if not isinstance(score, (int, float)):
                                    score = 0

                                detailed_result = {
                                    'success': True,
                                    'brand': current_brand,
                                    'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                                    'question': question,
                                    'response': ai_response_content,
                                    'authority_score': authority_score,
                                    'visibility_score': visibility_score,
                                    'sentiment_score': sentiment_score,
                                    'purity_score': purity_score,
                                    'consistency_score': consistency_score,
                                    'score': score,  # 保持原有分数以确保兼容性
                                    # 【任务 A：数据入库】将 ScoringResult 结构化存入对应 TestCase 的结果对象中
                                    'quality_metrics': {
                                        'accuracy_score': scoring_result.accuracy if scoring_result and isinstance(scoring_result.accuracy, (int, float)) else 0,
                                        'completeness_score': scoring_result.completeness if scoring_result and isinstance(scoring_result.completeness, (int, float)) else 0,
                                        'relevance_score': scoring_result.relevance if scoring_result and isinstance(scoring_result.relevance, (int, float)) else 0,
                                        'coherence_score': scoring_result.coherence if scoring_result and isinstance(scoring_result.coherence, (int, float)) else 0,
                                        'overall_quality_score': scoring_result.overall_score if scoring_result and isinstance(scoring_result.overall_score, (int, float)) else 0,
                                        'detailed_feedback': scoring_result.detailed_feedback if scoring_result else {}
                                    } if scoring_result else None,
                                    'enhanced_scores': {
                                        'geo_score': getattr(enhanced_result, 'geo_score', 0),
                                        'cognitive_confidence': getattr(enhanced_result, 'cognitive_confidence', 0.0),
                                        'bias_indicators': getattr(enhanced_result, 'bias_indicators', []),
                                        'detailed_analysis': getattr(enhanced_result, 'detailed_analysis', {}),
                                        'recommendations': getattr(enhanced_result, 'recommendations', [])
                                    },
                                    'misunderstanding_analysis': {
                                        'has_issue': getattr(misunderstanding_result, 'has_issue', False),
                                        'issue_types': getattr(misunderstanding_result, 'issue_types', []),
                                        'risk_level': getattr(misunderstanding_result, 'risk_level', 'low'),
                                        'issue_summary': getattr(misunderstanding_result, 'issue_summary', 'Analysis not available'),
                                        'improvement_hint': getattr(misunderstanding_result, 'improvement_hint', 'No suggestions')
                                    } if misunderstanding_result else None,
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
                            # 【任务 A：集成自动评分引擎】即使没有AI judge，也要进行基本评分
                            try:
                                from gco_validator.scoring import ResponseEvaluator
                                evaluator = ResponseEvaluator()
                                scoring_result = evaluator.evaluate_response(ai_response_content, question, current_brand)

                                # 记录评分日志
                                api_logger.info(f"[Evaluator] {current_brand} 评分：{scoring_result.overall_score}分 (准确度:{scoring_result.accuracy}, 完整度:{scoring_result.completeness})")
                            except Exception as eval_error:
                                api_logger.error(f"Evaluation failed for {current_brand}: {str(eval_error)}")
                                # 如果评分失败，使用默认值
                                scoring_result = None

                            # P0-2 修复：即使没有 AI judge，也要使用 ResponseEvaluator 的评分结果
                            authority_score = scoring_result.accuracy if scoring_result and isinstance(scoring_result.accuracy, (int, float)) else 0
                            visibility_score = scoring_result.completeness if scoring_result and isinstance(scoring_result.completeness, (int, float)) else 0
                            # 将 relevance 映射为 sentiment (好感度)
                            sentiment_score = scoring_result.relevance if scoring_result and isinstance(scoring_result.relevance, (int, float)) else 50
                            # 使用 coherence 作为 purity 和 consistency 的参考
                            purity_score = scoring_result.coherence if scoring_result and isinstance(scoring_result.coherence, (int, float)) else 0
                            consistency_score = scoring_result.coherence if scoring_result and isinstance(scoring_result.coherence, (int, float)) else 0
                            score = scoring_result.overall_score if scoring_result and isinstance(scoring_result.overall_score, (int, float)) else 0

                            detailed_result = {
                                'success': True,
                                'brand': current_brand,
                                'aiModel': result.get('model', result.get('ai_model', 'unknown')),
                                'question': question,
                                'response': ai_response_content,
                                'authority_score': authority_score,  # P0-2 修复：使用 evaluator 的评分
                                'visibility_score': visibility_score,
                                'sentiment_score': sentiment_score,
                                'purity_score': purity_score,
                                'consistency_score': consistency_score,
                                'score': score,  # P0-2 修复：使用 evaluator 的总分
                                # 【任务 A：数据入库】将 ScoringResult 结构化存入对应 TestCase 的结果对象中
                                'quality_metrics': {
                                    'accuracy_score': scoring_result.accuracy if scoring_result and isinstance(scoring_result.accuracy, (int, float)) else 0,
                                    'completeness_score': scoring_result.completeness if scoring_result and isinstance(scoring_result.completeness, (int, float)) else 0,
                                    'relevance_score': scoring_result.relevance if scoring_result and isinstance(scoring_result.relevance, (int, float)) else 0,
                                    'coherence_score': scoring_result.coherence if scoring_result and isinstance(scoring_result.coherence, (int, float)) else 0,
                                    'overall_quality_score': scoring_result.overall_score if scoring_result and isinstance(scoring_result.overall_score, (int, float)) else 0,
                                    'detailed_feedback': scoring_result.detailed_feedback if scoring_result else {}
                                } if scoring_result else None,
                                'enhanced_scores': {
                                    'geo_score': score,
                                    'cognitive_confidence': 0.5,
                                    'bias_indicators': [],
                                    'detailed_analysis': {},
                                    'recommendations': []
                                },
                                'misunderstanding_analysis': None,  # No analysis when AI judge is not available
                                'category': '国内' if result.get('model', result.get('ai_model', '')) in ['通义千问', '文心一言', '豆包', 'Kimi', '元宝', 'DeepSeek', '讯飞星火'] else '海外'
                            }
                            # Add a basic judge result with scores from evaluator for scoring calculations
                            basic_judge_result = JudgeResult(
                                accuracy_score=authority_score,
                                completeness_score=visibility_score,
                                sentiment_score=sentiment_score,
                                purity_score=purity_score,
                                consistency_score=consistency_score,
                                judgement="Auto-evaluated by ResponseEvaluator",
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
            except (TypeError, KeyError) as e:
                # 捕获TypeError或KeyError，确保即使部分模型调用失败，剩余模型的数据也能正常聚合
                api_logger.error(f"Error processing result due to TypeError/KeyError: {e}, result: {result}")
                # 创建一个默认的成功结果，确保任务能继续推进
                default_result = {
                    'success': True,
                    'brand': result.get('brand_name', result.get('brand', 'unknown')) if isinstance(result, dict) else 'unknown',
                    'aiModel': result.get('model', result.get('ai_model', 'unknown')) if isinstance(result, dict) else 'unknown',
                    'question': result.get('question', result.get('original_question', '')) if isinstance(result, dict) else 'unknown',
                    'response': "暂无分析结论",
                    'score': 0,
                    'error_message': f"Processing error: {str(e)}",
                    'error_type': 'ProcessingError'
                }
                detailed_results.append(default_result)
                continue  # 继续处理下一个结果
            except Exception as e:
                # 捕获其他类型的异常
                api_logger.error(f"Unexpected error processing result: {e}, result: {result}")
                # 创建一个默认的成功结果，确保任务能继续推进
                default_result = {
                    'success': True,
                    'brand': result.get('brand_name', result.get('brand', 'unknown')) if isinstance(result, dict) else 'unknown',
                    'aiModel': result.get('model', result.get('ai_model', 'unknown')) if isinstance(result, dict) else 'unknown',
                    'question': result.get('question', result.get('original_question', '')) if isinstance(result, dict) else 'unknown',
                    'response': "暂无分析结论",
                    'score': 0,
                    'error_message': f"Unexpected error: {str(e)}",
                    'error_type': 'UnexpectedError'
                }
                detailed_results.append(default_result)
                continue  # 继续处理下一个结果

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

        # Cancel the alarm before returning
        signal.alarm(0)
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)  # Restore the old handler
        return final_result
    except TimeoutError as te:
        # Handle timeout specifically
        api_logger.error(f"Timeout in process_and_aggregate_results_with_ai_judge: {str(te)}")

        # Cancel the alarm before returning
        signal.alarm(0)
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)  # Restore the old handler

        # Return default results to prevent deadlock
        default_results = []
        for brand in all_brands:
            default_results.append({
                'success': True,
                'brand': brand,
                'aiModel': 'default',
                'question': 'default question',
                'response': 'AI评估服务超时，使用默认数据',
                'authority_score': 0,
                'visibility_score': 0,
                'sentiment_score': 0,
                'purity_score': 0,
                'consistency_score': 0,
                'score': 0,
                'quality_metrics': {
                    'accuracy_score': 0,
                    'completeness_score': 0,
                    'relevance_score': 0,
                    'coherence_score': 0,
                    'overall_quality_score': 0,
                    'detailed_feedback': {}
                },
                'enhanced_scores': {
                    'geo_score': 0,
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                },
                'misunderstanding_analysis': None,
                'category': 'default'
            })

        default_brand_scores = {}
        for brand in all_brands:
            default_brand_scores[brand] = {
                'overallScore': 0,
                'overallGrade': 'D',
                'overallAuthority': 0,
                'overallVisibility': 0,
                'overallSentiment': 0,
                'overallPurity': 0,
                'overallConsistency': 0,
                'overallSummary': 'AI评估服务超时，使用默认数据',
                'enhanced_data': {
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                }
            }

        # Prepare the timeout result
        timeout_result = {
            'detailed_results': default_results,
            'main_brand': default_brand_scores.get(main_brand, {
                'overallScore': 0,
                'overallGrade': 'D',
                'enhanced_data': {
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                }
            }),
            'competitiveAnalysis': {
                'brandScores': default_brand_scores,
                'firstMentionByPlatform': {},
                'interceptionRisks': {}
            },
            'summary': {'total_tests': 0, 'brands_tested': len(all_brands)}
        }

        # Print JSON sample for verification
        import json
        print("=== BACKEND FINAL JSON SAMPLE (TIMEOUT) ===")
        print(json.dumps(timeout_result, indent=2, ensure_ascii=False))
        print("===============================")

        return timeout_result
    except Exception as e:
        # Cancel the alarm before returning
        signal.alarm(0)
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)  # Restore the old handler

        # 如果整个处理过程失败，返回默认的评估数据对象
        api_logger.error(f"Critical failure in process_and_aggregate_results_with_ai_judge: {str(e)}")

        # 创建默认的评估数据对象
        default_results = []
        for brand in all_brands:
            default_results.append({
                'success': True,
                'brand': brand,
                'aiModel': 'default',
                'question': 'default question',
                'response': '默认分析结论',
                'authority_score': 0,
                'visibility_score': 0,
                'sentiment_score': 0,
                'purity_score': 0,
                'consistency_score': 0,
                'score': 0,
                'quality_metrics': {
                    'accuracy_score': 0,
                    'completeness_score': 0,
                    'relevance_score': 0,
                    'coherence_score': 0,
                    'overall_quality_score': 0,
                    'detailed_feedback': {}
                },
                'enhanced_scores': {
                    'geo_score': 0,
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                },
                'misunderstanding_analysis': None,
                'category': 'default'
            })

        default_brand_scores = {}
        for brand in all_brands:
            default_brand_scores[brand] = {
                'overallScore': 0,
                'overallGrade': 'D',
                'overallAuthority': 0,
                'overallVisibility': 0,
                'overallSentiment': 0,
                'overallPurity': 0,
                'overallConsistency': 0,
                'overallSummary': '系统故障，使用默认数据',
                'enhanced_data': {
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                }
            }

        # Prepare the default result
        default_result = {
            'detailed_results': default_results,
            'main_brand': default_brand_scores.get(main_brand, {
                'overallScore': 0,
                'overallGrade': 'D',
                'enhanced_data': {
                    'cognitive_confidence': 0.0,
                    'bias_indicators': [],
                    'detailed_analysis': {},
                    'recommendations': []
                }
            }),
            'competitiveAnalysis': {
                'brandScores': default_brand_scores,
                'firstMentionByPlatform': {},
                'interceptionRisks': {}
            },
            'summary': {'total_tests': 0, 'brands_tested': len(all_brands)}
        }

        # Print JSON sample for verification
        import json
        print("=== BACKEND FINAL JSON SAMPLE (DEFAULT) ===")
        print(json.dumps(default_result, indent=2, ensure_ascii=False))
        print("===============================")

        return default_result


def convert_to_dashboard_format(aggregate_result, all_brands, main_brand):
    """
    将聚合引擎结果转换为 Dashboard 格式
    
    Args:
        aggregate_result: process_and_aggregate_results_with_ai_judge 返回的结果
        all_brands: 所有品牌列表
        main_brand: 主品牌
    
    Returns:
        Dashboard 格式的数据
    """
    try:
        detailed_results = aggregate_result.get('detailed_results', [])
        
        # ========== 集成信源分析 ==========
        try:
            from wechat_backend.analytics.source_aggregator import SourceAggregator
            
            # 准备模型响应数据
            model_responses = []
            for result in detailed_results:
                model_responses.append({
                    'model_name': result.get('aiModel', 'unknown'),
                    'ai_response': result.get('response', ''),
                    'citations': result.get('quality_metrics', {}).get('detailed_feedback', {}).get('citations', []),
                    'question': result.get('question', '')
                })
            
            # 调用信源聚合引擎
            aggregator = SourceAggregator()
            source_data = aggregator.aggregate_multiple_models(model_responses)
            
            # 提取有毒信源 (负面信源)
            toxic_sources = []
            for source in source_data.get('source_pool', []):
                # 根据引用次数和模型覆盖度判断信源质量
                citation_count = source.get('citation_count', 0)
                model_coverage = source.get('cross_model_coverage', 0)
                domain_authority = source.get('domain_authority', 'Medium')
                
                # 低质量信源判断标准：
                # 1. 被多个模型引用但权威度低
                # 2. 或者只被一个模型引用且权威度低
                if domain_authority == 'Low' or (citation_count > 2 and model_coverage == 1):
                    toxic_sources.append({
                        'url': source.get('url', ''),
                        'site': source.get('site_name', ''),
                        'model': list(model_coverage)[0] if isinstance(model_coverage, set) else 'multiple',
                        'attitude': 'negative',
                        'citation_count': citation_count,
                        'domain_authority': domain_authority
                    })
                    
        except Exception as source_error:
            api_logger.warning(f"信源分析失败：{source_error}")
            toxic_sources = []
        
        # ========== 集成排名分析 ==========
        try:
            from wechat_backend.analytics.rank_analyzer import RankAnalyzer
            
            # 按问题分组
            question_map = {}
            for result in detailed_results:
                question = result.get('question', '未知问题')
                if question not in question_map:
                    question_map[question] = {
                        'text': question,
                        'results': [],
                        'models': set()
                    }
                question_map[question]['results'].append(result)
                question_map[question]['models'].add(result.get('aiModel', 'unknown'))
            
            # 生成问题卡片
            question_cards = []
            for question_text, q_data in question_map.items():
                results = q_data['results']
                
                # 使用 RankAnalyzer 分析排名
                analyzer = RankAnalyzer()
                
                # 合并所有模型的响应
                combined_response = ' '.join([r.get('response', '') for r in results])
                
                # 分析排名
                rank_analysis = analyzer.analyze(combined_response, all_brands)
                
                # 获取主品牌的排名
                ranking_list = rank_analysis.get('ranking_list', [])
                brand_rank = ranking_list.index(main_brand) + 1 if main_brand in ranking_list else -1
                
                # 计算平均排名 (基于 geo_score 和物理排名)
                ranked_results = [r for r in results if r.get('enhanced_scores', {}).get('geo_score', 0) > 0]
                if ranked_results:
                    geo_avg_rank = sum(r['enhanced_scores']['geo_score'] for r in ranked_results) / len(ranked_results)
                    geo_avg_rank = round(geo_avg_rank / 10, 1)  # 转换为 1-10 排名
                    
                    # 如果物理排名有效，结合物理排名和 GEO 排名
                    if brand_rank > 0:
                        avg_rank = round((geo_avg_rank + brand_rank) / 2, 1)
                    else:
                        avg_rank = geo_avg_rank
                else:
                    avg_rank = brand_rank if brand_rank > 0 else '未入榜'
                
                # 计算平均情感
                sentiments = [r.get('sentiment_score', 0) for r in results if r.get('sentiment_score', 0) != 0]
                avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else '0.00'
                
                # 检查竞品拦截
                intercepted_by = []
                for result in results:
                    interception = result.get('interceptedBy', '')
                    if interception:
                        intercepted_by.append(interception)
                
                # 确定状态
                has_risk = len(intercepted_by) > 0 or (isinstance(avg_sentiment, (int, float)) and avg_sentiment < -0.3)
                
                question_cards.append({
                    'text': question_text,
                    'avgRank': str(avg_rank) if isinstance(avg_rank, float) else avg_rank,
                    'avgSentiment': str(avg_sentiment),
                    'mentionCount': len(results),
                    'totalModels': len(q_data['models']),
                    'status': 'risk' if has_risk else 'safe',
                    'interceptedBy': list(set(intercepted_by))
                })
                    
        except Exception as rank_error:
            api_logger.warning(f"排名分析失败：{rank_error}")
            # 回退到简单逻辑
            question_cards = []
            question_map = {}
            for result in detailed_results:
                question = result.get('question', '未知问题')
                if question not in question_map:
                    question_map[question] = {'text': question, 'results': [], 'models': set()}
                question_map[question]['results'].append(result)
                question_map[question]['models'].add(result.get('aiModel', 'unknown'))
            
            for question_text, q_data in question_map.items():
                results = q_data['results']
                ranked_results = [r for r in results if r.get('enhanced_scores', {}).get('geo_score', 0) > 0]
                if ranked_results:
                    avg_rank = sum(r['enhanced_scores']['geo_score'] for r in ranked_results) / len(ranked_results)
                    avg_rank = round(avg_rank / 10, 1)
                else:
                    avg_rank = '未入榜'
                
                sentiments = [r.get('sentiment_score', 0) for r in results if r.get('sentiment_score', 0) != 0]
                avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else '0.00'
                
                intercepted_by = [r.get('interceptedBy', '') for r in results if r.get('interceptedBy', '')]
                has_risk = len(intercepted_by) > 0 or (isinstance(avg_sentiment, (int, float)) and avg_sentiment < -0.3)
                
                question_cards.append({
                    'text': question_text,
                    'avgRank': str(avg_rank) if isinstance(avg_rank, float) else avg_rank,
                    'avgSentiment': str(avg_sentiment),
                    'mentionCount': len(results),
                    'totalModels': len(q_data['models']),
                    'status': 'risk' if has_risk else 'safe',
                    'interceptedBy': list(set(intercepted_by))
                })
        
        # 计算健康分
        safe_questions = [q for q in question_cards if q['status'] == 'safe']
        health_score = round((len(safe_questions) / len(question_cards)) * 100) if question_cards else 0
        
        # 计算 SOV
        total_mentions = len(detailed_results)
        main_brand_mentions = len([r for r in detailed_results if r.get('brand') == main_brand])
        sov = round((main_brand_mentions / total_mentions) * 100) if total_mentions > 0 else 0
        
        # 计算平均情感
        all_sentiments = [r.get('sentiment_score', 0) for r in detailed_results if r.get('sentiment_score', 0) != 0]
        avg_sentiment = round(sum(all_sentiments) / len(all_sentiments), 2) if all_sentiments else '0.00'
        
        dashboard_data = {
            'summary': {
                'brandName': main_brand,
                'healthScore': health_score,
                'sov': sov,
                'avgSentiment': str(avg_sentiment),
                'totalMentions': total_mentions,
                'totalTests': len(detailed_results)
            },
            'questionCards': question_cards,
            'toxicSources': toxic_sources
        }
        
        return dashboard_data
        
    except Exception as e:
        api_logger.error(f"转换 Dashboard 格式失败：{e}")
        # 返回默认数据
        return {
            'summary': {
                'brandName': main_brand,
                'healthScore': 0,
                'sov': 0,
                'avgSentiment': '0.00',
                'totalMentions': 0,
                'totalTests': 0
            },
            'questionCards': [],
            'toxicSources': []
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
        from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
        config_manager = PlatformConfigManager()

        status_info = {}

        # 预定义支持的平台
        supported_platforms = [
            'deepseek', 'deepseekr1', 'doubao', 'qwen', 'wenxin',
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
    """
    获取测试进度 - 【任务 3 优化】

    新增 is_synced 字段：
    - 当 status == 'completed' 且 len(results) == expected 时，is_synced 为 true
    - 告知前端，数据不仅运行完了，而且已经完全同步到了报告引擎中
    """
    execution_id = request.args.get('executionId')
    if execution_id and execution_id in execution_store:
        progress_data = execution_store[execution_id]

        # 【任务 3】数据同步检查 - 增加 is_synced 字段
        status = progress_data.get('status', 'unknown')
        results = progress_data.get('results', [])
        expected = progress_data.get('expected_total', progress_data.get('total', 0))
        completion_verified = progress_data.get('completion_verified', False)

        # is_synced 为 true 的条件：
        # 1. status == 'completed'
        # 2. len(results) == expected
        # 3. completion_verified == True（可选，增强检查）
        is_synced = (
            status == 'completed' and
            len(results) == expected and
            expected > 0 and
            completion_verified
        )

        progress_data['is_synced'] = is_synced
        progress_data['sync_check'] = {
            'status': status,
            'results_count': len(results),
            'expected_count': expected,
            'completion_verified': completion_verified
        }

        # 如果任务已完成，添加一个标志来通知前端停止轮询
        if progress_data.get('status') in ['completed', 'failed']:
            progress_data['should_stop_polling'] = True

        return jsonify(progress_data)
    else:
        return jsonify({'error': 'Execution ID not found'}), 404


# ====================
# SSE 实时推送端点
# ====================

@wechat_bp.route('/api/stream/progress/<execution_id>', methods=['GET'])
def stream_progress(execution_id):
    """
    SSE 实时进度推送端点
    
    客户端通过 EventSource 连接此端点，实时接收诊断进度更新
    
    事件类型:
    - connected: 连接成功
    - progress: 进度更新
    - intelligence: 情报更新
    - complete: 任务完成
    - error: 错误通知
    """
    # 生成客户端 ID
    client_id = f"{execution_id}_{uuid.uuid4().hex[:8]}"
    
    # 添加连接到管理器
    manager = get_sse_manager()
    manager.add_connection(execution_id, client_id)
    
    api_logger.info(f"[SSE] Client {client_id} connected to execution {execution_id}")
    
    # 创建 SSE 响应
    return create_sse_response(client_id)


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

            # 【串行执行策略】为确保所有AI平台请求都能成功完成，强制使用串行执行
            # 这样可以避免并发请求导致的资源竞争和超时问题
            executor = TestExecutor(max_workers=1, strategy=ExecutionStrategy.SEQUENTIAL)
            api_logger.info(f"[ExecutionStrategy] Using forced SEQUENTIAL execution with max_workers=1 for stability")

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
            from wechat_backend.models import DeepIntelligenceResult, BrandTestResult, save_brand_test_result
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
def get_task_status_api(task_id):
    """轮询任务进度与分阶段状态"""
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    # 尝试从全局存储获取任务状态
    if task_id in execution_store:
        task_status = execution_store[task_id]

        # 按照API契约返回任务状态信息
        response_data = {
            'task_id': task_id,
            'progress': task_status.get('progress', 0),
            'stage': task_status.get('stage', 'init'),  # 【任务 C：前端同步】确保返回当前的 stage 描述
            'status': task_status.get('status', 'init'),
            'results': task_status.get('results', []),
            'is_completed': task_status.get('status') == 'completed',
            'created_at': task_status.get('start_time', None)
        }

        # 返回任务状态信息
        return jsonify(response_data), 200
    else:
        return jsonify({'error': 'Task not found'}), 404


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

@wechat_bp.route('/api/dashboard/aggregate', methods=['GET'])
@require_auth_optional
@rate_limit(limit=30, window=60, per='endpoint')
@monitored_endpoint('/api/dashboard/aggregate', require_auth=False, validate_inputs=True)
def get_dashboard_aggregate():
    """
    获取 Dashboard 聚合数据 (增强版 - P0 级空缺修复)

    查询参数:
        executionId: 执行 ID (可选，如果提供则从数据库获取)
        userOpenid: 用户 OpenID (可选)

    返回:
        {
            "success": true,
            "dashboard": {
                "summary": {
                    "brandName": "品牌名称",
                    "healthScore": 75,
                    "sov": 50,
                    "avgSentiment": 0.3,
                    "totalMentions": 100,
                    "totalTests": 200
                },
                "questionCards": [...],
                "toxicSources": [...],
                "roi_metrics": {  # P0 新增
                    "exposure_roi": 3.5,
                    "sentiment_roi": 2.1,
                    "ranking_roi": 4.2,
                    "estimated_value": 50000
                },
                "impact_scores": {  # P0 新增
                    "authority_impact": 75,
                    "visibility_impact": 82,
                    "sentiment_impact": 68,
                    "overall_impact": 75
                }
            }
        }
    """
    try:
        execution_id = request.args.get('executionId')
        user_openid = request.args.get('userOpenid', 'anonymous')

        api_logger.info(f"请求 Dashboard 聚合数据：executionId={execution_id}, userOpenid={user_openid}")

        # 如果有 executionId，从数据库获取测试结果
        if execution_id:
            # 从数据库获取测试结果
            from wechat_backend.models import TestRecord
            record = TestRecord.query.filter_by(execution_id=execution_id).first()

            if record and record.results:
                # 使用已有的聚合结果
                api_logger.info(f"从数据库获取执行 ID {execution_id} 的结果")

                # 检查是否已经是 Dashboard 格式
                if 'dashboard' in record.results:
                    dashboard_data = record.results['dashboard']
                    
                    # P0 增强：添加 ROI 指标和影响力评分
                    dashboard_data = enrich_dashboard_with_roi(dashboard_data, execution_id)
                    
                    return jsonify({
                        'success': True,
                        'dashboard': dashboard_data
                    })
                else:
                    # 转换为 Dashboard 格式
                    dashboard_data = convert_to_dashboard_format(
                        record.results,
                        record.results.get('competitiveAnalysis', {}).get('brandScores', {}).keys(),
                        record.results.get('main_brand', '未知品牌')
                    )
                    
                    # P0 增强：添加 ROI 指标和影响力评分
                    dashboard_data = enrich_dashboard_with_roi(dashboard_data, execution_id)
                    
                    return jsonify({
                        'success': True,
                        'dashboard': dashboard_data
                    })

        # 如果没有 executionId 或数据库中没有，尝试从最近的测试获取
        try:
            from wechat_backend.models import TestRecord
            recent_record = TestRecord.query.filter_by(user_openid=user_openid).order_by(TestRecord.created_at.desc()).first()

            if recent_record and recent_record.results:
                api_logger.info(f"使用最近的测试结果：{recent_record.id}")

                # 转换为 Dashboard 格式
                dashboard_data = convert_to_dashboard_format(
                    recent_record.results,
                    recent_record.results.get('competitiveAnalysis', {}).get('brandScores', {}).keys(),
                    recent_record.results.get('main_brand', '未知品牌')
                )
                
                # P0 增强：添加 ROI 指标和影响力评分
                if hasattr(recent_record, 'execution_id') and recent_record.execution_id:
                    dashboard_data = enrich_dashboard_with_roi(dashboard_data, recent_record.execution_id)
                
                return jsonify({
                    'success': True,
                    'dashboard': dashboard_data
                })
        except Exception as db_error:
            api_logger.warning(f"数据库查询失败：{db_error}")

        # 如果没有历史数据，返回错误
        api_logger.warning(f"未找到 Dashboard 数据：executionId={execution_id}")
        return jsonify({
            'success': False,
            'error': '未找到测试数据，请先执行品牌测试',
            'code': 'NO_DATA'
        }), 404

    except Exception as e:
        api_logger.error(f"获取 Dashboard 聚合数据失败：{e}")
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


def enrich_dashboard_with_roi(dashboard_data: dict, execution_id: str) -> dict:
    """
    P0 级空缺修复：为 Dashboard 数据添加 ROI 指标和影响力评分
    
    Args:
        dashboard_data: 原始 Dashboard 数据
        execution_id: 执行 ID
        
    Returns:
        增强后的 Dashboard 数据
    """
    try:
        from .views_geo_analysis import ROIMetricsModel
        
        # 获取 ROI 指标
        roi_data = ROIMetricsModel.from_execution_id(execution_id)
        
        if roi_data:
            # 添加 ROI 指标
            dashboard_data['roi_metrics'] = roi_data['roi_metrics']
            dashboard_data['impact_scores'] = roi_data['impact_scores']
            dashboard_data['benchmarks'] = roi_data.get('benchmarks', {})
            
            api_logger.info(f"Dashboard enriched with ROI metrics for execution: {execution_id}")
        else:
            # 如果无法获取 ROI 数据，提供默认值
            dashboard_data['roi_metrics'] = {
                'exposure_roi': 0,
                'sentiment_roi': 0,
                'ranking_roi': 0,
                'estimated_value': 0
            }
            dashboard_data['impact_scores'] = {
                'authority_impact': 0,
                'visibility_impact': 0,
                'sentiment_impact': 0,
                'overall_impact': 0
            }
            api_logger.warning(f"Could not enrich ROI metrics for execution: {execution_id}")
            
    except Exception as e:
        api_logger.error(f"Error enriching dashboard with ROI: {e}")
        # 保持原数据，不抛出异常
        if 'roi_metrics' not in dashboard_data:
            dashboard_data['roi_metrics'] = {
                'exposure_roi': 0,
                'sentiment_roi': 0,
                'ranking_roi': 0,
                'estimated_value': 0
            }
        if 'impact_scores' not in dashboard_data:
            dashboard_data['impact_scores'] = {
                'authority_impact': 0,
                'visibility_impact': 0,
                'sentiment_impact': 0,
                'overall_impact': 0
            }
    
    return dashboard_data

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
        'domestic': [
            {'name': 'DeepSeek', 'checked': False, 'available': True},
            {'name': '豆包', 'checked': False, 'available': True},
            {'name': '元宝', 'checked': False, 'available': True},
            {'name': '通义千问', 'checked': True, 'available': True},  # Qwen now marked as available
            {'name': '文心一言', 'checked': False, 'available': True},
            {'name': 'Kimi', 'checked': True, 'available': True},
            {'name': '讯飞星火', 'checked': False, 'available': True}
        ],
        'overseas': [
            {'name': 'ChatGPT', 'checked': True, 'available': True},
            {'name': 'Claude', 'checked': True, 'available': True},
            {'name': 'Gemini', 'checked': False, 'available': True},
            {'name': 'Perplexity', 'checked': False, 'available': True},
            {'name': 'Grok', 'checked': False, 'available': True}
        ]
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


@wechat_bp.route('/action/recommendations', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
@monitored_endpoint('/action/recommendations', require_auth=False, validate_inputs=True)
def get_action_recommendations():
    """获取干预行动建议"""
    user_id = get_current_user_id()
    api_logger.info(f"Action recommendations endpoint accessed by user: {user_id}")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # 验证必需字段
    try:
        source_intelligence = data.get('source_intelligence', {})
        evidence_chain = data.get('evidence_chain', [])
        brand_name = data.get('brand_name', '未知品牌')

        if not isinstance(source_intelligence, dict):
            return jsonify({'error': 'source_intelligence must be a dictionary'}), 400

        if not isinstance(evidence_chain, list):
            return jsonify({'error': 'evidence_chain must be a list'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 创建推荐生成器实例
        generator = RecommendationGenerator()

        # 生成建议
        recommendations = generator.generate_recommendations(
            source_intelligence=source_intelligence,
            evidence_chain=evidence_chain,
            brand_name=brand_name
        )

        # 转换为JSON友好的格式
        recommendations_json = []
        for rec in recommendations:
            recommendations_json.append({
                'priority': rec.priority.value,
                'type': rec.type.value,
                'title': rec.title,
                'description': rec.description,
                'target': rec.target,
                'estimated_impact': rec.estimated_impact,
                'action_steps': rec.action_steps,
                'urgency': rec.urgency
            })

        return jsonify({
            'status': 'success',
            'recommendations': recommendations_json,
            'count': len(recommendations_json)
        })

    except Exception as e:
        api_logger.error(f"Error generating recommendations: {e}")
        return jsonify({'error': 'Failed to generate recommendations', 'details': str(e)}), 500


# 初始化巡航控制器
cruise_controller = CruiseController()


@wechat_bp.route('/cruise/config', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
@monitored_endpoint('/cruise/config', require_auth=False, validate_inputs=True)
def configure_cruise_task():
    """配置定时诊断任务"""
    user_id = get_current_user_id()
    api_logger.info(f"Cruise configuration endpoint accessed by user: {user_id}")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        # 验证必需字段
        user_openid = data.get('user_openid', user_id or 'anonymous')
        brand_name = data.get('brand_name', '')
        interval_hours = data.get('interval_hours', 24)  # 默认24小时
        ai_models = data.get('ai_models', [])
        questions = data.get('questions', [])
        job_id = data.get('job_id')

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if not ai_models or not isinstance(ai_models, list) or len(ai_models) == 0:
            return jsonify({'error': 'ai_models is required and must be a non-empty list'}), 400

        if not isinstance(interval_hours, int) or interval_hours <= 0:
            return jsonify({'error': 'interval_hours must be a positive integer'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 调度诊断任务
        scheduled_job_id = cruise_controller.schedule_diagnostic_task(
            user_openid=user_openid,
            brand_name=brand_name,
            interval_hours=interval_hours,
            ai_models=ai_models,
            questions=questions,
            job_id=job_id
        )

        return jsonify({
            'status': 'success',
            'message': 'Cruise task scheduled successfully',
            'job_id': scheduled_job_id,
            'brand_name': brand_name,
            'interval_hours': interval_hours
        })

    except Exception as e:
        api_logger.error(f"Error scheduling cruise task: {e}")
        return jsonify({'error': 'Failed to schedule cruise task', 'details': str(e)}), 500


@wechat_bp.route('/cruise/config', methods=['DELETE'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
@monitored_endpoint('/cruise/config', require_auth=False, validate_inputs=True)
def cancel_cruise_task():
    """取消定时诊断任务"""
    user_id = get_current_user_id()
    api_logger.info(f"Cruise task cancellation endpoint accessed by user: {user_id}")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    try:
        job_id = data.get('job_id')
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 取消已调度的任务
        cruise_controller.cancel_scheduled_task(job_id)

        return jsonify({
            'status': 'success',
            'message': 'Cruise task cancelled successfully',
            'job_id': job_id
        })

    except Exception as e:
        api_logger.error(f"Error cancelling cruise task: {e}")
        return jsonify({'error': 'Failed to cancel cruise task', 'details': str(e)}), 500


@wechat_bp.route('/cruise/tasks', methods=['GET'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/cruise/tasks', require_auth=False, validate_inputs=False)
def get_cruise_tasks():
    """获取所有已调度的巡航任务"""
    user_id = get_current_user_id()
    api_logger.info(f"Cruise tasks retrieval endpoint accessed by user: {user_id}")

    try:
        # 获取所有已调度的任务
        scheduled_tasks = cruise_controller.get_scheduled_tasks()

        return jsonify({
            'status': 'success',
            'tasks': scheduled_tasks,
            'count': len(scheduled_tasks)
        })

    except Exception as e:
        api_logger.error(f"Error retrieving cruise tasks: {e}")
        return jsonify({'error': 'Failed to retrieve cruise tasks', 'details': str(e)}), 500


@wechat_bp.route('/cruise/trends', methods=['GET'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/cruise/trends', require_auth=False, validate_inputs=True)
def get_cruise_trends():
    """获取趋势数据"""
    user_id = get_current_user_id()
    api_logger.info(f"Cruise trends endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取品牌名称和天数
        brand_name = request.args.get('brand_name', '')
        days = request.args.get('days', 30, type=int)

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 获取趋势数据
        trend_data = cruise_controller.get_trend_data(brand_name, days)

        return jsonify({
            'status': 'success',
            'brand_name': brand_name,
            'days': days,
            'trend_data': trend_data,
            'count': len(trend_data)
        })

    except Exception as e:
        api_logger.error(f"Error retrieving trend data: {e}")
        return jsonify({'error': 'Failed to retrieve trend data', 'details': str(e)}), 500


# 初始化市场情报服务
market_intelligence_service = MarketIntelligenceService()


@wechat_bp.route('/market/benchmark', methods=['GET'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/market/benchmark', require_auth=False, validate_inputs=True)
def get_market_benchmark():
    """获取市场基准对比数据"""
    user_id = get_current_user_id()
    api_logger.info(f"Market benchmark endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取必要参数
        brand_name = request.args.get('brand_name', '')
        category = request.args.get('category', None)  # 可选参数
        days = request.args.get('days', 30, type=int)

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400

        # 验证输入参数
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400
        if category and not sql_protector.validate_input(category):
            return jsonify({'error': 'Invalid category'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 获取市场基准数据
        benchmark_data = market_intelligence_service.get_market_benchmark_data(
            brand_name=brand_name,
            category=category,
            days=days
        )

        return jsonify({
            'status': 'success',
            'brand_name': brand_name,
            'category': category,
            'days': days,
            'benchmark_data': benchmark_data
        })

    except Exception as e:
        api_logger.error(f"Error retrieving market benchmark data: {e}")
        return jsonify({'error': 'Failed to retrieve market benchmark data', 'details': str(e)}), 500


@wechat_bp.route('/predict/forecast', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
@monitored_endpoint('/predict/forecast', require_auth=False, validate_inputs=True)
def get_prediction_forecast():
    """获取品牌认知趋势预测和风险因素"""
    user_id = get_current_user_id()
    api_logger.info(f"Prediction forecast endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取必要参数
        brand_name = request.args.get('brand_name', '')
        days = request.args.get('days', 7, type=int)  # 默认预测7天
        history_days = request.args.get('history_days', 30, type=int)  # 默认使用30天历史数据

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 30:
            return jsonify({'error': 'days must be between 1 and 30'}), 400

        if history_days <= 0 or history_days > 365:
            return jsonify({'error': 'history_days must be between 1 and 365'}), 400

        # 验证输入参数
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 获取历史趋势数据用于预测
        trend_data = cruise_controller.get_trend_data(brand_name, history_days)

        if not trend_data:
            return jsonify({
                'status': 'warning',
                'message': 'No historical data available for prediction',
                'predictions': [],
                'risk_factors': []
            })

        # 使用预测引擎进行预测
        from wechat_backend.analytics.prediction_engine import PredictionEngine
        prediction_engine = PredictionEngine()

        # 准备历史数据
        historical_data = []
        for data_point in trend_data:
            historical_entry = {
                'rank': data_point.get('rank'),
                'overall_score': data_point.get('overall_score'),
                'sentiment_score': data_point.get('sentiment_score'),
                'timestamp': data_point.get('timestamp'),
                'evidence_chain': []  # 在实际应用中，这需要从数据库获取完整的证据链数据
            }
            historical_data.append(historical_entry)

        # 获取证据链数据（简化版本，实际应用中需要从数据库获取完整证据链）
        # 这里我们使用趋势数据中的信息来模拟证据链
        evidence_chain = []
        for data_point in trend_data[-7:]:  # 使用最近7天的数据
            if data_point.get('overall_score', 100) < 60:  # 假设分数低于60表示有问题
                evidence_chain.append({
                    'negative_fragment': f"品牌认知分数偏低({data_point.get('overall_score', 0)})",
                    'associated_url': 'internal_system',
                    'source_name': 'System Alert',
                    'risk_level': 'Medium'
                })

        # 为每个历史数据点添加证据链
        for entry in historical_data:
            entry['evidence_chain'] = evidence_chain if entry['overall_score'] and entry['overall_score'] < 60 else []

        # 执行预测
        prediction_result = prediction_engine.predict_weekly_rank_with_risks(historical_data)

        return jsonify({
            'status': 'success',
            'brand_name': brand_name,
            'forecast_period': days,
            'prediction_result': prediction_result
        })

    except Exception as e:
        api_logger.error(f"Error generating prediction forecast: {e}")
        return jsonify({'error': 'Failed to generate prediction forecast', 'details': str(e)}), 500


# 初始化工作流管理器
from wechat_backend.analytics.workflow_manager import WorkflowManager
workflow_manager = WorkflowManager()

# 初始化资产智能引擎
from wechat_backend.analytics.asset_intelligence_engine import AssetIntelligenceEngine
asset_intelligence_engine = AssetIntelligenceEngine()


@wechat_bp.route('/assets/optimization', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
@monitored_endpoint('/assets/optimization', require_auth=False, validate_inputs=True)
def optimize_assets():
    """资产优化接口 - 分析官方资产与AI偏好的匹配度并提供优化建议"""
    user_id = get_current_user_id()
    api_logger.info(f"Asset optimization endpoint accessed by user: {user_id}")

    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # 验证必需字段
        required_fields = ['official_asset', 'ai_preferences']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # 提取参数
        official_asset = data['official_asset']
        ai_preferences = data['ai_preferences']  # 格式: {platform_name: [content1, content2, ...]}

        # 验证输入参数
        if not isinstance(official_asset, str) or len(official_asset.strip()) == 0:
            return jsonify({'error': 'official_asset must be a non-empty string'}), 400

        if not isinstance(ai_preferences, dict) or len(ai_preferences) == 0:
            return jsonify({'error': 'ai_preferences must be a non-empty dictionary'}), 400

        # 验证ai_preferences的结构
        for platform, contents in ai_preferences.items():
            if not isinstance(contents, list):
                return jsonify({'error': f'ai_preferences[{platform}] must be a list of strings'}), 400
            for content in contents:
                if not isinstance(content, str):
                    return jsonify({'error': f'all items in ai_preferences[{platform}] must be strings'}), 400

        # 验证输入内容的安全性
        from wechat_backend.security.input_validation import validate_safe_text
        if not validate_safe_text(official_asset, max_length=5000):
            return jsonify({'error': 'Invalid official_asset content'}), 400

        for platform, contents in ai_preferences.items():
            if not validate_safe_text(platform, max_length=100):
                return jsonify({'error': f'Invalid platform name: {platform}'}), 400
            for content in contents:
                if not validate_safe_text(content, max_length=5000):
                    return jsonify({'error': f'Invalid content in {platform}'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 执行资产智能分析
        analysis_result = asset_intelligence_engine.analyze_content_matching(
            official_asset=official_asset,
            ai_preferences=ai_preferences
        )

        return jsonify({
            'status': 'success',
            'analysis_result': analysis_result,
            'content_hit_rate': analysis_result['overall_score'],
            'optimization_suggestions': analysis_result['optimization_suggestions']
        })

    except Exception as e:
        api_logger.error(f"Error optimizing assets: {e}")
        return jsonify({'error': 'Failed to optimize assets', 'details': str(e)}), 500


# 初始化报告生成器
from wechat_backend.analytics.report_generator import ReportGenerator
report_generator = ReportGenerator()


@wechat_bp.route('/hub/summary', methods=['GET'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/hub/summary', require_auth=False, validate_inputs=True)
def get_hub_summary():
    """获取枢纽摘要数据 - 品牌GEO运营分析汇总"""
    user_id = get_current_user_id()
    api_logger.info(f"Hub summary endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取参数
        brand_name = request.args.get('brand_name', '')
        days = request.args.get('days', 7, type=int)  # 默认7天

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400

        # 验证输入参数
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 生成枢纽摘要
        summary = report_generator.get_hub_summary(brand_name, days)

        return jsonify({
            'status': 'success',
            'summary': summary
        })

    except Exception as e:
        api_logger.error(f"Error generating hub summary: {e}")
        return jsonify({'error': 'Failed to generate hub summary', 'details': str(e)}), 500


@wechat_bp.route('/reports/executive', methods=['GET'])
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
@monitored_endpoint('/reports/executive', require_auth=False, validate_inputs=True)
def get_executive_report():
    """获取高管视角报告"""
    user_id = get_current_user_id()
    api_logger.info(f"Executive report endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取参数
        brand_name = request.args.get('brand_name', '')
        days = request.args.get('days', 30, type=int)  # 默认30天

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400

        # 验证输入参数
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 生成高管报告
        summary = report_generator.generate_executive_summary(brand_name, days)

        return jsonify({
            'status': 'success',
            'report': summary
        })

    except Exception as e:
        api_logger.error(f"Error generating executive report: {e}")
        return jsonify({'error': 'Failed to generate executive report', 'details': str(e)}), 500


@wechat_bp.route('/reports/pdf', methods=['GET'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/reports/pdf', require_auth=False, validate_inputs=True)
def get_pdf_report():
    """获取PDF格式的报告"""
    user_id = get_current_user_id()
    api_logger.info(f"PDF report endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取参数
        brand_name = request.args.get('brand_name', '')
        days = request.args.get('days', 30, type=int)  # 默认30天

        if not brand_name:
            return jsonify({'error': 'brand_name is required'}), 400

        if days <= 0 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400

        # 验证输入参数
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 生成PDF报告
        pdf_data = report_generator.generate_pdf_report(brand_name, days)

        # 返回PDF文件
        from flask import Response
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=report_{brand_name}_{datetime.now().strftime("%Y%m%d")}.pdf'}
        )

    except Exception as e:
        api_logger.error(f"Error generating PDF report: {e}")
        return jsonify({'error': 'Failed to generate PDF report', 'details': str(e)}), 500


# 初始化工作流管理器
from wechat_backend.ai_adapters.workflow_manager import WorkflowManager
workflow_manager = WorkflowManager()


@wechat_bp.route('/workflow/tasks', methods=['POST'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/workflow/tasks', require_auth=False, validate_inputs=True)
def create_workflow_task():
    """创建工作流任务 - 处理负面证据并分发到指定Webhook"""
    user_id = get_current_user_id()
    api_logger.info(f"Workflow task creation endpoint accessed by user: {user_id}")

    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # 验证必需字段
        required_fields = [
            'evidence_fragment', 'associated_url', 'source_name',
            'risk_level', 'brand_name', 'intervention_script',
            'source_meta', 'webhook_url'
        ]

        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # 提取参数
        evidence_fragment = data['evidence_fragment']
        associated_url = data['associated_url']
        source_name = data['source_name']
        risk_level = data['risk_level']
        brand_name = data['brand_name']
        intervention_script = data['intervention_script']
        source_meta = data['source_meta']
        webhook_url = data['webhook_url']
        priority = data.get('priority', 'medium')  # 默认中等优先级

        # 验证输入参数
        if not sql_protector.validate_input(evidence_fragment):
            return jsonify({'error': 'Invalid evidence_fragment'}), 400
        if not sql_protector.validate_input(associated_url):
            return jsonify({'error': 'Invalid associated_url'}), 400
        if not sql_protector.validate_input(source_name):
            return jsonify({'error': 'Invalid source_name'}), 400
        if not sql_protector.validate_input(brand_name):
            return jsonify({'error': 'Invalid brand_name'}), 400
        if not sql_protector.validate_input(webhook_url):
            return jsonify({'error': 'Invalid webhook_url'}), 400

        # 验证风险等级
        valid_risk_levels = ['Low', 'Medium', 'High', 'Critical']
        if risk_level not in valid_risk_levels:
            return jsonify({'error': f'Invalid risk_level. Must be one of: {valid_risk_levels}'}), 400

        # 验证优先级
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority not in valid_priorities:
            return jsonify({'error': f'Invalid priority. Must be one of: {valid_priorities}'}), 400

        # 验证webhook_url格式
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        if not url_pattern.match(webhook_url):
            return jsonify({'error': 'Invalid webhook_url format'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400

    try:
        # 分发任务
        from wechat_backend.ai_adapters.workflow_manager import TaskPriority
        priority_enum = TaskPriority(priority)

        task_id = workflow_manager.dispatch_task(
            evidence_fragment=evidence_fragment,
            associated_url=associated_url,
            source_name=source_name,
            risk_level=risk_level,
            brand_name=brand_name,
            intervention_script=intervention_script,
            source_meta=source_meta,
            webhook_url=webhook_url,
            priority=priority_enum
        )

        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'message': 'Workflow task created and dispatched successfully',
            'webhook_url': webhook_url
        })

    except Exception as e:
        api_logger.error(f"Error creating workflow task: {e}")
        return jsonify({'error': 'Failed to create workflow task', 'details': str(e)}), 500


@wechat_bp.route('/workflow/tasks/<task_id>', methods=['GET'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
@monitored_endpoint('/workflow/tasks/task_id', require_auth=False, validate_inputs=False)
def get_workflow_task_status(task_id):
    """获取工作流任务状态"""
    user_id = get_current_user_id()
    api_logger.info(f"Workflow task status endpoint accessed by user: {user_id}, task_id: {task_id}")

    try:
        # 获取任务状态
        status_info = workflow_manager.get_task_status(task_id)

        if not status_info:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify({
            'status': 'success',
            'task_info': status_info
        })

    except Exception as e:
        api_logger.error(f"Error getting workflow task status: {e}")
        return jsonify({'error': 'Failed to get task status', 'details': str(e)}), 500



@wechat_bp.route('/api/send-verification-code', methods=['POST'])
@rate_limit(limit=5, window=60, per='ip')
def send_verification_code():
    """Send verification code to user"""
    api_logger.info("Send verification code endpoint accessed")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    phone = data.get('phone')
    if not phone:
        return jsonify({'error': 'Phone number is required'}), 400

    # Validate phone number format
    import re
    phone_pattern = r'^1[3-9]\d{9}$'
    if not re.match(phone_pattern, phone):
        return jsonify({'error': 'Invalid phone number format'}), 400

    # Generate 6-digit verification code
    import random
    verification_code = f"{random.randint(100000, 999999)}"

    # Save verification code (in-memory, should use Redis in production)
    from wechat_backend.database import save_verification_code
    save_verification_code(phone, verification_code)

    # In production, send SMS via SMS service (Aliyun, Tencent Cloud, etc.)
    # For development, log the code for testing
    api_logger.info(f"Verification code sent to {phone} (mock: {verification_code})")
    
    # For testing purposes, return the code in the response (remove in production!)
    return jsonify({
        'status': 'success',
        'message': 'Verification code sent successfully',
        'phone': phone,
        # REMOVE THIS IN PRODUCTION - for testing only!
        'mock_code': verification_code
    })


@wechat_bp.route('/api/register', methods=['POST'])
@rate_limit(limit=5, window=60, per='ip')
def register_user():
    """Register new user with phone and password"""
    api_logger.info("User registration endpoint accessed")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    phone = data.get('phone')
    verification_code = data.get('verificationCode') or data.get('verification_code')
    password = data.get('password')

    if not phone or not verification_code or not password:
        return jsonify({'error': 'Phone, verification code, and password are required'}), 400

    # Validate phone number format
    import re
    phone_pattern = r'^1[3-9]\d{9}$'
    if not re.match(phone_pattern, phone):
        return jsonify({'error': 'Invalid phone number format'}), 400

    # Validate password strength (at least 6 characters)
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400

    # Verify the verification code
    from wechat_backend.database import verify_code, create_user_with_phone
    if not verify_code(phone, verification_code):
        return jsonify({'error': 'Invalid or expired verification code'}), 400

    # Check if phone already registered
    from wechat_backend.database import get_user_by_phone
    existing_user = get_user_by_phone(phone)
    if existing_user:
        return jsonify({'error': 'Phone number already registered'}), 409

    # Hash password using bcrypt
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create user
    user_id = create_user_with_phone(phone, password_hash)
    if user_id == -1:
        return jsonify({'error': 'Failed to create user'}), 500

    # Generate JWT tokens
    from wechat_backend.security.auth import jwt_manager
    access_token = jwt_manager.generate_token(str(user_id), expires_delta=timedelta(hours=24), token_type='access')
    refresh_token = jwt_manager.generate_token(str(user_id), expires_delta=timedelta(days=7), token_type='refresh')

    # Save refresh token
    from wechat_backend.database import save_refresh_token
    save_refresh_token(str(user_id), refresh_token)

    api_logger.info(f"User registered successfully: {phone}, user_id: {user_id}")

    return jsonify({
        'status': 'success',
        'message': 'User registered successfully',
        'user_id': user_id,
        'token': access_token,
        'refresh_token': refresh_token,
        'expires_in': 86400,  # 24 hours
        'refresh_expires_in': 604800  # 7 days
    })


@wechat_bp.route('/api/login/phone', methods=['POST'])
@rate_limit(limit=10, window=60, per='ip')
def login_by_phone():
    """Login with phone and password"""
    api_logger.info("Phone login endpoint accessed")

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    phone = data.get('phone')
    password = data.get('password')

    if not phone or not password:
        return jsonify({'error': 'Phone and password are required'}), 400

    # Get user by phone
    from wechat_backend.database import get_user_by_phone
    user = get_user_by_phone(phone)

    if not user:
        api_logger.warning(f"Login failed: user not found for {phone}")
        return jsonify({'error': 'Invalid phone or password'}), 401

    # Verify password
    import bcrypt
    try:
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            api_logger.warning(f"Login failed: incorrect password for {phone}")
            return jsonify({'error': 'Invalid phone or password'}), 401
    except Exception as e:
        api_logger.error(f"Password verification error: {e}")
        return jsonify({'error': 'Login failed'}), 500

    # Generate JWT tokens
    from wechat_backend.security.auth import jwt_manager
    access_token = jwt_manager.generate_token(str(user['id']), expires_delta=timedelta(hours=24), token_type='access')
    refresh_token = jwt_manager.generate_token(str(user['id']), expires_delta=timedelta(days=7), token_type='refresh')

    # Save refresh token
    from wechat_backend.database import save_refresh_token
    save_refresh_token(str(user['id']), refresh_token)

    api_logger.info(f"User logged in successfully: {phone}, user_id: {user['id']}")

    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'user_id': user['id'],
        'token': access_token,
        'refresh_token': refresh_token,
        'expires_in': 86400,  # 24 hours
        'refresh_expires_in': 604800,  # 7 days
        'profile': {
            'phone': user['phone'],
            'nickname': user['nickname'],
            'avatar_url': user['avatar_url']
        }
    })


@wechat_bp.route('/api/validate-token', methods=['POST'])
@rate_limit(limit=30, window=60, per='ip')
def validate_token():
    """Validate access token"""
    api_logger.info("Token validation endpoint accessed")
    
    data = request.get_json()
    if not data:
        return jsonify({'status': 'invalid', 'error': 'No JSON data provided'}), 400
    
    token = data.get('token')
    if not token:
        # Try to get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if not token:
        return jsonify({'status': 'invalid', 'error': 'Token not provided'}), 400
    
    try:
        from wechat_backend.security.auth import jwt_manager
        if not jwt_manager:
            return jsonify({'status': 'invalid', 'error': 'JWT service unavailable'}), 500
        
        # Decode and validate token (verify it's an access token)
        payload = jwt_manager.decode_token(token, verify_type='access')
        
        return jsonify({
            'status': 'valid',
            'user_id': payload.get('user_id'),
            'expires_at': payload.get('exp')
        })
        
    except Exception as e:
        api_logger.warning(f"Token validation failed: {e}")
        return jsonify({'status': 'invalid', 'error': str(e)}), 401


@wechat_bp.route('/api/refresh-token', methods=['POST'])
@rate_limit(limit=10, window=60, per='ip')
def refresh_token():
    """Refresh access token using refresh token"""
    api_logger.info("Token refresh endpoint accessed")
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    refresh_token_str = data.get('refresh_token')
    
    if not refresh_token_str:
        # Try to get refresh token from cookie or header
        refresh_token_str = request.headers.get('X-Refresh-Token')
    
    if not refresh_token_str:
        return jsonify({'error': 'Refresh token is required'}), 400
    
    # Verify refresh token
    from wechat_backend.database import verify_refresh_token
    user_id = verify_refresh_token(refresh_token_str)
    
    if not user_id:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401
    
    try:
        from wechat_backend.security.auth import jwt_manager
        if not jwt_manager:
            return jsonify({'error': 'JWT service unavailable'}), 500
        
        # Generate new access token
        new_access_token = jwt_manager.generate_token(
            user_id,
            expires_delta=timedelta(hours=24),
            token_type='access'
        )
        
        # Generate new refresh token (rotate refresh tokens for security)
        new_refresh_token = jwt_manager.generate_token(
            user_id,
            expires_delta=timedelta(days=7),
            token_type='refresh'
        )
        
        # Save new refresh token
        from wechat_backend.database import save_refresh_token
        save_refresh_token(user_id, new_refresh_token)
        
        # Revoke old refresh token (token rotation)
        from wechat_backend.database import revoke_refresh_token
        revoke_refresh_token(refresh_token_str)
        
        api_logger.info(f"Token refreshed for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'token': new_access_token,
            'refresh_token': new_refresh_token,
            'expires_in': 86400,  # 24 hours
            'token_type': 'Bearer'
        })
        
    except Exception as e:
        api_logger.error(f"Token refresh failed: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500


@wechat_bp.route('/api/logout', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='ip')
def logout():
    """Logout user (revoke refresh tokens)"""
    api_logger.info("Logout endpoint accessed")
    
    data = request.get_json() or {}
    user_id = get_current_user_id()
    
    # Option 1: Logout from current device only
    refresh_token_str = data.get('refresh_token') or request.headers.get('X-Refresh-Token')
    if refresh_token_str:
        from wechat_backend.database import revoke_refresh_token
        revoke_refresh_token(refresh_token_str)
    
    # Option 2: Logout from all devices (if requested)
    if data.get('all_devices', False) and user_id:
        from wechat_backend.database import revoke_all_user_tokens
        revoke_all_user_tokens(user_id)
        api_logger.info(f"All tokens revoked for user {user_id}")
    else:
        api_logger.info(f"Token revoked for user {user_id or 'anonymous'}")
    
    return jsonify({
        'status': 'success',
        'message': 'Logout successful'
    })


@wechat_bp.route('/api/user/profile', methods=['GET'])
@require_auth
@rate_limit(limit=20, window=60, per='ip')
def get_user_profile():
    """Get user profile information"""
    user_id = get_current_user_id()
    api_logger.info(f"User profile endpoint accessed by user: {user_id}")
    
    # Convert user_id to int if it's a string
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        api_logger.warning(f"Invalid user_id format: {user_id}")
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Fetch user profile from database
    from wechat_backend.database import get_user_by_id
    user = get_user_by_id(user_id_int)
    
    if not user:
        api_logger.warning(f"User not found: {user_id}")
        return jsonify({'error': 'User not found'}), 404
    
    # Mask phone number for privacy
    phone_masked = '***'
    if user.get('phone'):
        phone = user['phone']
        if len(phone) >= 7:
            phone_masked = phone[:3] + '****' + phone[-4:]
    
    api_logger.info(f"User profile retrieved: {user_id}")
    
    return jsonify({
        'status': 'success',
        'profile': {
            'user_id': user['id'],
            'phone': phone_masked,
            'nickname': user.get('nickname') or '未设置昵称',
            'avatar_url': user.get('avatar_url') or '',
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at')
        }
    })


@wechat_bp.route('/api/user/profile', methods=['PUT'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def put_user_profile():
    """Update user profile information (PUT method)"""
    return update_user_profile_data()


@wechat_bp.route('/api/user/update', methods=['POST', 'PUT'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def update_user_profile():
    """Update user profile information"""
    return update_user_profile_data()


def update_user_profile_data():
    """Helper function to update user profile"""
    user_id = get_current_user_id()
    api_logger.info(f"Update user profile endpoint accessed by user: {user_id}")
    
    # Convert user_id to int if it's a string
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        api_logger.warning(f"Invalid user_id format: {user_id}")
        return jsonify({'error': 'Invalid user ID'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    # Update user profile in database
    from wechat_backend.database import update_user_profile
    success = update_user_profile(user_id_int, data)
    
    if success:
        api_logger.info(f"User profile updated: {user_id}")
        
        # Fetch updated profile
        from wechat_backend.database import get_user_by_id
        user = get_user_by_id(user_id_int)
        
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully',
            'profile': {
                'user_id': user['id'],
                'nickname': user.get('nickname'),
                'avatar_url': user.get('avatar_url')
            }
        })
    else:
        api_logger.error(f"Failed to update user profile: {user_id}")
        return jsonify({'error': 'Failed to update profile'}), 500


@wechat_bp.route('/api/sync-data', methods=['POST'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def sync_data():
    """
    Sync user data (incremental sync)
    
    Request body:
    - last_sync_timestamp: Last sync timestamp (optional, for incremental sync)
    - local_results: Local results to upload (optional)
    
    Response:
    - cloud_results: Results from cloud
    - uploaded_count: Number of results uploaded
    - last_sync_timestamp: Timestamp for next sync
    """
    user_id = get_current_user_id()
    api_logger.info(f"Data sync endpoint accessed by user: {user_id}")
    
    data = request.get_json() or {}
    last_sync_timestamp = data.get('last_sync_timestamp') or data.get('lastSyncTimestamp')
    local_results = data.get('local_results') or data.get('localResults', [])
    
    try:
        # Convert user_id to int
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Initialize sync database if needed
    from wechat_backend.database import init_sync_db, save_user_data, get_user_data
    init_sync_db()
    
    # 1. Save local results to cloud
    uploaded_count = 0
    if local_results and len(local_results) > 0:
        for result in local_results:
            result_id = save_user_data(user_id_int, result)
            if result_id:
                uploaded_count += 1
    
    api_logger.info(f"Uploaded {uploaded_count} results for user {user_id}")
    
    # 2. Get cloud results (incremental)
    cloud_results = get_user_data(user_id_int, last_sync_timestamp)
    
    # 3. Get current timestamp for next sync
    from datetime import datetime
    current_timestamp = datetime.now().isoformat()
    
    api_logger.info(f"Sync completed for user {user_id}: {len(cloud_results)} cloud results, {uploaded_count} uploaded")
    
    return jsonify({
        'status': 'success',
        'message': 'Data synced successfully',
        'cloud_results': cloud_results,
        'uploaded_count': uploaded_count,
        'last_sync_timestamp': current_timestamp,
        'has_more': False  # For pagination support in future
    })


@wechat_bp.route('/api/download-data', methods=['POST'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def download_data():
    """
    Download user data from cloud (incremental download)
    
    Request body:
    - last_sync_timestamp: Last sync timestamp (optional, for incremental sync)
    
    Response:
    - cloud_results: Results from cloud
    - last_sync_timestamp: Timestamp for next sync
    """
    user_id = get_current_user_id()
    api_logger.info(f"Data download endpoint accessed by user: {user_id}")
    
    data = request.get_json() or {}
    last_sync_timestamp = data.get('last_sync_timestamp') or data.get('lastSyncTimestamp')
    
    try:
        # Convert user_id to int
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Initialize sync database if needed
    from wechat_backend.database import init_sync_db, get_user_data
    init_sync_db()
    
    # Get cloud results (incremental)
    cloud_results = get_user_data(user_id_int, last_sync_timestamp)
    
    # Get current timestamp for next sync
    from datetime import datetime
    current_timestamp = datetime.now().isoformat()
    
    api_logger.info(f"Download completed for user {user_id}: {len(cloud_results)} results")
    
    return jsonify({
        'status': 'success',
        'message': 'Data downloaded successfully',
        'cloud_results': cloud_results,
        'last_sync_timestamp': current_timestamp,
        'has_more': False
    })


@wechat_bp.route('/api/upload-result', methods=['POST'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def upload_result():
    """
    Upload individual test result to cloud
    
    Request body:
    - result: Test result data
      - result_id: Unique result ID
      - brand_name: Brand name
      - ai_models_used: List of AI models used
      - questions_used: List of questions used
      - overall_score: Overall score
      - results_summary: Summary of results
      - detailed_results: Full detailed results
    """
    user_id = get_current_user_id()
    api_logger.info(f"Upload result endpoint accessed by user: {user_id}")
    
    data = request.get_json() or {}
    result = data.get('result')
    
    if not result:
        return jsonify({'error': 'Result data is required'}), 400
    
    try:
        # Convert user_id to int
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Initialize sync database if needed
    from wechat_backend.database import init_sync_db, save_user_data
    init_sync_db()
    
    # Save result to cloud
    result_id = save_user_data(user_id_int, result)
    
    if result_id:
        api_logger.info(f"Result {result_id} uploaded for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Result uploaded successfully',
            'result_id': result_id,
            'timestamp': datetime.now().isoformat()
        })
    else:
        api_logger.error(f"Failed to upload result for user {user_id}")
        return jsonify({'error': 'Failed to upload result'}), 500


@wechat_bp.route('/api/delete-result', methods=['POST'])
@require_auth
@rate_limit(limit=10, window=60, per='ip')
def delete_result():
    """
    Delete individual result from cloud (soft delete)
    
    Request body:
    - result_id: Result ID to delete
    """
    user_id = get_current_user_id()
    api_logger.info(f"Delete result endpoint accessed by user: {user_id}")
    
    data = request.get_json() or {}
    result_id = data.get('result_id') or data.get('id')
    
    if not result_id:
        return jsonify({'error': 'Result ID is required'}), 400
    
    try:
        # Convert user_id to int
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Initialize sync database if needed
    from wechat_backend.database import init_sync_db, delete_user_data
    init_sync_db()
    
    # Delete result from cloud
    success = delete_user_data(user_id_int, result_id)
    
    if success:
        api_logger.info(f"Result {result_id} deleted for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Result deleted successfully',
            'deleted_id': result_id,
            'timestamp': datetime.now().isoformat()
        })
    else:
        api_logger.warning(f"Result {result_id} not found for user {user_id}")
        return jsonify({'error': 'Result not found'}), 404


@wechat_bp.route('/api/competitive-analysis', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='ip')
def competitive_analysis():
    """Perform competitive analysis (duplicate of action/recommendations for frontend compatibility)"""
    user_id = get_current_user_id()
    api_logger.info(f"Competitive analysis endpoint accessed by user: {user_id}")

    data = request.get_json() or {}

    # This is a duplicate of /action/recommendations to satisfy frontend expectations
    # In a real implementation, this might have different logic
    source_intelligence = data.get('source_intelligence', {})
    evidence_chain = data.get('evidence_chain', [])
    brand_name = data.get('brand_name', '未知品牌')

    try:
        # Use the same logic as action/recommendations but with different endpoint
        from wechat_backend.recommendation_generator import RecommendationGenerator
        generator = RecommendationGenerator()

        recommendations = generator.generate_recommendations(
            source_intelligence=source_intelligence,
            evidence_chain=evidence_chain,
            brand_name=brand_name
        )

        # Convert to JSON-friendly format
        recommendations_json = []
        for rec in recommendations:
            recommendations_json.append({
                'priority': rec.priority.value,
                'type': rec.type.value,
                'title': rec.title,
                'description': rec.description,
                'target': rec.target,
                'estimated_impact': rec.estimated_impact,
                'action_steps': rec.action_steps,
                'urgency': rec.urgency
            })

        return jsonify({
            'status': 'success',
            'recommendations': recommendations_json,
            'count': len(recommendations_json),
            'brand_name': brand_name
        })

    except ImportError:
        # If RecommendationGenerator is not available, return a mock response
        api_logger.warning("RecommendationGenerator not available, returning mock data")
        return jsonify({
            'status': 'success',
            'recommendations': [],
            'count': 0,
            'brand_name': brand_name,
            'message': 'Mock response - RecommendationGenerator not available'
        })
    except Exception as e:
        api_logger.error(f"Error generating competitive analysis: {e}")
        return jsonify({'error': 'Failed to generate competitive analysis', 'details': str(e)}), 500