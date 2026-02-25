#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
容错机制测试脚本

测试场景：
1. 部分 AI 平台配额用尽（429 错误）
2. 部分 AI 平台调用失败（500 错误）
3. AI 响应解析失败
4. 序列化失败
5. 执行超时

预期结果：
- 任何错误都不影响结果产出
- 失败的平台在结果中标注错误
- 成功的平台正常显示结果
- 用户看到明确的错误提示和建议
"""

import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '.')

from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor, safe_json_serialize


class MockAIResponse:
    """模拟 AI 响应对象（用于测试序列化）"""
    def __init__(self, content: str, success: bool = True):
        self.content = content
        self.success = success
        self._private = "should not be serialized"
    
    def to_dict(self):
        return {
            'content': self.content,
            'success': self.success,
            'has_to_dict': True
        }


class MockAIResponseNoToDict:
    """模拟没有 to_dict 方法的 AI 响应对象"""
    def __init__(self, content: str):
        self.content = content
        self.latency = 1.5
        self.tokens = 100


def test_fault_tolerant_executor():
    """测试容错执行器"""
    print("="*60)
    print("测试 1: 容错执行器基础功能")
    print("="*60)
    
    executor = FaultTolerantExecutor("test-execution-001")
    
    # 测试 1: 成功结果收集
    print("\n1.1 成功结果收集")
    result1 = executor.collect_result(
        brand="品牌 A",
        question="问题 1",
        model="doubao",
        response=MockAIResponse("这是 AI 回答"),
        geo_data={"brand_mentioned": True, "rank": 1, "sentiment": 0.8},
        error=None
    )
    print(f"✅ 成功结果：{result1['status']}")
    assert result1['status'] == 'success'
    
    # 测试 2: 失败结果收集（带错误）
    print("\n1.2 失败结果收集")
    result2 = executor.collect_result(
        brand="品牌 A",
        question="问题 2",
        model="doubao",
        response=None,
        geo_data=None,
        error="AI 调用失败：429 配额用尽"
    )
    print(f"✅ 失败结果：{result2['status']}, 错误：{result2['error']}")
    assert result2['status'] == 'failed'
    assert 'geo_data' in result2
    assert result2['geo_data']['_error']
    
    # 测试 3: AIResponse 对象序列化（有 to_dict）
    print("\n1.3 AIResponse 序列化（有 to_dict）")
    result3 = executor.collect_result(
        brand="品牌 A",
        question="问题 3",
        model="qwen",
        response=MockAIResponse("通义千问回答"),
        geo_data={"brand_mentioned": False, "rank": -1},
        error=None
    )
    print(f"✅ 响应序列化：{result3['response']}")
    assert result3['response']['has_to_dict'] == True
    
    # 测试 4: AIResponse 对象序列化（无 to_dict）
    print("\n1.4 AIResponse 序列化（无 to_dict）")
    result4 = executor.collect_result(
        brand="品牌 A",
        question="问题 4",
        model="zhipu",
        response=MockAIResponseNoToDict("智谱回答"),
        geo_data={"brand_mentioned": True, "rank": 2},
        error=None
    )
    print(f"✅ 响应序列化：{result4['response']}")
    assert 'content' in result4['response']
    
    # 测试 5: 生成最终报告
    print("\n1.5 生成最终报告")
    report = executor.get_final_report()
    print(f"✅ 报告生成：{report['status']}")
    print(f"   总结果数：{report['results_count']}")
    print(f"   成功数：{report['success_count']}")
    print(f"   失败数：{report['failed_count']}")
    print(f"   警告数：{len(report['warnings'])}")
    
    # 验证报告可序列化
    json_str = json.dumps(report, ensure_ascii=False)
    print(f"✅ 报告 JSON 序列化成功，长度：{len(json_str)}")
    
    print("\n✅ 测试 1 通过：容错执行器基础功能正常")


def test_safe_json_serialize():
    """测试安全 JSON 序列化"""
    print("\n" + "="*60)
    print("测试 2: 安全 JSON 序列化")
    print("="*60)
    
    # 测试 1: 普通对象
    print("\n2.1 普通字典")
    data1 = {'key': 'value', 'num': 123}
    result1 = safe_json_serialize(data1)
    assert result1 == data1
    print(f"✅ 普通字典序列化成功")
    
    # 测试 2: 包含 AIResponse 对象
    print("\n2.2 包含 AIResponse 对象")
    data2 = {
        'response': MockAIResponse("测试内容"),
        'geo_data': {'rank': 1}
    }
    result2 = safe_json_serialize(data2)
    print(f"✅ AIResponse 序列化成功：{result2['response']}")
    assert result2['response']['has_to_dict'] == True
    
    # 测试 3: 包含不可序列化对象
    print("\n2.3 包含不可序列化对象")
    class UnserializableClass:
        def __init__(self):
            self.value = 42
    
    data3 = {
        'normal': 'data',
        'unserializable': UnserializableClass()
    }
    result3 = safe_json_serialize(data3)
    print(f"✅ 不可序列化对象处理成功：{result3['unserializable']}")
    
    print("\n✅ 测试 2 通过：安全 JSON 序列化正常")


def test_partial_failure_scenario():
    """测试部分失败场景"""
    print("\n" + "="*60)
    print("测试 3: 部分失败场景（模拟真实诊断）")
    print("="*60)
    
    executor = FaultTolerantExecutor("test-partial-failure")
    
    # 模拟 3 个 AI 平台，2 个成功，1 个失败
    platforms = [
        ('doubao', True, None),
        ('qwen', True, None),
        ('zhipu', False, '429 配额用尽')
    ]
    
    for model, success, error in platforms:
        if success:
            result = executor.collect_result(
                brand="测试品牌",
                question="测试问题",
                model=model,
                response=MockAIResponse(f"{model}的回答"),
                geo_data={"brand_mentioned": True, "rank": 1},
                error=None
            )
            print(f"✅ {model}: 成功")
        else:
            result = executor.collect_result(
                brand="测试品牌",
                question="测试问题",
                model=model,
                response=None,
                geo_data=None,
                error=error
            )
            print(f"❌ {model}: 失败 - {error}")
    
    # 生成报告
    report = executor.get_final_report()
    
    print(f"\n📊 报告统计:")
    print(f"   总结果数：{report['results_count']}")
    print(f"   成功数：{report['success_count']}")
    print(f"   失败数：{report['failed_count']}")
    print(f"   警告：{report['warnings']}")
    
    # 验证
    assert report['results_count'] == 3
    assert report['success_count'] == 2
    assert report['failed_count'] == 1
    assert any('配额' in w for w in report['warnings'])
    
    # 验证可序列化
    json_str = json.dumps(report, ensure_ascii=False)
    print(f"\n✅ 报告 JSON 序列化成功，长度：{len(json_str)}")
    
    print("\n✅ 测试 3 通过：部分失败场景正常")


def test_all_failure_scenario():
    """测试全部失败场景"""
    print("\n" + "="*60)
    print("测试 4: 全部失败场景（极端情况）")
    print("="*60)
    
    executor = FaultTolerantExecutor("test-all-failure")
    
    # 模拟所有平台都失败
    platforms = [
        ('doubao', '429 配额用尽'),
        ('qwen', '500 服务器错误'),
        ('zhipu', '超时')
    ]
    
    for model, error in platforms:
        result = executor.collect_result(
            brand="测试品牌",
            question="测试问题",
            model=model,
            response=None,
            geo_data=None,
            error=error
        )
        print(f"❌ {model}: 失败 - {error}")
    
    # 生成报告（即使全部失败也要生成）
    report = executor.get_final_report()
    
    print(f"\n📊 报告统计:")
    print(f"   总结果数：{report['results_count']}")
    print(f"   状态：{report['status']}")
    print(f"   警告：{report['warnings']}")
    
    # 验证即使全部失败也有报告
    assert report['results_count'] == 3
    assert report['status'] == 'completed_with_errors'
    assert len(report['errors']) > 0
    
    # 验证可序列化
    json_str = json.dumps(report, ensure_ascii=False)
    print(f"\n✅ 报告 JSON 序列化成功，长度：{len(json_str)}")
    
    print("\n✅ 测试 4 通过：全部失败场景仍能生成报告")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🧪 品牌诊断系统容错机制测试")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        test_fault_tolerant_executor()
        test_safe_json_serialize()
        test_partial_failure_scenario()
        test_all_failure_scenario()
        
        print("\n" + "="*70)
        print("✅ 所有测试通过！")
        print("="*70)
        print("\n容错机制验证完成:")
        print("1. ✅ 成功结果正常收集")
        print("2. ✅ 失败结果正确标注")
        print("3. ✅ AIResponse 对象正确序列化")
        print("4. ✅ 部分失败场景生成部分结果")
        print("5. ✅ 全部失败场景仍生成报告")
        print("6. ✅ 所有报告可 JSON 序列化")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
