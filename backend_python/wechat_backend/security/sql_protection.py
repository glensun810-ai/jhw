"""
SQL 注入防护模块
提供数据库查询的安全防护功能

修复记录:
- 2026-02-20: 添加上下文管理器支持，确保数据库连接正确关闭
- 2026-02-20: 添加事务支持 (begin, commit, rollback)
- 2026-02-20: 添加连接状态跟踪
"""

import sqlite3
import re
from typing import Any, List, Tuple, Union, Optional
import logging

logger = logging.getLogger(__name__)


class SQLInjectionProtector:
    """SQL 注入防护器"""

    def __init__(self):
        # 更精确的 SQL 注入模式 - 避免误判合法 SQL 语句
        # 专注于真正的恶意模式，而不是基本的 SQL 关键字
        self.sql_injection_patterns = [
            # 1. 危险的数据库操作 (在用户输入中不应该出现)
            r"(?i)\b(drop\s+(table|database|schema|view|procedure|function|trigger|event|index))\b",  # DROP 操作
            r"(?i)\b(alter\s+(table|database|schema|view))\b",  # ALTER 操作
            r"(?i)\b(create\s+(database|schema|procedure|function|trigger|event))\b",  # CREATE 操作
            r"(?i)\b(delete\s+from\s+information_schema)",  # 危险删除系统表
            r"(?i)(update\s+\w+\s+set\s+.+where\s+.+and\s+.+\s*[=<>]\s*.+)",  # 复杂 UPDATE
            r"(?i)(exec\s*\()",       # EXEC 执行
            r"(?i)(sp_\w+)",          # 存储过程
            r"(?i)(xp_\w+)",          # 扩展存储过程 (如 xp_cmdshell)
            r"(?i)(waitfor\s+delay)", # 延迟等待
            r"(?i)(shutdown\s*\(\s*\))", # 关机
            r"(?i)(backup\s+database)", # 备份数据库
            # 2. 注释和绕过技术
            r"'(?:--|#|/\*.*?\*/|--\s+.*|\s+OR\s+\d+=\d+)", # SQL 注释和 OR 注入
            # 3. 布尔型注入
            r"(?i)(\b\w+\s*[=<>]\s*\w+\s*(?:and|or)\s*\w+\s*[=<>]\s*\w+)", # AND/OR 条件
            # 4. 时间型注入
            r"(?i)(sleep\s*\(|pg_sleep\s*\(|waitfor\s+delay\s*\(|benchmark\s*\()", # 睡眠函数
            # 5. 联合查询注入 (更具体)
            r"(?i)(union\s+(all\s+)?select)", # UNION SELECT (any form)
            # 6. 危险函数注入
            r"(?i)(char\s*\(|ascii\s*\(|ord\s*\(|concat\s*\(|group_concat\s*\(|load_file\s*\(|into\s+outfile)", # 危险函数
            # 7. 嵌套查询注入
            r"(?i)(select\s+.+\s+from\s+.+\s+where\s+.+\s+and\s+.+\s*=\s*\(select)", # 嵌套 SELECT
        ]

    def contains_sql_injection(self, input_str: str) -> bool:
        """检查输入是否包含 SQL 注入模式"""
        if not input_str:
            return False

        # Check for dangerous patterns regardless of input type
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                logger.warning(f"Detected potential SQL injection: {input_str[:50]}...")
                return True
        return False

    def sanitize_input(self, input_str: str) -> str:
        """净化输入，移除潜在的危险字符"""
        if not input_str:
            return input_str

        # 移除危险字符
        sanitized = input_str.replace("'", "''")  # 转义单引号
        sanitized = sanitized.replace('"', '""')  # 转义双引号
        sanitized = sanitized.replace('--', '')   # 移除注释
        sanitized = sanitized.replace('/*', '')   # 移除注释
        sanitized = sanitized.replace('*/', '')   # 移除注释

        return sanitized

    def validate_input(self, input_str: str) -> bool:
        """验证输入是否安全"""
        if self.contains_sql_injection(input_str):
            return False
        return True


class SafeDatabaseQuery:
    """
    安全数据库查询器 (修复版)
    
    修复内容:
    1. ✅ 添加上下文管理器支持 (__enter__ 和 __exit__)
    2. ✅ 显式连接关闭方法 (close())
    3. ✅ 连接状态跟踪
    4. ✅ 事务支持 (begin(), commit(), rollback())
    5. ✅ 批量操作支持 (execute_many())
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.protector = SQLInjectionProtector()
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._closed = False

    def _ensure_connection(self):
        """确保数据库连接已建立"""
        if self.conn is None or self._closed:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._closed = False

    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """执行安全的数据库查询"""
        # 检查参数（用户输入）是否有 SQL 注入
        for param in params:
            if isinstance(param, str) and self.protector.contains_sql_injection(param):
                raise ValueError(f"Potential SQL injection detected in parameter: {param}")

        # 确保连接已建立
        self._ensure_connection()

        # 使用参数化查询执行（这是防 SQL 注入的主要手段）
        try:
            assert self.cursor is not None
            self.cursor.execute(query, params)
            result = self.cursor.fetchall()
            self.conn.commit()
            return result
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise

    def close(self):
        """显式关闭数据库连接"""
        if self.conn and not self._closed:
            try:
                self.conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
            finally:
                self._closed = True
                self.conn = None
                self.cursor = None

    def __enter__(self):
        """上下文管理器入口"""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 确保连接关闭"""
        self.close()
        # 如果有异常，返回 False 让异常继续传播
        return False

    def begin_transaction(self):
        """开始事务"""
        self._ensure_connection()
        # SQLite 默认自动开启事务，但显式 BEGIN 可以更清晰
        assert self.conn is not None
        self.conn.execute('BEGIN')
        logger.debug("Transaction started")

    def commit(self):
        """提交事务"""
        if self.conn:
            self.conn.commit()
            logger.debug("Transaction committed")

    def rollback(self):
        """回滚事务"""
        if self.conn:
            self.conn.rollback()
            logger.warning("Transaction rolled back")

    def execute_many(self, query: str, seq_of_params: List[Tuple]) -> int:
        """
        批量执行查询 (用于批量插入/更新)
        
        Args:
            query: SQL 查询语句
            seq_of_params: 参数列表
            
        Returns:
            受影响的行数
        """
        self._ensure_connection()
        
        # 检查所有参数是否有 SQL 注入
        for params in seq_of_params:
            for param in params:
                if isinstance(param, str) and self.protector.contains_sql_injection(param):
                    raise ValueError(f"Potential SQL injection detected in parameter: {param}")
        
        assert self.cursor is not None
        self.cursor.executemany(query, seq_of_params)
        self.conn.commit()
        return self.cursor.rowcount

    def execute_safe_select(self, table: str, conditions: dict = None, columns: List[str] = None) -> List[Tuple]:
        """执行安全的选择查询"""
        # 验证表名
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise ValueError(f"Invalid table name: {table}")

        # 验证列名
        if columns:
            for col in columns:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                    raise ValueError(f"Invalid column name: {col}")

        # 构建查询
        cols = '*'
        if columns:
            cols = ', '.join(columns)

        query = f"SELECT {cols} FROM {table}"
        params = ()

        if conditions:
            where_clause = []
            for key, value in conditions.items():
                # 验证列名
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                    raise ValueError(f"Invalid column name in condition: {key}")

                # 验证值
                if isinstance(value, str):
                    if self.protector.contains_sql_injection(value):
                        raise ValueError(f"Potential SQL injection in condition value: {value}")

                where_clause.append(f"{key} = ?")
                params += (value,)

            if where_clause:
                query += " WHERE " + " AND ".join(where_clause)

        return self.execute_query(query, params)

    def execute_safe_insert(self, table: str, data: dict) -> int:
        """
        执行安全的插入操作 (修复版)
        
        修复内容:
        1. ✅ 使用 self.conn.lastrowid 而不是创建新连接
        2. ✅ 确保连接状态正确
        """
        # 验证表名
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise ValueError(f"Invalid table name: {table}")

        # 验证数据
        columns = []
        values = []
        params = ()

        for key, value in data.items():
            # 验证列名
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid column name: {key}")

            # 验证值
            if isinstance(value, str):
                if self.protector.contains_sql_injection(value):
                    raise ValueError(f"Potential SQL injection in value: {value}")

            columns.append(key)
            values.append('?')
            params += (value,)

        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)})"
        self.execute_query(query, params)

        # 返回插入的行 ID - 使用已存在的连接
        self._ensure_connection()
        return self.conn.lastrowid if self.conn else None


# 全局实例
sql_protector = SQLInjectionProtector()


def is_safe_sql_input(input_str: str) -> bool:
    """便捷函数：检查输入是否安全"""
    return sql_protector.validate_input(input_str)


def sanitize_sql_input(input_str: str) -> str:
    """便捷函数：净化 SQL 输入"""
    return sql_protector.sanitize_input(input_str)


def create_safe_query(db_path: str) -> SafeDatabaseQuery:
    """便捷函数：创建安全查询对象"""
    return SafeDatabaseQuery(db_path)
