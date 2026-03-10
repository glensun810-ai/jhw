#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看工具 - 用于浏览诊断报告数据库

用法:
    python view_database.py                    # 查看所有表概览
    python view_database.py --table diagnosis_reports    # 查看指定表
    python view_database.py --report <execution_id>      # 查看特定报告
    python view_database.py --stats            # 查看统计信息
"""

import sqlite3
import argparse
import json
from datetime import datetime
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / 'backend_python' / 'database.db'


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    return conn


def list_tables():
    """列出所有表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n📊 数据库文件：{DB_PATH}")
    print(f"📋 表数量：{len(tables)}")
    print("\n表列表:")
    for table in tables:
        print(f"  - {table}")
    return tables


def show_table_schema(table_name: str):
    """显示表结构"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    
    print(f"\n📐 表结构：{table_name}")
    print("-" * 60)
    print(f"{'列名':<30} {'类型':<15} {'非空':<8} {'默认值':<15}")
    print("-" * 60)
    for col in columns:
        not_null = "✓" if col[3] else ""
        default = col[4] if col[4] else "-"
        print(f"{col[1]:<30} {col[2]:<15} {not_null:<8} {default:<15}")


def show_table_data(table_name: str, limit: int = 10):
    """显示表数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取列名
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    columns = [description[0] for description in cursor.description]
    
    # 获取数据
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT {limit}" if 'created_at' in columns 
                   else f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n📄 表数据：{table_name} (最近 {len(rows)} 条)")
    print("-" * 80)
    
    for i, row in enumerate(rows, 1):
        print(f"\n[记录 {i}]")
        for col_name, value in zip(columns, row):
            if value and len(str(value)) > 100:
                value = str(value)[:100] + "..."
            print(f"  {col_name}: {value}")


def show_report(execution_id: str):
    """显示特定诊断报告详情"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 查询报告
    cursor.execute("""
        SELECT execution_id, user_id, status, brand_name, 
               competitor_brands, selected_models, custom_questions,
               progress, stage, created_at, updated_at
        FROM diagnosis_reports 
        WHERE execution_id = ?
    """, (execution_id,))
    report = cursor.fetchone()
    
    if not report:
        print(f"❌ 未找到报告：{execution_id}")
        conn.close()
        return
    
    print(f"\n📊 诊断报告详情")
    print("=" * 80)
    print(f"执行 ID:      {report['execution_id']}")
    print(f"用户 ID:      {report['user_id']}")
    print(f"状态：{report['status']}")
    print(f"进度：{report['progress']}%")
    print(f"阶段：{report['stage']}")
    print(f"品牌名称：{report['brand_name']}")
    print(f"竞品列表：{report['competitor_brands']}")
    print(f"AI 模型：{report['selected_models']}")
    print(f"问题：{report['custom_questions']}")
    print(f"创建时间：{report['created_at']}")
    print(f"更新时间：{report['updated_at']}")
    
    # 查询诊断结果
    cursor.execute("""
        SELECT question, response_content, quality_score, sentiment, model
        FROM diagnosis_results 
        WHERE execution_id = ?
        ORDER BY id
    """, (execution_id,))
    results = cursor.fetchall()
    
    if results:
        print(f"\n📋 诊断结果 ({len(results)} 条):")
        print("-" * 80)
        for i, result in enumerate(results, 1):
            print(f"\n[问题 {i}]")
            print(f"  问题：{result['question']}")
            response = result['response_content']
            print(f"  回答：{response[:100]}..." if len(str(response)) > 100 else f"  回答：{response}")
            print(f"  质量分数：{result['quality_score']}")
            print(f"  情感：{result['sentiment']}")
            print(f"  模型：{result['model']}")
    
    # 查询分析数据
    cursor.execute("""
        SELECT analysis_type, analysis_data
        FROM diagnosis_analysis 
        WHERE execution_id = ?
    """, (execution_id,))
    analyses = cursor.fetchall()
    
    if analyses:
        print(f"\n📈 分析数据 ({len(analyses)} 条):")
        print("-" * 80)
        for analysis in analyses:
            print(f"\n[{analysis['analysis_type']}]")
            try:
                data = json.loads(analysis['analysis_data'])
                print(f"  {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            except:
                print(f"  {analysis['analysis_data'][:200]}...")
    
    conn.close()


def show_stats():
    """显示统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"\n📊 数据库统计信息")
    print("=" * 80)
    
    # 报告统计
    cursor.execute("SELECT COUNT(*) as count, status FROM diagnosis_reports GROUP BY status")
    report_stats = cursor.fetchall()
    print(f"\n诊断报告统计:")
    for stat in report_stats:
        print(f"  {stat['status']}: {stat['count']} 份")
    
    # 最近报告
    cursor.execute("""
        SELECT execution_id, brand_name, created_at 
        FROM diagnosis_reports 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_reports = cursor.fetchall()
    print(f"\n最近 5 份报告:")
    for report in recent_reports:
        print(f"  {report['created_at']} - {report['brand_name']} ({report['execution_id'][:8]}...)")
    
    # 结果统计
    cursor.execute("SELECT COUNT(*) as count FROM diagnosis_results")
    result_count = cursor.fetchone()['count']
    print(f"\n诊断结果总数：{result_count} 条")
    
    # 分析统计
    cursor.execute("SELECT COUNT(*) as count FROM diagnosis_analysis")
    analysis_count = cursor.fetchone()['count']
    print(f"分析数据总数：{analysis_count} 条")
    
    # 数据库大小
    db_size = Path(DB_PATH).stat().st_size / 1024 / 1024  # MB
    print(f"\n数据库大小：{db_size:.2f} MB")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='SQLite 数据库查看工具')
    parser.add_argument('--table', '-t', help='查看指定表的数据')
    parser.add_argument('--schema', '-s', action='store_true', help='显示表结构')
    parser.add_argument('--report', '-r', help='查看特定诊断报告 (execution_id)')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--limit', '-l', type=int, default=10, help='数据显示条数限制')
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return
    
    if args.report:
        show_report(args.report)
    elif args.table:
        if args.schema:
            show_table_schema(args.table)
        else:
            show_table_data(args.table, args.limit)
    elif args.stats:
        show_stats()
    else:
        list_tables()
        print("\n💡 使用提示:")
        print("  --table <表名>     查看指定表的数据")
        print("  --schema           显示表结构")
        print("  --report <ID>      查看特定诊断报告")
        print("  --stats            显示统计信息")


if __name__ == '__main__':
    main()
