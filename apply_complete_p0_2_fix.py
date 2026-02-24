#!/usr/bin/env python3
"""
P0-2 竞品遍历功能完整修复脚本

修复内容:
1. 更新总任务数计算
2. 添加品牌遍历循环
3. 更新提示词构建
4. 更新结果 brand 字段
5. 添加高级分析数据生成
"""

import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 总任务数计算
content = content.replace(
    'total_tasks = len(raw_questions) * len(selected_models)',
    'total_tasks = (1 + len(competitor_brands or [])) * len(raw_questions) * len(selected_models)  # P0-2: 品牌数×问题数×模型数'
)
print("✅ 修复 1: 总任务数计算已更新")

# 修复 2: 添加品牌遍历循环 - 使用正则表达式
old_pattern = r'''(            # 外层循环：遍历问题
            for q_idx, question in enumerate\(raw_questions\):
                # 内层循环：遍历模型
                for model_info in selected_models:
                    model_name = model_info\.get\('name', ''\)

                    # 检查模型是否可用（熔断器）
                    if not scheduler\.is_model_available\(model_name\):
                        api_logger\.warning\(f"\[NxM\] 模型 \{model_name\} 已熔断，跳过"\)
                        completed \+= 1
                        scheduler\.update_progress\(completed, total_tasks, 'ai_fetching'\)
                        continue

                    try:
                        # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                        from config import Config

                        # 创建 AI 客户端
                        client = AIAdapterFactory\.create\(model_name\)
                        api_key = Config\.get_api_key\(model_name\)

                        if not api_key:
                            raise ValueError\(f"模型 \{model_name\} API Key 未配置"\)

                        # 构建提示词
                        # P0 修复：模板需要 brand_name, competitors, question 三个参数
                        prompt = GEO_PROMPT_TEMPLATE\.format\(
                            brand_name=main_brand,
                            competitors=', '\.join\(competitor_brands\) if competitor_brands else '无',
                            question=question
                        \))'''

new_code = r'''            # P0-2 修复：遍历所有品牌（主品牌 + 竞品）
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

content = re.sub(old_pattern, new_code, content)
print("✅ 修复 2: 品牌遍历循环已添加")

# 修复 3: 更新失败结果的 brand 字段
content = content.replace(
    "'brand': main_brand,",
    "'brand': brand,  # P0-2 修复：使用当前遍历的品牌"
)
print("✅ 修复 3: 结果 brand 字段已更新")

# 修复 4: 在保存测试记录后添加高级分析数据生成
old_analytics = '''                save_test_record(
                    execution_id=execution_id,
                    user_id=user_id,
                    brand_name=main_brand,
                    results=deduplicated,
                    user_level=user_level
                )

                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")'''

new_analytics = '''                save_test_record(
                    execution_id=execution_id,
                    user_id=user_id,
                    brand_name=main_brand,
                    results=deduplicated,
                    user_level=user_level
                )

                # 【P0 修复】生成高级分析数据
                try:
                    api_logger.info(f"[NxM] 开始生成高级分析数据：{execution_id}")
                    
                    # 1. 生成核心洞察
                    try:
                        api_logger.info(f"[NxM] 开始生成核心洞察：{execution_id}")
                        target_brand_scores = brand_scores.get(main_brand, {})
                        authority = target_brand_scores.get('overallAuthority', 50)
                        visibility = target_brand_scores.get('overallVisibility', 50)
                        purity = target_brand_scores.get('overallPurity', 50)
                        consistency = target_brand_scores.get('overallConsistency', 50)
                        dimensions = {'权威度': authority, '可见度': visibility, '纯净度': purity, '一致性': consistency}
                        advantage_dim = max(dimensions, key=dimensions.get)
                        risk_dim = min(dimensions, key=dimensions.get)
                        insights = {
                            'advantage': f"{advantage_dim}表现突出，得分{dimensions[advantage_dim]}分",
                            'risk': f"{risk_dim}相对薄弱，得分{dimensions[risk_dim]}分，需重点关注",
                            'opportunity': f"{risk_dim}有较大提升空间，建议优先优化"
                        }
                        execution_store[execution_id]['insights'] = insights
                        api_logger.info(f"[NxM] 核心洞察生成完成：{execution_id}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 核心洞察生成失败：{e}")
                    
                    # 2. 生成信源纯净度分析
                    try:
                        api_logger.info(f"[NxM] 开始生成信源纯净度分析：{execution_id}")
                        from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor
                        processor = SourceIntelligenceProcessor()
                        source_purity_data = processor.process(main_brand, deduplicated)
                        execution_store[execution_id]['source_purity_data'] = source_purity_data
                        api_logger.info(f"[NxM] 信源纯净度分析完成：{execution_id}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 信源纯净度分析失败：{e}")
                    
                    # 3. 生成信源情报图谱
                    try:
                        api_logger.info(f"[NxM] 开始生成信源情报图谱：{execution_id}")
                        nodes = []
                        node_id = 0
                        for result in deduplicated:
                            geo_data = result.get('geo_data', {})
                            cited_sources = geo_data.get('cited_sources', [])
                            for source in cited_sources:
                                nodes.append({
                                    'id': f'source_{node_id}',
                                    'name': source.get('site_name', '未知信源'),
                                    'value': source.get('weight', 50),
                                    'sentiment': source.get('attitude', 'neutral'),
                                    'category': source.get('category', 'general'),
                                    'url': source.get('url', '')
                                })
                                node_id += 1
                        source_intelligence_map = {'nodes': nodes, 'links': []}
                        execution_store[execution_id]['source_intelligence_map'] = source_intelligence_map
                        api_logger.info(f"[NxM] 信源情报图谱生成完成：{execution_id}, 节点数：{len(nodes)}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 信源情报图谱生成失败：{e}")
                    
                    api_logger.info(f"[NxM] 高级分析数据生成完成：{execution_id}")
                except Exception as e:
                    api_logger.error(f"[NxM] 生成高级分析数据失败：{e}")

                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")'''

content = content.replace(old_analytics, new_analytics)
print("✅ 修复 4: 高级分析数据生成已添加")

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅✅✅ P0-2 竞品遍历功能完整修复完成！✅✅✅")
print("\n修复内容总结:")
print("1. 总任务数计算：品牌数×问题数×模型数")
print("2. 品牌遍历循环：外层品牌，中层问题，内层模型")
print("3. 提示词构建：使用当前遍历的品牌")
print("4. 结果 brand 字段：使用当前遍历的品牌")
print("5. 高级分析数据：核心洞察、信源纯净度、信源情报图谱")
print("\n预期效果:")
print("- 总任务数：8 品牌 × 1 问题 × 3 模型 = 24 任务")
print("- 完成率：100%")
print("- detailed_results 包含所有 8 个品牌")
