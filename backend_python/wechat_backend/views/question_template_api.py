"""
诊断问题模板库 API

功能:
- 获取模板列表
- 按分类/行业筛选
- 搜索模板
- 保存/删除自定义模板

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

from wechat_backend.logging_config import api_logger
from wechat_backend.services.question_template_service import get_template_service
from wechat_backend.decorators.rate_limit import rate_limit

# 创建蓝图
template_bp = Blueprint('template', __name__, url_prefix='/api/diagnosis/templates')


@template_bp.route('', methods=['GET'])
@rate_limit(limit=100, window=60, per='user')
def get_templates() -> Dict[str, Any]:
    """
    获取问题模板列表
    
    查询参数:
    - category: 按分类筛选
    - industry: 按行业筛选
    
    返回:
    {
        "templates": [...],
        "categories": [...],
        "industries": [...]
    }
    """
    try:
        category = request.args.get('category')
        industry = request.args.get('industry')
        
        service = get_template_service()
        
        # 按分类筛选
        if category:
            templates = service.get_templates_by_category(category)
            api_logger.info(f"[TemplateAPI] 按分类获取模板：{category}, 数量={len(templates)}")
            return jsonify({
                'success': True,
                'data': {
                    'templates': templates,
                    'categories': service.get_categories(),
                    'industries': service.get_industries()
                }
            })
        
        # 按行业筛选
        if industry:
            templates = service.get_templates_by_industry(industry)
            api_logger.info(f"[TemplateAPI] 按行业获取模板：{industry}, 数量={len(templates)}")
            return jsonify({
                'success': True,
                'data': {
                    'templates': templates,
                    'categories': service.get_categories(),
                    'industries': service.get_industries()
                }
            })
        
        # 获取全部
        all_data = service.get_all_templates()
        api_logger.info(f"[TemplateAPI] 获取全部模板：数量={len(all_data.get('templates', []))}")
        
        return jsonify({
            'success': True,
            'data': all_data
        })
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 获取模板失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEMPLATE_FETCH_FAILED',
                'message': '获取模板失败'
            }
        }), 500


@template_bp.route('/<template_id>', methods=['GET'])
@rate_limit(limit=100, window=60, per='user')
def get_template(template_id: str) -> Dict[str, Any]:
    """
    获取单个模板详情
    
    路径参数:
    - template_id: 模板 ID
    
    返回:
    {
        "success": true,
        "data": {...}
    }
    """
    try:
        service = get_template_service()
        template = service.get_template_by_id(template_id)
        
        if not template:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TEMPLATE_NOT_FOUND',
                    'message': '模板不存在'
                }
            }), 404
        
        # 增加使用次数
        service.increment_template_usage(template_id)
        
        api_logger.info(f"[TemplateAPI] 获取模板详情：{template_id}")
        
        return jsonify({
            'success': True,
            'data': template
        })
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 获取模板详情失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEMPLATE_FETCH_FAILED',
                'message': '获取模板失败'
            }
        }), 500


@template_bp.route('/search', methods=['POST'])
@rate_limit(limit=50, window=60, per='user')
def search_templates() -> Dict[str, Any]:
    """
    搜索模板
    
    请求体:
    {
        "keyword": "搜索关键词"
    }
    
    返回:
    {
        "success": true,
        "data": [...]
    }
    """
    try:
        data = request.get_json() or {}
        keyword = data.get('keyword', '')
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_KEYWORD',
                    'message': '搜索关键词不能为空'
                }
            }), 400
        
        service = get_template_service()
        results = service.search_templates(keyword)
        
        api_logger.info(f"[TemplateAPI] 搜索模板：{keyword}, 结果={len(results)}")
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 搜索模板失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEMPLATE_SEARCH_FAILED',
                'message': '搜索模板失败'
            }
        }), 500


@template_bp.route('/custom', methods=['POST'])
@rate_limit(limit=20, window=60, per='user')
def save_custom_template() -> Dict[str, Any]:
    """
    保存自定义模板
    
    请求体:
    {
        "name": "模板名称",
        "category": "分类",
        "industry": "行业",
        "description": "描述",
        "questions": ["问题 1", "问题 2", ...],
        "tags": ["标签 1", "标签 2", ...]
    }
    
    返回:
    {
        "success": true,
        "data": {...}
    }
    """
    try:
        data = request.get_json() or {}
        
        # 验证必填字段
        required_fields = ['name', 'questions']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': f'缺少必填字段：{field}'
                    }
                }), 400
        
        # 验证问题列表
        questions = data.get('questions', [])
        if not isinstance(questions, list) or len(questions) == 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_QUESTIONS',
                    'message': '问题列表不能为空'
                }
            }), 400
        
        # 获取用户 ID（从请求头或 session）
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        service = get_template_service()
        saved_template = service.save_custom_template(data, user_id)
        
        api_logger.info(f"[TemplateAPI] 保存自定义模板：{saved_template.get('id')}")
        
        return jsonify({
            'success': True,
            'data': saved_template
        }), 201
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 保存自定义模板失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEMPLATE_SAVE_FAILED',
                'message': '保存模板失败'
            }
        }), 500


@template_bp.route('/custom/<template_id>', methods=['DELETE'])
@rate_limit(limit=20, window=60, per='user')
def delete_custom_template(template_id: str) -> Dict[str, Any]:
    """
    删除自定义模板
    
    路径参数:
    - template_id: 模板 ID
    
    返回:
    {
        "success": true,
        "message": "删除成功"
    }
    """
    try:
        # 获取用户 ID
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        service = get_template_service()
        success = service.delete_custom_template(template_id, user_id)
        
        if success:
            api_logger.info(f"[TemplateAPI] 删除自定义模板：{template_id}")
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TEMPLATE_NOT_FOUND',
                    'message': '模板不存在或无权限删除'
                }
            }), 404
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 删除自定义模板失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEMPLATE_DELETE_FAILED',
                'message': '删除模板失败'
            }
        }), 500


@template_bp.route('/categories', methods=['GET'])
@rate_limit(limit=100, window=60, per='user')
def get_categories() -> Dict[str, Any]:
    """
    获取所有分类
    
    返回:
    {
        "success": true,
        "data": ["分类 1", "分类 2", ...]
    }
    """
    try:
        service = get_template_service()
        categories = service.get_categories()
        
        return jsonify({
            'success': True,
            'data': categories
        })
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 获取分类失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'CATEGORY_FETCH_FAILED',
                'message': '获取分类失败'
            }
        }), 500


@template_bp.route('/industries', methods=['GET'])
@rate_limit(limit=100, window=60, per='user')
def get_industries() -> Dict[str, Any]:
    """
    获取所有行业
    
    返回:
    {
        "success": true,
        "data": ["行业 1", "行业 2", ...]
    }
    """
    try:
        service = get_template_service()
        industries = service.get_industries()
        
        return jsonify({
            'success': True,
            'data': industries
        })
        
    except Exception as e:
        api_logger.error(f"[TemplateAPI] 获取行业失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INDUSTRY_FETCH_FAILED',
                'message': '获取行业失败'
            }
        }), 500
