#!/usr/bin/env python3
"""
DS-P1-2 修复：数据库事务处理上下文管理器

功能：
1. 提供统一的事务处理接口
2. 自动提交/回滚
3. 确保连接关闭
4. 记录事务日志

使用示例:
    with database_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_records ...")
        cursor.execute("INSERT INTO task_statuses ...")
        # 如果任何操作失败，自动回滚
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from datetime import datetime

from wechat_backend.logging_config import db_logger

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'database.db'


@contextmanager
def database_transaction(description: str = "数据库操作"):
    """
    数据库事务上下文管理器
    
    Args:
        description: 事务描述，用于日志记录
    
    Yields:
        sqlite3.Connection: 数据库连接对象
    
    Example:
        with database_transaction("创建诊断记录") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_records ...")
            cursor.execute("INSERT INTO task_statuses ...")
            # 如果任何操作失败，自动回滚
    """
    conn = None
    try:
        # 获取数据库连接
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')  # WAL 模式提升并发性能
        
        db_logger.info(f"[Transaction] 开始事务：{description}")
        
        # 产出连接供外部使用
        yield conn
        
        # 提交事务
        conn.commit()
        db_logger.info(f"[Transaction] 事务成功：{description}")
        
    except Exception as e:
        # 发生异常时回滚
        if conn:
            conn.rollback()
            db_logger.error(f"[Transaction] 事务回滚：{description}, 错误：{e}")
        raise
    
    finally:
        # 确保连接关闭
        if conn:
            conn.close()
            db_logger.debug(f"[Transaction] 连接关闭：{description}")


@contextmanager
def database_readonly_transaction(description: str = "数据库查询"):
    """
    数据库只读事务上下文管理器（使用 URI 模式）
    
    Args:
        description: 事务描述，用于日志记录
    
    Yields:
        sqlite3.Connection: 只读数据库连接对象
    
    Example:
        with database_readonly_transaction("查询诊断记录") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_records WHERE ...")
    """
    conn = None
    try:
        # 以只读模式打开数据库
        conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
        
        db_logger.info(f"[Transaction] 开始只读事务：{description}")
        
        yield conn
        
        db_logger.debug(f"[Transaction] 只读事务完成：{description}")
        
    except Exception as e:
        db_logger.error(f"[Transaction] 只读事务失败：{description}, 错误：{e}")
        raise
    
    finally:
        if conn:
            conn.close()


def get_connection(readonly: bool = False):
    """
    获取数据库连接（不自动管理事务）
    
    Args:
        readonly: 是否只读连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if readonly:
        return sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn


# 批量操作辅助函数
def execute_batch(cursor, sql: str, params_list: list, batch_size: int = 100):
    """
    批量执行 SQL 语句
    
    Args:
        cursor: 数据库游标
        sql: SQL 语句
        params_list: 参数列表
        batch_size: 批次大小
    
    Example:
        execute_batch(
            cursor,
            "INSERT INTO test_records (user_id, brand_name) VALUES (?, ?)",
            [(1, '品牌 A'), (2, '品牌 B'), ...],
            batch_size=100
        )
    """
    for i in range(0, len(params_list), batch_size):
        batch = params_list[i:i + batch_size]
        cursor.executemany(sql, batch)
        
        if (i // batch_size) % 10 == 0:
            db_logger.debug(f"[Batch] 已处理 {min(i + batch_size, len(params_list))}/{len(params_list)} 条记录")


# 事务统计
class TransactionStats:
    """事务统计信息"""
    
    def __init__(self):
        self.total_transactions = 0
        self.successful_transactions = 0
        self.failed_transactions = 0
        self.start_time = datetime.now()
    
    def record_success(self):
        self.total_transactions += 1
        self.successful_transactions += 1
    
    def record_failure(self):
        self.total_transactions += 1
        self.failed_transactions += 1
    
    def get_stats(self) -> dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'total': self.total_transactions,
            'successful': self.successful_transactions,
            'failed': self.failed_transactions,
            'success_rate': f"{self.successful_transactions / max(self.total_transactions, 1) * 100:.1f}%",
            'elapsed_seconds': elapsed,
            'transactions_per_second': self.total_transactions / max(elapsed, 1)
        }


# 全局统计实例
_transaction_stats = TransactionStats()


def get_transaction_stats() -> dict:
    """获取事务统计信息"""
    return _transaction_stats.get_stats()


# 装饰器：自动事务处理
def with_transaction(description: str = None):
    """
    自动事务处理装饰器
    
    Args:
        description: 事务描述
    
    Example:
        @with_transaction("保存诊断结果")
        def save_diagnosis_result(data):
            cursor.execute("INSERT INTO test_records ...")
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal description
            if description is None:
                description = f"{func.__module__}.{func.__name__}"
            
            with database_transaction(description) as conn:
                # 将连接注入到 kwargs
                kwargs['conn'] = conn
                result = func(*args, **kwargs)
                _transaction_stats.record_success()
                return result
        
        return wrapper
    
    return decorator


if __name__ == '__main__':
    # 测试事务处理
    print("="*60)
    print("DS-P1-2: 数据库事务处理上下文管理器")
    print("="*60)
    print()
    
    # 测试正常事务
    print("📋 测试 1: 正常事务提交")
    try:
        with database_transaction("测试插入") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (openid, nickname)
                VALUES (?, ?)
            """, ('test_openid_123', '测试用户'))
            print("✅ 事务提交成功")
    except Exception as e:
        print(f"❌ 事务失败：{e}")
    
    # 测试回滚
    print("\n📋 测试 2: 事务回滚")
    try:
        with database_transaction("测试回滚") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (openid, nickname)
                VALUES (?, ?)
            """, ('test_openid_456', '测试用户 2'))
            # 故意抛出异常
            raise ValueError("测试回滚")
    except Exception as e:
        print(f"✅ 事务已回滚：{e}")
    
    # 测试只读查询
    print("\n📋 测试 3: 只读查询")
    try:
        with database_readonly_transaction("测试查询") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"✅ 用户总数：{count}")
    except Exception as e:
        print(f"❌ 查询失败：{e}")
    
    # 显示统计
    print("\n📊 事务统计:")
    stats = get_transaction_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成")
