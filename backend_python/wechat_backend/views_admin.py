#!/usr/bin/env python3
"""
管理员后台 API 端点
提供用户管理、权限分配、系统监控、日志查看等功能
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth, get_current_user_id
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery, sql_protector
import sqlite3
import json
import os

# 创建管理员蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理员角色检查
def require_admin(f):
    """装饰器：要求管理员权限"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        
        # 检查是否为管理员（从数据库或配置检查）
        if not is_admin_user(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def is_admin_user(user_id):
    """检查用户是否为管理员"""
    if not user_id or user_id == 'anonymous':
        return False
    
    # 从数据库检查用户角色
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查用户是否有 admin 角色
        cursor.execute('''
            SELECT r.role_name FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ? AND r.role_name = 'admin'
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception:
        return False


# ============================================================================
# 仪表盘 API
# ============================================================================

@admin_bp.route('/dashboard', methods=['GET'])
@require_auth
@require_admin
def admin_dashboard():
    """获取管理员仪表盘数据"""
    api_logger.info(f"Admin dashboard accessed by user: {get_current_user_id()}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 用户统计
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # 今日新增用户
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?', (today,))
        new_users_today = cursor.fetchone()[0]
        
        # 测试记录统计
        cursor.execute('SELECT COUNT(*) FROM test_records')
        total_tests = cursor.fetchone()[0]
        
        # 今日测试数
        cursor.execute('SELECT COUNT(*) FROM test_records WHERE DATE(test_date) = ?', (today,))
        tests_today = cursor.fetchone()[0]
        
        # 任务状态统计
        cursor.execute('SELECT stage, COUNT(*) FROM task_statuses WHERE is_completed = 0 GROUP BY stage')
        pending_tasks = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 最近活动
        cursor.execute('''
            SELECT user_id, brand_name, test_date, overall_score 
            FROM test_records 
            ORDER BY test_date DESC 
            LIMIT 10
        ''')
        recent_activities = [
            {
                'user_id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'overall_score': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'overview': {
                    'total_users': total_users,
                    'new_users_today': new_users_today,
                    'total_tests': total_tests,
                    'tests_today': tests_today
                },
                'pending_tasks': pending_tasks,
                'recent_activities': recent_activities,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500


# ============================================================================
# 用户管理 API
# ============================================================================

@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_admin
def get_all_users():
    """获取所有用户列表"""
    api_logger.info(f"Get all users by admin: {get_current_user_id()}")
    
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        search = request.args.get('search', '')
        
        offset = (page - 1) * page_size
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 构建查询
        base_query = 'SELECT id, phone, nickname, avatar_url, created_at FROM users'
        count_query = 'SELECT COUNT(*) FROM users'
        
        if search:
            search_pattern = f'%{search}%'
            base_query += ' WHERE phone LIKE ? OR nickname LIKE ?'
            count_query += ' WHERE phone LIKE ? OR nickname LIKE ?'
            params = (search_pattern, search_pattern)
        else:
            params = ()
        
        # 获取总数
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # 获取用户列表
        base_query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        cursor.execute(base_query, params + (page_size, offset))
        
        users = [
            {
                'id': row[0],
                'phone': row[1],
                'nickname': row[2] or '未设置',
                'avatar_url': row[3] or '',
                'created_at': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'users': users,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to get users'}), 500


@admin_bp.route('/users/<user_id>', methods=['GET'])
@require_auth
@require_admin
def get_user_detail(user_id):
    """获取用户详情"""
    api_logger.info(f"Get user detail: {user_id}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取用户基本信息
        cursor.execute('''
            SELECT id, phone, nickname, avatar_url, created_at, updated_at
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        user = {
            'id': row[0],
            'phone': row[1],
            'nickname': row[2] or '未设置',
            'avatar_url': row[3] or '',
            'created_at': row[4],
            'updated_at': row[5]
        }
        
        # 获取用户角色
        cursor.execute('''
            SELECT r.role_name FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ?
        ''', (user_id,))
        
        user['roles'] = [row[0] for row in cursor.fetchall()]
        
        # 获取用户测试统计
        cursor.execute('''
            SELECT COUNT(*), AVG(overall_score), MAX(test_date)
            FROM test_records
            WHERE user_id = ?
        ''', (user_id,))
        
        stats_row = cursor.fetchone()
        user['stats'] = {
            'total_tests': stats_row[0] or 0,
            'avg_score': round(stats_row[1] or 0, 2),
            'last_test_date': stats_row[2]
        }
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': user
        })
        
    except Exception as e:
        api_logger.error(f"Error getting user detail: {e}")
        return jsonify({'error': 'Failed to get user detail'}), 500


@admin_bp.route('/users/<user_id>/roles', methods=['POST'])
@require_auth
@require_admin
def assign_user_role(user_id):
    """分配用户角色"""
    api_logger.info(f"Assign role to user: {user_id}")
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    role_name = data.get('role')
    action = data.get('action')  # 'grant' or 'revoke'
    
    if not role_name or not action:
        return jsonify({'error': 'role and action are required'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取角色 ID
        cursor.execute('SELECT id FROM roles WHERE role_name = ?', (role_name,))
        role_row = cursor.fetchone()
        
        if not role_row:
            conn.close()
            return jsonify({'error': 'Role not found'}), 404
        
        role_id = role_row[0]
        
        if action == 'grant':
            # 授予角色
            try:
                cursor.execute('''
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (?, ?)
                ''', (user_id, role_id))
                conn.commit()
                message = f'Role {role_name} granted to user {user_id}'
            except sqlite3.IntegrityError:
                message = f'User already has role {role_name}'
        elif action == 'revoke':
            # 撤销角色
            cursor.execute('''
                DELETE FROM user_roles
                WHERE user_id = ? AND role_id = ?
            ''', (user_id, role_id))
            conn.commit()
            message = f'Role {role_name} revoked from user {user_id}'
        else:
            conn.close()
            return jsonify({'error': 'Invalid action'}), 400
        
        conn.close()
        
        api_logger.info(message)
        
        return jsonify({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        api_logger.error(f"Error assigning role: {e}")
        return jsonify({'error': 'Failed to assign role'}), 500


# ============================================================================
# 系统监控 API
# ============================================================================

@admin_bp.route('/system/status', methods=['GET'])
@require_auth
@require_admin
def system_status():
    """获取系统状态"""
    api_logger.info(f"System status checked by admin: {get_current_user_id()}")
    
    try:
        import psutil
        import platform
        
        # 系统信息
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version()
        }
        
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        return jsonify({
            'status': 'success',
            'data': {
                'system': system_info,
                'resources': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_total_gb': round(memory.total / (1024**3), 2),
                    'memory_used_gb': round(memory.used / (1024**3), 2),
                    'disk_percent': disk_percent,
                    'disk_total_gb': round(disk.total / (1024**3), 2),
                    'disk_used_gb': round(disk.used / (1024**3), 2)
                },
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except ImportError:
        # psutil not installed, return basic info
        return jsonify({
            'status': 'success',
            'data': {
                'system': {'platform': 'Unknown'},
                'resources': {},
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        api_logger.error(f"Error getting system status: {e}")
        return jsonify({'error': 'Failed to get system status'}), 500


@admin_bp.route('/system/logs', methods=['GET'])
@require_auth
@require_admin
def get_system_logs():
    """获取系统日志"""
    api_logger.info(f"Get system logs by admin: {get_current_user_id()}")
    
    try:
        # 获取查询参数
        level = request.args.get('level', 'ERROR')
        lines = request.args.get('lines', 100, type=int)
        
        log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                'status': 'success',
                'data': {
                    'logs': [],
                    'message': 'No log file found'
                }
            })
        
        # 读取日志文件
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
            # 过滤指定级别的日志
            for line in reversed(all_lines[-lines*5:]):  # 多读一些以便过滤
                if level in line or level == 'ALL':
                    logs.append(line.strip())
                    if len(logs) >= lines:
                        break
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': logs,
                'level': level,
                'count': len(logs)
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting logs: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500


# ============================================================================
# 测试记录管理 API
# ============================================================================

@admin_bp.route('/tests', methods=['GET'])
@require_auth
@require_admin
def get_all_tests():
    """获取所有测试记录"""
    api_logger.info(f"Get all tests by admin: {get_current_user_id()}")
    
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        brand_name = request.args.get('brand_name', '')
        
        offset = (page - 1) * page_size
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 构建查询
        base_query = '''
            SELECT tr.id, tr.user_id, tr.brand_name, tr.test_date, 
                   tr.ai_models_used, tr.overall_score, u.phone
            FROM test_records tr
            LEFT JOIN users u ON tr.user_id = u.id
        '''
        count_query = 'SELECT COUNT(*) FROM test_records tr'
        
        params = []
        if brand_name:
            search_pattern = f'%{brand_name}%'
            base_query += ' WHERE tr.brand_name LIKE ?'
            count_query += ' WHERE tr.brand_name LIKE ?'
            params.append(search_pattern)
        
        # 获取总数
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # 获取测试列表
        base_query += ' ORDER BY tr.test_date DESC LIMIT ? OFFSET ?'
        cursor.execute(base_query, params + [page_size, offset])
        
        tests = [
            {
                'id': row[0],
                'user_id': row[1],
                'user_phone': row[6],
                'brand_name': row[2],
                'test_date': row[3],
                'ai_models_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'tests': tests,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting tests: {e}")
        return jsonify({'error': 'Failed to get tests'}), 500


# ============================================================================
# AI 平台配置管理 API
# ============================================================================

@admin_bp.route('/platforms', methods=['GET'])
@require_auth
@require_admin
def get_ai_platforms():
    """获取 AI 平台配置状态"""
    api_logger.info(f"Get AI platforms by admin: {get_current_user_id()}")
    
    try:
        from config import Config
        
        # 检查各平台配置
        platforms = [
            {'name': 'DeepSeek', 'configured': bool(Config.DEEPSEEK_API_KEY)},
            {'name': 'Qwen', 'configured': bool(Config.QWEN_API_KEY)},
            {'name': 'Doubao', 'configured': bool(Config.DOUBAO_API_KEY)},
            {'name': 'Zhipu', 'configured': bool(Config.ZHIPU_API_KEY)},
            {'name': 'ChatGPT', 'configured': bool(Config.CHATGPT_API_KEY)},
            {'name': 'Gemini', 'configured': bool(Config.GEMINI_API_KEY)}
        ]
        
        return jsonify({
            'status': 'success',
            'data': {
                'platforms': platforms,
                'total': len(platforms),
                'configured': sum(1 for p in platforms if p['configured'])
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting platforms: {e}")
        return jsonify({'error': 'Failed to get platforms'}), 500


# ============================================================================
# 批量操作 API
# ============================================================================

@admin_bp.route('/users/batch-action', methods=['POST'])
@require_auth
@require_admin
def batch_user_action():
    """
    批量操作用户
    
    Request body:
    - user_ids: 用户 ID 列表
    - action: 操作类型 (grant_admin/revoke_admin/export_data)
    """
    api_logger.info(f"Batch user action by admin: {get_current_user_id()}")
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    user_ids = data.get('user_ids', [])
    action = data.get('action')
    
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'error': 'user_ids is required and must be a list'}), 400
    
    if not action:
        return jsonify({'error': 'action is required'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        processed = 0
        failed = 0
        errors = []
        
        if action == 'grant_admin':
            # 批量授予管理员权限
            cursor.execute('SELECT id FROM roles WHERE role_name = ?', ('admin',))
            role_row = cursor.fetchone()
            
            if not role_row:
                conn.close()
                return jsonify({'error': 'Admin role not found'}), 404
            
            role_id = role_row[0]
            
            for user_id in user_ids:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_roles (user_id, role_id)
                        VALUES (?, ?)
                    ''', (user_id, role_id))
                    processed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f'User {user_id}: {str(e)}')
            
            conn.commit()
            message = f'Granted admin role to {processed} users'
            
        elif action == 'revoke_admin':
            # 批量撤销管理员权限
            cursor.execute('SELECT id FROM roles WHERE role_name = ?', ('admin',))
            role_row = cursor.fetchone()
            
            if not role_row:
                conn.close()
                return jsonify({'error': 'Admin role not found'}), 404
            
            role_id = role_row[0]
            
            for user_id in user_ids:
                try:
                    cursor.execute('''
                        DELETE FROM user_roles
                        WHERE user_id = ? AND role_id = ?
                    ''', (user_id, role_id))
                    processed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f'User {user_id}: {str(e)}')
            
            conn.commit()
            message = f'Revoked admin role from {processed} users'
            
        elif action == 'export_data':
            # 批量导出用户数据
            export_data = []
            
            for user_id in user_ids:
                try:
                    cursor.execute('''
                        SELECT id, phone, nickname, avatar_url, created_at
                        FROM users
                        WHERE id = ?
                    ''', (user_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        export_data.append({
                            'id': row[0],
                            'phone': row[1],
                            'nickname': row[2] or '',
                            'avatar_url': row[3] or '',
                            'created_at': row[4]
                        })
                        processed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f'User {user_id}: {str(e)}')
            
            conn.close()
            
            # 返回导出数据
            return jsonify({
                'status': 'success',
                'message': f'Exported {processed} users',
                'data': {
                    'exported_users': export_data,
                    'processed': processed,
                    'failed': failed
                }
            })
            
        else:
            conn.close()
            return jsonify({'error': f'Unknown action: {action}'}), 400
        
        conn.close()
        
        api_logger.info(f"Batch action completed: {message}, failed: {failed}")
        
        return jsonify({
            'status': 'success',
            'message': message,
            'processed': processed,
            'failed': failed,
            'errors': errors[:10]  # 只返回前 10 个错误
        })
        
    except Exception as e:
        api_logger.error(f"Error in batch user action: {e}")
        return jsonify({'error': 'Failed to perform batch action'}), 500


@admin_bp.route('/tests/batch-delete', methods=['POST'])
@require_auth
@require_admin
def batch_delete_tests():
    """
    批量删除测试记录
    
    Request body:
    - test_ids: 测试记录 ID 列表
    """
    api_logger.info(f"Batch delete tests by admin: {get_current_user_id()}")
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    test_ids = data.get('test_ids', [])
    
    if not test_ids or not isinstance(test_ids, list):
        return jsonify({'error': 'test_ids is required and must be a list'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 使用占位符构建 IN 子句
        placeholders = ','.join(['?' for _ in test_ids])
        
        # 删除测试记录
        cursor.execute(f'''
            DELETE FROM test_records
            WHERE id IN ({placeholders})
        ''', test_ids)
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        api_logger.info(f"Batch deleted {deleted_count} test records")
        
        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted_count} test records',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        api_logger.error(f"Error in batch delete tests: {e}")
        return jsonify({'error': 'Failed to delete test records'}), 500


@admin_bp.route('/users/batch-notification', methods=['POST'])
@require_auth
@require_admin
def batch_send_notification():
    """
    批量发送通知
    
    Request body:
    - user_ids: 用户 ID 列表（可选，为空则发送给所有用户）
    - title: 通知标题
    - message: 通知内容
    - type: 通知类型 (system/maintenance/promotion)
    """
    api_logger.info(f"Batch send notification by admin: {get_current_user_id()}")
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    user_ids = data.get('user_ids', [])
    title = data.get('title', '')
    message = data.get('message', '')
    notification_type = data.get('type', 'system')
    
    if not title or not message:
        return jsonify({'error': 'title and message are required'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取目标用户
        if user_ids:
            placeholders = ','.join(['?' for _ in user_ids])
            cursor.execute(f'SELECT id FROM users WHERE id IN ({placeholders})', user_ids)
        else:
            # 发送给所有用户
            cursor.execute('SELECT id FROM users')
        
        target_users = [row[0] for row in cursor.fetchall()]
        
        # 创建通知记录（简化版，实际应使用通知表）
        notification_record = {
            'title': title,
            'message': message,
            'type': notification_type,
            'sent_at': datetime.now().isoformat(),
            'sent_by': get_current_user_id(),
            'target_users': len(target_users)
        }
        
        # 保存到通知历史表（如果存在）
        try:
            cursor.execute('''
                INSERT INTO notifications (title, message, type, sent_at, sent_by, target_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, message, notification_type, datetime.now(), get_current_user_id(), len(target_users)))
            conn.commit()
        except sqlite3.OperationalError:
            # 表不存在，跳过
            pass
        
        conn.close()
        
        api_logger.info(f"Batch notification sent to {len(target_users)} users")
        
        # 注意：这里只是创建通知记录，实际推送需要集成微信订阅消息
        return jsonify({
            'status': 'success',
            'message': f'Notification created for {len(target_users)} users',
            'notification': notification_record,
            'target_count': len(target_users)
        })
        
    except Exception as e:
        api_logger.error(f"Error in batch send notification: {e}")
        return jsonify({'error': 'Failed to send notification'}), 500


@admin_bp.route('/export/users', methods=['GET'])
@require_auth
@require_admin
def export_users():
    """
    导出用户数据（CSV 格式）
    
    Query Parameters:
    - format: 导出格式 (csv/json，默认 csv)
    """
    api_logger.info(f"Export users by admin: {get_current_user_id()}")
    
    try:
        format_type = request.args.get('format', 'csv')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, phone, nickname, avatar_url, created_at
            FROM users
            ORDER BY created_at DESC
        ''')
        
        users = [
            {
                'id': row[0],
                'phone': row[1],
                'nickname': row[2] or '',
                'avatar_url': row[3] or '',
                'created_at': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        if format_type == 'json':
            return jsonify({
                'status': 'success',
                'data': users,
                'total': len(users)
            })
        else:
            # CSV 格式
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow(['ID', '手机号', '昵称', '头像', '注册时间'])
            
            # 写入数据
            for user in users:
                writer.writerow([
                    user['id'],
                    user['phone'],
                    user['nickname'],
                    user['avatar_url'],
                    user['created_at']
                ])
            
            csv_data = output.getvalue()
            output.close()
            
            from flask import Response
            return Response(
                csv_data.encode('utf-8-sig'),  # UTF-8 with BOM for Excel
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=users_{datetime.now().strftime("%Y%m%d")}.csv'
                }
            )
        
    except Exception as e:
        api_logger.error(f"Error exporting users: {e}")
        return jsonify({'error': 'Failed to export users'}), 500


def init_admin_routes(app):
    """初始化管理员路由"""
    app.register_blueprint(admin_bp)
    api_logger.info("Admin routes initialized")
