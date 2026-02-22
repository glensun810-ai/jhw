"""
管理后台 - 测试管理模块

功能：
- 测试记录查询
- 批量删除测试
- AI 平台管理
- 批量操作
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth, get_current_user_id
from wechat_backend.database import DB_PATH
import sqlite3
import json

# 创建测试管理蓝图
test_bp = Blueprint('admin_tests', __name__, url_prefix='/admin/tests')


def is_admin_user(user_id):
    """检查用户是否为管理员"""
    if not user_id or user_id == 'anonymous':
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
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


def require_admin(f):
    """装饰器：要求管理员权限"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not is_admin_user(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)

    return decorated_function


@test_bp.route('', methods=['GET'])
@require_auth
@require_admin
def get_all_tests():
    """获取所有测试记录"""
    api_logger.info(f"Test records accessed by: {get_current_user_id()}")

    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        offset = (page - 1) * page_size

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM test_records
            ORDER BY test_date DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        tests = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT COUNT(*) FROM test_records')
        total = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'tests': tests,
            'total': total,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        api_logger.error(f"获取测试记录失败：{e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/ai-platforms', methods=['GET'])
@require_auth
@require_admin
def get_ai_platforms():
    """获取 AI 平台配置"""
    api_logger.info(f"AI platforms accessed by: {get_current_user_id()}")

    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory

        platforms = []
        for platform_type, adapter_class in AIAdapterFactory._adapters.items():
            platforms.append({
                'name': platform_type.value,
                'class': adapter_class.__name__,
                'configured': True
            })

        return jsonify({'platforms': platforms})

    except Exception as e:
        api_logger.error(f"获取 AI 平台失败：{e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/batch/delete', methods=['POST'])
@require_auth
@require_admin
def batch_delete_tests():
    """批量删除测试记录"""
    api_logger.info(f"Batch delete tests by: {get_current_user_id()}")

    try:
        data = request.get_json()
        test_ids = data.get('test_ids', [])

        if not test_ids:
            return jsonify({'error': 'test_ids is required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(test_ids))
        cursor.execute(f'DELETE FROM test_records WHERE id IN ({placeholders})', test_ids)
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        api_logger.info(f"Deleted {deleted_count} test records")
        return jsonify({
            'message': f'Deleted {deleted_count} test records',
            'deleted_count': deleted_count
        })

    except Exception as e:
        api_logger.error(f"批量删除失败：{e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/batch/action', methods=['POST'])
@require_auth
@require_admin
def batch_user_action():
    """批量用户操作"""
    api_logger.info(f"Batch user action by: {get_current_user_id()}")

    try:
        data = request.get_json()
        action = data.get('action')
        user_ids = data.get('user_ids', [])

        if not action or not user_ids:
            return jsonify({'error': 'action and user_ids are required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if action == 'activate':
            cursor.execute('''
                UPDATE users SET status = 'active' WHERE id IN ({})
            '''.format(','.join('?' * len(user_ids))), user_ids)

        elif action == 'deactivate':
            cursor.execute('''
                UPDATE users SET status = 'inactive' WHERE id IN ({})
            '''.format(','.join('?' * len(user_ids))), user_ids)

        elif action == 'delete':
            cursor.execute('DELETE FROM users WHERE id IN ({})'.format(','.join('?' * len(user_ids))), user_ids)

        else:
            conn.close()
            return jsonify({'error': 'Invalid action'}), 400

        affected_count = cursor.rowcount
        conn.commit()
        conn.close()

        api_logger.info(f"Batch action '{action}' affected {affected_count} users")
        return jsonify({
            'message': f'Affected {affected_count} users',
            'affected_count': affected_count
        })

    except Exception as e:
        api_logger.error(f"批量操作失败：{e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/batch/notify', methods=['POST'])
@require_auth
@require_admin
def batch_send_notification():
    """批量发送通知"""
    api_logger.info(f"Batch notification by: {get_current_user_id()}")

    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        message = data.get('message', '')
        notification_type = data.get('type', 'system')

        if not user_ids or not message:
            return jsonify({'error': 'user_ids and message are required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 保存通知记录
        for user_id in user_ids:
            cursor.execute('''
                INSERT INTO notifications (user_id, message, type, created_at, is_read)
                VALUES (?, ?, ?, ?, 0)
            ''', (user_id, message, notification_type, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        api_logger.info(f"Sent notifications to {len(user_ids)} users")
        return jsonify({
            'message': f'Sent to {len(user_ids)} users',
            'sent_count': len(user_ids)
        })

    except Exception as e:
        api_logger.error(f"批量通知失败：{e}")
        return jsonify({'error': str(e)}), 500


def init_test_management_routes(app):
    """注册测试管理路由"""
    app.register_blueprint(test_bp)
    api_logger.info("Test management routes initialized")
