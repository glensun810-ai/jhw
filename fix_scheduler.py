#!/usr/bin/env python3
"""
Fix nxm_scheduler.py complete_execution method:
Add is_completed and detailed_results fields
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_scheduler.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix complete_execution method
old_complete = '''    def complete_execution(self):
        """完成执行"""
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'completed'
                store['progress'] = 100
                store['stage'] = 'completed'
                store['end_time'] = datetime.now().isoformat()

        api_logger.info(f"[Scheduler] 执行完成：{self.execution_id}")'''

new_complete = '''    def complete_execution(self):
        """完成执行"""
        with self._lock:
            if self.execution_id in self.execution_store:
                store = self.execution_store[self.execution_id]
                store['status'] = 'completed'
                store['progress'] = 100
                store['stage'] = 'completed'
                store['is_completed'] = True  # 【P0 修复】添加 is_completed 字段
                store['detailed_results'] = store.get('results', [])  # 【P0 修复】确保 detailed_results 存在
                store['end_time'] = datetime.now().isoformat()

        api_logger.info(f"[Scheduler] 执行完成：{self.execution_id}")'''

content = content.replace(old_complete, new_complete)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed complete_execution method!")
print("Added fields:")
print("  - is_completed: True")
print("  - detailed_results: copy of results")
