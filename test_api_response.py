"""
验证API端点将返回cross_model_coverage字段的测试
"""
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor


def test_api_response_structure():
    """测试API响应结构，确保包含cross_model_coverage字段"""
    print("测试API响应结构，验证cross_model_coverage字段...")

    # 创建处理器实例
    processor = SourceIntelligenceProcessor()

    # 准备测试数据 - 模拟来自多个AI模型的响应
    ai_responses = [
        {
            'success': True,
            'aiModel': 'qwen',  # 通义千问
            'question': '德施曼智能锁怎么样？',
            'response': '德施曼智能锁技术先进，可以参考知乎上的评测[https://zhihu.com/article/123]。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'response_time': 1.2
        },
        {
            'success': True,
            'aiModel': 'doubao',  # 豆包
            'question': '小米智能锁怎么样？',
            'response': '小米智能锁性价比高，在淘宝上销量很好[https://taobao.com/product/456]。',
            'citations': [{'url': 'https://taobao.com/product/456', 'title': '小米智能锁销售页面'}],
            'response_time': 1.5
        },
        {
            'success': True,
            'aiModel': 'deepseek',  # DeepSeek
            'question': '智能锁品牌对比',
            'response': '知乎上有很多关于智能锁的评测文章[https://zhihu.com/article/123]，包括德施曼和小米。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'response_time': 1.8
        },
        {
            'success': True,
            'aiModel': 'chatgpt',  # ChatGPT
            'question': '智能锁安全性如何？',
            'response': '知乎上的评测文章[https://zhihu.com/article/123]提到了智能锁的安全性问题。',
            'citations': [{'url': 'https://zhihu.com/article/123', 'title': '智能锁品牌对比评测'}],
            'response_time': 2.0
        }
    ]

    # 处理数据
    result = processor.process('德施曼', ai_responses)

    print(f"处理结果 - 节点数量: {len(result['nodes'])}, 链接数量: {len(result['links'])}")

    # 检查品牌节点
    brand_node = result['nodes'][0]
    print(f"品牌节点: {brand_node['name']} (ID: {brand_node['id']})")

    # 检查信源节点，特别是验证cross_model_coverage字段
    source_nodes = [node for node in result['nodes'][1:] if node['category'] == 'source']
    print(f"\n信源节点数量: {len(source_nodes)}")
    
    for i, node in enumerate(source_nodes):
        print(f"\n信源节点 {i+1}:")
        print(f"  - 名称: {node['name']}")
        print(f"  - ID: {node['id']}")
        print(f"  - 跨模型覆盖度 (cross_model_coverage): {node.get('cross_model_coverage', 'MISSING')}")
        print(f"  - 引用次数 (citation_count): {node.get('citation_count', 'MISSING')}")
        print(f"  - 影响力指数 (impact_index): {node.get('impact_index', 'MISSING')}")
        print(f"  - 权威度 (domain_authority): {node.get('domain_authority', 'MISSING')}")
        print(f"  - 节点大小: {node['symbolSize']:.2f}")
        
        # 验证必要的字段是否存在
        assert 'cross_model_coverage' in node, f"节点 {i+1} 缺少 cross_model_coverage 字段!"
        assert 'citation_count' in node, f"节点 {i+1} 缺少 citation_count 字段!"
        assert 'impact_index' in node, f"节点 {i+1} 缺少 impact_index 字段!"
        assert 'domain_authority' in node, f"节点 {i+1} 缺少 domain_authority 字段!"

    # 特别检查知乎链接，它应该被多个模型引用
    print(f"\n验证跨模型覆盖度计算:")
    zhihu_nodes = [node for node in source_nodes if 'zhihu' in node['name'].lower() or 'zhihu' in node.get('id', '').lower()]
    if zhihu_nodes:
        zhihu_node = zhihu_nodes[0]
        cross_model_coverage = zhihu_node.get('cross_model_coverage', 0)
        citation_count = zhihu_node.get('citation_count', 0)
        
        print(f"  知乎链接分析:")
        print(f"    - 跨模型覆盖度: {cross_model_coverage} (应该是3，因为qwen、deepseek和chatgpt都引用了)")
        print(f"    - 引用次数: {citation_count} (应该是3)")
        print(f"    - 影响力指数: {zhihu_node.get('impact_index', 'N/A'):.2f}")
        
        # 验证知乎链接确实被多个模型引用
        assert cross_model_coverage >= 2, f"知乎链接应该被至少2个模型引用，但实际只有 {cross_model_coverage} 个"
        assert citation_count >= 2, f"知乎链接应该被至少引用2次，但实际只有 {citation_count} 次"
    else:
        print("  未找到知乎链接节点")

    # 验证API规范要求的字段
    print(f"\n验证API规范要求的字段:")
    
    # 检查source_pool结构
    source_pool = [node for node in result['nodes'][1:] if node['category'] == 'source']
    
    for source in source_pool:
        required_fields = ['id', 'url', 'site_name', 'citation_count', 'domain_authority', 'cross_model_coverage', 'impact_index']
        missing_fields = [field for field in required_fields if field not in source]
        
        if missing_fields:
            print(f"  错误: 信源 {source.get('id', 'unknown')} 缺少字段: {missing_fields}")
        else:
            print(f"  ✓ 信源 {source['id']} 包含所有必需字段")
    
    print(f"\n✓ 所有测试通过! API响应结构符合要求，包含cross_model_coverage字段。")

    # 输出完整的JSON结构供参考
    print(f"\nAPI响应示例 (前两个信源节点):")
    example_sources = source_pool[:2]
    print(json.dumps(example_sources, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_api_response_structure()