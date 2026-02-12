"""
SQL注入防护模块
提供数据库查询的安全防护功能
"""

import sqlite3
import re
from typing import Any, List, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class SQLInjectionProtector:
    """SQL注入防护器"""
    
    def __init__(self):
        # 常见的SQL注入模式
        self.sql_injection_patterns = [
            r"(?i)(union\s+select)",  # UNION SELECT
            r"(?i)(drop\s+\w+)",      # DROP TABLE/DB
            r"(?i)(insert\s+into)",   # INSERT INTO
            r"(?i)(update\s+\w+\s+set)", # UPDATE
            r"(?i)(delete\s+from)",   # DELETE FROM
            r"(?i)(exec\s*\()",       # EXEC
            r"(?i)(sp_\w+)",          # Stored procedure
            r"(?i)(waitfor\s+delay)", # WAITFOR DELAY
            r"(?i)(shutdown\s*\(\s*\))", # SHUTDOWN
            r"'(?:--|#|/\*.*?\*/|--\s+.*|\s+OR\s+\d+=\d+)", # 注释和OR注入
            r"(?i)(\b\w+\s*[=<>]\s*\w+\s*(?:and|or)\s*\w+\s*[=<>]\s*\w+)" # AND/OR条件
        ]
    
    def contains_sql_injection(self, input_str: str) -> bool:
        """检查输入是否包含SQL注入模式"""
        if not input_str:
            return False
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_str):
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
    """安全数据库查询器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.protector = SQLInjectionProtector()
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """执行安全的数据库查询"""
        # 验证查询语句
        if self.protector.contains_sql_injection(query):
            raise ValueError("Potential SQL injection detected in query")
        
        # 验证参数
        for param in params:
            if isinstance(param, str) and self.protector.contains_sql_injection(param):
                raise ValueError(f"Potential SQL injection detected in parameter: {param}")
        
        # 使用参数化查询执行
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            return result
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise
        finally:
            conn.close()
    
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
        """执行安全的插入操作"""
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
        result = self.execute_query(query, params)
        
        # 返回插入的行ID
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        last_row_id = cursor.lastrowid
        conn.close()
        return last_row_id


# 全局实例
sql_protector = SQLInjectionProtector()


def is_safe_sql_input(input_str: str) -> bool:
    """便捷函数：检查输入是否安全"""
    return sql_protector.validate_input(input_str)


def sanitize_sql_input(input_str: str) -> str:
    """便捷函数：净化SQL输入"""
    return sql_protector.sanitize_input(input_str)


def create_safe_query(db_path: str) -> SafeDatabaseQuery:
    """便捷函数：创建安全查询对象"""
    return SafeDatabaseQuery(db_path)