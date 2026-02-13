"""
测试推荐生成器的功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.recommendation_generator import RecommendationGenerator
import json


def test_recommendation_generator():
    """测试推荐生成器的基本功能"""
    
    # 创建示例数据
    sample_source_intelligence = {
        "source_pool": [
            {
                "id": "zhihu",
                "url": "https://www.zhihu.com",
                "site_name": "知乎",
                "citation_count": 15,
                "domain_authority": "High"
            },
            {
                "id": "baidu_baike",
                "url": "https://baike.baidu.com",
                "site_name": "百度百科",
                "citation_count": 12,
                "domain_authority": "High"
            },
            {
                "id": "csdn",
                "url": "https://www.csdn.net",
                "site_name": "CSDN",
                "citation_count": 8,
                "domain_authority": "Medium"
            }
        ],
        "citation_rank": ["zhihu", "baidu_baike", "csdn"]
    }
    
    sample_evidence_chain = [
        {
            "negative_fragment": "德施曼智能锁质量不过关，多次出现故障",
            "associated_url": "https://www.zhihu.com/question/123456",
            "source_name": "知乎",
            "risk_level": "High"
        },
        {
            "negative_fragment": "德施曼的售后服务太差了",
            "associated_url": "https://www.csdn.net/article/789012",
            "source_name": "CSDN",
            "risk_level": "Medium"
        }
    ]
    
    brand_name = "德施曼"
    
    # 创建推荐生成器实例
    generator = RecommendationGenerator()
    
    # 生成推荐
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_source_intelligence,
        evidence_chain=sample_evidence_chain,
        brand_name=brand_name
    )
    
    print("=== 测试推荐生成器功能 ===")
    print(f"生成了 {len(recommendations)} 条建议:")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.title}")
        print(f"   优先级: {rec.priority.value}")
        print(f"   类型: {rec.type.value}")
        print(f"   描述: {rec.description}")
        print(f"   目标: {rec.target}")
        print(f"   预估影响: {rec.estimated_impact}")
        print(f"   紧急程度: {rec.urgency}")
        print(f"   行动步骤: {', '.join(rec.action_steps)}")
    
    return recommendations


def test_no_negative_content():
    """测试没有负面内容时的情况"""
    
    sample_source_intelligence = {
        "source_pool": [
            {
                "id": "zhihu",
                "url": "https://www.zhihu.com",
                "site_name": "知乎",
                "citation_count": 15,
                "domain_authority": "High"
            }
        ],
        "citation_rank": ["zhihu"]
    }
    
    sample_evidence_chain = []  # 没有负面内容
    
    brand_name = "德施曼"
    
    # 创建推荐生成器实例
    generator = RecommendationGenerator()
    
    # 生成推荐
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_source_intelligence,
        evidence_chain=sample_evidence_chain,
        brand_name=brand_name
    )
    
    print("\n=== 测试无负面内容情况 ===")
    print(f"生成了 {len(recommendations)} 条建议:")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.title}")
        print(f"   优先级: {rec.priority.value}")
        print(f"   类型: {rec.type.value}")
        print(f"   描述: {rec.description}")
        print(f"   目标: {rec.target}")
        print(f"   预估影响: {rec.estimated_impact}")
        print(f"   紧急程度: {rec.urgency}")
        print(f"   行动步骤: {', '.join(rec.action_steps)}")
    
    return recommendations


def test_api_endpoint_simulation():
    """模拟API端点请求"""
    import json
    from flask import Flask, request, jsonify
    
    # 创建示例数据
    sample_data = {
        "source_intelligence": {
            "source_pool": [
                {
                    "id": "zhihu",
                    "url": "https://www.zhihu.com",
                    "site_name": "知乎",
                    "citation_count": 15,
                    "domain_authority": "High"
                },
                {
                    "id": "baidu_baike",
                    "url": "https://baike.baidu.com",
                    "site_name": "百度百科",
                    "citation_count": 12,
                    "domain_authority": "High"
                }
            ],
            "citation_rank": ["zhihu", "baidu_baike"]
        },
        "evidence_chain": [
            {
                "negative_fragment": "德施曼智能锁质量不过关，多次出现故障",
                "associated_url": "https://www.zhihu.com/question/123456",
                "source_name": "知乎",
                "risk_level": "High"
            }
        ],
        "brand_name": "德施曼"
    }
    
    print("\n=== 模拟API端点请求 ===")
    print("请求数据:")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))
    
    # 使用推荐生成器处理数据
    generator = RecommendationGenerator()
    recommendations = generator.generate_recommendations(
        source_intelligence=sample_data["source_intelligence"],
        evidence_chain=sample_data["evidence_chain"],
        brand_name=sample_data["brand_name"]
    )
    
    # 转换为API响应格式
    recommendations_json = []
    for rec in recommendations:
        recommendations_json.append({
            'priority': rec.priority.value,
            'type': rec.type.value,
            'title': rec.title,
            'description': rec.description,
            'target': rec.target,
            'estimated_impact': rec.estimated_impact,
            'action_steps': rec.action_steps,
            'urgency': rec.urgency
        })
    
    response = {
        'status': 'success',
        'recommendations': recommendations_json,
        'count': len(recommendations_json)
    }
    
    print("\nAPI响应:")
    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # 运行测试
    test_recommendation_generator()
    test_no_negative_content()
    test_api_endpoint_simulation()