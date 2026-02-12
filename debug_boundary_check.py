#!/usr/bin/env python3
"""
详细调试边界字符检查
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试大小写匹配
ai_response = "Apple手机很好，APPLE商店服务也不错。"
brand = "Apple"

print("测试文本:", repr(ai_response))
print("品牌:", repr(brand))

# 检查位置0 (Apple)
pos = 0
print(f"\n检查位置 {pos} (Apple):")
print(f"  品牌: {repr(ai_response[pos:pos+len(brand)])}")
if pos > 0:
    print(f"  前一个字符: {repr(ai_response[pos-1])}")
    print(f"  前一个字符是否为边界: {analyzer._is_boundary_char(ai_response, pos, True)}")
else:
    print(f"  位置为0 (文本开头)")
    print(f"  位置为边界: {analyzer._is_boundary_char(ai_response, pos, True)}")

if pos + len(brand) < len(ai_response):
    print(f"  后一个字符: {repr(ai_response[pos+len(brand)])}")
    print(f"  后一个字符是否为边界: {analyzer._is_boundary_char(ai_response, pos+len(brand), False)}")
else:
    print(f"  位置为文本结尾")
    print(f"  位置为边界: {analyzer._is_boundary_char(ai_response, pos+len(brand), False)}")

# 检查位置10 (APPLE)
pos = 10
print(f"\n检查位置 {pos} (APPLE):")
print(f"  品牌: {repr(ai_response[pos:pos+len(brand)])}")
if pos > 0:
    print(f"  前一个字符: {repr(ai_response[pos-1])}")
    print(f"  前一个字符是否为边界: {analyzer._is_boundary_char(ai_response, pos, True)}")
else:
    print(f"  位置为0 (文本开头)")
    print(f"  位置为边界: {analyzer._is_boundary_char(ai_response, pos, True)}")

if pos + len(brand) < len(ai_response):
    print(f"  后一个字符: {repr(ai_response[pos+len(brand)])}")
    print(f"  后一个字符是否为边界: {analyzer._is_boundary_char(ai_response, pos+len(brand), False)}")
else:
    print(f"  位置为文本结尾")
    print(f"  位置为边界: {analyzer._is_boundary_char(ai_response, pos+len(brand), False)}")

# 手动测试查找
print("\n手动测试查找:")
pos = 0
text_lower = ai_response.lower()
brand_lower = brand.lower()
while pos < len(text_lower):
    pos = text_lower.find(brand_lower, pos)
    if pos == -1:
        break
    print(f"找到 '{brand_lower}' 在位置 {pos}")
    
    start_ok = analyzer._is_boundary_char(ai_response, pos, True)
    end_ok = analyzer._is_boundary_char(ai_response, pos + len(brand_lower), False)
    
    print(f"  开始边界检查: {start_ok}")
    print(f"  结束边界检查: {end_ok}")
    print(f"  整体匹配: {start_ok and end_ok}")
    
    pos += 1