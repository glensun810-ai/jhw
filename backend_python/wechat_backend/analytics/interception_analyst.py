import re
from collections import defaultdict
from typing import List, Dict, Any, Optional

class InterceptionAnalyst:
    """
    竞品拦截分析算法
    用于计算首位推荐率、声量占比 (SOV) 和拦截预警
    """

    def __init__(self, all_brands: List[str], main_brand: str):
        self.all_brands = all_brands
        self.main_brand = main_brand
        self.brand_keywords = {brand: [brand] for brand in all_brands} # 简化：品牌关键词就是品牌名本身

    def calculate_first_mention_rate(self, platform_results: List[Dict[str, Any]]) -> Optional[str]:
        """
        分析在某个AI平台下，哪个品牌被 AI 第一个提及。
        
        Args:
            platform_results: 某个AI平台下，所有品牌对某个通用问题的回答列表
                              [{brand: '蔚来', aiModel: 'DeepSeek', question: '介绍蔚来', response: '...'}]
        Returns:
            第一个被提及的品牌名称，如果没有则返回 None
        """
        # 假设 platform_results 已经按某种顺序排列 (例如，按AI回复的顺序)
        # 实际场景中，可能需要更复杂的NLP来判断“第一个提及”
        for result in platform_results:
            response_content = result.get('response', '')
            for brand in self.all_brands:
                if brand in response_content: # 简单判断品牌名是否在回复中
                    return brand
        return None

    def calculate_sov(self, response_content: str) -> Dict[str, float]:
        """
        计算各品牌在 AI 整个回复文本中的字数占比和关键词出现频次对比。
        
        Args:
            response_content: AI的回复文本
        Returns:
            一个包含各品牌SOV数据的字典 {brand: sov_percentage}
        """
        total_chars = len(response_content)
        if total_chars == 0:
            return {brand: 0.0 for brand in self.all_brands}

        brand_char_counts = defaultdict(int)
        for brand in self.all_brands:
            for keyword in self.brand_keywords[brand]:
                brand_char_counts[brand] += response_content.count(keyword) * len(keyword) # 关键词出现次数 * 关键词长度

        sov_data = {}
        for brand, count in brand_char_counts.items():
            sov_data[brand] = round((count / total_chars) * 100, 2) # 转换为百分比

        return sov_data

    def analyze_interception_risk(self, main_brand_source_map: Dict[str, Any], competitor_source_maps: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        拦截预警：若竞品的权威信源明显优于本品牌，生成“认知拦截风险”标签。
        
        Args:
            main_brand_source_map: 主品牌的信源情报图数据
            competitor_source_maps: 竞品的信源情报图数据 {brand: source_map}
        Returns:
            一个包含拦截风险的列表 [{brand: '竞品A', reason: '权威信源优势明显'}]
        """
        risks = []
        
        # 简化：假设“官方网站”和“Wikipedia”是权威信源
        def get_authority_score(source_map: Dict[str, Any]) -> float:
            if not source_map or not source_map.get('links'):
                return 0.0
            score = 0.0
            for link in source_map['links']:
                target_node = next((node for node in source_map['nodes'] if node.get('id') == link['target']), None)
                if target_node and target_node.get('name') in ['官方网站', 'Wikipedia']:
                    score += link.get('contribution_score', 0) * 10 # 权重加倍
            return score

        main_brand_authority = get_authority_score(main_brand_source_map)

        for comp_brand, comp_source_map in competitor_source_maps.items():
            comp_authority = get_authority_score(comp_source_map)
            if comp_authority > main_brand_authority * 1.2: # 竞品权威信源优势超过主品牌20%
                risks.append({
                    'brand': comp_brand,
                    'reason': f"竞品 {comp_brand} 在权威信源方面优势明显，可能导致AI认知拦截。",
                    'risk_level': 'high'
                })
        return risks

# 示例用法 (仅供测试)
if __name__ == "__main__":
    all_brands = ["蔚来", "特斯拉", "理想汽车"]
    main_brand = "蔚来"
    analyst = InterceptionAnalyst(all_brands, main_brand)

    # 模拟AI回复
    response1 = "蔚来汽车是一家领先的智能电动汽车公司，提供高性能产品和卓越服务。"
    response2 = "特斯拉是电动汽车行业的领导者，其创新技术和自动驾驶备受关注。"
    response3 = "理想汽车专注于家庭用户，提供增程式电动汽车，解决里程焦虑。"

    # 测试SOV
    print("SOV for response1:", analyst.calculate_sov(response1))
    print("SOV for response2:", analyst.calculate_sov(response2))
    print("SOV for response3:", analyst.calculate_sov(response3))

    # 模拟平台结果
    platform_results = [
        {'brand': '特斯拉', aiModel: 'DeepSeek', question: '介绍新能源汽车', response: response2},
        {'brand': '蔚来', aiModel: 'DeepSeek', question: '介绍新能源汽车', response: response1},
        {'brand': '理想汽车', aiModel: 'DeepSeek', question: '介绍新能源汽车', response: response3},
    ]
    print("First mention:", analyst.calculate_first_mention_rate(platform_results))

    # 模拟信源数据
    main_brand_source = {'nodes': [{'id': 'website', 'name': '官方网站'}], 'links': [{'source': 'brand', 'target': 'website', 'contribution_score': 0.7}]}
    comp_brand_source = {'nodes': [{'id': 'wiki', 'name': 'Wikipedia'}], 'links': [{'source': 'brand', 'target': 'wiki', 'contribution_score': 0.9}]}
    
    print("Interception risks:", analyst.analyze_interception_risk(main_brand_source, {'特斯拉': comp_brand_source}))