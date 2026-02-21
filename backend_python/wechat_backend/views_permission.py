"""
权限管理 API
P1 级空缺修复 - 后端支持

功能:
1. 获取用户权限列表
2. 授予用户权限
3. 撤销用户权限
4. 获取角色列表
5. 创建/删除角色

使用示例:
    GET /api/user/permissions?user_id=xxx
    POST /api/user/permission/grant
    DELETE /api/user/permission/revoke
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import sqlite3
from wechat_backend.logging_config import api_logger
from wechat_backend.database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery
from wechat_backend.security.input_validator import validate_string

# 创建 Blueprint
permission_bp = Blueprint('permission', __name__)


# =============================================================================
# 数据模型
# =============================================================================

class PermissionModel:
    """权限数据模型"""
    
    @staticmethod
    def get_user_permissions(user_id: str) -> Dict[str, Any]:
        """获取用户权限列表"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 获取用户角色
        roles_result = safe_query.execute_query('''
            SELECT r.id, r.name, r.description, ur.granted_at, ur.expires_at
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ? AND (ur.expires_at IS NULL OR ur.expires_at > ?)
        ''', (user_id, datetime.now().isoformat()))
        
        roles = []
        role_ids = []
        for row in roles_result:
            roles.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'granted_at': row[3],
                'expires_at': row[4]
            })
            role_ids.append(row[0])
        
        # 获取角色权限
        permissions = []
        if role_ids:
            placeholders = ','.join('?' * len(role_ids))
            perms_result = safe_query.execute_query(f'''
                SELECT DISTINCT p.id, p.name, p.description
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id IN ({placeholders})
            ''', tuple(role_ids))
            
            for row in perms_result:
                permissions.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2]
                })
        
        # 如果没有角色，分配默认 user 角色
        if not roles:
            PermissionModel.assign_default_role(user_id)
            return PermissionModel.get_user_permissions(user_id)
        
        return {
            'user_id': user_id,
            'permissions': permissions,
            'roles': roles,
            'permission_names': [p['name'] for p in permissions],
            'role_names': [r['name'] for r in roles]
        }
    
    @staticmethod
    def assign_default_role(user_id: str):
        """分配默认角色"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 获取 user 角色 ID
        roles = safe_query.execute_query('SELECT id FROM roles WHERE name = ?', ('user',))
        
        if roles:
            role_id = roles[0][0]
            try:
                safe_query.execute_query('''
                    INSERT OR IGNORE INTO user_roles (user_id, role_id, granted_at)
                    VALUES (?, ?, ?)
                ''', (user_id, role_id, datetime.now().isoformat()))
                api_logger.info(f'Assigned default role to user: {user_id}')
            except Exception as e:
                api_logger.error(f'Error assigning default role: {e}')
    
    @staticmethod
    def grant_permission(user_id: str, permission_id: int, granted_by: str, 
                        reason: str = None, expires_days: int = None) -> bool:
        """授予用户权限"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        try:
            # 开始事务
            safe_query.execute_query('BEGIN')
            
            # 创建临时角色（如果权限不属于任何现有角色）
            temp_role_name = f'temp_{permission_id}_{user_id}'
            
            # 检查权限是否存在
            perm = safe_query.execute_query('SELECT id, name FROM permissions WHERE id = ?', (permission_id,))
            if not perm:
                safe_query.execute_query('ROLLBACK')
                return False
            
            # 获取或创建临时角色
            roles = safe_query.execute_query('SELECT id FROM roles WHERE name = ?', (temp_role_name,))
            if roles:
                role_id = roles[0][0]
            else:
                # 创建临时角色
                safe_query.execute_query('''
                    INSERT INTO roles (name, description) VALUES (?, ?)
                ''', (temp_role_name, f'Temporary role for permission {perm[0][1]}'))
                role_id = safe_query.conn.lastrowid
            
            # 关联权限到角色
            safe_query.execute_query('''
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, permission_id))
            
            # 分配角色给用户
            expires_at = None
            if expires_days:
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
            
            safe_query.execute_query('''
                INSERT OR REPLACE INTO user_roles (user_id, role_id, granted_by, granted_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, role_id, granted_by, datetime.now().isoformat(), expires_at))
            
            # 记录日志
            safe_query.execute_query('''
                INSERT INTO permission_change_log (user_id, action, permission_id, changed_by, reason)
                VALUES (?, 'grant', ?, ?, ?)
            ''', (user_id, permission_id, granted_by, reason or ''))
            
            # 提交事务
            safe_query.execute_query('COMMIT')
            
            api_logger.info(f'Granted permission {permission_id} to user {user_id}')
            return True
            
        except Exception as e:
            safe_query.execute_query('ROLLBACK')
            api_logger.error(f'Error granting permission: {e}', exc_info=True)
            return False
    
    @staticmethod
    def revoke_permission(user_id: str, permission_id: int, revoked_by: str, 
                         reason: str = None) -> bool:
        """撤销用户权限"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        try:
            # 开始事务
            safe_query.execute_query('BEGIN')
            
            # 查找包含该权限的用户角色
            roles_result = safe_query.execute_query('''
                SELECT DISTINCT ur.role_id
                FROM user_roles ur
                JOIN role_permissions rp ON ur.role_id = rp.role_id
                WHERE ur.user_id = ? AND rp.permission_id = ?
            ''', (user_id, permission_id))
            
            role_ids = [row[0] for row in roles_result]
            
            # 删除用户角色关联
            if role_ids:
                placeholders = ','.join('?' * len(role_ids))
                safe_query.execute_query(f'''
                    DELETE FROM user_roles
                    WHERE user_id = ? AND role_id IN ({placeholders})
                ''', (user_id, *role_ids))
            
            # 记录日志
            safe_query.execute_query('''
                INSERT INTO permission_change_log (user_id, action, permission_id, changed_by, reason)
                VALUES (?, 'revoke', ?, ?, ?)
            ''', (user_id, permission_id, revoked_by, reason or ''))
            
            # 提交事务
            safe_query.execute_query('COMMIT')
            
            api_logger.info(f'Revoked permission {permission_id} from user {user_id}')
            return True
            
        except Exception as e:
            safe_query.execute_query('ROLLBACK')
            api_logger.error(f'Error revoking permission: {e}', exc_info=True)
            return False
    
    @staticmethod
    def get_all_permissions() -> List[Dict[str, Any]]:
        """获取所有权限"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        result = safe_query.execute_query('''
            SELECT id, name, description, created_at
            FROM permissions
            ORDER BY id
        ''')
        
        return [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_at': row[3]
            }
            for row in result
        ]
    
    @staticmethod
    def get_all_roles() -> List[Dict[str, Any]]:
        """获取所有角色"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        result = safe_query.execute_query('''
            SELECT r.id, r.name, r.description, 
                   COUNT(DISTINCT rp.permission_id) as permission_count,
                   COUNT(DISTINCT ur.user_id) as user_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN user_roles ur ON r.id = ur.role_id
            GROUP BY r.id
            ORDER BY r.id
        ''')
        
        return [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'permission_count': row[3],
                'user_count': row[4]
            }
            for row in result
        ]


# =============================================================================
# API 接口实现
# =============================================================================

@permission_bp.route('/api/user/permissions', methods=['GET'])
def get_user_permissions():
    """
    获取用户权限列表
    
    Query Parameters:
        user_id: 用户 ID (可选，默认为当前用户)
    
    Returns:
        {
            "success": true,
            "data": {
                "user_id": "xxx",
                "permissions": [...],
                "roles": [...],
                "permission_names": [...],
                "role_names": [...]
            }
        }
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            # 尝试从请求头获取
            user_id = request.headers.get('X-User-Id') or request.headers.get('X-OpenID')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': '缺少 user_id 参数'
            }), 400
        
        # 验证 user_id
        try:
            user_id = validate_string(user_id, field_name='user_id', max_length=100)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        
        # 获取权限
        permissions = PermissionModel.get_user_permissions(user_id)
        
        return jsonify({
            'success': True,
            'data': permissions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting permissions: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


@permission_bp.route('/api/user/permission/grant', methods=['POST'])
def grant_permission():
    """
    授予用户权限
    
    Request Body:
        {
            "user_id": "目标用户 ID",
            "permission_id": 权限 ID,
            "reason": "授权原因",
            "expires_days": 过期天数 (可选)
        }
    
    Returns:
        {
            "success": true,
            "message": "权限授予成功"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体'
            }), 400
        
        user_id = data.get('user_id')
        permission_id = data.get('permission_id')
        reason = data.get('reason', '')
        expires_days = data.get('expires_days')
        
        # 验证必填参数
        if not user_id or not permission_id:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：user_id 和 permission_id'
            }), 400
        
        # 验证参数类型
        try:
            user_id = validate_string(user_id, field_name='user_id', max_length=100)
            permission_id = int(permission_id)
            if expires_days:
                expires_days = int(expires_days)
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'参数类型错误：{str(e)}'
            }), 400
        
        # 获取操作人
        granted_by = request.headers.get('X-User-Id') or 'system'
        
        # 授予权限
        success = PermissionModel.grant_permission(
            user_id=user_id,
            permission_id=permission_id,
            granted_by=granted_by,
            reason=reason,
            expires_days=expires_days
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '权限授予成功',
                'data': {
                    'user_id': user_id,
                    'permission_id': permission_id,
                    'expires_days': expires_days
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '权限授予失败，请检查权限 ID 是否正确'
            }), 400
        
    except Exception as e:
        api_logger.error(f'Error granting permission: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


@permission_bp.route('/api/user/permission/revoke', methods=['DELETE'])
def revoke_permission():
    """
    撤销用户权限
    
    Request Body:
        {
            "user_id": "目标用户 ID",
            "permission_id": 权限 ID,
            "reason": "撤销原因"
        }
    
    Returns:
        {
            "success": true,
            "message": "权限撤销成功"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体'
            }), 400
        
        user_id = data.get('user_id')
        permission_id = data.get('permission_id')
        reason = data.get('reason', '')
        
        # 验证必填参数
        if not user_id or not permission_id:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：user_id 和 permission_id'
            }), 400
        
        # 验证参数类型
        try:
            user_id = validate_string(user_id, field_name='user_id', max_length=100)
            permission_id = int(permission_id)
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'参数类型错误：{str(e)}'
            }), 400
        
        # 获取操作人
        revoked_by = request.headers.get('X-User-Id') or 'system'
        
        # 撤销权限
        success = PermissionModel.revoke_permission(
            user_id=user_id,
            permission_id=permission_id,
            revoked_by=revoked_by,
            reason=reason
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '权限撤销成功',
                'data': {
                    'user_id': user_id,
                    'permission_id': permission_id
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '权限撤销失败，请检查用户是否拥有该权限'
            }), 400
        
    except Exception as e:
        api_logger.error(f'Error revoking permission: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


@permission_bp.route('/api/user/permissions/all', methods=['GET'])
def get_all_permissions():
    """获取所有权限列表"""
    try:
        permissions = PermissionModel.get_all_permissions()
        
        return jsonify({
            'success': True,
            'data': permissions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting all permissions: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


@permission_bp.route('/api/user/roles', methods=['GET'])
def get_all_roles():
    """获取所有角色列表"""
    try:
        roles = PermissionModel.get_all_roles()
        
        return jsonify({
            'success': True,
            'data': roles,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting all roles: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


# =============================================================================
# 蓝图导出
# =============================================================================

def init_permission_routes(app):
    """初始化权限管理路由"""
    app.register_blueprint(permission_bp)
    api_logger.info('Permission API routes registered')


def init_permission_db():
    """初始化权限管理数据库表"""
    import os
    sql_path = os.path.join(os.path.dirname(__file__), 'schema_permissions.sql')
    
    if os.path.exists(sql_path):
        try:
            # 使用 SafeDatabaseQuery 的上下文管理器
            from wechat_backend.security.sql_protection import SafeDatabaseQuery
            from wechat_backend.database import DB_PATH
            
            with SafeDatabaseQuery(DB_PATH) as safe_query:
                # 确保连接已建立
                safe_query._ensure_connection()
                
                with open(sql_path, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # 执行 SQL 脚本
                safe_query.conn.executescript(sql_script)
                safe_query.conn.commit()
                
                api_logger.info('Permission database tables initialized')
        except Exception as e:
            api_logger.error(f'Error initializing permission database: {e}', exc_info=True)
    else:
        api_logger.warning(f'Permission SQL script not found: {sql_path}')
