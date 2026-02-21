#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修复 database.py 添加连接关闭功能

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/database.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改 SafeDatabaseQuery 类添加上下文管理器
old_class = '''class SafeDatabaseQuery:
    """Safe database query wrapper with SQL injection protection"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = None
        self.cursor = None'''

new_class = '''class SafeDatabaseQuery:
    """Safe database query wrapper with SQL injection protection"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 确保连接关闭"""
        self.close()
        return False  # 不异常
    
    def connect(self):
        """建立数据库连接"""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
                db_logger.debug(f"Database connection established: {self.db_path}")
            except Exception as e:
                db_logger.error(f"Failed to connect to database: {e}")
                raise
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
            db_logger.debug(f"Database connection closed: {self.db_path}")'''

content = content.replace(old_class, new_class)

# 2. 修改 execute_query 方法确保使用连接
old_execute = '''    def execute_query(self, query: str, params: tuple = None):
        """Execute a query with SQL injection protection"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            
            # For SELECT queries, return results
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                conn.close()
                return results
            
            # For INSERT/UPDATE/DELETE, return last row id
            last_id = cursor.lastrowid
            conn.close()
            return last_id
            
        except Exception as e:
            db_logger.error(f"Database error: {e}")
            raise'''

new_execute = '''    def execute_query(self, query: str, params: tuple = None):
        """Execute a query with SQL injection protection"""
        try:
            # 确保连接已建立
            if self.conn is None:
                self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            self.conn.commit()
            
            # For SELECT queries, return results
            if query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                return results
            
            # For INSERT/UPDATE/DELETE, return last row id
            return self.cursor.lastrowid
            
        except Exception as e:
            db_logger.error(f"Database error: {e}")
            raise'''

content = content.replace(old_execute, new_execute)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ database.py 已修复：添加连接关闭功能')
