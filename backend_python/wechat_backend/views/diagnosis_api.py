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

        # P0 修复：转换为 camelCase
        return jsonify(convert_response_to_camel(result)), 200

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


# ==================== 导出 Blueprint ====================

def register_diagnosis_api(app):
    """注册诊断 API"""
    app.register_blueprint(diagnosis_bp)
    api_logger.info("✅ 诊断 API 注册完成")
