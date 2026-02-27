"""
报告存根数据模型

用于在诊断失败、部分成功或超时时，返回有意义的报告存根。
确保用户永远不会看到空白页面，始终获得有意义的反馈。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from collections import Counter


class ReportStatus(str, Enum):
    """
    报告状态枚举

    Attributes:
        COMPLETED: 完全成功
        PARTIAL_SUCCESS: 部分成功
        FAILED: 完全失败
        TIMEOUT: 超时
        PROCESSING: 处理中（用于中间状态）
    """
    COMPLETED = 'completed'
    PARTIAL_SUCCESS = 'partial_success'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    PROCESSING = 'processing'


@dataclass
class StubReport:
    """
    报告存根数据模型

    当完整报告不可用时，返回存根报告。
    存根报告包含：
    - 基本信息（执行 ID、品牌、时间等）
    - 状态信息（成功/失败/部分成功）
    - 错误信息（如果有）
    - 已获取的部分数据（如果有）
    - 元数据（数据完整度、下一步建议等）

    Attributes:
        execution_id: 执行 ID
        report_id: 报告 ID（可选）
        brand_name: 品牌名称
        status: 报告状态
        progress: 进度（0-100）
        stage: 当前阶段
        created_at: 创建时间
        completed_at: 完成时间（可选）
        error_message: 错误信息（可选）
        error_details: 错误详情（可选）
        partial_results: 部分结果列表
        results_count: 结果总数
        successful_count: 成功结果数
        is_stub: 是否存根报告（默认 True）
        data_completeness: 数据完整度（0-100%）
        has_data: 是否有任何数据
        retry_suggestion: 重试建议（可选）
        next_steps: 下一步操作建议列表
    """

    # 基本信息（无默认值）
    execution_id: str
    report_id: Optional[int]
    brand_name: str
    status: ReportStatus
    created_at: datetime

    # 状态信息（有默认值）
    progress: int = 0
    stage: str = 'unknown'

    # 时间信息（有默认值）
    completed_at: Optional[datetime] = None

    # 错误信息（有默认值）
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # 部分数据（有默认值）
    partial_results: List[Dict[str, Any]] = field(default_factory=list)
    results_count: int = 0
    successful_count: int = 0

    # 元数据（有默认值）
    is_stub: bool = True
    data_completeness: float = 0.0
    has_data: bool = False
    retry_suggestion: Optional[str] = None

    # 下一步操作建议（有默认值）
    next_steps: List[str] = field(default_factory=lambda: [
        "查看部分结果",
        "重新诊断",
        "联系客服"
    ])

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 API 响应）

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            'report': {
                'execution_id': self.execution_id,
                'report_id': self.report_id,
                'brand_name': self.brand_name,
                'status': self.status.value,
                'progress': self.progress,
                'stage': self.stage,
                'created_at': self.created_at.isoformat(),
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            },
            'results': self.partial_results,
            'analysis': {
                'brand_distribution': self._calculate_brand_distribution(),
                'sentiment_distribution': self._calculate_sentiment_distribution(),
                'keywords': self._extract_keywords(),
            },
            'meta': {
                'is_stub': self.is_stub,
                'data_completeness': self.data_completeness,
                'has_data': self.has_data,
                'results_count': self.results_count,
                'successful_count': self.successful_count,
                'error_message': self.error_message,
                'error_details': self.error_details,
                'retry_suggestion': self.retry_suggestion,
                'next_steps': self.next_steps,
            },
            'checksum_verified': False,
        }

    def _calculate_brand_distribution(self) -> Dict[str, float]:
        """
        从部分结果计算品牌分布

        Returns:
            Dict[str, float]: 品牌分布字典 {品牌名：百分比}
        """
        if not self.partial_results:
            return {}

        brand_counts: Dict[str, int] = {}
        for result in self.partial_results:
            brand = result.get('brand', 'unknown')
            brand_counts[brand] = brand_counts.get(brand, 0) + 1

        total = sum(brand_counts.values())
        if total == 0:
            return {}

        return {
            brand: round(count / total * 100, 2)
            for brand, count in brand_counts.items()
        }

    def _calculate_sentiment_distribution(self) -> Dict[str, float]:
        """
        从部分结果计算情感分布

        Returns:
            Dict[str, float]: 情感分布字典 {情感类型：百分比}
        """
        if not self.partial_results:
            return {'positive': 0, 'neutral': 0, 'negative': 0}

        sentiment_counts: Dict[str, int] = {'positive': 0, 'neutral': 0, 'negative': 0}
        for result in self.partial_results:
            geo_data = result.get('geo_data', {})
            sentiment = geo_data.get('sentiment', 'neutral')
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            else:
                sentiment_counts['neutral'] += 1

        total = sum(sentiment_counts.values())
        return {
            k: round(v / total * 100, 2) if total > 0 else 0
            for k, v in sentiment_counts.items()
        }

    def _extract_keywords(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        从部分结果提取关键词

        Args:
            top_n: 返回前 N 个关键词

        Returns:
            List[Dict[str, Any]]: 关键词列表 [{'word': str, 'count': int}]
        """
        all_keywords: List[str] = []
        for result in self.partial_results:
            keywords = result.get('keywords', [])
            if isinstance(keywords, list):
                all_keywords.extend(keywords)

        if not all_keywords:
            return []

        counter = Counter(all_keywords)
        return [
            {'word': word, 'count': count}
            for word, count in counter.most_common(top_n)
        ]

    @classmethod
    def from_diagnosis_record(
        cls,
        execution_id: str,
        diagnosis_record: Dict[str, Any],
        partial_results: Optional[List[Dict]] = None,
    ) -> 'StubReport':
        """
        从诊断记录创建存根报告

        Args:
            execution_id: 执行 ID
            diagnosis_record: 诊断记录字典
            partial_results: 部分结果列表（可选）

        Returns:
            StubReport: 存根报告对象
        """
        # 确定状态
        status = ReportStatus.PROCESSING
        if diagnosis_record.get('is_completed'):
            diag_status = diagnosis_record.get('status', 'failed')
            if diag_status == 'completed':
                status = ReportStatus.COMPLETED
            elif diag_status == 'partial_success':
                status = ReportStatus.PARTIAL_SUCCESS
            elif diag_status == 'timeout':
                status = ReportStatus.TIMEOUT
            else:
                status = ReportStatus.FAILED

        # 计算数据完整度
        results_count = len(partial_results) if partial_results else 0
        successful_count = sum(
            1 for r in (partial_results or [])
            if not r.get('error_message')
        )

        data_completeness = 0.0
        expected = diagnosis_record.get('expected_results_count', 0)
        if expected and expected > 0:
            data_completeness = round(successful_count / expected * 100, 2)

        # 生成重试建议
        retry_suggestion: Optional[str] = None
        if status == ReportStatus.TIMEOUT:
            retry_suggestion = "诊断超时，建议减少选择的 AI 模型数量后重试"
        elif status == ReportStatus.FAILED:
            retry_suggestion = "诊断失败，请检查网络连接后重试"
        elif data_completeness < 50:
            retry_suggestion = "数据完整度较低，建议重新诊断"

        # 解析时间
        created_at = datetime.now()
        if diagnosis_record.get('created_at'):
            try:
                created_at = datetime.fromisoformat(diagnosis_record['created_at'])
            except (ValueError, TypeError):
                pass

        completed_at: Optional[datetime] = None
        if diagnosis_record.get('completed_at'):
            try:
                completed_at = datetime.fromisoformat(diagnosis_record['completed_at'])
            except (ValueError, TypeError):
                pass

        return cls(
            execution_id=execution_id,
            report_id=diagnosis_record.get('id'),
            brand_name=diagnosis_record.get('brand_name', '未知'),
            status=status,
            progress=diagnosis_record.get('progress', 0),
            stage=diagnosis_record.get('stage', 'unknown'),
            created_at=created_at,
            completed_at=completed_at,
            error_message=diagnosis_record.get('error_message'),
            error_details=diagnosis_record.get('error_details'),
            partial_results=partial_results or [],
            results_count=results_count,
            successful_count=successful_count,
            data_completeness=data_completeness,
            has_data=successful_count > 0,
            retry_suggestion=retry_suggestion,
        )

    @classmethod
    def create_for_not_found(
        cls,
        execution_id: str,
    ) -> 'StubReport':
        """
        创建"报告不存在"的存根

        Args:
            execution_id: 执行 ID

        Returns:
            StubReport: 存根报告对象
        """
        return cls(
            execution_id=execution_id,
            report_id=None,
            brand_name='未知',
            status=ReportStatus.FAILED,
            progress=0,
            stage='not_found',
            created_at=datetime.now(),
            error_message=f"未找到执行 ID 为 {execution_id} 的诊断记录",
            error_details={'execution_id': execution_id},
            is_stub=True,
            has_data=False,
            retry_suggestion="请确认执行 ID 是否正确，或重新发起诊断",
        )
