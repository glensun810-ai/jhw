#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本
用于快速验证后端核心功能，避免超时问题

修复 P2-1: 后端 Python 测试超时问题
"""

import requests
import json
import time
import sys

# 配置
BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10  # 缩短超时时间


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
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        return print_result("健康检查", response.status_code == 200, f"({response.status_code})")
    except Exception as e:
        return print_result("健康检查", False, str(e))


def test_home_page():
    """首页测试"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        return print_result("首页访问", response.status_code == 200, f"({response.status_code})")
    except Exception as e:
        return print_result("首页访问", False, str(e))


def test_api_test():
    """API 测试端点"""
    try:
        response = requests.get(f"{BASE_URL}/api/test", timeout=TIMEOUT)
        return print_result("API 测试端点", response.status_code == 200, f"({response.status_code})")
    except Exception as e:
        return print_result("API 测试端点", False, str(e))


def test_cors_preflight():
    """CORS 预检测试"""
    try:
        response = requests.options(f"{BASE_URL}/api/perform-brand-test", timeout=TIMEOUT)
        return print_result("CORS 预检", response.status_code == 200, f"({response.status_code})")
    except Exception as e:
        return print_result("CORS 预检", False, str(e))


def test_ai_platforms():
    """AI 平台列表测试"""
    try:
        response = requests.get(f"{BASE_URL}/api/ai-platforms", timeout=TIMEOUT)
        return print_result("AI 平台列表", response.status_code == 200, f"({response.status_code})")
    except Exception as e:
        return print_result("AI 平台列表", False, str(e))


def run_quick_tests():
    """运行快速测试"""
    print_header("后端 Python 快速测试")
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
    print(f"  通过率：{(passed/total*100):.1f}%")
    
    return passed == total


if __name__ == '__main__':
    # 检查服务是否运行
    print("检查后端服务状态...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 后端服务未正常运行 (状态码：{response.status_code})")
            print(f"\n请先启动后端服务:")
            print(f"  cd /Users/sgl/PycharmProjects/PythonProject/backend_python")
            print(f"  python run.py")
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
    success = run_quick_tests()
    sys.exit(0 if success else 1)
