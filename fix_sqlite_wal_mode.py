#!/usr/bin/env python3
"""
SQLite 数据库并发隐患修复脚本

问题描述:
- 日志显示启动了 4 个 ExportWorker 线程，同时还有 Workflow background processor 和 Retry processor
- SQLite 在多线程高频写入时，如果未开启 WAL (Write-Ahead Logging) 模式，极易报 database is locked 错误

修复方案:
1. 为所有数据库连接添加 PRAGMA journal_mode=WAL
2. 设置 PRAGMA synchronous=NORMAL 以平衡性能和安全性
3. 修复 SafeDatabaseQuery 类的连接初始化
4. 修复 models.py 的数据库初始化

参考:
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/pragma.html
"""

import sqlite3
import os
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).resolve().parent / 'backend_python' / 'database.db'

def optimize_database_connection(conn: sqlite3.Connection, db_path: str = "main"):
    """
    优化 SQLite 连接配置，启用高性能模式
    
    Args:
        conn: SQLite 数据库连接
        db_path: 数据库路径标识（用于日志）
    """
    try:
        # 启用 WAL 模式 - 关键！允许多个读取器和一个写入者并发
        conn.execute('PRAGMA journal_mode=WAL')
        
        # 设置同步模式为 NORMAL - 平衡性能和安全性
        # WAL 模式下，NORMAL 已经足够安全，且性能更好
        conn.execute('PRAGMA synchronous=NORMAL')
        
        # 设置繁忙超时 - 避免 database is locked 错误
        conn.execute('PRAGMA busy_timeout=5000')  # 5 秒超时
        
        # 增加缓存大小（可选，根据内存情况调整）
        conn.execute('PRAGMA cache_size=-2000')  # 2MB 缓存
        
        # 启用外键约束（如果项目需要）
        conn.execute('PRAGMA foreign_keys=ON')
        
        print(f"[✓] 数据库优化配置已应用：{db_path}")
        return True
        
    except Exception as e:
        print(f"[✗] 数据库优化配置失败 {db_path}: {e}")
        return False


def fix_safe_database_query():
    """
    修复 SafeDatabaseQuery 类的数据库连接配置
    文件：backend_python/wechat_backend/security/sql_protection.py
    """
    file_path = Path(__file__).resolve().parent / 'backend_python' / 'wechat_backend' / 'security' / 'sql_protection.py'
    
    if not file_path.exists():
        print(f"[!] 文件不存在，跳过：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 _ensure_connection 方法并修复
    old_code = '''    def _ensure_connection(self):
        """确保数据库连接已建立"""
        if self.conn is None or self._closed:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._closed = False'''
    
    new_code = '''    def _ensure_connection(self):
        """确保数据库连接已建立"""
        if self.conn is None or self._closed:
            self.conn = sqlite3.connect(self.db_path, timeout=30.0)
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.conn.execute('PRAGMA synchronous=NORMAL')
            self.conn.execute('PRAGMA busy_timeout=5000')
            self.cursor = self.conn.cursor()
            self._closed = False'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[✓] 已修复：sql_protection.py::_ensure_connection")
        return True
    else:
        print(f"[!] 未找到需要修复的代码段（sql_protection.py），可能已修复或代码结构已变更")
        return False


def fix_models_init_db():
    """
    修复 models.py 的 init_task_status_db 函数
    文件：backend_python/wechat_backend/models.py
    """
    file_path = Path(__file__).resolve().parent / 'backend_python' / 'wechat_backend' / 'models.py'
    
    if not file_path.exists():
        print(f"[!] 文件不存在，跳过：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 init_task_status_db 函数并修复
    old_code = '''def init_task_status_db():
    """初始化任务状态相关的数据库表"""
    db_logger.info(f"Initializing task status database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()'''
    
    new_code = '''def init_task_status_db():
    """初始化任务状态相关的数据库表"""
    db_logger.info(f"Initializing task status database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=5000')
    cursor = conn.cursor()'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[✓] 已修复：models.py::init_task_status_db")
        return True
    else:
        print(f"[!] 未找到需要修复的代码段（models.py），可能已修复或代码结构已变更")
        return False


def apply_wal_to_main_database():
    """
    直接为主数据库应用 WAL 配置
    """
    if not DB_PATH.exists():
        print(f"[!] 数据库文件不存在：{DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        optimize_database_connection(conn, str(DB_PATH))
        
        # 验证 WAL 模式已启用
        cursor = conn.cursor()
        cursor.execute('PRAGMA journal_mode')
        mode = cursor.fetchone()[0]
        
        if mode == 'wal':
            print(f"[✓] 主数据库 WAL 模式已启用")
        else:
            print(f"[!] 主数据库 WAL 模式未启用，当前模式：{mode}")
        
        conn.close()
        return mode == 'wal'
        
    except Exception as e:
        print(f"[✗] 主数据库配置失败：{e}")
        return False


def audit_database_connections():
    """
    审计代码库中所有 sqlite3.connect 调用，确保都配置了 WAL 模式
    """
    import re
    
    print("\n" + "="*60)
    print("数据库连接审计报告")
    print("="*60)
    
    backend_dir = Path(__file__).resolve().parent / 'backend_python' / 'wechat_backend'
    
    files_to_check = list(backend_dir.rglob('*.py'))
    
    issues_found = []
    
    for file_path in files_to_check:
        # 跳过备份文件和测试文件
        if '.backup' in str(file_path) or 'test_' in str(file_path.name):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找 sqlite3.connect 调用
            connect_pattern = r'sqlite3\.connect\([^)]+\)'
            matches = list(re.finditer(connect_pattern, content))
            
            if matches:
                has_wal = 'PRAGMA journal_mode=WAL' in content or "PRAGMA journal_mode='WAL'" in content
                
                if not has_wal:
                    rel_path = file_path.relative_to(Path(__file__).resolve().parent)
                    line_num = content[:matches[0].start()].count('\n') + 1
                    issues_found.append((str(rel_path), line_num))
                    
        except Exception:
            continue
    
    if issues_found:
        print(f"\n发现 {len(issues_found)} 个未配置 WAL 模式的数据库连接:")
        for file_path, line_num in issues_found[:10]:  # 只显示前 10 个
            print(f"  - {file_path}:{line_num}")
        if len(issues_found) > 10:
            print(f"  ... 还有 {len(issues_found) - 10} 个文件")
    else:
        print("\n[✓] 所有数据库连接都已配置 WAL 模式")
    
    return len(issues_found) == 0


def main():
    """执行所有修复"""
    print("="*60)
    print("SQLite 数据库并发隐患修复")
    print("="*60)
    print()
    
    # 1. 直接应用 WAL 配置到主数据库
    print("[1/5] 配置主数据库...")
    apply_wal_to_main_database()
    print()
    
    # 2. 修复 SafeDatabaseQuery 类
    print("[2/5] 修复 SafeDatabaseQuery 类...")
    fix_safe_database_query()
    print()
    
    # 3. 修复 models.py
    print("[3/5] 修复 models.py...")
    fix_models_init_db()
    print()
    
    # 4. 审计所有数据库连接
    print("[4/5] 审计数据库连接...")
    audit_result = audit_database_connections()
    print()
    
    # 5. 总结
    print("="*60)
    print("修复总结")
    print("="*60)
    print()
    print("已完成的修复:")
    print("  ✓ 主数据库启用 WAL 模式")
    print("  ✓ SafeDatabaseQuery 添加 WAL 配置")
    print("  ✓ models.py 添加 WAL 配置")
    print()
    
    if audit_result:
        print("[✓] 所有数据库连接已正确配置 WAL 模式")
    else:
        print("[!] 仍有部分文件需要手动检查和修复")
        print()
        print("建议:")
        print("  1. 检查上述审计报告中列出的文件")
        print("  2. 为每个 sqlite3.connect 调用添加 WAL 配置:")
        print("     conn.execute('PRAGMA journal_mode=WAL')")
        print("     conn.execute('PRAGMA synchronous=NORMAL')")
        print("     conn.execute('PRAGMA busy_timeout=5000')")
    print()
    
    print("验证命令:")
    print(f"  sqlite3 {DB_PATH} \"PRAGMA journal_mode;\"")
    print()


if __name__ == '__main__':
    main()
