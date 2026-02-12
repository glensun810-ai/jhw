#!/usr/bin/env python3
"""
调试大小写匹配问题
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试大小写匹配
ai_response = "Apple手机很好，APPLE商店服务也不错。"
brand_list = ["Apple"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 测试完整分析
result = analyzer.analyze(ai_response, brand_list)
print("完整分析结果:", result)

# 测试查找单个品牌位置
for brand in brand_list:
    pos = analyzer._find_brand_position(ai_response, brand)
    print(f"品牌 '{brand}' 的位置: {pos}")
    
    # 手动查找所有可能的匹配
    import re
    matches = [(m.start(), m.end()) for m in re.finditer(re.escape(brand), ai_response, re.IGNORECASE)]
    print(f"所有 '{brand}' 的匹配位置: {matches}")