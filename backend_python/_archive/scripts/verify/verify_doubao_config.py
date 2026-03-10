#!/usr/bin/env python3
"""
验证豆包 API Key 配置状态
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def verify_doubao_config():
    print("=" * 80)
    print("豆包 API Key 配置验证")
    print("=" * 80)
    print()
    
    # 1. 检查环境变量
    import os
    doubao_key = os.environ.get('DOUBAO_API_KEY', '')
    ark_key = os.environ.get('ARK_API_KEY', '')
    
    print("1. 环境变量检查:")
    print(f"   DOUBAO_API_KEY: {'✓ 已设置' if doubao_key and doubao_key != '${ARK_API_KEY}' else '✗ 未设置'}")
    print(f"   ARK_API_KEY:    {'✓ 已设置' if ark_key and ark_key != '${ARK_API_KEY}' else '✗ 未设置'}")
    print()
    
    # 2. 检查 config_manager
    try:
        from wechat_backend.config_manager import config_manager
        
        print("2. Config Manager 检查:")
        key = config_manager.get_api_key('doubao')
        print(f"   config_manager.get_api_key('doubao'): {'✓ 已配置' if key else '✗ 未配置'}")
        if key:
            print(f"   Key 前缀：{key[:10]}...")
        print()
        
    except Exception as e:
        print(f"2. Config Manager 检查失败：{e}")
        print()
    
    # 3. 检查 AI Adapter Factory
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        print("3. AI Adapter Factory 检查:")
        is_registered = 'doubao' in [str(t).lower() for t in AIAdapterFactory._adapters.keys()]
        is_available = AIAdapterFactory.is_platform_available('doubao')
        print(f"   Adapter 已注册：{'✓' if is_registered else '✗'}")
        print(f"   平台可用：{'✓' if is_available else '✗'}")
        print()
        
    except Exception as e:
        print(f"3. AI Adapter Factory 检查失败：{e}")
        print()
    
    # 4. 检查最新日志记录
    log_file = Path(__file__).parent / 'data' / 'ai_responses' / 'ai_responses.jsonl'
    
    print("4. 最新日志记录检查:")
    if log_file.exists():
        import json
        from collections import Counter
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-20:]  # 最后 20 条
        
        platforms = Counter()
        for line in lines:
            try:
                record = json.loads(line.strip())
                platform = record.get('platform', 'Unknown')
                if isinstance(platform, dict):
                    platform = platform.get('name', 'Unknown')
                platforms[platform] += 1
            except:
                pass
        
        print(f"   最新 20 条记录平台分布:")
        for platform, count in platforms.most_common():
            status = '✓' if platform != '豆包' else '✗'
            print(f"   {status} {platform}: {count} 条")
        
        if '豆包' not in platforms:
            print()
            print("   ⚠️  最新 20 条记录中没有豆包日志!")
    else:
        print(f"   日志文件不存在：{log_file}")
    
    print()
    print("=" * 80)
    print("验证完成")
    print("=" * 80)
    print()
    
    # 5. 总结和建议
    has_key = bool(doubao_key and doubao_key != '${ARK_API_KEY}') or bool(ark_key and ark_key != '${ARK_API_KEY}')
    
    if not has_key:
        print("❌ 豆包 API Key 未配置")
        print()
        print("修复步骤:")
        print("1. 获取豆包 API Key:")
        print("   访问：https://console.volcengine.com/ark")
        print()
        print("2. 配置到环境变量:")
        print("   # 编辑 .env 文件")
        print("   DOUBAO_API_KEY=your_api_key_here")
        print("   # 或")
        print("   ARK_API_KEY=your_api_key_here")
        print()
        print("3. 重启应用")
        print()
    else:
        print("✅ 豆包 API Key 已配置")
        print()
        print("如果仍然没有豆包日志，请检查:")
        print("1. NXM 执行引擎是否选择了豆包平台")
        print("2. 豆包 API endpoint 配置是否正确")
        print("3. 查看 app.log 中是否有豆包相关的错误日志")

if __name__ == '__main__':
    verify_doubao_config()
