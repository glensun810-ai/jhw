#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证Token配置是否正确
"""

import os
import sys
from pathlib import Path

def verify_token_config():
    """验证Token配置"""
    print("🔍 验证Token配置...")
    
    # 添加项目路径到Python路径
    project_root = Path(__file__).parent
    backend_path = project_root / "backend_python"
    sys.path.insert(0, str(backend_path))
    
    # 检查 .env 文件
    env_file = project_root / ".env"
    if env_file.exists():
        print("✅ 找到 .env 文件")
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
            print(f"📄 .env 文件内容:\n{env_content}")
            
        # 从 .env 文件加载环境变量
        from dotenv import load_dotenv
        load_dotenv(str(env_file))
    else:
        print("❌ 未找到 .env 文件")
        return False
    
    # 获取环境变量
    token = os.getenv('WECHAT_TOKEN')
    app_id = os.getenv('WECHAT_APP_ID')
    app_secret = os.getenv('WECHAT_APP_SECRET')
    
    print(f"\n📋 当前环境变量:")
    print(f"   WECHAT_TOKEN: {'已设置' if token else '未设置'}")
    print(f"   WECHAT_APP_ID: {'已设置' if app_id else '未设置'}")
    print(f"   WECHAT_APP_SECRET: {'已设置' if app_secret else '未设置'}")
    
    if token:
        print(f"   Token值: {token}")
        print(f"   Token长度: {len(token)}")
        if 3 <= len(token) <= 32:
            print("✅ Token长度符合要求 (3-32位)")
        else:
            print("❌ Token长度不符合要求，应在3-32位之间")
            return False
    else:
        print("❌ WECHAT_TOKEN 未设置")
        return False
    
    # 检查后端配置文件
    try:
        # 临时将backend_python加入路径
        sys.path.insert(0, str(backend_path))
        
        # 导入配置
        from config import Config
        backend_token = Config.WECHAT_TOKEN
        
        print(f"\n⚙️ 后端配置中的Token: {backend_token}")
        
        if backend_token == token:
            print("✅ 前端配置与后端配置一致")
        else:
            print("❌ 前端配置与后端配置不一致")
            return False
            
    except ImportError as e:
        print(f"❌ 导入配置失败: {e}")
        return False
    except AttributeError as e:
        print(f"❌ 配置属性不存在: {e}")
        return False
    
    # 验证签名函数测试
    import hashlib
    import hmac
    
    def verify_wechat_signature(token, signature, timestamp, nonce):
        """验证微信签名的函数"""
        sorted_params = sorted([token, timestamp, nonce])
        concatenated_str = ''.join(sorted_params)
        calculated_signature = hashlib.sha1(concatenated_str.encode('utf-8')).hexdigest()
        return calculated_signature == signature
    
    # 测试签名验证功能
    test_timestamp = "1234567890"
    test_nonce = "abcdef"
    test_signature = hashlib.sha1(''.join(sorted([token, test_timestamp, test_nonce])).encode('utf-8')).hexdigest()
    
    verification_result = verify_wechat_signature(token, test_signature, test_timestamp, test_nonce)
    print(f"\n🧪 签名验证测试: {'通过' if verification_result else '失败'}")
    
    if verification_result:
        print("\n🎉 Token配置验证成功!")
        print("✅ 您的Token配置正确，可以用于微信服务器验证")
        return True
    else:
        print("\n❌ Token配置验证失败!")
        return False

if __name__ == "__main__":
    # 检查是否安装了python-dotenv
    try:
        import dotenv
    except ImportError:
        print("⚠️ 未安装python-dotenv，请先运行: pip install python-dotenv")
        exit(1)
    
    success = verify_token_config()
    if not success:
        print("\n💡 建议修复方案:")
        print("1. 确保 .env 文件中 WECHAT_TOKEN 设置正确")
        print("2. 确保后端服务已重启以加载新的环境变量")
        print("3. 检查微信小程序后台的Token设置是否与此一致")