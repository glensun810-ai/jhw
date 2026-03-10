#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端连通性测试脚本
验证前后端打通情况

修复 P0 问题：
1. 验证后端服务已启动
2. 验证端口配置正确
3. 验证 CORS 配置正确
4. 验证诊断 API 可用
"""

import requests
import json
import time
import sys

# 配置
BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_result(name, passed, message=""):
    """打印测试结果"""
    status = "✅" if passed else "❌"
    print(f"  {status} {name}: {'通过' if passed else '失败'} {message}")
    return passed

def test_health_check():
    """健康检查测试"""
    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        elapsed = (time.time() - start) * 1000
        passed = response.status_code == 200
        return print_result("健康检查", passed, f"({response.status_code}, {elapsed:.0f}ms)")
    except Exception as e:
        return print_result("健康检查", False, str(e))

def test_home_page():
    """首页测试"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        passed = response.status_code == 200
        return print_result("首页访问", passed, f"({response.status_code})")
    except Exception as e:
        return print_result("首页访问", False, str(e))

def test_api_test():
    """API 测试端点"""
    try:
        response = requests.get(f"{BASE_URL}/api/test", timeout=TIMEOUT)
        passed = response.status_code == 200
        return print_result("API 测试端点", passed, f"({response.status_code})")
    except Exception as e:
        return print_result("API 测试端点", False, str(e))

def test_cors_preflight():
    """CORS 预检测试"""
    try:
        response = requests.options(f"{BASE_URL}/api/perform-brand-test", timeout=TIMEOUT)
        passed = response.status_code == 200
        headers = dict(response.headers)
        cors_ok = 'Access-Control-Allow-Origin' in headers
        return print_result("CORS 预检", passed and cors_ok, 
                          f"({response.status_code}, CORS={'✓' if cors_ok else '✗'})")
    except Exception as e:
        return print_result("CORS 预检", False, str(e))

def test_ai_platforms():
    """AI 平台列表测试"""
    try:
        response = requests.get(f"{BASE_URL}/api/ai-platforms", timeout=TIMEOUT)
        passed = response.status_code == 200
        return print_result("AI 平台列表", passed, f"({response.status_code})")
    except Exception as e:
        return print_result("AI 平台列表", False, str(e))

def test_diagnosis_api_quick():
    """诊断 API 快速测试（不实际调用 AI）"""
    try:
        payload = {
            "brand_list": ["测试品牌"],
            "selectedModels": [{"name": "DeepSeek", "checked": True}],
            "custom_question": "测试"
        }
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=payload,
            timeout=TIMEOUT
        )
        # 期望 200（成功）或 400（参数验证失败）
        passed = response.status_code in [200, 400]
        return print_result("诊断 API 快速测试", passed, f"({response.status_code})")
    except Exception as e:
        return print_result("诊断 API 快速测试", False, str(e))

def run_all_tests():
    """运行所有测试"""
    print_header("端到端连通性测试")
    print(f"目标地址：{BASE_URL}")
    print(f"超时设置：{TIMEOUT}秒\n")
    
    tests = [
        ("基础连通性", [
            test_health_check,
            test_home_page,
            test_api_test,
        ]),
        ("CORS 与安全", [
            test_cors_preflight,
        ]),
        ("配置接口", [
            test_ai_platforms,
        ]),
        ("诊断接口", [
            test_diagnosis_api_quick,
        ]),
    ]
    
    total = 0
    passed = 0
    
    for category, test_funcs in tests:
        print(f"\n📋 {category}:")
        for test_func in test_funcs:
            total += 1
            if test_func():
                passed += 1
    
    # 打印统计
    print_header("测试统计")
    print(f"  总测试数：{total}")
    print(f"  通过：{passed}")
    print(f"  失败：{total - passed}")
    if total > 0:
        print(f"  通过率：{(passed/total*100):.1f}%")
    
    # 给出建议
    if passed == total:
        print("\n✅ 所有测试通过！后端服务正常运行。")
    elif passed >= total * 0.8:
        print("\n⚠️  大部分测试通过，但仍有问题需要修复。")
    else:
        print("\n❌ 测试失败较多，请检查后端服务配置。")
        print("\n建议操作:")
        print("  1. 检查后端服务是否启动：cd backend_python && python run.py")
        print("  2. 检查端口配置：确保前端使用 http://127.0.0.1:5000")
        print("  3. 检查 .env 配置文件是否存在")
    
    return passed == total

if __name__ == '__main__':
    # 检查服务是否运行
    print("检查后端服务状态...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 后端服务未正常运行 (状态码：{response.status_code})")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到后端服务 ({BASE_URL})")
        print(f"\n请先启动后端服务:")
        print(f"  cd /Users/sgl/PycharmProjects/PythonProject/backend_python")
        print(f"  python run.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 检查失败：{e}")
        sys.exit(1)
    
    print("✅ 后端服务正常运行\n")
    
    # 运行测试
    success = run_all_tests()
    sys.exit(0 if success else 1)
