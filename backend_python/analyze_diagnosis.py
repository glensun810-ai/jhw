#!/usr/bin/env python3
"""Analyze diagnosis data authenticity"""

import sqlite3
import json

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the latest diagnosis report
cursor.execute('''
    SELECT execution_id, brand_name, competitor_brands
    FROM diagnosis_reports
    ORDER BY created_at DESC
    LIMIT 1
''')
report = cursor.fetchone()

if report:
    exec_id = report['execution_id']
    brand_name = report['brand_name']
    competitor_brands = json.loads(report['competitor_brands']) if report['competitor_brands'] else []
    
    print('=' * 60)
    print('问题诊断报告')
    print('=' * 60)
    print()
    print('配置的主品牌:', brand_name)
    print('配置的竞品:', competitor_brands)
    print()
    
    # Check results
    cursor.execute('''
        SELECT id, brand, extracted_brand, platform, response_content
        FROM diagnosis_results
        WHERE execution_id = ?
    ''', (exec_id,))
    results = cursor.fetchall()
    
    print('=' * 60)
    print('发现的问题')
    print('=' * 60)
    print()
    
    issues = []
    
    for r in results:
        # Issue 1: Brand mismatch
        if r['brand'] not in [brand_name] + competitor_brands:
            issues.append({
                'type': '品牌字段不匹配',
                'expected': str([brand_name] + competitor_brands),
                'actual': r['brand'],
                'field': 'brand'
            })
        
        if r['extracted_brand'] not in [brand_name] + competitor_brands:
            issues.append({
                'type': '提取品牌不匹配',
                'expected': str([brand_name] + competitor_brands),
                'actual': r['extracted_brand'],
                'field': 'extracted_brand'
            })
        
        # Issue 2: Check if response is real AI response
        if r['response_content']:
            content = r['response_content'].lower()
            expected_in_content = [b.lower() for b in [brand_name] + competitor_brands]
            
            found_brands = []
            for b in expected_in_content:
                if b in content:
                    found_brands.append(b)
            
            if len(found_brands) == 0:
                issues.append({
                    'type': 'AI 响应未提及配置的品牌',
                    'expected': str([brand_name] + competitor_brands),
                    'actual': '未提及任何配置品牌',
                    'field': 'response_content'
                })
    
    # Check analysis data
    cursor.execute('''
        SELECT analysis_type, analysis_data
        FROM diagnosis_analysis
        WHERE execution_id = ?
    ''', (exec_id,))
    analyses = cursor.fetchall()
    
    for a in analyses:
        if a['analysis_data']:
            data = json.loads(a['analysis_data'])
            
            # Check brand_analysis
            if a['analysis_type'] == 'brand_analysis':
                user_brand = data.get('data', {}).get('user_brand_analysis', {}).get('brand', '')
                if user_brand != brand_name:
                    issues.append({
                        'type': '品牌分析中的品牌不匹配',
                        'expected': brand_name,
                        'actual': user_brand,
                        'field': 'brand_analysis.user_brand_analysis.brand'
                    })
                
                # Check if mention_rate is 0 (suspicious)
                mention_rate = data.get('data', {}).get('user_brand_analysis', {}).get('mention_rate', -1)
                if mention_rate == 0:
                    issues.append({
                        'type': '品牌提及率为 0（AI 未提及主品牌）',
                        'expected': '> 0',
                        'actual': str(mention_rate),
                        'field': 'brand_analysis.user_brand_analysis.mention_rate'
                    })
            
            # Check competitive_analysis
            if a['analysis_type'] == 'competitive_analysis':
                brand_scores = data.get('data', {}).get('brand_scores', {})
                for scored_brand in brand_scores.keys():
                    if scored_brand not in [brand_name] + competitor_brands:
                        issues.append({
                            'type': '品牌评分中的品牌不匹配',
                            'expected': str([brand_name] + competitor_brands),
                            'actual': scored_brand,
                            'field': 'competitive_analysis.brand_scores'
                        })
    
    # Print issues
    if issues:
        print('发现', len(issues), '个问题:')
        print()
        for i, issue in enumerate(issues, 1):
            print(str(i) + '. ' + issue['type'])
            print('   期望：' + issue.get('expected', 'N/A'))
            print('   实际：' + str(issue.get('actual', 'N/A')))
            print('   字段：' + issue['field'])
            print()
    else:
        print('未发现明显问题')

conn.close()
