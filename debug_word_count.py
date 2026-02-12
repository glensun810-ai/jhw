#!/usr/bin/env python3
"""
调试字数统计问题
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "德施曼的智能锁很好，功能强大。小米性价比高。"
brand = "德施曼"

print("测试文本:", ai_response)
print("品牌:", brand)
print("期望长度:", len("德施曼的智能锁很好，功能强大。"))

# 计算字数
word_count = analyzer._calculate_brand_word_count(ai_response, brand)
print("实际字数:", word_count)

# 检查品牌位置
positions = analyzer._find_all_brand_positions(ai_response, brand)
print("品牌位置:", positions)

# 检查句子边界
for pos in positions:
    start_idx = analyzer._find_sentence_start(ai_response, pos)
    end_idx = analyzer._find_sentence_end(ai_response, pos + len(brand))
    print(f"句子范围: {start_idx}-{end_idx}")
    print(f"句子内容: {ai_response[start_idx:end_idx]}")
    print(f"从品牌开始到句子结束: {ai_response[pos:end_idx]}")
    print(f"从品牌开始到句子结束长度: {len(ai_response[pos:end_idx])}")