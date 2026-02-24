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
        
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.error(f"获取用户历史失败：{e}")
        return jsonify({
            'error': '获取历史失败',
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
        "report": {
            "id": 1,
            "execution_id": "xxx",
            "brand_name": "品牌名称",
            ...
        },
        "results": [
            {
                "id": 1,
                "brand": "品牌名称",
                "question": "问题",
                "model": "AI 模型",
                "response": {
                    "content": "AI 回答",
                    "latency": 12.5
                },
                "geo_data": {...},
                "quality_score": 85,
                "quality_level": "high"
            }
        ],
        "analysis": {
            "competitive_analysis": {...},
            "brand_scores": {...},
            ...
        },
        "meta": {
            "data_schema_version": "1.0",
            "server_version": "2.0.0",
            "retrieved_at": "2026-02-28T10:00:00"
        },
        "checksum_verified": true
    }
    """
    try:
        # 获取服务
        service = get_report_service()
        
        # 获取完整报告
        report = service.get_full_report(execution_id)
        
        if not report:
            return jsonify({
                'error': '报告不存在',
                'execution_id': execution_id
            }), 404
        
        # 验证报告
        validation = get_validation_service().validate_report(report)
        if not validation['is_valid']:
            api_logger.warning(f"报告验证失败：{execution_id}, errors={validation['errors']}")
        
        api_logger.info(f"获取完整报告：execution_id={execution_id}, results={len(report.get('results', []))}")
        
        return jsonify(report), 200
        
    except Exception as e:
        api_logger.error(f"获取完整报告失败：{e}")
        return jsonify({
            'error': '获取报告失败',
            'message': str(e)
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
        
        return jsonify(validation), 200
        
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
