"""
API 响应类型定义

与 OpenAPI 规范保持一致，用于：
1. 类型提示
2. 契约测试
3. 数据验证

作者：系统架构组
日期：2026-03-01
版本：1.0
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================

class ReportStatus(str, Enum):
    """报告状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportStage(str, Enum):
    """报告阶段"""
    INIT = "init"
    AI_FETCHING = "ai_fetching"
    INTELLIGENCE_ANALYZING = "intelligence_analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityLevel(str, Enum):
    """质量等级"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SentimentLabel(str, Enum):
    """情感标签"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ErrorStatus(str, Enum):
    """错误状态"""
    NOT_FOUND = "not_found"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_RESULTS = "no_results"
    ERROR = "error"


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# ==================== 数据类 ====================

@dataclass
class GeoData:
    """GEO 分析数据"""
    brand_mentioned: bool = False
    rank: int = -1
    sentiment: float = 0.0
    cited_sources: List[str] = field(default_factory=list)
    keywords: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Response:
    """AI 响应"""
    content: str = ""
    latency: float = 0.0


@dataclass
class Result:
    """诊断结果"""
    id: Optional[int] = None
    brand: str = ""
    question: str = ""
    model: str = ""
    response: Optional[Response] = None
    geo_data: Optional[GeoData] = None
    quality_score: float = 0.0
    quality_level: QualityLevel = QualityLevel.MEDIUM


@dataclass
class Analysis:
    """分析数据"""
    competitive_analysis: Dict[str, Any] = field(default_factory=dict)
    brand_scores: Dict[str, Any] = field(default_factory=dict)
    semantic_drift: Dict[str, Any] = field(default_factory=dict)
    source_purity: Dict[str, Any] = field(default_factory=dict)
    recommendations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandDistribution:
    """品牌分布"""
    data: Dict[str, int] = field(default_factory=dict)
    total_count: int = 0


@dataclass
class SentimentDistribution:
    """情感分布"""
    data: Dict[str, int] = field(default_factory=dict)
    total_count: int = 0


@dataclass
class Keyword:
    """关键词"""
    word: str = ""
    count: int = 0
    sentiment: float = 0.0
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL


@dataclass
class Meta:
    """元数据"""
    data_schema_version: str = "1.0"
    server_version: str = "2.0.0"
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationDetails:
    """验证详情"""
    report_valid: bool = True
    results_valid: bool = True
    analysis_valid: bool = True
    aggregation_valid: bool = True
    checksum_valid: bool = True


@dataclass
class Validation:
    """验证信息"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    quality_score: int = 100
    details: Optional[ValidationDetails] = None


@dataclass
class QualityHints:
    """质量提示"""
    has_low_quality_results: bool = False
    has_partial_analysis: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class ErrorInfo:
    """错误信息"""
    status: ErrorStatus = ErrorStatus.ERROR
    message: str = ""
    suggestion: str = ""
    stage: Optional[str] = None


@dataclass
class PartialInfo:
    """部分结果信息"""
    is_partial: bool = False
    progress: int = 0
    stage: str = ""
    message: str = ""
    suggestion: str = ""


@dataclass
class Report:
    """报告主数据"""
    id: Optional[int] = None
    execution_id: str = ""
    user_id: str = ""
    brand_name: str = ""
    status: ReportStatus = ReportStatus.PENDING
    progress: int = 0
    stage: ReportStage = ReportStage.INIT
    is_completed: bool = False
    created_at: str = ""
    completed_at: Optional[str] = None
    checksum: Optional[str] = None


@dataclass
class FullReportResponse:
    """完整报告响应"""
    report: Report
    results: List[Result] = field(default_factory=list)
    analysis: Analysis = field(default_factory=Analysis)
    brand_distribution: BrandDistribution = field(default_factory=BrandDistribution)
    sentiment_distribution: SentimentDistribution = field(default_factory=SentimentDistribution)
    keywords: List[Keyword] = field(default_factory=list)
    meta: Meta = field(default_factory=Meta)
    validation: Validation = field(default_factory=Validation)
    quality_hints: QualityHints = field(default_factory=QualityHints)
    error: Optional[ErrorInfo] = None
    partial: Optional[PartialInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 JSON 序列化）"""
        return {
            'report': {
                'id': self.report.id,
                'execution_id': self.report.execution_id,
                'user_id': self.report.user_id,
                'brand_name': self.report.brand_name,
                'status': self.report.status.value,
                'progress': self.report.progress,
                'stage': self.report.stage.value,
                'is_completed': self.report.is_completed,
                'created_at': self.report.created_at,
                'completed_at': self.report.completed_at,
                'checksum': self.report.checksum
            },
            'results': [
                {
                    'id': r.id,
                    'brand': r.brand,
                    'question': r.question,
                    'model': r.model,
                    'response': {'content': r.response.content, 'latency': r.response.latency} if r.response else None,
                    'geo_data': vars(r.geo_data) if r.geo_data else None,
                    'quality_score': r.quality_score,
                    'quality_level': r.quality_level.value
                }
                for r in self.results
            ],
            'analysis': vars(self.analysis),
            'brandDistribution': vars(self.brand_distribution),
            'sentimentDistribution': vars(self.sentiment_distribution),
            'keywords': [vars(kw) for kw in self.keywords],
            'meta': vars(self.meta),
            'validation': {
                'is_valid': self.validation.is_valid,
                'errors': self.validation.errors,
                'warnings': self.validation.warnings,
                'quality_issues': self.validation.quality_issues,
                'quality_score': self.validation.quality_score,
                'details': vars(self.validation.details) if self.validation.details else None
            },
            'qualityHints': vars(self.quality_hints),
            'error': vars(self.error) if self.error else None,
            'partial': vars(self.partial) if self.partial else None
        }


@dataclass
class ReportSummary:
    """报告摘要"""
    id: int = 0
    execution_id: str = ""
    brand_name: str = ""
    status: str = ""
    progress: int = 0
    created_at: str = ""


@dataclass
class Pagination:
    """分页信息"""
    page: int = 1
    limit: int = 20
    total: int = 0
    has_more: bool = False


@dataclass
class HistoryResponse:
    """历史报告响应"""
    reports: List[ReportSummary] = field(default_factory=list)
    pagination: Pagination = field(default_factory=Pagination)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'reports': [vars(r) for r in self.reports],
            'pagination': vars(self.pagination)
        }


@dataclass
class TaskStatusResponse:
    """任务状态响应"""
    execution_id: str = ""
    status: str = ""
    progress: int = 0
    stage: str = ""
    results_count: int = 0
    total_tasks: int = 0
    should_stop_polling: bool = False
    detailed_results: List[Result] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'execution_id': self.execution_id,
            'status': self.status,
            'progress': self.progress,
            'stage': self.stage,
            'results_count': self.results_count,
            'total_tasks': self.total_tasks,
            'should_stop_polling': self.should_stop_polling,
            'detailed_results': [
                {
                    'id': r.id,
                    'brand': r.brand,
                    'question': r.question,
                    'model': r.model,
                    'response': {'content': r.response.content, 'latency': r.response.latency} if r.response else None,
                    'geo_data': vars(r.geo_data) if r.geo_data else None,
                    'quality_score': r.quality_score,
                    'quality_level': r.quality_level.value
                }
                for r in self.detailed_results
            ]
        }


@dataclass
class ValidationResponse:
    """验证响应"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_score: int = 100
    checksum_verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'quality_score': self.quality_score,
            'checksum_verified': self.checksum_verified
        }


@dataclass
class HealthResponse:
    """健康检查响应"""
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    services: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp,
            'services': self.services
        }


# ==================== 错误响应 ====================

@dataclass
class NotFoundError:
    """404 错误"""
    error: str = "报告不存在"
    execution_id: str = ""
    suggestion: str = "请检查执行 ID 是否正确，或重新进行诊断"
    
    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class ServerError:
    """500 错误"""
    error: str = "获取报告失败"
    message: str = ""
    execution_id: str = ""
    suggestion: str = "请稍后重试或联系技术支持"
    
    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class AuthError:
    """401 错误"""
    error: str = "未认证"
    message: str = "请先登录"
    
    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class RateLimitError:
    """429 错误"""
    error: str = "请求频率超限"
    retry_after: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


# ==================== 类型别名 ====================

ReportDict = Dict[str, Any]
ResultsList = List[Dict[str, Any]]
AnalysisDict = Dict[str, Any]
ValidationDict = Dict[str, Any]


# ==================== 工具函数 ====================

def create_empty_report(execution_id: str = "") -> FullReportResponse:
    """创建空报告响应"""
    return FullReportResponse(
        report=Report(execution_id=execution_id),
        results=[],
        analysis=Analysis(),
        brand_distribution=BrandDistribution(),
        sentiment_distribution=SentimentDistribution(),
        keywords=[],
        validation=Validation(
            is_valid=False,
            errors=["报告为空"],
            quality_score=0
        )
    )


def create_error_report(
    execution_id: str,
    status: ErrorStatus,
    message: str,
    suggestion: str
) -> FullReportResponse:
    """创建错误报告响应"""
    return FullReportResponse(
        report=Report(execution_id=execution_id, status=ReportStatus.FAILED),
        results=[],
        analysis=Analysis(),
        brand_distribution=BrandDistribution(),
        sentiment_distribution=SentimentDistribution(),
        keywords=[],
        error=ErrorInfo(
            status=status,
            message=message,
            suggestion=suggestion
        ),
        validation=Validation(
            is_valid=False,
            errors=[message],
            quality_score=0
        )
    )


__all__ = [
    # 枚举
    'ReportStatus',
    'ReportStage',
    'QualityLevel',
    'SentimentLabel',
    'ErrorStatus',
    'HealthStatus',
    
    # 数据类
    'GeoData',
    'Response',
    'Result',
    'Analysis',
    'BrandDistribution',
    'SentimentDistribution',
    'Keyword',
    'Meta',
    'Validation',
    'ValidationDetails',
    'QualityHints',
    'ErrorInfo',
    'PartialInfo',
    'Report',
    'FullReportResponse',
    'ReportSummary',
    'Pagination',
    'HistoryResponse',
    'TaskStatusResponse',
    'ValidationResponse',
    'HealthResponse',
    
    # 错误
    'NotFoundError',
    'ServerError',
    'AuthError',
    'RateLimitError',
    
    # 类型别名
    'ReportDict',
    'ResultsList',
    'AnalysisDict',
    'ValidationDict',
    
    # 工具函数
    'create_empty_report',
    'create_error_report'
]
