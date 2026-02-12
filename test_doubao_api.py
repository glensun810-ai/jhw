"""
测试豆包API调用
"""

import os
import sys

# 设置环境变量中的API密钥
os.environ['DOUBAO_API_KEY'] = 'YOUR_DOUBAO_API_KEY'


def test_doubao_api():
    """测试Doubao API"""
    print("=== 测试豆包API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取API密钥
        api_key = os.getenv('DOUBAO_API_KEY')
        if not api_key:
            print("✗ 豆包API密钥未设置")
            return False
            
        # 创建适配器 - 使用正确的模型名
        adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, 'ep-20240520111905-bavcb')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ 豆包API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ 豆包API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ 豆包API测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_erniebot_api():
    """测试文心一言API"""
    print("\n=== 测试文心一言API ===")
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 使用豆包的API密钥，因为提供的密钥格式更像是豆包的
        api_key = os.getenv('DOUBAO_API_KEY')
        if not api_key:
            print("✗ 文心一言API密钥未设置")
            return False
            
        # 创建适配器
        adapter = AIAdapterFactory.create(AIPlatformType.WENXIN, api_key, 'ernie-bot-4.5')
        
        # 发送测试请求
        response = adapter.send_prompt("你好，请简单介绍一下自己。")
        
        if response.success:
            print(f"✓ 文心一言API调用成功")
            print(f"  响应内容: {response.content[:100]}...")
            print(f"  耗时: {response.latency:.2f}s")
            return True
        else:
            print(f"✗ 文心一言API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ 文心一言API测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始测试豆包和文心一言API调用...\n")
    
    results = []
    
    # 测试API
    results.append(("豆包", test_doubao_api()))
    results.append(("文心一言", test_erniebot_api()))
    
    print(f"\n=== 测试总结 ===")
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}: {'成功' if success else '失败'}")
    
    total_success = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n总计: {total_success}/{total_tests} 个API调用成功")
    
    if total_success > 0:
        print("✅ 部分或全部API测试成功！")
        return True
    else:
        print("❌ 所有API测试失败。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)