#!/usr/bin/env python3
"""检查最新诊断结果数据"""

import sqlite3
import json
import os

db_path = os.path.join(os.path.dirname(__file__), 'database.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

try:
    # 查询最新的诊断报告
    cursor = conn.cursor()
    cursor.execute('''
        SELECT execution_id, brand_name, status, progress, stage, is_completed, created_at
        FROM diagnosis_reports 
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    report = cursor.fetchone()

    if report:
        print('=== 最新诊断报告 ===')
        print(f'execution_id: {report["execution_id"]}')
        print(f'brand_name: {report["brand_name"]}')
        print(f'status: {report["status"]}')
        print(f'progress: {report["progress"]}')
        print(f'stage: {report["stage"]}')
        print(f'is_completed: {report["is_completed"]}')
        print(f'created_at: {report["created_at"]}')
        
        # 查询结果明细
        print('\n=== 诊断结果明细 ===')
        cursor.execute('''
            SELECT id, brand, extracted_brand, question, model, response_content, 
                   quality_score, tokens_used, finish_reason, platform, status,
                   response_metadata, reasoning_content
            FROM diagnosis_results 
            WHERE execution_id = ?
        ''', (report['execution_id'],))
        
        results = cursor.fetchall()
        print(f'结果数量：{len(results)}')
        for r in results:
            print(f'\n--- 结果 {r["id"]} ---')
            print(f'  brand: {r["brand"]}')
            print(f'  extracted_brand: {r["extracted_brand"]}')
            print(f'  question: {r["question"][:50]}...')
            print(f'  model: {r["model"]}')
            print(f'  quality_score: {r["quality_score"]}')
            print(f'  tokens_used: {r["tokens_used"]}')
            print(f'  finish_reason: {r["finish_reason"]}')
            print(f'  platform: {r["platform"]}')
            print(f'  status: {r["status"]}')
            print(f'  response_content 前 100 字符：{r["response_content"][:100]}...')
            
            # 检查 response_metadata
            if r['response_metadata']:
                metadata = json.loads(r['response_metadata'])
                print(f'  response_metadata: {json.dumps(metadata, ensure_ascii=False)[:200]}...')
        
        # 查询分析数据
        print('\n=== 分析数据 ===')
        cursor.execute('''
            SELECT analysis_type, id, analysis_data
            FROM diagnosis_analysis 
            WHERE execution_id = ?
        ''', (report['execution_id'],))
        
        analyses = cursor.fetchall()
        print(f'分析类型数量：{len(analyses)}')
        for a in analyses:
            print(f'  - {a["analysis_type"]} (id={a["id"]})')
        
        # 查询快照
        print('\n=== 快照数据 ===')
        cursor.execute('''
            SELECT id, snapshot_reason, created_at
            FROM diagnosis_snapshots 
            WHERE execution_id = ?
        ''', (report['execution_id'],))
        
        snapshots = cursor.fetchall()
        print(f'快照数量：{len(snapshots)}')
        for s in snapshots:
            print(f'  - id={s["id"]}, reason={s["snapshot_reason"]}, at={s["created_at"]}')
    else:
        print('未找到诊断报告')

finally:
    conn.close()
