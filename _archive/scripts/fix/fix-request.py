#!/usr/bin/env python3
"""Fix request.js to inject device ID and openid"""

with open('utils/request.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the request interceptor section
old_code = """    // 请求拦截器：自动添加 token
    const token = wx.getStorageSync('userToken');
    if (token) {
      requestParams.header.Authorization = `Bearer ${token}`;
    }

    // 发起请求
    wx.request(requestParams);"""

new_code = """    // 请求拦截器：自动添加 token 和设备信息
    const token = wx.getStorageSync('userToken');
    if (token) {
      requestParams.header.Authorization = `Bearer ${token}`;
    }
    
    // 注入设备 ID（用于日志追踪）
    if (deviceId) {
      requestParams.header['X-Device-ID'] = deviceId;
    }
    
    // 注入 OpenID（用于用户识别）
    if (openid) {
      requestParams.header['X-User-OpenID'] = openid;
    }

    // 发起请求
    wx.request(requestParams);"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('utils/request.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ request.js updated successfully")
else:
    print("❌ Could not find the code section to replace")
    print("Searching for similar patterns...")
    import re
    match = re.search(r'// 请求拦截器.*?wx\.request\(requestParams\);', content, re.DOTALL)
    if match:
        print(f"Found similar pattern at position {match.start()}-{match.end()}")
        print(f"Content: {match.group()[:200]}...")
