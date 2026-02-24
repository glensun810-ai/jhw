#!/usr/bin/env python3
"""
诊断 /api/perform-brand-test 401 错误

测试场景:
1. 无认证头访问 /api/perform-brand-test - 应该允许（可选认证）
2. 有认证头访问 /api/perform-brand-test - 应该允许
3. 无认证头访问 /api/test-progress - 应该拒绝（严格认证）
4. 有认证头访问 /api/test-progress - 应该允许
"""

import requests
import sys
import json

BASE_URL = "http://127.0.0.1:5000"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_result(test_name, passed, details=""):
    status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
    print(f"{status} - {test_name}")
    if details:
        print(f"       {details}")


def test_perform_brand_test_no_auth():
    """测试 1: 无认证访问 /api/perform-brand-test"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json={
                "brand_list": ["华为", "小米"],
                "selectedModels": ["doubao"],
                "custom_question": "测试问题"
            },
            timeout=5
        )
        
        # 应该允许访问（可能返回 200 或 400，但不应该是 401）
        passed = response.status_code != 401
        print_result(
            "无认证访问 /api/perform-brand-test",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except requests.exceptions.ConnectionError:
        print_result(
            "无认证访问 /api/perform-brand-test",
            False,
            "无法连接到服务器"
        )
        return None
    except Exception as e:
        print_result(
            "无认证访问 /api/perform-brand-test",
            False,
            str(e)
        )
        return False


def test_perform_brand_test_with_auth():
    """测试 2: 有认证访问 /api/perform-brand-test"""
    try:
        headers = {
            'X-WX-OpenID': 'test_openid_12345'
        }
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json={
                "brand_list": ["华为", "小米"],
                "selectedModels": ["doubao"],
                "custom_question": "测试问题"
            },
            headers=headers,
            timeout=5
        )
        
        # 应该允许访问
        passed = response.status_code != 401
        print_result(
            "有认证访问 /api/perform-brand-test",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except Exception as e:
        print_result(
            "有认证访问 /api/perform-brand-test",
            False,
            str(e)
        )
        return False


def test_test_progress_no_auth():
    """测试 3: 无认证访问 /api/test-progress"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/test-progress?executionId=test123",
            timeout=5
        )
        
        # 应该拒绝（401）
        passed = response.status_code == 401
        print_result(
            "无认证访问 /api/test-progress (应拒绝)",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except Exception as e:
        print_result(
            "无认证访问 /api/test-progress",
            False,
            str(e)
        )
        return False


def test_test_progress_with_auth():
    """测试 4: 有认证访问 /api/test-progress"""
    try:
        headers = {
            'X-WX-OpenID': 'test_openid_12345'
        }
        response = requests.get(
            f"{BASE_URL}/api/test-progress?executionId=test123",
            headers=headers,
            timeout=5
        )
        
        # 应该允许（可能返回 200 或 404，但不应该是 401）
        passed = response.status_code != 401
        print_result(
            "有认证访问 /api/test-progress",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except Exception as e:
        print_result(
            "有认证访问 /api/test-progress",
            False,
            str(e)
        )
        return False


def test_test_history_no_auth():
    """测试 5: 无认证访问 /api/test-history"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/test-history",
            timeout=5
        )
        
        # 应该拒绝（401）
        passed = response.status_code == 401
        print_result(
            "无认证访问 /api/test-history (应拒绝)",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except Exception as e:
        print_result(
            "无认证访问 /api/test-history",
            False,
            str(e)
        )
        return False


def test_test_history_with_auth():
    """测试 6: 有认证访问 /api/test-history"""
    try:
        headers = {
            'X-WX-OpenID': 'test_openid_12345'
        }
        response = requests.get(
            f"{BASE_URL}/api/test-history",
            headers=headers,
            timeout=5
        )
        
        # 应该允许（可能返回 200 或其他，但不应该是 401）
        passed = response.status_code != 401
        print_result(
            "有认证访问 /api/test-history",
            passed,
            f"状态码：{response.status_code}"
        )
        return passed
        
    except Exception as e:
        print_result(
            "有认证访问 /api/test-history",
            False,
            str(e)
        )
        return False


def main():
    print_header("诊断 /api/perform-brand-test 401 错误")
    
    print(f"{Colors.OKCYAN}测试服务器：{BASE_URL}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}按 Enter 键开始测试...{Colors.ENDC}")
    input()
    
    results = []
    
    print("\n" + "="*60)
    print("测试组 1: /api/perform-brand-test (可选认证)")
    print("="*60)
    results.append(("无认证访问品牌测试", test_perform_brand_test_no_auth()))
    results.append(("有认证访问品牌测试", test_perform_brand_test_with_auth()))
    
    print("\n" + "="*60)
    print("测试组 2: /api/test-progress (严格认证)")
    print("="*60)
    results.append(("无认证访问进度查询", test_test_progress_no_auth()))
    results.append(("有认证访问进度查询", test_test_progress_with_auth()))
    
    print("\n" + "="*60)
    print("测试组 3: /api/test-history (严格认证)")
    print("="*60)
    results.append(("无认证访问历史记录", test_test_history_no_auth()))
    results.append(("有认证访问历史记录", test_test_history_with_auth()))
    
    # 汇总
    print_header("测试结果汇总")
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    for test_name, result in results:
        if result is True:
            print(f"{Colors.OKGREEN}✅ {test_name}: 通过{Colors.ENDC}")
        elif result is False:
            print(f"{Colors.FAIL}❌ {test_name}: 失败{Colors.ENDC}")
        else:
            print(f"{Colors.OKCYAN}⚠️  {test_name}: 跳过{Colors.ENDC}")
    
    print(f"\n总计：{passed} 通过，{failed} 失败，{skipped} 跳过")
    
    if failed == 0 and passed > 0:
        print(f"\n{Colors.OKGREEN}🎉 所有测试通过！{Colors.ENDC}")
        return 0
    else:
        print(f"\n{Colors.FAIL}⚠️  有 {failed} 个测试失败{Colors.ENDC}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
