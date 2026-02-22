"""
管理后台 - 系统管理模块

功能：
- 系统仪表盘
- 系统状态监控
- 日志查看
- 系统配置
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth, get_current_user_id
from wechat_backend.database import DB_PATH
from wechat_backend.database_connection_pool import get_db_pool_metrics
import sqlite3
import os
from pathlib import Path

# 创建系统管理蓝图
system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/system')


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


@system_bp.route('/dashboard', methods=['GET'])
@require_auth
@require_admin
def admin_dashboard():
    """获取管理员仪表盘数据"""
    api_logger.info(f"Admin dashboard accessed by: {get_current_user_id()}")

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
        cursor.execute('''
            SELECT stage, COUNT(*) FROM task_statuses
            WHERE is_completed = 0
            GROUP BY stage
        ''')
        pending_tasks = {row[0]: row[1] for row in cursor.fetchall()}

        # 最近活动
        cursor.execute('''
            SELECT * FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        recent_activity = [
            {
                'id': row[0],
                'user_id': row[1],
                'action': row[2],
                'timestamp': row[6]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        # 数据库连接池指标
        pool_metrics = get_db_pool_metrics()

        return jsonify({
            'users': {
                'total': total_users,
                'new_today': new_users_today
            },
            'tests': {
                'total': total_tests,
                'today': tests_today
            },
            'tasks': {
                'pending': pending_tasks
            },
            'recent_activity': recent_activity,
            'database': {
                'pool_metrics': pool_metrics
            }
        })

    except Exception as e:
        api_logger.error(f"获取仪表盘数据失败：{e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/status', methods=['GET'])
@require_auth
@require_admin
def system_status():
    """获取系统状态"""
    api_logger.info(f"System status accessed by: {get_current_user_id()}")

    try:
        # 数据库状态
        db_exists = os.path.exists(DB_PATH)
        db_size = os.path.getsize(DB_PATH) if db_exists else 0

        # 连接池状态
        pool_metrics = get_db_pool_metrics()

        # 日志文件状态
        log_dir = Path(__file__).parent.parent / 'logs'
        log_files = list(log_dir.glob('*.log')) if log_dir.exists() else []

        return jsonify({
            'database': {
                'exists': db_exists,
                'size_bytes': db_size,
                'path': str(DB_PATH)
            },
            'connection_pool': pool_metrics,
            'logs': {
                'files': [f.name for f in log_files],
                'count': len(log_files)
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        api_logger.error(f"获取系统状态失败：{e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/logs', methods=['GET'])
@require_auth
@require_admin
def get_system_logs():
    """获取系统日志"""
    api_logger.info(f"System logs accessed by: {get_current_user_id()}")

    try:
        lines = request.args.get('lines', 100, type=int)
        log_file = request.args.get('file', 'app.log')

        log_path = Path(__file__).parent.parent / 'logs' / log_file

        if not log_path.exists():
            return jsonify({'error': 'Log file not found'}), 404

        # 读取最后 N 行
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return jsonify({
            'logs': ''.join(last_lines),
            'file': log_file,
            'lines': len(last_lines)
        })

    except Exception as e:
        api_logger.error(f"获取日志失败：{e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/config', methods=['GET'])
@require_auth
@require_admin
def get_system_config():
    """获取系统配置"""
    api_logger.info(f"System config accessed by: {get_current_user_id()}")

    try:
        from wechat_backend.config import Config

        # 只返回非敏感配置
        config = {
            'app_name': getattr(Config, 'APP_NAME', 'GEO Brand Diagnosis'),
            'version': '2.0',
            'debug': getattr(Config, 'DEBUG', False),
            'encryption_enabled': getattr(Config, 'ENCRYPTION_ENABLED', False)
        }

        return jsonify({'config': config})

    except Exception as e:
        api_logger.error(f"获取配置失败：{e}")
        return jsonify({'error': str(e)}), 500


def init_system_management_routes(app):
    """注册系统管理路由"""
    app.register_blueprint(system_bp)
    api_logger.info("System management routes initialized")
