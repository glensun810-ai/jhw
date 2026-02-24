#!/usr/bin/env python3
"""
BUG-003 修复脚本：批量修复 bare except 语句
将 except: 替换为 except Exception as e:
"""

import re
import os

# 需要修复的文件列表
files_to_fix = [
    'backend_python/wechat_backend/database/audit_logs.py',
    'backend_python/wechat_backend/views_analytics.py',
    'backend_python/wechat_backend/views_analytics_behavior.py',
    'backend_python/wechat_backend/security/sqlcipher_evaluation.py',
    'backend_python/wechat_backend/security/encryption_enhanced.py',
    'backend_python/wechat_backend/security/rate_limit_monitor.py',
    'backend_python/wechat_backend/utils/ai_response_wrapper.py',
    'backend_python/wechat_backend/audit_decorator.py',
    'backend_python/wechat_backend/nxm_circuit_breaker.py',
    'backend_python/wechat_backend/views_pdf_export.py',
    'backend_python/wechat_backend/views_audit_full.py',
    'backend_python/wechat_backend/monitoring/alert_manager.py',
    'backend_python/wechat_backend/services/async_export_service.py',
    'backend_python/wechat_backend/services/enhanced_pdf_service.py',
    'backend_python/wechat_backend/services/report_data_service.py',
    'backend_python/wechat_backend/services/analytics_service.py',
]

total_fixed = 0

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        print(f"⚠️  文件不存在：{filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计修复前的 bare except 数量
    before_count = len(re.findall(r'\n\s+except:\s*\n', content))
    
    if before_count == 0:
        continue
    
    # 修复 bare except 为 except Exception as e
    # 保持缩进
    def replace_bare_except(match):
        indent = match.group(1)
        newline = match.group(2)
        return f'{indent}except Exception as e:{newline}{indent}    pass  # TODO: 添加适当的错误处理{newline}'
    
    content = re.sub(
        r'(\n\s+)except:(\s*\n)',
        replace_bare_except,
        content
    )
    
    # 统计修复后的数量
    after_count = len(re.findall(r'\n\s+except:\s*\n', content))
    
    if after_count < before_count:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        fixed_count = before_count - after_count
        total_fixed += fixed_count
        print(f"✅ {filepath}: 修复 {fixed_count} 处 bare except")

print(f"\n总计修复：{total_fixed} 处 bare except 语句")
