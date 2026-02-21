#!/usr/bin/env python3
"""
审计日志模块
记录管理员操作日志，支持查询、导出和告警
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from wechat_backend.logging_config import db_logger
from wechat_backend.database import DB_PATH


def init_audit_logs_table():
    """初始化审计日志表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT NOT NULL,
            action TEXT NOT NULL,
            resource TEXT,
            resource_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            request_method TEXT,
            request_data TEXT,
            response_status INTEGER,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id 
        ON audit_logs(admin_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action 
        ON audit_logs(action)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
        ON audit_logs(created_at)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource 
        ON audit_logs(resource)
    ''')
    
    conn.commit()
    conn.close()
    db_logger.info("Audit logs table initialized")


def save_audit_log(admin_id, action, resource=None, resource_id=None, 
                   ip_address=None, user_agent=None, request_method=None,
                   request_data=None, response_status=None, error_message=None):
    """
    保存审计日志
    
    Args:
        admin_id: 管理员 ID
        action: 操作类型
        resource: 操作资源
        resource_id: 资源 ID
        ip_address: IP 地址
        user_agent: 用户代理
        request_method: 请求方法
        request_data: 请求数据
        response_status: 响应状态码
        error_message: 错误信息
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO audit_logs (
                admin_id, action, resource, resource_id, ip_address,
                user_agent, request_method, request_data, response_status,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            admin_id, action, resource, resource_id, ip_address,
            user_agent, request_method,
            json.dumps(request_data) if request_data else None,
            response_status, error_message
        ))
        
        conn.commit()
        db_logger.debug(f"Audit log saved: {admin_id} - {action}")
        
    except Exception as e:
        db_logger.error(f"Failed to save audit log: {e}")
    finally:
        conn.close()


def get_audit_logs(admin_id=None, action=None, resource=None, 
                   start_date=None, end_date=None, page=1, page_size=20):
    """
    查询审计日志
    
    Args:
        admin_id: 管理员 ID（可选）
        action: 操作类型（可选）
        resource: 资源类型（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        page: 页码
        page_size: 每页数量
        
    Returns:
        dict: 日志列表和分页信息
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 构建查询条件
    conditions = []
    params = []
    
    if admin_id:
        conditions.append('admin_id = ?')
        params.append(admin_id)
    
    if action:
        conditions.append('action = ?')
        params.append(action)
    
    if resource:
        conditions.append('resource = ?')
        params.append(resource)
    
    if start_date:
        conditions.append('created_at >= ?')
        params.append(start_date)
    
    if end_date:
        conditions.append('created_at <= ?')
        params.append(end_date)
    
    where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    
    # 获取总数
    cursor.execute(f'SELECT COUNT(*) FROM audit_logs{where_clause}', params)
    total = cursor.fetchone()[0]
    
    # 获取日志列表
    offset = (page - 1) * page_size
    cursor.execute(f'''
        SELECT id, admin_id, action, resource, resource_id, ip_address,
               user_agent, request_method, request_data, response_status,
               error_message, created_at
        FROM audit_logs{where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', params + [page_size, offset])
    
    logs = [
        {
            'id': row[0],
            'admin_id': row[1],
            'action': row[2],
            'resource': row[3],
            'resource_id': row[4],
            'ip_address': row[5],
            'user_agent': row[6],
            'request_method': row[7],
            'request_data': json.loads(row[8]) if row[8] else None,
            'response_status': row[9],
            'error_message': row[10],
            'created_at': row[11]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    
    return {
        'logs': logs,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size
        }
    }


def get_audit_statistics(days=7):
    """
    获取审计统计数据
    
    Args:
        days: 统计天数
        
    Returns:
        dict: 统计数据
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 总操作数
    cursor.execute('''
        SELECT COUNT(*) FROM audit_logs WHERE created_at >= ?
    ''', (start_date,))
    total_actions = cursor.fetchone()[0]
    
    # 按操作类型统计
    cursor.execute('''
        SELECT action, COUNT(*) as count
        FROM audit_logs
        WHERE created_at >= ?
        GROUP BY action
        ORDER BY count DESC
    ''', (start_date,))
    actions_stats = [
        {'action': row[0], 'count': row[1]}
        for row in cursor.fetchall()
    ]
    
    # 按管理员统计
    cursor.execute('''
        SELECT admin_id, COUNT(*) as count
        FROM audit_logs
        WHERE created_at >= ?
        GROUP BY admin_id
        ORDER BY count DESC
        LIMIT 10
    ''', (start_date,))
    admin_stats = [
        {'admin_id': row[0], 'count': row[1]}
        for row in cursor.fetchall()
    ]
    
    # 错误统计
    cursor.execute('''
        SELECT COUNT(*) FROM audit_logs 
        WHERE created_at >= ? AND response_status >= 400
    ''', (start_date,))
    error_count = cursor.fetchone()[0]
    
    # 按资源统计
    cursor.execute('''
        SELECT resource, COUNT(*) as count
        FROM audit_logs
        WHERE created_at >= ?
        GROUP BY resource
        ORDER BY count DESC
        LIMIT 10
    ''', (start_date,))
    resource_stats = [
        {'resource': row[0], 'count': row[1]}
        for row in cursor.fetchall()
    ]
    
    conn.close()
    
    return {
        'total_actions': total_actions,
        'error_count': error_count,
        'error_rate': round(error_count / total_actions * 100, 2) if total_actions > 0 else 0,
        'actions_stats': actions_stats,
        'admin_stats': admin_stats,
        'resource_stats': resource_stats,
        'period': {
            'days': days,
            'start': start_date
        }
    }


def get_suspicious_activities(threshold=10, minutes=5):
    """
    检测可疑活动
    
    Args:
        threshold: 阈值（操作次数）
        minutes: 时间窗口（分钟）
        
    Returns:
        list: 可疑活动列表
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    time_window = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 检测频繁操作
    cursor.execute('''
        SELECT admin_id, action, COUNT(*) as count,
               MIN(created_at) as first_time,
               MAX(created_at) as last_time
        FROM audit_logs
        WHERE created_at >= ?
        GROUP BY admin_id, action
        HAVING count >= ?
        ORDER BY count DESC
    ''', (time_window, threshold))
    
    suspicious = [
        {
            'admin_id': row[0],
            'action': row[1],
            'count': row[2],
            'first_time': row[3],
            'last_time': row[4],
            'type': 'frequent_action'
        }
        for row in cursor.fetchall()
    ]
    
    # 检测错误操作
    cursor.execute('''
        SELECT admin_id, COUNT(*) as error_count
        FROM audit_logs
        WHERE created_at >= ? AND response_status >= 400
        GROUP BY admin_id
        HAVING error_count >= ?
    ''', (time_window, threshold // 2))
    
    for row in cursor.fetchall():
        suspicious.append({
            'admin_id': row[0],
            'error_count': row[1],
            'type': 'frequent_errors'
        })
    
    conn.close()
    
    return suspicious


def export_audit_logs(format='csv', admin_id=None, start_date=None, end_date=None):
    """
    导出审计日志
    
    Args:
        format: 导出格式（csv/json）
        admin_id: 管理员 ID（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        
    Returns:
        str: 导出的数据
    """
    # 获取日志数据
    result = get_audit_logs(
        admin_id=admin_id,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000  # 大量导出
    )
    
    logs = result['logs']
    
    if format == 'json':
        return json.dumps(logs, indent=2, ensure_ascii=False)
    else:
        # CSV 格式
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', '管理员 ID', '操作', '资源', '资源 ID', 'IP 地址',
            '请求方法', '响应状态', '错误信息', '时间'
        ])
        
        # 写入数据
        for log in logs:
            writer.writerow([
                log['id'],
                log['admin_id'],
                log['action'],
                log['resource'] or '',
                log['resource_id'] or '',
                log['ip_address'] or '',
                log['request_method'] or '',
                log['response_status'] or '',
                log['error_message'] or '',
                log['created_at']
            ])
        
        return output.getvalue()


# 初始化表
init_audit_logs_table()
