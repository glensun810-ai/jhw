#!/usr/bin/env python3
"""
AI 平台注册验证脚本

用于验证所有 AI 平台是否正确注册，检测平台消失问题

使用方法：
    python backend_python/scripts/verify_ai_platforms.py
"""
import sys
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.ai_adapters.platform_health_monitor import PlatformHealthMonitor


def print_header(title: str):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_platform_status(platform: str, data: dict):
    """打印平台状态"""
    status_icon = {
        'healthy': '✅',
        'degraded': '⚠️ ',
        'unhealthy': '❌'
    }.get(data['status'], '❓')
    
    print(f"\n{status_icon} {platform.upper()}")
    print(f"   Adapter Registered: {'✅' if data['adapter_registered'] else '❌'}")
    print(f"   Provider Registered: {'✅' if data['provider_registered'] else '❌'}")
    print(f"   API Key Configured: {'✅' if data['api_key_configured'] else '❌'}")
    print(f"   Status: {data['status']}")
    print(f"   Message: {data['message']}")


def main():
    """主函数"""
    print_header("AI Platform Registration Verification")
    
    # 运行健康检查
    results = PlatformHealthMonitor.run_health_check()
    
    if not results:
        print("\n❌ Health check failed to return results!")
        sys.exit(1)
    
    # 打印详细状态
    print_header("Platform Details")
    
    for platform in PlatformHealthMonitor.EXPECTED_PLATFORMS:
        if platform in results['platforms']:
            print_platform_status(platform, results['platforms'][platform])
    
    # 打印统计
    print_header("Summary Statistics")
    summary = results['summary']
    print(f"Total Platforms: {summary['total']}")
    print(f"Healthy: {summary['healthy']}")
    print(f"Degraded: {summary['degraded']}")
    print(f"Unhealthy: {summary['unhealthy']}")
    
    # 打印警告
    if results['warnings']:
        print_header("Warnings")
        for warning in results['warnings']:
            print(f"  ⚠️  {warning}")
    
    # 打印错误
    if results['errors']:
        print_header("Errors")
        for error in results['errors']:
            print(f"  ❌ {error}")
    
    # 打印建议
    if results['recommendations']:
        print_header("Recommendations")
        for rec in results['recommendations']:
            print(f"  • {rec}")
    
    # 打印最终状态
    print_header("Final Status")
    
    if results['status'] == 'healthy':
        print("✅ All AI platforms are healthy!")
        sys.exit(0)
    elif results['status'] == 'degraded':
        print("⚠️  Some AI platforms have issues. Review warnings above.")
        sys.exit(0)  # Degraded is acceptable
    else:
        print("❌ AI platform health check FAILED! Review errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
