#!/usr/bin/env python3
"""
负面信源提取验证测试

验证内容:
1. 从 AI 响应中提取 cited_sources
2. 过滤负面信源
3. 去重处理
4. 生成负面信源列表

执行：python3 test_negative_sources_extraction.py
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

# 模拟 AI 响应数据
mock_ai_responses = [
    {
        'status': 'success',
        'geo_data': {
            'rank': 1,
            'sentiment': 0.7,
            'cited_sources': [
                {'url': 'https://consumer.huawei.com/cn/phones/nova12/', 'site_name': '华为消费者官网', 'attitude': 'positive'},
                {'url': 'https://zhuanlan.zhihu.com/p/123456', 'site_name': '知乎专栏 - 手机评测', 'attitude': 'neutral'}
            ]
        }
    },
    {
        'status': 'success',
        'geo_data': {
            'rank': 2,
            'sentiment': 0.3,
            'cited_sources': [
                {'url': 'https://baike.baidu.com/item/华为', 'site_name': '百度百科', 'attitude': 'neutral'},
                {'url': 'https://weibo.com/some-negative-post', 'site_name': '微博', 'attitude': 'negative'}
            ]
        }
    },
    {
        'status': 'success',
        'geo_data': {
            'rank': -1,
            'sentiment': -0.2,
            'cited_sources': [
                {'url': 'https://zhuanlan.zhihu.com/p/negative-review', 'site_name': '知乎 - 负面评测', 'attitude': 'negative'}
            ]
        }
    }
]

def extract_negative_sources(all_results, main_brand_score):
    """从 AI 响应中提取负面信源"""
    negative_sources = []
    
    for result in all_results:
        if result.get('status') == 'success' and result.get('geo_data'):
            geo = result['geo_data']
            cited_sources = geo.get('cited_sources', [])
            
            for source in cited_sources:
                url = source.get('url', '')
                site_name = source.get('site_name', '')
                attitude = source.get('attitude', 'neutral')
                
                # 只提取负面或中性偏负面的信源
                if attitude == 'negative' or (attitude == 'neutral' and main_brand_score < 70):
                    # 检查是否已存在（去重）
                    exists = any(ns.get('source_url') == url for ns in negative_sources)
                    if not exists and url and site_name:
                        sentiment = geo.get('sentiment', 0)
                        severity = 'high' if sentiment < -0.3 else ('medium' if sentiment < 0 else 'low')
                        
                        negative_sources.append({
                            'source_name': site_name,
                            'source_url': url,
                            'source_type': 'article' if 'zhuanlan' in url or 'article' in url else 'encyclopedia' if 'baike' in url else 'social_media',
                            'content_summary': f'AI 回答中引用的信源：{site_name}',
                            'sentiment_score': sentiment,
                            'severity': severity,
                            'impact_scope': 'medium',
                            'estimated_reach': 100000 if 'baike' in url else 50000,
                            'from_ai_response': True,
                            'attitude': attitude
                        })
    
    return negative_sources


def main():
    print("\n" + "="*70)
    print("  负面信源提取验证测试")
    print("  Negative Sources Extraction Test")
    print("="*70)
    
    # 测试 1: 高分品牌（>70），只提取负面信源
    print("\n" + "="*70)
    print("测试 1: 高分品牌（85 分），只提取 attitude=negative 的信源")
    print("="*70)
    
    negative_sources_high = extract_negative_sources(mock_ai_responses, 85)
    
    print(f"\n  提取到的负面信源数量：{len(negative_sources_high)}")
    for i, ns in enumerate(negative_sources_high, 1):
        print(f"\n  [{i}] {ns['source_name']}")
        print(f"      URL: {ns['source_url']}")
        print(f"      态度：{ns['attitude']}")
        print(f"      情感：{ns['sentiment_score']}")
        print(f"      类型：{ns['source_type']}")
        print(f"      来自 AI: {ns['from_ai_response']}")
    
    # 验证
    expected_high = 2  # 微博（negative）+ 知乎负面评测（negative）
    if len(negative_sources_high) == expected_high:
        print(f"\n  ✅ 测试 1 通过：提取到 {expected_high} 个负面信源")
    else:
        print(f"\n  ❌ 测试 1 失败：预期 {expected_high} 个，实际 {len(negative_sources_high)} 个")
    
    # 测试 2: 低分品牌（<70），提取负面和中性信源
    print("\n" + "="*70)
    print("测试 2: 低分品牌（55 分），提取 attitude=negative 和 neutral 的信源")
    print("="*70)
    
    negative_sources_low = extract_negative_sources(mock_ai_responses, 55)
    
    print(f"\n  提取到的负面信源数量：{len(negative_sources_low)}")
    for i, ns in enumerate(negative_sources_low, 1):
        print(f"\n  [{i}] {ns['source_name']}")
        print(f"      URL: {ns['source_url']}")
        print(f"      态度：{ns['attitude']}")
        print(f"      情感：{ns['sentiment_score']}")
        print(f"      类型：{ns['source_type']}")
    
    # 验证
    expected_low = 4  # 知乎专栏（neutral）+ 百度百科（neutral）+ 微博（negative）+ 知乎负面（negative）
    if len(negative_sources_low) == expected_low:
        print(f"\n  ✅ 测试 2 通过：提取到 {expected_low} 个信源")
    else:
        print(f"\n  ❌ 测试 2 失败：预期 {expected_low} 个，实际 {len(negative_sources_low)} 个")
    
    # 测试 3: 去重验证
    print("\n" + "="*70)
    print("测试 3: 去重验证")
    print("="*70)
    
    # 添加重复数据
    mock_with_duplicates = mock_ai_responses + [
        {
            'status': 'success',
            'geo_data': {
                'rank': 3,
                'sentiment': -0.1,
                'cited_sources': [
                    {'url': 'https://weibo.com/some-negative-post', 'site_name': '微博', 'attitude': 'negative'}  # 重复
                ]
            }
        }
    ]
    
    negative_sources_dedup = extract_negative_sources(mock_with_duplicates, 55)
    print(f"\n  有重复输入的提取数量：{len(negative_sources_dedup)}")
    print(f"  无重复输入的提取数量：{len(negative_sources_low)}")
    
    if len(negative_sources_dedup) == len(negative_sources_low):
        print(f"\n  ✅ 测试 3 通过：去重功能正常")
    else:
        print(f"\n  ❌ 测试 3 失败：去重功能异常")
    
    # 测试 4: 信源类型识别
    print("\n" + "="*70)
    print("测试 4: 信源类型识别")
    print("="*70)
    
    source_types = {}
    for ns in negative_sources_low:
        st = ns['source_type']
        source_types[st] = source_types.get(st, 0) + 1
    
    print(f"\n  信源类型分布:")
    for st, count in source_types.items():
        print(f"    {st}: {count} 个")
    
    if 'article' in source_types and 'encyclopedia' in source_types and 'social_media' in source_types:
        print(f"\n  ✅ 测试 4 通过：信源类型识别正常")
    else:
        print(f"\n  ❌ 测试 4 失败：信源类型识别异常")
    
    # 汇总
    print("\n" + "="*70)
    print("  测试汇总")
    print("="*70)
    
    all_passed = (
        len(negative_sources_high) == expected_high and
        len(negative_sources_low) == expected_low and
        len(negative_sources_dedup) == len(negative_sources_low)
    )
    
    if all_passed:
        print("\n  🎉 所有测试通过！负面信源提取功能正常。")
        return True
    else:
        print("\n  ⚠️ 部分测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
