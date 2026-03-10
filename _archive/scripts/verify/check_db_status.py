#!/usr/bin/env python3
"""Check database diagnostic records"""
import sqlite3

conn = sqlite3.connect('backend_python/database.db')
cursor = conn.cursor()

# Check task_statuses
cursor.execute('SELECT COUNT(*) FROM task_statuses')
task_count = cursor.fetchone()[0]

# Check brand_test_results
cursor.execute('SELECT COUNT(*) FROM brand_test_results')
result_count = cursor.fetchone()[0]

# Check recent tasks
cursor.execute('SELECT task_id, stage, progress, is_completed, created_at FROM task_statuses ORDER BY created_at DESC LIMIT 5')
recent_tasks = cursor.fetchall()

# Check diagnosis_reports
try:
    cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
    report_count = cursor.fetchone()[0]
except:
    report_count = 'N/A'

print('=== 数据库状态检查 ===')
print(f'task_statuses 记录数：{task_count}')
print(f'brand_test_results 记录数：{result_count}')
print(f'diagnosis_reports 记录数：{report_count}')
print()
print('=== 最近 5 条任务状态 ===')
for task in recent_tasks:
    print(f'  task_id: {task[0]}, stage: {task[1]}, progress: {task[2]}%, completed: {task[3]}, created: {task[4]}')

conn.close()
