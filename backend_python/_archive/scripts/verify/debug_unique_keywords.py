#!/usr/bin/env python3
"""
调试独有关键词识别问题
"""
from wechat_backend.analytics.competitive_analyzer import CompetitiveAnalyzer
import jieba

# 创建分析器实例
analyzer = CompetitiveAnalyzer()

# 测试文本
ai_response = "德施曼的技术先进，工艺精湛。小米的性价比高。"
brand_list = ["德施曼", "小米"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 分词测试
words = jieba.lcut(ai_response)
print("分词结果:", words)

# 检查提取的关键词
keywords = analyzer._extract_keywords(ai_response, "德施曼")
print("为'德施曼'提取的关键词:", keywords)

keywords2 = analyzer._extract_keywords(ai_response, "小米")
print("为'小米'提取的关键词:", keywords2)

# 执行完整分析
result = analyzer.analyze(ai_response, ai_response, "德施曼", "小米")
print("完整分析结果:")
print("- 共同关键词:", result['common_keywords'])
print("- 我方独有关键词:", result['my_brand_unique_keywords'])
print("- 竞品独有关键词:", result['competitor_unique_keywords'])
print("- 差异总结:", result['differentiation_gap'])