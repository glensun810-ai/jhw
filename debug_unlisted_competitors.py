#!/usr/bin/env python3
"""
调试未列出竞争对手检测
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼和小米都不错，但鹿客的用户体验更好，TCL也很有竞争力。"
brand_list = ["德施曼", "小米"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 检测未列出的竞争对手
unlisted = analyzer._identify_unlisted_competitors(ai_response, brand_list)
print("检测到的未列出竞争对手:", unlisted)

# 检查处理后的文本
processed_text = ai_response
for brand in sorted(brand_list, key=len, reverse=True):
    import re
    processed_text = re.sub(re.escape(brand), '', processed_text, flags=re.IGNORECASE)

print("处理后的文本:", processed_text)