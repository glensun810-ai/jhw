#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单验证Token配置
"""

import os
import hashlib
import sys
from pathlib import Path

def simple_token_check():
    """简单检查Token配置"""
    print("🔍 检查Token配置...")
    
    # 检查 .env 文件
    env_file = Path("./.env")
    if env_file.exists():
        print("✅ 找到 .env 文件")
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            token_found = False
            for line in lines:
                if line.startswith("WECHAT_TOKEN="):
                    token_value = line.split("=", 1)[1].strip().strip('"\'')
                    print(f"   当前Token值: {token_value}")
                    token_found = True
                    
                    # 检查Token长度
                    if 3 <= len(token_value) <= 32:
                        print("✅ Token长度符合要求 (3-32位)")
                    else:
                        print("❌ Token长度不符合要求，应在3-32位之间")
                        
            if not token_found:
                print("❌ .env 文件中未找到 WECHAT_TOKEN 配置")
                return False
    else:
        print("❌ 未找到 .env 文件")
        return False
    
    # 检查环境变量
    token_from_env = os.environ.get('WECHAT_TOKEN')
    if token_from_env:
        print(f"✅ 环境变量中找到 WECHAT_TOKEN: {token_from_env}")
    else:
        print("⚠️ 环境变量中未找到 WECHAT_TOKEN，可能需要重启终端或服务")
    
    # 检查配置文件
    config_file = Path("./backend_python/config.py")
    if config_file.exists():
        print("\n✅ 找到后端配置文件")
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'WECHAT_TOKEN' in content:
                print("✅ 配置文件中包含 WECHAT_TOKEN 配置")
                
                # 检查是否从环境变量读取
                if 'os.environ.get(\'WECHAT_TOKEN\')' in content:
                    print("✅ 配置文件正确从环境变量读取Token")
                else:
                    print("⚠️ 配置文件可能使用硬编码的Token值")
            else:
                print("❌ 配置文件中未找到 WECHAT_TOKEN 配置")
    
    print("\n📋 验证结果总结:")
    print("1. 确保 .env 文件中的 WECHAT_TOKEN 与微信小程序后台设置的Token一致")
    print("2. 确保后端服务已重启以加载新的环境变量")
    print("3. 如果仍有问题，请检查微信小程序后台的URL是否正确指向您的服务器")
    
    print(f"\n🎯 您的Token 'yunchengqihangjinhuawangeo' 长度为 {len('yunchengqihangjinhuawangeo')} 位")
    if 3 <= len('yunchengqihangjinhuawangeo') <= 32:
        print("✅ Token长度符合要求")
    else:
        print("❌ Token长度不符合要求")
    
    # 简单的签名验证演示
    print(f"\n💡 签名验证原理:")
    print(f"   1. 微信服务器会发送 timestamp, nonce, signature 参数")
    print(f"   2. 后端使用同样的算法验证: SHA1排序后的[Token, timestamp, nonce]")
    print(f"   3. 如果计算出的签名与微信发送的signature一致，则验证通过")
    
    return True

if __name__ == "__main__":
    simple_token_check()