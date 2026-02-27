#!/usr/bin/env python3
"""
PDF 报告导出服务 - 增强版
支持完整的品牌诊断报告生成

版本：v2.0
日期：2026-02-21
"""

import io
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from wechat_backend.logging_config import api_logger


class EnhancedPDFExportService:
    """
    增强版 PDF 导出服务
    支持完整的品牌诊断报告生成
    """
    
    # 品牌色
    BRAND_COLORS = {
        'primary': HexColor('#1a1a2e'),
        'secondary': HexColor('#16213e'),
        'accent': HexColor('#0f3460'),
        'highlight': HexColor('#e94560'),
        'success': HexColor('#10b981'),
        'warning': HexColor('#f59e0b'),
        'error': HexColor('#ef4444'),
        'light': HexColor('#f8fafc'),
        'gray': HexColor('#64748b')
    }
    
    def __init__(self):
        self.logger = api_logger
        self.chinese_font_registered = False
        self.styles = {}
        self._register_chinese_font()
        self._create_styles()
    
    def _register_chinese_font(self):
        """注册中文字体"""
        font_paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttf'
        ]
        
        for font_path in font_paths:
            try:
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                self.chinese_font_registered = True
                self.logger.info(f"Registered Chinese font: {font_path}")
                return
            except Exception as e:
                self.logger.error(f"Error registering Chinese font {font_path}: {e}", exc_info=True)
                continue
        
        self.logger.warning("No Chinese font found, using default")
    
    def _create_styles(self):
        """创建样式"""
        font_name = 'Chinese' if self.chinese_font_registered else 'Helvetica'
        
        self.styles = {
            'reportTitle': ParagraphStyle(
                'ReportTitle',
                parent=getSampleStyleSheet()['Title'],
                fontName=font_name,
                fontSize=28,
                textColor=self.BRAND_COLORS['primary'],
                spaceAfter=30,
                alignment=TA_CENTER,
                leading=36
            ),
            'sectionTitle': ParagraphStyle(
                'SectionTitle',
                parent=getSampleStyleSheet()['Heading1'],
                fontName=font_name,
                fontSize=18,
                textColor=self.BRAND_COLORS['accent'],
                spaceAfter=20,
                spaceBefore=30,
                leading=24
            ),
            'subsectionTitle': ParagraphStyle(
                'SubsectionTitle',
                parent=getSampleStyleSheet()['Heading2'],
                fontName=font_name,
                fontSize=14,
                textColor=self.BRAND_COLORS['secondary'],
                spaceAfter=15,
                spaceBefore=20,
                leading=18
            ),
            'normal': ParagraphStyle(
                'Normal',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=10,
                textColor=self.BRAND_COLORS['primary'],
                spaceAfter=10,
                leading=14
            ),
            'metric': ParagraphStyle(
                'Metric',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=24,
                textColor=self.BRAND_COLORS['highlight'],
                alignment=TA_CENTER,
                leading=28
            ),
            'metricLabel': ParagraphStyle(
                'MetricLabel',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=9,
                textColor=self.BRAND_COLORS['gray'],
                alignment=TA_CENTER
            ),
            'gradeA': ParagraphStyle(
                'GradeA',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=32,
                textColor=self.BRAND_COLORS['success'],
                alignment=TA_CENTER
            ),
            'gradeB': ParagraphStyle(
                'GradeB',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=32,
                textColor=colors.blue,
                alignment=TA_CENTER
            ),
            'gradeC': ParagraphStyle(
                'GradeC',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=32,
                textColor=self.BRAND_COLORS['warning'],
                alignment=TA_CENTER
            ),
            'gradeD': ParagraphStyle(
                'GradeD',
                parent=getSampleStyleSheet()['Normal'],
                fontName=font_name,
                fontSize=32,
                textColor=self.BRAND_COLORS['error'],
                alignment=TA_CENTER
            )
        }
    
    def generate_enhanced_report(self, report_data: Dict[str, Any], 
                                  level: str = 'full',
                                  sections: str = 'all') -> bytes:
        """
        生成增强版报告
        
        Args:
            report_data: 完整报告数据
            level: 报告级别 (basic, detailed, full)
            sections: 需要的章节
        
        Returns:
            PDF 字节数据
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title="GEO 品牌战略诊断报告"
        )
        
        elements = []
        
        # 1. 封面
        elements.extend(self._create_cover(report_data))
        elements.append(PageBreak())
        
        # 2. 执行摘要
        if sections == 'all' or 'executiveSummary' in sections:
            elements.extend(self._create_executive_summary(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 3. 品牌健康度
        if level in ['detailed', 'full'] and (sections == 'all' or 'brandHealth' in sections):
            elements.extend(self._create_brand_health(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 4. 平台分析
        if level == 'full' and (sections == 'all' or 'platformAnalysis' in sections):
            elements.extend(self._create_platform_analysis(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 5. 竞品对比
        if level == 'full' and (sections == 'all' or 'competitiveAnalysis' in sections):
            elements.extend(self._create_competitive_analysis(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 6. 负面信源
        if level == 'full' and (sections == 'all' or 'negativeSources' in sections):
            elements.extend(self._create_negative_sources(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 7. ROI 指标
        if level == 'full' and (sections == 'all' or 'roiAnalysis' in sections):
            elements.extend(self._create_roi_analysis(report_data))
            elements.append(Spacer(1, 0.5*cm))
        
        # 8. 行动计划
        if level == 'full' and (sections == 'all' or 'actionPlan' in sections):
            elements.extend(self._create_action_plan(report_data))
        
        # 构建 PDF
        doc.build(elements)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        self.logger.info(f"Enhanced PDF generated: {len(pdf_data)} bytes")
        return pdf_data
    
    def _create_cover(self, report_data: Dict[str, Any]) -> List:
        """创建封面"""
        elements = []
        
        # 报告标题
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph("GEO 品牌战略诊断报告", self.styles['reportTitle']))
        
        # 品牌名称
        brand_name = report_data.get('reportMetadata', {}).get('brandName', '未知品牌')
        elements.append(Paragraph(f"—— {brand_name}", self.styles['sectionTitle']))
        
        elements.append(Spacer(1, 2*cm))
        
        # 健康度评分
        health_data = report_data.get('brandHealth', {})
        overall_score = health_data.get('overall_score', 0)
        health_grade = health_data.get('health_grade', 'B')
        
        grade_style = self.styles.get(f'grade{health_grade}', self.styles['gradeB'])
        
        elements.append(Paragraph("品牌健康度", self.styles['normal']))
        elements.append(Paragraph(f"{overall_score}", self.styles['metric']))
        elements.append(Paragraph(f"等级：{health_grade}", grade_style))
        
        elements.append(Spacer(1, 2*cm))
        
        # 报告信息
        metadata = report_data.get('reportMetadata', {})
        info_data = [
            ['报告版本:', metadata.get('reportVersion', '2.0')],
            ['生成时间:', metadata.get('generatedAt', '')[:19].replace('T', ' ')],
            ['执行 ID:', metadata.get('executionId', '')]
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Chinese'),
            ('FONTNAME', (1, 0), (1, -1), 'Chinese'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        
        # 页脚
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph("云程企航 · AI 搜索品牌影响力监测", self.styles['normal']))
        
        return elements
    
    def _create_executive_summary(self, report_data: Dict[str, Any]) -> List:
        """创建执行摘要"""
        elements = []
        
        elements.append(Paragraph("执行摘要", self.styles['sectionTitle']))
        
        summary = report_data.get('executiveSummary', {})
        
        # 核心发现
        elements.append(Paragraph("核心发现", self.styles['subsectionTitle']))
        
        key_findings = summary.get('key_findings', [])
        for finding in key_findings[:5]:
            elements.append(Paragraph(f"• {finding}", self.styles['normal']))
        
        elements.append(Spacer(1, 0.3*cm))
        
        # 优先级建议
        elements.append(Paragraph("优先级建议", self.styles['subsectionTitle']))
        
        recommendations = summary.get('priority_recommendations', [])
        for rec in recommendations[:3]:
            priority = rec.get('priority', 'medium')
            priority_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
            elements.append(Paragraph(
                f"{priority_icon} {rec.get('action', '')} ({rec.get('timeline', '')})",
                self.styles['normal']
            ))
        
        # 快速见效行动
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("快速见效行动", self.styles['subsectionTitle']))
        
        quick_wins = summary.get('quick_wins', [])
        for win in quick_wins[:3]:
            elements.append(Paragraph(f"✓ {win}", self.styles['normal']))
        
        return elements
    
    def _create_brand_health(self, report_data: Dict[str, Any]) -> List:
        """创建品牌健康度章节"""
        elements = []
        
        elements.append(Paragraph("品牌健康度诊断", self.styles['sectionTitle']))
        
        health_data = report_data.get('brandHealth', {})
        dimension_scores = health_data.get('dimension_scores', {})
        
        # 四维度表格
        elements.append(Paragraph("四维度评分", self.styles['subsectionTitle']))
        
        dimension_names = {
            'authority': '权威性',
            'visibility': '可见性',
            'purity': '纯净度',
            'consistency': '一致性'
        }
        
        table_data = [['维度', '评分', '等级']]
        for dim_key, dim_name in dimension_names.items():
            score = dimension_scores.get(dim_key, 0)
            if score >= 80:
                grade = 'A'
            elif score >= 70:
                grade = 'B'
            elif score >= 60:
                grade = 'C'
            else:
                grade = 'D'
            table_data.append([dim_name, f"{score}", grade])
        
        table = Table(table_data, colWidths=[4*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLORS['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Chinese'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_platform_analysis(self, report_data: Dict[str, Any]) -> List:
        """创建平台分析章节"""
        elements = []
        
        elements.append(Paragraph("AI 平台表现分析", self.styles['sectionTitle']))
        
        platform_scores = report_data.get('platformAnalysis', [])
        
        if platform_scores:
            table_data = [['平台', '评分', '排名', '情感']]
            for platform in platform_scores[:8]:
                table_data.append([
                    platform.get('platform', 'Unknown'),
                    f"{platform.get('score', 0)}",
                    f"#{platform.get('rank', 0)}",
                    f"{platform.get('sentiment', 0):.2f}"
                ])
            
            table = Table(table_data, colWidths=[4*cm, 2*cm, 2*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLORS['accent']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _create_competitive_analysis(self, report_data: Dict[str, Any]) -> List:
        """创建竞品分析章节"""
        elements = []
        
        elements.append(Paragraph("竞品对比分析", self.styles['sectionTitle']))
        
        comp_data = report_data.get('competitiveAnalysis', {})
        competitors = comp_data.get('competitors', [])
        comparison = comp_data.get('comparison_summary', {})
        
        # 对比摘要
        elements.append(Paragraph("竞争位置", self.styles['subsectionTitle']))
        
        elements.append(Paragraph(
            f"当前排名：第{comparison.get('my_rank', 0)}名 / 共{comparison.get('total_competitors', 0) + 1}个品牌",
            self.styles['normal']
        ))
        
        elements.append(Paragraph(
            f"与领导者差距：{comparison.get('gap_to_leader', 0)}分",
            self.styles['normal']
        ))
        
        # 竞品列表
        if competitors:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("竞品评分", self.styles['subsectionTitle']))
            
            table_data = [['竞品', '综合评分', '权威性', '可见性', '纯净度', '一致性']]
            for comp in competitors[:5]:
                table_data.append([
                    comp.get('competitor_name', 'Unknown'),
                    f"{comp.get('overall_score', 0)}",
                    f"{comp.get('authority_score', 0)}",
                    f"{comp.get('visibility_score', 0)}",
                    f"{comp.get('purity_score', 0)}",
                    f"{comp.get('consistency_score', 0)}"
                ])
            
            table = Table(table_data, colWidths=[3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLORS['accent']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _create_negative_sources(self, report_data: Dict[str, Any]) -> List:
        """创建负面信源章节"""
        elements = []
        
        elements.append(Paragraph("问题诊断与负面信源", self.styles['sectionTitle']))
        
        neg_data = report_data.get('negativeSources', {})
        sources = neg_data.get('sources', [])
        summary = neg_data.get('summary', {})
        
        # 摘要统计
        elements.append(Paragraph("负面信源统计", self.styles['subsectionTitle']))
        
        elements.append(Paragraph(
            f"总计：{summary.get('total_count', 0)}个 | "
            f"高危：{summary.get('critical_count', 0)}个 | "
            f"高：{summary.get('high_count', 0)}个 | "
            f"中：{summary.get('medium_count', 0)}个 | "
            f"低：{summary.get('low_count', 0)}个",
            self.styles['normal']
        ))
        
        # 高风险信源列表
        if sources:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("高风险信源详情", self.styles['subsectionTitle']))
            
            table_data = [['信源', '严重程度', '影响范围', '优先级', '应对建议']]
            for source in sources[:5]:
                severity = source.get('severity', 'low')
                severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
                
                table_data.append([
                    source.get('source_name', 'Unknown'),
                    f"{severity_icon} {severity}",
                    source.get('impact_scope', 'low'),
                    f"{source.get('priority_score', 0)}",
                    source.get('recommendation', '-')[:20]
                ])
            
            table = Table(table_data, colWidths=[3*cm, 2*cm, 2*cm, 1.5*cm, 4*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLORS['accent']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _create_roi_analysis(self, report_data: Dict[str, Any]) -> List:
        """创建 ROI 分析章节"""
        elements = []
        
        elements.append(Paragraph("ROI 指标分析", self.styles['sectionTitle']))
        
        roi_data = report_data.get('roiAnalysis', {})
        
        # ROI 指标表格
        table_data = [
            ['指标', '数值', '行业平均', '对比'],
            ['曝光 ROI', f"{roi_data.get('exposure_roi', 0)}x", '2.5x', ''],
            ['情感 ROI', f"{roi_data.get('sentiment_roi', 0)}x", '0.6x', ''],
            ['排名 ROI', f"{roi_data.get('ranking_roi', 0)}", '50', ''],
            ['综合 ROI', f"{roi_data.get('overall_roi', 0)} ({roi_data.get('roi_grade', 'B')})", '-', '']
        ]
        
        # 计算对比
        for i, row in enumerate(table_data[1:], 1):
            industry_avg = {'2.5x': 2.5, '0.6x': 0.6, '50': 50, '-': 0}.get(row[2], 0)
            actual = float(row[1].replace('x', '').split()[0]) if row[1] else 0
            if actual > industry_avg:
                row[3] = '✓ 优于行业'
            elif actual < industry_avg:
                row[3] = '✗ 低于行业'
            else:
                row[3] = '= 持平'
        
        table = Table(table_data, colWidths=[4*cm, 3*cm, 2.5*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLORS['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Chinese'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_action_plan(self, report_data: Dict[str, Any]) -> List:
        """创建行动计划章节"""
        elements = []
        
        elements.append(Paragraph("行动建议与实施计划", self.styles['sectionTitle']))
        
        action_plan = report_data.get('actionPlan', {})
        
        # 短期行动
        short_term = action_plan.get('short_term', [])
        if short_term:
            elements.append(Paragraph("短期行动 (1-4 周)", self.styles['subsectionTitle']))
            for action in short_term[:3]:
                elements.append(Paragraph(
                    f"🔴 {action.get('title', '')}",
                    self.styles['normal']
                ))
                elements.append(Paragraph(
                    f"   预计工时：{action.get('estimated_hours', 0)}小时 | "
                    f"预算：¥{action.get('estimated_budget', 0):,}",
                    self.styles['normal']
                ))
        
        # 中期行动
        mid_term = action_plan.get('mid_term', [])
        if mid_term:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("中期行动 (1-3 月)", self.styles['subsectionTitle']))
            for action in mid_term[:3]:
                elements.append(Paragraph(
                    f"🟡 {action.get('title', '')}",
                    self.styles['normal']
                ))
        
        # 长期行动
        long_term = action_plan.get('long_term', [])
        if long_term:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("长期行动 (3-6 月)", self.styles['subsectionTitle']))
            for action in long_term[:2]:
                elements.append(Paragraph(
                    f"🟢 {action.get('title', '')}",
                    self.styles['normal']
                ))
        
        # 资源汇总
        summary = action_plan.get('summary', {})
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("资源需求汇总", self.styles['subsectionTitle']))
        elements.append(Paragraph(
            f"总行动数：{summary.get('total_actions', 0)} | "
            f"预估工时：{summary.get('total_estimated_hours', 0)}小时 | "
            f"预估预算：¥{summary.get('total_estimated_budget', 0):,} | "
            f"预期评分提升：+{summary.get('expected_score_improvement', 0):.1f}分",
            self.styles['normal']
        ))
        
        return elements


# 全局服务实例
_enhanced_pdf_service = None


def get_enhanced_pdf_service() -> EnhancedPDFExportService:
    """获取增强版 PDF 服务实例"""
    global _enhanced_pdf_service
    if _enhanced_pdf_service is None:
        _enhanced_pdf_service = EnhancedPDFExportService()
    return _enhanced_pdf_service
