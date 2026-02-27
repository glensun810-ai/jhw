"""
诊断结果数据模型

用于存储每次 AI 调用的完整响应数据，包括 GEO 分析结果、质量评分等。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class DiagnosisResult:
    """
    诊断结果数据模型
    
    Attributes:
        report_id: 关联的报告 ID
        execution_id: 任务执行 ID
        brand: 品牌名称
        question: 问题内容
        model: AI 模型名称
        response: 完整的 API 响应（JSON）
        response_text: 提取的文本内容
        geo_data: GEO 分析结果
        exposure: 是否露出品牌
        sentiment: 情感倾向（positive/neutral/negative）
        keywords: 关键词列表
        quality_score: 质量评分（0-100）
        quality_level: 质量等级（high/medium/low/unknown）
        latency_ms: API 响应延迟
        error_message: 错误信息
        id: 数据库记录 ID
        data_version: 数据结构版本
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    # 关联信息
    report_id: int
    execution_id: str
    
    # 查询参数
    brand: str
    question: str
    model: str
    
    # 原始响应数据
    response: Dict[str, Any]
    response_text: Optional[str] = None
    
    # GEO 分析数据
    geo_data: Optional[Dict[str, Any]] = None
    exposure: bool = False
    sentiment: str = 'neutral'
    keywords: List[str] = field(default_factory=list)
    
    # 质量评分
    quality_score: Optional[float] = None
    quality_level: str = 'unknown'
    
    # 性能指标
    latency_ms: Optional[int] = None
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 元数据
    id: Optional[int] = None
    data_version: str = '1.0'
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 API 响应）
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        result = {
            'id': self.id,
            'report_id': self.report_id,
            'execution_id': self.execution_id,
            'brand': self.brand,
            'question': self.question,
            'model': self.model,
            'response': self.response,
            'exposure': self.exposure,
            'sentiment': self.sentiment,
            'keywords': self.keywords,
            'quality_score': self.quality_score,
            'quality_level': self.quality_level,
            'latency_ms': self.latency_ms,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
        }
        
        if self.geo_data:
            result['geo_data'] = self.geo_data
        
        return result
    
    def to_analysis_dict(self) -> Dict[str, Any]:
        """
        转换为分析用字典（简化版）
        
        Returns:
            Dict[str, Any]: 分析字典
        """
        return {
            'brand': self.brand,
            'model': self.model,
            'exposure': self.exposure,
            'sentiment': self.sentiment,
            'keywords': self.keywords,
            'quality_score': self.quality_score,
            'latency_ms': self.latency_ms,
        }
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'DiagnosisResult':
        """
        从数据库行记录创建对象
        
        Args:
            row: 数据库行记录
        
        Returns:
            DiagnosisResult: 诊断结果对象
        """
        return cls(
            id=row['id'],
            report_id=row['report_id'],
            execution_id=row['execution_id'],
            brand=row['brand'],
            question=row['question'],
            model=row['model'],
            response=json.loads(row['response']) if row['response'] else {},
            response_text=row['response_text'],
            geo_data=json.loads(row['geo_data']) if row.get('geo_data') else None,
            exposure=bool(row['exposure']),
            sentiment=row['sentiment'],
            keywords=json.loads(row['keywords']) if row.get('keywords') else [],
            quality_score=row['quality_score'],
            quality_level=row['quality_level'],
            latency_ms=row['latency_ms'],
            error_message=row['error_message'],
            data_version=row['data_version'],
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None,
        )
