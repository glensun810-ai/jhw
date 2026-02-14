#!/usr/bin/env python3
"""
验证物理排位解析引擎的完整功能
"""
from wechat_backend.analytics.rank_analyzer import RankAnalyzer

# 创建分析器实例
analyzer = RankAnalyzer()

# 测试文本
ai_response = """
在智能锁领域，德施曼的技术一直领先，其指纹识别算法较为先进。
小米的智能锁性价比突出，深受大众消费者喜爱。
凯迪仕在工程渠道也有一定份额。
相比之下，鹿客在用户体验方面做得更好。
TCL也很有竞争力。
"""
brand_list = ["德施曼", "小米", "凯迪仕"]

print("测试AI回复:", ai_response)
print("监控品牌列表:", brand_list)

# 执行分析
result = analyzer.analyze(ai_response, brand_list)

print("\n分析结果:")
print(f"- 排名列表: {result['ranking_list']}")
print(f"- 品牌详情: {list(result['brand_details'].keys())}")
for brand, details in result['brand_details'].items():
    print(f"  {brand}: 排名={details['rank']}, 字数={details['word_count']}, 篇幅占比={details['sov_share']:.3f}")
print(f"- 未列出的竞争对手: {result['unlisted_competitors']}")

# 验证结果是否符合API契约
print("\n验证API契约符合性:")
expected_keys = ['ranking_list', 'brand_details', 'unlisted_competitors']
for key in expected_keys:
    if key in result:
        print(f"✓ {key} 字段存在")
    else:
        print(f"✗ {key} 字段缺失")

# 验证排名列表
if '德施曼' in result['ranking_list']:
    print("✓ 德施曼在排名列表中")
else:
    print("✗ 德施曼不在排名列表中")

if '鹿客' in result['unlisted_competitors']:
    print("✓ 鹿客被识别为未列出的竞争对手")
else:
    print("✗ 鹿客未被识别为未列出的竞争对手")

if 'TCL' in result['unlisted_competitors']:
    print("✓ TCL被识别为未列出的竞争对手")
else:
    print("✗ TCL未被识别为未列出的竞争对手")

print("\n物理排位解析引擎测试完成！")