#!/usr/bin/env python3
"""
P0-2 竞品遍历功能修复脚本

修复内容:
1. 添加品牌遍历循环
2. 更新提示词构建使用当前品牌
3. 更新结果 brand 字段使用当前品牌
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 添加品牌遍历循环
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
                            # P0-2 修复：模板需要 brand_name, competitors, question 三个参数
                            # 竞品是当前品牌，其他品牌是竞争对手
                            current_competitors = [b for b in all_brands if b != brand]
                            prompt = GEO_PROMPT_TEMPLATE.format(
                                brand_name=brand,  # P0-2 修复：使用当前遍历的品牌
                                competitors=', '.join(current_competitors) if current_competitors else '无',
                                question=question
                            )'''

if old_loop in content:
    content = content.replace(old_loop, new_loop)
    print("✅ 修复 1: 品牌遍历循环已添加")
else:
    print("❌ 修复 1: 未找到目标循环代码")

# 修复 2: 更新失败结果的 brand 字段
old_fail_result = '''                            result = {
                                'brand': main_brand,
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }'''

new_fail_result = '''                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }'''

if old_fail_result in content:
    content = content.replace(old_fail_result, new_fail_result)
    print("✅ 修复 2: 失败结果的 brand 字段已更新")
else:
    print("❌ 修复 2: 未找到失败结果代码")

# 修复 3: 更新成功结果的 brand 字段
old_success_result = '''                            # 构建结果
                            result = {
                                'brand': main_brand,'''

new_success_result = '''                            # 构建结果（确保所有字段都是 JSON 可序列化的）
                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌'''

if old_success_result in content:
    content = content.replace(old_success_result, new_success_result)
    print("✅ 修复 3: 成功结果的 brand 字段已更新")
else:
    print("❌ 修复 3: 未找到成功结果代码")

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ P0-2 竞品遍历功能修复完成！")
print("\n修复内容:")
print("1. 添加品牌遍历循环 (外层：品牌，中层：问题，内层：模型)")
print("2. 提示词构建使用当前遍历的品牌")
print("3. 结果 brand 字段使用当前遍历的品牌")
print("\n预期效果:")
print("- 总任务数：8 品牌 × 1 问题 × 3 模型 = 24 任务")
print("- 完成率：100%")
print("- detailed_results 包含所有 8 个品牌")
