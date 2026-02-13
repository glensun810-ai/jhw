"""
竞争性分析器 - 对比我方品牌与竞品的语义差异
"""
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import jieba


class CompetitiveAnalyzer:
    """
    竞争性分析器
    对比我方品牌与Top 1竞品的文本描述，提取关键词差异，生成认知差距总结
    """
    
    def __init__(self):
        # 常见的停用词，用于过滤无关词汇
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '它', '他', '她', '我们', '你们', '他们', '这个', '那个', '这些', '那些', '什么', '怎么', '为什么', '哪个', '哪里', '何时', '如何', '可以', '能够', '应该', '需要', '想要', '希望', '觉得', '认为', '知道', '明白', '理解', '了解', '学习', '工作', '生活', '时间', '地方', '事情', '问题', '答案', '方法', '方式', '产品', '服务', '公司', '用户', '客户', '市场', '销售', '价格', '质量', '目标', '目的', '重要', '必要', '可能', '也许', '大概', '大约', '左右', '附近', '周围', '里面', '外面', '前面', '后面', '左边', '右边', '上面', '下面', '中间', '中央', '旁边', '附近'
        }
        
        # 品牌相关的正面/负面关键词
        self.positive_indicators = [
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

        self.negative_indicators = [
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
    
    def analyze(self, my_brand_desc: str, competitor_desc: str, my_brand: str, competitor_brand: str) -> Dict:
        """
        对比我方品牌与竞品的语义差异

        Args:
            my_brand_desc: 我方品牌的AI描述文本
            competitor_desc: 竞品的AI描述文本
            my_brand: 我方品牌名称
            competitor_brand: 竞品品牌名称

        Returns:
            包含关键词对比和认知差距的分析结果
        """
        # 1. 提取关键词云
        my_keywords = self._extract_keywords(my_brand_desc, my_brand)
        competitor_keywords = self._extract_keywords(competitor_desc, competitor_brand)

        # 2. 找出重合词和独有词
        common_keywords = list(set(my_keywords) & set(competitor_keywords))
        my_unique_keywords = list(set(my_keywords) - set(competitor_keywords))
        competitor_unique_keywords = list(set(competitor_keywords) - set(my_keywords))

        # 3. 生成认知差距总结
        differentiation_gap = self._generate_differentiation_summary(
            my_brand, competitor_brand,
            my_unique_keywords, competitor_unique_keywords,
            common_keywords
        )

        return {
            'common_keywords': common_keywords,
            'my_brand_unique_keywords': my_unique_keywords,
            'competitor_unique_keywords': competitor_unique_keywords,
            'differentiation_gap': differentiation_gap
        }
    
    def _extract_keywords(self, text: str, brand_name: str) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 要分析的文本
            brand_name: 品牌名称（用于排除）

        Returns:
            关键词列表
        """
        # 使用jieba进行中文分词
        # 首先获取基础分词结果
        words = jieba.lcut(text)

        # 为了处理品牌名重叠问题，我们需要确保包含品牌名的复合词被正确识别
        # 例如，如果品牌名是"小明"，我们需要确保"小明明"被作为一个词处理，而不是"小明"+"明"
        # 为此，我们先尝试识别文本中可能的复合词，然后添加到jieba词典中
        potential_compound_words = []
        for i in range(len(text)):
            # 查找可能的复合词（品牌名+额外字符）
            if text[i:i+len(brand_name)] == brand_name:
                # 检查品牌名前后是否有其他字符形成复合词
                # 向后扩展查找可能的复合词
                for length in range(len(brand_name)+1, min(len(text)-i+1, len(brand_name)+4)):  # 检查比品牌名长1-3个字符的词
                    potential_word = text[i:i+length]
                    if len(potential_word) > len(brand_name):
                        potential_compound_words.append(potential_word)

                # 向前扩展查找可能的复合词（如果品牌名在词中间）
                for start_offset in range(max(0, i-3), i):  # 最多向前3个字符
                    for end_offset in range(i+len(brand_name), min(len(text)+1, i+len(brand_name)+4)):  # 最多向后3个字符
                        if end_offset > start_offset:
                            potential_word = text[start_offset:end_offset]
                            if len(potential_word) > len(brand_name) and brand_name in potential_word:
                                potential_compound_words.append(potential_word)

        # 为潜在的复合词添加jieba频率建议
        for compound_word in set(potential_compound_words):
            jieba.suggest_freq(compound_word, tune=True)

        # 重新分词以获得更好的结果
        words = jieba.lcut(text)

        # 过滤停用词、品牌名和单字符词
        filtered_words = []
        for word in words:
            clean_word = word.strip()
            # 检查是否满足关键词条件
            # 重要：品牌名本身不应该被提取为关键词，但品牌名的一部分如果在其他上下文中出现，可以被提取
            # 例如：在"小明明的智能锁不错"中，"小明"是品牌，"明明"是其他概念，应该被提取
            if (len(clean_word) >= 2 and  # 至少2个字符
                clean_word not in self.stop_words and
                clean_word != brand_name and  # 品牌名本身不作为关键词
                not clean_word.isdigit() and  # 不是纯数字
                not re.match(r'^[a-zA-Z]+$', clean_word)):  # 不是纯英文单词
                # 额外检查：避免提取品牌名的子串作为关键词，但允许提取包含品牌名的完整词
                # 例如，如果品牌名是"小明"，那么在"小明明"中不应该提取"小明"作为独立关键词
                # 但应该允许提取"小明明"作为一个完整的、不同的词
                should_skip = False

                # 检查是否是品牌名的子串（如在"小明明"中提取"小明"）
                if clean_word in brand_name and clean_word != brand_name:
                    # 如果关键词是品牌名的子串且不是品牌名本身，则跳过
                    should_skip = True
                # 不跳过包含品牌名的完整词（如"小明明"包含"小明"，但"小明明"是完整词）
                # 例如，如果品牌名是"小明"，那么"小明明"是一个不同的词，不应该被跳过
                # 但需要处理包含附加字符的情况，如"小明明的"应提取为"小明明"
                elif brand_name in clean_word and brand_name != clean_word:
                    # 如果品牌名是关键词的子串，检查是否是完整品牌词加上描述词（如"小明的"、"小明品牌"）
                    # 这种情况下，我们可能需要提取原始品牌词或处理复合词
                    pass  # 不跳过，但可能需要进一步处理

                if not should_skip:
                    # 如果关键词包含品牌名但比品牌名长，尝试清理附加的描述词
                    if brand_name in clean_word and len(clean_word) > len(brand_name):
                        # 检查是否是品牌名+描述词的形式，如"小明明的"、"小明明品牌"
                        # 尝试移除常见的后缀词
                        common_suffixes = ['的', '是', '在', '有', '和', '与', '及', '了', '着', '过', '等', '之', '与', '及', '也', '就', '都', '而', '及', '或', '但', '及', '品牌', '公司', '产品', '服务', '技术', '功能', '性能', '特点', '优势', '劣势', '优点', '缺点', '用户', '客户', '市场', '销售', '价格', '质量']

                        # 尝试移除后缀
                        cleaned_word = clean_word
                        for suffix in common_suffixes:
                            if cleaned_word.endswith(suffix) and len(cleaned_word) > len(suffix):
                                potential_cleaned = cleaned_word[:-len(suffix)]
                                # 检查去除后缀后是否只剩品牌名或品牌名的子串
                                if potential_cleaned == brand_name or (brand_name in potential_cleaned and potential_cleaned != brand_name):
                                    # 如果去除后缀后是品牌名或其子串，则保留原始词（可能需要进一步处理）
                                    pass
                                elif len(potential_cleaned) >= len(brand_name) and brand_name in potential_cleaned:
                                    # 如果去除后缀后仍包含品牌名且长度足够，使用清理后的词
                                    cleaned_word = potential_cleaned
                                # 如果去除后缀后长度仍够大且不是品牌相关词，也使用清理后的词
                                elif len(potential_cleaned) >= 2 and potential_cleaned not in self.stop_words:
                                    cleaned_word = potential_cleaned
                                break  # 只处理第一个匹配的后缀

                        # 特别处理：如果清理后的词包含品牌名且比品牌名长，但以描述词结尾，则移除描述词
                        if brand_name in cleaned_word and len(cleaned_word) > len(brand_name):
                            # 检查是否以常见描述词结尾
                            for suffix in common_suffixes:
                                if cleaned_word.endswith(suffix) and len(cleaned_word) > len(suffix):
                                    potential_core = cleaned_word[:-len(suffix)]
                                    # 如果核心部分包含品牌名且长度合适，使用核心部分
                                    if brand_name in potential_core and len(potential_core) >= len(brand_name):
                                        cleaned_word = potential_core
                                    break

                        filtered_words.append(cleaned_word)
                    else:
                        filtered_words.append(clean_word)

        # 统计词频
        word_freq = Counter(filtered_words)

        # 返回所有过滤后的词（不仅仅是高频词），因为即使是单次出现的词也可能是重要的特征词
        unique_keywords = list(set(filtered_words))

        return unique_keywords
    
    def _generate_differentiation_summary(self, my_brand: str, competitor_brand: str,
                                        my_unique: List[str], competitor_unique: List[str],
                                        common: List[str]) -> str:
        """
        生成品牌差异总结

        Args:
            my_brand: 我方品牌
            competitor_brand: 竞品品牌
            my_unique: 我方独有关键词
            competitor_unique: 竞品独有关键词
            common: 共有关键词

        Returns:
            差异总结文本
        """
        summary_parts = []

        # 分析我方品牌的优势维度
        my_advantages = []
        for keyword in my_unique:
            if keyword in self.positive_indicators:
                my_advantages.append(keyword)

        # 分析竞品的优势维度
        competitor_advantages = []
        for keyword in competitor_unique:
            if keyword in self.positive_indicators:
                competitor_advantages.append(keyword)

        # 生成总结
        if competitor_advantages:
            summary_parts.append(f"{competitor_brand}在'{', '.join(competitor_advantages[:3])}'等维度更受AI青睐")

        if my_advantages:
            summary_parts.append(f"{my_brand}在'{', '.join(my_advantages[:3])}'维度有优势")

        # 如果我方优势但提及较少
        if my_advantages and len(my_unique) < len(competitor_unique):
            summary_parts.append("但声量不足")

        if not summary_parts:
            return f"在AI认知中，{my_brand}与{competitor_brand}在描述上各有侧重，未显示出明显差异。"

        return "，".join(summary_parts) + "。"
    
    def compare_brands_in_exposure_analysis(self, exposure_analysis: Dict, my_brand: str) -> Optional[Dict]:
        """
        在exposure_analysis结果中对比我方品牌与Top 1竞品
        
        Args:
            exposure_analysis: 露出分析结果
            my_brand: 我方品牌名称
            
        Returns:
            对比分析结果
        """
        # 获取排名列表，找到Top 1竞品（如果不是我方品牌的话）
        ranking_list = exposure_analysis.get('ranking_list', [])
        brand_details = exposure_analysis.get('brand_details', {})
        
        if not ranking_list or my_brand not in brand_details:
            return None
        
        # 找到Top 1品牌（排除我方品牌）
        top_competitor = None
        for brand in ranking_list:
            if brand != my_brand:
                top_competitor = brand
                break
        
        if not top_competitor or top_competitor not in brand_details:
            return None
        
        # 获取两个品牌的描述文本（从原始AI回复中提取，这里模拟）
        # 实际应用中需要从原始AI回复中提取对应品牌的描述部分
        my_brand_desc = self._extract_brand_description(exposure_analysis, my_brand)
        competitor_desc = self._extract_brand_description(exposure_analysis, top_competitor)
        
        # 执行对比分析
        return self.analyze(my_brand_desc, competitor_desc, my_brand, top_competitor)
    
    def _extract_brand_description(self, exposure_analysis: Dict, brand: str) -> str:
        """
        从露出分析结果中提取特定品牌的描述文本
        
        Args:
            exposure_analysis: 露出分析结果
            brand: 品牌名称
            
        Returns:
            该品牌的描述文本
        """
        # 这是一个模拟实现，实际应用中需要从原始AI回复中提取对应品牌的描述
        # 这里返回一个模拟的描述
        brand_detail = exposure_analysis.get('brand_details', {}).get(brand, {})
        word_count = brand_detail.get('word_count', 0)
        
        # 模拟生成品牌描述（实际应用中应从AI原始回复中提取）
        if word_count > 0:
            return f"{brand}的相关描述文本，包含{word_count}个字符的描述内容。"
        else:
            return f"{brand}的描述内容。"


# 示例使用
if __name__ == "__main__":
    analyzer = CompetitiveAnalyzer()
    
    # 示例文本
    my_brand_desc = "德施曼的智能锁技术领先，指纹识别算法先进，安全性高，用户体验良好。"
    competitor_desc = "小米的智能锁性价比突出，价格亲民，适合大众消费者，生态链完善。"
    
    # 执行分析
    result = analyzer.analyze(my_brand_desc, competitor_desc, "德施曼", "小米")
    
    print("共同关键词:", result['common_keywords'])
    print("我方独有关键词:", result['my_brand_unique_keywords'])
    print("竞品独有关键词:", result['competitor_unique_keywords'])
    print("差异总结:", result['differentiation_gap'])