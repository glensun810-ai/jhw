#!/usr/bin/env python3
"""
检查jieba分词行为
"""
import jieba

text = "小明明的智能锁不错，小明品牌也有提及。"
brand_name = "小明"

print("原始文本:", text)
print("品牌名称:", brand_name)

# 使用jieba分词
words = jieba.lcut(text)
print("分词结果:", words)

# 检查每个词
for i, word in enumerate(words):
    clean_word = word.strip()
    print(f"词[{i}]: '{clean_word}' (长度: {len(clean_word)})")
    if len(clean_word) >= 2:
        print(f"  - 是否在品牌名'{brand_name}'中: {clean_word in brand_name}")
        print(f"  - 是否等于品牌名: {clean_word == brand_name}")
        print(f"  - 是否应该跳过: {clean_word in brand_name and clean_word != brand_name}")