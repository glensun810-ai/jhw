#!/usr/bin/env python3
"""
PDF 报告导出 API 端点
完整支持品牌诊断报告导出

版本：v2.0
日期：2026-02-21
"""

from flask import Blueprint, request, Response, jsonify, send_file
from datetime import datetime
import os
from wechat_backend.logging_config import api_logger
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.security.auth import require_auth_optional, get_current_user_id

# 创建 Blueprint
pdf_export_bp = Blueprint('pdf_export', __name__)


@pdf_export_bp.route('/api/export/report-data', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def get_full_report_data():
    """
    获取完整报告数据
    
    Query Parameters:
    - executionId: 执行 ID (required)
    - format: 数据格式 (basic, detailed, full) default: full
    - sections: 需要的章节 (comma-separated) default: all
    
    Returns:
    - 完整报告数据 JSON
    """
    execution_id = request.args.get('executionId')
    format_level = request.args.get('format', 'full')
    sections = request.args.get('sections', 'all')
    
    if not execution_id:
        return jsonify({'error': 'executionId is required', 'code': 'MISSING_EXECUTION_ID'}), 400
    
    try:
        from wechat_backend.services.report_data_service import get_report_data_service
        
        report_service = get_report_data_service()
        full_report = report_service.generate_full_report(execution_id)
        
        # 根据 format_level 过滤数据
        if format_level == 'basic':
            report_data = _filter_basic(full_report)
        elif format_level == 'detailed':
            report_data = _filter_detailed(full_report)
        else:
            report_data = full_report
        
        # 根据 sections 过滤
        if sections != 'all':
            section_list = [s.strip() for s in sections.split(',')]
            report_data = {k: v for k, v in report_data.items() if k in section_list or k == 'reportMetadata'}
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
        
    except Exception as e:
        api_logger.error(f"获取报告数据失败：{e}", exc_info=True)
        return jsonify({
            'error': 'Failed to get report data',
            'details': str(e),
            'code': 'REPORT_DATA_ERROR'
        }), 500


@pdf_export_bp.route('/api/export/pdf', methods=['GET'])
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
def export_pdf_report():
    """
    导出测试报告为 PDF (增强版)
    
    Query Parameters:
    - executionId: 测试执行 ID (required)
    - level: 报告级别 (basic, detailed, full) default: full
    - sections: 需要的章节 (comma-separated) default: all
    - async: 是否异步生成 (true, false) default: false
    
    Returns:
    - PDF file download 或 异步任务 ID
    """
    execution_id = request.args.get('executionId')
    level = request.args.get('level', 'full')
    sections = request.args.get('sections', 'all')
    is_async = request.args.get('async', 'false').lower() == 'true'
    
    if not execution_id:
        return jsonify({'error': 'executionId is required', 'code': 'MISSING_EXECUTION_ID'}), 400
    
    if is_async:
        # 异步生成
        from wechat_backend.services.async_export_service import queue_pdf_generation
        
        task_id = queue_pdf_generation(execution_id, level, sections)
        
        return jsonify({
            'status': 'processing',
            'task_id': task_id,
            'status_url': f'/api/export/status/{task_id}'
        }), 202
    else:
        # 同步生成（仅支持 basic 级别）
        try:
            from wechat_backend.services.report_data_service import get_report_data_service
            from wechat_backend.services.pdf_export_service import PDFExportService
            
            report_service = get_report_data_service()
            report_data = report_service.generate_full_report(execution_id)
            
            pdf_service = PDFExportService()
            pdf_data = pdf_service.generate_enhanced_report(report_data, level, sections)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{execution_id}_{timestamp}.pdf"
            
            return Response(
                pdf_data,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': len(pdf_data),
                    'Access-Control-Expose-Headers': 'Content-Disposition'
                }
            )
        except Exception as e:
            api_logger.error(f"PDF 生成失败：{e}", exc_info=True)
            return jsonify({
                'error': 'Failed to generate PDF',
                'details': str(e),
                'code': 'PDF_GENERATION_ERROR'
            }), 500


@pdf_export_bp.route('/api/export/status/<task_id>', methods=['GET'])
@require_auth_optional
def get_export_status(task_id):
    """
    获取异步导出任务状态
    
    Returns:
    - 任务状态和结果
    """
    from wechat_backend.services.async_export_service import get_async_export_service
    
    service = get_async_export_service()
    status = service.get_task_status(task_id)
    
    if status.get('status') == 'not_found':
        return jsonify({
            'status': 'not_found',
            'error': 'Task not found'
        }), 404
    
    response_data = {
        'status': status.get('status'),
        'progress': status.get('progress', 0),
        'message': status.get('message', '')
    }
    
    if status.get('status') == 'completed':
        response_data['download_url'] = f'/api/export/download/{task_id}'
        response_data['file_size'] = status.get('file_size', 0)
    elif status.get('status') == 'failed':
        response_data['error'] = status.get('error', 'Unknown error')
    
    return jsonify(response_data)


@pdf_export_bp.route('/api/export/download/<task_id>', methods=['GET'])
@require_auth_optional
def download_export_file(task_id):
    """
    下载导出文件
    
    Returns:
    - PDF file download
    """
    from wechat_backend.services.async_export_service import get_async_export_service
    
    service = get_async_export_service()
    status = service.get_task_status(task_id)
    
    if status.get('status') != 'completed':
        return jsonify({
            'error': 'File not ready',
            'status': status.get('status')
        }), 400
    
    file_path = status.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({
            'error': 'File not found'
        }), 404
    
    return send_file(
        file_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )


@pdf_export_bp.route('/api/export/html', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def export_html_report():
    """
    导出测试报告为 HTML（用于微信小程序预览）
    
    Query Parameters:
    - executionId: 测试执行 ID (required)
    - level: 报告级别 (basic, detailed, full) default: full
    
    Returns:
    - HTML content
    """
    execution_id = request.args.get('executionId')
    level = request.args.get('level', 'full')
    
    if not execution_id:
        return jsonify({'error': 'executionId is required'}), 400
    
    try:
        from wechat_backend.services.report_data_service import get_report_data_service
        from wechat_backend.services.html_export_service import HTMLExportService
        
        report_service = get_report_data_service()
        report_data = report_service.generate_full_report(execution_id)
        
        html_service = HTMLExportService()
        html_content = html_service.generate_report(report_data, level)
        
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'inline; filename=report_{execution_id}.html',
            }
        )
    except Exception as e:
        api_logger.error(f"HTML 生成失败：{e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@pdf_export_bp.route('/api/export/stats', methods=['GET'])
@require_auth_optional
def get_export_stats():
    """
    获取导出统计信息
    
    Returns:
    - 统计信息 JSON
    """
    from wechat_backend.services.async_export_service import get_async_export_service
    
    service = get_async_export_service()
    stats = service.get_queue_stats()
    
    return jsonify({
        'status': 'success',
        'data': stats
    })


def _filter_basic(report_data: Dict) -> Dict:
    """过滤为基础版数据"""
    return {
        'reportMetadata': report_data.get('reportMetadata'),
        'executiveSummary': report_data.get('executiveSummary'),
        'brandHealth': {
            'overall_score': report_data.get('brandHealth', {}).get('overall_score'),
            'health_grade': report_data.get('brandHealth', {}).get('health_grade')
        }
    }


def _filter_detailed(report_data: Dict) -> Dict:
    """过滤为详细版数据"""
    return {
        'reportMetadata': report_data.get('reportMetadata'),
        'executiveSummary': report_data.get('executiveSummary'),
        'brandHealth': report_data.get('brandHealth'),
        'platformAnalysis': report_data.get('platformAnalysis'),
        'competitiveAnalysis': report_data.get('competitiveAnalysis'),
        'negativeSources': report_data.get('negativeSources')
    }


# 注册 Blueprint
def register_blueprints(app):
    """注册 PDF 导出 Blueprint"""
    app.register_blueprint(pdf_export_bp)
    api_logger.info('PDF Export Blueprint registered')
    
    # 启动清理线程
    from wechat_backend.services.async_export_service import start_cleanup_thread
    start_cleanup_thread(interval_hours=1, max_age_hours=24)
