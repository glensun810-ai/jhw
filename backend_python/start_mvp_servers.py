#!/usr/bin/env python3
"""
MVP服务器启动脚本
用于启动支持所有AI平台的后端服务
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

def check_api_keys():
    """检查API密钥是否配置"""
    print("🔍 检查API密钥配置...")
    
    required_keys = [
        ('DEEPSEEK_API_KEY', 'DeepSeek'),
        ('QWEN_API_KEY', '通义千问'),
        ('ZHIPU_API_KEY', '智谱AI'),
        ('DOUBAO_API_KEY', '豆包')
    ]
    
    all_configured = True
    for key, name in required_keys:
        value = os.getenv(key)
        if value and len(value.strip()) > 0:
            print(f"   ✅ {name} API密钥已配置")
        else:
            print(f"   ❌ {name} API密钥未配置")
            all_configured = False
    
    return all_configured

def verify_adapters():
    """验证适配器是否正确实现"""
    print("\n🔍 验证AI适配器实现...")
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        platforms = [
            (AIPlatformType.DEEPSEEK, "DeepSeek"),
            (AIPlatformType.QWEN, "通义千问"),
            (AIPlatformType.ZHIPU, "智谱AI"),
            (AIPlatformType.DOUBAO, "豆包")
        ]
        
        for platform_type, name in platforms:
            try:
                # 尝试创建适配器（使用空密钥，仅测试初始化）
                adapter_class = AIAdapterFactory.get_adapter_class(platform_type)
                print(f"   ✅ {name} 适配器已找到: {adapter_class.__name__}")
            except Exception as e:
                print(f"   ❌ {name} 适配器验证失败: {e}")
                return False
        
        print("   ✅ 所有适配器验证通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 适配器验证异常: {e}")
        return False

def verify_mvp_endpoints():
    """验证MVP端点是否已注册"""
    print("\n🔍 验证MVP端点注册...")
    
    try:
        import importlib.util
        views_path = os.path.join(os.path.dirname(__file__), 'wechat_backend', 'views.py')
        spec = importlib.util.spec_from_file_location("views", views_path)
        views_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(views_module)
        
        # 检查端点是否存在
        endpoints = [
            ('mvp_deepseek_test', 'DeepSeek MVP端点'),
            ('mvp_qwen_test', '通义千问MVP端点'),
            ('mvp_zhipu_test', '智谱AIMVP端点'),
            ('mvp_brand_test', '豆包MVP端点')
        ]
        
        for func_name, desc in endpoints:
            if hasattr(views_module, func_name):
                print(f"   ✅ {desc} 已注册")
            else:
                print(f"   ❌ {desc} 未找到")
                return False
        
        print("   ✅ 所有MVP端点验证通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 端点验证异常: {e}")
        return False

def start_flask_server():
    """启动Flask服务器"""
    print("\n🚀 启动Flask服务器...")
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
        
        # 启动Flask应用
        process = subprocess.Popen([
            sys.executable, '-m', 'flask', 
            '--app', 'wechat_backend.app:app', 
            'run', 
            '--host', '0.0.0.0', 
            '--port', '5000',
            '--debug'
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 等待服务器启动
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("   ✅ Flask服务器启动成功")
            print(f"   🌐 访问地址: http://localhost:5001")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ Flask服务器启动失败")
            print(f"   STDOUT: {stdout}")
            print(f"   STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"   ❌ 启动Flask服务器异常: {e}")
        return None

def main():
    """主函数"""
    print(f"{'='*60}")
    print("MVP AI平台集成验证启动器")
    print(f"{'='*60}")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行验证
    checks = [
        ("API密钥配置", check_api_keys),
        ("AI适配器验证", verify_adapters),
        ("MVP端点验证", verify_mvp_endpoints)
    ]
    
    all_passed = True
    for name, check_func in checks:
        if not check_func():
            all_passed = False
    
    if not all_passed:
        print(f"\n❌ 验证未全部通过，请检查上述错误")
        return 1
    
    print(f"\n✅ 所有验证通过！可以启动服务器")
    
    # 询问是否启动服务器
    response = input("\n是否启动Flask服务器？(y/n): ").lower().strip()
    if response in ['y', 'yes', '是']:
        process = start_flask_server()
        if process:
            print(f"\n🎉 MVP服务器已启动！")
            print(f"📋 功能列表:")
            print(f"   • DeepSeek MVP端点: POST /api/mvp/deepseek-test")
            print(f"   • 通义千问MVP端点: POST /api/mvp/qwen-test") 
            print(f"   • 智谱AIMVP端点: POST /api/mvp/zhipu-test")
            print(f"   • 豆包MVP端点: POST /api/mvp/brand-test")
            print(f"\n📱 前端页面:")
            print(f"   • 平台选择器: /pages/mvp-platform-selector/")
            print(f"\n💡 提示: 服务器将在前台运行，按 Ctrl+C 停止")
            
            try:
                # 等待进程结束
                process.wait()
            except KeyboardInterrupt:
                print(f"\n\n👋 正在停止服务器...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                print("✅ 服务器已停止")
        else:
            print(f"\n❌ 服务器启动失败")
            return 1
    else:
        print(f"\n✅ 验证完成，未启动服务器")
    
    return 0

if __name__ == "__main__":
    exit(main())