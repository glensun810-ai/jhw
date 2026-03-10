#!/usr/bin/env python3
"""
测试 Token 刷新机制
"""

import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'

def test_register_and_get_tokens():
    """测试注册并获取 tokens"""
    print("\n" + "="*50)
    print("测试 1: 注册并获取 Tokens")
    print("="*50)
    
    import random
    phone = f"1{random.randint(3000000000, 9999999999)}"
    password = "test123456"
    
    # 先获取验证码
    code_response = requests.post(
        f'{BASE_URL}/api/send-verification-code',
        json={'phone': phone},
        headers={'Content-Type': 'application/json'}
    )
    verification_code = code_response.json().get('mock_code', '123456')
    
    # 注册用户
    register_response = requests.post(
        f'{BASE_URL}/api/register',
        json={
            'phone': phone,
            'verificationCode': verification_code,
            'password': password
        },
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"注册响应：{json.dumps(register_response.json(), indent=2)}")
    
    if register_response.status_code == 200:
        data = register_response.json()
        if data.get('status') == 'success':
            print("✅ 注册成功")
            return {
                'phone': phone,
                'password': password,
                'token': data.get('token'),
                'refresh_token': data.get('refresh_token'),
                'user_id': data.get('user_id')
            }
    print("❌ 注册失败")
    return None


def test_validate_token(token):
    """测试验证 Token"""
    print("\n" + "="*50)
    print("测试 2: 验证 Token")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/validate-token',
        json={'token': token},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"验证响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'valid':
            print("✅ Token 有效")
            return True
    print("❌ Token 无效")
    return False


def test_refresh_token(refresh_token):
    """测试刷新 Token"""
    print("\n" + "="*50)
    print("测试 3: 刷新 Token")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/refresh-token',
        json={'refresh_token': refresh_token},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"刷新响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ Token 刷新成功")
            return {
                'token': data.get('token'),
                'refresh_token': data.get('refresh_token')
            }
    print("❌ Token 刷新失败")
    return None


def test_access_with_new_token(token, url='/api/test'):
    """使用新 Token 访问受保护资源"""
    print("\n" + "="*50)
    print(f"测试 4: 使用新 Token 访问 {url}")
    print("="*50)
    
    response = requests.get(
        f'{BASE_URL}{url}',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    print(f"访问响应状态码：{response.status_code}")
    print(f"访问响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ 访问成功")
        return True
    print("❌ 访问失败")
    return False


def test_logout(refresh_token):
    """测试登出"""
    print("\n" + "="*50)
    print("测试 5: 登出")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/logout',
        json={'refresh_token': refresh_token},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"登出响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ 登出成功")
        return True
    print("❌ 登出失败")
    return False


def test_invalidated_token(refresh_token):
    """测试已撤销的 Token 是否失效"""
    print("\n" + "="*50)
    print("测试 6: 验证已撤销的 Refresh Token")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/refresh-token',
        json={'refresh_token': refresh_token},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"响应状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("✅ 已撤销的 Token 正确失效")
        return True
    print("❌ 已撤销的 Token 仍然有效（安全漏洞）")
    return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("品牌 AI 诊断系统 - Token 刷新机制测试")
    print("="*60)
    
    # 测试 1: 注册并获取 tokens
    tokens = test_register_and_get_tokens()
    
    if not tokens:
        print("\n❌ 测试终止：注册失败")
        return
    
    access_token = tokens['token']
    refresh_token = tokens['refresh_token']
    
    # 测试 2: 验证 access token
    if not test_validate_token(access_token):
        print("\n❌ 测试终止：Token 验证失败")
        return
    
    # 测试 3: 刷新 token
    new_tokens = test_refresh_token(refresh_token)
    
    if not new_tokens:
        print("\n❌ 测试终止：Token 刷新失败")
        return
    
    new_access_token = new_tokens['token']
    new_refresh_token = new_tokens['refresh_token']
    
    # 测试 4: 使用新 token 访问资源
    if not test_access_with_new_token(new_access_token):
        print("\n❌ 测试终止：新 Token 访问失败")
        return
    
    # 测试 5: 登出
    if not test_logout(new_refresh_token):
        print("\n❌ 测试终止：登出失败")
        return
    
    # 测试 6: 验证已撤销的 token 失效
    if not test_invalidated_token(new_refresh_token):
        print("\n❌ 测试终止：Token 撤销验证失败")
        return
    
    print("\n" + "="*60)
    print("✅ 所有 Token 刷新机制测试通过！")
    print("="*60)
    print("\n测试总结:")
    print("1. ✅ 注册并获取 Access/Refresh Token")
    print("2. ✅ Access Token 验证")
    print("3. ✅ Refresh Token 刷新机制")
    print("4. ✅ 新 Token 访问受保护资源")
    print("5. ✅ 登出功能")
    print("6. ✅ Token 撤销验证")


if __name__ == '__main__':
    main()
