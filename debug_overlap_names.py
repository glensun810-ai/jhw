#!/usr/bin/env python3
"""
调试重叠名称匹配问题
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试重叠名称
ai_response = "小明科技的产品很不错，明明是个好孩子。"
brand_list = ["小明", "明明"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 检查每个品牌的匹配情况
for brand in brand_list:
    pos = analyzer._find_brand_position(ai_response, brand)
    print(f"品牌 '{brand}' 的位置: {pos}")
    
    # 查找所有可能的匹配
    all_positions = []
    text_lower = ai_response.lower()
    brand_lower = brand.lower()
    pos = 0
    while pos < len(text_lower):
        pos = text_lower.find(brand_lower, pos)
        if pos == -1:
            break
        if analyzer._is_valid_brand_boundary(ai_response, pos, pos + len(brand_lower)):
            all_positions.append(pos)
        pos += 1
    print(f"品牌 '{brand}' 的所有有效位置: {all_positions}")

# 测试提取排名列表
ranking_list = analyzer._extract_ranking_list(ai_response, brand_list)
print("排名列表:", ranking_list)