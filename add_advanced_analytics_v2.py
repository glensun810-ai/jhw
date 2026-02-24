#!/usr/bin/env python3
"""添加高级分析数据生成代码 - 版本 2"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 使用更精确的匹配
old_text = '''                )

                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")
            else:
                scheduler.fail_execution(verification['message'])'''

new_text = '''                )

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

                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")
            else:
                scheduler.fail_execution(verification['message'])'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 高级分析数据生成代码已添加")
else:
    print("❌ 未找到目标文本")
    # 显示找到的内容
    import re
    match = re.search(r'\)\s+api_logger\.info\(f"\[NxM\] 执行成功', content)
    if match:
        print(f"找到类似内容：{match.group()[:100]}")
