#!/usr/bin/env python3
"""
详细调试排名列表提取
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼的智能锁很好，功能强大。小米性价比高。凯迪仕也不错。鹿客用户体验更好。"
brand_list = ["德施曼", "小米", "凯迪仕"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 测试每个品牌的匹配情况
for brand in brand_list:
    pos = analyzer._find_brand_position(ai_response, brand)
    print(f"'{brand}' 的位置: {pos}")
    
    # 检查所有可能的位置
    all_positions = analyzer._find_all_brand_positions(ai_response, brand)
    print(f"'{brand}' 的所有位置: {all_positions}")
    
    # 检查边界有效性
    for pos_single in all_positions:
        is_valid = analyzer._is_valid_brand_boundary(ai_response, pos_single, pos_single + len(brand))
        print(f"  位置 {pos_single} 的边界有效性: {is_valid}")

# 测试提取排名列表
ranking_list = analyzer._extract_ranking_list(ai_response, brand_list)
print("排名列表:", ranking_list)

# 测试未列出竞争对手
unlisted = analyzer._identify_unlisted_competitors(ai_response, brand_list)
print("未列出竞争对手:", unlisted)