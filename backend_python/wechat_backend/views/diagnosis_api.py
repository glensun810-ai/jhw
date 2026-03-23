"""
品牌诊断报告 API - 存储架构优化版本

新增 API:
1. GET /api/diagnosis/history - 获取用户历史报告
2. GET /api/diagnosis/report/{execution_id} - 获取完整报告

更新 API:
1. POST /api/perform-brand-test - 集成新存储层
2. GET /test/status/{task_id} - 从数据库读取

作者：首席全栈工程师
日期：2026-02-28
版本：1.0
"""

from flask import Blueprint, request, jsonify
from wechat_backend.diagnosis_report_service import get_report_service, get_validation_service
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth_enhanced import enforce_auth_middleware
from wechat_backend.security.rate_limiting import rate_limit
# P2-2 优化：导入统一错误码
from wechat_backend.error_codes import (
    ErrorCode,
    BusinessException,
    ReportException,
    get_error_message
)
# P2-3 优化：导入质量监控
from wechat_backend.quality_monitoring import record_quality_score, check_quality_alerts

# P0 修复：字段转换器导入（兼容不同执行环境）
try:
    from utils.field_converter import convert_response_to_camel
except ImportError:
    try:
        from backend_python.utils.field_converter import convert_response_to_camel
    except ImportError:
        def convert_response_to_camel(data):
            return data

# 创建 Blueprint
diagnosis_bp = Blueprint('diagnosis_api', __name__, url_prefix='/api/diagnosis')


@diagnosis_bp.route('/history', methods=['GET'])
@rate_limit(limit=30, window=60, per='user')
def get_user_history():
    """
    获取用户历史报告（P0 修复 - 2026-03-17：确保 execution_id 正确传递）

    请求参数:
    - page: 页码 (默认 1)
    - limit: 每页数量 (默认 20)

    返回:
    {
        "reports": [
            {
                "id": 1,
                "execution_id": "xxx",
                "executionId": "xxx",  // P0 修复：同时返回 camelCase 格式
                "brand_name": "品牌名称",
                "brandName": "品牌名称",  // P0 修复：同时返回 camelCase 格式
                "status": "completed",
                "progress": 100,
                "stage": "completed",
                "is_completed": true,
                "created_at": "2026-02-28T10:00:00",
                "createdAt": "2026-02-28T10:00:00",  // P0 修复：同时返回 camelCase 格式
                "completed_at": "2026-02-28T10:05:00"
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 100,
            "has_more": true
        }
    }
    """
    try:
        # 获取用户 ID（从认证中间件）
        user_id = request.args.get('user_id', 'anonymous')

        # 获取分页参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        # 获取服务
        service = get_report_service()

        # 获取历史
        result = service.get_user_history(user_id, page, limit)

        api_logger.info(f"获取用户历史：user_id={user_id}, page={page}, limit={limit}, count={len(result['reports'])}")

        # 【P0 修复 - 2026-03-17】同时返回 snake_case 和 camelCase 格式
        # 确保前端可以使用任一格式访问
        if 'reports' in result and isinstance(result['reports'], list):
            for report in result['reports']:
                if isinstance(report, dict):
                    # 确保 executionId 可用
                    if 'execution_id' in report and 'executionId' not in report:
                        report['executionId'] = report['execution_id']
                    # 确保 brandName 可用
                    if 'brand_name' in report and 'brandName' not in report:
                        report['brandName'] = report['brand_name']
                    # 确保 createdAt 可用
                    if 'created_at' in report and 'createdAt' not in report:
                        report['createdAt'] = report['created_at']
                    # 确保 overallScore 可用
                    if 'overall_score' in report and 'overallScore' not in report:
                        report['overallScore'] = report['overall_score']

        # P21 修复：直接返回结果（包含双格式字段）
        return jsonify(result), 200

    except BusinessException as e:
        # P2-2 优化：使用统一错误码处理业务异常
        api_logger.warning(f"获取用户历史业务异常：{e.error_code.code} - {e.message}")
        response = {
            'error_code': e.error_code.code,
            'error_message': e.message,
            'http_status': e.http_status
        }
        if e.detail:
            response['detail'] = e.detail
        return jsonify(response), e.http_status
    except Exception as e:
        api_logger.error(f"获取用户历史失败：{e}")
        return jsonify({
            'error_code': ErrorCode.INTERNAL_ERROR.code,
            'error_message': get_error_message(ErrorCode.INTERNAL_ERROR),
            'http_status': 500
        }), 500


@diagnosis_bp.route('/report/<execution_id>/history', methods=['GET'])
@rate_limit(limit=60, window=60, per='user')
def get_history_report_api(execution_id):
    """
    获取历史报告（增强版 - 2026-03-13 第 18 次）

    专为历史报告查看优化：
    1. 优先从数据库读取，不触发新的诊断
    2. 包含完整的元数据（品牌、时间、状态等）
    3. 即使部分数据缺失，也返回可用的最大数据集
    4. 支持从 DiagnosisResult 表重建数据
    """
    try:
        # 获取服务
        service = get_report_service()

        # 获取历史报告（不重新计算）
        report = service.get_history_report(execution_id)

        if not report:
            api_logger.warning(f"历史报告不存在：execution_id={execution_id}")
            return jsonify({
                'error': '报告不存在',
                'execution_id': execution_id
            }), 404

        # 【P0 关键修复 - 第 18 次】检查并重建 brandDistribution
        brand_dist = report.get('brandDistribution', {})
        has_raw_results = len(report.get('results', [])) > 0
        
        if not brand_dist.get('data'):
            api_logger.warning(
                f"⚠️ [历史报告] brandDistribution 为空，有原始结果：{has_raw_results}"
            )

            # 尝试直接从 DiagnosisResult 读取
            if has_raw_results:
                try:
                    # 从原始结果重建 brandDistribution
                    brand_data = {}
                    for result in report.get('results', []):
                        brand = result.get('extracted_brand') or result.get('brand')
                        if brand:
                            brand_data[brand] = brand_data.get(brand, 0) + 1

                    if brand_data:
                        # 更新 report
                        report['brandDistribution'] = {
                            'data': brand_data,
                            'totalCount': sum(brand_data.values()),
                            'successRate': 1.0
                        }
                        
                        # 添加质量警告
                        if 'qualityHints' not in report:
                            report['qualityHints'] = {}
                        report['qualityHints']['partial_success'] = True
                        report['qualityHints']['warnings'] = [
                            '品牌分布数据已从原始结果重建'
                        ]
                        
                        api_logger.info(
                            f"✅ [历史报告] 重建 brandDistribution: {list(brand_data.keys())}"
                        )
                except Exception as e:
                    api_logger.error(f"❌ [历史报告] 重建失败：{e}")

        # 【P0 关键修复 - 第 18 次】返回成功响应，包含部分成功标志
        final_has_data = (
            brand_dist.get('data') or
            (report.get('brandDistribution', {}).get('data'))
        )

        return jsonify({
            'success': True,
            'data': report,
            'hasPartialData': not final_has_data and has_raw_results,
            'warnings': report.get('qualityHints', {}).get('warnings', [])
        }), 200

    except Exception as e:
        api_logger.error(f"获取历史报告失败：{e}", exc_info=True)
        return jsonify({
            'error': '获取失败',
            'execution_id': execution_id,
            'message': str(e)
        }), 500


@diagnosis_bp.route('/report/<execution_id>', methods=['GET'])
@rate_limit(limit=60, window=60, per='user')
def get_full_report(execution_id):
    """
    获取完整诊断报告
    【P0 架构级修复 - 2026-03-18】使用统一响应格式和服务层验证器
    【P0 关键修复 - 2026-03-20】强化数据校验，防止空响应体导致前端崩溃

    路径参数:
    - execution_id: 执行 ID

    返回:
    {
        "success": True,
        "data": {
            "report": {...},
            "results": [...],
            "analysis": {...},
            ...
        },
        "metadata": {...},
        "timestamp": "..."
    }
    """
    try:
        # 【P0 架构级修复】导入统一响应格式和服务层验证器
        from wechat_backend.middleware.response_formatter import StandardizedResponse
        from wechat_backend.validators.service_validator import ServiceDataValidator

        # 1. 获取服务
        service = get_report_service()

        # 2. 获取完整报告
        report = service.get_full_report(execution_id)

        # 3. 【P0 关键修复 - 2026-03-20】空报告拦截
        # 如果 service 层返回 None 或空字典，立即返回明确错误
        if not report:
            api_logger.error(f"❌ [服务层返回空报告] execution_id={execution_id}")
            return StandardizedResponse.error(
                ErrorCode.DATA_NOT_FOUND,
                detail={
                    'execution_id': execution_id,
                    'suggestion': '诊断报告不存在或数据为空，请尝试重新诊断',
                    'recovery_actions': [
                        '点击"重试"重新加载',
                        '点击"重新诊断"创建新任务',
                        '查看历史报告记录'
                    ]
                },
                http_status=404
            )

        # 4. 【P0 架构级修复】服务层数据验证
        ServiceDataValidator.validate_report_data(report, execution_id)

        # 5. 【P0 关键修复 - 2026-03-20】检查报告状态
        # 处理报告为失败状态的情况
        if isinstance(report, dict) and report.get('error'):
            api_logger.warning(f"报告为失败状态：execution_id={execution_id}")
            # 返回失败状态但使用统一格式，确保前端可以渲染错误卡片
            return StandardizedResponse.partial_success(
                data=report,
                warnings=[report.get('error_message', '诊断执行失败')],
                message='报告为失败状态，包含错误信息',
                metadata={
                    'execution_id': execution_id,
                    'error_type': report.get('error', {}).get('status', 'unknown'),
                    'fallback_info': report.get('error', {}).get('fallback_info', {})
                }
            )

        # 6. 检查是否有原始结果
        has_raw_results = len(report.get('results', [])) > 0
        has_valid_data = (
            report.get('brandDistribution', {}).get('data') and
            len(report.get('brandDistribution', {}).get('data', {})) > 0
        )

        # 7. 【P0 关键修复 - 2026-03-20】数据完全为空时返回明确错误（增强版）
        if not has_valid_data and not has_raw_results:
            api_logger.error(
                f"❌ [数据完全为空] execution_id={execution_id}, "
                f"brandDistribution.data={report.get('brandDistribution', {}).get('data')}"
            )
            # 尝试从 report 中提取错误信息
            error_msg = '诊断数据为空'
            if report.get('validation', {}).get('errors'):
                error_msg = report['validation']['errors'][0]
            elif report.get('qualityHints', {}).get('warnings'):
                error_msg = report['qualityHints']['warnings'][0]

            return StandardizedResponse.error(
                ErrorCode.DATA_NOT_FOUND,
                detail={
                    'execution_id': execution_id,
                    'suggestion': '诊断已完成但未生成有效数据，可能原因：AI 调用失败或数据保存失败',
                    'error_message': error_msg,
                    'recovery_actions': [
                        '检查后端日志查看详细错误',
                        '点击"重新诊断"创建新任务',
                        '查看历史报告记录'
                    ]
                },
                http_status=404
            )

        # 8. 数据不完整但有原始结果时，返回部分成功
        if not has_valid_data and has_raw_results:
            api_logger.warning(f"⚠️ [部分成功] execution_id={execution_id}, 有原始结果")
            # 【P0 关键修复】尝试重建 brandDistribution
            try:
                brand_data = {}
                for result in report.get('results', []):
                    brand = result.get('extracted_brand') or result.get('brand')
                    if brand:
                        brand_data[brand] = brand_data.get(brand, 0) + 1

                if brand_data:
                    report['brandDistribution'] = {
                        'data': brand_data,
                        'totalCount': sum(brand_data.values()),
                        'successRate': 1.0
                    }
                    api_logger.info(
                        f"✅ [重建成功] execution_id={execution_id}, brands={list(brand_data.keys())}"
                    )
            except Exception as rebuild_err:
                api_logger.warning(f"⚠️ [重建失败] execution_id={execution_id}, error={rebuild_err}")

            return StandardizedResponse.partial_success(
                data=report,
                warnings=report.get('qualityHints', {}).get('warnings', []),
                message='数据部分成功，包含原始结果',
                metadata={
                    'execution_id': execution_id,
                    'results_count': len(report.get('results', [])),
                    'rebuilt_brand_distribution': 'brand_data' in locals()
                }
            )

        # 9. 【P0 架构级修复】数据完整，返回标准成功响应
        api_logger.info(f"✅ [报告获取成功] execution_id={execution_id}")
        return StandardizedResponse.success(
            data=report,
            message='报告获取成功',
            metadata={
                'execution_id': execution_id,
                'data_version': report.get('data_schema_version', '1.0'),
                'results_count': len(report.get('results', [])),
                'brand_count': len(report.get('brandDistribution', {}).get('data', {}))
            }
        )

    except BusinessException as e:
        # P2-2 优化：使用统一错误码处理业务异常
        api_logger.warning(
            f"获取完整报告业务异常：execution_id={execution_id}, "
            f"{e.error_code.code} - {e.message}"
        )
        return StandardizedResponse.error(e.error_code, e.detail, e.http_status)

    except Exception as e:
        # 系统异常：返回内部错误
        api_logger.error(f"获取报告失败：execution_id={execution_id}, 错误：{e}", exc_info=True)
        return StandardizedResponse.error(
            ErrorCode.INTERNAL_ERROR,
            detail={'execution_id': execution_id, 'detail': str(e)},
            http_status=500
        )


@diagnosis_bp.route('/report/<execution_id>/validate', methods=['GET'])
def validate_report(execution_id):
    """
    验证报告完整性

    路径参数:
    - execution_id: 执行 ID

    返回:
    {
        "is_valid": true,
        "errors": [],
        "warnings": [],
        "checksum_verified": true
    }
    """
    try:
        # 获取服务
        service = get_report_service()

        # 获取报告
        report = service.get_full_report(execution_id)

        if not report:
            return jsonify({
                'error': '报告不存在',
                'execution_id': execution_id
            }), 404

        # 验证报告
        validation = get_validation_service().validate_report(report)

        # 添加校验和验证
        validation['checksum_verified'] = report.get('checksum_verified', False)

        # P0 修复：转换为 camelCase
        return jsonify(convert_response_to_camel(validation)), 200

    except Exception as e:
        api_logger.error(f"验证报告失败：{e}")
        return jsonify({
            'error': '验证失败',
            'message': str(e)
        }), 500


# ==================== P21 修复：历史诊断详情 API ====================

@diagnosis_bp.route('/history/<execution_id>/detail', methods=['GET'])
@rate_limit(limit=30, window=60, per='user')
def get_diagnosis_detail(execution_id):
    """
    获取历史诊断详情数据（P21 新增 - 2026-03-14）
    
    从 diagnosis_reports、diagnosis_results、diagnosis_analysis 三张表
    完整提取诊断数据，供前端历史详情页展示
    
    路径参数:
        execution_id: 诊断执行 ID
    
    返回:
        {
            "success": true,
            "data": {
                "report": {...},           // 诊断报告基本信息
                "results": [...],          // 诊断结果列表
                "analysis": {...},         // 诊断分析数据
                "brandAnalysis": {...},    // 品牌分析
                "top3Brands": [...]        // Top3 品牌排名
            }
        }
    """
    try:
        api_logger.info(f"请求诊断详情：execution_id={execution_id}")
        
        # 使用 DiagnosisReportRepository 获取完整数据
        from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
        
        report_repo = DiagnosisReportRepository()
        report = report_repo.get_by_execution_id(execution_id)
        
        if not report:
            api_logger.warning(f"诊断报告不存在：execution_id={execution_id}")
            return jsonify({
                'success': False,
                'error': '报告不存在',
                'execution_id': execution_id
            }), 404
        
        # 提取诊断结果
        results = report.get('results', [])
        
        # 提取诊断分析数据
        brand_analysis = report.get('brandAnalysis')
        user_brand_analysis = report.get('userBrandAnalysis')
        competitor_analysis = report.get('competitorAnalysis', [])
        comparison = report.get('comparison')
        top3_brands = report.get('top3Brands', [])
        
        # 构建响应数据
        response_data = {
            'report': {
                'id': report.get('id'),
                'execution_id': report.get('execution_id'),
                'brand_name': report.get('brand_name'),
                'competitor_brands': report.get('competitor_brands', []),
                'status': report.get('status'),
                'progress': report.get('progress', 100),
                'stage': report.get('stage'),
                'is_completed': report.get('is_completed', True),
                'created_at': report.get('created_at'),
                'completed_at': report.get('completed_at'),
                'error_message': report.get('error_message')
            },
            'results': results,
            'analysis': {
                'brandAnalysis': brand_analysis,
                'userBrandAnalysis': user_brand_analysis,
                'competitorAnalysis': competitor_analysis,
                'comparison': comparison,
                'top3Brands': top3_brands
            },
            'statistics': {
                'total_results': len(results),
                'total_questions': len(set(r.get('question', '') for r in results if r.get('question'))),
                'platforms': list(set(r.get('platform', '') for r in results if r.get('platform')))
            }
        }
        
        api_logger.info(
            f"诊断详情获取成功：execution_id={execution_id}, "
            f"results={len(results)}, questions={response_data['statistics']['total_questions']}"
        )
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except Exception as e:
        api_logger.error(f"获取诊断详情失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}'
        }), 500


# ==================== 导出 Blueprint ====================

def register_diagnosis_api(app):
    """注册诊断 API"""
    app.register_blueprint(diagnosis_bp)
    api_logger.info("✅ 诊断 API 注册完成")
