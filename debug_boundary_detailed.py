#!/usr/bin/env python3
"""
详细调试边界检查
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
text = "小明科技的产品很不错，明明是个好孩子。"
brand = "小明"

print("测试文本:", repr(text))
print("品牌:", repr(brand))

# 检查位置0的"小明"
start_pos = 0
end_pos = 2  # "小明"的长度
print(f"\n检查位置 {start_pos}-{end_pos} ('小明'):")

brand_text = text[start_pos:end_pos]
print(f"品牌文本: {repr(brand_text)}")
print(f"品牌文本属性: isalpha={brand_text.isalpha()}, isascii={brand_text.isascii()}")

if start_pos == 0:
    print("开始位置是文本开头，start_ok=True")
else:
    prev_char = text[start_pos - 1]
    print(f"前一个字符: {repr(prev_char)}")
    start_ok = prev_char in [c.lower() for c in analyzer.brand_prefixes]
    print(f"前一个字符是否为边界: {start_ok}")

next_char = text[end_pos]
print(f"后一个字符: {repr(next_char)}")
print(f"后一个字符属性: isalnum={next_char.isalnum()}, isascii={next_char.isascii()}")

end_ok_basic = next_char in [c.lower() for c in analyzer.brand_suffixes]
print(f"基本边界检查: {end_ok_basic}")

# 检查英文品牌逻辑
if brand_text.isalpha() and brand_text.isascii():
    print("这是一个英文品牌")
    end_ok = end_ok_basic or (not next_char.isascii() or not next_char.isalnum())
else:
    print("这是一个中文品牌")
    end_ok = end_ok_basic or (not next_char.isalnum())
    
print(f"最终end_ok: {end_ok}")

overall = (start_pos == 0 or (start_pos > 0 and text[start_pos - 1] in [c.lower() for c in analyzer.brand_prefixes])) and end_ok
print(f"整体边界检查: {overall}")

# 检查函数
func_result = analyzer._is_valid_brand_boundary(text, start_pos, end_pos)
print(f"函数结果: {func_result}")