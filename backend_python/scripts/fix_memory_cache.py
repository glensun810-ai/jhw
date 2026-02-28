#!/usr/bin/env python3
# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/cache/api_cache.py', 'r') as f:
    content = f.read()

# 添加全局实例（在文件末尾）
new_code = '''

# ==================== 全局内存缓存实例 ====================
# P1-CACHE-1 修复：创建全局 memory_cache 实例供缓存预热使用

memory_cache = MemoryCache(max_size=CacheConfig.MAX_ENTRIES)
"""全局内存缓存实例，供缓存预热等模块使用"""
'''

# 在文件末尾添加
content = content.rstrip() + new_code

# 写回文件
with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/cache/api_cache.py', 'w') as f:
    f.write(content)

print("✅ Global memory_cache instance added successfully")
