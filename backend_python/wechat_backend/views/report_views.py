"""
Report 相关视图模块
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

