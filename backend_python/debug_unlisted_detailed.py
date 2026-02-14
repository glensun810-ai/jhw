#!/usr/bin/env python3
"""
详细调试未列出竞争对手检测
"""
import re
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼和小米都不错，但鹿客的用户体验更好，TCL也很有竞争力。"
brand_list = ["德施曼", "小米"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 检查处理后的文本
processed_text = ai_response
for brand in sorted(brand_list, key=len, reverse=True):
    processed_text = re.sub(re.escape(brand), '', processed_text, flags=re.IGNORECASE)

print("处理后的文本:", processed_text)

# 测试各种正则表达式模式
potential_competitor_patterns = [
    r'(?<!\w)([A-Z][a-z]+(?:[A-Z][a-z]*)*)(?!\w)',  # 驼峰式命名
    r'(?<!\w)([A-Z]{2,})(?!\w)',  # 全大写字母缩写
    r'(?<!\w)([A-Z][a-z]+(?:\s+[A-Z][a-z]*)+)(?!\w)',  # 多词品牌名
]

print("\n测试正则表达式模式:")
for i, pattern in enumerate(potential_competitor_patterns):
    matches = re.findall(pattern, processed_text)
    print(f"模式 {i+1} ({pattern}): {matches}")

# 检测未列出的竞争对手
unlisted = analyzer._identify_unlisted_competitors(ai_response, brand_list)
print("\n检测到的未列出竞争对手:", unlisted)