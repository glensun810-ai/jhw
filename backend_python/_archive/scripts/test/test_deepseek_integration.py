#!/usr/bin/env python3
"""
DeepSeek适配器集成测试
验证DeepSeekAdapter能正常调用API
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType


def test_deepseek_basic():
    """测试DeepSeek基础调用"""
    print("=" * 60)
    print("DeepSeek适配器基础测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        print(f"\n1. 创建适配器...")
        print(f"   API Key: {api_key[:20]}...")
        print(f"   Model: {model_name}")
        
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        print("   ✅ 适配器创建成功")
        
        print(f"\n2. 测试简单prompt...")
        test_prompt = "请用一句话介绍DeepSeek"
        print(f"   Prompt: {test_prompt}")
        
        start_time = time.time()
        response = adapter.send_prompt(test_prompt, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"   响应时间: {elapsed:.2f}秒")
        print(f"   成功状态: {response.success}")
        
        if response.success:
            print(f"   ✅ API调用成功")
            print(f"   内容预览: {response.content[:100]}...")
            print(f"   Token使用: {response.tokens_used}")
            print(f"   模型: {response.model}")
            return True
        else:
            print(f"   ❌ API调用失败")
            print(f"   错误: {response.error_message}")
            print(f"   错误类型: {response.error_type}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deepseek_brand_question():
    """测试品牌问题（模拟真实场景）"""
    print("\n" + "=" * 60)
    print("DeepSeek品牌问题测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        
        # 模拟真实品牌问题
        test_questions = [
            "元若曦养生茶怎么样？",
            "养生堂品牌介绍",
            "固生堂靠谱吗？"
        ]
        
        results = []
        for i, question in enumerate(test_questions, 1):
            print(f"\n   问题{i}: {question}")
            start_time = time.time()
            response = adapter.send_prompt(question, timeout=30)
            elapsed = time.time() - start_time
            
            results.append({
                'question': question,
                'success': response.success,
                'latency': elapsed,
                'content_length': len(response.content) if response.content else 0
            })
            
            if response.success:
                print(f"   ✅ 成功 ({elapsed:.2f}s, {len(response.content)}字符)")
            else:
                print(f"   ❌ 失败: {response.error_message}")
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        avg_latency = sum(r['latency'] for r in results) / len(results)
        
        print(f"\n   统计: {success_count}/{len(results)} 成功")
        print(f"   平均响应时间: {avg_latency:.2f}秒")
        
        return success_count == len(results)
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deepseek_performance():
    """测试DeepSeek性能（连续调用）"""
    print("\n" + "=" * 60)
    print("DeepSeek性能测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        
        latencies = []
        test_prompt = "你好"
        
        print(f"\n   连续调用10次...")
        for i in range(10):
            start_time = time.time()
            response = adapter.send_prompt(test_prompt, timeout=30)
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            
            status = "✅" if response.success else "❌"
            print(f"   {status} 调用{i+1}: {elapsed:.2f}s")
            
            if not response.success:
                print(f"      错误: {response.error_message}")
        
        # 计算统计值
        latencies.sort()
        p50 = latencies[len(latencies)//2]
        p95 = latencies[int(len(latencies)*0.95)]
        avg = sum(latencies) / len(latencies)
        
        print(f"\n   性能统计:")
        print(f"   - 平均响应时间: {avg:.2f}秒")
        print(f"   - P50响应时间: {p50:.2f}秒")
        print(f"   - P95响应时间: {p95:.2f}秒")
        print(f"   - 最小响应时间: {min(latencies):.2f}秒")
        print(f"   - 最大响应时间: {max(latencies):.2f}秒")
        
        # 建议超时时间
        suggested_timeout = int(p95 * 1.5)
        print(f"\n   建议超时时间: {suggested_timeout}秒")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("DeepSeek平台集成测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API密钥: sk-13908093890f46fb82c52a01c8dfc464")
    print(f"模型: deepseek-chat")
    
    results = []
    
    # 运行测试
    results.append(("基础调用", test_deepseek_basic()))
    results.append(("品牌问题", test_deepseek_brand_question()))
    results.append(("性能测试", test_deepseek_performance()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！DeepSeek平台已调通。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述详情。")
        return 1


if __name__ == "__main__":
    exit(main())
