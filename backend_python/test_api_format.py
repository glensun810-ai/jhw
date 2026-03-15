#!/usr/bin/env python3
"""测试 API 端点返回的数据格式"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.diagnosis_report_service import DiagnosisReportService
from utils.field_converter import convert_response_to_camel

# 使用最新的 execution_id
execution_id = '3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9'

print(f'=== 测试 API 返回格式：{execution_id} ===\n')

service = DiagnosisReportService()

# 获取报告
report = service.get_history_report(execution_id)

print('1. 原始报告格式 (snake_case)...')
print(f'   键列表：{list(report.keys())[:10]}...')

# 转换为 camelCase
camel_report = convert_response_to_camel(report)

print('\n2. 转换后格式 (camelCase)...')
print(f'   键列表：{list(camel_report.keys())[:10]}...')

# 检查前端需要的关键字段
print('\n3. 前端关键字段检查...')
required_fields = [
    'brandDistribution',
    'sentimentDistribution', 
    'keywords',
    'results',
    'detailedResults',
    'brandScores'
]

for field in required_fields:
    if field in camel_report:
        value = camel_report[field]
        if value:
            if isinstance(value, (list, dict)):
                print(f'  ✅ {field}: {type(value).__name__} ({len(value)} items)')
            else:
                print(f'  ✅ {field}: {value}')
        else:
            print(f'  ⚠️ {field}: 空值')
    else:
        print(f'  ❌ {field}: 字段不存在')

# 输出完整的 JSON 用于调试
print('\n4. 完整报告 JSON (前 2000 字符)...')
print(json.dumps(camel_report, ensure_ascii=False, indent=2)[:2000])

print('\n=== 测试完成 ===')
