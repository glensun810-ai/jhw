#!/usr/bin/env python3
"""
调试jieba分词行为
"""
import jieba

# 测试文本
text = "小明明的智能锁不错，小明品牌也有提及。"
brand_name = "小明"

print("原始文本:", text)
print("品牌名称:", brand_name)

# 在添加频率建议前分词
print("\n添加频率建议前的分词结果:")
words_before = jieba.lcut(text)
print(words_before)

# 添加频率建议
jieba.suggest_freq(brand_name, tune=True)
print(f"为'{brand_name}'添加频率建议")

# 在添加频率建议后分词
print("\n添加频率建议后的分词结果:")
words_after = jieba.lcut(text)
print(words_after)

# 检查是否包含"小明明"
if "小明明" in words_after:
    print("\n✓ 找到了'小明明'")
else:
    print("\n✗ 没有找到'小明明'")

# 尝试更具体的解决方案：手动添加复合词
composite_word = "小明明"
jieba.suggest_freq(composite_word, tune=True)
print(f"为复合词'{composite_word}'添加频率建议")

print("\n再次分词的结果:")
words_final = jieba.lcut(text)
print(words_final)

if "小明明" in words_final:
    print("✓ 找到了'小明明'")
else:
    print("✗ 仍然没有找到'小明明'")