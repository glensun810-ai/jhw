#!/usr/bin/env python3
"""
P0-2 竞品遍历功能修复 - 最终版本
使用简单直接的字符串替换
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 总任务数
content = content.replace(
    'total_tasks = len(raw_questions) * len(selected_models)',
    'total_tasks = (1 + len(competitor_brands or [])) * len(raw_questions) * len(selected_models)'
)

# 修复 2: 品牌遍历 - 分步替换
# 2a: 在 run_execution 后添加品牌列表
content = content.replace(
    '''    def run_execution():
        try:
            results = []
            completed = 0

            # 外层循环：遍历问题''',
    '''    def run_execution():
        try:
            results = []
            completed = 0

            # P0-2 修复：遍历所有品牌（主品牌 + 竞品）
            all_brands = [main_brand] + (competitor_brands or [])
            api_logger.info(f"[NxM] 执行品牌数：{len(all_brands)}, 品牌列表：{all_brands}")

            # 外层循环：遍历品牌
            for brand in all_brands:
                # 中层循环：遍历问题'''
)

# 2b: 添加模型循环缩进
content = content.replace(
    '''                # 中层循环：遍历问题
                for q_idx, question in enumerate(raw_questions):
                    # 内层循环：遍历模型
                    for model_info in selected_models:''',
    '''                # 中层循环：遍历问题
                for q_idx, question in enumerate(raw_questions):
                    # 内层循环：遍历模型
                    for model_info in selected_models:'''
)

# 2c: 更新提示词
content = content.replace(
    '''                        prompt = GEO_PROMPT_TEMPLATE.format(
                            brand_name=main_brand,
                            competitors=', '.join(competitor_brands) if competitor_brands else '无',
                            question=question
                        )''',
    '''                        # P0-2 修复：使用当前品牌和其竞争对手
                        current_competitors = [b for b in all_brands if b != brand]
                        prompt = GEO_PROMPT_TEMPLATE.format(
                            brand_name=brand,
                            competitors=', '.join(current_competitors) if current_competitors else '无',
                            question=question
                        )'''
)

# 修复 3: 结果 brand 字段
content = content.replace(
    "'brand': main_brand,",
    "'brand': brand,"
)

# 保存
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ P0-2 修复完成")
