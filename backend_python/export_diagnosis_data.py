#!/usr/bin/env python3
"""Export diagnosis data to markdown document"""

import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the latest diagnosis report
cursor.execute('''
    SELECT execution_id, brand_name, competitor_brands, selected_models, 
           status, stage, progress, is_completed, created_at, updated_at
    FROM diagnosis_reports
    ORDER BY created_at DESC
    LIMIT 1
''')
report = cursor.fetchone()

if report:
    exec_id = report['execution_id']
    output_path = '/Users/sgl/PycharmProjects/PythonProject/DIAGNOSIS_DATA_EXPORT.md'
    
    # Export report data
    report_data = dict(report)
    report_data['competitor_brands'] = json.loads(report['competitor_brands']) if report['competitor_brands'] else []
    report_data['selected_models'] = json.loads(report['selected_models']) if report['selected_models'] else []
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 诊断数据详细导出报告\n\n")
        f.write(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**诊断执行 ID**: `{exec_id}`\n")
        f.write(f"**品牌**: {report['brand_name']}\n")
        f.write(f"**竞品**: {report_data['competitor_brands']}\n")
        f.write(f"**AI 平台**: {report_data['selected_models']}\n")
        f.write(f"**诊断时间**: {report['created_at']}\n")
        f.write(f"**状态**: {report['status']}\n\n")
        
        # 1. Diagnosis Report Main Table
        f.write("---\n\n")
        f.write("## 1. 诊断报告主数据 (diagnosis_reports)\n\n")
        f.write("**保存接口**: `DiagnosisReportRepository.create()`  \n")
        f.write("**调用位置**: `diagnosis_orchestrator.py` → `_phase_init()`  \n")
        f.write("**功能说明**: 创建诊断报告主记录，存储基本配置信息\n\n")
        f.write("### 保存的详细内容:\n\n```json\n")
        f.write(json.dumps({k: v for k, v in report_data.items() if k not in ['competitor_brands', 'selected_models']}, 
                          indent=2, ensure_ascii=False, default=str))
        f.write("\n```\n\n")
    
    # Get results
    cursor.execute('''
        SELECT id, brand, question, model, platform, response_content, extracted_brand,
               status, finish_reason, tokens_used, quality_score, quality_level,
               geo_data, response_metadata, reasoning_content, request_id,
               response_latency, sentiment, created_at
        FROM diagnosis_results
        WHERE execution_id = ?
    ''', (exec_id,))
    results = cursor.fetchall()
    
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write("---\n\n")
        f.write("## 2. AI 响应结果明细 (diagnosis_results)\n\n")
        f.write("**保存接口**: `DiagnosisResultRepository.add_batch()`  \n")
        f.write("**调用位置**: `diagnosis_orchestrator.py` → `_phase_ai_fetching()`  \n")
        f.write("**功能说明**: 保存各 AI 平台的调用结果和响应内容\n\n")
        f.write(f"### 记录数量：{len(results)}\n\n")
        
        for r in results:
            result_dict = dict(r)
            if r['geo_data']:
                result_dict['geo_data'] = json.loads(r['geo_data'])
            if r['response_metadata']:
                result_dict['response_metadata'] = json.loads(r['response_metadata'])
            
            f.write(f"### 结果 {r['id']} - {r['platform']} 平台\n\n")
            f.write("```json\n")
            f.write(json.dumps(result_dict, indent=2, ensure_ascii=False, default=str))
            f.write("\n```\n\n")

    # Get analysis data
    cursor.execute('''
        SELECT id, analysis_type, analysis_data
        FROM diagnosis_analysis
        WHERE execution_id = ?
    ''', (exec_id,))
    analyses = cursor.fetchall()
    
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write("---\n\n")
        f.write("## 3. 诊断分析数据 (diagnosis_analysis)\n\n")
        f.write("**保存接口**: `DiagnosisAnalysisRepository.add()` / `DiagnosisTransaction.add_analysis()`  \n")
        f.write("**调用位置**: `diagnosis_orchestrator.py` → `_phase_complete()`  \n")
        f.write("**功能说明**: 保存后台分析模块生成的分析结果\n\n")
        f.write(f"### 分析记录数量：{len(analyses)}\n\n")
        
        for a in analyses:
            analysis_dict = dict(a)
            if a['analysis_data']:
                analysis_dict['analysis_data'] = json.loads(a['analysis_data'])
            
            f.write(f"### 分析类型：{a['analysis_type']}\n\n")
            f.write(f"**analysis_id**: {a['id']}  \n")
            f.write("**保存内容**:\n\n```json\n")
            f.write(json.dumps(analysis_dict['analysis_data'], indent=2, ensure_ascii=False, default=str))
            f.write("\n```\n\n")

    # Get snapshot data
    cursor.execute('''
        SELECT id, snapshot_reason, snapshot_data, created_at
        FROM diagnosis_snapshots
        WHERE execution_id = ?
    ''', (exec_id,))
    snapshots = cursor.fetchall()
    
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write("---\n\n")
        f.write("## 4. 诊断报告快照 (diagnosis_snapshots)\n\n")
        f.write("**保存接口**: `DiagnosisReportRepository.create_snapshot()`  \n")
        f.write("**调用位置**: `diagnosis_report_service.py` → `complete_report()`  \n")
        f.write("**功能说明**: 创建诊断完成时的完整数据快照，用于归档和快速检索\n\n")
        f.write(f"### 快照记录数量：{len(snapshots)}\n\n")
        
        for s in snapshots:
            f.write(f"### 快照 {s['id']} - {s['snapshot_reason']}\n\n")
            f.write(f"**创建时间**: {s['created_at']}  \n")
            
            if s['snapshot_data']:
                snapshot_dict = json.loads(s['snapshot_data'])
                f.write("**快照数据结构**:\n\n```json\n")
                f.write(json.dumps({
                    'snapshot_reason': s['snapshot_reason'],
                    'created_at': s['created_at'],
                    'data_keys': list(snapshot_dict.keys()),
                    'report_keys': list(snapshot_dict.get('report', {}).keys()) if snapshot_dict.get('report') else [],
                    'results_count': len(snapshot_dict.get('results', [])),
                    'analysis_keys': list(snapshot_dict.get('analysis', {}).keys()) if snapshot_dict.get('analysis') else []
                }, indent=2, ensure_ascii=False, default=str))
                f.write("\n```\n\n")
            else:
                f.write("**快照数据**: NULL\n\n")

    # Summary table
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write("---\n\n")
        f.write("## 5. 数据保存汇总表\n\n")
        f.write("| 数据表 | 保存接口 | 调用位置 | 功能模块 | 记录数 | 状态 |\n")
        f.write("|--------|---------|---------|---------|--------|------|\n")
        
        cursor.execute("SELECT COUNT(*) FROM diagnosis_reports WHERE execution_id = ?", (exec_id,))
        f.write(f"| diagnosis_reports | `DiagnosisReportRepository.create()` | `_phase_init()` | 报告创建 | {cursor.fetchone()[0]} | ✅ |\n")
        
        cursor.execute("SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = ?", (exec_id,))
        f.write(f"| diagnosis_results | `DiagnosisResultRepository.add_batch()` | `_phase_ai_fetching()` | AI 调用 | {cursor.fetchone()[0]} | ✅ |\n")
        
        cursor.execute("SELECT COUNT(*) FROM diagnosis_analysis WHERE execution_id = ?", (exec_id,))
        f.write(f"| diagnosis_analysis | `DiagnosisAnalysisRepository.add()` | `_phase_complete()` | 后台分析 | {cursor.fetchone()[0]} | ✅ |\n")
        
        cursor.execute("SELECT COUNT(*) FROM diagnosis_snapshots WHERE execution_id = ?", (exec_id,))
        f.write(f"| diagnosis_snapshots | `DiagnosisReportRepository.create_snapshot()` | `complete_report()` | 报告归档 | {cursor.fetchone()[0]} | ✅ |\n")
        
        f.write("\n---\n\n")
        f.write("## 6. 调用链路图\n\n")
        f.write("```\n")
        f.write("用户请求诊断\n")
        f.write("    ↓\n")
        f.write("DiagnosisOrchestrator.execute()\n")
        f.write("    ↓\n")
        f.write("┌─────────────────────────────────────────┐\n")
        f.write("│ Phase 1: _phase_init()                  │\n")
        f.write("│ └─ DiagnosisReportRepository.create()   │ → diagnosis_reports\n")
        f.write("└─────────────────────────────────────────┘\n")
        f.write("    ↓\n")
        f.write("┌─────────────────────────────────────────┐\n")
        f.write("│ Phase 2: _phase_ai_fetching()           │\n")
        f.write("│ └─ DiagnosisResultRepository.add_batch()│ → diagnosis_results\n")
        f.write("└─────────────────────────────────────────┘\n")
        f.write("    ↓\n")
        f.write("┌─────────────────────────────────────────┐\n")
        f.write("│ Phase 6: _phase_complete()              │\n")
        f.write("│ └─ DiagnosisTransaction.add_analysis()  │ → diagnosis_analysis\n")
        f.write("└─────────────────────────────────────────┘\n")
        f.write("    ↓\n")
        f.write("┌─────────────────────────────────────────┐\n")
        f.write("│ Phase 7: complete_report()              │\n")
        f.write("│ └─ DiagnosisReportRepository.create_    │ → diagnosis_snapshots\n")
        f.write("│    snapshot()                           │\n")
        f.write("└─────────────────────────────────────────┘\n")
        f.write("    ↓\n")
        f.write("诊断完成，返回结果\n")
        f.write("```\n\n")

conn.close()
print(f"Export completed: {output_path}")
