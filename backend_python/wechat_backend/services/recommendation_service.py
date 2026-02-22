"""
推荐生成服务

功能：
- 优化建议生成
- 行动计划制定
- 优先级排序
"""

from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.recommendation_generator import RecommendationGenerator


class RecommendationService:
    """
    推荐生成服务类
    
    功能：
    - 优化建议生成
    - 行动计划制定
    - 优先级排序
    """
    
    @staticmethod
    def generate_recommendations(
        brand_scores: Dict[str, Any],
        semantic_drift: Optional[Dict[str, Any]] = None,
        interception_risks: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议
        
        参数：
        - brand_scores: 品牌评分
        - semantic_drift: 语义偏移数据
        - interception_risks: 拦截风险数据
        
        返回：
        - recommendations: 建议列表
        """
        try:
            recommendations = []
            
            # 基于品牌评分生成建议
            score_recommendations = RecommendationService._generate_score_recommendations(brand_scores)
            recommendations.extend(score_recommendations)
            
            # 基于语义偏移生成建议
            if semantic_drift:
                drift_recommendations = RecommendationService._generate_drift_recommendations(semantic_drift)
                recommendations.extend(drift_recommendations)
            
            # 基于拦截风险生成建议
            if interception_risks:
                risk_recommendations = RecommendationService._generate_risk_recommendations(interception_risks)
                recommendations.extend(risk_recommendations)
            
            # 按优先级排序
            recommendations.sort(key=lambda x: x.get('priority', 999))
            
            api_logger.info(f'[RecommendationService] 生成 {len(recommendations)} 条建议')
            
            return recommendations
            
        except Exception as e:
            api_logger.error(f'[RecommendationService] 建议生成失败：{e}')
            return []
    
    @staticmethod
    def _generate_score_recommendations(brand_scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于品牌评分生成建议
        
        参数：
        - brand_scores: 品牌评分
        
        返回：
        - recommendations: 建议列表
        """
        recommendations = []
        
        for brand, scores in brand_scores.items():
            overall_score = scores.get('overallScore', 0)
            
            if overall_score < 60:
                recommendations.append({
                    'type': 'score_improvement',
                    'priority': 1,
                    'title': f'{brand} 需要全面提升',
                    'description': '品牌综合得分较低，建议从权威度、可见度、纯净度等多方面进行优化',
                    'action_items': [
                        '提升品牌权威度',
                        '增加品牌可见度',
                        '优化品牌纯净度'
                    ]
                })
            elif overall_score < 80:
                recommendations.append({
                    'type': 'score_improvement',
                    'priority': 2,
                    'title': f'{brand} 有提升空间',
                    'description': '品牌综合得分中等，建议在薄弱环节进行针对性优化',
                    'action_items': [
                        '分析薄弱维度',
                        '制定针对性优化方案'
                    ]
                })
        
        return recommendations
    
    @staticmethod
    def _generate_drift_recommendations(semantic_drift: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于语义偏移生成建议
        
        参数：
        - semantic_drift: 语义偏移数据
        
        返回：
        - recommendations: 建议列表
        """
        recommendations = []
        
        drift_score = semantic_drift.get('drift_score', 0)
        severity = semantic_drift.get('drift_severity', 'low')
        
        if severity == 'high':
            recommendations.append({
                'type': 'semantic_alignment',
                'priority': 1,
                'title': '严重语义偏移，需要立即调整',
                'description': 'AI 生成的关键词与官方关键词存在严重偏差，建议调整品牌传播策略',
                'action_items': [
                    '重新审视品牌定位',
                    '优化官方关键词策略',
                    '加强品牌一致性传播'
                ]
            })
        elif severity == 'medium':
            recommendations.append({
                'type': 'semantic_alignment',
                'priority': 2,
                'title': '存在语义偏移，建议优化',
                'description': 'AI 生成的关键词与官方关键词存在一定偏差，建议优化品牌传播',
                'action_items': [
                    '检查品牌传播一致性',
                    '优化关键词策略'
                ]
            })
        
        return recommendations
    
    @staticmethod
    def _generate_risk_recommendations(interception_risks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于拦截风险生成建议
        
        参数：
        - interception_risks: 拦截风险数据
        
        返回：
        - recommendations: 建议列表
        """
        recommendations = []
        
        level = interception_risks.get('level', 'medium')
        
        if level == 'high':
            recommendations.append({
                'type': 'risk_mitigation',
                'priority': 1,
                'title': '高风险拦截，需要紧急处理',
                'description': '品牌面临较高的拦截风险，建议立即采取措施',
                'action_items': [
                    '分析拦截原因',
                    '优化 SEO 策略',
                    '增加正面内容曝光'
                ]
            })
        elif level == 'medium':
            recommendations.append({
                'type': 'risk_mitigation',
                'priority': 2,
                'title': '中等风险，建议关注',
                'description': '品牌面临一定的拦截风险，建议持续关注并优化',
                'action_items': [
                    '监控拦截情况',
                    '优化内容策略'
                ]
            })
        
        return recommendations


# 导出服务实例
recommendation_service = RecommendationService()
