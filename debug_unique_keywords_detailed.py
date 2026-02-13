#!/usr/bin/env python3
"""
调试独有关键词识别问题
"""
from wechat_backend.analytics.competitive_analyzer import CompetitiveAnalyzer
import jieba

# 创建分析器实例
analyzer = CompetitiveAnalyzer()

# 测试文本 - 与测试用例完全一致
my_text = "德施曼的智能锁技术先进，工艺精湛。"
competitor_text = "小米的智能锁性价比高，生态丰富。"
brand_list = ["德施曼", "小米"]

print("我方文本:", my_text)
print("竞品文本:", competitor_text)
print("品牌列表:", brand_list)

# 分别提取关键词
my_keywords = analyzer._extract_keywords(my_text, "德施曼")
comp_keywords = analyzer._extract_keywords(competitor_text, "小米")

print("我方文本提取的关键词:", my_keywords)
print("竞品文本提取的关键词:", comp_keywords)

# 执行完整分析
result = analyzer.analyze(my_text, competitor_text, "德施曼", "小米")

print("\n完整分析结果:")
print("- 共同关键词:", result['common_keywords'])
print("- 我方独有关键词:", result['my_brand_unique_keywords'])
print("- 竞品独有关键词:", result['competitor_unique_keywords'])

# 检查是否包含"技术"
if "技术" in my_keywords:
    print("'技术'在德施曼文本的关键词中")
else:
    print("'技术'不在德施曼文本的关键词中")

# 检查分词结果
print("\n德施曼文本的分词结果:", jieba.lcut(my_text))
print("小米文本的分词结果:", jieba.lcut(competitor_text))