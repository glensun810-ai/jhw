#!/usr/bin/env python3
"""
Fix taskStatusService.js:
1. Fix detailed_results default value from {} to []
2. Add debug logging
3. Fix default case to not set is_completed=true
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/services/taskStatusService.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: detailed_results default value
content = content.replace(
    "detailed_results: (statusData && typeof statusData === 'object') ? statusData.detailed_results || {} : {}",
    "detailed_results: (statusData && typeof statusData === 'object') ? (Array.isArray(statusData.detailed_results) ? statusData.detailed_results : []) : []"
)

# Fix 2: results default value with Array check
content = content.replace(
    "results: (statusData && typeof statusData === 'object') ? statusData.results || [] : [],",
    "results: (statusData && typeof statusData === 'object') ? (Array.isArray(statusData.results) ? statusData.results : []) : [],",
)

# Fix 3: is_completed type check
content = content.replace(
    "is_completed: (statusData && typeof statusData === 'object') ? (statusData.is_completed || false) : false",
    "is_completed: (statusData && typeof statusData === 'object') ? (typeof statusData.is_completed === 'boolean' ? statusData.is_completed : false) : false"
)

# Fix 4: Add debug logging before return statement
old_return = "  // 返回解析后的状态信息\n  return parsed;"
new_return = """  // 【关键修复】添加调试日志
  console.log('[parseTaskStatus] 解析结果:', {
    stage: parsed.stage,
    progress: parsed.progress,
    is_completed: parsed.is_completed,
    status: parsed.status,
    results_count: parsed.results.length,
    detailed_results_count: parsed.detailed_results.length
  });

  // 返回解析后的状态信息
  return parsed;"""

content = content.replace(old_return, new_return)

# Fix 5: Fix default case comment
content = content.replace(
    "      default:\n        parsed.statusText = '处理中...';\n        parsed.stage = 'processing';",
    "      default:\n        // 【关键修复】未知状态时不要设置为 completed，继续轮询\n        parsed.statusText = `处理中... (${cleanStatus})`;\n        parsed.stage = 'processing';\n        parsed.is_completed = false;"
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed taskStatusService.js!")
print("Changes:")
print("  1. detailed_results default: {} → []")
print("  2. results: Added Array.isArray check")
print("  3. is_completed: Added type check")
print("  4. Added debug logging")
print("  5. Fixed default case")
