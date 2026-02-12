#!/usr/bin/env python3
"""
测试新的边界检查函数
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
text = "Apple手机很好，APPLE商店服务也不错。"
brand = "Apple"

print("测试文本:", repr(text))
print("品牌:", repr(brand))

# 测试边界检查函数
print("\n测试边界检查函数:")
print(f"_is_valid_brand_boundary(text, 0, 5): {analyzer._is_valid_brand_boundary(text, 0, 5)}")  # Apple
print(f"_is_valid_brand_boundary(text, 10, 15): {analyzer._is_valid_brand_boundary(text, 10, 15)}")  # APPLE

# 手动测试查找
print("\n手动测试查找:")
pos = 0
text_lower = text.lower()
brand_lower = brand.lower()
while pos < len(text_lower):
    pos = text_lower.find(brand_lower, pos)
    if pos == -1:
        break
    print(f"找到 '{brand_lower}' 在位置 {pos}")
    
    boundary_ok = analyzer._is_valid_brand_boundary(text, pos, pos + len(brand_lower))
    print(f"  边界检查: {boundary_ok}")
    
    pos += 1

# 测试查找品牌位置
print(f"\n测试查找品牌位置:")
position = analyzer._find_brand_position(text, brand)
print(f"品牌 '{brand}' 的位置: {position}")

# 测试完整分析
print(f"\n测试完整分析:")
result = analyzer.analyze(text, [brand])
print(f"分析结果: {result}")