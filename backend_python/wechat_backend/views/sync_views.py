"""
Sync 相关视图模块
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

