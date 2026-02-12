#!/usr/bin/env python3
"""
调试未列出竞争对手检测功能
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

# 手动测试中文品牌模式
chinese_brand_pattern = r'[\u4e00-\u9fa5]{2,4}'
chinese_matches = re.findall(chinese_brand_pattern, processed_text)
print("中文品牌模式匹配结果:", chinese_matches)

# 检查是否是常见的非品牌词
common_non_brand_words = ['不错', '更好', '更有', '很', '比较', '相对', '但是', '不过', '然而', '所以', '因为', '如果', '虽然', '这个', '那个', '这些', '那些', '什么', '怎么', '为什么', '怎么样', '如何', '可以', '能够', '应该', '需要', '想要', '希望', '觉得', '认为', '知道', '明白', '理解', '了解', '学习', '工作', '生活', '时间', '地方', '事情', '问题', '答案', '方法', '方式', '技术', '产品', '服务', '公司', '用户', '客户', '市场', '销售', '价格', '质量', '功能', '性能', '特点', '优势', '劣势', '优点', '缺点', '好处', '坏处', '影响', '效果', '结果', '目标', '目的', '意义', '价值', '重要', '必要', '可能', '也许', '大概', '大约', '左右', '附近', '周围', '里面', '外面', '前面', '后面', '左边', '右边', '上面', '下面', '中间', '中央', '旁边', '附近', '的', '是', '在', '有', '和', '与', '及', '了', '着', '过', '等', '之', '与', '及', '也', '就', '都', '而', '及', '或', '但', '及']

for match in chinese_matches:
    print(f"'{match}' 是否在常见非品牌词中: {match in common_non_brand_words}")

# 检查知名品牌列表
known_brands = ['鹿客', 'TCL', '华为', '苹果', '三星', 'OPPO', 'vivo', '一加', '魅族', '索尼', '松下', '西门子', '飞利浦', '美的', '格力', '海尔', '联想', '戴尔', '惠普', '华硕', '宏碁', '佳能', '尼康', '比亚迪', '吉利', '长城', '奇瑞', '蔚来', '小鹏', '理想', '特斯拉', '宝马', '奔驰', '奥迪', '大众', '丰田', '本田', '小米', '荣耀', 'TCL', '海信', '创维', '长虹']
for match in chinese_matches:
    print(f"'{match}' 是否是知名品牌: {match in known_brands}")

# 检查上下文模式
for match in chinese_matches:
    if match not in common_non_brand_words:
        context_patterns = [
            # 在对比结构中，如"相比之下，XXX做得更好"、"但XXX的用户体验更好"
            r'(?:相比|相对|不同于|不像|除了|但|然而|不过|可是|但是)\s*' + re.escape(match) + r'\s*(?:的|是|在|有|比|也|很|非常|特别|相当|尤其|尤其|而且|并且|还|又|更|最)',
            # 在"XXX也"、"XXX很"等结构中
            r'' + re.escape(match) + r'\s*(?:也|很|非常|特别|相当|尤其|尤其|而且|并且|还|又|更|最)',
        ]
        
        found_in_context = any(re.search(pattern, processed_text) for pattern in context_patterns)
        print(f"'{match}' 是否在特定上下文中: {found_in_context}")

# 执行完整的检测
unlisted = analyzer._identify_unlisted_competitors(ai_response, brand_list)
print("完整检测结果:", unlisted)