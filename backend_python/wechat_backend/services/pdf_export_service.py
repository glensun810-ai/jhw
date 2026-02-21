#!/usr/bin/env python3
"""
PDF 报告导出服务
支持中文 PDF 报告生成
"""

import io
import json
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from wechat_backend.logging_config import api_logger


class PDFExportService:
    """PDF 导出服务"""
    
    def __init__(self):
        self.logger = api_logger
        self.chinese_font_registered = False
        self._register_chinese_font()
    
    def _register_chinese_font(self):
        """注册中文字体以支持中文 PDF"""
        try:
            # 尝试注册常见中文字体
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/System/Library/Fonts/STHeiti Light.ttc',  # macOS
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # Linux
                'C:/Windows/Fonts/simhei.ttf',  # Windows
                'C:/Windows/Fonts/msyh.ttf'  # Windows 微软雅黑
            ]
            
            for font_path in font_paths:
                try:
                    pdfmetrics.registerFont(TTFont('Chinese', font_path))
                    self.chinese_font_registered = True
                    self.logger.info(f"Registered Chinese font: {font_path}")
                    return
                except Exception:
                    continue
            
            # 如果都没找到，使用默认字体
            self.logger.warning("No Chinese font found, using default font")
        except Exception as e:
            self.logger.error(f"Error registering Chinese font: {e}")
    
    def generate_test_report(self, test_data: Dict[str, Any]) -> bytes:
        """
        生成测试报告 PDF
        
        Args:
            test_data: 测试数据字典，包含：
                - executionId: 执行 ID
                - brandName: 品牌名称
                - competitorBrands: 竞品品牌列表
                - aiModels: 使用的 AI 模型
                - overallScore: 总体评分
                - platformScores: 各平台评分
                - dimensionScores: 各维度评分
                - testDate: 测试日期
                - recommendations: 优化建议
        
        Returns:
            PDF 文件的字节数据
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        styles = self._create_styles()
        
        # 添加标题
        elements.append(self._create_title(test_data.get('brandName', '品牌诊断报告'), styles))
        elements.append(Spacer(1, 20))
        
        # 添加基本信息
        elements.append(self._create_basic_info(test_data, styles))
        elements.append(Spacer(1, 20))
        
        # 添加总体评分
        elements.append(self._create_overall_score(test_data, styles))
        elements.append(Spacer(1, 20))
        
        # 添加平台评分
        if test_data.get('platformScores'):
            elements.append(self._create_platform_scores(test_data['platformScores'], styles))
            elements.append(Spacer(1, 20))
        
        # 添加维度评分
        if test_data.get('dimensionScores'):
            elements.append(self._create_dimension_scores(test_data['dimensionScores'], styles))
            elements.append(Spacer(1, 20))
        
        # 添加优化建议
        if test_data.get('recommendations'):
            elements.append(self._create_recommendations(test_data['recommendations'], styles))
        
        # 构建 PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """创建样式"""
        styles = getSampleStyleSheet()
        
        # 中文字体样式
        font_name = 'Chinese' if self.chinese_font_registered else 'Helvetica'
        
        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=font_name,
            leading=32
        )
        
        # 副标题样式
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=10,
            textColor=colors.darkblue,
            fontName=font_name,
            leading=24
        )
        
        # 正文样式
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            fontName=font_name,
            leading=14
        )
        
        return {
            'title': title_style,
            'subtitle': subtitle_style,
            'normal': normal_style,
            'heading': styles['Heading3']
        }
    
    def _create_title(self, brand_name: str, styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建标题"""
        title = f"品牌 AI 认知诊断报告"
        subtitle = f"—— {brand_name}"
        
        title_para = Paragraph(title, styles['title'])
        subtitle_para = Paragraph(subtitle, styles['subtitle'])
        
        # 返回包含标题和副标题的容器
        from reportlab.platypus import Flowable
        class TitleFlowable(Flowable):
            def __init__(self, title, subtitle):
                Flowable.__init__(self)
                self.title = title
                self.subtitle = subtitle
            
            def draw(self):
                self.canv.setFont('Chinese' if self.chinese_font_registered else 'Helvetica-Bold', 24)
                self.canv.drawCentredString(0, 0, self.title)
        
        return title_para
    
    def _create_basic_info(self, test_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建基本信息"""
        test_date = test_data.get('testDate', datetime.now().strftime('%Y-%m-%d'))
        ai_models = ', '.join(test_data.get('aiModels', []))
        competitors = ', '.join(test_data.get('competitorBrands', []))
        
        info_text = f"""
        <b>测试日期：</b>{test_date}<br/>
        <b>测试品牌：</b>{test_data.get('brandName', 'N/A')}<br/>
        <b>竞品对比：</b>{competitors if competitors else '无'}<br/>
        <b>AI 模型：</b>{ai_models if ai_models else '无'}<br/>
        <b>报告生成时间：</b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return Paragraph(info_text, styles['normal'])
    
    def _create_overall_score(self, test_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建总体评分"""
        overall_score = test_data.get('overallScore', 0)
        
        # 根据评分确定等级和颜色
        if overall_score >= 90:
            level = '优秀'
            color = 'green'
        elif overall_score >= 75:
            level = '良好'
            color = 'blue'
        elif overall_score >= 60:
            level = '中等'
            color = 'orange'
        else:
            level = '待改进'
            color = 'red'
        
        score_text = f"""
        <b>总体评分：</b><font color="{color}" size="16">{overall_score}</font> / 100<br/>
        <b>评级：</b><font color="{color}">{level}</font>
        """
        
        return Paragraph(score_text, styles['normal'])
    
    def _create_platform_scores(self, platform_scores: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建平台评分表格"""
        elements = []
        elements.append(Paragraph("各平台评分", styles['subtitle']))
        elements.append(Spacer(1, 10))
        
        # 创建表格数据
        data = [['平台', '评分', '等级']]
        for ps in platform_scores:
            platform = ps.get('platform', 'N/A')
            score = ps.get('score', 0)
            
            if score >= 90:
                level = '优秀'
            elif score >= 75:
                level = '良好'
            elif score >= 60:
                level = '中等'
            else:
                level = '待改进'
            
            data.append([platform, f"{score}", level])
        
        # 创建表格
        table = Table(data, colWidths=[4*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        from reportlab.platypus import Flowable
        class TableFlowable(Flowable):
            def __init__(self, table):
                Flowable.__init__(self)
                self.table = table
            
            def draw(self):
                self.table.drawOn(self.canv, 0, 0)
        
        elements.append(table)
        
        # 简单返回表格说明
        return Paragraph(f"共测试 {len(platform_scores)} 个 AI 平台，详见表格", styles['normal'])
    
    def _create_dimension_scores(self, dimension_scores: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建维度评分"""
        elements = []
        elements.append(Paragraph("维度分析", styles['subtitle']))
        elements.append(Spacer(1, 10))
        
        # 创建表格数据
        data = [['维度', '评分', '说明']]
        dimensions = [
            ('权威性', dimension_scores.get('authority', 0), '品牌在 AI 回复中的权威程度'),
            ('可见性', dimension_scores.get('visibility', 0), '品牌被 AI 提及的频率'),
            ('纯净度', dimension_scores.get('purity', 0), '品牌信息的准确性'),
            ('一致性', dimension_scores.get('consistency', 0), '跨平台信息一致性')
        ]
        
        for dim_name, score, desc in dimensions:
            data.append([dim_name, f"{score}", desc])
        
        # 创建表格
        table = Table(data, colWidths=[2*cm, 1.5*cm, 4.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        from reportlab.platypus import Flowable
        class TableFlowable(Flowable):
            def __init__(self, table):
                Flowable.__init__(self)
                self.table = table
            
            def draw(self):
                self.table.drawOn(self.canv, 0, 0)
        
        elements.append(table)
        
        return Paragraph("各维度评分详见表格", styles['normal'])
    
    def _create_recommendations(self, recommendations: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle]) -> Paragraph:
        """创建优化建议"""
        elements = []
        elements.append(Paragraph("优化建议", styles['subtitle']))
        elements.append(Spacer(1, 10))
        
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'medium')
            priority_text = {'high': '高', 'medium': '中', 'low': '低'}.get(priority, priority)
            priority_color = {'high': 'red', 'medium': 'orange', 'low': 'green'}.get(priority, 'black')
            
            rec_text = f"""
            <b>{i}. {rec.get('title', '建议')}</b> <font color="{priority_color}">[{priority_text}优先级]</font><br/>
            {rec.get('description', '')}<br/>
            """
            
            elements.append(Paragraph(rec_text, styles['normal']))
            elements.append(Spacer(1, 10))
        
        return Paragraph("共{}条优化建议，详见上文".format(len(recommendations)), styles['normal'])


# 全局服务实例
_pdf_export_service = None


def get_pdf_export_service() -> PDFExportService:
    """获取 PDF 导出服务实例"""
    global _pdf_export_service
    if _pdf_export_service is None:
        _pdf_export_service = PDFExportService()
    return _pdf_export_service
