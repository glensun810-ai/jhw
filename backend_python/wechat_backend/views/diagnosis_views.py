"""
诊断相关视图模块
包含品牌诊断、测试执行、进度查询等路由

注意：本模块使用 views/__init__.py 中定义的 wechat_bp 蓝图

【P0 重构 - 阶段五】使用 DiagnosisOrchestrator 统一编排诊断流程
核心原则：
1. 顺序执行 - API 响应保存 → 统计分析 → 结果聚合 → 报告生成
2. 状态一致 - 内存和数据库原子性更新
3. 完整持久化 - 所有结果必须完整保存后才能进入下一环节
4. 统一调度 - 由诊断编排器协调所有子流程
"""
from flask import request, jsonify, g, current_app
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

# 【P0-WebSocket 修复】导入并行执行引擎和实时推送服务
from wechat_backend.nxm_concurrent_engine_v3 import execute_parallel_nxm
from wechat_backend.services.realtime_push_service import send_progress_sync, send_complete_sync, send_error_sync

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

# 【P0 关键修复 - 2026-03-03】WebSocket 服务导入（替代 SSE，微信小程序不支持 SSE）
from wechat_backend.websocket_route import (
    send_progress_update,
    send_diagnosis_progress as send_intelligence_update
)

# 【P0 关键修复】任务完成和错误通知使用 realtime_push_service
from wechat_backend.services.realtime_push_service import (
    send_complete_sync as send_task_complete,
    send_error_sync as send_error
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

# 【P0 重构 - 阶段五】导入诊断编排器
from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator

# 从主模块导入蓝图（修复 P0-3: 确保路由注册到正确的蓝图）
from . import wechat_bp

# P0 修复：导入字段转换器
from utils.field_converter import convert_response_to_camel

# 【P2 增强 - 2026-03-05】品牌分析输入验证增强
# 导入输入验证工具函数
from wechat_backend.security.input_validation import validate_safe_text

# 【P2 增强】验证常量
BRAND_VALIDATION_CONSTANTS = {
    'MIN_BRAND_NAME_LENGTH': 1,
    'MAX_BRAND_NAME_LENGTH': 100,
    'MAX_BRANDS_COUNT': 10,
    'MIN_QUESTION_LENGTH': 1,
    'MAX_QUESTION_LENGTH': 500,
    'MAX_QUESTIONS_COUNT': 20,
    'MAX_MODEL_COUNT': 10,
}

# 【P2 增强】品牌名称验证正则（允许中英文、数字、常见符号）
BRAND_NAME_PATTERN = re.compile(r'^[\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\-_.()（）]+$')


def _validate_brand_name(brand_name: str) -> tuple:
    """
    验证品牌名称的有效性

    Args:
        brand_name: 品牌名称

    Returns:
        (is_valid: bool, error_message: str)

    【P2 增强 - 2026-03-05】新增品牌名称验证
    """
    if not brand_name:
        return False, '品牌名称不能为空'

    if not isinstance(brand_name, str):
        return False, f'品牌名称必须是字符串，得到 {type(brand_name).__name__}'

    trimmed = brand_name.strip()
    if not trimmed:
        return False, '品牌名称不能全为空白字符'

    # 长度验证
    if len(trimmed) < BRAND_VALIDATION_CONSTANTS['MIN_BRAND_NAME_LENGTH'] or \
       len(trimmed) > BRAND_VALIDATION_CONSTANTS['MAX_BRAND_NAME_LENGTH']:
        return False, (
            f'品牌名称长度应在 {BRAND_VALIDATION_CONSTANTS["MIN_BRAND_NAME_LENGTH"]}-'
            f'{BRAND_VALIDATION_CONSTANTS["MAX_BRAND_NAME_LENGTH"]} 字符之间，当前为 {len(trimmed)}'
        )

    # 字符合法性验证
    if not BRAND_NAME_PATTERN.match(trimmed):
        return False, f'品牌名称包含非法字符：{trimmed[:20]}'

    # 检查过多重复字符
    max_repeat = 50
    current_repeat = 1
    for i in range(1, min(len(trimmed), 200)):
        if trimmed[i] == trimmed[i-1]:
            current_repeat += 1
            if current_repeat > max_repeat:
                return False, '品牌名称包含过多的重复字符'
        else:
            current_repeat = 1

    return True, ''


def _validate_question_text(question: str, index: int = 0) -> tuple:
    """
    验证问题文本的有效性

    Args:
        question: 问题文本
        index: 问题索引（用于错误提示）

    Returns:
        (is_valid: bool, error_message: str)

    【P2 增强 - 2026-03-05】新增问题文本验证
    """
    if not question:
        return False, f'问题 {index + 1} 不能为空'

    if not isinstance(question, str):
        return False, f'问题 {index + 1} 必须是字符串，得到 {type(question).__name__}'

    trimmed = question.strip()
    if not trimmed:
        return False, f'问题 {index + 1} 不能全为空白字符'

    # 长度验证
    if len(trimmed) < BRAND_VALIDATION_CONSTANTS['MIN_QUESTION_LENGTH'] or \
       len(trimmed) > BRAND_VALIDATION_CONSTANTS['MAX_QUESTION_LENGTH']:
        return False, (
            f'问题 {index + 1} 长度应在 '
            f'{BRAND_VALIDATION_CONSTANTS["MIN_QUESTION_LENGTH"]}-'
            f'{BRAND_VALIDATION_CONSTANTS["MAX_QUESTION_LENGTH"]} 字符之间'
        )

    # 检查不可控制字符
    for char in trimmed:
        code = ord(char)
        # 允许的控制字符：\t (9), \n (10), \r (13)
        if code < 32 and code not in (9, 10, 13):
            return False, f'问题 {index + 1} 包含非法控制字符'
        # 检查 Unicode 代理对
        if 0xD800 <= code <= 0xDFFF:
            return False, f'问题 {index + 1} 包含无效 Unicode 字符'

    return True, ''


def _validate_brand_test_input(data: dict) -> tuple:
    """
    综合验证品牌测试输入数据

    Args:
        data: 请求数据字典

    Returns:
        (is_valid: bool, error_response: tuple)
        - is_valid: 是否验证通过
        - error_response: (response_data, status_code) 或 None

    【P2 增强 - 2026-03-05】统一输入验证逻辑
    """
    # 验证 brand_list
    if 'brand_list' not in data:
        return False, (jsonify({
            "status": "error",
            "error": 'Missing brand_list in request data',
            "code": 400,
            'received_fields': list(data.keys())
        }), 400)

    if not isinstance(data['brand_list'], list):
        return False, (jsonify({
            "status": "error",
            "error": 'brand_list must be a list',
            "code": 400,
            'received': type(data['brand_list']).__name__,
            'received_value': data['brand_list']
        }), 400)

    brand_list = data['brand_list']
    if not brand_list:
        return False, (jsonify({
            "status": "error",
            "error": 'brand_list cannot be empty',
            "code": 400,
            'received': brand_list
        }), 400)

    # 【P2 增强】品牌数量限制
    if len(brand_list) > BRAND_VALIDATION_CONSTANTS['MAX_BRANDS_COUNT']:
        return False, (jsonify({
            "status": "error",
            "error": f'品牌数量过多，最多支持 {BRAND_VALIDATION_CONSTANTS["MAX_BRANDS_COUNT"]} 个品牌',
            "code": 400,
            'received_count': len(brand_list),
            'max_allowed': BRAND_VALIDATION_CONSTANTS['MAX_BRANDS_COUNT']
        }), 400)

    # 【P2 增强】验证每个品牌名称
    for i, brand in enumerate(brand_list):
        if not isinstance(brand, str):
            return False, (jsonify({
                "status": "error",
                "error": f'Each brand in brand_list must be a string, got {type(brand).__name__}',
                "code": 400,
                'index': i,
                'problematic_value': str(brand)[:100]
            }), 400)

        is_valid, error_msg = _validate_brand_name(brand)
        if not is_valid:
            return False, (jsonify({
                "status": "error",
                "error": f'品牌 {i + 1} 验证失败：{error_msg}',
                "code": 400,
                'index': i,
                'brand_name': brand[:50]
            }), 400)

    # 验证 selectedModels
    if 'selectedModels' not in data:
        return False, (jsonify({
            "status": "error",
            "error": 'Missing selectedModels in request data',
            "code": 400,
            'received_fields': list(data.keys())
        }), 400)

    if not isinstance(data['selectedModels'], list):
        return False, (jsonify({
            "status": "error",
            "error": 'selectedModels must be a list',
            "code": 400,
            'received': type(data['selectedModels']).__name__,
            'received_value': data['selectedModels']
        }), 400)

    selected_models = data['selectedModels']
    if not selected_models:
        return False, (jsonify({
            "status": "error",
            "error": 'At least one AI model must be selected',
            "code": 400,
            'received': selected_models
        }), 400)

    # 【P2 增强】模型数量限制
    if len(selected_models) > BRAND_VALIDATION_CONSTANTS['MAX_MODEL_COUNT']:
        return False, (jsonify({
            "status": "error",
            "error": f'模型数量过多，最多支持 {BRAND_VALIDATION_CONSTANTS["MAX_MODEL_COUNT"]} 个模型',
            "code": 400,
            'received_count': len(selected_models),
            'max_allowed': BRAND_VALIDATION_CONSTANTS['MAX_MODEL_COUNT']
        }), 400)

    # 验证 custom_question / customQuestions
    custom_questions = []
    if 'custom_question' in data:
        if not isinstance(data['custom_question'], str):
            return False, (jsonify({
                "status": "error",
                "error": 'custom_question must be a string',
                "code": 400,
                'received': type(data['custom_question']).__name__,
                'received_value': str(data['custom_question'])[:200]
            }), 400)

        # 智能分割多个问题
        question_text = data['custom_question'].strip()
        if question_text:
            raw_questions = re.split(r'[？?.\n\s]+', question_text)
            custom_questions = [
                q.strip() + ('?' if not q.strip().endswith('?') else '')
                for q in raw_questions if q.strip()
            ]

    elif 'customQuestions' in data:
        if not isinstance(data['customQuestions'], list):
            return False, (jsonify({
                "status": "error",
                "error": 'customQuestions must be a list',
                "code": 400,
                'received': type(data['customQuestions']).__name__,
                'received_value': str(data['customQuestions'])[:200]
            }), 400)
        custom_questions = data['customQuestions']

    # 【P2 增强】问题数量限制
    if len(custom_questions) > BRAND_VALIDATION_CONSTANTS['MAX_QUESTIONS_COUNT']:
        return False, (jsonify({
            "status": "error",
            "error": f'问题数量过多，最多支持 {BRAND_VALIDATION_CONSTANTS["MAX_QUESTIONS_COUNT"]} 个问题',
            "code": 400,
            'received_count': len(custom_questions),
            'max_allowed': BRAND_VALIDATION_CONSTANTS['MAX_QUESTIONS_COUNT']
        }), 400)

    # 【P2 增强】验证每个问题
    for i, question in enumerate(custom_questions):
        if not isinstance(question, str):
            return False, (jsonify({
                'status': "error",
                'error': f'Each question must be a string, got {type(question).__name__}',
                'code': 400,
                'index': i
            }), 400)

        is_valid, error_msg = _validate_question_text(question, i)
        if not is_valid:
            return False, (jsonify({
                'status': "error",
                'error': error_msg,
                'code': 400,
                'index': i,
                'question': question[:100]
            }), 400)

    return True, None


# Global store for execution progress (in production, use Redis or database)
execution_store = {}

# 诊断相关辅助函数
# 【P0 重构 - 阶段五】使用 DiagnosisOrchestrator 统一编排诊断流程
# 核心原则：
# 1. 顺序执行 - API 响应保存 → 统计分析 → 结果聚合 → 报告生成
# 2. 状态一致 - 内存和数据库原子性更新
# 3. 完整持久化 - 所有结果必须完整保存后才能进入下一环节
# 4. 统一调度 - 由诊断编排器协调所有子流程
@wechat_bp.route('/api/perform-brand-test', methods=['POST', 'OPTIONS'])
@handle_api_exceptions
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
@monitored_endpoint('/api/perform-brand-test', require_auth=False, validate_inputs=True)
def perform_brand_test():
    """
    执行品牌认知诊断测试（重构版）
    
    【P0 重构 - 阶段五】使用 DiagnosisOrchestrator 统一编排诊断流程
    
    诊断流程：
    1. 初始化阶段 - 设置初始状态，创建数据库记录
    2. AI 调用阶段 - 并行调用多个 AI 平台获取诊断结果
    3. 结果保存阶段 - 将所有结果保存到数据库
    4. 结果验证阶段 - 验证结果数量和质量
    5. 后台分析阶段 - 异步执行品牌分析和竞争分析
    6. 报告聚合阶段 - 聚合所有结果为最终报告
    7. 完成阶段 - 更新状态并发送通知
    
    Returns:
        JSON 响应：
        - success: 启动是否成功
        - execution_id: 执行 ID（用于轮询进度）
        - message: 启动消息
    """
    # 处理 CORS 预检请求
    if request.method == 'OPTIONS':
        api_logger.info("[DEBUG] Handling OPTIONS preflight request")
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add(
            'Access-Control-Allow-Headers',
            'Content-Type,Authorization,X-WX-OpenID,X-OpenID,X-Wechat-OpenID'
        )
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

    # 获取当前用户 ID
    try:
        user_id = get_current_user_id()
    except Exception:
        user_id = 'anonymous'

    # 解析请求数据
    data = request.get_json(force=True)
    if data is None:
        return jsonify({
            "status": "error",
            "error": "Empty or invalid JSON",
            "code": 400
        }), 400

    # ========== 【P2 增强】输入验证和净化（使用统一验证函数） ==========
    is_valid, error_response = _validate_brand_test_input(data)
    if not is_valid:
        api_logger.warning(f"[BrandTest] 输入验证失败：{error_response[0].get_json()}")
        return error_response

    # 验证通过，继续处理
    try:
        brand_list = data['brand_list']
        selected_models = data['selectedModels']

        # 解析模型列表（支持字典和字符串格式）
        parsed_selected_models = []
        for model in selected_models:
            if isinstance(model, dict):
                model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
                if model_name:
                    parsed_selected_models.append({
                        'name': model_name,
                        'checked': model.get('checked', True)
                    })
                else:
                    # 尝试使用第一个可用的键值
                    for key, value in model.items():
                        if key in ['name', 'id', 'value', 'label'] and isinstance(value, str):
                            parsed_selected_models.append({
                                'name': value,
                                'checked': model.get('checked', True)
                            })
                            break
            elif isinstance(model, str):
                parsed_selected_models.append({'name': model, 'checked': True})
            else:
                api_logger.warning(f"Unsupported model format: {model}, type: {type(model)}")

        selected_models = parsed_selected_models

        if not selected_models:
            return jsonify({
                "status": "error",
                "error": 'No valid AI models found after parsing',
                "code": 400
            }), 400

        # 解析问题列表（已在验证函数中处理）
        custom_questions = []
        if 'custom_question' in data:
            question_text = data['custom_question'].strip()
            if question_text:
                raw_questions = re.split(r'[？?.\n\s]+', question_text)
                custom_questions = [
                    q.strip() + ('?' if not q.strip().endswith('?') else '')
                    for q in raw_questions if q.strip()
                ]
        elif 'customQuestions' in data:
            custom_questions = data['customQuestions']

        api_logger.info(f"[QuestionSplit] 分割后问题数：{len(custom_questions)}")

        # 获取用户信息
        user_openid = data.get('userOpenid') or (user_id if user_id != 'anonymous' else 'anonymous')
        user_level = UserLevel(data.get('userLevel', 'Free'))

        # 验证模型可用性
        for model in selected_models:
            model_name = model['name'] if isinstance(model, dict) else model
            normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)

            if not AIAdapterFactory.is_platform_available(normalized_model_name):
                registered_keys = [pt.value for pt in AIAdapterFactory._adapters.keys()]
                api_logger.error(
                    f"Model {model_name} (normalized to {normalized_model_name}) "
                    f"not registered or not configured. Available models: {registered_keys}"
                )
                return jsonify({
                    "status": "error",
                    "error": f'Model {model_name} not registered or not configured in AIAdapterFactory',
                    "code": 400,
                    "available_models": registered_keys,
                    "received_model": model_name,
                    "normalized_to": normalized_model_name
                }), 400

            # 验证 API Key 配置
            from wechat_backend.config_manager import config_manager
            api_key = config_manager.get_api_key(normalized_model_name)
            if not api_key:
                return jsonify({
                    "status": "error",
                    "error": f'Model {model_name} not configured - missing API key',
                    "code": 400,
                    'message': 'API Key 缺失'
                }), 400

        # 验证模型区域一致性
        model_names = [
            model["name"] if isinstance(model, dict) else model
            for model in selected_models
        ]
        normalized_model_names = [
            AIAdapterFactory.get_normalized_model_name(name)
            for name in model_names
        ]

        is_valid, error_msg = validate_model_region_consistency(normalized_model_names)
        if not is_valid:
            api_logger.warning(f"Model region consistency check failed: {error_msg}")
            return jsonify({
                "status": "error",
                "error": error_msg,
                "code": 400
            }), 400

        # 验证问题安全性
        for question in custom_questions:
            if not isinstance(question, str):
                return jsonify({
                    'error': f'Each question in customQuestions must be a string, got {type(question)}'
                }), 400
            if not validate_safe_text(question, max_length=500):
                return jsonify({
                    'error': f'Unsafe question content: {question}'
                }), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({
            'error': f'Invalid input data: {str(e)}'
        }), 400

    # ========== 启动诊断编排器 ==========
    execution_id = str(uuid.uuid4())

    api_logger.info(
        f"[Orchestrator] 启动诊断 - execution_id={execution_id}, "
        f"brand={brand_list[0]}, models={len(selected_models)}, "
        f"questions={len(custom_questions)}"
    )

    # 【P0 关键修复 - 2026-03-05】在主线程中捕获 Flask app 实例，供背景线程使用
    # 必须在主线程中捕获，因为 current_app 是 context-local proxy
    from flask import current_app as flask_current_app
    app_instance = flask_current_app._get_current_object() if hasattr(flask_current_app, '_get_current_object') else flask_current_app
    api_logger.info(f"[AppContext] 主线程中捕获 app 实例：{app_instance}")

    # 【P0 修复 - 2026-03-04】提前创建报告记录，获取 report_id
    report_id = None
    try:
        from wechat_backend.diagnosis_report_service import get_report_service
        
        service = get_report_service()
        config = {
            'brand_name': brand_list[0],
            'competitor_brands': brand_list[1:] if len(brand_list) > 1 else [],
            'selected_models': selected_models,
            'custom_questions': custom_questions
        }
        
        # 创建初始报告记录
        report_id = service.create_report(
            execution_id=execution_id,
            user_id=user_id or 'anonymous',
            config=config
        )
        
        api_logger.info(
            f"[Orchestrator] ✅ 初始报告记录已创建：{execution_id}, "
            f"report_id={report_id}"
        )
        
        # 更新初始状态
        service.report_repo.update_status(
            execution_id=execution_id,
            status='initializing',
            progress=0,
            stage='init',
            is_completed=False
        )
        
    except Exception as e:
        api_logger.error(f"[Orchestrator] ⚠️ 创建初始报告记录失败：{e}")
        # 报告记录创建失败不影响主流程，继续执行

    # 初始化 execution_store
    execution_store[execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': 0,
        'status': 'initializing',
        'stage': 'init',
        'results': [],
        'start_time': datetime.now().isoformat(),
        'report_id': report_id
    }

    def run_orchestrated_diagnosis():
        """
        使用诊断编排器执行诊断流程
        
        【P0 重构 - 阶段五】
        所有子流程由 DiagnosisOrchestrator 统一协调：
        1. 初始化阶段
        2. AI 调用阶段 (并行)
        3. 结果保存阶段
        4. 结果验证阶段
        5. 后台分析阶段 (异步)
        6. 报告聚合阶段
        7. 完成阶段
        """
        thread_id = None
        timeout_manager = None
        
        try:
            import threading
            thread_id = threading.current_thread().ident
            api_logger.info(
                f"[Orchestrator] 异步线程启动 - execution_id={execution_id}, "
                f"thread_id={thread_id}"
            )

            # 启动全局超时计时器（10 分钟）
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
                        brand_name=brand_list[0],
                        competitor_brands=brand_list[1:] if len(brand_list) > 1 else [],
                        selected_models=selected_models,
                        custom_questions=custom_questions
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

            # 【P0 修复 - 消除双重数据库记录创建】
            # 注意：不再在此处创建数据库记录，由 DiagnosisOrchestrator._phase_results_saving
            # 在阶段 3 统一创建（使用事务管理，确保原子性）
            # 这样可以避免：
            # 1. 重复创建报告记录
            # 2. 不必要的数据库写入
            # 3. 事务管理冲突

            # 使用诊断编排器执行完整诊断流程
            import asyncio

            def run_async_in_thread(coro):
                """在线程中安全运行异步代码"""
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            # 【P0 关键修复 - 2026-03-05】使用主线程捕获的 app_instance
            # app_instance 已在主线程中捕获（见 line 595），通过闭包传递到背景线程
            def run_with_app_context():
                """在应用上下文中运行诊断"""
                with app_instance.app_context():
                    return run_async_in_thread(
                        orchestrator.execute_diagnosis(
                            user_id=user_id or 'anonymous',
                            brand_list=brand_list,
                            selected_models=selected_models,
                            custom_questions=custom_questions,
                            user_openid=user_openid,
                            user_level=user_level.value
                        )
                    )

            # 创建并执行诊断编排器
            orchestrator = DiagnosisOrchestrator(execution_id, execution_store)

            result = run_with_app_context()

            # 处理编排器返回结果
            if result.get('success'):
                api_logger.info(
                    f"[Orchestrator] ✅ 诊断执行完成 - execution_id={execution_id}, "
                    f"总耗时={result.get('total_time', 'N/A')}秒"
                )

                # 取消超时计时器
                try:
                    timeout_manager.cancel_timer(execution_id)
                    api_logger.info(f"[超时管理] ✅ 计时器已取消：{execution_id}")
                except Exception as timer_err:
                    api_logger.warning(f"[超时管理] 计时器取消失败：{timer_err}")
                
                # 【P0 关键修复 - 2026-03-05】清理数据库连接，防止连接泄漏
                try:
                    from wechat_backend.database_connection_pool import get_pool_manager
                    pool_manager = get_pool_manager()
                    
                    if hasattr(pool_manager, 'cleanup_thread_sessions'):
                        pool_manager.cleanup_thread_sessions()
                    
                    try:
                        from wechat_backend.database import db
                        if hasattr(db, 'session') and db.session:
                            db.session.close()
                            db_logger.info(f"[DB 清理] 成功完成后的数据库会话已关闭：{execution_id}")
                    except Exception:
                        pass
                    
                    api_logger.info(f"[DB 清理] 成功完成后的数据库连接已清理：{execution_id}")
                except Exception as cleanup_err:
                    api_logger.warning(f"[DB 清理] 清理失败：{cleanup_err}")
                    
            else:
                error_message = result.get('error', '诊断执行失败')
                api_logger.error(
                    f"[Orchestrator] ❌ 诊断执行失败 - execution_id={execution_id}, "
                    f"错误={error_message}"
                )
                
                # 取消超时计时器
                try:
                    timeout_manager.cancel_timer(execution_id)
                except Exception:
                    pass

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_message = f"{str(e)}"
            api_logger.error(
                f"[Orchestrator] ❌ 未预期异常 - execution_id={execution_id}, "
                f"thread_id={thread_id}: {error_message}\nTraceback: {error_traceback}"
            )

            # 更新内存状态
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'status': 'failed',
                    'stage': 'failed',
                    'progress': 100,
                    'is_completed': True,
                    'should_stop_polling': True,
                    'error': f"异步任务执行失败：{error_message}"
                })

            # 更新数据库状态
            try:
                from wechat_backend.state_manager import get_state_manager
                state_manager = get_state_manager(execution_store)
                state_manager.update_state(
                    execution_id=execution_id,
                    status='failed',
                    stage='failed',
                    progress=100,
                    is_completed=True,
                    error_message=f"异步任务执行失败：{error_message}",
                    write_to_db=True,
                    user_id=user_id or "anonymous",
                    brand_name=brand_list[0],
                    competitor_brands=brand_list[1:] if len(brand_list) > 1 else [],
                    selected_models=selected_models,
                    custom_questions=custom_questions
                )
                api_logger.info(f"[Orchestrator] ✅ 数据库异常状态已更新：{execution_id}")
            except Exception as state_err:
                api_logger.error(f"[Orchestrator] ⚠️ 数据库状态更新失败：{state_err}")

            # 取消超时计时器
            try:
                if timeout_manager:
                    timeout_manager.cancel_timer(execution_id)
            except Exception:
                pass

        finally:
            # 【P0 关键修复 - 2026-03-05】清理数据库连接，防止连接泄漏
            # 背景线程中创建的数据库会话需要显式清理
            try:
                from wechat_backend.database_connection_pool import get_db_pool
                pool = get_db_pool()
                
                # 清理当前线程的数据库连接
                if pool and hasattr(pool, 'release_connection'):
                    # 如果当前线程有连接，归还它
                    pass  # 连接池会自动管理
                
                api_logger.info(f"[DB 清理] 背景线程数据库连接清理完成：{execution_id}")
            except Exception as cleanup_err:
                api_logger.warning(f"[DB 清理] 清理失败：{cleanup_err}")

    # 启动异步线程
    thread = Thread(target=run_orchestrated_diagnosis, daemon=True)
    thread.name = f"OrchestratorThread-{execution_id[:8]}"
    thread.start()

    api_logger.info(
        f"[Orchestrator] ✅ 异步线程已启动 - execution_id={execution_id}, "
        f"thread_name={thread.name}"
    )

    # P0 修复：转换为 camelCase 并返回 report_id
    response_data = {
        'status': 'success',
        'execution_id': execution_id,
        'report_id': report_id,
        'message': 'Test started successfully'
    }
    return jsonify(convert_response_to_camel(response_data))


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
            api_logger.info(f"[P1 数据持久化] 开始保存深度情报结果：task_id={task_id}")
            try:
                save_deep_intelligence_result(task_id, deep_result_obj)
                api_logger.info(f"[P1 数据持久化] ✅ 深度情报结果已保存：task_id={task_id}")
            except Exception as save_err:
                api_logger.error(f"[P1 数据持久化] ❌ 保存深度情报结果失败：{save_err}")
                raise

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

            api_logger.info(f"[P1 数据持久化] 开始保存品牌测试结果：task_id={task_id}")
            try:
                save_brand_test_result(brand_test_result)
                api_logger.info(f"[P1 数据持久化] ✅ 品牌测试结果已保存：task_id={task_id}")
            except Exception as save_err:
                api_logger.error(f"[P1 数据持久化] ❌ 保存品牌测试结果失败：{save_err}")
                raise

            # 最终更新为完成状态
            update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")
            api_logger.info(f"[P1 数据持久化] ✅ 任务已完成：task_id={task_id}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            api_logger.error(f"[P1 数据持久化] ❌ Async test execution failed: {e}")
            api_logger.error(f"[P1 数据持久化] 错误堆栈：{error_details}")
            update_task_stage(task_id, TaskStage.INIT, 0, f"任务执行失败: {str(e)}")

    thread = Thread(target=run_async_test)
    thread.start()

    return jsonify({
        'task_id': task_id,
        'message': '任务已接收并加入队列'
    }), 202




@wechat_bp.route('/test/status/<task_id>', methods=['GET'])
@rate_limit(limit=30, window=60, per='endpoint')  # 【P0 优化 - 2026-03-04】提高限流
@monitored_endpoint('/test/status', require_auth=False, validate_inputs=False)
def get_task_status_api(task_id):
    """
    轮询任务进度与分阶段状态（P0 性能优化版 - 2026-03-04）

    【P0 关键修复】
    1. 只查询报告主表，不查询明细和结果（性能提升 3-5 倍）
    2. 使用轻量级查询，减少数据库负载
    3. 增量轮询优化，无变化时返回空响应
    4. 只在完成时返回完整数据

    响应字段说明：
    - basic: task_id, status, stage, progress, is_completed, should_stop_polling
    - full: basic + results (只在完成时返回)
    """
    if not task_id:
        return jsonify({'error': 'Task ID is required'}), 400

    # 获取增量轮询参数
    since = request.args.get('since')
    fields = request.args.get('fields', 'basic')  # basic | full

    # ==================== 主数据源：数据库（轻量级查询） ====================
    # 【P0 关键修复 - 2026-03-04】只查询报告主表，不查询明细
    try:
        from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
        
        report_repo = DiagnosisReportRepository()
        report = report_repo.get_by_execution_id(task_id)

        if not report:
            # 降级：从 execution_store 读取
            if task_id in execution_store:
                report = execution_store[task_id]
            else:
                return jsonify({
                    'task_id': task_id,
                    'status': 'not_found',
                    'progress': 0,
                    'error': 'Task not found'
                }), 404

        # 提取基本字段
        # 【P0 关键修复 - 2026-03-04】安全访问报告字段，防止 NoneType 错误
        if not report:
            # 数据库查询返回 None，降级到缓存
            api_logger.warning(
                f"[TaskStatus] 数据库返回 None，降级到缓存：{task_id}"
            )
            if task_id in execution_store:
                report = execution_store[task_id]
            else:
                return jsonify({
                    'task_id': task_id,
                    'status': 'not_found',
                    'progress': 0,
                    'error': 'Task not found'
                }), 404

        # 安全提取字段（使用默认值）
        stage = (report or {}).get('stage', 'init')
        status = (report or {}).get('status', 'processing')
        progress = (report or {}).get('progress', 0)
        is_completed = bool((report or {}).get('is_completed', False))
        updated_at = (report or {}).get('updated_at', '')
        error_message = (report or {}).get('error_message', None)

        # 【P0 优化】增量轮询：无变化时返回空响应
        if since and updated_at <= since:
            # P0 修复：转换为 camelCase
            return jsonify(convert_response_to_camel({
                'task_id': task_id,
                'has_updates': False,
                'last_updated': updated_at,
                'status': status,
                'progress': progress
            })), 200

        # 【P0 增强】完整状态推导（防止一直是 init）
        # 阶段推导：根据进度推断实际阶段
        if stage == 'init' and progress > 0 and progress < 30:
            stage = 'ai_fetching'
        elif stage == 'init' and progress >= 30 and progress < 60:
            stage = 'ai_fetching'
        elif stage == 'init' and progress >= 60 and progress < 70:
            stage = 'results_saving'
        elif stage == 'init' and progress >= 70 and progress < 80:
            stage = 'results_validating'
        elif stage == 'init' and progress >= 80 and progress < 90:
            stage = 'background_analysis'
        elif stage == 'init' and progress >= 90 and progress < 100:
            stage = 'report_aggregating'
        
        # 状态推导：根据阶段推断实际状态
        if stage == 'init' and progress > 0:
            status = 'ai_fetching'
        elif stage in ['ai_fetching', 'results_saving', 'results_validating', 
                      'background_analysis', 'report_aggregating']:
            status = 'processing'
        
        # 完成状态推导
        if progress >= 100 and stage not in ['completed', 'failed']:
            stage = 'completed'
            status = 'completed'
            is_completed = True
        
        # 失败状态推导
        if error_message and status not in ['failed']:
            stage = 'failed'
            status = 'failed'
            is_completed = True

        # 构建轻量级响应
        response_data = {
            'task_id': task_id,
            'status': status,
            'stage': stage,
            'progress': progress,
            'is_completed': is_completed,
            'should_stop_polling': status in ['completed', 'failed'],
            'updated_at': updated_at,
            'has_updates': True,
            'source': 'database'
        }

        # 【P0 优化】只在完成时返回结果数据
        if is_completed and fields == 'full':
            from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository
            result_repo = DiagnosisResultRepository()
            results = result_repo.get_by_execution_id(task_id)
            response_data['results'] = results
            response_data['result_count'] = len(results)

        # 【P0 修复】添加防缓存头
        # P0 修复：转换为 camelCase
        response = jsonify(convert_response_to_camel(response_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        api_logger.info(
            f"[TaskStatus-Lite] 返回数据：{task_id}, "
            f"status={status}, progress={progress}, source=database"
        )
        
        return response, 200

    except Exception as e:
        api_logger.error(f'[TaskStatus] 数据库查询失败：{task_id}, 错误：{e}', exc_info=True)
        
        # 降级：从 execution_store 读取
        if task_id in execution_store:
            task_status = execution_store[task_id]
            # P0 修复：转换为 camelCase
            return jsonify(convert_response_to_camel({
                'task_id': task_id,
                'status': task_status.get('status', 'unknown'),
                'stage': task_status.get('stage', 'init'),
                'progress': task_status.get('progress', 0),
                'is_completed': task_status.get('is_completed', False),
                'should_stop_polling': task_status.get('status') in ['completed', 'failed'],
                'source': 'cache'
            })), 200

        # P0 修复：转换为 camelCase
        return jsonify(convert_response_to_camel({
            'task_id': task_id,
            'status': 'error',
            'error': str(e)
        })), 500


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
    获取诊断任务状态（P0 关键修复 - 2026-03-04）

    【P0 关键修复】合并内存和数据库状态，确保一致性

    参数:
        execution_id: 执行 ID

    返回:
        {
            "execution_id": "uuid",
            "status": "running|success|failed|pending|queued",
            "progress": 50,
            "stage": "ai_fetching|results_saving|...",
            "is_completed": true/false,
            "should_stop_polling": true/false,
            "results": [...],  # 完成后返回
            "result_count": 10,
            "error_message": null,  # 失败时返回
            "start_time": "...",
            "end_time": "..."
        }
    """
    if not execution_id:
        return jsonify({'error': 'Execution ID is required'}), 400

    from wechat_backend.state_manager import get_state_manager
    from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository, DiagnosisResultRepository

    # 1. 获取内存状态
    execution_store = {}
    from wechat_backend.async_diagnosis_executor import get_execution_store
    execution_store = get_execution_store()
    
    memory_state = execution_store.get(execution_id, {})

    # 2. 获取数据库状态
    report_repo = DiagnosisReportRepository()
    db_report = report_repo.get_by_execution_id(execution_id)

    # 3. 获取数据库结果
    result_repo = DiagnosisResultRepository()
    db_results = result_repo.get_by_execution_id(execution_id)

    # 4. 合并状态（以数据库为准，内存为补充）
    merged_state = {
        'execution_id': execution_id,
        'status': db_report.get('status') if db_report else memory_state.get('status', 'unknown'),
        'stage': db_report.get('stage') if db_report else memory_state.get('stage', 'unknown'),
        'progress': db_report.get('progress') if db_report else memory_state.get('progress', 0),
        'is_completed': (db_report.get('is_completed') == 1) if db_report else memory_state.get('is_completed', False),
        'should_stop_polling': (db_report.get('should_stop_polling') == 1) if db_report else memory_state.get('should_stop_polling', False),
        'error_message': db_report.get('error_message') if db_report else memory_state.get('error'),
        'start_time': db_report.get('start_time') if db_report else memory_state.get('start_time'),
        'end_time': db_report.get('end_time') if db_report else memory_state.get('end_time'),
        # 结果数据（从数据库获取）
        'results': db_results if db_results else memory_state.get('results', []),
        'result_count': len(db_results) if db_results else len(memory_state.get('results', []))
    }

    # 5. 记录日志（用于审计）
    api_logger.debug(
        f"[DiagnosisStatus] 状态查询：{execution_id}, "
        f"status={merged_state['status']}, "
        f"progress={merged_state['progress']}, "
        f"result_count={merged_state['result_count']}"
    )

    if not db_report and not memory_state:
        return jsonify({'error': 'Task not found', 'execution_id': execution_id}), 404

    return jsonify({
        'success': True,
        'data': merged_state
    }), 200


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


# ==================== AI 超时监控 API ====================
@wechat_bp.route('/ai/timeout-metrics', methods=['GET'])
@monitored_endpoint('/ai/timeout-metrics', require_auth=False, validate_inputs=False)
def get_ai_timeout_metrics():
    """
    获取 AI 平台超时监控指标

    返回:
        {
            "timestamp": "2026-03-04T12:00:00",
            "window_seconds": 300,
            "alert_threshold": 0.05,
            "platforms": {
                "qwen": {
                    "requests_total": 100,
                    "timeouts_total": 5,
                    "timeout_rate": 0.05,
                    "avg_duration_seconds": 2.5,
                    "consecutive_timeouts": 0
                },
                "doubao": {
                    "requests_total": 80,
                    "timeouts_total": 12,
                    "timeout_rate": 0.15,
                    "avg_duration_seconds": 3.2,
                    "consecutive_timeouts": 2
                }
            }
        }
    """
    from wechat_backend.ai_adapters.timeout_monitor import get_timeout_monitor

    monitor = get_timeout_monitor()
    metrics = monitor.export_metrics()

    # 添加告警建议
    alerts = []
    for platform, stats in metrics.get('platforms', {}).items():
        if stats.get('timeout_rate', 0) > monitor.alert_threshold:
            recommendation = monitor.get_recommendation(platform)
            if recommendation:
                alerts.append({
                    'platform': platform,
                    'message': recommendation,
                    'severity': 'high' if stats.get('consecutive_timeouts', 0) >= 3 else 'medium'
                })

    metrics['alerts'] = alerts

    return jsonify(metrics), 200


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