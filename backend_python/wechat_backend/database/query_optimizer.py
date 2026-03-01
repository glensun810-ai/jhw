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
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from wechat_backend.logging_config import api_logger

# ==================== 数据库配置 ====================

# 从配置管理器获取数据库路径（优先使用环境变量）
# P0-DB-INIT-004 修复：统一使用与 database_core.py 相同的数据库路径
import sys
from pathlib import Path

# P0-DB-INIT-004: 直接计算 backend_python 目录，避免相对路径错误
# 无论此文件在哪个子目录，都能正确定位到 backend_python/database.db
DATABASE_DIR = os.environ.get('DATABASE_DIR') or ''

if DATABASE_DIR:
    # 如果设置了 DATABASE_DIR，则使用完整路径
    DATABASE_PATH = os.path.join(DATABASE_DIR, 'database.db')
else:
    # P0-DB-INIT-004: 使用绝对路径计算，确保与 database_core.py 一致
    # 此文件路径：/.../backend_python/wechat_backend/database/query_optimizer.py
    # 需要上溯 3 层到 backend_python 目录
    backend_root = Path(__file__).resolve().parent.parent.parent
    DATABASE_PATH = backend_root / 'database.db'

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

    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            return cursor.fetchone() is not None

    def get_table_columns(self, table: str) -> List[str]:
        """获取表的所有列名"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
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
        创建索引（增强版：检查表和列是否存在）

        参数:
            table: 表名
            columns: 列名列表
            index_name: 索引名称（可选）
            unique: 是否唯一索引

        返回:
            创建结果
        """
        # 检查表是否存在
        if not self.table_exists(table):
            api_logger.warning(f'跳过索引创建：表 {table} 不存在')
            return {
                'success': False,
                'error': f'Table {table} does not exist',
                'skipped': True
            }

        # 检查列是否存在
        table_columns = self.get_table_columns(table)
        missing_columns = [col for col in columns if col not in table_columns]
        
        if missing_columns:
            api_logger.warning(
                f'跳过索引创建：表 {table} 缺少列 {missing_columns}，现有列：{table_columns}'
            )
            return {
                'success': False,
                'error': f'Columns {missing_columns} do not exist in table {table}',
                'skipped': True
            }

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
    """
    初始化推荐索引（增强版 - P0-DB-INIT-003 修复）
    
    修复说明：
    1. 增加重试次数和等待时间，应对多进程竞争
    2. 添加表创建后的验证延迟（WAL 检查点）
    3. 使用文件锁防止多进程同时初始化
    4. 即使部分表缺失，也为已存在的表创建索引
    5. P0-DB-INIT-003: 确保使用与 init_db() 相同的连接方式
    """
    import time
    import fcntl
    import os

    index_manager = get_index_manager()

    # P0-DB-INIT-003: 记录数据库路径用于诊断
    api_logger.info(f"[索引初始化] 数据库路径：{index_manager.db_path}")
    api_logger.info(f"[索引初始化] 数据库文件存在：{os.path.exists(index_manager.db_path)}")

    # P0-DB-INIT-002: 使用文件锁防止多进程同时初始化
    lock_file = '/tmp/wechat_db_init.lock'
    lock_fd = None
    
    try:
        # 尝试获取独占锁（非阻塞）
        lock_fd = open(lock_file, 'w')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            api_logger.info("已获取数据库初始化锁")
        except BlockingIOError:
            # 其他进程正在初始化，等待获取锁
            api_logger.info("等待其他进程完成数据库初始化...")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            api_logger.info("已获取数据库初始化锁")
        
        # 获取锁后，再次检查表是否已存在（可能已被其他进程创建）
        tables = index_manager.list_tables()
        required_tables = ['users', 'test_records', 'brand_test_results', 'audit_logs', 'sync_results', 'cache_entries']
        existing_tables = [t for t in required_tables if t in tables]
        
        # P0-DB-INIT-003: 详细诊断日志
        api_logger.info(f"[索引初始化] 当前存在的表：{tables}")
        api_logger.info(f"[索引初始化] 必需的表：{required_tables}")
        api_logger.info(f"[索引初始化] 已存在的表：{existing_tables}")
        
        if len(existing_tables) == len(required_tables):
            api_logger.info("所有必需表已存在（可能已被其他进程创建），开始创建索引")
            _create_indexes(index_manager, required_tables)
            return
        
        # P0-DB-INIT-003: 如果表完全为空，可能是数据库路径问题或 init_db() 未执行
        if not tables:
            api_logger.warning(
                "[索引初始化] 数据库中没有任何表！"
                "这可能是 database_core.py:init_db() 未执行或数据库路径配置错误。"
                "尝试等待 init_db() 完成..."
            )
        
        # P0-DB-INIT-002: 增强重试机制
        # 增加重试次数和等待时间，应对表创建延迟
        max_retries = 10
        retry_delays = [0.5, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 5.0, 5.0]  # 渐进式延迟
        
        for attempt in range(max_retries):
            tables = index_manager.list_tables()
            missing_tables = [t for t in required_tables if t not in tables]

            if not missing_tables:
                # P0-DB-INIT-002: 表创建后添加短暂延迟，确保 WAL 检查点完成
                api_logger.info(f"所有必需表已存在，等待 0.5s 确保事务提交完成...")
                time.sleep(0.5)
                
                # 验证表确实可用
                verification_tables = index_manager.list_tables()
                still_missing = [t for t in required_tables if t not in verification_tables]
                if still_missing:
                    api_logger.warning(f"验证失败，表再次消失：{still_missing}，继续等待...")
                    continue
                
                api_logger.info("表验证通过，开始创建索引")
                _create_indexes(index_manager, required_tables)
                return
            else:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    api_logger.warning(
                        f"等待表创建：缺少 {missing_tables}，"
                        f"尝试 {attempt + 1}/{max_retries}，{delay}s 后重试..."
                    )
                    time.sleep(delay)
                    
                    # P0-DB-INIT-002: 触发 WAL 检查点，确保事务持久化
                    try:
                        with index_manager.get_connection() as conn:
                            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except Exception as e:
                        api_logger.debug(f"WAL 检查点触发失败（可忽略）：{e}")
                else:
                    api_logger.error(f"表创建超时，跳过索引创建：{missing_tables}")
                    api_logger.error(f"当前存在的表：{tables}")
                    api_logger.error(
                        "可能的原因：1) init_db() 未执行 2) 数据库路径不一致 3) 权限问题"
                    )
                    
                    # P0-DB-INIT-003: 尝试直接检查数据库文件
                    if os.path.exists(index_manager.db_path):
                        api_logger.error(f"数据库文件大小：{os.path.getsize(index_manager.db_path)} bytes")
                    else:
                        api_logger.error(f"数据库文件不存在：{index_manager.db_path}")
                    
                    api_logger.warning("将为已存在的表创建索引...")
                    
                    # 为已存在的表创建索引
                    _create_indexes(index_manager, existing_tables)
                    return
    
    except Exception as e:
        api_logger.error(f"初始化索引失败：{e}")
        import traceback
        api_logger.error(traceback.format_exc())
    finally:
        # 释放文件锁
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                api_logger.debug("数据库初始化锁已释放")
            except Exception as e:
                api_logger.debug(f"释放锁失败（可忽略）：{e}")


def _create_indexes(index_manager, tables_to_create: list):
    """
    为指定的表创建索引
    
    Args:
        index_manager: 索引管理器实例
        tables_to_create: 需要创建索引的表名列表
    """
    # 定义推荐索引
    # 注意：字段名必须与 database_core.py 中的表结构一致
    recommended_indexes = [
        # 用户相关
        {'table': 'users', 'columns': ['openid'], 'unique': True},
        {'table': 'users', 'columns': ['created_at']},

        # 测试结果相关（P0-DB-INIT-005 修复：使用 user_openid 而非 user_id）
        {'table': 'test_records', 'columns': ['user_openid']},
        {'table': 'test_records', 'columns': ['brand_name']},
        {'table': 'test_records', 'columns': ['test_date']},
        {'table': 'test_records', 'columns': ['overall_score']},
        {'table': 'test_records', 'columns': ['user_openid', 'test_date']},
        {'table': 'test_records', 'columns': ['brand_name', 'test_date']},

        # 品牌测试结果相关
        {'table': 'brand_test_results', 'columns': ['task_id']},
        {'table': 'brand_test_results', 'columns': ['brand_name']},
        {'table': 'brand_test_results', 'columns': ['created_at']},
        {'table': 'brand_test_results', 'columns': ['task_id', 'brand_name']},

        # 审计日志相关
        {'table': 'audit_logs', 'columns': ['admin_id']},
        {'table': 'audit_logs', 'columns': ['action']},
        {'table': 'audit_logs', 'columns': ['created_at']},

        # 同步数据相关
        {'table': 'sync_results', 'columns': ['user_id']},
        {'table': 'sync_results', 'columns': ['sync_timestamp']},

        # 缓存相关
        {'table': 'cache_entries', 'columns': ['expires_at']},
        {'table': 'cache_entries', 'columns': ['created_at']},
    ]

    created_count = 0
    skipped_count = 0
    failed_count = 0

    for idx_config in recommended_indexes:
        # 只为指定的表创建索引
        if idx_config['table'] not in tables_to_create:
            continue

        result = index_manager.create_index(
            table=idx_config['table'],
            columns=idx_config['columns'],
            unique=idx_config.get('unique', False)
        )

        if result.get('success'):
            created_count += 1
        elif result.get('skipped'):
            skipped_count += 1
            api_logger.debug(
                f'索引跳过：{idx_config["table"]}({idx_config["columns"]}) - '
                f'{result.get("error", "未知原因")}'
            )
        else:
            failed_count += 1
            api_logger.error(
                f'索引创建失败：{idx_config["table"]}({idx_config["columns"]}) - '
                f'{result.get("error", "未知原因")}'
            )

    api_logger.info(
        f'推荐索引初始化完成：成功 {created_count} 个，'
        f'跳过 {skipped_count} 个，失败 {failed_count} 个'
    )

    return {
        'success': True,
        'created_count': created_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'total_indexes': len(recommended_indexes)
    }
