"""
报告生成服务

功能：
- 生成诊断报告
- 报告格式化
- 报告导出
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger


class ReportGenerationService:
    """
    报告生成服务类
    
    功能：
    - 生成诊断报告
    - 报告格式化
    - 报告导出
    """
    
    @staticmethod
    def generate_report(
        execution_id: str,
        brand_name: str,
        results: List[Dict[str, Any]],
        competitive_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成诊断报告
        
        参数：
        - execution_id: 执行 ID
        - brand_name: 品牌名称
        - results: 诊断结果列表
        - competitive_analysis: 竞争分析数据
        
        返回：
        - report: 报告数据
        """
        try:
            # 计算综合得分
            overall_score = ReportGenerationService._calculate_overall_score(results)
            
            # 生成品牌评分
            brand_scores = ReportGenerationService._generate_brand_scores(results, brand_name)
            
            # 生成报告
            report = {
                'execution_id': execution_id,
                'brand_name': brand_name,
                'overall_score': overall_score,
                'brand_scores': brand_scores,
                'competitive_analysis': competitive_analysis or {},
                'generated_at': datetime.now().isoformat(),
                'results_count': len(results)
            }
            
            api_logger.info(f'[ReportGenerationService] 报告生成成功：{brand_name}, 得分：{overall_score}')
            
            return report
            
        except Exception as e:
            api_logger.error(f'[ReportGenerationService] 报告生成失败：{e}')
            return {
                'error': str(e),
                'execution_id': execution_id
            }
    
    @staticmethod
    def _calculate_overall_score(results: List[Dict[str, Any]]) -> float:
        """
        计算综合得分
        
        参数：
        - results: 诊断结果列表
        
        返回：
        - score: 综合得分
        """
        if not results:
            return 0.0
        
        total_score = 0.0
        count = 0
        
        for result in results:
            score = result.get('score', 0)
            if score:
                total_score += score
                count += 1
        
        return round(total_score / count, 2) if count > 0 else 0.0
    
    @staticmethod
    def _generate_brand_scores(
        results: List[Dict[str, Any]],
        brand_name: str
    ) -> Dict[str, Any]:
        """
        生成品牌评分
        
        参数：
        - results: 诊断结果列表
        - brand_name: 品牌名称
        
        返回：
        - scores: 品牌评分
        """
        brand_results = [r for r in results if r.get('brand') == brand_name]
        
        if not brand_results:
            return {
                brand_name: {
                    'overallScore': 0,
                    'overallGrade': 'D',
                    'overallAuthority': 0,
                    'overallVisibility': 0,
                    'overallPurity': 0,
                    'overallConsistency': 0,
                    'overallSummary': '暂无数据'
                }
            }
        
        # 计算各项平均分
        total_score = sum(r.get('score', 0) for r in brand_results)
        avg_score = round(total_score / len(brand_results))
        
        # 计算等级
        if avg_score >= 90:
            grade = 'A+'
            summary = '表现卓越'
        elif avg_score >= 80:
            grade = 'A'
            summary = '表现良好'
        elif avg_score >= 70:
            grade = 'B'
            summary = '表现一般'
        elif avg_score >= 60:
            grade = 'C'
            summary = '有待提升'
        else:
            grade = 'D'
            summary = '需要改进'
        
        return {
            brand_name: {
                'overallScore': avg_score,
                'overallGrade': grade,
                'overallAuthority': round(avg_score * 0.9),
                'overallVisibility': round(avg_score * 0.85),
                'overallPurity': round(avg_score * 0.9),
                'overallConsistency': round(avg_score * 0.8),
                'overallSummary': summary
            }
        }
    
    @staticmethod
    def format_report_for_export(report: Dict[str, Any], format_type: str = 'html') -> str:
        """
        格式化报告用于导出
        
        参数：
        - report: 报告数据
        - format_type: 导出格式（html/pdf/markdown）
        
        返回：
        - content: 格式化后的内容
        """
        if format_type == 'html':
            return ReportGenerationService._format_html_report(report)
        elif format_type == 'markdown':
            return ReportGenerationService._format_markdown_report(report)
        else:
            return ReportGenerationService._format_html_report(report)
    
    @staticmethod
    def _format_html_report(report: Dict[str, Any]) -> str:
        """
        格式化 HTML 报告
        
        参数：
        - report: 报告数据
        
        返回：
        - html: HTML 内容
        """
        brand_name = report.get('brand_name', '品牌')
        overall_score = report.get('overall_score', 0)
        brand_scores = report.get('brand_scores', {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{brand_name} - 品牌诊断报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #667eea; text-align: center; }}
                .score {{ font-size: 48px; color: #667eea; text-align: center; }}
                .section {{ margin: 20px 0; }}
                .brand-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <h1>{brand_name} - 品牌诊断报告</h1>
            
            <div class="section">
                <h2>综合得分</h2>
                <div class="score">{overall_score} 分</div>
            </div>
            
            <div class="section">
                <h2>品牌评分</h2>
                {ReportGenerationService._generate_brand_scores_html(brand_scores)}
            </div>
            
            <div class="section">
                <p style="text-align: center; color: #999; font-size: 12px;">
                    报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _generate_brand_scores_html(brand_scores: Dict[str, Any]) -> str:
        """
        生成品牌评分 HTML
        
        参数：
        - brand_scores: 品牌评分
        
        返回：
        - html: HTML 内容
        """
        if not brand_scores:
            return '<p>暂无评分数据</p>'
        
        html = '<div class="brand-scores">'
        
        for brand, scores in brand_scores.items():
            html += f"""
            <div class="brand-item">
                <strong>{brand}</strong>: 
                {scores.get('overallScore', 0)} 分 
                ({scores.get('overallGrade', '-')})
            </div>
            """
        
        html += '</div>'
        return html
    
    @staticmethod
    def _format_markdown_report(report: Dict[str, Any]) -> str:
        """
        格式化 Markdown 报告
        
        参数：
        - report: 报告数据
        
        返回：
        - markdown: Markdown 内容
        """
        brand_name = report.get('brand_name', '品牌')
        overall_score = report.get('overall_score', 0)
        brand_scores = report.get('brand_scores', {})
        
        markdown = f"# {brand_name} - 品牌诊断报告\n\n"
        markdown += f"## 综合得分\n\n"
        markdown += f"**{overall_score} 分**\n\n"
        markdown += f"## 品牌评分\n\n"
        
        for brand, scores in brand_scores.items():
            markdown += f"- **{brand}**: {scores.get('overallScore', 0)} 分 ({scores.get('overallGrade', '-')})\n"
        
        markdown += f"\n---\n"
        markdown += f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return markdown


# 导出服务实例
report_generation_service = ReportGenerationService()
