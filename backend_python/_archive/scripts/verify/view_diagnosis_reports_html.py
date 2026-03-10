#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断报告数据可视化查看器 - HTML 版本

生成 HTML 格式的诊断报告查看器，支持：
1. 表格形式展示所有报告
2. 详细数据展示
3. 数据完整性检查
4. 导出功能

使用方法：
    python view_diagnosis_reports_html.py              # 生成 HTML 报告
    python view_diagnosis_reports_html.py --latest 10  # 查看最新 10 条
"""

import sqlite3
import json
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
    """获取所有诊断报告"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            id, execution_id, user_id, brand_name,
            competitor_brands, selected_models, custom_questions,
            status, progress, stage, is_completed,
            created_at, updated_at, completed_at,
            data_schema_version, server_version
        FROM diagnosis_reports
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    reports = cursor.fetchall()
    conn.close()
    return reports


def get_report_snapshots(execution_id: str) -> List[sqlite3.Row]:
    """获取报告快照"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, report_data, report_version, storage_timestamp, size_kb
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


# ==================== HTML 生成 ====================

def generate_html_report(reports: List[sqlite3.Row]) -> str:
    """生成 HTML 报告"""
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>诊断报告数据可视化查看器</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #3498db; }}
        .stat-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
        .table-container {{ padding: 30px; overflow-x: auto; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #34495e;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 8px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-completed {{ background: #d4edda; color: #155724; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-processing {{ background: #fff3cd; color: #856404; }}
        .progress-bar {{
            width: 100px;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            transition: width 0.3s;
        }}
        .detail-section {{
            padding: 30px;
            border-top: 1px solid #e9ecef;
        }}
        .detail-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .detail-title {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .detail-item {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid #3498db;
        }}
        .detail-label {{ font-size: 12px; color: #7f8c8d; }}
        .detail-value {{ font-size: 14px; color: #2c3e50; margin-top: 4px; word-break: break-word; }}
        .tag {{
            display: inline-block;
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin: 2px;
        }}
        .integrity-ok {{ color: #28a745; }}
        .integrity-warning {{ color: #ffc107; }}
        .integrity-error {{ color: #dc3545; }}
        .btn {{
            display: inline-block;
            padding: 8px 16px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 13px;
            transition: background 0.3s;
        }}
        .btn:hover {{ background: #2980b9; }}
        .dimension-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border: 1px solid #e9ecef;
        }}
        .dimension-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .dimension-name {{ font-weight: 600; color: #2c3e50; }}
        .dimension-status {{ font-size: 12px; padding: 2px 8px; border-radius: 4px; }}
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 诊断报告数据可视化查看器</h1>
            <p>生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        {generate_stats_html(reports)}
        
        <div class="table-container">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">报告列表</h2>
            {generate_table_html(reports)}
        </div>
        
        {generate_details_html(reports)}
    </div>
</body>
</html>'''
    
    return html


def generate_stats_html(reports: List[sqlite3.Row]) -> str:
    """生成统计卡片 HTML"""
    total = len(reports)
    completed = sum(1 for r in reports if r['is_completed'])
    failed = sum(1 for r in reports if r['status'] == 'failed')
    avg_progress = sum(r['progress'] for r in reports) / total if total > 0 else 0
    
    return f'''
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">总报告数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{completed}</div>
                <div class="stat-label">已完成</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #dc3545;">{failed}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #ffc107;">{avg_progress:.1f}%</div>
                <div class="stat-label">平均进度</div>
            </div>
        </div>
    '''


def generate_table_html(reports: List[sqlite3.Row]) -> str:
    """生成表格 HTML"""
    rows = []
    for report in reports:
        competitor_count = len(json.loads(report['competitor_brands']) or [])
        status_class = f"status-{report['status']}"
        
        # 解析 selected_models
        selected_models_raw = json.loads(report['selected_models']) or []
        selected_models = []
        for m in selected_models_raw:
            if isinstance(m, dict):
                selected_models.append(m.get('name', m.get('id', str(m))))
            else:
                selected_models.append(str(m))
        
        rows.append(f'''
            <tr>
                <td>{report['id']}</td>
                <td style="font-family: monospace; font-size: 11px;">{report['execution_id'][:32]}...</td>
                <td><strong>{report['brand_name']}</strong></td>
                <td>{competitor_count}</td>
                <td>{", ".join(selected_models[:3])}{"..." if len(selected_models) > 3 else ""}</td>
                <td><span class="status-badge {status_class}">{report['status']}</span></td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {report['progress']}%;"></div>
                    </div>
                    <span style="font-size: 11px; margin-top: 4px; display: block;">{report['progress']}%</span>
                </td>
                <td>{report['stage']}</td>
                <td>{"✅" if report['is_completed'] else "❌"}</td>
                <td style="font-size: 11px;">{report['created_at'][:19]}</td>
            </tr>
        ''')
    
    return f'''
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Execution ID</th>
                    <th>品牌</th>
                    <th>竞品数</th>
                    <th>AI 平台</th>
                    <th>状态</th>
                    <th>进度</th>
                    <th>阶段</th>
                    <th>完成</th>
                    <th>创建时间</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    '''


def generate_details_html(reports: List[sqlite3.Row]) -> str:
    """生成详细信息 HTML"""
    details = []
    
    for report in reports:
        # 获取快照数据
        snapshots = get_report_snapshots(report['execution_id'])
        task_status = get_task_status(report['execution_id'])
        
        # 解析数据
        competitor_brands = json.loads(report['competitor_brands']) or []
        selected_models_raw = json.loads(report['selected_models']) or []
        custom_questions = json.loads(report['custom_questions']) or []
        
        selected_models = []
        for m in selected_models_raw:
            if isinstance(m, dict):
                selected_models.append(m.get('name', m.get('id', str(m))))
            else:
                selected_models.append(str(m))
        
        # 检查完整性
        integrity_issues = check_integrity(report, snapshots)
        
        # 报告数据
        report_data_html = ""
        if snapshots:
            try:
                report_data = json.loads(snapshots[0]['report_data'])
                dimensions = report_data.get('dimensions', [])
                quality_score = report_data.get('quality_score', {})
                
                dimensions_html = ""
                for dim in dimensions:
                    status_class = "status-completed" if dim.get('status') == 'completed' else "status-failed"
                    dimensions_html += f'''
                        <div class="dimension-item">
                            <div class="dimension-header">
                                <span class="dimension-name">📍 {dim.get('question', 'N/A')}</span>
                                <span class="dimension-status {status_class}">{dim.get('status', 'N/A')}</span>
                            </div>
                            <div style="font-size: 12px; color: #7f8c8d;">
                                <div>模型：{dim.get('model', 'N/A')}</div>
                                <div>质量评分：{dim.get('quality_score', 'N/A')}</div>
                            </div>
                        </div>
                    '''
                
                if not dimensions_html:
                    dimensions_html = "<p style='color: #7f8c8d; font-size: 13px;'>⚠️ 无维度数据</p>"
                
                report_data_html = f'''
                    <div class="detail-grid">
                        <div class="detail-item">
                            <div class="detail-label">报告版本</div>
                            <div class="detail-value">{report_data.get('reportVersion', 'N/A')}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">生成时间</div>
                            <div class="detail-value">{report_data.get('generateTime', 'N/A')}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">总体评分</div>
                            <div class="detail-value">{quality_score.get('quality_level', 'N/A')} ({quality_score.get('quality_score', 'N/A')})</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <div class="detail-title">维度分析 ({len(dimensions)} 个)</div>
                        {dimensions_html}
                    </div>
                '''
            except Exception as e:
                report_data_html = f"<p style='color: #dc3545;'>❌ 报告数据解析失败：{e}</p>"
        
        # 完整性检查 HTML
        integrity_html = ""
        if integrity_issues:
            for issue in integrity_issues:
                if "❌" in issue:
                    integrity_html += f"<div class='integrity-error'>{issue}</div>"
                elif "⚠️" in issue:
                    integrity_html += f"<div class='integrity-warning'>{issue}</div>"
                else:
                    integrity_html += f"<div class='integrity-ok'>{issue}</div>"
        else:
            integrity_html = "<div class='integrity-ok'>✅ 数据完整性检查通过</div>"
        
        # 任务状态 HTML
        task_status_html = ""
        if task_status:
            task_status_html = f'''
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">阶段</div>
                        <div class="detail-value">{task_status['stage']}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">进度</div>
                        <div class="detail-value">{task_status['progress']}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">状态文本</div>
                        <div class="detail-value">{task_status['status_text']}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">完成情况</div>
                        <div class="detail-value">{task_status['completed_count']}/{task_status['total_count']}</div>
                    </div>
                </div>
            '''
        else:
            task_status_html = "<p style='color: #7f8c8d;'>⚠️ 无任务状态记录</p>"
        
        detail_html = f'''
            <div class="detail-section">
                <div class="detail-card">
                    <div class="detail-title">📋 报告 #{report['id']}: {report['brand_name']} ({report['execution_id'][:32]}...)</div>
                    
                    <div class="detail-grid">
                        <div class="detail-item">
                            <div class="detail-label">用户 ID</div>
                            <div class="detail-value">{report['user_id']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">竞品数量</div>
                            <div class="detail-value">{len(competitor_brands)} {", ".join(competitor_brands[:3])}{"..." if len(competitor_brands) > 3 else ""}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">AI 平台</div>
                            <div class="detail-value">{", ".join([f"<span class='tag'>{m}</span>" for m in selected_models])}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">问题数量</div>
                            <div class="detail-value">{len(custom_questions)}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <div class="detail-title">自定义问题</div>
                        {''.join([f"<div class='tag'>{q.get('text', str(q)) if isinstance(q, dict) else str(q)}</div>" for q in custom_questions])}
                    </div>
                </div>
                
                <div class="detail-card">
                    <div class="detail-title">📈 报告数据</div>
                    {report_data_html}
                </div>
                
                <div class="detail-card">
                    <div class="detail-title">📊 任务状态</div>
                    {task_status_html}
                </div>
                
                <div class="detail-card">
                    <div class="detail-title">🔍 数据完整性检查</div>
                    {integrity_html}
                </div>
            </div>
        '''
        
        details.append(detail_html)
    
    return ''.join(details)


def check_integrity(report: sqlite3.Row, snapshots: List = None) -> List[str]:
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
    
    # 检查快照
    if snapshots is not None and not snapshots:
        issues.append("⚠️  没有报告快照数据")
    
    if not issues:
        issues.append("✅ 数据完整性检查通过")
    
    return issues


# ==================== 主程序 ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='诊断报告 HTML 可视化查看器')
    parser.add_argument('--latest', '-l', type=int, default=20, help='显示最新 N 条报告')
    parser.add_argument('--output', '-o', type=str, default='diagnosis_reports_view.html', help='输出 HTML 文件路径')
    
    args = parser.parse_args()
    
    print(f"📊 正在加载最新 {args.latest} 条诊断报告...")
    reports = get_all_reports(args.latest)
    
    print(f"📝 生成 HTML 报告...")
    html = generate_html_report(reports)
    
    output_path = Path(__file__).parent / args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 报告已生成：{output_path}")
    print(f"🌐 请在浏览器中打开查看：file://{output_path.absolute()}")


if __name__ == '__main__':
    main()
