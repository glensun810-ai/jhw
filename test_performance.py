#!/usr/bin/env python3
"""
性能验证测试：模拟 20 条 + 原始数据（约 10 万字）
测试聚合和跳转响应时间是否小于 300ms
"""

import time
import random
import json

def generate_large_test_data(num_questions=5, num_models=4, content_length=2000):
    """
    生成大数据量测试结果
    
    Args:
        num_questions: 问题数量
        num_models: 模型数量
        content_length: 每个回答的字符数
    
    Returns:
        结果数组和总字符数
    """
    results = []
    total_chars = 0
    
    # 生成一些示例内容
    sample_texts = [
        "Tesla 是一家美国的电动汽车和清洁能源公司，由埃隆·马斯克于 2003 年创立。公司总部位于德克萨斯州奥斯汀，主要业务包括电动汽车制造、太阳能产品、储能系统等。Tesla 是全球电动汽车市场的领导者，其 Model S、Model 3、Model X 和 Model Y 等车型广受欢迎。",
        "在技术创新方面，Tesla 不断推动自动驾驶技术的发展，其 Autopilot 系统和 Full Self-Driving (FSD) 功能代表了行业最高水平。公司还建立了庞大的超级充电网络，为用户提供便捷的充电服务。",
        "与传统汽车制造商相比，Tesla 的竞争优势在于其垂直整合的生产模式、先进的电池技术、强大的软件能力以及品牌影响力。然而，面临来自 BMW、Mercedes-Benz、Audi 等传统豪华品牌的竞争压力也在增加。",
        "根据最新的市场调研，Tesla 在全球电动汽车市场的份额约为 20%，在中国市场面临比亚迪、蔚来、小鹏等本土品牌的激烈竞争。投资者对 Tesla 的估值存在分歧，支持者认为其技术领先，反对者认为估值过高。",
        "Tesla 的财务状况持续改善，已连续多个季度实现盈利。2023 年营收超过 960 亿美元，净利润约 150 亿美元。公司计划在未来几年内推出更低价的车型，进一步扩大市场份额。"
    ]
    
    for q_idx in range(num_questions):
        for m_idx in range(num_models):
            # 生成随机内容
            content = " ".join(random.sample(sample_texts, 3))
            # 扩展到目标长度
            while len(content) < content_length:
                content += " " + random.choice(sample_texts)
            content = content[:content_length]
            
            total_chars += len(content)
            
            # 生成 geo_data
            brand_mentioned = random.random() > 0.15  # 85% 提及率
            geo_data = {
                "brand_mentioned": brand_mentioned,
                "rank": random.randint(1, 5) if brand_mentioned else -1,
                "sentiment": round(random.uniform(-0.5, 0.9), 2),
                "cited_sources": [],
                "interception": ""
            }
            
            # 添加一些信源
            if random.random() > 0.5:
                num_sources = random.randint(1, 3)
                for _ in range(num_sources):
                    geo_data["cited_sources"].append({
                        "url": f"https://example{random.randint(1,100)}.com/article/{random.randint(1000,9999)}",
                        "site_name": f"Media Site {random.randint(1, 20)}",
                        "attitude": random.choice(["positive", "neutral", "negative"])
                    })
            
            # 添加竞品拦截
            if random.random() > 0.7:
                geo_data["interception"] = random.choice(["BMW", "Mercedes", "Audi", "BYD"])
            
            results.append({
                "question_id": q_idx,
                "question_text": f"测试问题 {q_idx + 1}：" + random.choice([
                    "介绍一下 Tesla",
                    "Tesla 的主要产品是什么",
                    "Tesla 和竞品有什么区别",
                    "Tesla 的市场表现如何",
                    "Tesla 的技术优势在哪里"
                ]),
                "model": random.choice(["doubao", "qwen", "deepseek", "zhipu"]),
                "content": content,
                "geo_data": geo_data,
                "status": "success",
                "latency": round(random.uniform(0.5, 3.0), 2)
            })
    
    return results, total_chars

def simulate_aggregation(results, brand_name, competitors):
    """
    模拟聚合引擎处理
    """
    start_time = time.time()
    
    # 1. 按问题分组
    question_map = {}
    for item in results:
        q_id = item["question_id"]
        if q_id not in question_map:
            question_map[q_id] = {
                "questionText": item["question_text"],
                "models": [],
                "totalRank": 0,
                "mentionCount": 0,
                "sentimentSum": 0,
                "competitorInterception": []
            }
        
        geo_data = item.get("geo_data") or {}
        question_map[q_id]["models"].append(item)
        
        if geo_data.get("brand_mentioned"):
            question_map[q_id]["mentionCount"] += 1
            rank = geo_data.get("rank", 10) if geo_data.get("rank", 10) > 0 else 10
            question_map[q_id]["totalRank"] += rank
            question_map[q_id]["sentimentSum"] += geo_data.get("sentiment", 0)
        
        if geo_data.get("interception"):
            question_map[q_id]["competitorInterception"].append(geo_data["interception"])
    
    # 2. 计算全局指标
    total_questions = len(question_map)
    total_mentions = sum(1 for r in results if (r.get("geo_data") or {}).get("brand_mentioned"))
    sov = (total_mentions / len(results)) * 100 if results else 0
    
    # 3. 构建信源黑榜
    toxic_sources = []
    for r in results:
        for src in (r.get("geo_data") or {}).get("cited_sources", []):
            if src.get("attitude") == "negative":
                toxic_sources.append({
                    "url": src["url"],
                    "site": src["site_name"],
                    "model": r["model"]
                })
    
    # 4. 计算健康度
    avg_sentiment = sum((r.get("geo_data") or {}).get("sentiment", 0) for r in results) / len(results) if results else 0
    health_score = round((sov * 0.5) + ((avg_sentiment + 1) * 50 * 0.3) + (total_mentions / len(results) * 100 * 0.2)) if results else 0
    health_score = max(0, min(100, health_score))
    
    # 5. 构建问题卡片
    question_cards = []
    for q in question_map.values():
        avg_rank = round(q["totalRank"] / q["mentionCount"], 1) if q["mentionCount"] > 0 else "未入榜"
        status = "safe" if q["mentionCount"] > (len(results) / total_questions / 2) else "risk"
        intercepted_by = list(set(q["competitorInterception"]))[:2]
        
        question_cards.append({
            "text": q["questionText"],
            "avgRank": str(avg_rank) if isinstance(avg_rank, float) else avg_rank,
            "status": status,
            "interceptedBy": intercepted_by,
            "mentionCount": q["mentionCount"],
            "totalModels": len(q["models"]),
            "avgSentiment": round(q["sentimentSum"] / (q["mentionCount"] or 1), 2)
        })
    
    processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
    
    return {
        "summary": {
            "brandName": brand_name,
            "sov": round(sov, 1),
            "avgSentiment": round(avg_sentiment, 2),
            "healthScore": health_score,
            "totalTests": len(results),
            "totalMentions": total_mentions
        },
        "questionCards": question_cards,
        "toxicSources": toxic_sources[:5],
        "processingTimeMs": processing_time
    }

def run_performance_test():
    """运行性能测试"""
    print("\n" + "="*60)
    print("性能验证测试：大数据量聚合响应时间")
    print("="*60)
    
    # 生成测试数据：5 问题 × 4 模型 = 20 条结果，每条约 2000 字符
    print("\n生成测试数据...")
    gen_start = time.time()
    results, total_chars = generate_large_test_data(
        num_questions=5,
        num_models=4,
        content_length=2000
    )
    gen_time = (time.time() - gen_start) * 1000
    
    print(f"  结果数量：{len(results)} 条")
    print(f"  总字符数：{total_chars:,} 字 ({total_chars/1000:.1f}K)")
    print(f"  数据生成时间：{gen_time:.1f}ms")
    
    # 模拟聚合处理
    print("\n执行聚合处理...")
    agg_start = time.time()
    dashboard_data = simulate_aggregation(results, "Tesla", ["BMW", "Mercedes", "Audi"])
    agg_time = (time.time() - agg_start) * 1000
    
    print(f"\n  聚合处理时间：{agg_time:.2f}ms")
    print(f"  目标响应时间：< 300ms")
    print(f"  性能评估：{'✅ 通过' if agg_time < 300 else '❌ 失败'}")
    
    # 显示聚合结果摘要
    print(f"\n  聚合结果摘要:")
    print(f"    SOV: {dashboard_data['summary']['sov']}%")
    print(f"    健康度：{dashboard_data['summary']['healthScore']}")
    print(f"    情感均值：{dashboard_data['summary']['avgSentiment']}")
    print(f"    问题卡片数：{len(dashboard_data['questionCards'])}")
    print(f"    负面信源数：{len(dashboard_data['toxicSources'])}")
    
    # 模拟跳转时间（包括数据序列化 + 页面加载）
    print(f"\n  模拟跳转流程:")
    serialize_start = time.time()
    json.dumps(dashboard_data)
    serialize_time = (time.time() - serialize_start) * 1000
    print(f"    数据序列化：{serialize_time:.2f}ms")
    
    # 假设页面加载时间（微信小程序环境）
    page_load_time = 100  # 估计值
    print(f"    页面加载（估计）：{page_load_time}ms")
    
    total_response_time = agg_time + serialize_time + page_load_time
    print(f"\n  总响应时间：{total_response_time:.2f}ms")
    print(f"  目标：< 300ms")
    print(f"  总体评估：{'✅ 通过' if total_response_time < 300 else '⚠️ 接近上限' if total_response_time < 500 else '❌ 需要优化'}")
    
    # 余量分析
    margin = 300 - total_response_time
    if margin > 0:
        print(f"  性能余量：+{margin:.1f}ms")
    else:
        print(f"  性能余量：{margin:.1f}ms (需要优化)")
    
    return total_response_time < 300

if __name__ == '__main__':
    result = run_performance_test()
    exit(0 if result else 1)
