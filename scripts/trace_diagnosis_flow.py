#!/usr/bin/env python3
"""
诊断数据流追踪脚本 - 第 5 次深度分析

用途：
1. 实际运行一次诊断
2. 追踪数据在每个环节的状态
3. 定位数据在哪里丢失

使用方法：
python scripts/trace_diagnosis_flow.py
"""

import sys
import os
import json
import time

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_python'))

from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
)
from wechat_backend.database_connection_pool import get_db_pool


def print_separator(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")


def check_wal_status():
    """检查 WAL 状态"""
    print_separator("0. WAL 状态检查")
    
    pool = get_db_pool()
    conn = pool.get_connection()
    try:
        # 检查日志模式
        result = conn.execute('PRAGMA journal_mode').fetchone()
        print(f"日志模式：{result[0]}")
        
        # 检查 WAL 文件状态
        result = conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        print(f"WAL 检查点状态：{result}")
        print(f"  - 检查点成功：{result[0] == 0}")
        print(f"  - WAL 页数：{result[1]}")
        print(f"  - 已检查点页数：{result[2]}")
        
    finally:
        pool.return_connection(conn)


def check_recent_executions(limit=5):
    """检查最近的执行记录"""
    print_separator("1. 最近的诊断执行记录")
    
    report_repo = DiagnosisReportRepository()
    result_repo = DiagnosisResultRepository()
    
    pool = get_db_pool()
    conn = pool.get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询最近的执行
        cursor.execute('''
            SELECT execution_id, status, progress, stage, is_completed, 
                   created_at, completed_at,
                   (SELECT COUNT(*) FROM diagnosis_results r 
                    WHERE r.execution_id = p.execution_id) as result_count
            FROM diagnosis_reports p
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ 没有找到任何诊断执行记录")
            return None
        
        for i, row in enumerate(rows, 1):
            print(f"\n[执行 {i}]")
            print(f"  execution_id: {row['execution_id']}")
            print(f"  status: {row['status']}")
            print(f"  progress: {row['progress']}")
            print(f"  stage: {row['stage']}")
            print(f"  is_completed: {row['is_completed']}")
            print(f"  result_count: {row['result_count']}")
            print(f"  created_at: {row['created_at']}")
            if row['completed_at']:
                print(f"  completed_at: {row['completed_at']}")
            
            # 如果有结果，显示第一条
            if row['result_count'] > 0:
                cursor.execute('''
                    SELECT brand, question, model, quality_score
                    FROM diagnosis_results
                    WHERE execution_id = ?
                    LIMIT 1
                ''', (row['execution_id'],))
                first_result = cursor.fetchone()
                if first_result:
                    print(f"  第 1 条结果：brand={first_result['brand']}, "
                          f"question={first_result['question'][:30]}..., "
                          f"score={first_result['quality_score']}")
        
        return rows[0]['execution_id'] if rows else None
        
    finally:
        pool.return_connection(conn)


def trace_data_flow(execution_id):
    """追踪特定执行的数据流"""
    print_separator(f"2. 数据流追踪：{execution_id}")
    
    pool = get_db_pool()
    conn = pool.get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 检查报告
        print(f"\n[1/5] 检查诊断报告...")
        cursor.execute('''
            SELECT * FROM diagnosis_reports
            WHERE execution_id = ?
        ''', (execution_id,))
        report = cursor.fetchone()
        
        if not report:
            print(f"  ❌ 报告不存在")
            return
        print(f"  ✅ 报告存在")
        print(f"     status={report['status']}, progress={report['progress']}, "
              f"stage={report['stage']}, is_completed={report['is_completed']}")
        
        # 2. 检查结果（提交前）
        print(f"\n[2/5] 检查诊断结果（不提交）...")
        cursor.execute('''
            SELECT COUNT(*) FROM diagnosis_results
            WHERE execution_id = ?
        ''', (execution_id,))
        count = cursor.fetchone()[0]
        print(f"  结果数量：{count}")
        
        if count > 0:
            cursor.execute('''
                SELECT brand, question, model, quality_score, response_content
                FROM diagnosis_results
                WHERE execution_id = ?
                LIMIT 3
            ''', (execution_id,))
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"  结果 {i}: brand={row['brand']}, score={row['quality_score']}, "
                      f"response_content 长度={len(row['response_content']) if row['response_content'] else 0}")
        else:
            print(f"  ❌ 结果为空 - 这是数据丢失的关键证据！")
        
        # 3. 强制 WAL 检查点
        print(f"\n[3/5] 执行 WAL 检查点...")
        cursor.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        print(f"  ✅ WAL 检查点完成")
        
        # 4. 检查 WAL 检查点后的结果
        print(f"\n[4/5] 检查 WAL 检查点后的结果...")
        cursor.execute('''
            SELECT COUNT(*) FROM diagnosis_results
            WHERE execution_id = ?
        ''', (execution_id,))
        count_after = cursor.fetchone()[0]
        print(f"  结果数量：{count_after}")
        
        if count_after == 0:
            print(f"  ❌ WAL 检查点后仍然为空！说明数据根本没有保存！")
        elif count_after != count:
            print(f"  ⚠️ 数量变化：{count} -> {count_after}")
        
        # 5. 检查 execution_store（内存）
        print(f"\n[5/5] 检查 execution_store（内存）...")
        from wechat_backend.state_manager import get_state_manager
        store = {}
        state_manager = get_state_manager(store)
        state = state_manager.get_state(execution_id)
        
        if state:
            print(f"  ✅ execution_store 中有状态")
            print(f"     status={state.get('status')}, progress={state.get('progress')}")
            
            # 检查是否有 results
            if execution_id in store:
                stored_results = store[execution_id].get('results', [])
                print(f"     内存中的 results 数量：{len(stored_results)}")
                if stored_results:
                    print(f"     第 1 条结果：brand={stored_results[0].get('brand')}")
            else:
                print(f"  ❌ execution_store 中没有此 execution_id")
        else:
            print(f"  ❌ execution_store 中没有状态")
        
    finally:
        pool.return_connection(conn)


def main():
    print("\n开始诊断数据流追踪...")
    
    # 0. 检查 WAL 状态
    check_wal_status()
    
    # 1. 检查最近的执行
    latest_execution_id = check_recent_executions(limit=5)
    
    if not latest_execution_id:
        print("\n❌ 没有可追踪的执行记录")
        print("\n请先运行一次诊断，然后再运行此脚本")
        return
    
    # 2. 追踪数据流
    trace_data_flow(latest_execution_id)
    
    print_separator("总结")
    print("请检查以上输出，定位数据在哪个环节丢失：")
    print("  1. 如果报告中 result_count=0，说明数据未保存")
    print("  2. 如果 WAL 检查点后仍然为 0，说明数据根本没有写入")
    print("  3. 如果内存中有但数据库中没有，说明事务未提交")
    print()


if __name__ == '__main__':
    main()
