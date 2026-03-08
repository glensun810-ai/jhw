"""
报告聚合器 - ReportAggregator

核心职责：
1. 聚合所有诊断结果为战略看板数据结构
2. 计算品牌分数、SOV、风险评分
3. 生成品牌洞察文本
4. 整合后台分析结果

设计原则：
1. 与前端 reportAggregator.js 保持逻辑一致
2. 支持完整的品牌诊断指标计算
3. 提供可扩展的架构，便于添加新指标

@author: 系统架构组
@date: 2026-03-04
@version: 1.0.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from wechat_backend.logging_config import api_logger


class ReportAggregator:
    """
    报告聚合器 - Python 后端实现
    
    职责：
    1. 聚合所有诊断结果为战略看板数据结构
    2. 计算品牌分数、SOV、风险评分
    3. 生成品牌洞察文本
    4. 整合后台分析结果
    """
    
    # 分数等级映射
    GRADE_MAPPING = {
        90: 'A+',
        80: 'A',
        70: 'B',
        60: 'C',
        0: 'D'
    }
    
    # 分数描述映射
    SCORE_SUMMARY = {
        90: '表现卓越',
        80: '表现良好',
        70: '表现一般',
        60: '有待提升',
        0: '需要改进'
    }
    
    def __init__(self):
        """初始化报告聚合器"""
        api_logger.debug("[ReportAggregator] 初始化完成")
    
    def aggregate(
        self,
        raw_results: List[Dict[str, Any]],
        brand_name: str,
        competitors: List[str],
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        聚合品牌诊断报告
        
        参数：
            raw_results: 原始诊断结果列表
            brand_name: 主品牌名称
            competitors: 竞品列表
            additional_data: 额外数据（语义偏移、推荐等）
            
        返回：
            聚合后的报告数据
        """
        api_logger.info(
            f"[ReportAggregator] 开始聚合报告：brand={brand_name}, "
            f"results={len(raw_results)}, competitors={len(competitors)}"
        )
        
        # 1. 数据清洗
        cleaned_results = self._sanitize_results(raw_results)
        filled_results = self._fill_missing_data(cleaned_results, brand_name)
        
        # 2. 计算品牌分数
        brand_scores = self._calculate_brand_scores(
            filled_results, brand_name, competitors
        )
        
        # 3. 计算 SOV (Share of Voice)
        sov_data = self._calculate_sov(filled_results, brand_name, competitors)
        
        # 4. 计算风险评分
        risk_data = self._calculate_risk(filled_results, brand_name)
        
        # 5. 品牌健康度
        health_data = self._calculate_brand_health(
            brand_scores.get(brand_name, {})
        )
        
        # 6. 生成洞察文本
        insights = self._generate_insights(
            brand_scores.get(brand_name, {}),
            brand_name
        )
        
        # 7. 计算首次提及率
        first_mention_data = self._calculate_first_mention_by_platform(filled_results)
        
        # 8. 计算拦截风险
        interception_risks = self._calculate_interception_risks(filled_results, brand_name)
        
        # 9. 整合报告
        report = {
            'brandName': brand_name,
            'competitors': competitors,
            'brandScores': brand_scores,
            'sov': sov_data,
            'risk': risk_data,
            'health': health_data,
            'insights': insights,
            'semanticDriftData': additional_data.get('semantic_drift_data') if additional_data else None,
            'recommendationData': additional_data.get('recommendation_data') if additional_data else None,
            'negativeSources': additional_data.get('negative_sources') if additional_data else None,
            'competitiveAnalysis': additional_data.get('competitive_analysis') if additional_data else None,
            'firstMentionByPlatform': first_mention_data,
            'interceptionRisks': interception_risks,
            'overallScore': brand_scores.get(brand_name, {}).get('overallScore', 50),
            'timestamp': datetime.now().isoformat(),
            
            # 【P1 修复 - 2026-03-06】补充品牌分析相关字段
            'brandAnalysis': additional_data.get('brand_analysis') if additional_data else None,
            'userBrandAnalysis': additional_data.get('user_brand_analysis') if additional_data else None,
            'comparison': additional_data.get('comparison') if additional_data else None,
            'top3Brands': additional_data.get('top_3_brands', []) if additional_data else []
        }

        api_logger.info(
            f"[ReportAggregator] ✅ 报告聚合完成：{brand_name}, "
            f"overallScore={report['overallScore']}"
        )

        return report
    
    def _sanitize_results(self, results: List[Dict]) -> List[Dict]:
        """
        数据清洗
        
        参数：
            results: 原始结果列表
            
        返回：
            清洗后的结果列表
        """
        sanitized = []
        
        for result in results:
            if not result:
                continue
            
            # 提取必要字段
            cleaned = {
                'brand': result.get('brand', ''),
                'question': result.get('question', ''),
                'model': result.get('model', 'unknown'),
                'score': result.get('score', 50),
                'sentiment': result.get('sentiment', 'neutral'),
                'response': result.get('response', {}),
                'geo_data': result.get('geo_data', {}),
                'timestamp': result.get('timestamp', datetime.now().isoformat())
            }
            
            # 确保分数在有效范围内
            score = cleaned['score']
            if isinstance(score, (int, float)):
                cleaned['score'] = max(0, min(100, score))
            else:
                cleaned['score'] = 50
            
            sanitized.append(cleaned)
        
        api_logger.debug(f"[ReportAggregator] 数据清洗完成：{len(results)} -> {len(sanitized)}")
        return sanitized
    
    def _fill_missing_data(self, results: List[Dict], brand_name: str) -> List[Dict]:
        """
        填充缺失数据
        
        参数：
            results: 清洗后的结果列表
            brand_name: 主品牌名称
            
        返回：
            填充后的结果列表
        """
        filled = []
        
        for result in results:
            # 确保品牌名称存在
            if not result.get('brand'):
                result['brand'] = brand_name
            
            # 确保问题存在
            if not result.get('question'):
                result['question'] = '通用诊断问题'
            
            filled.append(result)
        
        return filled
    
    def _calculate_brand_scores(
        self,
        results: List[Dict],
        brand_name: str,
        competitors: List[str]
    ) -> Dict[str, Any]:
        """
        计算品牌分数
        
        参数：
            results: 结果列表
            brand_name: 主品牌名称
            competitors: 竞品列表
            
        返回：
            品牌分数字典
        """
        all_brands = [brand_name] + competitors
        scores = {}
        
        for brand in all_brands:
            brand_results = [r for r in results if r.get('brand') == brand]
            
            if not brand_results:
                # 无数据时使用默认分数
                scores[brand] = {
                    'overallScore': 50,
                    'overallGrade': 'C',
                    'overallAuthority': 50,
                    'overallVisibility': 50,
                    'overallPurity': 50,
                    'overallConsistency': 50,
                    'overallSummary': '暂无数据'
                }
                continue
            
            # 计算平均分
            total_score = sum(r.get('score', 50) for r in brand_results)
            avg_score = round(total_score / len(brand_results))
            
            # 计算等级
            grade = self._get_grade(avg_score)
            summary = self._get_score_summary(avg_score)
            
            # 计算各项分数（简化计算）
            scores[brand] = {
                'overallScore': avg_score,
                'overallGrade': grade,
                'overallAuthority': round(avg_score * 0.9),
                'overallVisibility': round(avg_score * 0.85),
                'overallPurity': round(avg_score * 0.9),
                'overallConsistency': round(avg_score * 0.8),
                'overallSummary': summary
            }
        
        api_logger.debug(f"[ReportAggregator] 品牌分数计算完成：{len(scores)}个品牌")
        return scores
    
    def _calculate_sov(
        self,
        results: List[Dict],
        brand_name: str,
        competitors: List[str]
    ) -> Dict[str, Any]:
        """
        计算品牌 SOV (Share of Voice)
        
        参数：
            results: 结果列表
            brand_name: 主品牌名称
            competitors: 竞品列表
            
        返回：
            SOV 数据
        """
        brand_mentions = sum(1 for r in results if r.get('brand') == brand_name)
        competitor_mentions = sum(
            1 for r in results if r.get('brand') in competitors
        )
        
        total_mentions = brand_mentions + competitor_mentions
        
        if total_mentions == 0:
            return {
                'brandMentions': 0,
                'competitorMentions': 0,
                'totalMentions': 0,
                'brandSOV': 0,
                'competitorSOV': 0
            }
        
        brand_sov = round((brand_mentions / total_mentions) * 100)
        competitor_sov = round((competitor_mentions / total_mentions) * 100)
        
        return {
            'brandMentions': brand_mentions,
            'competitorMentions': competitor_mentions,
            'totalMentions': total_mentions,
            'brandSOV': brand_sov,
            'competitorSOV': competitor_sov
        }
    
    def _calculate_risk(
        self,
        results: List[Dict],
        brand_name: str
    ) -> Dict[str, Any]:
        """
        计算品牌风险评分
        
        参数：
            results: 结果列表
            brand_name: 主品牌名称
            
        返回：
            风险评分数据
        """
        brand_results = [r for r in results if r.get('brand') == brand_name]
        
        if not brand_results:
            return {
                'riskScore': 50,
                'riskLevel': 'medium',
                'positiveInterceptions': 0,
                'negativeInterceptions': 0,
                'totalMentions': 0
            }
        
        negative_count = sum(
            1 for r in brand_results if r.get('sentiment') == 'negative'
        )
        positive_count = len(brand_results) - negative_count
        total = len(brand_results)
        
        # 计算风险分数（负面比例越高，风险越高）
        risk_score = round((negative_count / total) * 100) if total > 0 else 50
        
        # 确定风险等级
        if risk_score > 50:
            risk_level = 'high'
        elif risk_score > 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'riskScore': risk_score,
            'riskLevel': risk_level,
            'positiveInterceptions': positive_count,
            'negativeInterceptions': negative_count,
            'totalMentions': total
        }
    
    def _calculate_brand_health(
        self,
        brand_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算品牌健康度
        
        参数：
            brand_score: 品牌分数
            
        返回：
            健康度数据
        """
        if not brand_score:
            return {
                'score': 50,
                'level': 'medium',
                'authority': 50,
                'visibility': 50,
                'purity': 50,
                'consistency': 50
            }
        
        authority = brand_score.get('overallAuthority', 50)
        visibility = brand_score.get('overallVisibility', 50)
        purity = brand_score.get('overallPurity', 50)
        consistency = brand_score.get('overallConsistency', 50)
        
        # 计算综合健康分数
        health_score = round((authority + visibility + purity + consistency) / 4)
        
        # 确定健康等级
        if health_score >= 80:
            health_level = 'excellent'
        elif health_score >= 60:
            health_level = 'good'
        elif health_score >= 40:
            health_level = 'fair'
        else:
            health_level = 'poor'
        
        return {
            'score': health_score,
            'level': health_level,
            'authority': authority,
            'visibility': visibility,
            'purity': purity,
            'consistency': consistency
        }
    
    def _generate_insights(
        self,
        brand_score: Dict[str, Any],
        brand_name: str
    ) -> Dict[str, Any]:
        """
        生成品牌洞察文本
        
        参数：
            brand_score: 品牌分数
            brand_name: 品牌名称
            
        返回：
            洞察文本数据
        """
        if not brand_score:
            return {
                'summary': f'暂无 {brand_name} 的洞察数据',
                'strengths': [],
                'weaknesses': [],
                'opportunities': [],
                'threats': []
            }
        
        overall_score = brand_score.get('overallScore', 50)
        authority = brand_score.get('overallAuthority', 50)
        visibility = brand_score.get('overallVisibility', 50)
        
        # 生成摘要
        if overall_score >= 80:
            summary = f'{brand_name} 表现卓越，在 AI 平台中具有很强的影响力'
        elif overall_score >= 60:
            summary = f'{brand_name} 表现良好，但仍有提升空间'
        elif overall_score >= 40:
            summary = f'{brand_name} 表现一般，需要加强在 AI 平台的存在'
        else:
            summary = f'{brand_name} 需要改进，在 AI 平台的影响力较弱'
        
        # 生成优势
        strengths = []
        if authority >= 70:
            strengths.append('权威性较高，AI 平台认可度强')
        if visibility >= 70:
            strengths.append('可见性良好，容易被用户发现')
        if not strengths:
            strengths.append('品牌基础稳定')
        
        # 生成劣势
        weaknesses = []
        if authority < 60:
            weaknesses.append('权威性有待提升，需要增强专业内容')
        if visibility < 60:
            weaknesses.append('可见性不足，需要增加曝光')
        if not weaknesses:
            weaknesses.append('各项指标相对均衡')
        
        # 生成机会
        opportunities = [
            '加强 AI 平台内容优化',
            '提升品牌在 AI 回答中的提及率',
            '增强与竞品的差异化定位'
        ]
        
        # 生成威胁
        threats = [
            '竞品可能在 AI 平台占据更多曝光',
            'AI 算法变化可能影响品牌展示'
        ]
        
        return {
            'summary': summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'opportunities': opportunities,
            'threats': threats
        }
    
    def _calculate_first_mention_by_platform(
        self,
        results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        计算各平台的首次提及率
        
        参数：
            results: 结果列表
            
        返回：
            各平台的首次提及率
        """
        platform_stats = {}
        
        for result in results:
            platform = result.get('model', 'unknown')
            
            if platform not in platform_stats:
                platform_stats[platform] = {
                    'platform': platform,
                    'total': 0,
                    'firstMention': 0
                }
            
            platform_stats[platform]['total'] += 1
            
            # 检查是否提及品牌
            geo_data = result.get('geo_data', {})
            if geo_data and geo_data.get('brand_mentioned'):
                platform_stats[platform]['firstMention'] += 1
        
        # 计算提及率
        first_mention_data = []
        for platform, stats in platform_stats.items():
            rate = round(
                (stats['firstMention'] / stats['total']) * 100
            ) if stats['total'] > 0 else 0
            
            first_mention_data.append({
                'platform': platform,
                'rate': rate,
                'firstMention': stats['firstMention'],
                'total': stats['total']
            })
        
        return first_mention_data
    
    def _calculate_interception_risks(
        self,
        results: List[Dict],
        brand_name: str
    ) -> List[Dict[str, Any]]:
        """
        计算拦截风险
        
        参数：
            results: 结果列表
            brand_name: 主品牌名称
            
        返回：
            拦截风险列表
        """
        interception_counts = {}
        total_intercepted = 0
        
        for result in results:
            geo_data = result.get('geo_data', {})
            interception = geo_data.get('interception', '') if geo_data else ''
            
            if interception and interception.strip():
                total_intercepted += 1
                
                # 分割竞品名称（可能包含多个）
                competitors = [
                    c.strip() for c in interception.replace(',', ',').split(',')
                    if c.strip()
                ]
                
                for competitor in competitors:
                    if competitor and competitor != brand_name:
                        interception_counts[competitor] = (
                            interception_counts.get(competitor, 0) + 1
                        )
        
        total_results = len(results)
        interception_rate = (
            (total_intercepted / total_results) * 100
        ) if total_results > 0 else 0
        
        # 确定风险等级
        if interception_rate > 50:
            risk_level = 'high'
        elif interception_rate > 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # 构建拦截风险列表
        risks = []
        for competitor, count in interception_counts.items():
            risks.append({
                'type': 'brand_interception',
                'competitor': competitor,
                'count': count,
                'rate': round((count / total_results) * 100),
                'level': risk_level,
                'description': (
                    f'{competitor} 在 {count}/{total_results} 次诊断中'
                    f'拦截了您的品牌'
                )
            })
        
        # 按拦截次数排序
        risks.sort(key=lambda x: x['count'], reverse=True)
        
        return risks
    
    def _get_grade(self, score: int) -> str:
        """获取分数等级"""
        for threshold, grade in sorted(
            self.GRADE_MAPPING.items(),
            key=lambda x: x[0],
            reverse=True
        ):
            if score >= threshold:
                return grade
        return 'D'
    
    def _get_score_summary(self, score: int) -> str:
        """获取分数摘要"""
        for threshold, summary in sorted(
            self.SCORE_SUMMARY.items(),
            key=lambda x: x[0],
            reverse=True
        ):
            if score >= threshold:
                return summary
        return self.SCORE_SUMMARY[0]


# 全局实例
_report_aggregator_instance: Optional[ReportAggregator] = None


def get_report_aggregator() -> ReportAggregator:
    """
    获取报告聚合器实例（单例模式）
    
    Returns:
        ReportAggregator 实例
    """
    global _report_aggregator_instance
    if _report_aggregator_instance is None:
        _report_aggregator_instance = ReportAggregator()
        api_logger.info("[ReportAggregator] 创建全局实例")
    return _report_aggregator_instance


def aggregate_report(
    raw_results: List[Dict[str, Any]],
    brand_name: str,
    competitors: List[str],
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    聚合品牌诊断报告（便捷函数）
    
    参数：
        raw_results: 原始诊断结果列表
        brand_name: 主品牌名称
        competitors: 竞品列表
        additional_data: 额外数据
        
    返回：
        聚合后的报告数据
    """
    aggregator = get_report_aggregator()
    return aggregator.aggregate(
        raw_results=raw_results,
        brand_name=brand_name,
        competitors=competitors,
        additional_data=additional_data
    )
