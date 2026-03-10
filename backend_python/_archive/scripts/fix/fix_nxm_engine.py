#!/usr/bin/env python3
"""
修复 nxm_execution_engine.py - 集成后置品牌分析

此脚本修改 nxm_execution_engine.py 文件，将后置品牌分析逻辑集成进去
"""

import re

def fix_nxm_engine():
    file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换 1: 聚合逻辑
    old_text = '''                # 聚合结果 - 客观提问模式下，需要对 deduplicated 进行品牌提及分析后才能聚合
                # 方案中阶段三提及需添加后置分析。此处聚合逻辑需调整。
                # 暂时注释掉原有的品牌聚合，待后置分析完善后使用。
                # aggregated = aggregate_results_by_brand(deduplicated)
                aggregated = []
                api_logger.info(f"[NxM] 聚合结果：客观提问模式，待后置分析")'''
    
    new_text = '''                # 【P0 修复】后置品牌提及分析（客观提问模式的核心）
                # 从 AI 客观回答中提取用户品牌提及情况和竞品对比
                aggregated = []
                brand_analysis = None
                try:
                    from wechat_backend.services.brand_analysis_service import get_brand_analysis_service
                    
                    # 获取品牌分析服务
                    analysis_service = get_brand_analysis_service(judge_model='doubao')
                    
                    # 执行品牌提及分析
                    brand_analysis = analysis_service.analyze_brand_mentions(
                        results=deduplicated,
                        user_brand=main_brand,
                        competitor_brands=competitor_brands  # 可为 None，自动从回答中提取
                    )
                    
                    # 构建聚合结果（基于品牌分析）
                    if brand_analysis:
                        aggregated = [{
                            'brand': main_brand,
                            'is_user_brand': True,
                            'mention_rate': brand_analysis['user_brand_analysis']['mention_rate'],
                            'average_rank': brand_analysis['user_brand_analysis']['average_rank'],
                            'average_sentiment': brand_analysis['user_brand_analysis']['average_sentiment'],
                            'is_top3': brand_analysis['user_brand_analysis']['is_top3'],
                            'mentioned_count': brand_analysis['user_brand_analysis']['mentioned_count'],
                            'total_responses': brand_analysis['user_brand_analysis']['total_responses'],
                            'comparison': brand_analysis['comparison']
                        }]
                        
                        # 添加竞品分析
                        for comp in brand_analysis.get('competitor_analysis', []):
                            aggregated.append({
                                'brand': comp['brand'],
                                'is_user_brand': False,
                                'mention_rate': comp['mention_rate'],
                                'average_rank': comp['average_rank'],
                                'average_sentiment': comp['average_sentiment'],
                                'is_top3': comp['is_top3'],
                                'mentioned_count': comp['mentioned_count'],
                                'total_responses': len(comp['mentions']),
                                'comparison': None
                            })
                        
                        api_logger.info(
                            f"[P0 修复] ✅ 品牌分析完成：{main_brand}, "
                            f"提及率={brand_analysis['user_brand_analysis']['mention_rate']:.1%}, "
                            f"竞品数={len(brand_analysis['competitor_analysis'])}"
                        )
                    
                except Exception as analysis_err:
                    api_logger.error(f"[P0 修复] ⚠️ 品牌分析失败：{analysis_err}")
                    # 降级：返回空聚合结果
                    aggregated = []'''
    
    if old_text in content:
        content = content.replace(old_text, new_text)
        print("✓ 替换 1 完成：聚合逻辑已更新")
    else:
        print("✗ 替换 1 失败：未找到目标文本")
        return False
    
    # 替换 2: results_summary 构建
    old_text2 = '''                    # 构建结果摘要
                    results_summary = {
                        'total_tasks': total_tasks,
                        'completed_tasks': len(deduplicated),
                        'success_rate': len(deduplicated) / total_tasks if total_tasks > 0 else 0,
                        'quality_score': overall_score,
                        # 品牌信息需要后置分析，此处 brands 置空。
                        'brands': [],
                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),
                    }'''
    
    new_text2 = '''                    # 构建结果摘要（包含品牌分析）
                    results_summary = {
                        'total_tasks': total_tasks,
                        'completed_tasks': len(deduplicated),
                        'success_rate': len(deduplicated) / total_tasks if total_tasks > 0 else 0,
                        'quality_score': overall_score,
                        # 品牌信息（来自后置分析）
                        'brands': [main_brand] + [c['brand'] for c in brand_analysis.get('competitor_analysis', [])] if brand_analysis else [],
                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),
                        'user_brand_analysis': brand_analysis.get('user_brand_analysis') if brand_analysis else None,
                        'comparison': brand_analysis.get('comparison') if brand_analysis else None,
                    }'''
    
    if old_text2 in content:
        content = content.replace(old_text2, new_text2)
        print("✓ 替换 2 完成：results_summary 已更新")
    else:
        print("✗ 替换 2 失败：未找到目标文本")
        return False
    
    # 替换 3: 返回结果中的 aggregated
    old_text3 = '''                    'results': deduplicated,
                    'aggregated': [], # 待后置分析'''
    
    new_text3 = '''                    'results': deduplicated,
                    'aggregated': aggregated,
                    'brand_analysis': brand_analysis,'''
    
    if old_text3 in content:
        content = content.replace(old_text3, new_text3)
        print("✓ 替换 3 完成：返回结果已更新")
    else:
        print("✗ 替换 3 失败：未找到目标文本")
        return False
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✓ 所有修改已完成！")
    return True

if __name__ == '__main__':
    fix_nxm_engine()
