#!/usr/bin/env python3
# =============================================================================
# 测试数据清理脚本
# =============================================================================
# 功能：
# 1. 清理测试数据库文件
# 2. 清理数据库中的测试数据
# 3. 清理测试缓存
#
# 使用方式：
#   python scripts/cleanup_test_data.py [--all] [--dry-run]
#
# 参数：
#   --all     清理所有测试数据（包括主数据库）
#   --dry-run 只显示将要清理的内容，不实际删除
#
# 作者：系统架构组
# 日期：2026-02-27
# 版本：1.0.0
# =============================================================================

import sqlite3
import os
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_test_databases(dry_run: bool = False):
    """清理测试数据库文件"""
    print("清理测试数据库文件...")
    test_db_pattern = "test_*.db"
    deleted_count = 0
    
    # 查找所有测试数据库
    search_paths = ['/tmp', '/var/tmp', os.getcwd()]
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
            
        for root, dirs, files in os.walk(search_path):
            # 跳过太深的目录
            if root.count(os.sep) > 5:
                continue
                
            for file in files:
                if file.startswith('test_') and file.endswith('.db'):
                    filepath = os.path.join(root, file)
                    
                    # 检查文件修改时间
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        age = datetime.now() - mtime
                        
                        if dry_run:
                            print(f"  [将删除] {filepath} (修改于：{mtime}, 距今：{age})")
                            deleted_count += 1
                        else:
                            # 只删除超过 1 小时的文件
                            if age > timedelta(hours=1):
                                os.remove(filepath)
                                print(f"  [已删除] {filepath}")
                                deleted_count += 1
                    except Exception as e:
                        print(f"  [错误] 无法处理 {filepath}: {e}")
    
    if dry_run:
        print(f"  将删除 {deleted_count} 个测试数据库文件")
    else:
        print(f"  已删除 {deleted_count} 个测试数据库文件")
    
    return deleted_count


def cleanup_test_data_in_db(db_path: str, dry_run: bool = False):
    """清理数据库中的测试数据"""
    if not os.path.exists(db_path):
        print(f"数据库不存在：{db_path}")
        return 0
    
    print(f"清理数据库中的测试数据：{db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        deleted_counts = {}
        
        # 删除测试用户的数据
        tables_to_clean = [
            ('diagnosis_reports', 'user_id'),
            ('diagnosis_reports', 'execution_id'),
            ('diagnosis_results', 'execution_id'),
            ('api_call_logs', 'execution_id'),
            ('dead_letter_queue', 'execution_id')
        ]
        
        for table, field in tables_to_clean:
            try:
                # 检查表是否存在
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    continue
                
                # 删除测试数据
                if field == 'user_id':
                    query = f"DELETE FROM {table} WHERE {field} LIKE 'test_%'"
                else:
                    query = f"DELETE FROM {table} WHERE {field} LIKE 'test_%' OR {field} LIKE 'concurrent_test_%'"
                
                if dry_run:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} LIKE 'test_%'")
                    count = cursor.fetchone()[0]
                    deleted_counts[f"{table}.{field}"] = count
                else:
                    cursor.execute(query)
                    deleted_counts[f"{table}.{field}"] = cursor.rowcount
            except Exception as e:
                print(f"  [警告] 清理 {table}.{field} 时出错：{e}")
        
        if not dry_run:
            conn.commit()
        
        conn.close()
        
        # 输出清理结果
        if dry_run:
            print("  将删除的测试数据：")
            for key, count in deleted_counts.items():
                if count > 0:
                    print(f"    - {key}: {count} 条记录")
        else:
            total = sum(deleted_counts.values())
            print(f"  已删除 {total} 条测试数据")
        
        return sum(deleted_counts.values())
        
    except Exception as e:
        print(f"  [错误] 清理数据库失败：{e}")
        return 0


def cleanup_test_cache(dry_run: bool = False):
    """清理测试缓存"""
    print("清理测试缓存...")
    
    cache_dirs = [
        '.pytest_cache',
        '__pycache__',
        'tests/__pycache__',
        'tests/integration/__pycache__',
    ]
    
    deleted_count = 0
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            if dry_run:
                print(f"  [将删除] {cache_dir}/")
                deleted_count += 1
            else:
                try:
                    shutil.rmtree(cache_dir)
                    print(f"  [已删除] {cache_dir}/")
                    deleted_count += 1
                except Exception as e:
                    print(f"  [错误] 无法删除 {cache_dir}: {e}")
    
    # 清理 .pyc 文件
    for root, dirs, files in os.walk('.'):
        # 跳过太深的目录
        if root.count(os.sep) > 5:
            continue
            
        # 跳过隐藏目录
        if '/.' in root or root.startswith('.'):
            if root != './.venv':
                continue
        
        for file in files:
            if file.endswith('.pyc'):
                filepath = os.path.join(root, file)
                if dry_run:
                    deleted_count += 1
                else:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except:
                        pass
    
    if dry_run:
        print(f"  将清理 {deleted_count} 个缓存项")
    else:
        print(f"  已清理 {deleted_count} 个缓存项")
    
    return deleted_count


def main():
    parser = argparse.ArgumentParser(description='清理测试数据')
    parser.add_argument('--all', action='store_true', help='清理所有测试数据（包括主数据库）')
    parser.add_argument('--dry-run', action='store_true', help='只显示将要清理的内容，不实际删除')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("测试数据清理")
    print("=" * 60)
    print()
    
    if args.dry_run:
        print("[预览模式] 以下文件和数据将被删除：")
        print()
    
    total_cleaned = 0
    
    # 清理测试数据库文件
    count = cleanup_test_databases(dry_run=args.dry_run)
    total_cleaned += count
    print()
    
    # 清理测试缓存
    count = cleanup_test_cache(dry_run=args.dry_run)
    total_cleaned += count
    print()
    
    # 清理主数据库中的测试数据
    if args.all:
        main_db_paths = [
            '/data/diagnosis.db',
            'data/diagnosis.db',
            'backend_python/data/diagnosis.db',
        ]
        
        for db_path in main_db_paths:
            if os.path.exists(db_path):
                count = cleanup_test_data_in_db(db_path, dry_run=args.dry_run)
                total_cleaned += count
                print()
    else:
        print("提示：使用 --all 参数清理主数据库中的测试数据")
        print()
    
    # 清理临时测试文件
    test_report_dir = 'test_reports/integration'
    if os.path.exists(test_report_dir) and not args.dry_run:
        # 保留最新的报告，删除旧的
        try:
            files = os.listdir(test_report_dir)
            if len(files) > 10:
                # 按修改时间排序，删除最旧的文件
                files_with_mtime = [
                    (f, os.path.getmtime(os.path.join(test_report_dir, f)))
                    for f in files
                ]
                files_with_mtime.sort(key=lambda x: x[1], reverse=True)
                
                for f, _ in files_with_mtime[10:]:
                    filepath = os.path.join(test_report_dir, f)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        total_cleaned += 1
                        if args.verbose:
                            print(f"  [已删除] {filepath}")
        except Exception as e:
            if args.verbose:
                print(f"  [警告] 清理测试报告时出错：{e}")
    
    print("=" * 60)
    if args.dry_run:
        print(f"预览：将清理 {total_cleaned} 项测试数据")
    else:
        print(f"完成：已清理 {total_cleaned} 项测试数据")
    print("=" * 60)
    
    if not args.dry_run:
        print()
        print("提示：")
        print("  - 运行测试：./scripts/run_integration_tests.sh")
        print("  - 预览清理：python scripts/cleanup_test_data.py --dry-run")
        print("  - 完全清理：python scripts/cleanup_test_data.py --all")


if __name__ == '__main__':
    main()
