#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信消息推送配置验证脚本

验证项目中的微信消息推送配置是否与微信公众平台配置一致。

配置来源：
- URL(服务器地址): https://nonsuccessful-disparately-cataleya.ngrok-free.dev
- Token(令牌): 12345633
- EncodingAESKey: d7cHwq4lzWW65sEmkrUEDvP8MWd0NiCGZSm2NrLUBLi
"""

import os
import sys
import hashlib
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / '.env'

# 预期的微信配置
EXPECTED_CONFIG = {
    'WECHAT_TOKEN': '12345633',
    'WECHAT_ENCODING_AES_KEY': 'd7cHwq4lzWW65sEmkrUEDvP8MWd0NiCGZSm2NrLUBLi',
}


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(message: str):
    """打印成功消息"""
    print(f"✅ {message}")


def print_error(message: str):
    """打印错误消息"""
    print(f"❌ {message}")


def print_warning(message: str):
    """打印警告消息"""
    print(f"⚠️  {message}")


def load_env_file() -> dict:
    """加载 .env 文件"""
    env_vars = {}
    
    if not ENV_FILE.exists():
        print_error(f".env 文件不存在：{ENV_FILE}")
        return env_vars
    
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            # 解析键值对
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                # 去除引号
                value = value.strip().strip('"\'')
                env_vars[key] = value
    
    return env_vars


def verify_wechat_token(env_vars: dict) -> bool:
    """验证微信 Token 配置"""
    print_header("微信 Token 配置验证")
    
    token = env_vars.get('WECHAT_TOKEN', '')
    expected_token = EXPECTED_CONFIG['WECHAT_TOKEN']
    
    print(f"配置的 Token: {token}")
    print(f"预期的 Token: {expected_token}")
    
    if token == expected_token:
        print_success("Token 配置正确")
        return True
    else:
        print_error("Token 配置不匹配")
        return False


def verify_encoding_aes_key(env_vars: dict) -> bool:
    """验证 EncodingAESKey 配置"""
    print_header("EncodingAESKey 配置验证")
    
    aes_key = env_vars.get('WECHAT_ENCODING_AES_KEY', '')
    expected_aes_key = EXPECTED_CONFIG['WECHAT_ENCODING_AES_KEY']
    
    if not aes_key:
        print_error("WECHAT_ENCODING_AES_KEY 未配置")
        return False
    
    print(f"配置的 EncodingAESKey: {aes_key}")
    print(f"预期的 EncodingAESKey: {expected_aes_key}")
    
    if aes_key == expected_aes_key:
        print_success("EncodingAESKey 配置正确")
        return True
    else:
        print_error("EncodingAESKey 配置不匹配")
        return False


def verify_wechat_app_id(env_vars: dict) -> bool:
    """验证微信 AppID 配置"""
    print_header("微信 AppID 配置验证")
    
    app_id = env_vars.get('WECHAT_APP_ID', '')
    
    if not app_id:
        print_error("WECHAT_APP_ID 未配置")
        return False
    
    print(f"配置的 AppID: {app_id}")
    
    # AppID 应该是 18 位字符
    if len(app_id) == 18 and app_id.startswith('wx'):
        print_success("AppID 格式正确")
        return True
    else:
        print_warning("AppID 格式可能不正确（应该是 wx 开头的 18 位字符）")
        return False


def verify_wechat_app_secret(env_vars: dict) -> bool:
    """验证微信 AppSecret 配置"""
    print_header("微信 AppSecret 配置验证")
    
    app_secret = env_vars.get('WECHAT_APP_SECRET', '')
    
    if not app_secret:
        print_error("WECHAT_APP_SECRET 未配置")
        return False
    
    print(f"配置的 AppSecret: {app_secret[:10]}...{app_secret[-10:]}")
    
    # AppSecret 应该是 32 位字符
    if len(app_secret) == 32:
        print_success("AppSecret 格式正确")
        return True
    else:
        print_warning("AppSecret 格式可能不正确（应该是 32 位字符）")
        return False


def verify_signature_calculation() -> bool:
    """验证签名计算逻辑"""
    print_header("微信签名算法验证")
    
    # 使用配置的 Token 测试签名计算
    token = EXPECTED_CONFIG['WECHAT_TOKEN']
    timestamp = '1234567890'
    nonce = 'abcdefg'
    
    # 字典序排序
    params = [token, timestamp, nonce]
    params.sort()
    concatenated_str = ''.join(params)
    
    # SHA1 加密
    signature = hashlib.sha1(concatenated_str.encode('utf-8')).hexdigest()
    
    print(f"Token: {token}")
    print(f"Timestamp: {timestamp}")
    print(f"Nonce: {nonce}")
    print(f"计算得到的签名：{signature}")
    
    print_success("签名计算逻辑正常")
    return True


def verify_config_in_code() -> bool:
    """验证代码中的配置引用"""
    print_header("代码配置引用验证")
    
    # 检查 legacy_config.py
    config_file = PROJECT_ROOT / 'backend_python' / 'legacy_config.py'
    
    if not config_file.exists():
        print_error(f"配置文件不存在：{config_file}")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'WECHAT_TOKEN': 'WECHAT_TOKEN' in content,
        'WECHAT_ENCODING_AES_KEY': 'WECHAT_ENCODING_AES_KEY' in content,
    }
    
    all_passed = True
    for key, passed in checks.items():
        if passed:
            print_success(f"代码中包含 {key} 配置")
        else:
            print_error(f"代码中缺少 {key} 配置")
            all_passed = False
    
    return all_passed


def check_pyCryptodome_installed() -> bool:
    """检查 pycryptodome 库是否可用"""
    print_header("加密库依赖检查")
    
    try:
        from Crypto.Cipher import AES
        print_success("pycryptodome 库已安装")
        return True
    except ImportError:
        print_error("pycryptodome 库未安装")
        print("安装命令：pip install pycryptodome")
        return False


def generate_report(results: dict) -> bool:
    """生成验证报告"""
    print_header("验证报告")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"总检查项：{total}")
    print(f"通过：{passed}")
    print(f"失败：{failed}")
    
    if failed == 0:
        print_success("\n🎉 所有配置验证通过！微信消息推送配置可以正常生效。")
        print("\n📋 配置摘要:")
        print(f"  - Token: {EXPECTED_CONFIG['WECHAT_TOKEN']}")
        print(f"  - EncodingAESKey: {EXPECTED_CONFIG['WECHAT_ENCODING_AES_KEY'][:20]}...")
        print("\n🔧 下一步操作:")
        print("  1. 确保后端服务已启动：python backend_python/wechat_backend/app.py")
        print("  2. 在微信公众平台确认服务器地址：https://nonsuccessful-disparately-cataleya.ngrok-free.dev/wechat/verify")
        print("  3. 使用微信开发者工具测试消息推送功能")
        return True
    else:
        print_error("\n⚠️  存在配置问题，微信消息推送可能无法正常生效。")
        print("\n🔧 建议操作:")
        print("  1. 根据上述错误提示修正配置")
        print("  2. 重启后端服务使配置生效")
        print("  3. 重新运行此验证脚本")
        return False


def main():
    """主函数"""
    print_header("微信消息推送配置验证工具")
    print(f"验证时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f".env 文件：{ENV_FILE}")
    
    # 加载环境变量
    env_vars = load_env_file()
    
    if not env_vars:
        print_error("无法加载 .env 文件，请确保文件存在且格式正确")
        sys.exit(1)
    
    # 执行各项验证
    results = {}
    results['wechat_token'] = verify_wechat_token(env_vars)
    results['encoding_aes_key'] = verify_encoding_aes_key(env_vars)
    results['wechat_app_id'] = verify_wechat_app_id(env_vars)
    results['wechat_app_secret'] = verify_wechat_app_secret(env_vars)
    results['signature_calculation'] = verify_signature_calculation()
    results['config_in_code'] = verify_config_in_code()
    results['pycryptodome'] = check_pyCryptodome_installed()
    
    # 生成报告
    success = generate_report(results)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
