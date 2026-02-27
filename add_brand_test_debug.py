#!/usr/bin/env python3
"""
Add more debug logging to brandTestService.js to help diagnose the issue
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/services/brandTestService.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug logging before calling parseTaskStatus
old_poll = """      try {
        const res = await getTaskStatusApi(executionId);

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);"""

new_poll = """      try {
        const res = await getTaskStatusApi(executionId);

        // 【DEBUG】输出后端响应
        logger.debug('[brandTestService] 后端响应:', JSON.stringify(res, null, 2));

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);
          
          // 【DEBUG】输出解析后的状态
          logger.debug('[brandTestService] 解析后的状态:', {
            stage: parsedStatus.stage,
            progress: parsedStatus.progress,
            is_completed: parsedStatus.is_completed,
            error: parsedStatus.error
          });"""

content = content.replace(old_poll, new_poll)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added debug logging to brandTestService.js!")
print("Now you will see:")
print("  1. Backend response")
print("  2. Parsed status")
print("\nPlease restart WeChat DevTools and test again!")
