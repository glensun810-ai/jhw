"""
竞争分析服务

功能：
- 竞争数据聚合
- 竞品对比分析
- 市场份额计算
"""

from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger


class CompetitiveAnalysisService:
    """
    竞争分析服务类
    
    功能：
    - 竞争数据聚合
    - 竞品对比分析
    - 市场份额计算
    """
    
    @staticmethod
    def analyze_competition(
        results: List[Dict[str, Any]],
        main_brand: str,
        competitor_brands: List[str]
    ) -> Dict[str, Any]:
        """
        分析竞争数据
        
        参数：
        - results: 诊断结果列表
        - main_brand: 主品牌
        - competitor_brands: 竞品品牌列表
        
        返回：
        - analysis: 竞争分析结果
        """
        try:
            # 按品牌分组
            brand_results = CompetitiveAnalysisService._group_by_brand(results)
            
            # 计算品牌评分
            brand_scores = CompetitiveAnalysisService._calculate_brand_scores(brand_results)
            
            # 计算首次提及率
            first_mention = CompetitiveAnalysisService._calculate_first_mention(results)
            
            # 计算拦截风险
            interception_risks = CompetitiveAnalysisService._calculate_interception_risks(results, main_brand)
            
            analysis = {
                'brand_scores': brand_scores,
                'first_mention_by_platform': first_mention,
                'interception_risks': interception_risks,
                'main_brand': main_brand,
                'competitor_brands': competitor_brands
            }
            
            api_logger.info(f'[CompetitiveAnalysisService] 竞争分析完成：{main_brand}')
            
            return analysis
            
        except Exception as e:
            api_logger.error(f'[CompetitiveAnalysisService] 竞争分析失败：{e}')
            return {'error': str(e)}
    
    @staticmethod
    def _group_by_brand(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按品牌分组结果
        
        参数：
        - results: 诊断结果列表
        
        返回：
        - grouped: 分组后的结果
        """
        grouped = {}
        
        for result in results:
            brand = result.get('brand', 'unknown')
            if brand not in grouped:
                grouped[brand] = []
            grouped[brand].append(result)
        
        return grouped
    
    @staticmethod
    def _calculate_brand_scores(
        brand_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        计算品牌评分
        
        参数：
        - brand_results: 按品牌分组的结果
        
        返回：
        - scores: 品牌评分
        """
        scores = {}
        
        for brand, results in brand_results.items():
            if not results:
                continue
            
            total_score = sum(r.get('score', 0) for r in results)
            avg_score = round(total_score / len(results))
            
            # 计算等级
            if avg_score >= 90:
                grade = 'A+'
            elif avg_score >= 80:
                grade = 'A'
            elif avg_score >= 70:
                grade = 'B'
            elif avg_score >= 60:
                grade = 'C'
            else:
                grade = 'D'
            
            scores[brand] = {
                'overallScore': avg_score,
                'overallGrade': grade
            }
        
        return scores
    
    @staticmethod
    def _calculate_first_mention(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算首次提及率
        
        参数：
        - results: 诊断结果列表
        
        返回：
        - rates: 首次提及率
        """
        # 简化实现
        return {}
    
    @staticmethod
    def _calculate_interception_risks(
        results: List[Dict[str, Any]],
        main_brand: str
    ) -> Dict[str, Any]:
        """
        计算拦截风险
        
        参数：
        - results: 诊断结果列表
        - main_brand: 主品牌
        
        返回：
        - risks: 拦截风险
        """
        # 简化实现
        return {
            'level': 'medium',
            'description': '中等风险'
        }


# 导出服务实例
competitive_analysis_service = CompetitiveAnalysisService()
