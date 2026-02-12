"""
测试豆包API调用 - 专门用于调试新部署ID
"""

import os
import sys

# 设置环境变量中的API密钥
os.environ['DOUBAO_API_KEY'] = '2a376e32-8877-4df8-9865-7eb3e99c9f92'


def test_doubao_api():
    """测试Doubao API"""
    print("=== 测试豆包API (新部署ID) ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('DOUBAO_API_KEY')
        if not api_key:
            print("✗ 豆包API密钥未设置")
            return False
            
        # 创建适配器 - 使用新的endpoint ID
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, 'ep-20260212000000-gd5tq')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ 豆包API调用成功")
            print(f"  响应内容: {response.content[:200]}...")
            print(f"  耗时: {response.latency:.2f}s")
            print(f"  平台: {response.platform}")
            print(f"  模型: {response.model}")
            return True
        else:
            print(f"✗ 豆包API调用失败: {response.error_message}")
            print(f"  错误类型: {response.error_type}")
            return False
            
    except Exception as e:
        print(f"✗ 豆包API测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_model_names():
    """测试不同的模型名称格式"""
    print("\n=== 测试不同的模型名称格式 ===")
    
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key:
        print("✗ 豆包API密钥未设置")
        return False
    
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    from wechat_backend.ai_adapters.base_adapter import AIPlatformType
    
    # 测试不同的模型名称格式
    model_names = [
        'ep-20260212000000-gd5tq',
        'gd5tq',  # 可能只需要后缀
        'ep-20260212000000-gd5tq.ark.cn-beijing.volces.com',  # 完整域名
    ]
    
    for model_name in model_names:
        print(f"\n尝试模型名称: {model_name}")
        try:
            adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, model_name)
            response = adapter.send_prompt("你好。")
            
            if response.success:
                print(f"  ✓ 成功 - 响应: {response.content[:100]}...")
                return True
            else:
                print(f"  ✗ 失败: {response.error_message}")
        except Exception as e:
            print(f"  ✗ 异常: {e}")
    
    return False


def main():
    """主测试函数"""
    print("开始测试豆包新部署ID API调用...\n")
    
    results = []
    
    # 测试主要API
    results.append(("主要测试", test_doubao_api()))
    
    # 测试不同模型名称格式
    results.append(("不同格式测试", test_different_model_names()))
    
    print(f"\n=== 测试总结 ===")
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}: {'成功' if success else '失败'}")
    
    total_success = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n总计: {total_success}/{total_tests} 个测试成功")
    
    if total_success > 0:
        print("✅ 至少有一个测试成功！")
        return True
    else:
        print("❌ 所有测试失败。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)