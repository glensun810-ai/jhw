#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断报告数据可视化查看器

功能：
1. 以表格形式展示所有诊断报告
2. 显示报告详细数据
3. 检查数据完整性
4. 导出报告数据为 JSON

使用方法：
    python view_diagnosis_reports.py              # 查看所有报告
    python view_diagnosis_reports.py --latest 5   # 查看最新 5 条
    python view_diagnosis_reports.py --detail <execution_id>  # 查看详情
    python view_diagnosis_reports.py --export <execution_id>  # 导出 JSON
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


# ==================== 数据库连接 ====================

def get_db_connection():
    """获取数据库连接"""
    db_path = Path(__file__).parent / 'database.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ==================== 数据查询 ====================

def get_all_reports(limit: int = 20) -> List[sqlite3.Row]:
    """获取所有诊断报告（默认最新 20 条）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id,
            execution_id,
            user_id,
            brand_name,
            competitor_brands,
            selected_models,
            custom_questions,
            status,
            progress,
            stage,
            is_completed,
            created_at,
            updated_at,
            completed_at,
            data_schema_version,
            server_version
        FROM diagnosis_reports
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    reports = cursor.fetchall()
    conn.close()
    return reports


def get_report_by_execution_id(execution_id: str) -> Optional[sqlite3.Row]:
    """根据 execution_id 获取报告详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM diagnosis_reports
        WHERE execution_id = ?
    ''', (execution_id,))
    
    report = cursor.fetchone()
    conn.close()
    return report


def get_report_snapshots(execution_id: str) -> List[sqlite3.Row]:
    """获取报告的快照历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id,
            execution_id,
            user_id,
            report_data,
            report_hash,
            size_kb,
            storage_timestamp,
            report_version
        FROM report_snapshots
        WHERE execution_id = ?
        ORDER BY storage_timestamp DESC
    ''', (execution_id,))
    
    snapshots = cursor.fetchall()
    conn.close()
    return snapshots


def get_task_status(execution_id: str) -> Optional[sqlite3.Row]:
    """获取任务状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM task_statuses
        WHERE task_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
    ''', (execution_id,))
    
    status = cursor.fetchone()
    conn.close()
    return status


# ==================== 数据展示 ====================

def print_table_header():
    """打印表格头部"""
    print("\n" + "="*160)
    print(f"{'ID':<5} {'Execution ID':<38} {'品牌':<15} {'竞品数':<6} {'状态':<12} {'进度':<6} {'阶段':<15} {'完成':<6} {'创建时间':<22}")
    print("="*160)


def print_report_row(report: sqlite3.Row):
    """打印单行报告数据"""
    competitor_count = len(json.loads(report['competitor_brands']) or [])
    is_completed = '✅' if report['is_completed'] else '❌'
    
    # 截断过长的 execution_id
    exec_id = report['execution_id']
    if len(exec_id) > 36:
        exec_id = exec_id[:32] + '...'
    
    print(f"{report['id']:<5} {exec_id:<38} {report['brand_name']:<15} {competitor_count:<6} {report['status']:<12} {report['progress']:<6} {report['stage']:<15} {is_completed:<6} {report['created_at']:<22}")


def display_reports_summary(reports: List[sqlite3.Row]):
    """显示报告摘要表格"""
    print(f"\n📊 诊断报告列表 (共 {len(reports)} 条)\n")
    
    if not reports:
        print("⚠️  没有找到诊断报告")
        return
    
    print_table_header()
    
    for report in reports:
        print_report_row(report)
    
    print("="*160)


def display_report_detail(report: sqlite3.Row):
    """显示报告详细信息"""
    print("\n" + "="*160)
    print("📋 诊断报告详细信息")
    print("="*160)
    
    print(f"\n【基本信息】")
    print(f"  Report ID:      {report['id']}")
    print(f"  Execution ID:   {report['execution_id']}")
    print(f"  User ID:        {report['user_id']}")
    print(f"  品牌名称：      {report['brand_name']}")
    print(f"  数据版本：      {report['data_schema_version']}")
    print(f"  服务器版本：    {report['server_version']}")
    
    print(f"\n【诊断配置】")
    
    # 竞品列表
    competitor_brands = json.loads(report['competitor_brands']) or []
    print(f"  竞品数量：      {len(competitor_brands)}")
    if competitor_brands:
        print(f"  竞品列表：      {', '.join(competitor_brands)}")
    
    # AI 模型选择
    selected_models_raw = json.loads(report['selected_models']) or []
    # selected_models 可能是字符串列表或字典列表
    selected_models = []
    for m in selected_models_raw:
        if isinstance(m, dict):
            selected_models.append(m.get('name', m.get('id', str(m))))
        else:
            selected_models.append(str(m))
    
    print(f"  AI 平台数量：    {len(selected_models)}")
    if selected_models:
        print(f"  AI 平台：       {', '.join(selected_models)}")
    
    # 自定义问题
    custom_questions = json.loads(report['custom_questions']) or []
    print(f"  问题数量：      {len(custom_questions)}")
    if custom_questions:
        for i, q in enumerate(custom_questions, 1):
            question_text = q.get('text', '') if isinstance(q, dict) else str(q)
            print(f"                  {i}. {question_text[:60]}{'...' if len(question_text) > 60 else ''}")
    
    print(f"\n【执行状态】")
    print(f"  状态：          {report['status']}")
    print(f"  进度：          {report['progress']}%")
    print(f"  阶段：          {report['stage']}")
    print(f"  是否完成：      {'✅ 是' if report['is_completed'] else '❌ 否'}")
    
    print(f"\n【时间戳】")
    print(f"  创建时间：      {report['created_at']}")
    print(f"  更新时间：      {report['updated_at']}")
    print(f"  完成时间：      {report['completed_at'] or 'N/A'}")
    
    # 从快照表获取报告数据
    snapshots = get_report_snapshots(report['execution_id'])
    if snapshots:
        print(f"\n【报告数据 (来自 report_snapshots 表)】")
        try:
            latest_snapshot = snapshots[0]
            report_data = json.loads(latest_snapshot['report_data'])
            display_report_data_summary(report_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"  ⚠️  报告数据解析失败：{e}")
    else:
        print(f"\n【报告数据】")
        print(f"  ⚠️  未找到报告快照数据")
    
    print("\n" + "="*160)


def display_report_data_summary(report_data: Dict[str, Any]):
    """显示报告数据摘要"""
    print(f"  报告版本：      {report_data.get('reportVersion', 'N/A')}")
    print(f"  生成时间：      {report_data.get('generateTime', 'N/A')}")
    
    # 维度分析
    dimensions = report_data.get('dimensions', [])
    print(f"  分析维度数：    {len(dimensions)}")
    
    if dimensions:
        print(f"  维度列表：")
        for dim in dimensions:
            dim_name = dim.get('dimension', 'N/A')
            status = dim.get('status', 'N/A')
            ai_count = len(dim.get('ai_responses', []))
            print(f"    - {dim_name:<20} 状态：{status:<12} AI 回答数：{ai_count}")
    
    # 质量评分
    quality_score = report_data.get('quality_score', {})
    if quality_score:
        print(f"\n  质量评分：")
        overall = quality_score.get('overall_score', 'N/A')
        print(f"    总体评分：      {overall}")
        
        dimension_scores = quality_score.get('dimension_scores', {})
        if dimension_scores:
            print(f"    维度评分：")
            for dim_name, score in dimension_scores.items():
                print(f"      {dim_name:<20} {score}")
    
    # 聚合结果
    aggregated = report_data.get('aggregated', [])
    if aggregated:
        print(f"\n  聚合结果：")
        for agg in aggregated:
            dim = agg.get('dimension', 'N/A')
            status = agg.get('status', 'N/A')
            print(f"    - {dim:<20} 状态：{status}")


def display_task_status(status: Optional[sqlite3.Row]):
    """显示任务状态"""
    print("\n【任务状态 (task_statuses 表)】")
    
    if not status:
        print("  ⚠️  未找到任务状态记录")
        return
    
    print(f"  阶段：          {status['stage']}")
    print(f"  进度：          {status['progress']}%")
    print(f"  状态文本：      {status['status_text']}")
    print(f"  已完成：        {status['completed_count']}/{status['total_count']}")
    print(f"  是否完成：      {'✅ 是' if status['is_completed'] else '❌ 否'}")
    print(f"  更新时间：      {status['updated_at']}")


def display_snapshots(snapshots: List[sqlite3.Row]):
    """显示报告快照历史"""
    print("\n【报告快照历史 (report_snapshots 表)】")
    
    if not snapshots:
        print("  ⚠️  未找到快照记录")
        return
    
    print(f"  快照数量：      {len(snapshots)}")
    print(f"\n  {'ID':<5} {'版本':<10} {'时间戳':<22} {'大小 (KB)':<10} {'哈希值':<20}")
    print("  " + "-"*80)
    
    for snapshot in snapshots:
        report_hash = snapshot['report_hash'] or 'N/A'
        if len(report_hash) > 18:
            report_hash = report_hash[:16] + '...'
        
        print(f"  {snapshot['id']:<5} {snapshot['report_version']:<10} {snapshot['storage_timestamp']:<22} {snapshot['size_kb']:<10} {report_hash:<20}")


def check_data_integrity(report: sqlite3.Row, snapshots: List = None) -> List[str]:
    """检查数据完整性"""
    issues = []
    
    # 检查必填字段
    required_fields = ['execution_id', 'user_id', 'brand_name', 'status', 'stage']
    for field in required_fields:
        if not report[field]:
            issues.append(f"❌ 必填字段缺失：{field}")
    
    # 检查 JSON 字段
    json_fields = ['competitor_brands', 'selected_models', 'custom_questions']
    for field in json_fields:
        if report[field]:
            try:
                json.loads(report[field])
            except (json.JSONDecodeError, TypeError):
                issues.append(f"❌ JSON 字段解析失败：{field}")
    
    # 检查状态一致性
    if report['is_completed'] and report['status'] != 'completed':
        issues.append(f"⚠️  状态不一致：is_completed=true 但 status={report['status']}")
    
    if report['progress'] == 100 and report['status'] not in ['completed', 'failed']:
        issues.append(f"⚠️  进度与状态不匹配：progress=100 但 status={report['status']}")
    
    # 检查是否有快照数据
    if snapshots is not None and not snapshots:
        issues.append("⚠️  没有报告快照数据 (report_snapshots 表)")
    
    # 检查快照数据
    if snapshots:
        try:
            report_data = json.loads(snapshots[0]['report_data'])
            if 'dimensions' in report_data and not report_data['dimensions']:
                issues.append("⚠️  报告数据中 dimensions 为空数组")
        except (json.JSONDecodeError, TypeError):
            issues.append("❌ 快照数据解析失败")
    
    return issues


def display_integrity_check(issues: List[str]):
    """显示数据完整性检查结果"""
    print("\n【数据完整性检查】")
    
    if not issues:
        print("  ✅ 数据完整性检查通过")
    else:
        print(f"  发现 {len(issues)} 个问题：")
        for issue in issues:
            print(f"    {issue}")


def export_report_to_json(report: sqlite3.Row, snapshots: List[sqlite3.Row], output_path: str):
    """导出报告为 JSON"""
    # 转换 Row 为字典
    report_dict = dict(report)
    
    # 解析 JSON 字段
    for field in ['competitor_brands', 'selected_models', 'custom_questions']:
        if report_dict[field]:
            try:
                report_dict[field] = json.loads(report_dict[field])
            except (json.JSONDecodeError, TypeError):
                pass
    
    # 添加快照数据
    if snapshots:
        try:
            report_dict['report_data'] = json.loads(snapshots[0]['report_data'])
            report_dict['snapshots_count'] = len(snapshots)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已导出到：{output_path}")


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(description='诊断报告数据可视化查看器')
    parser.add_argument('--latest', '-l', type=int, default=20, help='显示最新 N 条报告')
    parser.add_argument('--detail', '-d', type=str, help='显示指定 execution_id 的报告详情')
    parser.add_argument('--export', '-e', type=str, help='导出指定 execution_id 的报告为 JSON')
    parser.add_argument('--check', '-c', action='store_true', help='检查数据完整性')
    
    args = parser.parse_args()
    
    if args.detail:
        # 显示详情
        report = get_report_by_execution_id(args.detail)
        if not report:
            print(f"❌ 未找到报告：{args.detail}")
            return
        
        display_report_detail(report)
        
        # 显示任务状态
        task_status = get_task_status(args.detail)
        display_task_status(task_status)
        
        # 显示快照历史
        snapshots = get_report_snapshots(args.detail)
        display_snapshots(snapshots)
        
        # 数据完整性检查
        if args.check:
            issues = check_data_integrity(report, snapshots)
            display_integrity_check(issues)
    
    elif args.export:
        # 导出报告
        report = get_report_by_execution_id(args.export)
        if not report:
            print(f"❌ 未找到报告：{args.export}")
            return
        
        snapshots = get_report_snapshots(args.export)
        output_path = f"report_{args.export}.json"
        export_report_to_json(report, snapshots, output_path)
    
    else:
        # 显示摘要
        reports = get_all_reports(args.latest)
        display_reports_summary(reports)
        
        # 显示统计信息
        print(f"\n📈 统计信息:")
        print(f"  总报告数：      {len(reports)}")
        
        completed = sum(1 for r in reports if r['is_completed'])
        failed = sum(1 for r in reports if r['status'] == 'failed')
        processing = sum(1 for r in reports if r['status'] == 'processing')
        
        print(f"  已完成：        {completed}")
        print(f"  失败：          {failed}")
        print(f"  进行中：        {processing}")
        
        if reports:
            avg_progress = sum(r['progress'] for r in reports) / len(reports)
            print(f"  平均进度：    {avg_progress:.1f}%")


if __name__ == '__main__':
    main()
