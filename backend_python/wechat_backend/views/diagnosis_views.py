"""
诊断相关视图模块
包含品牌诊断、测试执行、进度查询等路由

注意：本模块使用 views/__init__.py 中定义的 wechat_bp 蓝图
"""
from flask import request, jsonify, g
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

from legacy_config import Config
from wechat_backend.database import save_test_record, get_user_test_history, get_test_record_by_id
from wechat_backend.models import TaskStatus, TaskStage, get_task_status, save_task_status, get_deep_intelligence_result, save_deep_intelligence_result, update_task_stage
from wechat_backend.realtime_analyzer import get_analyzer
from wechat_backend.incremental_aggregator import get_aggregator
from wechat_backend.logging_config import api_logger, wechat_logger, db_logger
from wechat_backend.ai_adapters.base_adapter import AIPlatformType, AIClient, AIResponse, GEO_PROMPT_TEMPLATE, parse_geo_json
from wechat_backend.ai_adapters.base_adapter import validate_model_region_consistency

# P0-004 新增：异常处理
from wechat_backend.exceptions import (
    ValidationError,
    AIConfigError,
    AIPlatformError,
    TaskExecutionError,
    TaskTimeoutError
)
from wechat_backend.error_handler import handle_api_exceptions

# 差距 1 修复：导入认证装饰器
from wechat_backend.security.auth_enhanced import require_strict_auth, log_audit_access
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

# P0-010 新增：在 perform_brand_test 函数上添加 @handle_api_exceptions 装饰器

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

# Timeout management (P1-T2: 全局超时保护)
from wechat_backend.v2.services.timeout_service import TimeoutManager

# 从主模块导入蓝图（修复 P0-3: 确保路由注册到正确的蓝图）
from . import wechat_bp

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

# 诊断相关辅助函数
@wechat_bp.route('/api/perform-brand-test', methods=['POST', 'OPTIONS'])
@handle_api_exceptions  # P0-010 新增：统一异常处理
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

        # P0- 新增：验证所选模型是否来自同一区域（国内或海外）
        model_names = [model["name"] if isinstance(model, dict) else model for model in selected_models]
        normalized_model_names = [AIAdapterFactory.get_normalized_model_name(name) for name in model_names]

        is_valid, error_msg = validate_model_region_consistency(normalized_model_names)
        if not is_valid:
            api_logger.warning(f"Model region consistency check failed: {error_msg}")
            return jsonify({
                "status": "error",
                "error": error_msg,
                "code": 400
            }), 400

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

    # 【P1-T2 新增】启动全局超时计时器（10 分钟）
    timeout_manager = TimeoutManager()
    
    def on_timeout(eid: str):
        """超时回调：记录日志并标记任务超时"""
        api_logger.error(
            "global_timeout_triggered",
            extra={
                'event': 'global_timeout_triggered',
                'execution_id': eid,
                'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
            }
        )
        # 更新内存状态
        if eid in execution_store:
            execution_store[eid].update({
                'status': 'timeout',
                'stage': 'timeout',
                'progress': 100,
                'is_completed': True,
                'should_stop_polling': True,
                'error': f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）'
            })
        # 尝试更新数据库状态
        try:
            from wechat_backend.state_manager import get_state_manager
            state_manager = get_state_manager(execution_store)
            state_manager.update_state(
                execution_id=eid,
                status='timeout',
                stage='timeout',
                progress=100,
                is_completed=True,
                error_message=f'诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）',
                write_to_db=True,
                user_id=user_id or "anonymous",
                brand_name=main_brand,
                competitor_brands=competitor_brands if 'competitor_brands' in locals() else [],
                selected_models=selected_models,
                custom_questions=raw_questions if 'raw_questions' in locals() else []
            )
        except Exception as timeout_db_err:
            api_logger.error(f"[超时处理] 数据库状态更新失败：{timeout_db_err}")

    # 启动 10 分钟全局超时计时器
    timeout_manager.start_timer(
        execution_id=execution_id,
        on_timeout=on_timeout,
        timeout_seconds=TimeoutManager.MAX_EXECUTION_TIME
    )
    api_logger.info(
        "global_timeout_timer_started",
        extra={
            'event': 'global_timeout_timer_started',
            'execution_id': execution_id,
            'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
        }
    )


    # 【P0 关键修复】立即创建数据库初始记录，避免前端轮询时数据库无记录
    report_id = None
    try:
        service = get_report_service()
        config = {
            'brand_name': main_brand,
            'competitor_brands': competitor_brands if 'competitor_brands' in locals() else [],
            'selected_models': selected_models,
            'custom_questions': raw_questions if 'raw_questions' in locals() else []
        }
        report_id = service.create_report(execution_id, user_id or 'anonymous', config)
        service.report_repo.update_status(
            execution_id=execution_id,
            status='initializing',
            progress=0,
            stage='init',
            is_completed=False
        )
        api_logger.info(f"[P0 修复] ✅ 初始数据库记录已创建：{execution_id}, report_id={report_id}")
    except Exception as db_init_err:
        api_logger.error(f"[P0 修复] ⚠️ 创建初始记录失败：{db_init_err}")    # 先设置一个初始状态，稍后再更新总数
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
                        execution_store[execution_id].update({
                            'status': 'failed',
                            'stage': 'failed',  # 【修复 P0-002】同步 stage 与 status
                            'error': f"Invalid questions: {'; '.join(validation_result['errors'])}"
                        })
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

                # 【P0 修复 - 架构师决策】使用统一状态管理器
                # 原则：只有一个地方负责更新数据库状态
                # 流程：1.获取结果 → 2.保存结果明细 → 3.统一更新状态 → 4.发送 SSE 通知

                try:
                    from wechat_backend.repositories import save_report_snapshot
                    from wechat_backend.diagnosis_report_repository import save_diagnosis_report
                    from wechat_backend.diagnosis_report_service import get_report_service
                    from wechat_backend.state_manager import get_state_manager

                    # ==================== 步骤 1: 获取结果明细 ====================
                    results = result.get('results', [])
                    api_logger.info(f"[状态同步 -1/4] execution_id={execution_id}, 结果数={len(results)}")

                    # 如果 result 中没有结果，尝试从 execution_store 获取
                    if not results and execution_id in execution_store:
                        fallback_results = execution_store[execution_id].get('results', [])
                        if fallback_results:
                            results = fallback_results
                            api_logger.info(f"[状态同步 -1/4] 从 execution_store 恢复 {len(results)} 个结果")

                    # ==================== 步骤 2: 保存结果明细 ====================
                    try:
                        service = get_report_service()

                        # 创建/获取报告
                        config = {
                            'brand_name': main_brand,
                            'competitor_brands': competitor_brands if 'competitor_brands' in locals() else [],
                            'selected_models': selected_models,
                            'custom_questions': raw_questions if 'raw_questions' in locals() else []
                        }
                        report_id = service.create_report(execution_id, user_id or 'anonymous', config)

                        # 添加结果明细
                        if results:
                            service.add_results_batch(report_id, execution_id, results)
                            api_logger.info(f"[状态同步 -2/4] ✅ 结果明细已保存：{execution_id}, 数量：{len(results)}")
                            
                            # 【P0 关键修复】验证结果数量是否匹配
                            from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
                            result_repo = DiagnosisResultRepository()
                            saved_results = result_repo.get_by_execution_id(execution_id)
                            
                            expected_count = len(results)
                            actual_count = len(saved_results)
                            
                            if actual_count != expected_count:
                                api_logger.error(
                                    f"[状态同步 -2/4] ⚠️ 结果数量不匹配：{execution_id}, "
                                    f"期望={expected_count}, 实际={actual_count}"
                                )
                        else:
                            api_logger.error(f"[状态同步 -2/4] ❌ 无结果明细可保存：{execution_id}")

                    except Exception as storage_err:
                        api_logger.error(f"[状态同步 -2/4] ⚠️ 存储层保存失败：{storage_err}")

                    # ==================== 步骤 3: 统一更新状态 ====================
                    # 关键：使用状态管理器，确保内存和数据库原子性更新
                    state_manager = get_state_manager(execution_store)
                    state_manager.complete_execution(
                        execution_id=execution_id,
                        user_id=user_id or "anonymous",
                        brand_name=main_brand,
                        competitor_brands=competitor_brands,
                        selected_models=selected_models,
                        custom_questions=raw_questions
                    )
                    api_logger.info(f"[状态同步 -3/4] ✅ 状态已统一更新：{execution_id}")

                    # ==================== 步骤 4: 保存快照并发送 SSE 通知 ====================
                    # 构建完整报告数据并保存快照
                    # 防御性编程：安全获取嵌套字典值，避免 None.get() 错误
                    quality_score = result.get('quality_score') or {}
                    brand_analysis = result.get('brand_analysis') or {}
                    
                    report_data = {
                        "reportId": execution_id,
                        "userId": user_id or "anonymous",
                        "brandName": main_brand,
                        "competitorBrands": competitor_brands,
                        "generateTime": datetime.now().isoformat(),
                        "reportVersion": "v2.0",
                        "requestParams": {
                            "selectedModels": selected_models,
                            "customQuestions": raw_questions,
                            "userLevel": user_level.value
                        },
                        "reportData": {
                            "overallScore": quality_score.get('overall_score') if quality_score else None,
                            "overallStatus": "completed",
                            "dimensions": results,
                            "aggregated": result.get('aggregated', []),
                            "qualityScore": quality_score,
                            # 【P0 关键修复】添加品牌分析数据
                            "brandAnalysis": brand_analysis,
                            "userBrandAnalysis": brand_analysis.get('user_brand_analysis') if brand_analysis else None,
                            "competitorAnalysis": brand_analysis.get('competitor_analysis', []) if brand_analysis else [],
                            "comparison": brand_analysis.get('comparison') if brand_analysis else None,
                            "top3Brands": brand_analysis.get('top3_brands', []) if brand_analysis else []
                        },
                        "executionInfo": {
                            "formula": result.get('formula'),
                            "totalTasks": result.get('total_tasks'),
                            "completedTasks": result.get('completed_tasks')
                        }
                    }

                    # 保存快照到 report_snapshots 表
                    save_report_snapshot(
                        execution_id=execution_id,
                        user_id=user_id or "anonymous",
                        report_data=report_data,
                        report_version="v2.0"
                    )
                    api_logger.info(f"[状态同步 -4/4] ✅ 报告快照已保存：{execution_id}")

                    # 【关键修复】发送 SSE 完成通知，立即告知前端诊断已完成
                    # 注意：SSE 服务暂未实现，使用日志记录替代
                    try:
                        from wechat_backend.services.sse_service import get_sse_service
                        sse_service = get_sse_service()
                        sse_service.send_event(
                            execution_id=execution_id,
                            event_type='complete',
                            data={
                                'progress': 100,
                                'stage': 'completed',
                                'status_text': '诊断完成',
                                'results_count': len(results),
                                'total_tasks': result.get('total_tasks', 0)
                            }
                        )
                        api_logger.info(f"[SSE] ✅ 完成通知已发送：{execution_id}")
                    except Exception as sse_err:
                        api_logger.debug(f"[SSE] ⚠️ 通知发送失败：{sse_err}")

                    # 【P1-T2 新增】任务完成，取消超时计时器
                    try:
                        timeout_manager.cancel_timer(execution_id)
                        api_logger.info(f"[超时管理] ✅ 计时器已取消：{execution_id}")
                    except Exception as timer_err:
                        api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")

                except Exception as snapshot_err:
                    # 快照保存失败不影响主流程，仅记录错误
                    api_logger.error(f"[M004] ⚠️ 报告快照保存失败：{execution_id}, 错误：{snapshot_err}")
            else:
                error_message = result.get('error', '执行失败')
                api_logger.error(f"NxM execution failed for '{execution_id}': {error_message}")

                # 【P0 关键修复】步骤 1: 立即更新内存状态，确保前端轮询能收到失败信号
                if execution_id in execution_store:
                    execution_store[execution_id].update({
                        'status': 'failed',
                        'stage': 'failed',
                        'progress': 100,
                        'is_completed': True,
                        'should_stop_polling': True,  # 强制停止轮询
                        'error': error_message
                    })
                    api_logger.info(f"[状态同步 - 失败处理 1/3] ✅ 内存状态已更新：{execution_id}")

                # 步骤 2: 使用状态管理器统一更新数据库
                try:
                    from wechat_backend.state_manager import get_state_manager
                    state_manager = get_state_manager(execution_store)
                    state_manager.update_state(
                        execution_id=execution_id,
                        status='failed',
                        stage='failed',
                        progress=100,
                        is_completed=True,
                        error_message=error_message,
                        write_to_db=True,
                        user_id=user_id or "anonymous",
                        brand_name=main_brand,
                        competitor_brands=competitor_brands,
                        selected_models=selected_models,
                        custom_questions=raw_questions
                    )
                    api_logger.info(f"[状态同步 - 失败处理 2/3] ✅ 数据库状态已更新：{execution_id}")
                except Exception as state_err:
                    api_logger.error(f"[状态同步 - 失败处理 2/3] ⚠️ 状态管理器更新失败：{state_err}")

                # 【P0-前端同步修复】同时更新 task_statuses 表，确保前端轮询能获取到失败状态
                try:
                    from wechat_backend.repositories.task_status_repository import save_task_status
                    save_task_status(
                        task_id=execution_id,
                        stage='failed',
                        progress=100,
                        status_text='诊断失败：' + (error_message or '未知错误'),
                        is_completed=True
                    )
                    api_logger.info(f"[状态同步 - 失败处理 2.5/3] ✅ task_statuses 表已同步更新：{execution_id}")
                except Exception as task_err:
                    api_logger.error(f"[状态同步 - 失败处理 2.5/3] ⚠️ task_statuses 表更新失败：{execution_id}, 错误：{task_err}")

                # M004 改造：即使失败也保存错误报告
                try:
                    from wechat_backend.repositories import save_report_snapshot
                    from wechat_backend.diagnosis_report_repository import save_diagnosis_report

                    error_report = {
                        "reportId": execution_id,
                        "userId": user_id or "anonymous",
                        "brandName": main_brand,
                        "generateTime": datetime.now().isoformat(),
                        "reportVersion": "v2.0",
                        "status": "failed",
                        "error": error_message,
                        "reportData": {
                            "overallStatus": "failed",
                            "dimensions": result.get('results', [])
                        }
                    }

                    # 保存错误报告快照
                    save_report_snapshot(
                        execution_id=execution_id,
                        user_id=user_id or "anonymous",
                        report_data=error_report,
                        report_version="v2.0"
                    )

                    # 【关键修复】同时更新 diagnosis_reports 表，确保前端能够查询到
                    save_diagnosis_report(
                        execution_id=execution_id,
                        user_id=user_id or "anonymous",
                        brand_name=main_brand,
                        competitor_brands=competitor_brands,
                        selected_models=selected_models,
                        custom_questions=raw_questions,
                        status="failed",
                        progress=100,  # 进度设为 100%，因为执行已完成（虽然是失败）
                        stage="failed",
                        is_completed=True
                    )

                    api_logger.info(f"[状态同步 - 失败处理 3/3] ✅ 错误报告已保存：{execution_id}")

                except Exception as snapshot_err:
                    api_logger.error(f"[M004] ⚠️ 错误报告保存失败：{execution_id}, 错误：{snapshot_err}")

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_message = f"{str(e)}"
            api_logger.error(f"Async test execution failed for execution_id {execution_id}: {error_message}\nTraceback: {error_traceback}")
            
            # 【P0 关键修复】异常时也要更新内存状态和数据库状态
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'status': 'failed',
                    'stage': 'failed',
                    'progress': 100,
                    'is_completed': True,
                    'should_stop_polling': True,  # 强制停止轮询
                    'error': f"{error_message}\nTraceback: {error_traceback}"
                })
                api_logger.info(f"[异常处理] ✅ 内存状态已更新：{execution_id}")
            
            # 尝试更新数据库
            try:
                from wechat_backend.state_manager import get_state_manager
                state_manager = get_state_manager(execution_store)
                state_manager.update_state(
                    execution_id=execution_id,
                    status='failed',
                    stage='failed',
                    progress=100,
                    is_completed=True,
                    error_message=error_message,
                    write_to_db=True,
                    user_id=user_id or "anonymous",
                    brand_name=main_brand,
                    competitor_brands=competitor_brands,
                    selected_models=selected_models,
                    custom_questions=raw_questions
                )
                api_logger.info(f"[异常处理] ✅ 数据库状态已更新：{execution_id}")
            except Exception as state_err:
                api_logger.error(f"[异常处理] ⚠️ 数据库更新失败：{state_err}")
            
            # 【P1-T2 新增】异常处理完成，取消超时计时器
            try:
                timeout_manager.cancel_timer(execution_id)
                api_logger.info(f"[超时管理] ✅ 计时器已取消（异常处理）：{execution_id}")
            except Exception as timer_err:
                api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")
    
    thread = Thread(target=run_async_test)
    thread.start()

    return jsonify({'status': 'success', 'execution_id': execution_id, 'message': 'Test started successfully'})

import signal



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
            'stage': 'ai_fetching',
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
                from utils.ai_response_logger_v3 import log_ai_response
                
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
                    except Exception as log_err:
                        # 错误报告保存失败不影响主流程，记录日志
                        api_logger.error(f"[DeepSeek MVP] 错误报告保存失败：{log_err}")

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
            'stage': 'ai_fetching',
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
                from utils.ai_response_logger_v3 import log_ai_response
                
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
                    except Exception as log_err:
                        # 错误报告保存失败不影响主流程，记录日志
                        api_logger.error(f"[Qwen MVP] 错误报告保存失败：{log_err}")

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
            'stage': 'ai_fetching',
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
                from utils.ai_response_logger_v3 import log_ai_response
                
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
                    except Exception as log_err:
                        # 错误报告保存失败不影响主流程，记录日志
                        api_logger.error(f"[Zhipu MVP] 错误报告保存失败：{log_err}")

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
            'stage': 'ai_fetching',
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
                from utils.ai_response_logger_v3 import log_ai_response
                
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

        # 【关键修复】构建 final_result 对象
        final_result = {
            'detailed_results': detailed_results,
            'main_brand': brand_scores.get(main_brand, {
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
            }),
            'competitiveAnalysis': competitive_analysis,
            'summary': {
                'total_tests': len(detailed_results),
                'brands_tested': len(all_brands)
            },
            # 【新增】传递语义偏移和优化建议数据
            'semantic_drift_data': semantic_drift_data if 'semantic_drift_data' in dir() else None,
            'semantic_contrast_data': semantic_contrast_data if 'semantic_contrast_data' in dir() else None,
            'recommendation_data': recommendation_data if 'recommendation_data' in dir() else None,
            'negative_sources': negative_sources if 'negative_sources' in dir() else None
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
                # 防御性编程：安全获取嵌套字典值
                quality_metrics = result.get('quality_metrics') or {}
                detailed_feedback = quality_metrics.get('detailed_feedback') or {}
                model_responses.append({
                    'model_name': result.get('aiModel', 'unknown'),
                    'ai_response': result.get('response', ''),
                    'citations': detailed_feedback.get('citations', []),
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
                # 防御性编程：安全获取 enhanced_scores
                ranked_results = []
                for r in results:
                    enhanced_scores = r.get('enhanced_scores') or {}
                    if enhanced_scores.get('geo_score', 0) > 0:
                        ranked_results.append(r)
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
                # 防御性编程：安全获取 enhanced_scores
                ranked_results = []
                for r in results:
                    enhanced_scores = r.get('enhanced_scores') or {}
                    if enhanced_scores.get('geo_score', 0) > 0:
                        ranked_results.append(r)
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
@rate_limit(limit=20, window=60, per='endpoint')  # 限制每分钟 20 次请求
@monitored_endpoint('/api/platform-status', require_auth=False, validate_inputs=False)
def get_platform_status():
    """获取所有 AI 平台的状态信息（前端用于显示可用性和配置状态）"""
    try:
        # 从配置管理器获取平台状态
        from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
        config_manager = PlatformConfigManager()
        
        # 从健康检查模块获取详细状态
        from wechat_backend.ai_adapters.platform_health_monitor import PlatformHealthMonitor
        health_results = PlatformHealthMonitor.run_health_check()

        status_info = {}

        # 预定义支持的平台（按前端显示顺序）
        domestic_platforms = [
            {'id': 'deepseek', 'name': 'DeepSeek'},
            {'id': 'doubao', 'name': '豆包'},
            {'id': 'qwen', 'name': '通义千问'},
            {'id': 'wenxin', 'name': '文心一言'},
        ]
        
        overseas_platforms = [
            {'id': 'chatgpt', 'name': 'ChatGPT'},
            {'id': 'gemini', 'name': 'Gemini'},
            {'id': 'zhipu', 'name': '智谱 AI'},
        ]

        # 处理国内平台
        for platform_info in domestic_platforms:
            platform = platform_info['id']
            config = config_manager.get_platform_config(platform)
            health_data = health_results.get('platforms', {}).get(platform, {})
            
            is_configured = bool(config and config.api_key)
            
            status_info[platform] = {
                'id': platform,
                'name': platform_info['name'],
                'isConfigured': is_configured,  # 【前端需要】是否已配置
                'status': 'active' if is_configured else 'inactive',
                'has_api_key': is_configured,
                'category': 'domestic',  # 【新增】平台类别
                'quota': {
                    'daily_limit': getattr(config, 'daily_limit', None) if config else None,
                    'used_today': getattr(config, 'used_today', 0) if config else 0,
                } if config and is_configured else None,
            }

        # 处理海外平台
        for platform_info in overseas_platforms:
            platform = platform_info['id']
            config = config_manager.get_platform_config(platform)
            health_data = health_results.get('platforms', {}).get(platform, {})
            
            is_configured = bool(config and config.api_key)
            
            status_info[platform] = {
                'id': platform,
                'name': platform_info['name'],
                'isConfigured': is_configured,  # 【前端需要】是否已配置
                'status': 'active' if is_configured else 'inactive',
                'has_api_key': is_configured,
                'category': 'overseas',  # 【新增】平台类别
            }

        return jsonify({
            'status': 'success',
            'platforms': status_info,
            'summary': {
                'total': len(domestic_platforms) + len(overseas_platforms),
                'configured': sum(1 for p in status_info.values() if p['isConfigured']),
                'unconfigured': sum(1 for p in status_info.values() if not p['isConfigured']),
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting platform status: {e}")
        import traceback
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
                overall_score=(processed_results.get('main_brand') or {}).get('overallScore', 0),
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
    """
    轮询任务进度与分阶段状态

    【P0 修复 - 2026-02-28】数据源优化：
    1. 优先从新存储层读取（数据库）
    2. execution_store 作为缓存（降级方案）
    3. 支持增量轮询（减少数据传输）
    
    【P1 优化 - 同步检查机制】
    1. 检查 execution_store 和数据库数据是否同步
    2. 如果不同步，优先使用数据库数据
    3. 记录同步警告日志
    """
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    # 获取增量轮询参数
    since = request.args.get('since')  # 客户端传入的上次更新时间

    # ==================== 主数据源：新存储层（数据库） ====================
    try:
        service = get_report_service()
        report = service.get_full_report(task_id)

        if report and report.get('report'):
            report_data = report['report']
            results = report.get('results', [])
            analysis = report.get('analysis', {})

            # 增量轮询优化
            if since:
                last_updated = report_data.get('updated_at', '')
                if last_updated <= since:
                    # 无新数据，返回空响应
                    return jsonify({
                        'task_id': task_id,
                        'has_updates': False,
                        'last_updated': last_updated,
                        'source': 'database'
                    }), 200

            # P1 优化：同步检查机制
            # 检查 execution_store 是否有数据
            cache_sync_status = 'unknown'
            if task_id in execution_store:
                cache_data = execution_store[task_id]
                cache_progress = cache_data.get('progress', 0)
                db_progress = report_data.get('progress', 0)

                # 检查进度是否同步
                if abs(cache_progress - db_progress) > 10:  # 允许 10% 的误差
                    cache_sync_status = 'out_of_sync'
                    api_logger.warning(f"[TaskStatus] 同步警告：{task_id}, 缓存进度={cache_progress}%, 数据库进度={db_progress}%")
                else:
                    cache_sync_status = 'synced'
            else:
                cache_sync_status = 'cache_miss'

            # 【P0 修复 - 架构师决策】添加详细调试日志
            api_logger.info(f"[TaskStatus] 数据库查询结果：{task_id}, stage={report_data.get('stage')}, status={report_data.get('status')}, progress={report_data.get('progress')}, is_completed={report_data.get('is_completed')}")

            # 构建响应
            response_data = {
                'task_id': task_id,
                'progress': report_data.get('progress', 0),
                'stage': report_data.get('stage') or 'processing',  # 【修复】不要使用 'init' 作为默认值
                'detailed_results': results,
                'status': report_data.get('status') or 'processing',  # 【修复】不要使用 'processing' 作为默认值
                'results': results,
                'is_completed': report_data.get('is_completed', False),
                # 【P0 关键修复】强制停止轮询标志
                'should_stop_polling': report_data.get('status') in ['completed', 'failed'],
                'created_at': report_data.get('created_at', ''),
                'updated_at': report_data.get('updated_at', ''),
                'has_updates': True,
                'source': 'database',
                'cache_sync_status': cache_sync_status  # P1 优化：添加同步状态
            }

            # 添加高级分析数据（如果已完成）
            if report_data.get('status') == 'completed':
                response_data.update(analysis)

            api_logger.info(f"[TaskStatus] 返回前端数据：{task_id}, stage={response_data['stage']}, is_completed={response_data['is_completed']}, results={len(results)}")
            return jsonify(response_data), 200

    except Exception as db_err:
        api_logger.error(f'[TaskStatus] 数据库查询失败：{task_id}, 错误：{db_err}')
        # 继续尝试从缓存读取

    # ==================== 修复：优先使用数据库数据 ====================
    # 【P0 修复】数据库查询成功时，直接返回，不检查缓存
    # 避免缓存中的旧数据覆盖数据库的新数据
    if report:
        # 【P0 修复 - 架构师决策】添加详细调试日志
        api_logger.info(f"[TaskStatus] 数据库查询结果（第二次检查）：{task_id}, stage={report_data.get('stage')}, status={report_data.get('status')}, is_completed={report_data.get('is_completed')}")

        # 构建响应
        response_data = {
            'task_id': task_id,
            'progress': report_data.get('progress', 0),
            'stage': report_data.get('stage') or 'processing',  # 【修复】不要使用 'init' 作为默认值
            'detailed_results': results,
            'status': report_data.get('status') or 'processing',  # 【修复】不要使用 'processing' 作为默认值
            'results': results,
            'is_completed': report_data.get('is_completed', False),
            'created_at': report_data.get('created_at', ''),
            'updated_at': report_data.get('updated_at', ''),
            'has_updates': True,
            'source': 'database',  # 标识数据来源
            'cache_sync_status': 'database_priority'  # 标记使用数据库优先
        }

        # 添加高级分析数据（如果已完成）
        if report_data.get('status') == 'completed':
            response_data.update(analysis)

        api_logger.info(f"[TaskStatus] ✅ 返回前端数据（第二次）：{task_id}, stage={response_data['stage']}, is_completed={response_data['is_completed']}, results={len(results)}")
        return jsonify(response_data), 200

    # ==================== 降级：execution_store 缓存 ====================
    # 【降级方案】数据库查询结果为空时，从内存缓存读取
    api_logger.warning(f'[TaskStatus] 数据库无数据，降级到缓存：{task_id}')
    if task_id in execution_store:
        task_status = execution_store[task_id]

        # 【关键修复】确保 results 字段存在且为列表
        results_list = task_status.get('results', [])
        if not isinstance(results_list, list):
            results_list = []
            api_logger.warning(f'[TaskStatus] Task {task_id} results is not a list, resetting to empty list')

        # 增量轮询优化
        if since:
            last_updated = task_status.get('updated_at', '')
            if last_updated <= since:
                return jsonify({
                    'task_id': task_id,
                    'has_updates': False,
                    'last_updated': last_updated,
                    'source': 'cache'
                }), 200

        # 按照 API 契约返回任务状态信息
        response_data = {
            'task_id': task_id,
            'progress': task_status.get('progress', 0),
            'stage': task_status.get('stage', 'init'),
            'detailed_results': results_list,
            'status': task_status.get('status', 'init'),
            'results': results_list,
            'is_completed': task_status.get('status') == 'completed',
            # 【P0 关键修复】添加 should_stop_polling 字段，确保前端能停止轮询
            'should_stop_polling': task_status.get('status') in ['completed', 'failed'],
            'created_at': task_status.get('start_time', None),
            'updated_at': task_status.get('updated_at', ''),
            'has_updates': True,
            'source': 'cache'  # 标识数据来源
        }
        
        # 【P0 修复】如果任务已完成，返回高级分析数据
        if task_status.get('status') == 'completed':
            for key in ['semantic_drift_data', 'recommendation_data', 'negative_sources',
                        'competitive_analysis', 'brand_scores', 'insights',
                        'source_purity_data', 'source_intelligence_map', 'missing_brands']:
                if key in task_status:
                    response_data[key] = task_status[key]
        
        api_logger.debug(f"[TaskStatus] 从缓存返回：{task_id}, 结果数：{len(results_list)}")
        return jsonify(response_data), 200
    
    # ==================== 错误：任务不存在 ====================
    api_logger.warning(f'[TaskStatus] 任务不存在：{task_id}')
    return jsonify({'error': 'Task not found', 'task_id': task_id}), 404



# ==================== 存储架构优化集成 ====================
# 导入新的存储层服务
from wechat_backend.diagnosis_report_service import get_report_service

# ==================== P2-4 消息队列异步诊断接口 ====================
from wechat_backend.services.async_diagnosis_executor import get_async_executor


@wechat_bp.route('/api/perform-brand-test-async', methods=['POST', 'OPTIONS'])
@handle_api_exceptions
@require_auth_optional
@rate_limit(limit=3, window=60, per='user')  # 异步任务限流更严格
@monitored_endpoint('/api/perform-brand-test-async', require_auth=False, validate_inputs=True)
def perform_brand_test_async():
    """
    异步执行品牌诊断任务（P2-4 消息队列实现）

    使用 Celery 消息队列异步执行诊断任务，适用于：
    - 大量品牌对比
    - 多模型并行测试
    - 长耗时诊断任务

    请求格式与 /api/perform-brand-test 相同

    返回:
        {
            "status": "queued",
            "execution_id": "uuid",
            "message": "任务已提交，正在处理中",
            "estimated_time": 120  # 预估执行时间（秒）
        }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

    # 获取请求数据
    data = request.get_json(force=True)
    if data is None:
        return jsonify({"status": "error", "error": "Empty or invalid JSON", "code": 400}), 400

    # 获取当前用户 ID
    try:
        user_id = get_current_user_id()
    except:
        user_id = 'anonymous'

    # 输入验证
    try:
        # 验证品牌列表
        if 'brand_list' not in data:
            return jsonify({"status": "error", "error": "Missing brand_list", "code": 400}), 400
        if not isinstance(data['brand_list'], list):
            return jsonify({"status": "error", "error": "brand_list must be a list", "code": 400}), 400
        brand_list = data['brand_list']
        if not brand_list:
            return jsonify({"status": "error", "error": "brand_list cannot be empty", "code": 400}), 400

        # 验证模型列表
        if 'selectedModels' not in data:
            return jsonify({"status": "error", "error": "Missing selectedModels", "code": 400}), 400
        if not isinstance(data['selectedModels'], list):
            return jsonify({"status": "error", "error": "selectedModels must be a list", "code": 400}), 400
        selected_models = data['selectedModels']

        # 验证自定义问题（可选）
        custom_questions = data.get('customQuestions', [])
        if isinstance(custom_questions, str):
            import re
            custom_questions = [q.strip() for q in re.split(r'[？?.\n]+', custom_questions) if q.strip()]

        # 验证用户 OpenID
        user_openid = data.get('userOpenid') or (user_id if user_id != 'anonymous' else 'anonymous')

        # 验证优先级（可选，0-10）
        priority = min(10, max(0, int(data.get('priority', 0))))

    except Exception as e:
        api_logger.error(f"Input validation failed: {e}")
        return jsonify({'error': f'Invalid input data: {str(e)}'}), 400

    # 提交异步任务
    async_executor = get_async_executor()
    execution_id, response = async_executor.submit_diagnosis_task(
        user_id=user_id,
        brand_list=brand_list,
        selected_models=selected_models,
        custom_questions=custom_questions,
        user_openid=user_openid,
        priority=priority
    )

    # 返回响应
    status_code = 202 if response['status'] == 'queued' else 500
    return jsonify(response), status_code


@wechat_bp.route('/api/diagnosis/status/<execution_id>', methods=['GET'])
@rate_limit(limit=30, window=60, per='user')
@monitored_endpoint('/api/diagnosis/status', require_auth=False, validate_inputs=False)
def get_diagnosis_status(execution_id):
    """
    获取诊断任务状态（P2-4 消息队列）

    参数:
        execution_id: 执行 ID

    返回:
        {
            "execution_id": "uuid",
            "status": "running|success|failed|pending|queued",
            "progress": 50,
            "task_type": "brand_diagnosis",
            "created_at": "2026-02-28T10:00:00",
            "started_at": "2026-02-28T10:00:05",
            "completed_at": null,
            "result": {...},  # 完成后返回
            "error_message": null  # 失败时返回
        }
    """
    if not execution_id:
        return jsonify({'error': 'Execution ID is required'}), 400

    async_executor = get_async_executor()
    task_status = async_executor.get_task_status(execution_id)

    if not task_status:
        return jsonify({'error': 'Task not found', 'execution_id': execution_id}), 404

    return jsonify(task_status), 200


@wechat_bp.route('/api/diagnosis/cancel/<execution_id>', methods=['POST'])
@require_auth
@rate_limit(limit=5, window=60, per='user')
@monitored_endpoint('/api/diagnosis/cancel', require_auth=True, validate_inputs=False)
def cancel_diagnosis_task(execution_id):
    """
    取消诊断任务

    参数:
        execution_id: 执行 ID

    返回:
        {
            "status": "success|error",
            "message": "任务已取消"
        }
    """
    if not execution_id:
        return jsonify({'error': 'Execution ID is required'}), 400

    async_executor = get_async_executor()
    success = async_executor.cancel_task(execution_id)

    if success:
        return jsonify({'status': 'success', 'message': '任务已取消'}), 200
    else:
        return jsonify({'status': 'error', 'error': '无法取消任务，可能已完成或不存在'}), 400


@wechat_bp.route('/api/diagnosis/statistics', methods=['GET'])
@rate_limit(limit=10, window=60, per='user')
@monitored_endpoint('/api/diagnosis/statistics', require_auth=False, validate_inputs=False)
def get_diagnosis_statistics():
    """
    获取诊断任务统计信息

    返回:
        {
            "total_tasks": 100,
            "by_status": {"success": 80, "failed": 10, "running": 5, "pending": 5},
            "by_type": {"brand_diagnosis": 90, "analytics": 10},
            "avg_duration_seconds": 120.5,
            "success_rate": 88.9
        }
    """
    from wechat_backend.models_pkg.task_queue import get_task_statistics

    days = request.args.get('days', 7, type=int)
    stats = get_task_statistics(days)

    return jsonify(stats), 200


# ==================== 更新 perform_brand_test - 集成新存储层 ====================
# 导入新的存储层服务
from wechat_backend.diagnosis_report_service import get_report_service

# ==================== 更新 perform_brand_test - 集成新存储层 ====================
# 在 run_async_test 函数中，找到执行完成后添加以下代码：
# 
# # 使用新存储层保存报告
# try:
#     service = get_report_service()
#     
#     # 1. 创建报告
#     config = {
#         'brand_name': main_brand,
#         'competitor_brands': competitor_brands if 'competitor_brands' in locals() else [],
#         'selected_models': selected_models,
#         'custom_questions': raw_questions if 'raw_questions' in locals() else []
#     }
#     report_id = service.create_report(execution_id, user_id or 'anonymous', config)
#     
#     # 2. 添加结果
#     results = execution_store[execution_id].get('results', [])
#     service.add_results_batch(report_id, execution_id, results)
#     
#     # 3. 添加分析数据
#     analysis_data = {}
#     if 'competitive_analysis' in execution_store[execution_id]:
#         analysis_data['competitive_analysis'] = execution_store[execution_id]['competitive_analysis']
#     if 'brand_scores' in execution_store[execution_id]:
#         analysis_data['brand_scores'] = execution_store[execution_id]['brand_scores']
#     service.add_analyses_batch(report_id, execution_id, analysis_data)
#     
#     # 4. 完成报告
#     full_report = {
#         'report': execution_store[execution_id],
#         'results': results,
#         'analysis': analysis_data
#     }
#     service.complete_report(execution_id, full_report)
#     
#     api_logger.info(f"✅ 使用新存储层保存报告：{execution_id}")
# except Exception as storage_err:
#     api_logger.error(f"❌ 存储层保存失败：{storage_err}")
#     # 不影响原有逻辑，继续执行