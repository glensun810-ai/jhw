#!/usr/bin/env python3
"""
调试rank_analyzer.py中的问题
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼的智能锁很好，小米也不错，凯迪仕也有一定市场。"
brand_list = ["德施曼", "小米", "凯迪仕"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 测试查找单个品牌位置
for brand in brand_list:
    pos = analyzer._find_brand_position(ai_response, brand)
    print(f"品牌 '{brand}' 的位置: {pos}")

# 测试提取排名列表
ranking_list = analyzer._extract_ranking_list(ai_response, brand_list)
print("排名列表:", ranking_list)

# 测试完整分析
result = analyzer.analyze(ai_response, brand_list)
print("完整分析结果:", result)