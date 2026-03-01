#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Markdown 格式的诊断报告摘要"""

import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / 'database.db'
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

# 获取最新报告
cursor = conn.cursor()
cursor.execute('''
    SELECT * FROM diagnosis_reports
    ORDER BY created_at DESC
    LIMIT 5
''')
reports = cursor.fetchall()

print("# 📊 诊断报告数据完整性检查报告\n")
print(f"**总报告数**: {len(reports)}\n\n")

# 统计
completed = sum(1 for r in reports if r['is_completed'])
failed = sum(1 for r in reports if r['status'] == 'failed')

print("## 📈 统计概览\n")
print(f"- ✅ 已完成：{completed}")
print(f"- ❌ 失败：{failed}")
print(f"- ⏳ 进行中：{len(reports) - completed - failed}\n\n")

print("## 📋 报告详细数据\n\n")

for i, report in enumerate(reports, 1):
    print(f"### 报告 #{report['id']}: {report['brand_name']}\n")
    print(f"- **Execution ID**: `{report['execution_id']}`")
    print(f"- **用户**: {report['user_id']}")
    print(f"- **状态**: {report['status']}")
    print(f"- **进度**: {report['progress']}%")
    print(f"- **阶段**: {report['stage']}")
    print(f"- **创建时间**: {report['created_at']}")
    
    # 竞品
    competitors = json.loads(report['competitor_brands']) or []
    print(f"- **竞品**: {len(competitors)} 个 - {', '.join(competitors) if competitors else '无'}")
    
    # AI 平台
    models_raw = json.loads(report['selected_models']) or []
    models = []
    for m in models_raw:
        if isinstance(m, dict):
            models.append(m.get('name', str(m)))
        else:
            models.append(str(m))
    print(f"- **AI 平台**: {len(models)} 个 - {', '.join(models)}")
    
    # 问题
    questions = json.loads(report['custom_questions']) or []
    print(f"- **问题**: {len(questions)} 个")
    for j, q in enumerate(questions, 1):
        q_text = q.get('text', str(q)) if isinstance(q, dict) else str(q)
        print(f"  {j}. {q_text[:80]}{'...' if len(q_text) > 80 else ''}")
    
    # 获取快照数据
    cursor.execute('''
        SELECT report_data, report_version FROM report_snapshots
        WHERE execution_id = ?
        ORDER BY storage_timestamp DESC
        LIMIT 1
    ''', (report['execution_id'],))
    snapshot = cursor.fetchone()
    
    if snapshot:
        try:
            data = json.loads(snapshot['report_data'])
            # 修复：数据在 reportData 键下
            report_data = data.get('reportData', {})
            dimensions = report_data.get('dimensions', [])
            quality = report_data.get('qualityScore', {})
            
            print(f"\n**报告数据** (版本：{snapshot['report_version']}):")
            print(f"- 维度数：{len(dimensions)}")
            if dimensions:
                for dim in dimensions[:3]:
                    print(f"  - {dim.get('question', 'N/A')[:60]}... [模型：{dim.get('model', 'N/A')}]")
            if quality:
                print(f"- 质量评分：{quality.get('quality_level', 'N/A')} ({quality.get('quality_score', 'N/A')})")
        except Exception as e:
            print(f"- ⚠️ 报告数据解析失败：{e}")
    
    # 获取任务状态
    cursor.execute('''
        SELECT stage, progress, status_text, completed_count, total_count, is_completed
        FROM task_statuses
        WHERE task_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
    ''', (report['execution_id'],))
    task = cursor.fetchone()
    
    if task:
        print(f"\n**任务状态**:")
        print(f"- 阶段：{task['stage']}")
        print(f"- 进度：{task['progress']}%")
        print(f"- 状态：{task['status_text'][:60]}...")
        print(f"- 完成：{task['completed_count']}/{task['total_count']}")
    
    print("\n---\n")

conn.close()
