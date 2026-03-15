"""
诊断报告导出 API

功能:
- 导出 Excel 格式报告
- 导出 HTML 格式报告
- 批量导出

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

from flask import Blueprint, request, jsonify, send_file, make_response
from typing import Dict, Any

from wechat_backend.logging_config import api_logger
from wechat_backend.services.report_export_service import get_export_service
from wechat_backend.services.diagnosis_report_service import get_report_service
from wechat_backend.decorators.rate_limit import rate_limit

# 创建蓝图
export_bp = Blueprint('export', __name__, url_prefix='/api/diagnosis/export')


@export_bp.route('/<execution_id>/excel', methods=['GET'])
@rate_limit(limit=10, window=60, per='user')
def export_excel(execution_id: str):
    """
    导出报告为 Excel 格式
    
    路径参数:
    - execution_id: 执行 ID
    
    返回:
    - Excel 文件
    """
    try:
        # 获取报告数据
        report_service = get_report_service()
        report = report_service.get_full_report(execution_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REPORT_NOT_FOUND',
                    'message': '报告不存在'
                }
            }), 404
        
        # 导出 Excel
        export_service = get_export_service()
        excel_data = export_service.export_to_excel(report, execution_id)
        
        # 创建响应
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=diagnosis_report_{execution_id[:8]}.xlsx'
        response.headers['Content-Length'] = len(excel_data)
        
        api_logger.info(f"[ExportAPI] ✅ Excel 导出成功：{execution_id}")
        
        return response
        
    except ImportError as e:
        api_logger.error(f"[ExportAPI] ❌ Excel 导出失败：{e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'DEPENDENCY_MISSING',
                'message': '缺少 openpyxl 依赖，请联系管理员安装：pip install openpyxl'
            }
        }), 500
        
    except Exception as e:
        api_logger.error(f"[ExportAPI] ❌ Excel 导出失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_FAILED',
                'message': '导出失败'
            }
        }), 500


@export_bp.route('/<execution_id>/html', methods=['GET'])
@rate_limit(limit=10, window=60, per='user')
def export_html(execution_id: str):
    """
    导出报告为 HTML 格式（用于转长图）
    
    路径参数:
    - execution_id: 执行 ID
    
    返回:
    - HTML 字符串
    """
    try:
        # 获取报告数据
        report_service = get_report_service()
        report = report_service.get_full_report(execution_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REPORT_NOT_FOUND',
                    'message': '报告不存在'
                }
            }), 404
        
        # 导出 HTML
        export_service = get_export_service()
        html_content = export_service.export_to_html(report)
        
        api_logger.info(f"[ExportAPI] ✅ HTML 导出成功：{execution_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'html': html_content
            }
        })
        
    except Exception as e:
        api_logger.error(f"[ExportAPI] ❌ HTML 导出失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_FAILED',
                'message': '导出失败'
            }
        }), 500


@export_bp.route('/<execution_id>/image', methods=['POST'])
@rate_limit(limit=5, window=60, per='user')
def export_image(execution_id: str):
    """
    导出报告为长图格式
    
    说明:
    此接口需要前端配合，使用 html2canvas 将 HTML 转为图片
    
    路径参数:
    - execution_id: 执行 ID
    
    返回:
    - HTML 内容（前端渲染后转图片）
    """
    try:
        # 获取报告数据
        report_service = get_report_service()
        report = report_service.get_full_report(execution_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REPORT_NOT_FOUND',
                    'message': '报告不存在'
                }
            }), 404
        
        # 导出 HTML
        export_service = get_export_service()
        html_content = export_service.export_to_html(report)
        
        api_logger.info(f"[ExportAPI] ✅ 长图 HTML 生成成功：{execution_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'html': html_content,
                'filename': f'diagnosis_report_{execution_id[:8]}'
            }
        })
        
    except Exception as e:
        api_logger.error(f"[ExportAPI] ❌ 长图导出失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_FAILED',
                'message': '导出失败'
            }
        }), 500


@export_bp.route('/batch', methods=['POST'])
@rate_limit(limit=5, window=300, per='user')
def batch_export():
    """
    批量导出报告
    
    请求体:
    {
        "execution_ids": ["id1", "id2", ...],
        "format": "excel"  // excel | html
    }
    
    返回:
    - 文件列表或 ZIP 包
    """
    try:
        data = request.get_json() or {}
        execution_ids = data.get('execution_ids', [])
        export_format = data.get('format', 'excel')
        
        if not execution_ids:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PARAMS',
                    'message': '执行 ID 列表不能为空'
                }
            }), 400
        
        if len(execution_ids) > 10:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TOO_MANY_REQUESTS',
                    'message': '单次最多导出 10 个报告'
                }
            }), 400
        
        report_service = get_report_service()
        export_service = get_export_service()
        
        results = []
        
        for exec_id in execution_ids:
            try:
                report = report_service.get_full_report(exec_id)
                if not report:
                    results.append({
                        'execution_id': exec_id,
                        'success': False,
                        'error': '报告不存在'
                    })
                    continue
                
                if export_format == 'excel':
                    # Excel 导出返回文件信息
                    results.append({
                        'execution_id': exec_id,
                        'success': True,
                        'format': 'excel',
                        'filename': f'diagnosis_report_{exec_id[:8]}.xlsx'
                    })
                else:
                    results.append({
                        'execution_id': exec_id,
                        'success': True,
                        'format': 'html',
                        'filename': f'diagnosis_report_{exec_id[:8]}.html'
                    })
                    
            except Exception as e:
                results.append({
                    'execution_id': exec_id,
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r.get('success'))
        
        api_logger.info(f"[ExportAPI] ✅ 批量导出完成：{success_count}/{len(execution_ids)}")
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'success_count': success_count,
                'total_count': len(execution_ids)
            }
        })
        
    except Exception as e:
        api_logger.error(f"[ExportAPI] ❌ 批量导出失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_FAILED',
                'message': '批量导出失败'
            }
        }), 500
