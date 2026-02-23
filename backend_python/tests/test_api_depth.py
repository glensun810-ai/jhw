#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端 API 深度测试
测试所有诊断相关 API 端点

对应测试计划：第一阶段
"""

import requests
import time
import sys

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

def test_api_endpoints():
    """测试所有 API 端点"""
    
    print_header("后端 API 深度测试")
    print(f"目标地址：{BASE_URL}")
    print(f"超时设置：{TIMEOUT}秒\n")
    
    tests = []
    
    # 1. AI 平台列表
    print("1. 测试 AI 平台列表 (/api/ai-platforms)...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai-platforms", timeout=TIMEOUT)
        passed = response.status_code == 200
        tests.append(print_result("AI 平台列表", passed, f"({response.status_code})"))
        if passed:
            platforms = response.json()
            print(f"     可用平台：{len(platforms) if platforms else 0} 个")
    except Exception as e:
        tests.append(print_result("AI 平台列表", False, str(e)))
    
    # 2. 平台状态查询
    print("\n2. 测试平台状态查询 (/api/platform-status)...")
    try:
        response = requests.get(f"{BASE_URL}/api/platform-status", timeout=TIMEOUT)
        passed = response.status_code == 200
        tests.append(print_result("平台状态查询", passed, f"({response.status_code})"))
    except Exception as e:
        tests.append(print_result("平台状态查询", False, str(e)))
    
    # 3. 诊断任务提交
    print("\n3. 测试诊断任务提交 (/api/perform-brand-test)...")
    try:
        payload = {
            "brand_list": ["测试品牌"],
            "selectedModels": [{"name": "DeepSeek", "checked": True}],
            "custom_question": "介绍一下测试品牌"
        }
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200
        tests.append(print_result("诊断任务提交", passed, f"({response.status_code})"))
        
        if passed:
            data = response.json()
            execution_id = data.get('execution_id')
            print(f"     执行 ID: {execution_id}")
            return execution_id
    except Exception as e:
        tests.append(print_result("诊断任务提交", False, str(e)))
    
    return None

def test_task_status(execution_id):
    """测试任务状态查询"""
    
    if not execution_id:
        print("\n⚠️  跳过任务状态测试（无 execution_id）")
        return
    
    print_header("任务状态测试")
    
    # 4. 任务状态查询
    print(f"4. 测试任务状态查询 (/test/status/{execution_id})...")
    try:
        response = requests.get(
            f"{BASE_URL}/test/status/{execution_id}",
            timeout=TIMEOUT
        )
        passed = response.status_code == 200
        print_result("任务状态查询", passed, f"({response.status_code})")
        
        if passed:
            status_data = response.json()
            stage = status_data.get('stage', 'unknown')
            progress = status_data.get('progress', 0)
            print(f"     当前阶段：{stage} ({progress}%)")
    except Exception as e:
        print_result("任务状态查询", False, str(e))
    
    # 5. 任务进度查询
    print(f"\n5. 测试任务进度查询 (/api/test-progress)...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/test-progress?executionId={execution_id}",
            timeout=TIMEOUT
        )
        passed = response.status_code == 200
        print_result("任务进度查询", passed, f"({response.status_code})")
    except Exception as e:
        print_result("任务进度查询", False, str(e))

def main():
    """主函数"""
    # 检查服务是否运行
    print("检查后端服务状态...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 后端服务未正常运行 (状态码：{response.status_code})")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到后端服务 ({BASE_URL})")
        print(f"\n请先启动后端服务:")
        print(f"  cd /Users/sgl/PycharmProjects/PythonProject/backend_python")
        print(f"  python run.py")
        return 1
    except Exception as e:
        print(f"❌ 检查失败：{e}")
        return 1
    
    print("✅ 后端服务正常运行\n")
    
    # 执行 API 测试
    execution_id = test_api_endpoints()
    
    # 执行任务状态测试
    test_task_status(execution_id)
    
    # 打印统计
    print_header("测试统计")
    print(f"  执行 ID: {execution_id or 'N/A'}")
    print(f"  建议：查看完整测试报告")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
