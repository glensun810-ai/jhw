"""
情报枢纽——自动化报告与高管视角
报告生成器模块
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import math
import io
from wechat_backend.logging_config import api_logger
from wechat_backend.database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery, sql_protector
from wechat_backend.models import get_brand_test_result, get_deep_intelligence_result
from wechat_backend.cruise_controller import CruiseController

# PDF 生成相关导入
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ReportGenerator:
    """报告生成器 - 聚合测试结果、巡航趋势和工作流任务数据，计算ROI并生成报告"""

    def __init__(self):
        self.db_path = DB_PATH
        self.logger = api_logger
        self.cruise_controller = CruiseController()

    def generate_executive_summary(self, brand_name: str, days: int = 30) -> Dict[str, Any]:
        """
        生成高管摘要报告

        Args:
            brand_name: 品牌名称
            days: 查询天数

        Returns:
            包含汇总数据的字典
        """
        # 获取测试结果数据
        test_results = self._get_test_results(brand_name, days)
        
        # 获取巡航趋势数据
        trend_data = self.cruise_controller.get_trend_data(brand_name, days)
        
        # 计算ROI相关指标
        roi_metrics = self._calculate_roi_metrics(test_results, trend_data)
        
        # 计算曝光增量
        exposure_increment = self._calculate_exposure_increment(trend_data)
        
        # 生成汇总报告
        summary = {
            'brand_name': brand_name,
            'report_period': {
                'start_date': (datetime.now() - timedelta(days=days)).isoformat(),
                'end_date': datetime.now().isoformat(),
                'days': days
            },
            'roi_metrics': roi_metrics,
            'exposure_metrics': {
                'estimated_exposure_increment': exposure_increment,
                'ranking_improvement': self._calculate_ranking_improvement(trend_data),
                'sentiment_trend': self._calculate_sentiment_trend(trend_data)
            },
            'performance_summary': {
                'avg_overall_score': self._calculate_avg_score(test_results),
                'test_count': len(test_results),
                'trend_data_points': len(trend_data)
            },
            'key_insights': self._generate_key_insights(test_results, trend_data),
            'recommendations': self._generate_recommendations(test_results, trend_data)
        }
        
        return summary

    def _get_test_results(self, brand_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取测试结果数据"""
        safe_query = SafeDatabaseQuery(self.db_path)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取指定品牌的历史测试记录
        records_data = safe_query.execute_query('''
            SELECT id, test_date, brand_name, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results
            FROM test_records
            WHERE brand_name = ? AND test_date >= ?
            ORDER BY test_date DESC
        ''', (brand_name, start_date))
        
        test_results = []
        for row in records_data:
            record_id, test_date, brand, ai_models_used, questions_used, overall_score, total_tests, results_summary_str, detailed_results_str = row
            
            # 解析JSON数据
            results_summary = json.loads(results_summary_str) if results_summary_str else {}
            detailed_results = json.loads(detailed_results_str) if detailed_results_str else []
            
            test_results.append({
                'id': record_id,
                'test_date': test_date,
                'brand_name': brand,
                'ai_models_used': json.loads(ai_models_used) if ai_models_used else [],
                'questions_used': json.loads(questions_used) if questions_used else [],
                'overall_score': overall_score,
                'total_tests': total_tests,
                'results_summary': results_summary,
                'detailed_results': detailed_results
            })
        
        return test_results

    def _calculate_roi_metrics(self, test_results: List[Dict[str, Any]], trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算ROI相关指标"""
        if not test_results and not trend_data:
            return {
                'roi_score': 0.0,
                'investment_value': 0.0,
                'return_value': 0.0,
                'roi_percentage': 0.0,
                'confidence_level': 'low'
            }
        
        # 计算投资价值（基于测试数量和复杂度）
        total_tests = sum([result.get('total_tests', 0) for result in test_results])
        investment_value = total_tests * 100  # 假设每次测试价值100单位
        
        # 计算回报价值（基于排名提升和曝光增加）
        ranking_improvement = self._calculate_ranking_improvement(trend_data)
        exposure_increment = self._calculate_exposure_increment(trend_data)
        
        # 计算回报价值
        return_value = (ranking_improvement * 500) + (exposure_increment * 10)  # 假设排名提升和曝光的价值
        
        # 计算ROI
        if investment_value > 0:
            roi_percentage = ((return_value - investment_value) / investment_value) * 100
            roi_score = max(0, min(100, (return_value / investment_value) * 50))  # 标准化到0-100
        else:
            roi_percentage = 0.0
            roi_score = 0.0
        
        # 计算置信度
        confidence_level = 'high' if len(test_results) >= 5 and len(trend_data) >= 10 else 'medium' if len(test_results) >= 2 and len(trend_data) >= 5 else 'low'
        
        return {
            'roi_score': round(roi_score, 2),
            'investment_value': round(investment_value, 2),
            'return_value': round(return_value, 2),
            'roi_percentage': round(roi_percentage, 2),
            'confidence_level': confidence_level
        }

    def _calculate_exposure_increment(self, trend_data: List[Dict[str, Any]]) -> float:
        """计算预估曝光增量"""
        if len(trend_data) < 2:
            return 0.0
        
        # 获取最早的排名和最新的排名
        sorted_trend_data = sorted(trend_data, key=lambda x: x['timestamp'])
        initial_rank = sorted_trend_data[0].get('rank')
        final_rank = sorted_trend_data[-1].get('rank')
        
        if initial_rank is None or final_rank is None:
            return 0.0
        
        # 计算排名改善（数字越小表示排名越高）
        rank_improvement = initial_rank - final_rank
        
        # 假设排名改善与曝光增量正相关
        # 排名每提升1位，曝光增量约为10%
        exposure_increment = rank_improvement * 10.0
        
        # 如果排名下降，曝光增量为负
        return max(0, exposure_increment)  # 只返回非负值

    def _calculate_ranking_improvement(self, trend_data: List[Dict[str, Any]]) -> float:
        """计算排名改善程度"""
        if len(trend_data) < 2:
            return 0.0
        
        # 获取最早的排名和最新的排名
        sorted_trend_data = sorted(trend_data, key=lambda x: x['timestamp'])
        initial_rank = sorted_trend_data[0].get('rank')
        final_rank = sorted_trend_data[-1].get('rank')
        
        if initial_rank is None or final_rank is None:
            return 0.0
        
        # 计算排名改善（数字越小表示排名越高）
        rank_improvement = initial_rank - final_rank
        
        return float(rank_improvement)

    def _calculate_sentiment_trend(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算情感趋势"""
        if not trend_data:
            return {
                'average_sentiment': 0.0,
                'trend_direction': 'stable',
                'change_magnitude': 0.0
            }
        
        # 提取情感分数
        sentiment_scores = [point.get('sentiment_score', 0) for point in trend_data if point.get('sentiment_score') is not None]
        
        if not sentiment_scores:
            return {
                'average_sentiment': 0.0,
                'trend_direction': 'stable',
                'change_magnitude': 0.0
            }
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        
        # 计算趋势方向
        if len(sentiment_scores) >= 2:
            initial_sentiment = sentiment_scores[0]
            final_sentiment = sentiment_scores[-1]
            change_magnitude = final_sentiment - initial_sentiment
            
            if change_magnitude > 0.1:
                trend_direction = 'improving'
            elif change_magnitude < -0.1:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        else:
            change_magnitude = 0.0
            trend_direction = 'stable'
        
        return {
            'average_sentiment': round(avg_sentiment, 2),
            'trend_direction': trend_direction,
            'change_magnitude': round(change_magnitude, 2)
        }

    def _calculate_avg_score(self, test_results: List[Dict[str, Any]]) -> float:
        """计算平均分数"""
        if not test_results:
            return 0.0
        
        total_score = sum([result.get('overall_score', 0) for result in test_results])
        return total_score / len(test_results) if test_results else 0.0

    def _generate_key_insights(self, test_results: List[Dict[str, Any]], trend_data: List[Dict[str, Any]]) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        # 分析测试结果
        if test_results:
            avg_score = self._calculate_avg_score(test_results)
            if avg_score > 80:
                insights.append(f"品牌认知度表现优异，平均得分为{avg_score:.1f}分")
            elif avg_score > 60:
                insights.append(f"品牌认知度表现良好，平均得分为{avg_score:.1f}分")
            else:
                insights.append(f"品牌认知度有待提升，平均得分为{avg_score:.1f}分")
        
        # 分析趋势数据
        if trend_data:
            ranking_improvement = self._calculate_ranking_improvement(trend_data)
            if ranking_improvement > 0:
                insights.append(f"品牌排名有所提升，改善了{ranking_improvement}位")
            elif ranking_improvement < 0:
                insights.append(f"品牌排名有所下降，下滑了{abs(ranking_improvement)}位")
            
            exposure_increment = self._calculate_exposure_increment(trend_data)
            if exposure_increment > 0:
                insights.append(f"预估曝光量增加了{exposure_increment:.1f}%")
        
        # 分析ROI
        roi_metrics = self._calculate_roi_metrics(test_results, trend_data)
        if roi_metrics['roi_percentage'] > 0:
            insights.append(f"投资回报率为{roi_metrics['roi_percentage']:.1f}%，表现积极")
        elif roi_metrics['roi_percentage'] < 0:
            insights.append(f"投资回报率为{roi_metrics['roi_percentage']:.1f}%，需要优化策略")
        
        return insights

    def _generate_recommendations(self, test_results: List[Dict[str, Any]], trend_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """生成优化建议"""
        recommendations = []
        
        # 基于排名的建议
        ranking_improvement = self._calculate_ranking_improvement(trend_data)
        if ranking_improvement < 0:
            recommendations.append({
                'type': 'ranking_improvement',
                'title': '排名优化建议',
                'description': '当前品牌排名呈下降趋势，建议加强内容质量和增加高质量信源引用',
                'priority': 'high'
            })
        elif ranking_improvement == 0:
            recommendations.append({
                'type': 'ranking_stabilization',
                'title': '排名稳定建议',
                'description': '当前品牌排名保持稳定，建议持续监控并寻找突破机会',
                'priority': 'medium'
            })
        else:
            recommendations.append({
                'type': 'ranking_maintenance',
                'title': '排名维护建议',
                'description': '当前品牌排名呈上升趋势，建议维持现有策略并扩大优势',
                'priority': 'low'
            })
        
        # 基于情感的建议
        sentiment_trend = self._calculate_sentiment_trend(trend_data)
        if sentiment_trend['trend_direction'] == 'declining':
            recommendations.append({
                'type': 'sentiment_improvement',
                'title': '情感优化建议',
                'description': '品牌情感倾向呈下降趋势，建议加强正面内容投放和危机公关准备',
                'priority': 'high'
            })
        elif sentiment_trend['trend_direction'] == 'improving':
            recommendations.append({
                'type': 'sentiment_maintenance',
                'title': '情感维护建议',
                'description': '品牌情感倾向呈上升趋势，建议维持正面内容策略',
                'priority': 'medium'
            })
        
        # 基于ROI的建议
        roi_metrics = self._calculate_roi_metrics(test_results, trend_data)
        if roi_metrics['roi_percentage'] < 0:
            recommendations.append({
                'type': 'roi_optimization',
                'title': 'ROI优化建议',
                'description': '当前投资回报率为负，建议重新评估测试策略和资源配置',
                'priority': 'high'
            })
        elif roi_metrics['roi_percentage'] < 20:
            recommendations.append({
                'type': 'roi_improvement',
                'title': 'ROI提升建议',
                'description': '当前投资回报率较低，建议优化测试模型组合和问题设计',
                'priority': 'medium'
            })
        
        return recommendations

    def generate_pdf_report(self, brand_name: str, days: int = 30) -> bytes:
        """
        生成PDF报告

        Args:
            brand_name: 品牌名称
            days: 查询天数

        Returns:
            PDF文件的字节数据
        """
        # 获取报告数据
        summary = self.generate_executive_summary(brand_name, days)
        
        # 创建PDF文档
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # 样式设置
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # 居中
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.darkblue
        )
        
        # 添加标题
        title = Paragraph(f"品牌GEO运营分析报告 - {brand_name}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # 添加报告期间信息
        period_text = f"""
        报告期间: {summary['report_period']['start_date'][:10]} 至 {summary['report_period']['end_date'][:10]}<br/>
        数据天数: {summary['report_period']['days']} 天<br/>
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        period_para = Paragraph(period_text, styles['Normal'])
        elements.append(period_para)
        elements.append(Spacer(1, 20))
        
        # 添加ROI指标
        elements.append(Paragraph("ROI指标", subtitle_style))
        roi_data = [
            ['指标', '数值', '说明'],
            ['ROI得分', f"{summary['roi_metrics']['roi_score']}/100", '品牌运营效果评分'],
            ['投资价值', f"{summary['roi_metrics']['investment_value']:.2f}", '测试投入价值'],
            ['回报价值', f"{summary['roi_metrics']['return_value']:.2f}", '运营回报价值'],
            ['ROI百分比', f"{summary['roi_metrics']['roi_percentage']:.2f}%", '投资回报率'],
            ['置信度', summary['roi_metrics']['confidence_level'], '数据可靠性']
        ]
        roi_table = Table(roi_data)
        roi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(roi_table)
        elements.append(Spacer(1, 20))
        
        # 添加曝光指标
        elements.append(Paragraph("曝光指标", subtitle_style))
        exposure_data = [
            ['指标', '数值', '说明'],
            ['预估曝光增量', f"{summary['exposure_metrics']['estimated_exposure_increment']:.2f}%", '排名提升带来的曝光增长'],
            ['排名改善', f"{summary['exposure_metrics']['ranking_improvement']}", '排名变化情况'],
            ['情感趋势', summary['exposure_metrics']['sentiment_trend']['trend_direction'], '情感变化方向']
        ]
        exposure_table = Table(exposure_data)
        exposure_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(exposure_table)
        elements.append(Spacer(1, 20))
        
        # 添加关键洞察
        elements.append(Paragraph("关键洞察", subtitle_style))
        for insight in summary['key_insights']:
            elements.append(Paragraph(f"• {insight}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # 添加优化建议
        elements.append(Paragraph("优化建议", subtitle_style))
        for rec in summary['recommendations']:
            priority_color = {
                'high': colors.red,
                'medium': colors.orange,
                'low': colors.green
            }.get(rec['priority'], colors.black)
            
            rec_title = Paragraph(f"<font color='{priority_color}'>{rec['title']} ({rec['priority']}优先级)</font>", styles['Heading3'])
            elements.append(rec_title)
            elements.append(Paragraph(f"{rec['description']}", styles['Normal']))
            elements.append(Spacer(1, 10))
        
        # 构建PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data

    def get_hub_summary(self, brand_name: str, days: int = 7) -> Dict[str, Any]:
        """
        获取枢纽摘要数据（用于GET /hub/summary接口）

        Args:
            brand_name: 品牌名称
            days: 查询天数

        Returns:
            汇总数据字典
        """
        try:
            # 获取测试结果数据
            test_results = self._get_test_results(brand_name, days)
            
            # 获取巡航趋势数据
            trend_data = self.cruise_controller.get_trend_data(brand_name, days)
            
            # 计算关键指标
            roi_metrics = self._calculate_roi_metrics(test_results, trend_data)
            exposure_increment = self._calculate_exposure_increment(trend_data)
            ranking_improvement = self._calculate_ranking_improvement(trend_data)
            avg_score = self._calculate_avg_score(test_results)
            
            # 如果数据不足，返回合理的默认值
            if not test_results and not trend_data:
                return {
                    'brand_name': brand_name,
                    'summary_period': {
                        'start_date': (datetime.now() - timedelta(days=days)).isoformat(),
                        'end_date': datetime.now().isoformat(),
                        'days': days
                    },
                    'metrics': {
                        'roi_score': 0.0,
                        'roi_percentage': 0.0,
                        'estimated_exposure_increment': 0.0,
                        'ranking_improvement': 0,
                        'average_overall_score': 0.0,
                        'test_count': 0,
                        'trend_data_points': 0
                    },
                    'status': 'no_data',
                    'message': '暂无数据，请运行品牌测试以获取分析结果'
                }
            
            return {
                'brand_name': brand_name,
                'summary_period': {
                    'start_date': (datetime.now() - timedelta(days=days)).isoformat(),
                    'end_date': datetime.now().isoformat(),
                    'days': days
                },
                'metrics': {
                    'roi_score': roi_metrics['roi_score'],
                    'roi_percentage': roi_metrics['roi_percentage'],
                    'estimated_exposure_increment': exposure_increment,
                    'ranking_improvement': ranking_improvement,
                    'average_overall_score': avg_score,
                    'test_count': len(test_results),
                    'trend_data_points': len(trend_data)
                },
                'status': 'success',
                'message': '数据获取成功'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating hub summary for {brand_name}: {e}")
            return {
                'brand_name': brand_name,
                'summary_period': {
                    'start_date': (datetime.now() - timedelta(days=days)).isoformat(),
                    'end_date': datetime.now().isoformat(),
                    'days': days
                },
                'metrics': {
                    'roi_score': 0.0,
                    'roi_percentage': 0.0,
                    'estimated_exposure_increment': 0.0,
                    'ranking_improvement': 0,
                    'average_overall_score': 0.0,
                    'test_count': 0,
                    'trend_data_points': 0
                },
                'status': 'error',
                'message': f'数据获取失败: {str(e)}'
            }


# Example usage
if __name__ == "__main__":
    generator = ReportGenerator()
    
    # Example: Generate summary for a brand
    summary = generator.generate_executive_summary("TechBrand", days=30)
    
    print("Executive Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # Example: Get hub summary
    hub_summary = generator.get_hub_summary("TechBrand", days=7)
    
    print("\nHub Summary:")
    print(json.dumps(hub_summary, indent=2, ensure_ascii=False))