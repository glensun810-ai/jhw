#!/usr/bin/env python3
"""
测试API请求频率优化效果
"""

import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_python'))

from backend_python.wechat_backend.optimization.request_frequency_optimizer import (
    request_frequency_optimizer,
    get_platform_frequency_info,
    cleanup_frequency_records
)


def simulate_api_request(platform: str, request_id: int):
    """模拟API请求"""
    print(f"Request {request_id} to {platform} starting...")
    
    # 检查是否需要延迟
    delay_time = request_frequency_optimizer.should_delay_request(platform)
    
    if delay_time > 0:
        print(f"Request {request_id} to {platform} delayed for {delay_time:.2f}s")
        time.sleep(delay_time)
    
    # 模拟API调用（耗时100ms）
    time.sleep(0.1)
    
    print(f"Request {request_id} to {platform} completed")
    return f"Response_{request_id}"


def test_frequency_control():
    """测试频率控制效果"""
    print("="*60)
    print("API请求频率优化测试")
    print("="*60)
    
    # 清理旧记录
    cleanup_frequency_records()
    
    platform = "doubao"  # 使用豆包平台（有较严格的频率限制）
    
    print(f"\n测试平台: {platform}")
    print(f"平台最小间隔: {request_frequency_optimizer.platform_intervals[platform]}s")
    
    # 测试单个请求
    print("\n1. 测试单个请求...")
    start_time = time.time()
    simulate_api_request(platform, 1)
    single_duration = time.time() - start_time
    print(f"   单个请求耗时: {single_duration:.2f}s")
    
    # 测试连续请求
    print("\n2. 测试连续请求...")
    request_times = []
    for i in range(5):
        start_time = time.time()
        simulate_api_request(platform, i+2)
        req_time = time.time() - start_time
        request_times.append(req_time)
        print(f"   请求 {i+2} 耗时: {req_time:.2f}s")
        
        # 获取当前频率信息
        freq_info = get_platform_frequency_info(platform)
        print(f"   当前频率: {freq_info['frequency_per_minute']:.2f} 次/分钟")
    
    # 测试并发请求
    print("\n3. 测试并发请求...")
    concurrent_start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(6):
            future = executor.submit(simulate_api_request, platform, i+7)
            futures.append(future)
        
        # 等待所有请求完成
        results = [future.result() for future in futures]
    
    concurrent_duration = time.time() - concurrent_start
    print(f"   6个并发请求总耗时: {concurrent_duration:.2f}s")
    
    # 检查最终频率信息
    final_freq_info = get_platform_frequency_info(platform)
    print(f"\n4. 最终频率信息:")
    print(f"   平均频率: {final_freq_info['frequency_per_minute']:.2f} 次/分钟")
    print(f"   总请求数: {final_freq_info['total_recent_requests']}")
    if final_freq_info['last_request_time']:
        print(f"   最后请求时间: {time.ctime(final_freq_info['last_request_time'])}")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


def test_different_platforms():
    """测试不同平台的频率控制"""
    print("\n" + "="*60)
    print("不同平台频率控制测试")
    print("="*60)
    
    platforms = ["doubao", "qwen", "zhipu", "deepseek"]
    
    for platform in platforms:
        print(f"\n测试平台: {platform}")
        print(f"最小间隔: {request_frequency_optimizer.platform_intervals[platform]}s")
        
        # 连续发送3个请求
        for i in range(3):
            start_time = time.time()
            simulate_api_request(platform, i+1)
            req_time = time.time() - start_time
            print(f"  请求 {i+1} 耗时: {req_time:.2f}s")
        
        # 检查该平台的频率信息
        freq_info = get_platform_frequency_info(platform)
        print(f"  最终频率: {freq_info['frequency_per_minute']:.2f} 次/分钟")


if __name__ == "__main__":
    test_frequency_control()
    test_different_platforms()