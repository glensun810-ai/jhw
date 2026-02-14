#!/usr/bin/env python3
"""
最终验证脚本
验证所有安全改进措施是否正确实施
"""

import os
import sys
import importlib
from pathlib import Path


def check_module_availability():
    """检查所有新模块是否可以正确导入"""
    modules_to_check = [
        "wechat_backend.security.secure_config",
        "wechat_backend.network.security",
        "wechat_backend.network.connection_pool",
        "wechat_backend.network.circuit_breaker",
        "wechat_backend.network.retry_mechanism",
        "wechat_backend.network.rate_limiter",
        "wechat_backend.network.request_wrapper",
        "wechat_backend.monitoring.metrics_collector",
        "wechat_backend.monitoring.alert_system",
        "wechat_backend.monitoring.logging_enhancements",
    ]
    
    print("🔍 检查模块可用性...")
    all_imported = True
    
    for module_name in modules_to_check:
        try:
            importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}: {e}")
            all_imported = False
    
    return all_imported


def check_file_existence():
    """检查所有必需的文件是否存在"""
    files_to_check = [
        "wechat_backend/security/secure_config.py",
        "wechat_backend/network/security.py",
        "wechat_backend/network/connection_pool.py",
        "wechat_backend/network/circuit_breaker.py",
        "wechat_backend/network/retry_mechanism.py",
        "wechat_backend/network/rate_limiter.py",
        "wechat_backend/network/request_wrapper.py",
        "wechat_backend/monitoring/metrics_collector.py",
        "wechat_backend/monitoring/alert_system.py",
        "wechat_backend/monitoring/logging_enhancements.py",
        "wechat_backend/ai_adapters/deepseek_adapter.py",  # 更新后的适配器
        ".env.example",  # 安全的环境变量示例
    ]
    
    print("\n📁 检查文件存在性...")
    all_exist = True
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path}")
            all_exist = False
    
    return all_exist


def check_sensitive_data_removal():
    """检查是否已移除敏感数据"""
    files_to_check = [
        ".env",
        "test_doubao_api.py",
        "test_real_api_calls_updated.py",
        "test_api_keys.py",
        "real_api_implementation_summary.md",
    ]
    
    print("\n🔒 检查敏感数据移除...")
    sensitive_patterns = [
        "sk-13908093890f46fb82c52a01c8dfc464",
        "sk-5261a4dfdf964a5c9a6364128cc4c653", 
        "2a376e32-8877-4df8-9865-7eb3e99c9f92",
        "AIzaSyCOeSqGt-YluHUQkdStzc-RVkufFKBldCE",
        "504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh",
        "wx8876348e089bc261",
        "6d43225261bbfc9bfe3c68de9e069b66",
    ]
    
    all_clean = True
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            found_patterns = []
            for pattern in sensitive_patterns:
                if pattern in content:
                    found_patterns.append(pattern)
            
            if found_patterns:
                print(f"  ✗ {file_path}: 发现敏感数据 {found_patterns}")
                all_clean = False
            else:
                print(f"  ✓ {file_path}: 无敏感数据")
    
    return all_clean


def run_all_checks():
    """运行所有检查"""
    print("🚀 开始最终验证...")
    print("=" * 50)
    
    results = []
    
    # 检查模块可用性
    modules_ok = check_module_availability()
    results.append(("模块可用性", modules_ok))
    
    # 检查文件存在性
    files_ok = check_file_existence()
    results.append(("文件存在性", files_ok))
    
    # 检查敏感数据移除
    sensitive_clean = check_sensitive_data_removal()
    results.append(("敏感数据移除", sensitive_clean))
    
    print("\n" + "=" * 50)
    print("📋 验证结果摘要:")
    
    all_passed = True
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {check_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n🎯 总体结果: {'✓ ALL CHECKS PASSED' if all_passed else '✗ SOME CHECKS FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
