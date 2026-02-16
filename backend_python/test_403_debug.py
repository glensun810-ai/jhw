#!/usr/bin/env python3
"""
调试403错误的测试脚本
"""

import requests
import json

# 测试不同的请求方式
base_url = "http://127.0.0.1:5000"

# 1. 测试简单的GET请求
print("=" * 60)
print("测试1: 简单的GET请求到 /")
print("=" * 60)
try:
    response = requests.get(f"{base_url}/", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# 2. 测试OPTIONS预检请求
print("\n" + "=" * 60)
print("测试2: OPTIONS预检请求到 /api/perform-brand-test")
print("=" * 60)
try:
    headers = {
        'Origin': 'http://localhost',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type,Authorization,X-WX-OpenID'
    }
    response = requests.options(f"{base_url}/api/perform-brand-test", headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# 3. 测试POST请求（无body）
print("\n" + "=" * 60)
print("测试3: POST请求到 /api/perform-brand-test（无body）")
print("=" * 60)
try:
    response = requests.post(f"{base_url}/api/perform-brand-test", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# 4. 测试POST请求（有body）
print("\n" + "=" * 60)
print("测试4: POST请求到 /api/perform-brand-test（有body）")
print("=" * 60)
try:
    headers = {'Content-Type': 'application/json'}
    data = {
        "brand_list": ["元若曦", "养生堂", "固生堂"],
        "selectedModels": ["豆包"],
        "custom_question": "养生茶哪家好 养生茶品牌推荐 靠谱的养生茶品牌"
    }
    response = requests.post(
        f"{base_url}/api/perform-brand-test",
        headers=headers,
        json=data,
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# 5. 测试带微信头的POST请求
print("\n" + "=" * 60)
print("测试5: POST请求到 /api/perform-brand-test（带微信头）")
print("=" * 60)
try:
    headers = {
        'Content-Type': 'application/json',
        'X-WX-OpenID': 'test_openid_123'
    }
    data = {
        "brand_list": ["元若曦", "养生堂", "固生堂"],
        "selectedModels": ["豆包"],
        "custom_question": "养生茶哪家好 养生茶品牌推荐 靠谱的养生茶品牌"
    }
    response = requests.post(
        f"{base_url}/api/perform-brand-test",
        headers=headers,
        json=data,
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
