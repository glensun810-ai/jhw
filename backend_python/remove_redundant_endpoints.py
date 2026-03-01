#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除冗余 API 接口脚本
目标：
1. 删除 /test/submit 接口
2. 删除 /test/result/{task_id} 接口
"""
import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 删除 /test/submit 接口
submit_pattern = r"\n@wechat_bp\.route\('/test/submit'.*?return jsonify\(\{'status': 'success', 'execution_id': execution_id, 'results': results\}\), 200\n"
content = re.sub(submit_pattern, '\n', content, flags=re.DOTALL)

# 删除 /test/result/{task_id} 接口
result_pattern = r"\n@wechat_bp\.route\('/test/result/<task_id>', methods=\['GET'\]\).*?return jsonify\(deep_intelligence_result\.to_dict\(\)\), 200\n"
content = re.sub(result_pattern, '\n', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已删除冗余接口:")
print("   - /test/submit")
print("   - /test/result/{task_id}")
