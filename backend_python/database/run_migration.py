#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌诊断报告存储架构优化 - 数据库迁移执行脚本

使用方法:
    python3 run_migration.py

功能:
1. 创建数据库表
2. 创建索引
3. 迁移历史数据
4. 验证迁移结果
"""

import sqlite3
import os
import sys
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def run_migration(migration_file: str) -> dict:
    """执行单个迁移文件"""
    print(f"\n{'='*60}")
    print(f"执行迁移：{migration_file}")
    print('='*60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 读取 SQL 文件
        with open(os.path.join(MIGRATIONS_DIR, migration_file), 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 【P0 修复 - 2026-03-11】检查是否是添加字段的迁移，如果是则先检查字段是否存在
        if '005_add_geo_data_field' in migration_file:
            cursor.execute("""
                SELECT COUNT(*) FROM PRAGMA_TABLE_INFO('diagnosis_results')
                WHERE name = 'geo_data'
            """)
            exists = cursor.fetchone()[0]
            if exists > 0:
                print("ℹ️  geo_data 字段已存在，跳过此迁移")
                return {'status': 'skipped', 'file': migration_file, 'reason': 'Field already exists'}

        # 执行 SQL
        cursor.executescript(sql_script)
        conn.commit()

        # 获取结果
        cursor.execute("SELECT '✅ 迁移成功' AS status")
        result = cursor.fetchone()

        print(f"结果：{result[0]}")

        return {'status': 'success', 'file': migration_file}

    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        # 【P0 修复】如果是"duplicate column"错误，认为迁移已成功（字段已存在）
        if 'duplicate column' in error_msg.lower():
            print(f"ℹ️  字段已存在，跳过此迁移")
            return {'status': 'skipped', 'file': migration_file, 'reason': error_msg}

        print(f"❌ 迁移失败：{e}")
        return {'status': 'error', 'file': migration_file, 'error': error_msg}

    finally:
        conn.close()


def verify_migration():
    """验证迁移结果"""
    print(f"\n{'='*60}")
    print("验证迁移结果")
    print('='*60)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        tables = ['diagnosis_reports', 'diagnosis_results', 'diagnosis_analysis', 'diagnosis_snapshots']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} 条记录")
        
        # 检查索引
        cursor.execute("""
            SELECT name, tbl_name 
            FROM sqlite_master 
            WHERE type = 'index' 
            AND tbl_name IN ('diagnosis_reports', 'diagnosis_results', 'diagnosis_analysis', 'diagnosis_snapshots')
        """)
        indexes = cursor.fetchall()
        print(f"\n✅ 创建索引：{len(indexes)} 个")
        
        # 检查数据完整性
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT execution_id) as unique_executions,
                COUNT(CASE WHEN checksum IS NOT NULL AND checksum != '' THEN 1 END) as with_checksum
            FROM diagnosis_reports
        """)
        result = cursor.fetchone()
        print(f"\n📊 数据完整性:")
        print(f"   - 唯一 execution_id: {result[0]}")
        print(f"   - 有校验和的记录：{result[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败：{e}")
        return False
        
    finally:
        conn.close()


def main():
    """主函数"""
    print("="*60)
    print("品牌诊断报告存储架构优化 - 数据库迁移")
    print("="*60)
    print(f"数据库路径：{DB_PATH}")
    print(f"迁移文件目录：{MIGRATIONS_DIR}")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查迁移文件
    migration_files = sorted([
        f for f in os.listdir(MIGRATIONS_DIR) 
        if f.endswith('.sql')
    ])
    
    if not migration_files:
        print(f"\n❌ 未找到迁移文件：{MIGRATIONS_DIR}")
        return 1
    
    print(f"\n找到 {len(migration_files)} 个迁移文件:")
    for f in migration_files:
        print(f"  - {f}")
    
    # 执行迁移
    results = []
    for migration_file in migration_files:
        result = run_migration(migration_file)
        results.append(result)
        
        if result['status'] == 'error':
            print(f"\n❌ 迁移中断：{migration_file}")
            print(f"错误：{result['error']}")
            return 1
    
    # 验证迁移
    if not verify_migration():
        print("\n❌ 迁移验证失败")
        return 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print("迁移总结")
    print('='*60)
    print(f"✅ 所有迁移执行成功")
    print(f"📊 迁移文件：{len(results)} 个")
    print(f"⏰ 完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
