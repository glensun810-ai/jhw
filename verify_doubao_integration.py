#!/usr/bin/env python3
"""
验证豆包API集成的简单测试脚本
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_doubao_api_integration():
    """测试豆包API集成"""
    print("🔍 验证豆包API集成...")
    
    # 检查API密钥
    api_key = os.getenv('DOUBAO_API_KEY')
    if not api_key or api_key == 'fake-api-key-for-testing' or 'YOUR_' in api_key:
        print("⚠️  警告: 未设置有效的DOUBAO_API_KEY")
        print("💡 提示: 请在环境变量中设置有效的豆包API密钥")
        print("   示例: export DOUBAO_API_KEY=your_actual_api_key_here")
        return False
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 创建适配器
        print("🔧 创建豆包适配器...")
        adapter = AIAdapterFactory.create(
            AIPlatformType.DOUBAO,
            api_key=api_key,
            model_name='ep-20240520111905-bavcb'  # 示例模型ID
        )
        
        # 发送测试请求
        print("📡 发送测试请求...")
        response = adapter.send_prompt("你好，请简单介绍一下自己，用一句话回答。")
        
        if response.success:
            print("✅ 豆包API集成验证成功!")
            print(f"📝 响应内容: {response.content[:100]}...")
            print(f"⏱️  响应时间: {response.latency:.2f}秒")
            print(f"🔢 使用token数: {response.tokens_used}")
            return True
        else:
            print(f"❌ 豆包API请求失败: {response.error_message}")
            print(f"🏷️  错误类型: {response.error_type}")
            return False
            
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 豆包(Doubao) API集成验证")
    print("="*50)
    
    success = test_doubao_api_integration()
    
    print("\n" + "="*50)
    if success:
        print("🎉 豆包API集成验证成功!")
        print("✅ 您的系统已正确配置豆包API集成")
    else:
        print("⚠️  豆包API集成验证未完成")
        print("💡 请检查API密钥配置并重试")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)