#!/usr/bin/env python3
"""测试从 API 获取完整诊断报告"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.diagnosis_report_service import DiagnosisReportService

# 使用最新的 execution_id
execution_id = '3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9'

print(f'=== 测试获取完整报告：{execution_id} ===\n')

service = DiagnosisReportService()

# 测试 get_history_report
print('1. 测试 get_history_report()...')
try:
    report = service.get_history_report(execution_id)
    
    if report:
        print(f'  ✅ 获取成功')
        print(f'  品牌：{report.get("brand_name", "N/A")}')
        print(f'  状态：{report.get("status", "N/A")}')
        print(f'  结果数量：{len(report.get("results", []))}')
        
        # 检查 brandDistribution
        brand_dist = report.get('brandDistribution', {})
        if brand_dist and brand_dist.get('data'):
            print(f'  ✅ brandDistribution: {brand_dist.get("data")}')
        else:
            print(f'  ❌ brandDistribution: 空')
        
        # 检查 sentimentDistribution
        sentiment_dist = report.get('sentimentDistribution', {})
        if sentiment_dist and sentiment_dist.get('data'):
            print(f'  ✅ sentimentDistribution: {sentiment_dist.get("data")}')
        else:
            print(f'  ❌ sentimentDistribution: 空')
        
        # 检查 keywords
        keywords = report.get('keywords', [])
        if keywords:
            print(f'  ✅ keywords: {len(keywords)} 个')
        else:
            print(f'  ❌ keywords: 空')
        
        # 检查结果字段
        results = report.get('results', [])
        if results:
            print(f'\n  === 结果字段检查 ===')
            first = results[0]
            print(f'  字段列表：{list(first.keys())}')
            
            # 检查关键字段
            key_fields = ['brand', 'extracted_brand', 'question', 'model', 
                         'response_content', 'quality_score', 'geo_data',
                         'tokens_used', 'finish_reason', 'request_id',
                         'response_metadata', 'reasoning_content']
            
            for field in key_fields:
                if field in first:
                    value = first.get(field)
                    if value is not None and value != '':
                        if isinstance(value, str) and len(value) > 50:
                            print(f'  ✅ {field}: {value[:50]}...')
                        else:
                            print(f'  ✅ {field}: {value}')
                    else:
                        print(f'  ⚠️ {field}: NULL/空')
                else:
                    print(f'  ❌ {field}: 字段不存在')
    else:
        print(f'  ❌ 返回为空')
        
except Exception as e:
    print(f'  ❌ 异常：{e}')
    import traceback
    traceback.print_exc()

print('\n=== 测试完成 ===')
