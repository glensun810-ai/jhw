#!/usr/bin/env python3
"""
测试用户注册流程
"""

import requests
import json
import random

BASE_URL = 'http://127.0.0.1:5000'

def test_send_verification_code():
    """测试发送验证码"""
    print("\n" + "="*50)
    print("测试 1: 发送验证码")
    print("="*50)
    
    # 生成随机手机号
    phone = f"1{random.randint(3000000000, 9999999999)}"
    
    response = requests.post(
        f'{BASE_URL}/api/send-verification-code',
        json={'phone': phone},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/send-verification-code")
    print(f"手机号：{phone}")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ 验证码发送成功")
            return phone, data.get('mock_code')
        else:
            print("❌ 验证码发送失败")
            return None, None
    else:
        print(f"❌ HTTP 错误：{response.status_code}")
        return None, None


def test_register(phone, verification_code):
    """测试用户注册"""
    print("\n" + "="*50)
    print("测试 2: 用户注册")
    print("="*50)
    
    password = "test123456"
    
    response = requests.post(
        f'{BASE_URL}/api/register',
        json={
            'phone': phone,
            'verificationCode': verification_code,
            'password': password
        },
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/register")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ 用户注册成功")
            return data.get('token'), password
        else:
            print("❌ 用户注册失败")
            return None, None
    elif response.status_code == 409:
        print("⚠️ 手机号已被注册")
        return None, None
    else:
        print(f"❌ HTTP 错误：{response.status_code}")
        return None, None


def test_login(phone, password):
    """测试手机号登录"""
    print("\n" + "="*50)
    print("测试 3: 手机号登录")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/login/phone',
        json={
            'phone': phone,
            'password': password
        },
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/login/phone")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ 登录成功")
            return data.get('token')
        else:
            print("❌ 登录失败")
            return None
    else:
        print(f"❌ HTTP 错误：{response.status_code}")
        return None


def test_invalid_phone():
    """测试无效手机号"""
    print("\n" + "="*50)
    print("测试 4: 无效手机号格式")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/send-verification-code',
        json={'phone': '12345678901'},  # 无效格式
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/send-verification-code")
    print(f"手机号：12345678901 (无效)")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ 正确拒绝了无效手机号")
        return True
    else:
        print("❌ 未正确拒绝无效手机号")
        return False


def test_weak_password():
    """测试弱密码"""
    print("\n" + "="*50)
    print("测试 5: 弱密码拒绝")
    print("="*50)
    
    # 先获取验证码
    phone = f"1{random.randint(3000000000, 9999999999)}"
    code_response = requests.post(
        f'{BASE_URL}/api/send-verification-code',
        json={'phone': phone},
        headers={'Content-Type': 'application/json'}
    )
    verification_code = code_response.json().get('mock_code', '123456')
    
    response = requests.post(
        f'{BASE_URL}/api/register',
        json={
            'phone': phone,
            'verificationCode': verification_code,
            'password': '123'  # 弱密码
        },
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/register")
    print(f"密码：123 (弱密码)")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ 正确拒绝了弱密码")
        return True
    else:
        print("❌ 未正确拒绝弱密码")
        return False


def test_invalid_verification_code():
    """测试无效验证码"""
    print("\n" + "="*50)
    print("测试 6: 无效验证码")
    print("="*50)
    
    phone = f"1{random.randint(3000000000, 9999999999)}"
    
    # 发送真实验证码
    code_response = requests.post(
        f'{BASE_URL}/api/send-verification-code',
        json={'phone': phone},
        headers={'Content-Type': 'application/json'}
    )
    
    # 使用错误的验证码
    response = requests.post(
        f'{BASE_URL}/api/register',
        json={
            'phone': phone,
            'verificationCode': '000000',  # 错误的验证码
            'password': 'test123456'
        },
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"请求：POST /api/register")
    print(f"验证码：000000 (错误)")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("✅ 正确拒绝了无效验证码")
        return True
    else:
        print("❌ 未正确拒绝无效验证码")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("品牌 AI 诊断系统 - 用户注册流程测试")
    print("="*60)
    
    # 测试 1: 发送验证码
    phone, verification_code = test_send_verification_code()
    
    if phone and verification_code:
        # 测试 2: 用户注册
        token, password = test_register(phone, verification_code)
        
        if token and password:
            # 测试 3: 手机号登录
            login_token = test_login(phone, password)
            
            if login_token:
                print("\n" + "="*60)
                print("✅ 所有测试通过！")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("❌ 登录测试失败")
                print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ 注册测试失败")
            print("="*60)
    
    # 测试 4-6: 错误处理
    test_invalid_phone()
    test_weak_password()
    test_invalid_verification_code()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == '__main__':
    main()
