"""
Analytics 相关视图模块
"""

# 从__init__.py 导入共享的蓝图实例
from . import wechat_bp


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

from legacy_config import Config
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

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

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

