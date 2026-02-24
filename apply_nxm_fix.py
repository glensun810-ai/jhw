#!/usr/bin/env python3
"""
Fix P0 issues in nxm_execution_engine.py:
1. Increase timeout from 300s to 600s
2. Add real-time result storage to execution_store
"""

import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Increase timeout from 300 to 600
print("Fix 1: Increasing timeout from 300s to 600s...")
content = content.replace(
    'timeout_seconds: int = 300',
    'timeout_seconds: int = 600  # P0 修复：从 5 分钟增加到 10 分钟，适应复杂诊断场景'
)

# Fix 2: Add real-time result storage after scheduler.add_result(result)
# Find the location after "scheduler.add_result(result)" in the success branch
print("Fix 2: Adding real-time result storage to execution_store...")

# Locate the success branch and add real-time storage
success_pattern = r'''(                        scheduler\.add_result\(result\)\n                        results\.append\(result\))'''

replacement = r'''                        scheduler.add_result(result)
                        results.append(result)

                        # 【P0 修复】实时持久化到 execution_store，防止超时导致结果丢失
                        try:
                            from wechat_backend.views import execution_store as views_execution_store
                            if execution_id in views_execution_store:
                                if 'results' not in views_execution_store[execution_id]:
                                    views_execution_store[execution_id]['results'] = []
                                
                                # 实时追加结果（不要覆盖）
                                views_execution_store[execution_id]['results'].append(result)
                                
                                # 更新进度
                                views_execution_store[execution_id].update({
                                    'progress': int((completed / total_tasks) * 100),
                                    'status': 'processing',
                                    'stage': 'ai_fetching'
                                })
                        except Exception as e:
                            api_logger.error(f"[NxM] 实时存储结果失败：{e}")'''

content = re.sub(success_pattern, replacement, content)

# Also fix the async version timeout
content = re.sub(
    r'async def execute_nxm_test_async\(\n    # \.\.\.\n    timeout_seconds: int = 600  # P0 修复：从 5 分钟增加到 10 分钟，适应复杂诊断场景',
    'async def execute_nxm_test_async(\n    # ...\n    timeout_seconds: int = 600  # P0 修复：从 5 分钟增加到 10 分钟，适应复杂诊断场景',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixes applied successfully!")
print("\nChanges made:")
print("1. Timeout increased: 300s → 600s (10 minutes)")
print("2. Real-time result storage added to execution_store")
print("\nNext step: Check and fix nxm_scheduler.py complete_execution method")
