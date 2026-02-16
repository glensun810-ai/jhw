#!/usr/bin/env python3
"""
GEO系统快速冒烟测试
用于快速验证核心接口是否正常工作
"""

import requests
import sys
import time

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10


def test_endpoint(name: str, method: str, endpoint: str, 
                  data: dict = None, params: dict = None,
                  expected_status: int = 200) -> bool:
    """测试单个端点"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=TIMEOUT)
        elif method == "OPTIONS":
            response = requests.options(url, timeout=TIMEOUT)
        else:
            print(f"  ⚠️  不支持的方法: {method}")
            return False
        
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {name}: {response.status_code} ({response.elapsed.total_seconds()*1000:.0f}ms)")
        
        if not success:
            print(f"     预期: {expected_status}, 实际: {response.status_code}")
            if response.text:
                print(f"     响应: {response.text[:100]}")
        
        return success
        
    except requests.exceptions.ConnectionError:
        print(f"  ❌ {name}: 连接失败 - 服务可能未启动")
        return False
    except requests.exceptions.Timeout:
        print(f"  ❌ {name}: 请求超时")
        return False
    except Exception as e:
        print(f"  ❌ {name}: 错误 - {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("GEO系统快速冒烟测试")
    print("=" * 60)
    print(f"测试URL: {BASE_URL}")
    print(f"超时设置: {TIMEOUT}秒")
    print("=" * 60)
    
    results = []
    
    # 1. 基础连通性
    print("\n1. 基础连通性测试")
    results.append(test_endpoint("健康检查", "GET", "/health"))
    results.append(test_endpoint("首页", "GET", "/"))
    results.append(test_endpoint("API测试", "GET", "/api/test"))
    
    # 2. CORS测试
    print("\n2. CORS预检测试")
    results.append(test_endpoint("CORS预检", "OPTIONS", "/api/perform-brand-test"))
    
    # 3. 认证接口
    print("\n3. 认证接口测试")
    results.append(test_endpoint("登录-无效code", "POST", "/api/login", 
                                {"code": "invalid"}, expected_status=400))
    
    # 4. 品牌测试接口
    print("\n4. 品牌测试接口测试")
    results.append(test_endpoint("品牌测试-缺少参数", "POST", "/api/perform-brand-test",
                                {}, expected_status=400))
    results.append(test_endpoint("品牌测试-空brand_list", "POST", "/api/perform-brand-test",
                                {"brand_list": []}, expected_status=400))
    
    # 5. 配置接口
    print("\n5. 配置接口测试")
    results.append(test_endpoint("AI平台列表", "GET", "/api/ai-platforms"))
    results.append(test_endpoint("平台状态", "GET", "/api/platform-status"))
    results.append(test_endpoint("配置获取", "GET", "/api/config"))
    
    # 6. 数据接口
    print("\n6. 数据接口测试")
    results.append(test_endpoint("历史记录-无openid", "GET", "/api/test-history",
                                expected_status=400))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过！系统基本功能正常。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上述详细信息。")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
