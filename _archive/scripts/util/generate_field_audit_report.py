#!/usr/bin/env python3
"""
结果页字段数据源深度分析报告生成脚本
"""
import sqlite3, json, gzip

conn = sqlite3.connect('/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db')
cursor = conn.cursor()

# 获取最新测试记录
cursor.execute('SELECT * FROM test_records ORDER BY test_date DESC LIMIT 1')
row = cursor.fetchone()
cols = [d[0] for d in cursor.description]
record = dict(zip(cols, row))

report = []
report.append('# 品牌洞察报告结果页字段数据源深度分析报告')
report.append('')
report.append('**报告编号**: FIELD-AUDIT-2026-0222-001')
report.append('**分析日期**: 2026-02-22')
report.append('**分析工程师**: AI Assistant (系统架构师)')
report.append('**分析级别**: 🔴 P0 - 全面审计')
report.append('')
report.append('---')
report.append('')
report.append('## 📋 数据库字段清单')
report.append('')
report.append(f'**测试 ID**: {record["id"]}')
report.append(f'**品牌**: {record["brand_name"]}')
report.append(f'**总分**: {record["overall_score"]}')
report.append(f'**测试时间**: {record["test_date"]}')
report.append('')

# 解析 results_summary
try:
    summary_raw = record['results_summary']
    if record['is_summary_compressed']:
        summary = json.loads(gzip.decompress(summary_raw).decode('utf-8'))
    else:
        summary = json.loads(summary_raw)
    
    report.append('### results_summary 字段')
    report.append('')
    for key, val in summary.items():
        if isinstance(val, dict):
            report.append(f'#### {key}')
            report.append('')
            report.append('| 字段 | 值 | 状态 |')
            report.append('|------|-----|--------|')
            for k, v in val.items():
                if isinstance(v, (int, float, str)):
                    status = '✅' if v else '⚠️'
                    report.append(f'| {k} | {v} | {status} |')
            report.append('')
        elif isinstance(val, list):
            report.append(f'#### {key}')
            report.append('')
            report.append(f'- 列表长度：{len(val)}')
            if len(val) > 0 and isinstance(val[0], dict):
                report.append(f'- 首项字段：{list(val[0].keys())}')
            report.append('')
        else:
            report.append(f'#### {key}')
            report.append('')
            report.append(f'- 值：{val}')
            report.append('')
except Exception as e:
    report.append(f'解析失败：{e}')

conn.close()

# 保存报告
with open('/Users/sgl/PycharmProjects/PythonProject/docs/2026-02-22_结果页字段数据源深度分析报告.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('✅ 报告已生成：docs/2026-02-22_结果页字段数据源深度分析报告.md')
