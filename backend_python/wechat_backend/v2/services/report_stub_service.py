"""
报告存根服务

用于在诊断失败、部分成功或超时时，生成有意义的报告存根。
确保用户永远不会看到空白页面，始终获得有意义的反馈。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from wechat_backend.v2.models.report_stub import StubReport, ReportStatus
from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
from wechat_backend.logging_config import api_logger


class ReportStubService:
    """
    报告存根服务

    职责：
    1. 当完整报告不可用时，生成存根报告
    2. 从诊断记录和已有结果构建存根
    3. 提供友好的错误信息和下一步建议
    4. 确保所有 API 请求都能返回有意义的报告

    使用示例:
        >>> service = ReportStubService()
        >>> stub = service.get_stub_report(execution_id='exec-123')
        >>> response = stub.to_dict()
    """

    def __init__(
        self,
        diagnosis_repo: Optional[DiagnosisRepository] = None,
        result_repo: Optional[DiagnosisResultRepository] = None,
    ):
        """
        初始化报告存根服务

        Args:
            diagnosis_repo: 诊断仓库实例（可选）
            result_repo: 诊断结果仓库实例（可选）
        """
        self.diagnosis_repo = diagnosis_repo or DiagnosisRepository()
        self.result_repo = result_repo or DiagnosisResultRepository()

        api_logger.info(
            "report_stub_service_initialized",
            extra={
                'event': 'report_stub_service_initialized',
            }
        )

    def get_stub_report(
        self,
        execution_id: str,
        include_partial_results: bool = True,
    ) -> StubReport:
        """
        获取存根报告

        流程：
        1. 查询诊断记录
        2. 如果存在，从诊断记录构建存根
        3. 如果不存在，返回基本错误存根
        4. 可选包含部分结果

        Args:
            execution_id: 执行 ID
            include_partial_results: 是否包含部分结果数据

        Returns:
            StubReport: 存根报告对象
        """
        # 1. 查询诊断记录
        diagnosis_record = self.diagnosis_repo.get_by_execution_id(execution_id)

        if not diagnosis_record:
            # 诊断记录完全不存在，返回基本错误存根
            api_logger.warning(
                "diagnosis_record_not_found",
                extra={
                    'event': 'diagnosis_record_not_found',
                    'execution_id': execution_id,
                }
            )
            return StubReport.create_for_not_found(execution_id)

        # 2. 获取部分结果（如果需要）
        partial_results: List[Dict[str, Any]] = []
        if include_partial_results:
            results = self.result_repo.get_by_execution_id(execution_id, limit=100)
            partial_results = [r.to_dict() for r in results]

        # 3. 从诊断记录构建存根
        stub = StubReport.from_diagnosis_record(
            execution_id=execution_id,
            diagnosis_record=diagnosis_record,
            partial_results=partial_results,
        )

        api_logger.info(
            "stub_report_generated",
            extra={
                'event': 'stub_report_generated',
                'execution_id': execution_id,
                'status': stub.status.value,
                'has_data': stub.has_data,
                'data_completeness': stub.data_completeness,
            }
        )

        return stub

    def get_stub_for_failed_task(
        self,
        execution_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> StubReport:
        """
        为失败任务创建存根报告

        用于任务创建失败等无法获取诊断记录的场景

        Args:
            execution_id: 执行 ID
            error_message: 错误信息
            error_details: 错误详情（可选）

        Returns:
            StubReport: 存根报告对象
        """
        stub = StubReport(
            execution_id=execution_id,
            report_id=None,
            brand_name='未知',
            status=ReportStatus.FAILED,
            progress=0,
            stage='failed',
            created_at=datetime.now(),
            error_message=error_message,
            error_details=error_details,
            is_stub=True,
            has_data=False,
            retry_suggestion="请稍后重试或联系客服",
        )

        api_logger.info(
            "failed_task_stub_created",
            extra={
                'event': 'failed_task_stub_created',
                'execution_id': execution_id,
                'error_message': error_message,
            }
        )

        return stub

    def get_stub_for_timeout(
        self,
        execution_id: str,
        diagnosis_record: Optional[Dict[str, Any]] = None,
        partial_results: Optional[List[Dict[str, Any]]] = None,
    ) -> StubReport:
        """
        为超时任务创建存根报告

        Args:
            execution_id: 执行 ID
            diagnosis_record: 诊断记录（可选）
            partial_results: 部分结果（可选）

        Returns:
            StubReport: 存根报告对象
        """
        if diagnosis_record:
            return StubReport.from_diagnosis_record(
                execution_id=execution_id,
                diagnosis_record=diagnosis_record,
                partial_results=partial_results,
            )

        stub = StubReport(
            execution_id=execution_id,
            report_id=None,
            brand_name='未知',
            status=ReportStatus.TIMEOUT,
            progress=0,
            stage='timeout',
            created_at=datetime.now(),
            error_message="诊断任务执行超时",
            error_details={'timeout_seconds': 600},
            partial_results=partial_results or [],
            has_data=len(partial_results or []) > 0,
            retry_suggestion="建议减少选择的 AI 模型数量后重试",
        )

        api_logger.info(
            "timeout_stub_created",
            extra={
                'event': 'timeout_stub_created',
                'execution_id': execution_id,
                'has_data': stub.has_data,
            }
        )

        return stub

    def enhance_with_suggestions(
        self,
        stub: StubReport,
        user_history: Optional[List[Dict[str, Any]]] = None,
    ) -> StubReport:
        """
        为存根报告添加智能建议

        基于用户历史、错误类型等提供个性化建议

        Args:
            stub: 存根报告对象
            user_history: 用户历史记录（可选）

        Returns:
            StubReport: 增强后的存根报告
        """
        suggestions: List[str] = []

        # 基于状态添加建议
        if stub.status == ReportStatus.TIMEOUT:
            suggestions.append("选择较少的 AI 模型可以加快诊断速度")
            suggestions.append("尝试在非高峰时段进行诊断")

        elif stub.status == ReportStatus.FAILED:
            if stub.error_message:
                if 'API key' in stub.error_message or 'API 密钥' in stub.error_message:
                    suggestions.append("请检查 API 密钥配置")
                elif 'network' in stub.error_message.lower() or '网络' in stub.error_message:
                    suggestions.append("请检查网络连接")
                else:
                    suggestions.append("请稍后重试，如问题持续请联系客服")
            else:
                suggestions.append("请稍后重试或联系客服")

        elif stub.data_completeness < 50:
            suggestions.append("部分 AI 平台响应失败，建议重新诊断")

        # 基于用户历史（如果有）
        if user_history and len(user_history) > 0:
            last_success = next(
                (h for h in user_history if h.get('status') == 'completed'),
                None,
            )
            if last_success:
                created_at = last_success.get('created_at', '')
                if created_at:
                    suggestions.append(f"上次成功诊断于 {created_at[:10]}")

        # 合并建议（新建议在前）
        stub.next_steps = suggestions + stub.next_steps

        api_logger.info(
            "stub_suggestions_enhanced",
            extra={
                'event': 'stub_suggestions_enhanced',
                'execution_id': stub.execution_id,
                'suggestions_count': len(suggestions),
            }
        )

        return stub

    def should_return_stub(self, report_data: Optional[Dict[str, Any]]) -> bool:
        """
        判断是否应该返回存根报告

        条件：
        1. 报告数据为 None
        2. 报告数据为空
        3. 报告状态为失败/超时/部分成功

        Args:
            report_data: 报告数据字典

        Returns:
            bool: 是否应该返回存根
        """
        if report_data is None:
            return True

        # 检查结果和分析是否为空
        has_results = bool(report_data.get('results'))
        has_analysis = bool(report_data.get('analysis'))

        if not has_results and not has_analysis:
            return True

        # 检查状态
        status = report_data.get('report', {}).get('status')
        if status in ['failed', 'timeout', 'partial_success']:
            return True

        return False

    def get_user_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取用户历史诊断记录

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        try:
            # 从诊断仓库获取用户历史
            # 注意：这里需要 DiagnosisRepository 支持按用户 ID 查询
            # 如果未实现，返回空列表
            if hasattr(self.diagnosis_repo, 'get_by_user_id'):
                records = self.diagnosis_repo.get_by_user_id(user_id, limit=limit)
                return records or []
            return []
        except Exception:
            # 获取历史失败不影响主流程
            return []
