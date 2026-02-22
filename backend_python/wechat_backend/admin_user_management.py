"""
管理后台 - 用户管理模块

功能：
- 用户列表查询
- 用户详情查看
- 用户角色分配
- 用户数据导出
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth, get_current_user_id
from wechat_backend.database import DB_PATH
import sqlite3
import json

# 创建用户管理蓝图
user_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')


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


@user_bp.route('', methods=['GET'])
@require_auth
@require_admin
def get_all_users():
    """获取所有用户列表"""
    api_logger.info(f"User list accessed by: {get_current_user_id()}")

    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        offset = (page - 1) * page_size

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取用户列表
        cursor.execute('''
            SELECT * FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        users = [dict(row) for row in cursor.fetchall()]

        # 获取总数
        cursor.execute('SELECT COUNT(*) FROM users')
        total = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'users': users,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })

    except Exception as e:
        api_logger.error(f"获取用户列表失败：{e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/<user_id>', methods=['GET'])
@require_auth
@require_admin
def get_user_detail(user_id):
    """获取用户详情"""
    api_logger.info(f"User detail accessed: {user_id}")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取用户信息
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = dict(cursor.fetchone()) if cursor.fetchone() else None

        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        # 获取用户角色
        cursor.execute('''
            SELECT r.* FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ?
        ''', (user_id,))
        user['roles'] = [dict(row) for row in cursor.fetchall()]

        # 获取用户测试记录数
        cursor.execute('SELECT COUNT(*) FROM test_records WHERE user_openid = ?', (user.get('openid'),))
        user['test_count'] = cursor.fetchone()[0]

        conn.close()

        return jsonify({'user': user})

    except Exception as e:
        api_logger.error(f"获取用户详情失败：{e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/<user_id>/role', methods=['PUT'])
@require_auth
@require_admin
def assign_user_role(user_id):
    """分配用户角色"""
    api_logger.info(f"Assigning role to user: {user_id}")

    try:
        data = request.get_json()
        role_id = data.get('role_id')

        if not role_id:
            return jsonify({'error': 'role_id is required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 检查角色是否存在
        cursor.execute('SELECT * FROM roles WHERE id = ?', (role_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Role not found'}), 404

        # 删除现有角色
        cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))

        # 添加新角色
        cursor.execute('''
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            VALUES (?, ?, ?)
        ''', (user_id, role_id, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        api_logger.info(f"Role {role_id} assigned to user {user_id}")
        return jsonify({'message': 'Role assigned successfully'})

    except Exception as e:
        api_logger.error(f"分配角色失败：{e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/export', methods=['GET'])
@require_auth
@require_admin
def export_users():
    """导出用户数据"""
    api_logger.info(f"User data exported by: {get_current_user_id()}")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = [dict(row) for row in cursor.fetchall()]

        conn.close()

        # 转换为 CSV 格式
        if users:
            headers = list(users[0].keys())
            csv_lines = [','.join(headers)]
            for user in users:
                csv_lines.append(','.join(str(user.get(h, '')) for h in headers))

            csv_content = '\n'.join(csv_lines)

            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename=users_{datetime.now().strftime("%Y%m%d")}.csv'}
            )
        else:
            return jsonify({'error': 'No users to export'}), 404

    except Exception as e:
        api_logger.error(f"导出用户数据失败：{e}")
        return jsonify({'error': str(e)}), 500


from flask import Response


def init_user_management_routes(app):
    """注册用户管理路由"""
    app.register_blueprint(user_bp)
    api_logger.info("User management routes initialized")
