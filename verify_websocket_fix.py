#!/usr/bin/env python3
"""
P0 WebSocket 前端配置修复验证脚本

验证内容：
1. 协议是否正确修改为 wss://
2. 开发环境地址是否修改为 ws://127.0.0.1:8765
3. 占位符是否已替换
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
websocket_file = project_root / 'miniprogram' / 'services' / 'webSocketClient.js'

print("=" * 60)
print("P0 WebSocket 前端配置修复验证")
print("=" * 60)

try:
    with open(websocket_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('wss:// 协议 (生产环境)', 'wss://${envId}.ws.tencentcloudapi.com'),
        ('ws:// 协议 (开发环境)', 'ws://127.0.0.1:8765'),
        ('注释更新', '【P0 修复 - 2026-03-03】'),
        ('错误协议已移除', 'wxs://your-dev-ws-server.com', True),  # True 表示应该不存在
        ('错误占位符已移除', 'wxs://${envId}', True),
    ]
    
    all_passed = True
    
    for check_name, pattern, *should_not_exist in checks:
        exists = pattern in content
        expected = not should_not_exist[0] if should_not_exist else True
        
        if exists == expected:
            print(f"  ✅ {check_name}: 正确")
        else:
            print(f"  ❌ {check_name}: {'不应存在但存在' if exists else '不存在'}")
            all_passed = False
    
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if all_passed:
        print("✅ WebSocket 前端配置修复成功！")
        print("\n修复内容:")
        print("  - 生产/体验版：wxs:// → wss://")
        print("  - 开发版：wxs://your-dev-ws-server.com → ws://127.0.0.1:8765")
        print("\n下一步操作:")
        print("  1. 重启微信开发者工具")
        print("  2. 确保后端 WebSocket 服务在 8765 端口运行")
        print("  3. 执行诊断任务测试 WebSocket 连接")
        print("  4. 检查 Console 是否有 WebSocket 连接成功日志")
        return 0
    else:
        print("❌ 部分检查未通过，请检查代码")
        return 1

except Exception as e:
    print(f"❌ 验证失败：{e}")
    return 1
