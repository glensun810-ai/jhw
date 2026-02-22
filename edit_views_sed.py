#!/usr/bin/env python3
"""
使用 sed 精确替换 views.py
"""
import subprocess

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

# 修复 1: 添加 detailed_results 字段
cmd1 = f"""sed -i.bak "s/'results': task_status.get('results', \\[\\]),/'results': task_status.get('results', []),\\n            'detailed_results': task_status.get('results', []),  # 【P0 修复】添加 detailed_results/g" {file_path}"""
subprocess.run(cmd1, shell=True)
print('✅ 修复 1: 添加 detailed_results 字段')

# 修复 2: 添加导入语句
cmd2 = f"""sed -i.bak2 "s/from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result/from wechat_backend.models import get_task_status as get_db_task_status, get_deep_intelligence_result\\n            from wechat_backend.database_core import get_connection\\n            import gzip, json/g" {file_path}"""
subprocess.run(cmd2, shell=True)
print('✅ 修复 2: 添加导入语句')

# 验证语法
result = subprocess.run(f"python3 -m py_compile {file_path}", shell=True, capture_output=True, text=True)
if result.returncode == 0:
    print('✅ 语法检查通过')
else:
    print('❌ 语法检查失败')
    print(result.stdout)
    print(result.stderr)
