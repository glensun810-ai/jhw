#!/usr/bin/env python3
"""
调试边界检查函数
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
text = "Apple手机很好，APPLE商店服务也不错。"
brand = "Apple"

print("测试文本:", repr(text))
print("品牌:", repr(brand))

# 检查品牌文本的属性
brand_text = text[0:5]  # "Apple"
print(f"brand_text: {repr(brand_text)}")
print(f"brand_text.isalpha(): {brand_text.isalpha()}")
print(f"brand_text.isascii(): {brand_text.isascii()}")

# 检查下一个字符的属性
next_char = text[5]  # "手"
print(f"next_char: {repr(next_char)}")
print(f"next_char.isalnum(): {next_char.isalnum()}")
print(f"next_char in brand_suffixes: {next_char in analyzer.brand_suffixes}")

# 检查边界检查的各个部分
start_pos = 0
end_pos = 5
brand_text = text[start_pos:end_pos]
next_char = text[end_pos]

print(f"\n边界检查分析:")
print(f"start_pos == 0: {start_pos == 0}")
print(f"text[start_pos - 1].lower() in brand_prefixes: {text[start_pos - 1].lower() in [c.lower() for c in analyzer.brand_prefixes] if start_pos > 0 else 'N/A'}")

print(f"end_pos >= len(text): {end_pos >= len(text)}")
print(f"next_char in brand_suffixes: {next_char in [c.lower() for c in analyzer.brand_suffixes]}")
print(f"brand_text.isalpha() and brand_text.isascii(): {brand_text.isalpha() and brand_text.isascii()}")
print(f"not next_char.isalnum(): {not next_char.isalnum()}")

# 检查end_ok的计算
end_ok = next_char in [c.lower() for c in analyzer.brand_suffixes]
print(f"end_ok (basic): {end_ok}")

if brand_text.isalpha() and brand_text.isascii():  # 纯英文字母
    end_ok = end_ok or not next_char.isalnum()
    print(f"end_ok (after english check): {end_ok}")

# 检查start_ok的计算
start_ok = start_pos == 0 or text[start_pos - 1].lower() in [c.lower() for c in analyzer.brand_prefixes]
print(f"start_ok: {start_ok}")

print(f"Overall: {start_ok and end_ok}")