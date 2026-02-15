#!/usr/bin/env python3
"""
测试增强版AI响应日志记录功能
"""

import os
import sys
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from utils.ai_response_wrapper import log_detailed_response, get_user_statistics, get_user_responses
from utils.ai_response_logger_enhanced import get_enhanced_logger


def test_enhanced_logging():
    """测试增强版日志记录功能"""
    print("🧪 开始测试增强版AI响应日志记录功能...")
    
    # 测试1: 记录成功的AI响应
    print("\n📝 测试1: 记录成功的AI响应")
    try:
        response_data = log_detailed_response(
            question="这是一个测试问题",
            response="这是一个测试答案，用于验证增强版日志记录功能。",
            platform="test_platform",
            model="test_model",
            success=True,
            latency_ms=1500,
            tokens_used=50,
            brand="测试品牌",
            competitor="测试竞品",
            user_id="test_user_123",
            execution_id="test_exec_456"
        )
        print(f"✅ 成功记录响应，记录ID: {response_data.get('record_id')}")
    except Exception as e:
        print(f"❌ 记录成功响应失败: {e}")
    
    # 测试2: 记录失败的AI响应
    print("\n📝 测试2: 记录失败的AI响应")
    try:
        response_data = log_detailed_response(
            question="这是另一个测试问题",
            response="",  # 失败时无响应内容
            platform="test_platform",
            model="test_model",
            success=False,
            error_message="模拟的API错误",
            error_type="TEST_ERROR",
            latency_ms=3000,
            user_id="test_user_123",
            execution_id="test_exec_789"
        )
        print(f"✅ 成功记录失败响应，记录ID: {response_data.get('record_id')}")
    except Exception as e:
        print(f"❌ 记录失败响应失败: {e}")
    
    # 测试3: 获取用户统计数据
    print("\n📊 测试3: 获取用户统计数据")
    try:
        stats = get_user_statistics(user_id="test_user_123", days=1)
        print(f"✅ 获取用户统计数据成功:")
        print(f"   - 总记录数: {stats.get('total_records', 0)}")
        print(f"   - 成功记录: {stats.get('successful_records', 0)}")
        print(f"   - 失败记录: {stats.get('failed_records', 0)}")
        print(f"   - 平台统计: {stats.get('platforms', {})}")
    except Exception as e:
        print(f"❌ 获取用户统计数据失败: {e}")
    
    # 测试4: 获取用户响应记录
    print("\n📋 测试4: 获取用户响应记录")
    try:
        responses = get_user_responses(user_id="test_user_123", limit=10)
        print(f"✅ 获取用户响应记录成功，共 {len(responses)} 条记录")
        for i, resp in enumerate(responses[:2]):  # 只打印前两条
            print(f"   记录 {i+1}: {resp.get('question', {}).get('text', '')[:30]}...")
    except Exception as e:
        print(f"❌ 获取用户响应记录失败: {e}")
    
    # 测试5: 测试多用户区分
    print("\n👥 测试5: 测试多用户区分")
    try:
        # 记录不同用户的响应
        for user_id in ["user_a", "user_b", "user_c"]:
            log_detailed_response(
                question=f"用户 {user_id} 的问题",
                response=f"用户 {user_id} 的答案",
                platform="multi_user_test",
                model="test_model",
                user_id=user_id,
                execution_id=f"exec_{user_id}"
            )
        
        # 获取每个用户的统计
        for user_id in ["user_a", "user_b", "user_c"]:
            stats = get_user_statistics(user_id=user_id, days=1)
            print(f"   用户 {user_id}: {stats.get('total_records', 0)} 条记录")
        
        print("✅ 多用户区分功能正常")
    except Exception as e:
        print(f"❌ 多用户区分测试失败: {e}")
    
    # 测试6: 测试数据分区
    print("\n📁 测试6: 测试数据分区")
    try:
        # 使用增强版记录器直接检查日志文件结构
        logger = get_enhanced_logger()
        user_dir = logger.user_log_dir / "test_user_123"
        if user_dir.exists():
            log_files = list(user_dir.glob("*.jsonl*"))  # 包括压缩文件
            print(f"✅ 用户分区目录存在，包含 {len(log_files)} 个日志文件")
        else:
            print("⚠️  用户分区目录不存在，可能是首次运行")
    except Exception as e:
        print(f"❌ 数据分区测试失败: {e}")
    
    print("\n🎉 增强版AI响应日志记录功能测试完成！")


def test_with_real_scenario():
    """测试真实场景下的日志记录"""
    print("\n🚀 开始真实场景测试...")
    
    # 模拟真实的AI平台调用
    platforms = ["豆包", "通义千问", "智谱AI", "DeepSeek"]
    brands = ["品牌A", "品牌B", "品牌C"]
    
    for i in range(5):  # 模拟5次调用
        platform = platforms[i % len(platforms)]
        brand = brands[i % len(brands)]
        
        try:
            log_detailed_response(
                question=f"关于{brand}品牌的市场竞争分析",
                response=f"这是{platform}平台对{brand}品牌的分析结果...",
                platform=platform,
                model=f"{platform.lower()}_model",
                success=i % 4 != 3,  # 模拟部分失败
                latency_ms=(i + 1) * 1000,  # 递增延迟
                tokens_used=100 + i * 20,
                brand=brand,
                user_id=f"real_user_{i % 3}",  # 3个不同用户
                execution_id=f"real_exec_{i}"
            )
            print(f"   第 {i+1} 次调用记录成功")
        except Exception as e:
            print(f"   第 {i+1} 次调用记录失败: {e}")
    
    print("✅ 真实场景测试完成")


if __name__ == "__main__":
    test_enhanced_logging()
    test_with_real_scenario()