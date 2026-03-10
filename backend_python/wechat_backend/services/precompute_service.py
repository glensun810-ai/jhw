"""
诊断结果预计算模块
为前端分层加载提供预计算数据

功能：
1. 计算评分维度（dimension_scores）
2. 生成问题诊断数据（recommendation_data）
3. 计算质量评分（quality_score）

作者：系统架构优化项目
日期：2026-03-11
"""

import math
from typing import Dict, List, Any, Optional
from collections import defaultdict


class DiagnosisPrecomputeService:
    """诊断结果预计算服务"""
    
    @staticmethod
    def calculate_dimension_scores(detailed_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        计算评分维度
        
        Args:
            detailed_results: 详细结果列表
            
        Returns:
            dimension_scores: {
                authority: 80,
                visibility: 75,
                purity: 90,
                consistency: 85
            }
        """
        if not detailed_results or len(detailed_results) == 0:
            return {
                'authority': 0,
                'visibility': 0,
                'purity': 0,
                'consistency': 0
            }
        
        # 限制计算数据量，最多 50 条（性能优化）
        limited_results = detailed_results[:50]
        total = len(limited_results)
        
        auth_sum = 0
        vis_sum = 0
        pur_sum = 0
        con_sum = 0
        
        for result in limited_results:
            # 从不同字段名兼容获取
            auth_sum += (
                result.get('authority_score') or 
                result.get('authority') or 
                result.get('score', 0)
            )
            vis_sum += (
                result.get('visibility_score') or 
                result.get('visibility') or 
                result.get('score', 0)
            )
            pur_sum += (
                result.get('purity_score') or 
                result.get('purity') or 
                result.get('score', 0)
            )
            con_sum += (
                result.get('consistency_score') or 
                result.get('consistency') or 
                result.get('score', 0)
            )
        
        return {
            'authority': round(auth_sum / total),
            'visibility': round(vis_sum / total),
            'purity': round(pur_sum / total),
            'consistency': round(con_sum / total)
        }
    
    @staticmethod
    def generate_recommendation_data(
        detailed_results: List[Dict[str, Any]],
        source_intelligence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成问题诊断数据
        
        Args:
            detailed_results: 详细结果列表
            source_intelligence: 信源分析数据（可选）
            
        Returns:
            recommendation_data: {
                risk_levels: {
                    high: [...],
                    medium: [...]
                },
                priority_recommendations: [...]
            }
        """
        risk_levels = {
            'high': [],
            'medium': []
        }
        priority_recommendations = []
        
        if not detailed_results:
            return {
                'risk_levels': risk_levels,
                'priority_recommendations': priority_recommendations
            }
        
        # 分析低分结果，识别风险
        low_score_results = [
            r for r in detailed_results 
            if (r.get('score') or 0) < 60
        ]
        
        # 生成高风险问题
        for i, result in enumerate(low_score_results[:5]):  # 最多 5 个高风险
            risk_item = {
                'id': f'risk_{i+1}',
                'text': f'{result.get("brand", "品牌")} - {result.get("question", "问题")}',
                'source': result.get('aiModel') or result.get('ai_model') or '未知',
                'score': result.get('score', 0),
                'question': result.get('question', ''),
                'response': result.get('response') or result.get('answer', '')
            }
            risk_levels['high'].append(risk_item)
        
        # 生成中风险问题
        medium_score_results = [
            r for r in detailed_results 
            if 60 <= (r.get('score') or 0) < 75
        ]
        
        for i, result in enumerate(medium_score_results[:5]):  # 最多 5 个中风险
            risk_item = {
                'id': f'risk_m{i+1}',
                'text': f'{result.get("brand", "品牌")} - {result.get("question", "问题")}',
                'source': result.get('aiModel') or result.get('ai_model') or '未知',
                'score': result.get('score', 0),
                'question': result.get('question', ''),
                'response': result.get('response') or result.get('answer', '')
            }
            risk_levels['medium'].append(risk_item)
        
        # 生成优化建议
        if len(low_score_results) > 0:
            priority_recommendations.append({
                'id': 'rec_1',
                'text': '提升 AI 认知质量',
                'priority': '高',
                'description': f'发现{len(low_score_results)}个低分评价，需要重点关注'
            })
        
        if source_intelligence and source_intelligence.get('source_pool'):
            negative_sources = [
                s for s in source_intelligence['source_pool']
                if s.get('domain_authority') == '低'
            ]
            if negative_sources:
                priority_recommendations.append({
                    'id': 'rec_2',
                    'text': '优化信源质量',
                    'priority': '中',
                    'description': f'发现{len(negative_sources)}个低权威信源，建议优化'
                })
        
        # 通用建议
        if len(detailed_results) > 0:
            avg_score = sum(r.get('score', 0) for r in detailed_results) / len(detailed_results)
            if avg_score < 70:
                priority_recommendations.append({
                    'id': 'rec_3',
                    'text': '加强品牌建设',
                    'priority': '高',
                    'description': f'当前平均分{round(avg_score)}分，低于行业平均水平'
                })
        
        return {
            'risk_levels': risk_levels,
            'priority_recommendations': priority_recommendations
        }
    
    @staticmethod
    def calculate_quality_score(
        dimension_scores: Dict[str, int],
        detailed_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算质量评分
        
        Args:
            dimension_scores: 评分维度
            detailed_results: 详细结果列表
            
        Returns:
            quality_score: {
                overall_score: 85,
                dimension_scores: {...}
            }
        """
        # 计算总体评分
        overall_score = round(
            (dimension_scores['authority'] + 
             dimension_scores['visibility'] + 
             dimension_scores['purity'] + 
             dimension_scores['consistency']) / 4
        )
        
        return {
            'overall_score': overall_score,
            'dimension_scores': dimension_scores
        }
    
    @staticmethod
    def precompute_all(
        detailed_results: List[Dict[str, Any]],
        source_intelligence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        预计算所有数据
        
        Args:
            detailed_results: 详细结果列表
            source_intelligence: 信源分析数据（可选）
            
        Returns:
            precomputed_data: {
                dimension_scores: {...},
                recommendation_data: {...},
                quality_score: {...}
            }
        """
        # 1. 计算评分维度
        dimension_scores = DiagnosisPrecomputeService.calculate_dimension_scores(
            detailed_results
        )
        
        # 2. 生成问题诊断数据
        recommendation_data = DiagnosisPrecomputeService.generate_recommendation_data(
            detailed_results,
            source_intelligence
        )
        
        # 3. 计算质量评分
        quality_score = DiagnosisPrecomputeService.calculate_quality_score(
            dimension_scores,
            detailed_results
        )
        
        return {
            'dimension_scores': dimension_scores,
            'recommendation_data': recommendation_data,
            'quality_score': quality_score
        }


# 便捷函数
def precompute_diagnosis_data(
    detailed_results: List[Dict[str, Any]],
    source_intelligence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    预计算诊断数据（便捷函数）
    
    Args:
        detailed_results: 详细结果列表
        source_intelligence: 信源分析数据（可选）
        
    Returns:
        precomputed_data: 预计算数据
    """
    return DiagnosisPrecomputeService.precompute_all(
        detailed_results,
        source_intelligence
    )
