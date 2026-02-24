#!/usr/bin/env python3
"""
应用 P0-2 竞品数据生成修复到 nxm_execution_engine.py
"""

import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 更新总任务数计算
content = content.replace(
    '''    # 计算总任务数
    total_tasks = len(raw_questions) * len(selected_models)''',
    '''    # P0-2 修复：计算总任务数（品牌数 × 问题数 × 模型数）
    all_brands_count = 1 + len(competitor_brands or [])
    total_tasks = all_brands_count * len(raw_questions) * len(selected_models)'''
)

# 修复 2: 更新执行循环遍历所有品牌
old_loop = '''            # 外层循环：遍历问题
            for q_idx, question in enumerate(raw_questions):
                # 内层循环：遍历模型
                for model_info in selected_models:
                    model_name = model_info.get('name', '')
                    
                    # 检查模型是否可用（熔断器）
                    if not scheduler.is_model_available(model_name):
                        api_logger.warning(f"[NxM] 模型 {model_name} 已熔断，跳过")
                        completed += 1
                        scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                        continue
                    
                    try:
                        # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                        from config import Config

                        # 创建 AI 客户端
                        client = AIAdapterFactory.create(model_name)
                        api_key = Config.get_api_key(model_name)

                        if not api_key:
                            raise ValueError(f"模型 {model_name} API Key 未配置")

                        # 构建提示词
                        # P0 修复：模板需要 brand_name, competitors, question 三个参数
                        prompt = GEO_PROMPT_TEMPLATE.format(
                            brand_name=main_brand,
                            competitors=', '.join(competitor_brands) if competitor_brands else '无',
                            question=question
                        )'''

new_loop = '''            # P0-2 修复：遍历所有品牌（主品牌 + 竞品）
            all_brands = [main_brand] + (competitor_brands or [])
            api_logger.info(f"[NxM] 执行品牌数：{len(all_brands)}, 品牌列表：{all_brands}")

            # 外层循环：遍历品牌
            for brand in all_brands:
                # 中层循环：遍历问题
                for q_idx, question in enumerate(raw_questions):
                    # 内层循环：遍历模型
                    for model_info in selected_models:
                        model_name = model_info.get('name', '')

                        # 检查模型是否可用（熔断器）
                        if not scheduler.is_model_available(model_name):
                            api_logger.warning(f"[NxM] 模型 {model_name} 已熔断，跳过")
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                            continue

                        try:
                            # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                            from config import Config

                            # 创建 AI 客户端
                            client = AIAdapterFactory.create(model_name)
                            api_key = Config.get_api_key(model_name)

                            if not api_key:
                                raise ValueError(f"模型 {model_name} API Key 未配置")

                            # 构建提示词
                            # P0 修复：模板需要 brand_name, competitors, question 三个参数
                            # 竞品是当前品牌，其他品牌是竞争对手
                            current_competitors = [b for b in all_brands if b != brand]
                            prompt = GEO_PROMPT_TEMPLATE.format(
                                brand_name=brand,
                                competitors=', '.join(current_competitors) if current_competitors else '无',
                                question=question
                            )'''

content = content.replace(old_loop, new_loop)

# 修复 3: 更新结果中的 brand 字段（失败情况）
content = content.replace(
    '''                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }''',
    '''                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }'''
)

# 修复 4: 更新结果中的 brand 字段（成功情况）
content = content.replace(
    '''                            # 构建结果
                            result = {
                                'brand': main_brand,''',
    '''                            # 构建结果（确保所有字段都是 JSON 可序列化的）
                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌'''
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ P0-2 竞品数据生成修复已应用")
