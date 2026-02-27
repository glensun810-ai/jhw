"""
诊断报告 API v2

提供诊断报告查询接口，支持在完整报告不可用时返回存根报告。
确保用户永远不会看到空白页面，始终获得有意义的反馈。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify

from wechat_backend.v2.services.report_stub_service import ReportStubService
from wechat_backend.v2.services.diagnosis_service import DiagnosisService
from wechat_backend.v2.feature_flags import is_feature_enabled
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import DiagnosisError

# 创建 Blueprint
report_bp = Blueprint('report_v2', __name__, url_prefix='/api/v2/diagnostic')

# 服务实例
stub_service = ReportStubService()
diagnosis_service = DiagnosisService()


@report_bp.route('/tasks/<task_id>/report', methods=['GET'])
def get_report(task_id: str) -> Dict[str, Any]:
    """
    获取诊断报告

    如果完整报告可用，返回完整报告
    否则返回存根报告（确保用户获得有意义的反馈）

    Path Parameters:
        task_id: 任务 ID（执行 ID）

    Query Parameters:
        include_partial: 是否包含部分结果（默认 true）

    Returns:
        完整报告或存根报告

    Example:
        GET /api/v2/diagnostic/tasks/exec-123/report
    """
    try:
        # 1. 检查是否启用存根功能
        use_stub = is_feature_enabled('diagnosis_v2_report_stub')

        # 2. 尝试获取完整报告
        full_report: Optional[Dict[str, Any]] = None
        try:
            full_report = diagnosis_service.get_report(task_id)
        except Exception:
            # 获取完整报告失败，继续返回存根
            pass

        # 3. 判断是否需要返回存根
        if use_stub and (full_report is None or stub_service.should_return_stub(full_report)):
            include_partial = request.args.get('include_partial', 'true').lower() != 'false'

            # 获取存根报告
            stub = stub_service.get_stub_report(
                execution_id=task_id,
                include_partial_results=include_partial,
            )

            # 添加智能建议
            user_id = request.headers.get('X-User-ID', request.args.get('user_id', ''))
            if user_id:
                user_history = stub_service.get_user_history(user_id, limit=5)
                stub = stub_service.enhance_with_suggestions(stub, user_history)

            api_logger.info(
                "stub_report_returned",
                extra={
                    'event': 'stub_report_returned',
                    'execution_id': task_id,
                    'status': stub.status.value,
                    'has_data': stub.has_data,
                    'data_completeness': stub.data_completeness,
                }
            )

            return jsonify(stub.to_dict())

        # 4. 返回完整报告
        if full_report:
            return jsonify(full_report)

        # 5. 兜底：如果上面都没返回，返回 404 带存根
        stub = stub_service.get_stub_for_failed_task(
            execution_id=task_id,
            error_message="报告不存在",
            error_details={'reason': 'execution_id_not_found'},
        )

        api_logger.warning(
            "report_not_found_returning_stub",
            extra={
                'event': 'report_not_found_returning_stub',
                'execution_id': task_id,
            }
        )

        return jsonify(stub.to_dict()), 404

    except DiagnosisError as e:
        api_logger.error(
            "get_report_diagnosis_error",
            extra={
                'event': 'get_report_diagnosis_error',
                'execution_id': task_id,
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )

        # 返回错误存根
        stub = stub_service.get_stub_for_failed_task(
            execution_id=task_id,
            error_message=str(e),
            error_details=e.to_dict(),
        )
        return jsonify(stub.to_dict()), e.status_code

    except Exception as e:
        api_logger.error(
            "get_report_error",
            extra={
                'event': 'get_report_error',
                'execution_id': task_id,
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )

        # 返回错误存根
        stub = stub_service.get_stub_for_failed_task(
            execution_id=task_id,
            error_message=str(e),
            error_details={'type': type(e).__name__},
        )
        return jsonify(stub.to_dict()), 500


@report_bp.route('/tasks/<task_id>/status', methods=['GET'])
def get_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态

    即使任务失败，也返回有意义的状态信息

    Path Parameters:
        task_id: 任务 ID（执行 ID）

    Returns:
        任务状态信息

    Example:
        GET /api/v2/diagnostic/tasks/exec-123/status
    """
    try:
        # 尝试从诊断服务获取状态
        try:
            status = diagnosis_service.get_diagnosis_state(task_id)

            # 如果状态显示已完成但报告可能为空，返回状态时带上提示
            if status.get('is_completed') and not status.get('has_data'):
                status['warning'] = '任务已完成但部分数据可能缺失'
                status['next_step'] = '查看存根报告'

            return jsonify(status)

        except Exception:
            # 诊断服务获取失败，尝试从仓库获取
            from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
            repo = DiagnosisRepository()
            state = repo.get_state(task_id)

            if state:
                return jsonify({
                    **state,
                    'execution_id': task_id,
                })

            # 都失败，返回基本状态存根
            return jsonify({
                'status': 'unknown',
                'execution_id': task_id,
                'is_completed': False,
                'should_stop_polling': False,
                'message': '无法获取任务状态，请稍后重试',
            })

    except Exception as e:
        api_logger.error(
            "get_status_error",
            extra={
                'event': 'get_status_error',
                'execution_id': task_id,
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )

        # 状态查询失败，返回基本状态存根（返回 200 避免前端轮询卡死）
        return jsonify({
            'status': 'unknown',
            'execution_id': task_id,
            'error': str(e),
            'is_completed': True,
            'should_stop_polling': True,
            'message': '无法获取任务状态，请查看报告',
        })


@report_bp.route('/tasks/<task_id>/stub', methods=['GET'])
def get_stub_report_explicit(task_id: str) -> Dict[str, Any]:
    """
    显式获取存根报告

    用于前端主动请求存根报告的场景

    Path Parameters:
        task_id: 任务 ID（执行 ID）

    Query Parameters:
        include_partial: 是否包含部分结果（默认 true）
        include_suggestions: 是否包含智能建议（默认 true）

    Returns:
        存根报告

    Example:
        GET /api/v2/diagnostic/tasks/exec-123/stub
    """
    try:
        include_partial = request.args.get('include_partial', 'true').lower() != 'false'
        include_suggestions = request.args.get('include_suggestions', 'true').lower() != 'false'

        # 获取存根报告
        stub = stub_service.get_stub_report(
            execution_id=task_id,
            include_partial_results=include_partial,
        )

        # 添加智能建议
        if include_suggestions:
            user_id = request.headers.get('X-User-ID', request.args.get('user_id', ''))
            if user_id:
                user_history = stub_service.get_user_history(user_id, limit=5)
                stub = stub_service.enhance_with_suggestions(stub, user_history)

        return jsonify(stub.to_dict())

    except Exception as e:
        api_logger.error(
            "get_stub_report_error",
            extra={
                'event': 'get_stub_report_error',
                'execution_id': task_id,
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )

        # 返回错误存根
        stub = stub_service.get_stub_for_failed_task(
            execution_id=task_id,
            error_message=str(e),
            error_details={'type': type(e).__name__},
        )
        return jsonify(stub.to_dict()), 500
