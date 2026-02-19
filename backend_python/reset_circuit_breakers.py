#!/usr/bin/env python3
"""
工具脚本：重置所有AI平台的熔断器
用于解决熔断器持续开启导致的服务不可用问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

from wechat_backend.circuit_breaker import reset_circuit_breaker, _circuit_breakers
from wechat_backend.logging_config import api_logger


def reset_all_circuit_breakers():
    """重置所有AI平台的熔断器"""
    print("正在重置所有AI平台的熔断器...")
    api_logger.info("Resetting all AI platform circuit breakers...")
    
    platforms_to_reset = [
        ("doubao", "doubao-pro"),
        ("doubao", "doubao"),
        # 豆包断路器（2026 年 2 月 19 日更新：使用新部署点）
        ("doubao", "ep-20260212000000-gd5tq"),
        ("qwen", "qwen-max"),
        ("qwen", "qwen"),
        ("deepseek", "deepseek-chat"),
        ("deepseek", "deepseek-coder"),
        ("deepseek", "deepseek"),
        ("zhipu", "glm-4"),
        ("zhipu", "glm-4-air"),
        ("zhipu", "zhipu"),
        ("deepseekr1", "deepseek-r1"),
        ("deepseekr1", "deepseekr1"),
        ("chatgpt", "gpt-4"),
        ("chatgpt", "gpt-3.5-turbo"),
        ("gemini", "gemini-pro"),
        ("gemini", "gemini"),
    ]
    
    for platform, model in platforms_to_reset:
        try:
            reset_circuit_breaker(platform, model)
            print(f"✓ 已重置 {platform} ({model}) 的熔断器")
        except Exception as e:
            print(f"✗ 重置 {platform} ({model}) 的熔断器失败: {e}")
    
    # 显示当前所有熔断器的状态
    print("\n当前熔断器状态:")
    print("-" * 50)
    for name, cb in _circuit_breakers.items():
        state_info = cb.get_state_info()
        print(f"熔断器: {name}")
        print(f"  状态: {state_info['state']}")
        print(f"  失败计数: {state_info['failure_count']}/{state_info['failure_threshold']}")
        print(f"  剩余恢复时间: {state_info['remaining_time']:.1f}秒")
        print()


def reset_specific_platform(platform_name: str, model_name: str = None):
    """重置特定平台的熔断器"""
    print(f"正在重置 {platform_name} 平台的熔断器...")
    api_logger.info(f"Resetting circuit breaker for {platform_name} ({model_name or 'default'})...")
    
    try:
        reset_circuit_breaker(platform_name, model_name)
        print(f"✓ 已重置 {platform_name} ({model_name or 'default'}) 的熔断器")
        
        # 显示该熔断器的当前状态
        name = f"{platform_name}_{model_name}" if model_name else platform_name
        if name in _circuit_breakers:
            cb = _circuit_breakers[name]
            state_info = cb.get_state_info()
            print(f"\n熔断器 {name} 当前状态:")
            print(f"  状态: {state_info['state']}")
            print(f"  失败计数: {state_info['failure_count']}/{state_info['failure_threshold']}")
            print(f"  剩余恢复时间: {state_info['remaining_time']:.1f}秒")
        
    except Exception as e:
        print(f"✗ 重置 {platform_name} ({model_name or 'default'}) 的熔断器失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            reset_all_circuit_breakers()
        elif sys.argv[1] == "--platform":
            if len(sys.argv) >= 3:
                platform = sys.argv[2]
                model = sys.argv[3] if len(sys.argv) > 3 else None
                reset_specific_platform(platform, model)
            else:
                print("用法: python reset_circuit_breakers.py --platform <platform_name> [model_name]")
        else:
            print("用法:")
            print("  python reset_circuit_breakers.py --all                    # 重置所有熔断器")
            print("  python reset_circuit_breakers.py --platform <平台名> [模型名]  # 重置指定平台熔断器")
    else:
        reset_all_circuit_breakers()