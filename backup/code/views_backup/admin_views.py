"""
Admin 相关视图模块
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
            from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result
            from wechat_backend.database_core import get_connection  # 添加这一行
            import gzip, json  # 添加这一行
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
