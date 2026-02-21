#!/usr/bin/env python3
"""
数据库查询优化模块
提供索引管理、查询优化、性能分析等功能

功能:
1. 索引管理 (Index Management)
2. 查询优化 (Query Optimization)
3. 性能分析 (Performance Analysis)
4. 慢查询日志 (Slow Query Logging)
"""

import sqlite3
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from wechat_backend.logging_config import api_logger

# ==================== 数据库配置 ====================

DATABASE_PATH = 'database.db'
SLOW_QUERY_THRESHOLD = 1.0  # 秒


# ==================== 查询优化器 ====================

class QueryOptimizer:
    """
    查询优化器
    分析并优化 SQL 查询
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.slow_queries: List[Dict[str, Any]] = []
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def optimize_query(self, sql: str, params: Tuple = None) -> Tuple[str, List[str]]:
        """
        优化 SQL 查询
        
        返回:
            优化后的 SQL, 优化建议列表
        """
        suggestions = []
        optimized_sql = sql.strip()
        
        # 分析查询
        sql_upper = optimized_sql.upper()
        
        # 检查 SELECT *
        if 'SELECT *' in sql_upper:
            suggestions.append('避免使用 SELECT *，明确指定需要的列')
        
        # 检查缺少 WHERE 的 UPDATE/DELETE
        if ('UPDATE' in sql_upper or 'DELETE' in sql_upper) and 'WHERE' not in sql_upper:
            suggestions.append('警告：UPDATE/DELETE 缺少 WHERE 条件')
        
        # 检查 LIKE 前缀通配符
        if "LIKE '%" in sql_upper:
            suggestions.append('避免使用 LIKE 前缀通配符，无法使用索引')
        
        # 检查 ORDER BY 无 LIMIT
        if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
            suggestions.append('ORDER BY 建议配合 LIMIT 使用')
        
        # 检查子查询
        if 'SELECT' in sql_upper[sql_upper.find('FROM'):] if 'FROM' in sql_upper else False:
            suggestions.append('考虑将子查询改为 JOIN')
        
        return optimized_sql, suggestions
    
    def analyze_query_performance(self, sql: str, params: Tuple = None) -> Dict[str, Any]:
        """
        分析查询性能
        
        返回:
            性能分析报告
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 执行 EXPLAIN QUERY PLAN
            try:
                cursor.execute(f"EXPLAIN QUERY PLAN {sql}", params or ())
                plan = cursor.fetchall()
                
                analysis = {
                    'sql': sql,
                    'query_plan': [dict(row) for row in plan],
                    'uses_index': False,
                    'full_table_scan': False,
                    'tables_accessed': [],
                    'suggestions': []
                }
                
                # 分析执行计划
                for row in plan:
                    detail = row.get('detail', '') if isinstance(row, dict) else str(row)
                    
                    if 'USING INDEX' in detail or 'USING COVERING INDEX' in detail:
                        analysis['uses_index'] = True
                    
                    if 'SCAN TABLE' in detail or 'SCAN CURSOR' in detail:
                        analysis['full_table_scan'] = True
                        # 提取表名
                        parts = detail.split()
                        for i, part in enumerate(parts):
                            if part in ['TABLE', 'CURSOR'] and i + 1 < len(parts):
                                table_name = parts[i + 1]
                                if table_name not in analysis['tables_accessed']:
                                    analysis['tables_accessed'].append(table_name)
                
                # 生成建议
                if analysis['full_table_scan'] and not analysis['uses_index']:
                    analysis['suggestions'].append(
                        f"考虑为表 {', '.join(analysis['tables_accessed'])} 添加索引"
                    )
                
                return analysis
                
            except Exception as e:
                return {
                    'sql': sql,
                    'error': str(e),
                    'suggestions': ['SQL 语法可能有误，请检查']
                }
    
    def log_slow_query(self, sql: str, duration: float, params: Tuple = None):
        """记录慢查询"""
        if duration >= SLOW_QUERY_THRESHOLD:
            with self._lock:
                self.slow_queries.append({
                    'sql': sql,
                    'duration': duration,
                    'params': params,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 限制记录数量
                if len(self.slow_queries) > 1000:
                    self.slow_queries = self.slow_queries[-1000:]
            
            api_logger.warning(
                f'慢查询检测到：{duration:.2f}s, SQL: {sql[:100]}...'
            )
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        return sorted(
            self.slow_queries[-limit:],
            key=lambda x: x['duration'],
            reverse=True
        )
    
    def get_query_stats(self) -> Dict[str, Any]:
        """获取查询统计"""
        return {
            'slow_query_count': len(self.slow_queries),
            'slow_query_threshold': SLOW_QUERY_THRESHOLD,
            'recent_slow_queries': self.get_slow_queries(10)
        }


# ==================== 索引管理器 ====================

class IndexManager:
    """
    索引管理器
    管理数据库索引的创建、删除和分析
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.optimizer = QueryOptimizer(db_path)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def list_tables(self) -> List[str]:
        """列出所有表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return [row['name'] for row in cursor.fetchall()]
    
    def list_indexes(self, table: str = None) -> List[Dict[str, Any]]:
        """列出索引"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if table:
                cursor.execute(
                    "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
                    (table,)
                )
            else:
                cursor.execute(
                    "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_index(self, table: str, columns: List[str], 
                     index_name: str = None, unique: bool = False) -> Dict[str, Any]:
        """
        创建索引
        
        参数:
            table: 表名
            columns: 列名列表
            index_name: 索引名称（可选）
            unique: 是否唯一索引
        
        返回:
            创建结果
        """
        if not index_name:
            index_name = f"idx_{table}_{'_'.join(columns)}"
        
        columns_sql = ', '.join(columns)
        unique_str = 'UNIQUE ' if unique else ''
        
        sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table} ({columns_sql})"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                conn.commit()
            
            api_logger.info(f'索引创建成功：{index_name} on {table}({columns_sql})')
            
            return {
                'success': True,
                'index_name': index_name,
                'table': table,
                'columns': columns,
                'unique': unique
            }
        except Exception as e:
            api_logger.error(f'索引创建失败：{e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def drop_index(self, index_name: str) -> Dict[str, Any]:
        """删除索引"""
        sql = f"DROP INDEX IF EXISTS {index_name}"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                conn.commit()
            
            api_logger.info(f'索引删除成功：{index_name}')
            
            return {
                'success': True,
                'index_name': index_name
            }
        except Exception as e:
            api_logger.error(f'索引删除失败：{e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_table(self, table: str) -> Dict[str, Any]:
        """
        分析表
        
        返回:
            表分析报告
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取表信息
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [dict(row) for row in cursor.fetchall()]
            
            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = [dict(row) for row in cursor.fetchall()]
            
            # 获取行数
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            row_count = cursor.fetchone()['count']
            
            # 获取索引详情
            index_details = []
            for idx in indexes:
                cursor.execute(f"PRAGMA index_info({idx['name']})")
                idx_info = [dict(row) for row in cursor.fetchall()]
                index_details.append({
                    'name': idx['name'],
                    'unique': bool(idx['unique']),
                    'columns': [info['name'] for info in idx_info]
                })
            
            # 分析建议
            suggestions = []
            
            # 检查没有索引的列
            indexed_columns = set()
            for idx in index_details:
                indexed_columns.update(idx['columns'])
            
            for col in columns:
                if col['name'] not in indexed_columns:
                    if col['type'] in ['INTEGER', 'TEXT']:
                        suggestions.append(f"考虑为列 {col['name']} 创建索引")
            
            return {
                'table': table,
                'row_count': row_count,
                'columns': columns,
                'indexes': index_details,
                'suggestions': suggestions
            }
    
    def get_missing_indexes(self) -> List[Dict[str, Any]]:
        """获取建议创建的索引"""
        suggestions = []
        
        for table in self.list_tables():
            analysis = self.analyze_table(table)
            if analysis['suggestions']:
                suggestions.append({
                    'table': table,
                    'suggestions': analysis['suggestions']
                })
        
        return suggestions
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库
        
        返回:
            优化结果
        """
        results = {
            'vacuum': False,
            'analyze': False,
            'integrity_check': 'unknown'
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # VACUUM
            try:
                cursor.execute('VACUUM')
                results['vacuum'] = True
                api_logger.info('数据库 VACUUM 完成')
            except Exception as e:
                api_logger.error(f'VACUUM 失败：{e}')
            
            # ANALYZE
            try:
                cursor.execute('ANALYZE')
                results['analyze'] = True
                api_logger.info('数据库 ANALYZE 完成')
            except Exception as e:
                api_logger.error(f'ANALYZE 失败：{e}')
            
            # 完整性检查
            try:
                cursor.execute('PRAGMA integrity_check')
                result = cursor.fetchone()
                results['integrity_check'] = result[0] if result else 'unknown'
            except Exception as e:
                results['integrity_check'] = f'error: {str(e)}'
        
        return results


# ==================== 性能监控装饰器 ====================

def monitor_query_performance(func):
    """
    查询性能监控装饰器
    
    用法:
        @monitor_query_performance
        def get_user_data(user_id):
            ...
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            
            if duration >= SLOW_QUERY_THRESHOLD:
                optimizer = QueryOptimizer()
                optimizer.log_slow_query(
                    sql=f"{func.__name__}({args}, {kwargs})",
                    duration=duration
                )
    
    return wrapper


# ==================== 全局实例 ====================

_query_optimizer = QueryOptimizer()
_index_manager = IndexManager()


def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器实例"""
    return _query_optimizer


def get_index_manager() -> IndexManager:
    """获取索引管理器实例"""
    return _index_manager


# ==================== 初始化推荐索引 ====================

def init_recommended_indexes():
    """初始化推荐索引"""
    index_manager = get_index_manager()
    
    # 定义推荐索引
    recommended_indexes = [
        # 用户相关
        {'table': 'users', 'columns': ['openid'], 'unique': True},
        {'table': 'users', 'columns': ['created_at']},
        
        # 测试结果相关
        {'table': 'test_results', 'columns': ['user_id']},
        {'table': 'test_results', 'columns': ['execution_id']},
        {'table': 'test_results', 'columns': ['created_at']},
        {'table': 'test_results', 'columns': ['brand_name']},
        
        # 审计日志相关
        {'table': 'audit_logs', 'columns': ['user_id']},
        {'table': 'audit_logs', 'columns': ['action']},
        {'table': 'audit_logs', 'columns': ['timestamp']},
        
        # 同步数据相关
        {'table': 'sync_results', 'columns': ['user_id']},
        {'table': 'sync_results', 'columns': ['sync_timestamp']},
    ]
    
    created_count = 0
    
    for idx_config in recommended_indexes:
        result = index_manager.create_index(
            table=idx_config['table'],
            columns=idx_config['columns'],
            unique=idx_config.get('unique', False)
        )
        
        if result.get('success'):
            created_count += 1
    
    api_logger.info(f'推荐索引初始化完成，创建 {created_count} 个索引')
    
    return {
        'success': True,
        'created_count': created_count,
        'total_indexes': len(recommended_indexes)
    }
