"""
诊断编排器视图模块 - Phase 5 重构版

【P0 重构 - 阶段五】使用 DiagnosisOrchestrator 统一编排诊断流程

核心原则：
1. 顺序执行 - API 响应保存 → 统计分析 → 结果聚合 → 报告生成
2. 状态一致 - 内存和数据库原子性更新
3. 完整持久化 - 所有结果必须完整保存后才能进入下一环节
4. 统一调度 - 由诊断编排器协调所有子流程

架构师签字：___________
日期：2026-03-02
版本：2.0.0 (阶段五重构版)
"""

from flask import request, jsonify
from threading import Thread
from datetime import datetime
import uuid
import re

from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import get_current_user_id
from wechat_backend.security.input_validation import validate_safe_text
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import validate_model_region_consistency
from wechat_backend.analytics.monetization_service import UserLevel
from wechat_backend.v2.services.timeout_service import TimeoutManager
from wechat_backend.services.diagnosis_orchestrator import DiagnosisOrchestrator
from wechat_backend.error_handler import handle_api_exceptions
from wechat_backend.security.auth_enhanced import require_auth_optional
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.monitoring.monitoring_decorator import monitored_endpoint

from . import wechat_bp

# P0 修复：导入字段转换器
# P0 修复：字段转换器导入（兼容不同执行环境）
try:
    from utils.field_converter import convert_response_to_camel
except ImportError:
    try:
        from backend_python.utils.field_converter import convert_response_to_camel
    except ImportError:
        def convert_response_to_camel(data):
            return data

# Global store for execution progress
execution_store = {}


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

    # ========== 输入验证和净化 ==========
    try:
        # 验证品牌列表
        if 'brand_list' not in data:
            return jsonify({
                "status": "error",
                "error": 'Missing brand_list in request data',
                "code": 400,
                'received_fields': list(data.keys())
            }), 400
        
        if not isinstance(data['brand_list'], list):
            return jsonify({
                "status": "error",
                "error": 'brand_list must be a list',
                "code": 400,
                'received': type(data['brand_list']).__name__,
                'received_value': data['brand_list']
            }), 400
        
        brand_list = data['brand_list']
        if not brand_list:
            return jsonify({
                "status": "error",
                "error": 'brand_list cannot be empty',
                "code": 400,
                'received': brand_list
            }), 400

        # 验证品牌名称安全性
        for brand in brand_list:
            if not isinstance(brand, str):
                return jsonify({
                    "status": "error",
                    "error": f'Each brand in brand_list must be a string, got {type(brand)}',
                    "code": 400,
                    'problematic_value': brand
                }), 400
            if not validate_safe_text(brand, max_length=100):
                return jsonify({
                    "status": "error",
                    "error": f'Invalid brand name: {brand}',
                    "code": 400
                }), 400

        api_logger.info(f"[Sprint 1] 接收到品牌列表：{brand_list}")

        # 验证模型列表
        if 'selectedModels' not in data:
            return jsonify({
                "status": "error",
                "error": 'Missing selectedModels in request data',
                "code": 400,
                'received_fields': list(data.keys())
            }), 400
        
        if not isinstance(data['selectedModels'], list):
            return jsonify({
                "status": "error",
                "error": 'selectedModels must be a list',
                "code": 400,
                'received': type(data['selectedModels']).__name__,
                'received_value': data['selectedModels']
            }), 400
        
        selected_models = data['selectedModels']
        if not selected_models:
            return jsonify({
                "status": "error",
                "error": 'At least one AI model must be selected',
                "code": 400,
                'received': selected_models
            }), 400

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

        original_model_names = [
            model.get('name', model) if isinstance(model, dict) else model
            for model in data['selectedModels']
        ]
        converted_model_names = [model['name'] for model in selected_models]
        api_logger.info(
            f"[Sprint 1] 转换后的模型列表：{converted_model_names} "
            f"(原始：{original_model_names})"
        )

        if not selected_models:
            return jsonify({
                "status": "error",
                "error": 'No valid AI models found after parsing',
                "code": 400
            }), 400

        # 验证和解析问题列表
        custom_questions = []
        if 'custom_question' in data:
            # 优先处理新的 custom_question 字段（字符串）
            if not isinstance(data['custom_question'], str):
                return jsonify({
                    "status": "error",
                    "error": 'custom_question must be a string',
                    "code": 400,
                    'received': type(data['custom_question']).__name__,
                    'received_value': data['custom_question']
                }), 400

            # 智能分割多个问题
            question_text = data['custom_question'].strip()
            if question_text:
                raw_questions = re.split(r'[？?.\n\s]+', question_text)
                custom_questions = [
                    q.strip() + ('?' if not q.strip().endswith('?') else '')
                    for q in raw_questions if q.strip()
                ]
                api_logger.info(
                    f"[QuestionSplit] 分割后问题数：{len(custom_questions)}"
                )
        elif 'customQuestions' in data:
            # 保持对旧格式的兼容（数组格式）
            if not isinstance(data['customQuestions'], list):
                return jsonify({
                    "status": "error",
                    "error": 'customQuestions must be a list',
                    "code": 400,
                    'received': type(data['customQuestions']).__name__,
                    'received_value': data['customQuestions']
                }), 400
            custom_questions = data['customQuestions']

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

    # 初始化 execution_store
    execution_store[execution_id] = {
        'progress': 0,
        'completed': 0,
        'total': 0,
        'status': 'initializing',
        'stage': 'init',
        'results': [],
        'start_time': datetime.now().isoformat()
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

            # 创建数据库初始记录
            try:
                from wechat_backend.diagnosis_report_service import get_report_service
                service = get_report_service()
                config = {
                    'brand_name': brand_list[0],
                    'competitor_brands': brand_list[1:] if len(brand_list) > 1 else [],
                    'selected_models': selected_models,
                    'custom_questions': custom_questions
                }
                report_id = service.create_report(execution_id, user_id or 'anonymous', config)
                service.report_repo.update_status(
                    execution_id=execution_id,
                    status='initializing',
                    progress=0,
                    stage='init',
                    is_completed=False
                )
                api_logger.info(
                    f"[Orchestrator] ✅ 初始数据库记录已创建：{execution_id}, "
                    f"report_id={report_id}"
                )
            except Exception as db_init_err:
                api_logger.error(f"[Orchestrator] ⚠️ 创建初始记录失败：{db_init_err}")
                report_id = None

            # 使用诊断编排器执行完整诊断流程
            import asyncio

            def run_async_in_thread(coro):
                """在线程中安全运行异步代码"""
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            # 创建并执行诊断编排器
            orchestrator = DiagnosisOrchestrator(execution_id, execution_store)
            
            result = run_async_in_thread(
                orchestrator.execute_diagnosis(
                    user_id=user_id or 'anonymous',
                    brand_list=brand_list,
                    selected_models=selected_models,
                    custom_questions=custom_questions,
                    user_openid=user_openid,
                    user_level=user_level.value
                )
            )

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
