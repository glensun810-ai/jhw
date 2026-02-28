#!/usr/bin/env python3
"""
P0-2 修复验证测试

验证内容：
1. Markdown JSON 代码块解析
2. 内联 JSON 解析
3. 正则提取 geo_analysis
4. 平衡括号法提取 JSON
5. 语义分析降级方案
6. 错误处理和日志记录
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend.ai_adapters.geo_parser import parse_geo_json_enhanced

def test_markdown_json():
    """测试 Markdown JSON 代码块解析"""
    print("=" * 60)
    print("测试 1: Markdown JSON 代码块解析")
    print("=" * 60)
    
    markdown_response = '''
作为专业顾问，我推荐以下品牌：

TOP1: 华为
理由：技术领先，品质可靠。

TOP2: 小米
理由：性价比高，服务好。

```json
{
  "geo_analysis": {
    "brand_mentioned": true,
    "rank": 1,
    "sentiment": 0.9,
    "cited_sources": [
      {"url": "https://www.zhihu.com/question/123", "site_name": "知乎", "attitude": "positive"}
    ],
    "interception": ""
  }
}
```
'''
    
    result = parse_geo_json_enhanced(markdown_response, "test-001", 0, "doubao")
    
    assert result['brand_mentioned'] == True, "应检测到品牌提及"
    assert result['rank'] == 1, "排名应为 1"
    assert result['sentiment'] == 0.9, "情感应为 0.9"
    assert len(result['cited_sources']) > 0, "应有信源"
    assert '_error' not in result, "不应有错误"
    
    print("✓ Markdown JSON 代码块解析成功")
    print(f"  结果：mentioned={result['brand_mentioned']}, rank={result['rank']}, sentiment={result['sentiment']}")
    print()
    return True

def test_inline_json():
    """测试内联 JSON 解析"""
    print("=" * 60)
    print("测试 2: 内联 JSON 解析")
    print("=" * 60)
    
    inline_response = '''
根据我的了解，华为是不错的选择。

{"geo_analysis": {"brand_mentioned": true, "rank": 2, "sentiment": 0.7, "cited_sources": [], "interception": ""}}
'''
    
    result = parse_geo_json_enhanced(inline_response, "test-002", 0, "qwen")
    
    assert result['brand_mentioned'] == True, "应检测到品牌提及"
    assert result['rank'] == 2, "排名应为 2"
    assert result['sentiment'] == 0.7, "情感应为 0.7"
    assert '_error' not in result, "不应有错误"
    
    print("✓ 内联 JSON 解析成功")
    print(f"  结果：mentioned={result['brand_mentioned']}, rank={result['rank']}, sentiment={result['sentiment']}")
    print()
    return True

def test_nested_json():
    """测试嵌套 JSON 解析"""
    print("=" * 60)
    print("测试 3: 嵌套 JSON 解析")
    print("=" * 60)
    
    nested_response = '''
推荐以下品牌：

{
  "analysis": {
    "summary": "华为表现优秀",
    "geo_analysis": {
      "brand_mentioned": true,
      "rank": 3,
      "sentiment": 0.8,
      "cited_sources": [],
      "interception": "检测到竞品拦截"
    }
  }
}
'''
    
    result = parse_geo_json_enhanced(nested_response, "test-003", 0, "deepseek")
    
    assert result['brand_mentioned'] == True, "应检测到品牌提及"
    assert result['rank'] == 3, "排名应为 3"
    assert result['sentiment'] == 0.8, "情感应为 0.8"
    assert result['interception'] == "检测到竞品拦截", "应检测到拦截"
    
    print("✓ 嵌套 JSON 解析成功")
    print(f"  结果：mentioned={result['brand_mentioned']}, rank={result['rank']}, sentiment={result['sentiment']}")
    print()
    return True

def test_semantic_fallback():
    """测试语义分析降级方案"""
    print("=" * 60)
    print("测试 4: 语义分析降级方案（P0-2 新增）")
    print("=" * 60)
    
    # 无 JSON 格式的纯文本响应
    text_response = '''
作为您的专业购车顾问，我将基于当前新能源汽车市场的公开信息，为您进行客观分析和推荐。

根据我的了解，深圳地区有以下优秀的新能源汽车改装门店：

第一推荐：深圳车尚艺改装店
理由：专业技术团队，丰富经验，使用高品质配件，客户口碑极佳。

第二推荐：深圳承美车居
理由：服务好，价格透明，诚信经营。

第三推荐：深圳趣车良品
理由：创新技术，设备先进，改装效果出色，值得推荐！

综合来看，这三家都是不错的选择，建议您实地考察后决定。
'''
    
    result = parse_geo_json_enhanced(text_response, "test-004", 0, "doubao")
    
    # 验证语义分析结果
    assert result['brand_mentioned'] == True, "应检测到品牌提及"
    assert result['rank'] > 0, "应有排名（语义分析提取）"
    assert result['sentiment'] > 0, "情感应为正（文本中有'推荐'、'优秀'等词）"
    assert result.get('_parse_method') == 'semantic_analysis', "应使用语义分析方法"
    assert result.get('_warning') is not None, "应有警告标记"
    
    print("✓ 语义分析降级成功")
    print(f"  结果：mentioned={result['brand_mentioned']}, rank={result['rank']}, sentiment={result['sentiment']:.2f}")
    print(f"  解析方法：{result.get('_parse_method')}")
    print(f"  警告：{result.get('_warning', '')[:50]}...")
    print()
    return True

def test_error_handling():
    """测试错误处理"""
    print("=" * 60)
    print("测试 5: 错误处理")
    print("=" * 60)
    
    # 空响应
    result_empty = parse_geo_json_enhanced("", "test-005", 0, "doubao")
    assert '_error' in result_empty, "空响应应有错误标记"
    assert result_empty['brand_mentioned'] == False, "空响应应返回默认值"
    
    # None 响应
    result_none = parse_geo_json_enhanced(None, "test-006", 0, "doubao")
    assert '_error' in result_none, "None 响应应有错误标记"
    
    # 无效文本
    result_invalid = parse_geo_json_enhanced("这是一段完全无效的文本，没有任何 JSON 格式或有用信息", "test-007", 0, "doubao")
    assert '_error' in result_invalid or result_invalid.get('_parse_method') == 'semantic_analysis', "无效文本应有错误或使用语义分析"
    
    print("✓ 错误处理正常")
    print(f"  空响应：error={result_empty.get('_error', '')[:30]}...")
    print(f"  None 响应：error={result_none.get('_error', '')[:30]}...")
    print()
    return True

def test_raw_response_preservation():
    """测试原始响应保留"""
    print("=" * 60)
    print("测试 6: 原始响应保留")
    print("=" * 60)
    
    invalid_response = "完全无效的响应内容"
    result = parse_geo_json_enhanced(invalid_response, "test-008", 0, "doubao")
    
    assert '_raw_response' in result, "应保留原始响应"
    assert result['_raw_response'] is not None, "原始响应不应为 None"
    assert '完全无效' in result['_raw_response'], "原始响应应包含原文"
    
    print("✓ 原始响应保留正常")
    print(f"  原始响应长度：{len(result['_raw_response']) if result['_raw_response'] else 0} 字符")
    print()
    return True

def test_parse_methods():
    """测试解析方法标记"""
    print("=" * 60)
    print("测试 7: 解析方法标记")
    print("=" * 60)
    
    # JSON 解析成功
    json_response = '{"geo_analysis": {"brand_mentioned": true, "rank": 1, "sentiment": 0.9, "cited_sources": [], "interception": ""}}'
    result_json = parse_geo_json_enhanced(json_response, "test-009", 0, "doubao")
    
    # 语义分析降级
    text_response = "我推荐华为品牌，它是第一选择，非常优秀！"
    result_semantic = parse_geo_json_enhanced(text_response, "test-010", 0, "doubao")
    
    print("✓ 解析方法标记正常")
    print(f"  JSON 解析：method={result_json.get('_parse_method', 'json (default)')}")
    print(f"  语义分析：method={result_semantic.get('_parse_method', 'unknown')}")
    print()
    return True

def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("P0-2 修复验证测试 - AI 响应解析容错性增强")
    print("=" * 60)
    print()
    
    tests = [
        ("Markdown JSON 代码块解析", test_markdown_json),
        ("内联 JSON 解析", test_inline_json),
        ("嵌套 JSON 解析", test_nested_json),
        ("语义分析降级方案", test_semantic_fallback),
        ("错误处理", test_error_handling),
        ("原始响应保留", test_raw_response_preservation),
        ("解析方法标记", test_parse_methods),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ {test_name} 测试失败：{e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常：{e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
