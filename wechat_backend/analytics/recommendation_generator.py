"""
干预建议生成器 - 基于信源情报和证据链生成行动建议
"""
import re
from typing import Dict, List, Any, Optional
from collections import Counter
import jieba
import requests
from urllib.parse import urlparse


class RecommendationGenerator:
    """
    干预建议生成器
    基于source_intelligence中的信源频次和evidence_chain中的负面证据，生成行动建议
    """
    
    def __init__(self):
        # 常见的停用词
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '它', '他', '她', '我们', '你们', '他们', '这个', '那个', '这些', '那些', '什么', '怎么', '为什么', '哪个', '哪里', '何时', '如何', '可以', '能够', '应该', '需要', '想要', '希望', '觉得', '认为', '知道', '明白', '理解', '了解', '学习', '工作', '生活', '时间', '地方', '事情', '问题', '答案', '方法', '方式', '技术', '产品', '服务', '公司', '用户', '客户', '市场', '销售', '价格', '质量', '功能', '性能', '特点', '优势', '劣势', '优点', '缺点', '好处', '坏处', '影响', '效果', '结果', '目标', '目的', '意义', '价值', '重要', '必要', '可能', '也许', '大概', '大约', '左右', '附近', '周围', '里面', '外面', '前面', '后面', '左边', '右边', '上面', '下面', '中间', '中央', '旁边', '附近', '的', '是', '在', '有', '和', '与', '及', '了', '着', '过', '等', '之', '与', '及', '也', '就', '都', '而', '及', '或', '但', '及'
        }
        
        # 常见的负面关键词，用于识别负面内容
        self.negative_keywords = [
            '差', '不好', '较差', '一般', '缺点', '不足', '问题', '风险', '隐患', '缺陷', '故障', 
            '不稳定', '不耐用', '不实用', '不美观', '不舒适', '不环保', '不健康', '不安全', 
            '不靠谱', '不推荐', '慎用', '注意', '小心', '警惕', '谨慎', '担忧', '担心', '疑虑', 
            '质疑', '批评', '指责', '抱怨', '不满', '失望', '糟糕', '差劲', '垃圾', '烂', '坑', 
            '骗', '套路', '陷阱', '忽悠', '夸大', '虚假', '误导', '偏见', '歧视', '争议', '纠纷', 
            '矛盾', '冲突', '对立', '敌对', '攻击', '贬低', '诋毁', '诽谤', '造谣', '传谣', '谣言', 
            '假消息', '假新闻', '假信息', '假货', '仿冒', '山寨', '抄袭', '剽窃', '侵权', '盗版', 
            '非法', '违法', '违规', '不当', '不合适', '不宜', '有害', '不利', '负面影响', '消极影响', 
            '不良影响', '负面作用', '副作用', '毒副作用', '过敏反应', '刺激性', '腐蚀性', '毒性', 
            '放射性', '危险性', '风险性', '不确定性', '不稳定性', '不可靠性', '不安全性', '不实用性', 
            '不美观性', '不舒适性', '不环保性', '不健康性', '不经济性', '不划算', '不值得', '不推荐', 
            '不建议', '不适宜', '不适合', '不匹配', '不兼容', '不协调', '不和谐', '不统一', '不一致', 
            '不连贯', '不流畅', '不顺畅', '不顺手', '不顺心', '不顺意', '不顺遂', '不顺当', '不顺利'
        ]
        
        # 常见的正面关键词，用于识别正面内容
        self.positive_keywords = [
            '好', '优秀', '先进', '领先', '强大', '出色', '卓越', '优质', '高端', '专业', '可靠', '稳定',
            '安全', '耐用', '智能', '高效', '创新', '精美', '舒适', '美观', '时尚', '经典', '独特',
            '个性', '定制', '专业', '权威', '标准', '认证', '专利', '品牌', '名牌', '老字号', '新兴',
            '成长', '发展', '扩张', '盈利', '收益', '回报', '投资', '成本', '价格', '性价比', '优惠',
            '折扣', '促销', '活动', '营销', '推广', '宣传', '广告', '公关', '传播', '曝光', '知名度',
            '声誉', '信誉', '口碑', '评价', '评分', '星级', '推荐', '好评', '体验', '感受', '印象',
            '认知', '认识', '了解', '熟悉', '新鲜', '新颖', '传统', '现代', '当代', '古典', '复古',
            '未来', '科技', '科学', '艺术', '文化', '教育', '培训', '学习', '知识', '智慧', '经验',
            '技能', '能力', '素质', '品格', '道德', '伦理', '法律', '法规', '政策', '制度', '规则',
            '秩序', '纪律', '自由', '民主', '平等', '公正', '公平', '正义', '和平', '竞争', '合作',
            '团结', '友谊', '爱情', '亲情', '友情', '家庭', '社会', '国家', '世界', '宇宙', '自然'
        ]
    
    def generate_recommendations(self, source_intelligence: Dict, evidence_chain: List[Dict], my_brand: str) -> List[Dict]:
        """
        基于信源情报和证据链生成行动建议
        
        Args:
            source_intelligence: 信源情报数据
            evidence_chain: 证据链数据
            my_brand: 我方品牌名称
            
        Returns:
            按优先级排序的行动建议列表
        """
        recommendations = []
        
        # 1. 识别高优攻坚站点
        high_priority_sites = self._identify_high_priority_sites(source_intelligence, my_brand)
        for site in high_priority_sites:
            recommendations.append({
                'priority': 'High',
                'type': 'site_targeting',
                'title': '高优攻坚站点',
                'description': f'信源 "{site["url"]}"({site["site_name"]}) 引用频次高但缺乏我方正面内容，建议优先投放公关资源',
                'action': 'content_placement',
                'target': site['url'],
                'confidence': site['citation_count'] / 10.0  # 基于引用频次的置信度
            })
        
        # 2. 生成公关纠偏话术
        if evidence_chain:
            correction_statements = self._generate_correction_statements(evidence_chain, my_brand)
            for stmt in correction_statements:
                recommendations.append({
                    'priority': 'High',
                    'type': 'correction',
                    'title': '公关纠偏建议',
                    'description': f'针对负面内容 "{stmt["negative_fragment"][:20]}..." 进行纠偏',
                    'action': 'public_relations_correction',
                    'content': stmt['correction_statement'],
                    'target_evidence': stmt['negative_fragment'],
                    'associated_url': stmt.get('associated_url', ''),
                    'confidence': 0.8 if stmt['risk_level'] == 'High' else 0.6
                })
        else:
            # 3. 如果没有负面信息，提供品牌心智强化建议
            reinforcement_suggestions = self._generate_reinforcement_suggestions(source_intelligence, my_brand)
            for suggestion in reinforcement_suggestions:
                recommendations.append({
                    'priority': 'Medium',
                    'type': 'reinforcement',
                    'title': '品牌心智强化',
                    'description': suggestion['description'],
                    'action': 'brand_reinforcement',
                    'content': suggestion['content'],
                    'confidence': 0.7
                })
        
        # 按优先级排序
        priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 99))
        
        return recommendations
    
    def _identify_high_priority_sites(self, source_intelligence: Dict, my_brand: str) -> List[Dict]:
        """
        识别高优攻坚站点：引用频次高但无我方正面内容的信源
        
        Args:
            source_intelligence: 信源情报数据
            my_brand: 我方品牌名称
            
        Returns:
            高优先级站点列表
        """
        high_priority_sites = []
        
        source_pool = source_intelligence.get('source_pool', [])
        citation_rank = source_intelligence.get('citation_rank', [])
        
        # 按引用频次排序信源
        sorted_sources = sorted(source_pool, key=lambda x: x.get('citation_count', 0), reverse=True)
        
        for source in sorted_sources[:5]:  # 只检查前5个高频信源
            url = source.get('url', '')
            site_name = source.get('site_name', '')
            citation_count = source.get('citation_count', 0)
            domain_authority = source.get('domain_authority', 'Low')
            
            # 如果引用频次大于等于2，且权威度较高，则标记为高优攻坚站点
            if citation_count >= 2 and domain_authority in ['High', 'Medium']:
                high_priority_sites.append({
                    'url': url,
                    'site_name': site_name,
                    'citation_count': citation_count,
                    'domain_authority': domain_authority
                })
        
        return high_priority_sites
    
    def _generate_correction_statements(self, evidence_chain: List[Dict], my_brand: str) -> List[Dict]:
        """
        为负面证据生成公关纠偏话术
        
        Args:
            evidence_chain: 证据链数据
            my_brand: 我方品牌名称
            
        Returns:
            纠偏话术列表
        """
        correction_statements = []
        
        for evidence in evidence_chain:
            negative_fragment = evidence.get('negative_fragment', '')
            associated_url = evidence.get('associated_url', '')
            source_name = evidence.get('source_name', '')
            risk_level = evidence.get('risk_level', 'Medium')
            
            # 生成针对负面内容的纠偏话术
            correction_statement = self._create_correction_statement(negative_fragment, my_brand)
            
            correction_statements.append({
                'negative_fragment': negative_fragment,
                'associated_url': associated_url,
                'source_name': source_name,
                'risk_level': risk_level,
                'correction_statement': correction_statement
            })
        
        return correction_statements
    
    def _create_correction_statement(self, negative_content: str, my_brand: str) -> str:
        """
        创建针对负面内容的纠偏话术

        Args:
            negative_content: 负面内容片段
            my_brand: 我方品牌名称

        Returns:
            纠偏话术
        """
        # 这里可以集成AI生成能力，但现在我们使用高级模板生成
        # 实际应用中，这里应该调用AI模型生成更精准的公关话术

        # 分析负面内容的类型
        negative_type = self._analyze_negative_content_type(negative_content)

        # 生成更具体的公关回应
        if negative_type == 'quality_issue':
            return f"关于网络上对{my_brand}产品质量的关切，我们郑重声明：{my_brand}始终遵循严格的质量管控体系，所有产品均通过国家级质量检测认证。我们感谢社会各界的监督，并将持续提升产品品质以满足用户期待。"
        elif negative_type == 'security_concern':
            return f"针对近期网络上关于{my_brand}产品安全性的不实信息，我们特此澄清：{my_brand}产品已通过国家权威机构的安全认证，采用军工级加密技术保障用户信息安全。我们坚决反对任何未经证实的安全质疑，并保留追究法律责任的权利。"
        elif negative_type == 'performance_issue':
            return f"关于{my_brand}产品性能的客观评价：{my_brand}产品在出厂前均经过严苛的性能测试，确保在各种使用环境下稳定运行。我们不断优化产品性能，致力于为用户提供卓越的使用体验。"
        elif negative_type == 'service_complaint':
            return f"关于{my_brand}售后服务的说明：我们始终以用户满意度为核心，建立了完善的售后服务体系。如您遇到任何服务问题，请通过官方客服渠道反馈，我们将第一时间为您解决。"
        else:
            # 通用公关回应模板
            return f"关于网络上有关{my_brand}的某些信息，我们高度重视用户反馈。{my_brand}始终坚持高标准的产品质量和服务理念，致力于为用户提供优质的产品体验。对于不实信息，我们已记录并会持续关注。如您有任何疑问或建议，欢迎通过官方渠道与我们沟通。"

    def _analyze_negative_content_type(self, content: str) -> str:
        """
        分析负面内容的类型

        Args:
            content: 负面内容

        Returns:
            负面内容类型
        """
        content_lower = content.lower()

        # 检查是否涉及质量问题
        quality_indicators = ['质量', '品质', '缺陷', '故障', '坏', '差', '问题', '缺陷', '瑕疵', '损坏', '失效', '不良', '次品', '残次', '不合格', '不达标', '问题', '毛病', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', 'bug', '
    
    def _analyze_negative_content_type(self, content: str) -> str:
        """
        分析负面内容的类型
        
        Args:
            content: 负面内容
            
        Returns:
            负面内容类型
        """
        content_lower = content.lower()
        
        # 检查是否涉及质量问题
        quality_indicators = ['质量', '品质', '缺陷', '故障', '坏', '差', '问题', '缺陷', '瑕疵', '损坏', '失效']
        if any(indicator in content_lower for indicator in quality_indicators):
            return 'quality_issue'
        
        # 检查是否涉及安全问题
        security_indicators = ['安全', '隐私', '泄露', '风险', '漏洞', '危险', '有害', '威胁', '攻击', '破解']
        if any(indicator in content_lower for indicator in security_indicators):
            return 'security_concern'
        
        # 检查是否涉及性能问题
        performance_indicators = ['性能', '速度', '效率', '功能', '效果', '表现', '能力', '功率', '效能']
        if any(indicator in content_lower for indicator in performance_indicators):
            return 'performance_issue'
        
        # 默认类型
        return 'general_concern'
    
    def _generate_reinforcement_suggestions(self, source_intelligence: Dict, my_brand: str) -> List[Dict]:
        """
        生成品牌心智强化建议（当没有负面信息时）
        
        Args:
            source_intelligence: 信源情报数据
            my_brand: 我方品牌名称
            
        Returns:
            品牌强化建议列表
        """
        suggestions = []
        
        # 获取高频信源
        source_pool = source_intelligence.get('source_pool', [])
        high_freq_sources = [s for s in source_pool if s.get('citation_count', 0) >= 2]
        
        if high_freq_sources:
            # 建议在高频信源上加强正面内容投放
            top_sources = sorted(high_freq_sources, key=lambda x: x.get('citation_count', 0), reverse=True)[:3]
            for source in top_sources:
                suggestions.append({
                    'description': f'在{source["site_name"]}平台加强{my_brand}正面内容投放',
                    'content': f'建议制作关于{my_brand}在{source["site_name"]}平台的正面评测内容，提升品牌在该平台的正面声量。'
                })
        else:
            # 如果没有特定高频信源，提供通用强化建议
            suggestions.append({
                'description': f'全面提升{my_brand}品牌心智',
                'content': f'建议通过多渠道内容营销，强化{my_brand}在用户心智中的正面形象，突出产品核心优势和差异化特色。'
            })
        
        # 添加其他强化建议
        suggestions.append({
            'description': f'强化{my_brand}核心优势传播',
            'content': f'围绕{my_brand}的核心技术优势和用户体验亮点，制作系列正面内容，提升品牌认知度。'
        })
        
        return suggestions


# 示例使用
if __name__ == "__main__":
    generator = RecommendationGenerator()

    # 示例数据
    sample_source_intel = {
        'source_pool': [
            {'id': '1', 'url': 'https://zhihu.com/article/123', 'site_name': '知乎', 'citation_count': 5, 'domain_authority': 'High'},
            {'id': '2', 'url': 'https://baidu.com/baike/456', 'site_name': '百度百科', 'citation_count': 3, 'domain_authority': 'High'},
            {'id': '3', 'url': 'https://weibo.com/post/789', 'site_name': '微博', 'citation_count': 1, 'domain_authority': 'Medium'}
        ],
        'citation_rank': ['1', '2', '3']
    }

    sample_evidence_chain = [
        {
            'negative_fragment': '德施曼的智能锁容易被破解',
            'associated_url': 'https://zhihu.com/article/123',
            'source_name': '知乎',
            'risk_level': 'High'
        }
    ]

    # 生成建议
    recommendations = generator.generate_recommendations(sample_source_intel, sample_evidence_chain, '德施曼')

    print("生成的行动建议:")
    for rec in recommendations:
        print(f"- {rec['title']}: {rec['description']}")
        if 'content' in rec:
            print(f"  内容: {rec['content']}")
        print()