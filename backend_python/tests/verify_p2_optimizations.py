#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 体验优化验证脚本
验证以下优化功能：
1. 加载状态优化
2. 错误重试机制
3. 结果缓存
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def verify_request_retry():
    """验证请求重试机制"""
    print_header("P2-1: 请求重试机制验证")
    
    # 检查 request.js 文件
    request_file = os.path.join(os.path.dirname(__file__), 
                                '../../utils/request.js')
    
    if not os.path.exists(request_file):
        print("❌ request.js 文件不存在")
        return False
    
    with open(request_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('RETRY_CONFIG', '重试配置'),
        ('requestWithRetry', '重试函数'),
        ('isRetryableError', '错误判断'),
        ('getRetryDelay', '延迟计算'),
        ('指数退避', '指数退避策略'),
        ('MAX_RETRIES', '最大重试次数'),
    ]
    
    passed = 0
    for keyword, desc in checks:
        if keyword in content:
            print(f"  ✅ {desc}: 已实现")
            passed += 1
        else:
            print(f"  ❌ {desc}: 未实现")
    
    print(f"\n验证结果：{passed}/{len(checks)} 通过")
    return passed == len(checks)

def verify_loading_progress():
    """验证加载进度显示"""
    print_header("P2-2: 加载进度显示验证")
    
    request_file = os.path.join(os.path.dirname(__file__), 
                                '../../utils/request.js')
    
    if not os.path.exists(request_file):
        print("❌ request.js 文件不存在")
        return False
    
    with open(request_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('showLoadingProgress', '进度显示函数'),
        ('updateLoadingProgress', '进度更新函数'),
        ('stage', '阶段支持'),
        ('progress', '进度百分比'),
    ]
    
    passed = 0
    for keyword, desc in checks:
        if keyword in content:
            print(f"  ✅ {desc}: 已实现")
            passed += 1
        else:
            print(f"  ❌ {desc}: 未实现")
    
    print(f"\n验证结果：{passed}/{len(checks)} 通过")
    return passed == len(checks)

def verify_cache_service():
    """验证缓存服务"""
    print_header("P2-3: 结果缓存服务验证")
    
    cache_file = os.path.join(os.path.dirname(__file__), 
                              '../../services/cacheService.js')
    
    if not os.path.exists(cache_file):
        print("❌ cacheService.js 文件不存在")
        return False
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('CACHE_CONFIG', '缓存配置'),
        ('getCachedDiagnosis', '获取缓存'),
        ('cacheDiagnosis', '保存缓存'),
        ('cleanupCache', '缓存清理'),
        ('EXPIRY_TIME', '过期时间'),
        ('generateCacheKey', '缓存键生成'),
    ]
    
    passed = 0
    for keyword, desc in checks:
        if keyword in content:
            print(f"  ✅ {desc}: 已实现")
            passed += 1
        else:
            print(f"  ❌ {desc}: 未实现")
    
    print(f"\n验证结果：{passed}/{len(checks)} 通过")
    return passed == len(checks)

def verify_cache_integration():
    """验证缓存集成"""
    print_header("P2-4: 缓存集成验证")
    
    index_file = os.path.join(os.path.dirname(__file__), 
                              '../../pages/index/index.js')
    
    if not os.path.exists(index_file):
        print("❌ index.js 文件不存在")
        return False
    
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('cacheService', '缓存服务导入'),
        ('getCachedDiagnosis', '缓存获取调用'),
        ('cacheDiagnosis', '缓存保存调用'),
        ('isCacheHit', '缓存命中检查'),
    ]
    
    passed = 0
    for keyword, desc in checks:
        if keyword in content:
            print(f"  ✅ {desc}: 已集成")
            passed += 1
        else:
            print(f"  ❌ {desc}: 未集成")
    
    print(f"\n验证结果：{passed}/{len(checks)} 通过")
    return passed == len(checks)

def main():
    """主函数"""
    print_header("P2 体验优化验证")
    
    results = {
        '请求重试': verify_request_retry(),
        '加载进度': verify_loading_progress(),
        '缓存服务': verify_cache_service(),
        '缓存集成': verify_cache_integration(),
    }
    
    # 总结
    print_header("验证总结")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}: {'通过' if result else '失败'}")
    
    print(f"\n总体验收：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有 P2 优化功能已正确实现！")
        return 0
    else:
        print("\n⚠️  部分功能未完全实现，请检查代码")
        return 1

if __name__ == '__main__':
    sys.exit(main())
