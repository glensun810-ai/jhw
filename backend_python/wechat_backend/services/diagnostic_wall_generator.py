"""
问题诊断墙生成器

基于评分维度结果，生成问题诊断墙，包括：
1. 高风险问题（需立即关注）
2. 中风险问题（需要优化）
3. 优化建议（按优先级排序）

作者：首席架构师
日期：2026-03-22
版本：1.0
"""

from typing import Dict, Any, List


class DiagnosticWallGenerator:
    """问题诊断墙生成器"""
    
    # 高风险识别规则
    HIGH_RISK_RULES = {
        'low_rank': {
            'id': 'RISK-001',
            'threshold': 40,
            'title': '排名严重落后',
            'description': '您的品牌在 AI 回答中排名第{position}位，落后于主要竞品',
            'metric_key': 'rank_score',
            'recommendation': {
                'id': 'REC-001',
                'content': '提升物理排名：加强在权威渠道（知乎、百度百科、行业网站）的品牌曝光，确保 AI 训练数据中品牌排名靠前',
                'expected_impact': '高',
                'difficulty': '中'
            }
        },
        'low_sov': {
            'id': 'RISK-002',
            'threshold': 40,
            'title': '声量份额过低',
            'description': '您的品牌在 AI 回答中的声量份额仅{sov}%，远低于行业平均水平',
            'metric_key': 'sov_score',
            'recommendation': {
                'id': 'REC-002',
                'content': '增加声量份额：创作更多品牌相关内容，覆盖更多测试问题场景，提升 AI 回答中的篇幅占比',
                'expected_impact': '高',
                'difficulty': '中'
            }
        },
        'low_visibility': {
            'id': 'RISK-003',
            'threshold': 60,
            'title': '品牌未被充分识别',
            'description': 'AI 对您的品牌提及不足，可能影响用户认知',
            'metric_key': 'visibility_score',
            'recommendation': {
                'id': 'REC-003',
                'content': '增强品牌识别：优化品牌关键词布局，确保 AI 能准确识别和提取品牌信息',
                'expected_impact': '高',
                'difficulty': '低'
            }
        },
        'negative_sentiment': {
            'id': 'RISK-004',
            'threshold': 40,
            'title': '负面评价风险',
            'description': 'AI 回答中对您的品牌存在负面或谨慎评价',
            'metric_key': 'sentiment_score',
            'recommendation': {
                'id': 'REC-004',
                'content': '改善情感倾向：监测并处理负面评价源头，增加正面用户案例和权威背书',
                'expected_impact': '高',
                'difficulty': '高'
            }
        },
        'low_overall': {
            'id': 'RISK-005',
            'threshold': 60,
            'title': '整体表现不佳',
            'description': '您的品牌在 AI 认知中处于明显劣势',
            'metric_key': 'overall_score',
            'recommendation': {
                'id': 'REC-005',
                'content': '综合 GEO 优化：制定系统的生成式引擎优化策略，全面提升 AI 认知表现',
                'expected_impact': '高',
                'difficulty': '高'
            }
        }
    }
    
    # 中风险识别规则
    MEDIUM_RISK_RULES = {
        'rank_room': {
            'id': 'RISK-101',
            'min_threshold': 40,
            'max_threshold': 60,
            'title': '排名有提升空间',
            'description': '您的品牌排名第{position}位，与第 1 名差距较小，有机会超越',
            'metric_key': 'rank_score',
            'recommendation': {
                'id': 'REC-101',
                'content': '缩小排名差距：分析排名第 1 品牌的优势，针对性加强内容建设',
                'expected_impact': '中',
                'difficulty': '中'
            }
        },
        'sov_medium': {
            'id': 'RISK-102',
            'min_threshold': 40,
            'max_threshold': 60,
            'title': '声量份额中等',
            'description': '您的品牌声量份额{sov}%，处于行业中等水平',
            'metric_key': 'sov_score',
            'recommendation': {
                'id': 'REC-102',
                'content': '扩大声量优势：在现有基础上进一步增加高质量内容产出',
                'expected_impact': '中',
                'difficulty': '中'
            }
        },
        'visibility_medium': {
            'id': 'RISK-103',
            'min_threshold': 60,
            'max_threshold': 80,
            'title': '品牌可见度一般',
            'description': 'AI 对您的品牌描述篇幅适中，可增加曝光',
            'metric_key': 'visibility_score',
            'recommendation': {
                'id': 'REC-103',
                'content': '优化提及位置：确保品牌信息在 AI 回答的前半部分出现',
                'expected_impact': '中',
                'difficulty': '低'
            }
        },
        'sentiment_neutral': {
            'id': 'RISK-104',
            'min_threshold': 40,
            'max_threshold': 60,
            'title': '情感倾向中性',
            'description': 'AI 对您的品牌评价较为中性，缺乏突出亮点',
            'metric_key': 'sentiment_score',
            'recommendation': {
                'id': 'REC-104',
                'content': '强化正面认知：突出品牌独特卖点和用户好评',
                'expected_impact': '中',
                'difficulty': '中'
            }
        },
        'inconsistency': {
            'id': 'RISK-105',
            'threshold': 60,
            'title': '评价不一致',
            'description': '不同 AI 平台对您品牌的评价差异较大',
            'metric_key': 'cross_platform_consistency',
            'recommendation': {
                'id': 'REC-105',
                'content': '统一品牌形象：确保各渠道品牌信息一致性，减少 AI 认知偏差',
                'expected_impact': '中',
                'difficulty': '中'
            }
        }
    }
    
    # 低优先级建议（通用持续优化）
    LOW_PRIORITY_RECOMMENDATIONS = [
        {
            'id': 'REC-201',
            'content': '定期监测：建立 GEO 监测机制，定期追踪品牌在 AI 中的表现',
            'expected_impact': '低',
            'difficulty': '低'
        },
        {
            'id': 'REC-202',
            'content': '竞品对标：持续监控竞品在 AI 中的表现，及时调整策略',
            'expected_impact': '低',
            'difficulty': '低'
        },
        {
            'id': 'REC-203',
            'content': '内容迭代：根据 AI 回答特点，持续优化内容策略',
            'expected_impact': '低',
            'difficulty': '低'
        }
    ]
    
    def generate(
        self,
        visibility_score: int,
        rank_score: int,
        sov_score: int,
        sentiment_score: int,
        overall_score: int,
        cross_platform_consistency: int = 100,
        detailed_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成问题诊断墙
        
        参数:
        - visibility_score: 可见度得分 (0-100)
        - rank_score: 排位得分 (0-100)
        - sov_score: 声量得分 (0-100)
        - sentiment_score: 情感得分 (0-100)
        - overall_score: 综合得分 (0-100)
        - cross_platform_consistency: 跨平台一致性得分 (0-100)
        - detailed_data: 详细数据（排名、SOV%、情感词等）
        
        返回:
        {
            "high_risks": [...],
            "medium_risks": [...],
            "recommendations": [...]
        }
        """
        if detailed_data is None:
            detailed_data = {}
        
        high_risks = []
        medium_risks = []
        recommendations = []
        
        # 构建得分数典
        scores = {
            'visibility_score': visibility_score,
            'rank_score': rank_score,
            'sov_score': sov_score,
            'sentiment_score': sentiment_score,
            'overall_score': overall_score,
            'cross_platform_consistency': cross_platform_consistency
        }
        
        # ========== 高风险识别 ==========
        for risk_key, rule in self.HIGH_RISK_RULES.items():
            metric_key = rule['metric_key']
            threshold = rule['threshold']
            current_score = scores.get(metric_key, 100)
            
            # 检查是否触发高风险（得分低于阈值）
            if current_score < threshold:
                risk_info = self._create_risk_info(
                    rule=rule,
                    score=current_score,
                    detailed_data=detailed_data,
                    risk_level='high'
                )
                high_risks.append(risk_info)
                
                # 添加对应的高优先级建议
                recommendations.append({
                    'priority': 'high',
                    **rule['recommendation']
                })
        
        # ========== 中风险识别 ==========
        for risk_key, rule in self.MEDIUM_RISK_RULES.items():
            metric_key = rule['metric_key']
            current_score = scores.get(metric_key, 100)
            
            # 检查是否触发中风险
            is_triggered = False
            
            if 'min_threshold' in rule and 'max_threshold' in rule:
                # 区间判断（得分在阈值范围内）
                is_triggered = rule['min_threshold'] <= current_score < rule['max_threshold']
            elif 'threshold' in rule:
                # 单阈值判断（得分低于阈值但高于高风险阈值）
                high_risk_threshold = self.HIGH_RISK_RULES.get(
                    risk_key.replace('_medium', '').replace('_room', ''),
                    {}
                ).get('threshold', 0)
                is_triggered = high_risk_threshold <= current_score < rule['threshold']
            
            if is_triggered:
                risk_info = self._create_risk_info(
                    rule=rule,
                    score=current_score,
                    detailed_data=detailed_data,
                    risk_level='medium'
                )
                medium_risks.append(risk_info)
                
                # 添加对应的中优先级建议
                recommendations.append({
                    'priority': 'medium',
                    **rule['recommendation']
                })
        
        # ========== 建议去重和排序 ==========
        # 按优先级排序：high > medium > low
        # 同优先级内按预期影响排序
        recommendations = self._sort_and_deduplicate_recommendations(recommendations)
        
        # 如果没有高风险或中风险，添加通用建议
        if not high_risks and not medium_risks:
            # 表现良好，添加鼓励性建议
            if overall_score >= 80:
                maintenance_rec = {
                    'priority': 'low',
                    'id': 'REC-301',
                    'content': '保持优势：继续维护当前的 GEO 表现，定期监测防止下滑',
                    'expected_impact': '低',
                    'difficulty': '低'
                }
                recommendations.append(maintenance_rec)
            
            # 添加通用持续优化建议
            for rec in self.LOW_PRIORITY_RECOMMENDATIONS:
                recommendations.append({
                    'priority': 'low',
                    **rec
                })
        
        # 限制建议数量（最多 5 条）
        recommendations = recommendations[:5]
        
        return {
            'high_risks': high_risks,
            'medium_risks': medium_risks,
            'recommendations': recommendations,
            'summary': self._generate_summary(
                overall_score, 
                len(high_risks), 
                len(medium_risks)
            )
        }
    
    def _create_risk_info(
        self,
        rule: Dict[str, Any],
        score: int,
        detailed_data: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """
        创建风险信息对象
        
        参数:
        - rule: 风险规则
        - score: 当前得分
        - detailed_data: 详细数据
        - risk_level: 风险等级 (high/medium)
        
        返回:
        - 风险信息字典
        """
        # 填充描述模板
        description = rule['description']
        
        # 替换占位符
        if '{position}' in description:
            position = detailed_data.get('position', 0)
            description = description.replace('{position}', str(position))
        
        if '{sov}' in description:
            sov = detailed_data.get('sov', 0)
            description = description.replace('{sov}', str(sov))
        
        if '{word_count}' in description:
            word_count = detailed_data.get('word_count', 0)
            description = description.replace('{word_count}', str(word_count))
        
        if '{avg_word_count}' in description:
            avg_word_count = detailed_data.get('avg_word_count', 0)
            description = description.replace('{avg_word_count}', str(avg_word_count))
        
        if '{sentiment}' in description:
            sentiment = detailed_data.get('sentiment', 0)
            description = description.replace('{sentiment}', str(sentiment))
        
        if '{gap_to_first}' in description:
            gap = detailed_data.get('gap_to_first', 0)
            description = description.replace('{gap_to_first}', str(gap))
        
        if '{top_sov}' in description:
            top_sov = detailed_data.get('top_sov', 0)
            description = description.replace('{top_sov}', str(top_sov))
        
        # 构建数据支撑
        data_support = {
            'score': score,
            'threshold': rule.get('threshold', rule.get('max_threshold', 0))
        }
        
        # 添加详细数据支撑
        if rule['metric_key'] == 'rank_score':
            data_support['position'] = detailed_data.get('position', 0)
            data_support['competitor_positions'] = detailed_data.get('competitor_ranks', {})
        elif rule['metric_key'] == 'sov_score':
            data_support['sov_percentage'] = detailed_data.get('sov', 0)
            data_support['industry_average'] = 25
        elif rule['metric_key'] == 'visibility_score':
            data_support['word_count'] = detailed_data.get('word_count', 0)
            data_support['average'] = detailed_data.get('avg_word_count', 0)
        elif rule['metric_key'] == 'sentiment_score':
            data_support['sentiment_polarity'] = detailed_data.get('sentiment', 0)
            data_support['positive_keywords'] = detailed_data.get('positive_keywords', [])
            data_support['negative_keywords'] = detailed_data.get('negative_keywords', [])
        elif rule['metric_key'] == 'cross_platform_consistency':
            data_support['consistency_score'] = score
        
        return {
            'type': rule['id'],
            'level': risk_level,
            'title': rule['title'],
            'description': description,
            'score': score,
            'data_support': data_support
        }
    
    def _sort_and_deduplicate_recommendations(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        建议排序和去重
        
        参数:
        - recommendations: 建议列表
        
        返回:
        - 排序去重后的建议列表
        """
        # 按优先级排序：high > medium > low
        # 同优先级内按预期影响排序：高 > 中 > 低
        def sort_key(rec):
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            impact_order = {'高': 0, '中': 1, '低': 2}
            
            priority = priority_order.get(rec.get('priority', 'low'), 2)
            impact = impact_order.get(rec.get('expected_impact', '低'), 2)
            
            return (priority, impact)
        
        recommendations.sort(key=sort_key)
        
        # 去重（同类型建议只保留 1 条）
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            rec_id = rec.get('id', '')
            if rec_id not in seen_ids:
                seen_ids.add(rec_id)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _generate_summary(
        self,
        overall_score: int,
        high_risk_count: int,
        medium_risk_count: int
    ) -> Dict[str, Any]:
        """
        生成诊断摘要
        
        参数:
        - overall_score: 综合得分
        - high_risk_count: 高风险数量
        - medium_risk_count: 中风险数量
        
        返回:
        - 摘要字典
        """
        # 确定等级
        if overall_score >= 90:
            grade = 'S'
            grade_text = '优秀'
            grade_description = '在 AI 认知中占据绝对优势'
        elif overall_score >= 80:
            grade = 'A'
            grade_text = '良好'
            grade_description = '在 AI 认知中表现较好'
        elif overall_score >= 70:
            grade = 'B'
            grade_text = '中等'
            grade_description = '在 AI 认知中表现一般'
        elif overall_score >= 60:
            grade = 'C'
            grade_text = '及格'
            grade_description = '在 AI 认知中存在感偏弱'
        else:
            grade = 'D'
            grade_text = '较差'
            grade_description = '在 AI 认知中处于劣势'
        
        # 生成总体评价
        if high_risk_count > 0:
            overall_comment = f'存在{high_risk_count}个高风险问题，需要立即关注和处理'
        elif medium_risk_count > 0:
            overall_comment = f'存在{medium_risk_count}个中风险问题，建议优化改进'
        else:
            overall_comment = '表现良好，继续保持并定期监测'
        
        return {
            'grade': grade,
            'grade_text': grade_text,
            'grade_description': grade_description,
            'overall_score': overall_score,
            'high_risk_count': high_risk_count,
            'medium_risk_count': medium_risk_count,
            'overall_comment': overall_comment
        }
    
    def generate_for_multiple_brands(
        self,
        brand_scores: Dict[str, Dict[str, int]],
        main_brand: str
    ) -> Dict[str, Any]:
        """
        为多品牌对比生成诊断墙
        
        参数:
        - brand_scores: {品牌名：{各维度得分}}
        - main_brand: 主品牌名
        
        返回:
        - 诊断墙结果
        """
        if main_brand not in brand_scores:
            return {
                'high_risks': [],
                'medium_risks': [],
                'recommendations': [],
                'summary': {'error': '主品牌不在评分数据中'}
            }
        
        main_scores = brand_scores[main_brand]
        
        return self.generate(
            visibility_score=main_scores.get('visibility_score', 0),
            rank_score=main_scores.get('rank_score', 0),
            sov_score=main_scores.get('sov_score', 0),
            sentiment_score=main_scores.get('sentiment_score', 0),
            overall_score=main_scores.get('overall_score', 0),
            cross_platform_consistency=main_scores.get('cross_platform_consistency', 100),
            detailed_data={
                'position': main_scores.get('rank', 0),
                'sov': main_scores.get('sov_percentage', 0),
                'competitor_scores': {
                    brand: scores.get('overall_score', 0)
                    for brand, scores in brand_scores.items()
                    if brand != main_brand
                }
            }
        )
