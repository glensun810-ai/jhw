"""
用户相关视图模块
包含登录、注册、用户资料等路由
"""
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

# Create a blueprint
wechat_bp = Blueprint('wechat', __name__)

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

# 用户认证装饰器导入
from wechat_backend.security.auth import jwt_manager
from wechat_backend.app import APP_ID, APP_SECRET
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

