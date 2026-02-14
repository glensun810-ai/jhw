#!/usr/bin/env python3
"""
调试完整工作流程测试
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = "在智能锁领域，德施曼的技术领先，小米性价比突出，凯迪仕也有一定份额。鹿客用户体验更好。"
brand_list = ["德施曼", "小米", "凯迪仕"]

print("测试文本:", ai_response)
print("品牌列表:", brand_list)

# 执行完整分析
result = analyzer.analyze(ai_response, brand_list)

print("完整分析结果:")
print("- 排名列表:", result['ranking_list'])
print("- 品牌详情:", list(result['brand_details'].keys()))
print("- 未列出的竞争对手:", result['unlisted_competitors'])

# 单独测试未列出竞争对手检测
unlisted = analyzer._identify_unlisted_competitors(ai_response, brand_list)
print("单独检测未列出竞争对手:", unlisted)

# 检查处理后的文本
import re
processed_text = ai_response
for brand in sorted(brand_list, key=len, reverse=True):
    processed_text = re.sub(re.escape(brand), '', processed_text, flags=re.IGNORECASE)

print("处理后的文本:", processed_text)

# 检查中文品牌模式匹配
chinese_brand_pattern = r'[\u4e00-\u9fa5]{2,4}'
import re
chinese_matches = re.findall(chinese_brand_pattern, processed_text)
print("中文品牌模式匹配结果:", chinese_matches)

# 检查是否在知名品牌列表中
known_brands = ['鹿客', 'TCL', '华为', '苹果', '三星', 'OPPO', 'vivo', '一加', '魅族', '索尼', '松下', '西门子', '飞利浦', '美的', '格力', '海尔', '联想', '戴尔', '惠普', '华硕', '宏碁', '佳能', '尼康', '比亚迪', '吉利', '长城', '奇瑞', '蔚来', '小鹏', '理想', '特斯拉', '宝马', '奔驰', '奥迪', '大众', '丰田', '本田', '小米', '荣耀', '海信', '创维', '长虹']
for match in chinese_matches:
    print(f"'{match}' 是否在知名品牌列表中: {match in known_brands}")