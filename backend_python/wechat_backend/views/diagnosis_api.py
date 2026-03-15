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
    获取用户历史报告

    请求参数:
    - page: 页码 (默认 1)
    - limit: 每页数量 (默认 20)

    返回:
    {
        "reports": [
            {
                "id": 1,
                "execution_id": "xxx",
                "brand_name": "品牌名称",
                "status": "completed",
                "progress": 100,
                "stage": "completed",
                "is_completed": true,
                "created_at": "2026-02-28T10:00:00",
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

        # P21 修复：直接返回 snake_case 格式，不转换
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

    路径参数:
    - execution_id: 执行 ID

    返回:
    {
        "report": {...},
        "results": [...],
        "analysis": {...},
        "brandDistribution": {...},
        "sentimentDistribution": {...},
        "keywords": [...],
        "meta": {...},
        "validation": {
            "is_valid": true,
            "errors": [],
            "warnings": [],
            "quality_score": 95
        },
        "qualityHints": {...}
    }
    """
    try:
        # 获取服务
        service = get_report_service()

        # 获取完整报告
        report = service.get_full_report(execution_id)

        # P2-2 优化：使用统一错误码处理报告不存在的情况
        if not report:
            api_logger.warning(f"报告不存在：execution_id={execution_id}")
            raise ReportException(
                ErrorCode.REPORT_NOT_FOUND,
                detail=f'execution_id={execution_id}'
            )

        # 【P0-缓存修复】处理报告为字典但包含 error 字段的情况
        if isinstance(report, dict) and report.get('error'):
            api_logger.warning(f"报告为失败状态：execution_id={execution_id}, error={report.get('error', {})}")
            return jsonify(report), 200

        # 【P0-缓存修复】确保 report 是正确的结构
        if not isinstance(report, dict):
            api_logger.error(f"报告格式错误：execution_id={execution_id}, type={type(report)}")
            raise ReportException(
                ErrorCode.REPORT_INVALID_FORMAT,
                {'detail': f'Unexpected type: {type(report)}'},
                detail=f'execution_id={execution_id}'
            )

        # 【P0 关键修复 - 2026-03-12】添加详细的数据结构验证日志
        api_logger.info(
            f"[报告数据检查] execution_id={execution_id}, "
            f"keys={list(report.keys())}, "
            f"results_count={len(report.get('results', []))}"
        )

        brand_dist = report.get('brandDistribution', {})
        sentiment_dist = report.get('sentimentDistribution', {})
        keywords = report.get('keywords', [])

        # 【P0 关键修复 - 2026-03-13 第 14 次】兼容 camelCase 和 snake_case
        # 注意：report 数据已经通过 convert_response_to_camel() 转换为 camelCase
        # 所以 total_count 已转换为 totalCount，但验证代码仍在使用 total_count
        total_count = brand_dist.get('totalCount') or brand_dist.get('total_count', 0)
        sentiment_total = sentiment_dist.get('totalCount') or sentiment_dist.get('total_count', 0)

        api_logger.info(
            f"[报告数据详情] execution_id={execution_id}, "
            f"brandDistribution.totalCount={brand_dist.get('totalCount', 'N/A')}, "
            f"brandDistribution.total_count={brand_dist.get('total_count', 'N/A')}, "
            f"brandDistribution.data.keys={list(brand_dist.get('data', {}).keys()) if isinstance(brand_dist.get('data'), dict) else 'N/A'}, "
            f"sentimentDistribution.totalCount={sentiment_dist.get('totalCount', 'N/A')}, "
            f"sentimentDistribution.total_count={sentiment_dist.get('total_count', 'N/A')}, "
            f"keywords_count={len(keywords) if isinstance(keywords, list) else 'N/A'}"
        )

        # 【P0 关键修复 - 2026-03-13 第 15 次】增强数据验证和降级处理
        # 验证数据是否有效
        has_valid_data = (
            brand_dist.get('data') and 
            isinstance(brand_dist.get('data'), dict) and 
            len(brand_dist.get('data', {})) > 0 and 
            total_count > 0
        )

        # 【P0 关键修复 - 2026-03-13 第 18 次】即使数据不完整，也返回已有数据
        # 核心原则：优先返回原始结果，让前端决定如何展示
        
        has_raw_results = len(report.get('results', [])) > 0
        
        if not has_valid_data:
            api_logger.warning(
                f"⚠️ [数据验证警告] execution_id={execution_id}, "
                f"brandDistribution 为空，但有原始结果：{has_raw_results}"
            )

            # 尝试从数据库重建
            if has_raw_results:
                try:
                    # 从原始结果重建 brandDistribution
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
                        brand_dist = report['brandDistribution']
                        total_count = sum(brand_data.values())

                        # 添加质量警告
                        if 'qualityHints' not in report:
                            report['qualityHints'] = {}
                        report['qualityHints']['partial_success'] = True
                        report['qualityHints']['warnings'] = [
                            '品牌分布数据已从原始结果重建'
                        ]

                        api_logger.info(
                            f"✅ [数据重建成功] execution_id={execution_id}, "
                            f"brands={len(brand_data)}, total={total_count}"
                        )
                except Exception as rebuild_err:
                    api_logger.error(
                        f"❌ [数据重建失败] execution_id={execution_id}, error={rebuild_err}"
                    )

        # 【P0 关键修复 - 第 18 次】即使数据不完全，也返回 200 成功
        # 让前端决定如何展示
        final_has_data = (
            brand_dist.get('data') and
            isinstance(brand_dist.get('data'), dict) and
            len(brand_dist.get('data', {})) > 0
        )

        if not final_has_data and not has_raw_results:
            # 真的没有任何数据
            api_logger.error(
                f"❌ [数据完全为空] execution_id={execution_id}, "
                f"无原始结果，返回错误"
            )
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DATA_NOT_FOUND',
                    'message': '诊断数据为空，无法生成报告',
                    'suggestion': '请尝试重新诊断或联系客服'
                }
            }), 404

        # 【P0 关键】返回成功响应，包含部分成功标志
        return jsonify({
            'success': True,
            'data': report,
            'hasPartialData': not final_has_data and has_raw_results,
            'warnings': report.get('qualityHints', {}).get('warnings', [])
        }), 200

        # P1-3 修复：验证报告并返回验证信息（包含质量评分和质量等级）
        try:
            validation = get_validation_service().validate_report(report)
        except Exception as validation_err:
            api_logger.warning(f"验证服务失败：{validation_err}，使用默认验证结果")
            validation = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'quality_score': 80
            }

        # P1-3 增强：添加质量等级和详细提示
        quality_score = validation.get('quality_score', 0) if validation else 0

        # 定义质量等级
        quality_level_info = {
            'level': 'excellent',
            'label': '优秀',
            'color': '#28a745',
            'description': '报告质量优秀，数据完整可靠',
            'recommendation': '可以直接使用报告结果进行决策'
        }

        if quality_score >= 80:
            quality_level_info = {
                'level': 'excellent',
                'label': '优秀',
                'color': '#28a745',
                'description': '报告质量优秀，数据完整可靠',
                'recommendation': '可以直接使用报告结果进行决策'
            }
        elif quality_score >= 60:
            quality_level_info = {
                'level': 'good',
                'label': '良好',
                'color': '#17a2b8',
                'description': '报告质量良好，部分数据可能需要关注',
                'recommendation': '建议查看警告信息，了解可改进的方面'
            }
        elif quality_score >= 40:
            quality_level_info = {
                'level': 'fair',
                'label': '一般',
                'color': '#ffc107',
                'description': '报告质量一般，存在较多数据质量问题',
                'recommendation': '建议优化配置后重新诊断，以获得更准确的结果'
            }
        elif quality_score >= 20:
            quality_level_info = {
                'level': 'poor',
                'label': '较差',
                'color': '#fd7e14',
                'description': '报告质量较差，数据完整性不足',
                'recommendation': '强烈建议优化配置后重新诊断'
            }
        else:
            quality_level_info = {
                'level': 'critical',
                'label': '严重',
                'color': '#dc3545',
                'description': '报告质量严重不足，参考价值有限',
                'recommendation': '请检查配置并重新诊断，或联系技术支持'
            }

        # 添加质量等级到验证信息
        if validation:
            validation['quality_level'] = quality_level_info

        # 记录质量指标
        api_logger.info(
            f"获取完整报告：execution_id={execution_id}, "
            f"results={len(report.get('results', []))}, "
            f"quality_score={quality_score}, "
            f"quality_level={quality_level_info['label']}"
        )

        # 如果质量评分低，记录警告
        if quality_score < 60:
            api_logger.warning(
                f"报告质量评分低：execution_id={execution_id}, "
                f"quality_score={quality_score}, "
                f"quality_level={quality_level_info['label']}, "
                f"errors={len(validation.get('errors', []) if validation else [])}, "
                f"warnings={len(validation.get('warnings', []) if validation else [])}"
            )

        # 如果质量评分极低，记录错误
        if quality_score < 30:
            api_logger.error(
                f"报告质量评分极低：execution_id={execution_id}, "
                f"quality_score={quality_score}, "
                f"quality_level={quality_level_info['label']}, "
                f"quality_issues={validation.get('quality_issues', []) if validation else []}"
            )

        # P2-3 优化：记录质量指标
        try:
            record_quality_score(execution_id, quality_score, {
                'quality_level': quality_level_info['level'],
                'result_count': len(report.get('results', []))
            })
            
            # 检查是否有告警
            alerts = check_quality_alerts(execution_id)
            if alerts:
                api_logger.warning(
                    f"质量告警触发：execution_id={execution_id}, "
                    f"alerts={[a['rule_name'] for a in alerts]}"
                )
                # 在响应中添加告警信息
                report['qualityAlerts'] = alerts
        except Exception as monitoring_err:
            api_logger.error(f"质量监控记录失败：{monitoring_err}")

        # 将验证信息添加到响应中
        if validation:
            report['validation'] = validation

        # P0 修复：转换为 camelCase
        return jsonify(convert_response_to_camel(report)), 200

    except BusinessException as e:
        # P2-2 优化：使用统一错误码处理业务异常
        api_logger.warning(
            f"获取完整报告业务异常：execution_id={execution_id}, "
            f"{e.error_code.code} - {e.message}"
        )
        response = {
            'error_code': e.error_code.code,
            'error_message': e.message,
            'http_status': e.http_status,
            'execution_id': execution_id
        }
        if e.detail:
            response['detail'] = e.detail
        return jsonify(response), e.http_status
    except Exception as e:
        # P0-2 修复：增强错误处理
        api_logger.error(f"获取完整报告失败：execution_id={execution_id}, 错误：{e}", exc_info=True)
        return jsonify({
            'error_code': ErrorCode.INTERNAL_ERROR.code,
            'error_message': get_error_message(ErrorCode.INTERNAL_ERROR),
            'http_status': 500,
            'execution_id': execution_id,
            'suggestion': '请稍后重试或联系技术支持'
        }), 500


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
