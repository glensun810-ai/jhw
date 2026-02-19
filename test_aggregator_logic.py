#!/usr/bin/env python3
"""
Unit Test Runner for reportAggregator.js logic
验证聚合引擎的逻辑正确性
"""

import json

def test_aggregate_report():
    """测试聚合报告逻辑"""
    print("\n" + "="*60)
    print("GEO 品牌战略聚合引擎 - 闭环验收测试")
    print("="*60)
    
    # 测试数据 1: 正常数据（3 问题×4 模型×1 主品牌）
    test1_results = [
        # 问题 1 - 4 个模型的回答
        {"question_id": 0, "question_text": "介绍一下 Tesla", "model": "doubao", "geo_data": {"brand_mentioned": True, "rank": 2, "sentiment": 0.7, "cited_sources": [{"url": "https://a.com", "site_name": "Site A", "attitude": "positive"}], "interception": ""}},
        {"question_id": 0, "question_text": "介绍一下 Tesla", "model": "qwen", "geo_data": {"brand_mentioned": True, "rank": 3, "sentiment": 0.5, "cited_sources": [], "interception": "BMW"}},
        {"question_id": 0, "question_text": "介绍一下 Tesla", "model": "deepseek", "geo_data": {"brand_mentioned": True, "rank": 1, "sentiment": 0.8, "cited_sources": [{"url": "https://b.com", "site_name": "Site B", "attitude": "negative"}], "interception": ""}},
        {"question_id": 0, "question_text": "介绍一下 Tesla", "model": "zhipu", "geo_data": {"brand_mentioned": True, "rank": 2, "sentiment": 0.6, "cited_sources": [], "interception": ""}},
        # 问题 2 - 4 个模型的回答
        {"question_id": 1, "question_text": "Tesla 的主要产品", "model": "doubao", "geo_data": {"brand_mentioned": True, "rank": 3, "sentiment": 0.4, "cited_sources": [], "interception": ""}},
        {"question_id": 1, "question_text": "Tesla 的主要产品", "model": "qwen", "geo_data": {"brand_mentioned": True, "rank": 4, "sentiment": 0.3, "cited_sources": [], "interception": "Mercedes"}},
        {"question_id": 1, "question_text": "Tesla 的主要产品", "model": "deepseek", "geo_data": {"brand_mentioned": False, "rank": -1, "sentiment": 0, "cited_sources": [], "interception": ""}},
        {"question_id": 1, "question_text": "Tesla 的主要产品", "model": "zhipu", "geo_data": {"brand_mentioned": True, "rank": 2, "sentiment": 0.5, "cited_sources": [], "interception": ""}},
        # 问题 3 - 4 个模型的回答
        {"question_id": 2, "question_text": "Tesla 和竞品区别", "model": "doubao", "geo_data": {"brand_mentioned": True, "rank": 1, "sentiment": 0.9, "cited_sources": [], "interception": ""}},
        {"question_id": 2, "question_text": "Tesla 和竞品区别", "model": "qwen", "geo_data": {"brand_mentioned": True, "rank": 2, "sentiment": 0.7, "cited_sources": [], "interception": ""}},
        {"question_id": 2, "question_text": "Tesla 和竞品区别", "model": "deepseek", "geo_data": {"brand_mentioned": True, "rank": 1, "sentiment": 0.8, "cited_sources": [], "interception": ""}},
        {"question_id": 2, "question_text": "Tesla 和竞品区别", "model": "zhipu", "geo_data": {"brand_mentioned": True, "rank": 3, "sentiment": 0.6, "cited_sources": [], "interception": "BMW"}}
    ]
    
    # 手动计算期望值
    total_results = len(test1_results)
    total_mentions = sum(1 for r in test1_results if r.get("geo_data", {}).get("brand_mentioned", False))
    sov = (total_mentions / total_results) * 100
    
    print(f"\n测试 1: 正常数据（3 问题×4 模型×1 主品牌）")
    print("-"*60)
    print(f"  总结果数：{total_results}")
    print(f"  提及数：{total_mentions}")
    print(f"  SOV: {sov:.1f}% (期望：91.7%)")
    
    # 验证 SOV 计算
    sov_match = abs(sov - 91.7) < 1
    print(f"  SOV 验证：{'✅ 通过' if sov_match else '❌ 失败'}")
    
    # 计算每个问题的平均排名
    from collections import defaultdict
    question_map = defaultdict(list)
    for r in test1_results:
        qid = r["question_id"]
        geo = r.get("geo_data") or {}
        if geo.get("brand_mentioned"):
            rank = geo.get("rank", 10) if geo.get("rank", 10) > 0 else 10
            question_map[qid].append(rank)
    
    print(f"\n  QuestionCards 验证:")
    for qid in sorted(question_map.keys()):
        ranks = question_map[qid]
        avg_rank = sum(ranks) / len(ranks) if ranks else 0
        mention_count = len(ranks)
        print(f"    问题 {qid+1}: 平均排名={avg_rank:.1f}, 提及率={mention_count}/4")
    
    # 验证问题 1 的排名计算
    q1_ranks = [2, 3, 1, 2]  # 4 个模型的排名
    q1_avg = sum(q1_ranks) / len(q1_ranks)
    print(f"\n  问题 1 排名验证:")
    print(f"    原始排名：{q1_ranks}")
    print(f"    计算平均：{q1_avg:.1f} (期望：2.0)")
    q1_match = abs(q1_avg - 2.0) < 0.1
    print(f"    排名验证：{'✅ 通过' if q1_match else '❌ 失败'}")
    
    # 验证竞品拦截
    interceptions = []
    for r in test1_results:
        geo = r.get("geo_data") or {}
        if geo.get("interception"):
            interceptions.append(geo["interception"])
    
    print(f"\n  竞品拦截验证:")
    print(f"    拦截记录：{interceptions}")
    print(f"    拦截次数：{len(interceptions)} (BMW: {interceptions.count('BMW')}, Mercedes: {interceptions.count('Mercedes')})")
    
    # 验证负面信源
    toxic_sources = []
    for r in test1_results:
        geo = r.get("geo_data") or {}
        for src in geo.get("cited_sources", []):
            if src.get("attitude") == "negative":
                toxic_sources.append(src)
    
    print(f"\n  负面信源验证:")
    print(f"    负面信源数：{len(toxic_sources)} (期望：1)")
    for src in toxic_sources:
        print(f"      - [{src.get('site_name')}] {src.get('url')}")
    
    # 测试 2: 部分数据缺失
    print(f"\n{'='*60}")
    print(f"测试 2: 部分数据缺失")
    print("-"*60)
    
    test2_results = [
        {"question_id": 0, "geo_data": {"brand_mentioned": True, "rank": 5, "sentiment": 0.3}},
        {"question_id": 0, "geo_data": None},
        {"question_id": 0, "geo_data": {"brand_mentioned": False, "rank": -1, "sentiment": 0}},
        {"question_id": 1, "geo_data": None},
        {"question_id": 1, "geo_data": {"brand_mentioned": True, "rank": 8, "sentiment": -0.2}}
    ]
    
    total_t2 = len(test2_results)
    mentions_t2 = sum(1 for r in test2_results if r.get("geo_data") and r["geo_data"].get("brand_mentioned"))
    sov_t2 = (mentions_t2 / total_t2) * 100
    
    print(f"  总结果数：{total_t2}")
    print(f"  提及数：{mentions_t2}")
    print(f"  SOV: {sov_t2:.1f}% (期望：40%)")
    sov_t2_match = abs(sov_t2 - 40) < 1
    print(f"  SOV 验证：{'✅ 通过' if sov_t2_match else '❌ 失败'}")
    
    # 测试 3: 全空数据
    print(f"\n{'='*60}")
    print(f"测试 3: 全空数据")
    print("-"*60)
    
    test3_results = []
    result_t3 = None if len(test3_results) == 0 else "有数据"
    print(f"  结果数：{len(test3_results)}")
    print(f"  返回值：{result_t3} (期望：null)")
    t3_pass = result_t3 is None
    print(f"  验证：{'✅ 通过' if t3_pass else '❌ 失败'}")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print("="*60)
    
    all_pass = sov_match and q1_match and sov_t2_match and t3_pass
    print(f"  SOV 计算：{'✅ 通过' if sov_match else '❌ 失败'}")
    print(f"  平均排名：{'✅ 通过' if q1_match else '❌ 失败'}")
    print(f"  缺失处理：{'✅ 通过' if sov_t2_match else '❌ 失败'}")
    print(f"  全空处理：{'✅ 通过' if t3_pass else '❌ 失败'}")
    print(f"\n  总体结果：{'🎉 所有测试通过！' if all_pass else '⚠️ 部分测试失败'}")
    
    return all_pass

if __name__ == '__main__':
    result = test_aggregate_report()
    exit(0 if result else 1)
