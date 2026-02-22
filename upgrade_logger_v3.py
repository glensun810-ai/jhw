#!/usr/bin/env python3
"""
批量替换日志器引用：v2 → v3
"""
import os
import re

BASE_DIR = '/Users/sgl/PycharmProjects/PythonProject/backend_python'

# 需要替换的文件
files_to_update = [
    'wechat_backend/test_engine/scheduler.py',
    'wechat_backend/views.py',
    'wechat_backend/nxm_execution_engine.py',
]

# 替换规则
replacements = [
    (r'from utils\.ai_response_logger_v2 import', 'from utils.ai_response_logger_v3 import'),
    (r'from wechat_backend\.utils\.ai_response_logger_v2 import', 'from wechat_backend.utils.ai_response_logger_v3 import'),
    (r'ai_response_logger_v2', 'ai_response_logger_v3'),
]

for file_path in files_to_update:
    full_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(full_path):
        print(f'❌ 文件不存在：{full_path}')
        continue
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements:
        content = re.sub(old, new, content)
    
    if content != original_content:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ 已更新：{file_path}')
    else:
        print(f'⚠️  无变化：{file_path}')

print('\n✅ 批量替换完成')
print('\n⚠️  请手动检查以下文件:')
print('  - wechat_backend/utils/ai_response_wrapper.py')
print('  - wechat_backend/utils/ai_response_logger_enhanced.py')
