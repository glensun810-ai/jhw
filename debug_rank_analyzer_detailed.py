#!/usr/bin/env python3
"""
详细调试rank_analyzer.py中的问题
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼的智能锁很好，小米也不错，凯迪仕也有一定市场。"
brand = "德施曼"

print("测试文本:", repr(ai_response))
print("品牌:", repr(brand))
print("Brand prefixes:", analyzer.brand_prefixes)
print("Brand suffixes:", analyzer.brand_suffixes)

# 手动测试查找逻辑
text_lower = ai_response.lower()
brand_lower = brand.lower()

print(f"Text lower: {repr(text_lower)}")
print(f"Brand lower: {repr(brand_lower)}")

pos = 0
while pos < len(text_lower):
    pos = text_lower.find(brand_lower, pos)
    print(f"Found '{brand_lower}' at position {pos}")
    if pos == -1:
        break
        
    # 检查边界字符
    if pos == 0:
        start_ok = True
        print("Start is OK (pos == 0)")
    else:
        prev_char = ai_response[pos - 1]  # 使用原始文本
        print(f"Previous character: {repr(prev_char)}")
        start_ok = prev_char in analyzer.brand_prefixes
        print(f"Start OK: {start_ok}, prev_char in prefixes: {prev_char in analyzer.brand_prefixes}")
    
    if pos + len(brand_lower) == len(text_lower):
        end_ok = True
        print("End is OK (end of text)")
    else:
        next_char = ai_response[pos + len(brand_lower)]  # 使用原始文本
        print(f"Next character: {repr(next_char)}")
        end_ok = next_char in analyzer.brand_suffixes
        print(f"End OK: {end_ok}, next_char in suffixes: {next_char in analyzer.brand_suffixes}")
    
    if start_ok and end_ok:
        print(f"Match found at position {pos}")
        break
    else:
        print("No match, continuing search")
    
    pos += 1