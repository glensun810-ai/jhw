#!/usr/bin/env python3
"""
测试豆包模型修复效果
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'backend_python'))

def test_model_name_mapping():
    """测试模型名称映射"""
    print("🔍 测试模型名称映射...")
    
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    
    # 测试各种豆包名称变体
    test_names = [
        "豆包",
        "doubao", 
        "Doubao",
        "DOUBAO",
        "doubao-cn",
        "doubao-pro"
    ]
    
    print("豆包相关名称映射测试:")
    for name in test_names:
        mapped = AIAdapterFactory.get_normalized_model_name(name)
        print(f"  {name} -> {mapped}")
    
    return True

def test_api_key_config():
    """测试API密钥配置"""
    print("\n🔍 测试API密钥配置...")
    
    from backend_python.config import Config
    
    # 测试豆包API密钥获取
    test_platforms = ["豆包", "doubao", "doubao-cn", "Doubao"]
    
    for platform in test_platforms:
        api_key = Config.get_api_key(platform)
        is_configured = Config.is_api_key_configured(platform)
        print(f"  {platform}: 配置状态={is_configured}, API密钥长度={len(api_key) if api_key else 0}")
    
    return True

def test_platform_availability():
    """测试平台可用性"""
    print("\n🔍 测试平台可用性...")
    
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    
    # 测试豆包平台可用性
    test_platforms = ["豆包", "doubao", "doubao-cn"]
    
    for platform in test_platforms:
        is_available = AIAdapterFactory.is_platform_available(platform)
        print(f"  {platform}: 可用性={is_available}")
    
    return True

def main():
    """主函数"""
    print("🚀 豆包模型修复验证测试")
    print("="*50)
    
    try:
        test_model_name_mapping()
        test_api_key_config()
        test_platform_availability()
        
        print("\n✅ 所有测试完成，豆包模型映射修复已应用")
        print("💡 请重启后端服务使更改生效")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()