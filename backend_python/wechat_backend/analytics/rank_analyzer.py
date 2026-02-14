"""
物理排位解析引擎 - 从AI回复中提取品牌排名、篇幅和拦截者信息
"""
import re
from typing import Dict, List, Tuple, Optional
from collections import OrderedDict


class RankAnalyzer:
    """
    物理排位解析引擎
    从AI原始回复文本中提取品牌排名、篇幅统计和拦截者信息
    输出符合exposure_analysis结构的数据
    """
    
    def __init__(self):
        # 品牌名称的前缀和后缀字符，用于边界检查
        self.brand_prefixes = ['"', '"', '“', '”', '《', '》', '(', ')', '（', '）', ' ', ',', '，', '、', ':', '：', ';', '；', '的', '是', '在', '有', '和', '与', '及', '但', '不过', '然而', '可是', '虽然', '尽管', '即使', '如果', '假如', '只要', '只有', '除了', '除非', '相比', '相对', '不同于', '不像']
        self.brand_suffixes = ['"', '"', '“', '”', '《', '》', '(', ')', '（', '）', ' ', ',', '，', '、', ':', '：', ';', '；', '.', '。', '!', '！', '?', '？', '的', '是', '在', '有', '和', '与', '及', '了', '着', '过', '等', '之', '与', '及', '也', '就', '都', '而', '及', '或', '但', '及', '呢', '吧', '啊', '呀', '哦', '嗯']
    
    def analyze(self, ai_response: str, brand_list: List[str]) -> Dict:
        """
        分析AI回复，提取露出与排位信息
        
        Args:
            ai_response: AI原始回复文本
            brand_list: 监控的品牌列表
            
        Returns:
            符合exposure_analysis结构的字典
        """
        # 1. 识别品牌排名列表
        ranking_list = self._extract_ranking_list(ai_response, brand_list)
        
        # 2. 统计各品牌详情
        brand_details = self._extract_brand_details(ai_response, brand_list)

        # 3. 识别未列出的竞争对手
        unlisted_competitors = self._identify_unlisted_competitors(ai_response, brand_list)

        return {
            'ranking_list': ranking_list,
            'brand_details': brand_details,
            'unlisted_competitors': unlisted_competitors
        }
    
    def _extract_ranking_list(self, ai_response: str, brand_list: List[str]) -> List[str]:
        """
        提取品牌在AI回复中的物理出现顺序
        
        Args:
            ai_response: AI回复文本
            brand_list: 监控品牌列表
            
        Returns:
            按首次出现顺序排列的品牌列表
        """
        # 创建一个列表来存储所有品牌的出现位置
        all_matches = []
        
        # 对品牌列表进行排序，优先匹配较长的品牌名称，避免短名称误匹配
        sorted_brands = sorted(brand_list, key=len, reverse=True)
        
        # 查找所有品牌的出现位置
        for brand in sorted_brands:
            # 查找品牌在文本中的所有出现位置
            text_lower = ai_response.lower()
            brand_lower = brand.lower()
            pos = 0
            
            while pos < len(text_lower):
                pos = text_lower.find(brand_lower, pos)
                if pos == -1:
                    break
                # 检查是否为有效边界内的匹配
                if self._is_valid_brand_boundary(ai_response, pos, pos + len(brand)):
                    # 检查是否与已有的匹配重叠
                    is_overlapping = False
                    for start, end, existing_brand in all_matches:
                        if not (pos + len(brand) <= start or pos >= end):
                            # 如果重叠，保留较长的品牌名
                            if len(brand) > len(existing_brand):
                                # 替换较短的品牌
                                all_matches = [m for m in all_matches if m[2] != existing_brand]
                                all_matches.append((pos, pos + len(brand), brand))
                            is_overlapping = True
                            break
                    if not is_overlapping:
                        all_matches.append((pos, pos + len(brand), brand))
                pos += 1
        
        # 按起始位置排序
        all_matches.sort(key=lambda x: x[0])
        
        # 去除重叠的匹配（优先保留较长的匹配）
        non_overlapping_matches = []
        for start, end, brand in all_matches:
            # 检查是否与已有匹配重叠
            overlaps = False
            for existing_start, existing_end, _ in non_overlapping_matches:
                if not (end <= existing_start or start >= existing_end):
                    overlaps = True
                    break
            if not overlaps:
                non_overlapping_matches.append((start, end, brand))
        
        # 按位置排序，返回品牌列表
        non_overlapping_matches.sort(key=lambda x: x[0])
        result = [match[2] for match in non_overlapping_matches]
        
        return result
    
    def _is_valid_brand_boundary(self, text: str, start_pos: int, end_pos: int) -> bool:
        """
        检查品牌名称是否在有效边界内（支持中英文混合）

        Args:
            text: 要检查的文本
            start_pos: 品牌开始位置
            end_pos: 品牌结束位置

        Returns:
            边界是否有效
        """
        # 检查开始边界
        start_ok = start_pos == 0 or text[start_pos - 1].lower() in [c.lower() for c in self.brand_prefixes]

        # 检查结束边界
        if end_pos >= len(text):
            end_ok = True
        else:
            next_char = text[end_pos].lower()
            end_ok = next_char in [c.lower() for c in self.brand_suffixes]

            # 如果品牌是纯英文字母，允许后面跟非英文字母数字字符作为边界
            brand_text = text[start_pos:end_pos]
            if brand_text.isalpha() and brand_text.isascii():  # 纯英文字母
                # 英文品牌后面可以跟任何非英文字母数字字符作为边界
                end_ok = end_ok or (not next_char.isascii() or not next_char.isalnum())
            else:
                # 对于中文品牌，我们采用更宽松的策略
                # 在中文语境中，品牌名称后面跟着描述词是非常常见的，如"小米手机"、"小米性价比高"
                # 所以我们默认接受匹配，除非是明显的部分匹配情况
                # 例如，"小明科技"中的"小明"，我们需要避免这种情况
                
                # 检查是否是明显的部分匹配（如"小明科技"中的"小明"）
                # 这种情况下，品牌名称后面紧跟另一个中文词，且该词是常见的公司后缀
                company_suffixes = ['科技', '公司', '集团', '股份', '有限', '责任', '厂', '店', '行', '社', '会', '机构', '企业', '网', '在线', '商城', '超市', '连锁']

                # 检查后面是否跟着公司后缀
                remaining_text = text[end_pos:end_pos+4]  # 检查后面最多4个字符
                is_company_suffix = any(remaining_text.startswith(suffix) for suffix in company_suffixes)

                if is_company_suffix:
                    # 如果是公司后缀，这可能是部分匹配，不接受
                    end_ok = False
                else:
                    # 对于其他情况，我们接受匹配，因为品牌后跟描述词是常见情况
                    end_ok = True

        return start_ok and end_ok
    
    def _extract_brand_details(self, ai_response: str, brand_list: List[str]) -> Dict:
        """
        提取各品牌的详细信息（排名、字数、篇幅占比、情感分数）
        
        Args:
            ai_response: AI回复文本
            brand_list: 监控品牌列表
            
        Returns:
            包含各品牌详情的字典
        """
        brand_details = {}
        ranking_list = self._extract_ranking_list(ai_response, brand_list)
        total_length = len(ai_response)
        
        for idx, brand in enumerate(ranking_list):
            # 计算品牌描述的字符长度
            word_count = self._calculate_brand_word_count(ai_response, brand)
            
            # 计算篇幅占比
            sov_share = round(word_count / total_length, 4) if total_length > 0 else 0.0
            
            # 获取排名（从1开始）
            rank = idx + 1
            
            # 情感分数暂时设为默认值，实际应用中可以从AI判断模块获取
            sentiment_score = 50  # 默认中性分数
            
            brand_details[brand] = {
                'rank': rank,
                'word_count': word_count,
                'sov_share': sov_share,
                'sentiment_score': sentiment_score
            }
        
        # 为没有在回复中出现的品牌也添加记录
        for brand in brand_list:
            if brand not in brand_details:
                brand_details[brand] = {
                    'rank': -1,  # 表示未出现
                    'word_count': 0,
                    'sov_share': 0.0,
                    'sentiment_score': 50
                }
        
        return brand_details
    
    def _calculate_brand_word_count(self, ai_response: str, brand: str) -> int:
        """
        计算AI回复中特定品牌的描述字符长度
        
        Args:
            ai_response: AI回复文本
            brand: 品牌名称
            
        Returns:
            该品牌相关描述的字符长度
        """
        # 找到品牌在文本中的所有出现位置
        positions = self._find_all_brand_positions(ai_response, brand)
        
        if not positions:
            return 0
        
        # 计算每个出现位置周围的上下文长度
        total_count = 0
        processed_ranges = []  # 已处理的范围，避免重复计算
        
        for pos in positions:
            # 定义上下文范围（向前和向后搜索句子边界）
            start_idx = self._find_sentence_start(ai_response, pos)
            end_idx = self._find_sentence_end(ai_response, pos + len(brand))
            
            # 检查是否与已处理的范围重叠
            overlap = False
            for existing_start, existing_end in processed_ranges:
                if not (end_idx <= existing_start or start_idx >= existing_end):
                    overlap = True
                    # 如果有重叠，只计算未重叠的部分
                    actual_start = max(start_idx, existing_end)
                    actual_end = min(end_idx, existing_start)
                    if actual_start < actual_end:
                        total_count += actual_end - actual_start
                    break
            
            if not overlap:
                # 计算从品牌开始到句子结束的字符数
                brand_context = ai_response[pos:end_idx]
                total_count += len(brand_context)
                processed_ranges.append((start_idx, end_idx))
        
        return total_count
    
    def _find_all_brand_positions(self, text: str, brand: str) -> List[int]:
        """
        查找品牌在文本中的所有出现位置

        Args:
            text: 要搜索的文本
            brand: 要查找的品牌名称

        Returns:
            品牌出现位置的列表
        """
        positions = []
        text_lower = text.lower()
        brand_lower = brand.lower()

        pos = 0
        while pos < len(text_lower):
            pos = text_lower.find(brand_lower, pos)
            if pos == -1:
                break

            # 检查品牌名称是否在有效边界内
            if self._is_valid_brand_boundary(text, pos, pos + len(brand_lower)):
                # 额外检查：避免部分匹配，如在"小明明"中匹配到"小明"
                # 检查匹配的字符串是否完全等于我们要找的品牌名
                matched_text = text[pos:pos + len(brand)]
                if matched_text == brand:
                    positions.append(pos)

            pos += 1

        return positions
    
    def _find_sentence_start(self, text: str, pos: int) -> int:
        """
        从指定位置向前查找句子开始位置
        
        Args:
            text: 文本
            pos: 起始位置
            
        Returns:
            句子开始位置
        """
        # 向前查找句号、感叹号、问号等标点符号
        for i in range(pos, -1, -1):
            if i < len(text) and text[i] in ['.', '。', '!', '！', '?', '？', ';', '；', '\n', '\r', '，', '，']:
                return i + 1
        return 0
    
    def _find_sentence_end(self, text: str, pos: int) -> int:
        """
        从指定位置向后查找句子结束位置
        
        Args:
            text: 文本
            pos: 起始位置
            
        Returns:
            句子结束位置
        """
        # 向后查找句号、感叹号、问号等句子结束标点符号
        for i in range(pos, len(text)):
            if text[i] in ['.', '。', '!', '！', '?', '？', '\n', '\r']:
                return i + 1  # 返回句子结束标点符号之后的位置
        return len(text)
    
    def _identify_unlisted_competitors(self, ai_response: str, brand_list: List[str]) -> List[str]:
        """
        识别AI回复中出现但不在监控列表中的潜在竞争对手
        
        Args:
            ai_response: AI回复文本
            brand_list: 监控品牌列表
            
        Returns:
            未列出的竞争对手列表
        """
        # 首先将已知品牌从文本中移除，避免重复识别
        processed_text = ai_response
        for brand in sorted(brand_list, key=len, reverse=True):
            # 使用正则表达式替换，忽略大小写
            processed_text = re.sub(re.escape(brand), '', processed_text, flags=re.IGNORECASE)

        # 定义可能表示品牌的常见模式
        # 这里使用一些常见的品牌特征词作为示例，实际应用中可能需要更复杂的NLP处理
        potential_competitor_patterns = [
            r'(?:^|[^a-zA-Z])([A-Z][a-z]+(?:[A-Z][a-z]*)+)(?:[^a-zA-Z]|$)',  # 驼峰式命名
            r'(?:^|[^a-zA-Z])([A-Z]{2,})(?:[^a-zA-Z]|$)',  # 全大写字母缩写
            r'(?:^|[^a-zA-Z])([A-Z][a-z]+(?:\s+[A-Z][a-z]*)+)(?:[^a-zA-Z]|$)',  # 多词品牌名
        ]

        unlisted_competitors = set()

        # 搜索潜在的竞争者
        for pattern in potential_competitor_patterns:
            matches = re.findall(pattern, processed_text)
            for match in matches:
                # 清理匹配结果
                clean_match = match.strip()
                if len(clean_match) > 1 and clean_match not in brand_list and clean_match not in unlisted_competitors:  # 避免单字符匹配和重复
                    unlisted_competitors.add(clean_match)

        # 另一种方法：查找在描述产品质量、特点时提到的其他品牌
        # 例如："相比之下，XXX做得更好"，"不像YYY那样..."，"但XXX的..."
        contrast_pattern = r'(?:相比|相对|不同于|不像|除了|但|然而|不过)\s*([A-Za-z\u4e00-\u9fa5]+)[\u4e00-\u9fa5]*\s*(?:的|是|在|有|比)'
        contrast_matches = re.findall(contrast_pattern, processed_text)
        for match in contrast_matches:
            clean_match = match.strip()
            if len(clean_match) > 1 and clean_match not in brand_list and clean_match not in unlisted_competitors:
                unlisted_competitors.add(clean_match)

        # 更通用的方法：查找中文品牌名称（连续的中文字符）
        # 匹配2-4个连续的中文字符，这通常是品牌名称的长度
        chinese_brand_pattern = r'[\u4e00-\u9fa5]{2,4}'
        chinese_matches = re.findall(chinese_brand_pattern, processed_text)
        for match in chinese_matches:
            clean_match = match.strip()
            # 检查是否是品牌名称而不是普通词汇
            if len(clean_match) >= 2 and clean_match not in brand_list and clean_match not in unlisted_competitors:
                # 检查是否是常见的非品牌词，避免误判
                common_non_brand_words = ['不错', '更好', '更有', '很', '比较', '相对', '但是', '不过', '然而', '所以', '因为', '如果', '虽然', '这个', '那个', '这些', '那些', '什么', '怎么', '为什么', '怎么样', '如何', '可以', '能够', '应该', '需要', '想要', '希望', '觉得', '认为', '知道', '明白', '理解', '了解', '学习', '工作', '生活', '时间', '地方', '事情', '问题', '答案', '方法', '方式', '技术', '产品', '服务', '公司', '用户', '客户', '市场', '销售', '价格', '质量', '功能', '性能', '特点', '优势', '劣势', '优点', '缺点', '好处', '坏处', '影响', '效果', '结果', '目标', '目的', '意义', '价值', '重要', '必要', '可能', '也许', '大概', '大约', '左右', '附近', '周围', '里面', '外面', '前面', '后面', '左边', '右边', '上面', '下面', '中间', '中央', '旁边', '附近', '的', '是', '在', '有', '和', '与', '及', '了', '着', '过', '等', '之', '与', '及', '也', '就', '都', '而', '及', '或', '但', '及', '用户体验', '产品', '功能', '性能', '质量', '服务', '售后', '品质', '设计', '外观', '材料', '工艺', '技术', '创新', '安全', '可靠', '稳定', '耐用', '易用', '便捷', '智能', '高效', '节能', '环保', '健康', '舒适', '美观', '时尚', '潮流', '经典', '独特', '个性', '定制', '专业', '专家', '权威', '标准', '认证', '专利', '商标', '版权', '品牌', '名牌', '老字号', '新兴', '初创', '成长', '发展', '扩张', '盈利', '收益', '回报', '投资', '成本', '价格', '性价比', '优惠', '折扣', '促销', '活动', '营销', '推广', '宣传', '广告', '公关', '传播', '曝光', '知名度', '声誉', '信誉', '口碑', '评价', '评分', '星级', '推荐', '好评', '差评', '投诉', '反馈', '建议', '意见', '看法', '观点', '态度', '情绪', '情感', '感觉', '感受', '印象', '认知', '认识', '熟悉', '陌生', '新鲜', '新颖', '传统', '现代', '当代', '古典', '复古', '未来', '科学', '艺术', '文化', '教育', '培训', '学习', '知识', '智慧', '经验', '技能', '能力', '素质', '品格', '道德', '伦理', '法律', '法规', '政策', '制度', '规则', '秩序', '纪律', '自由', '民主', '平等', '公正', '公平', '正义', '和平', '战争', '冲突', '竞争', '合作', '团结', '友谊', '爱情', '亲情', '友情', '家庭', '社会', '国家', '世界', '宇宙', '自然', '地球', '太阳', '月亮', '星星', '天空', '海洋', '河流', '湖泊', '山川', '森林', '草原', '沙漠', '城市', '乡村', '农村', '农业', '工业', '商业', '服务业', '制造业', '建筑业', '交通运输', '通信', '能源', '水利', '环保', '医疗', '卫生', '体育', '娱乐', '旅游', '餐饮', '住宿', '购物', '金融', '保险', '证券', '房地产', '电信', '邮政', '电力', '燃气', '供水', '供热', '绿化', '清洁', '垃圾', '废物', '回收', '处理', '防治', '保护', '维护', '管理', '监督', '控制', '调节', '平衡', '协调', '统一', '分散', '集中', '分布', '布局', '结构', '组成', '构成', '要素', '成分', '部分', '整体', '个体', '集体', '群体', '组织', '机构', '团体', '协会', '学会', '联盟', '工会', '政党', '政府', '议会', '法院', '检察院', '警察', '军队', '国防', '外交', '内政', '政治', '经济', '财政', '税收', '货币', '银行', '信贷', '储蓄', '贷款', '投资', '消费', '生产', '供应', '需求', '交易', '买卖', '交换', '贸易', '商务', '合同', '协议', '条款', '规定', '约定', '承诺', '保证', '担保', '抵押', '质押', '租赁', '承包', '委托', '代理']
                if clean_match not in common_non_brand_words:
                    # 检查是否出现在特定的上下文中，表明它可能是品牌
                    # 如"XXX的用户体验"、"XXX也很有竞争力"等
                    # 但要确保不是在句子中间的普通词汇
                    context_patterns = [
                        # 在对比结构中，如"相比之下，XXX做得更好"、"但XXX的用户体验更好"
                        r'(?:相比|相对|不同于|不像|除了|但|然而|不过|可是|但是)\s*' + re.escape(clean_match) + r'\s*(?:的|是|在|有|比|也|很|非常|特别|相当|尤其|尤其|而且|并且|还|又|更|最)',
                        # 在"XXX也"、"XXX很"等结构中
                        r'' + re.escape(clean_match) + r'\s*(?:也|很|非常|特别|相当|尤其|尤其|而且|并且|还|又|更|最)',
                        # 在"XXX的YYY"结构中，其中YYY是描述词
                        r'' + re.escape(clean_match) + r'\s*的\s*(?:用户体验|产品|服务|技术|功能|性能|质量|口碑|品牌|公司|智能锁|手机|电脑|汽车|手表|耳机|音响|电视|冰箱|空调|洗衣机|路由器|软件|应用|平台|网站|商城|超市|店铺|工厂|制造商|供应商|代理商|经销商|智能锁|手机|电脑|汽车|手表|耳机|音响|电视|冰箱|空调|洗衣机|路由器|软件|应用|平台|网站|商城|超市|店铺|工厂|制造商|供应商|代理商|经销商)',
                    ]

                    # 检查是否匹配任一上下文模式
                    found_in_context = any(re.search(pattern, processed_text) for pattern in context_patterns)

                    # 如果在特定上下文中找到，或者是知名品牌，则认为是品牌
                    if found_in_context:
                        unlisted_competitors.add(clean_match)
                    else:
                        # 检查是否是知名品牌
                        known_brands = ['鹿客', 'TCL', '华为', '苹果', '三星', 'OPPO', 'vivo', '一加', '魅族', '索尼', '松下', '西门子', '飞利浦', '美的', '格力', '海尔', '联想', '戴尔', '惠普', '华硕', '宏碁', '佳能', '尼康', '比亚迪', '吉利', '长城', '奇瑞', '蔚来', '小鹏', '理想', '特斯拉', '宝马', '奔驰', '奥迪', '大众', '丰田', '本田', '小米', '荣耀', '海信', '创维', '长虹']
                        if clean_match in known_brands:
                            unlisted_competitors.add(clean_match)

        return list(unlisted_competitors)


# 示例使用
if __name__ == "__main__":
    analyzer = RankAnalyzer()

    # 示例AI回复
    sample_response = """
    在智能锁领域，德施曼一直表现不错，其指纹识别技术较为先进。
    小米的智能锁性价比高，适合大众消费者。
    凯迪仕也有一定的市场份额，特别是在工程渠道。
    相比之下，鹿客在用户体验方面做得更好。
    TCL也很有竞争力。
    """
    
    # 监控品牌列表
    brands = ["德施曼", "小米", "凯迪仕"]

    # 执行分析
    result = analyzer.analyze(sample_response, brands)

    print("排名列表:", result['ranking_list'])
    print("品牌详情:", result['brand_details'])
    print("未列出的竞争对手:", result['unlisted_competitors'])