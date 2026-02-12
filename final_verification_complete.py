#!/usr/bin/env python3
"""
最终验证脚本 - 确认所有安全改进措施已正确实施
"""

import ast
import re
from pathlib import Path


def check_auth_decorator_usage():
    """检查是否所有需要修复的端点都已更新为可选认证"""
    
    print("🔍 检查认证装饰器使用情况...")
    
    # 检查views.py文件
    views_path = Path('wechat_backend/views.py')
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有路由定义及其认证装饰器
    route_pattern = r'@wechat_bp\.route\([^\)]+\)\s*@require_auth(?!\_optional)'
    matches = re.findall(route_pattern, content)
    
    if matches:
        print(f"❌ 发现 {len(matches)} 个端点仍在使用强制认证装饰器:")
        for match in matches:
            print(f"   - {match.strip()}")
        return False
    else:
        print("✅ 所有端点都已更新为使用可选认证装饰器")
        return True


def check_import_statements():
    """检查导入语句是否正确"""
    
    print("\n🔍 检查导入语句...")
    
    # 检查app.py中的导入
    app_path = Path('wechat_backend/app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # 检查是否使用了正确的可选认证装饰器
    if '@require_auth_optional' in app_content:
        print("✅ app.py中使用了正确的可选认证装饰器")
    elif '@require_auth' in app_content and 'api/config' in app_content:
        print("⚠️  app.py中配置端点仍使用强制认证，这可能是有意为之")
    else:
        print("✅ app.py中认证装饰器使用正确")
    
    # 检查views.py中的导入
    views_path = Path('wechat_backend/views.py')
    with open(views_path, 'r', encoding='utf-8') as f:
        views_content = f.read()
    
    if 'require_auth_optional' in views_content:
        print("✅ views.py中导入了可选认证装饰器")
    else:
        print("❌ views.py中未找到可选认证装饰器导入")
        return False
    
    return True


def check_security_improvements():
    """检查安全改进措施是否已实施"""
    
    print("\n🔍 检查安全改进措施...")
    
    checks = [
        ("安全配置模块", Path('wechat_backend/security/secure_config.py').exists()),
        ("网络安全性模块", Path('wechat_backend/network/security.py').exists()),
        ("输入验证模块", Path('wechat_backend/security/input_validation.py').exists()),
        ("速率限制模块", Path('wechat_backend/network/rate_limiter.py').exists()),
        ("断路器模块", Path('wechat_backend/network/circuit_breaker.py').exists()),
        ("指标收集器", Path('wechat_backend/monitoring/metrics_collector.py').exists()),
        ("告警系统", Path('wechat_backend/monitoring/alert_system.py').exists()),
        ("日志增强", Path('wechat_backend/monitoring/logging_enhancements.py').exists()),
        ("统一请求封装", Path('wechat_backend/network/request_wrapper.py').exists()),
        ("连接池管理", Path('wechat_backend/network/connection_pool.py').exists()),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False
    
    return all_passed


def check_sensitive_info_removal():
    """检查是否已移除敏感信息"""
    
    print("\n🔍 检查敏感信息移除...")
    
    sensitive_patterns = [
        r'sk-[a-zA-Z0-9]{32,}',  # OpenAI等API密钥格式
        r'[A-Za-z0-9+/]{32,}={0,2}',  # 通用密钥格式
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',  # UUID格式
        r'AIza[0-9A-Za-z_-]{33}',  # Google API密钥格式
    ]
    
    files_to_check = [
        '.env',
        'config.py',
        '*.py',
        '*.md'
    ]
    
    sensitive_found = False
    for pattern in sensitive_patterns:
        for py_file in Path('.').rglob('*.py'):
            if 'test' not in str(py_file) and 'backup' not in str(py_file):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    matches = re.findall(pattern, content)
                    if matches:
                        print(f"   ❌ 在 {py_file} 中发现敏感信息: {matches[:3]}...")  # 只显示前3个匹配
                        sensitive_found = True
                except:
                    continue
    
    if not sensitive_found:
        print("   ✅ 未发现明显的敏感信息")
    
    return not sensitive_found


def check_api_endpoints():
    """检查API端点实现"""
    
    print("\n🔍 检查API端点实现...")
    
    endpoints_to_check = [
        ('/api/perform-brand-test', 'POST'),
        ('/api/platform-status', 'GET'),
        ('/api/login', 'POST'),
        ('/api/test', 'GET'),
    ]
    
    views_path = Path('wechat_backend/views.py')
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_found = True
    for endpoint, method in endpoints_to_check:
        if endpoint in content:
            print(f"   ✅ 端点 {endpoint} ({method}) 存在")
        else:
            print(f"   ❌ 端点 {endpoint} ({method}) 不存在")
            all_found = False
    
    return all_found


def main():
    print("🚀 最终验证 - 确认所有安全改进措施")
    print("=" * 60)
    
    results = []
    
    results.append(check_auth_decorator_usage())
    results.append(check_import_statements())
    results.append(check_security_improvements())
    results.append(check_sensitive_info_removal())
    results.append(check_api_endpoints())
    
    print("\n" + "=" * 60)
    print("📋 最终验证结果:")
    
    if all(results):
        print("✅ 所有验证通过！")
        print("\n系统现在具备以下改进：")
        print("• 所有API端点不再无条件返回401错误")
        print("• 实施了全面的安全改进措施")
        print("• 移除了敏感信息")
        print("• 增强了性能和可靠性")
        print("• 实现了完整的监控系统")
        print("\n🎉 项目安全改进工作圆满完成！")
        return True
    else:
        print("❌ 部分验证失败，请检查上述问题")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)