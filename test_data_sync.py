#!/usr/bin/env python3
"""
测试数据同步功能
"""

import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'

def register_and_login():
    """注册并登录获取 token"""
    import random
    phone = f"1{random.randint(3000000000, 9999999999)}"
    password = "test123456"
    
    # 获取验证码
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
    
    if register_response.status_code == 200:
        data = register_response.json()
        return {
            'phone': phone,
            'token': data.get('token'),
            'user_id': data.get('user_id')
        }
    return None


def test_upload_result(token):
    """测试上传单个结果"""
    print("\n" + "="*50)
    print("测试 1: 上传单个结果")
    print("="*50)
    
    result_data = {
        "result": {
            "result_id": f"test_result_{int(time.time())}",
            "brand_name": "测试品牌",
            "ai_models_used": ["deepseek", "qwen"],
            "questions_used": ["问题 1", "问题 2"],
            "overall_score": 85.5,
            "total_tests": 10,
            "results_summary": {
                "authority": 80,
                "visibility": 90
            },
            "detailed_results": {
                "platform_scores": [
                    {"platform": "deepseek", "score": 85}
                ]
            }
        }
    }
    
    response = requests.post(
        f'{BASE_URL}/api/upload-result',
        json=result_data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    )
    
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ 上传成功")
            return result_data['result']
    print("❌ 上传失败")
    return None


def test_sync_data(token, local_results):
    """测试同步数据"""
    print("\n" + "="*50)
    print("测试 2: 同步数据")
    print("="*50)
    
    sync_data_payload = {
        "localResults": local_results
    }
    
    response = requests.post(
        f'{BASE_URL}/api/sync-data',
        json=sync_data_payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    )
    
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print(f"✅ 同步成功：上传 {data.get('uploaded_count')} 条，下载 {len(data.get('cloud_results', []))} 条")
            return data
    print("❌ 同步失败")
    return None


def test_download_data(token, last_sync_timestamp):
    """测试下载数据"""
    print("\n" + "="*50)
    print("测试 3: 下载数据（增量）")
    print("="*50)
    
    download_data_payload = {
        "lastSyncTimestamp": last_sync_timestamp
    }
    
    response = requests.post(
        f'{BASE_URL}/api/download-data',
        json=download_data_payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    )
    
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print(f"✅ 下载成功：{len(data.get('cloud_results', []))} 条")
            return data
    print("❌ 下载失败")
    return None


def test_delete_result(token, result_id):
    """测试删除结果"""
    print("\n" + "="*50)
    print("测试 4: 删除结果")
    print("="*50)
    
    delete_data = {
        "result_id": result_id
    }
    
    response = requests.post(
        f'{BASE_URL}/api/delete-result',
        json=delete_data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    )
    
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ 删除成功")
            return True
    print("❌ 删除失败")
    return False


def test_unauthorized_access():
    """测试未授权访问"""
    print("\n" + "="*50)
    print("测试 5: 未授权访问")
    print("="*50)
    
    response = requests.post(
        f'{BASE_URL}/api/sync-data',
        json={},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"状态码：{response.status_code}")
    
    if response.status_code == 401:
        print("✅ 正确拒绝未授权访问")
        return True
    print("❌ 未正确拒绝未授权访问")
    return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("品牌 AI 诊断系统 - 数据同步功能测试")
    print("="*60)
    
    # 注册并登录
    print("\n注册测试用户...")
    user = register_and_login()
    
    if not user:
        print("\n❌ 测试终止：注册失败")
        return
    
    print(f"✅ 用户注册成功：{user['phone']}")
    token = user['token']
    
    # 测试 1: 上传单个结果
    uploaded_result = test_upload_result(token)
    
    if not uploaded_result:
        print("\n❌ 测试终止：上传失败")
        return
    
    # 等待一下确保时间戳不同
    time.sleep(1)
    
    # 测试 2: 同步数据
    sync_result = test_sync_data(token, [uploaded_result])
    
    if not sync_result:
        print("\n❌ 测试终止：同步失败")
        return
    
    last_sync_timestamp = sync_result.get('last_sync_timestamp')
    
    # 测试 3: 增量下载
    download_result = test_download_data(token, last_sync_timestamp)
    
    if not download_result:
        print("\n❌ 测试终止：下载失败")
        return
    
    # 测试 4: 删除结果
    if not test_delete_result(token, uploaded_result['result_id']):
        print("\n❌ 测试终止：删除失败")
        return
    
    # 测试 5: 未授权访问
    if not test_unauthorized_access():
        print("\n❌ 测试终止：安全验证失败")
        return
    
    print("\n" + "="*60)
    print("✅ 所有数据同步功能测试通过！")
    print("="*60)
    print("\n测试总结:")
    print("1. ✅ 上传单个结果")
    print("2. ✅ 同步数据（增量）")
    print("3. ✅ 下载数据（增量）")
    print("4. ✅ 删除结果")
    print("5. ✅ 未授权访问保护")


if __name__ == '__main__':
    main()
