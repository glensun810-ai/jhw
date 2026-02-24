#!/usr/bin/env python3
"""
PDF 报告导出 API 端点
完整支持品牌诊断报告导出

修复版本：v1.1
修复内容:
1. 修复表名错误 (test_results → test_records)
2. 添加 gzip 解压缩支持
3. 修复 execution_id 查询逻辑
"""

import gzip
import json
from flask import Blueprint, request, Response, jsonify
from datetime import datetime
from wechat_backend.logging_config import api_logger
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.security.auth import require_auth_optional, get_current_user_id

# 创建 Blueprint
pdf_export_bp = Blueprint('pdf_export', __name__)


@pdf_export_bp.route('/api/export/pdf', methods=['GET'])
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
def export_pdf_report():
    """
    导出测试报告为 PDF

    Query Parameters:
    - executionId: 测试执行 ID

    Returns:
    - PDF file download
    """
    user_id = get_current_user_id() or 'anonymous'
    api_logger.info(f"PDF export endpoint accessed by user: {user_id}")

    try:
        # 从查询参数获取参数
        execution_id = request.args.get('executionId', '')

        if not execution_id:
            return jsonify({'error': 'executionId is required', 'code': 'MISSING_EXECUTION_ID'}), 400

        # 验证输入参数
        if not isinstance(execution_id, str) or len(execution_id) < 3:
            return jsonify({'error': 'Invalid executionId', 'code': 'INVALID_EXECUTION_ID'}), 400

    except Exception as e:
        api_logger.error(f"Input validation failed: {str(e)}")
        return jsonify({'error': 'Invalid input data', 'code': 'VALIDATION_ERROR'}), 400

    try:
        # 获取诊断报告数据
        from wechat_backend.models import get_deep_intelligence_result
        from wechat_backend.database import get_connection

        # 尝试从 deep_intelligence_results 获取
        deep_result = get_deep_intelligence_result(execution_id)

        if not deep_result:
            # 修复：从 test_records 表获取（实际存在的表）
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, brand_name, test_date, ai_models_used, questions_used,
                           overall_score, total_tests, results_summary, detailed_results,
                           is_summary_compressed, is_detailed_compressed
                    FROM test_records
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()

                # 查找匹配 execution_id 的记录
                for row in rows:
                    columns = ['id', 'user_id', 'brand_name', 'test_date', 'ai_models_used', 
                               'questions_used', 'overall_score', 'total_tests', 'results_summary', 
                               'detailed_results', 'is_summary_compressed', 'is_detailed_compressed']
                    record_data = dict(zip(columns, row))
                    
                    # 解析 results_summary（可能需要解压）
                    results_summary_raw = record_data.get('results_summary')
                    is_compressed = record_data.get('is_summary_compressed', 0)
                    
                    try:
                        if is_compressed and results_summary_raw:
                            results_summary_bytes = gzip.decompress(results_summary_raw)
                            results_summary = json.loads(results_summary_bytes.decode('utf-8'))
                        elif results_summary_raw:
                            results_summary = json.loads(results_summary_raw)
                        else:
                            results_summary = {}
                    except (json.JSONDecodeError, TypeError, gzip.BadGzipFile):
                        results_summary = {}
                    
                    # 检查是否匹配 execution_id
                    summary_exec_id = results_summary.get('execution_id', '')
                    if summary_exec_id == execution_id:
                        # 解析 detailed_results
                        detailed_results_raw = record_data.get('detailed_results')
                        is_detailed_compressed = record_data.get('is_detailed_compressed', 0)
                        
                        try:
                            if is_detailed_compressed and detailed_results_raw:
                                detailed_results_bytes = gzip.decompress(detailed_results_raw)
                                detailed_results = json.loads(detailed_results_bytes.decode('utf-8'))
                            elif detailed_results_raw:
                                detailed_results = json.loads(detailed_results_raw)
                            else:
                                detailed_results = []
                        except (json.JSONDecodeError, TypeError, gzip.BadGzipFile):
                            detailed_results = []

                        # 解析其他 JSON 字段
                        try:
                            ai_models_used = json.loads(record_data.get('ai_models_used', '[]'))
                            questions_used = json.loads(record_data.get('questions_used', '[]'))
                        except Exception as e:

                            pass  # TODO: 添加适当的错误处理
                            ai_models_used = []
                            questions_used = []

                        # 构建 deep_result
                        deep_result = {
                            'execution_id': summary_exec_id,
                            'result_id': record_data.get('id'),
                            'brand_name': record_data.get('brand_name', '未知品牌'),
                            'test_date': record_data.get('test_date', ''),
                            'ai_models_used': ai_models_used,
                            'questions_used': questions_used,
                            'overall_score': record_data.get('overall_score', 0) or 0,
                            'total_tests': record_data.get('total_tests', 0) or 0,
                            'results_summary': results_summary,
                            'detailed_results': detailed_results,
                            'platform_scores': [],
                            'dimension_scores': {}
                        }
                        
                        # 从 results_summary 中提取更多信息
                        if results_summary:
                            deep_result['competitor_brands'] = results_summary.get('competitor_brands', [])
                            deep_result['formula'] = results_summary.get('formula', '')
                        
                        break

        if not deep_result:
            return jsonify({'error': 'Test result not found', 'code': 'RESULT_NOT_FOUND'}), 404

        # 构建平台评分
        detailed_results = deep_result.get('detailed_results', [])
        if isinstance(detailed_results, list):
            for result in detailed_results:
                if isinstance(result, dict):
                    deep_result.setdefault('platform_scores', []).append({
                        'platform': result.get('model', result.get('platform', 'Unknown')),
                        'score': result.get('score', result.get('overall_score', 0)),
                        'rank': result.get('rank', 0),
                        'sentiment': result.get('sentiment', 0)
                    })

        # 构建维度评分
        deep_result['dimension_scores'] = {
            'authority': deep_result.get('authority_score', 75),
            'visibility': deep_result.get('visibility_score', 70),
            'purity': deep_result.get('purity_score', 80),
            'consistency': deep_result.get('consistency_score', 75)
        }

        # 准备测试数据
        test_data = {
            'executionId': execution_id,
            'brandName': deep_result.get('brand_name', '未知品牌'),
            'competitorBrands': deep_result.get('competitor_brands', []),
            'aiModels': deep_result.get('ai_models_used', []),
            'overallScore': deep_result.get('overall_score', 0),
            'platformScores': deep_result.get('platform_scores', []),
            'dimensionScores': deep_result.get('dimension_scores', {}),
            'testDate': deep_result.get('test_date', datetime.now().isoformat()),
            'recommendations': deep_result.get('recommendations', []),
            'questionCards': deep_result.get('question_cards', []),
            'toxicSources': deep_result.get('toxic_sources', []),
            'roiMetrics': deep_result.get('roi_metrics', {})
        }

        # 生成 PDF 报告
        from wechat_backend.services.pdf_export_service import get_pdf_export_service
        pdf_service = get_pdf_export_service()
        pdf_data = pdf_service.generate_test_report(test_data)

        api_logger.info(f"PDF report generated successfully: executionId={execution_id}, size={len(pdf_data)} bytes")

        # 返回 PDF 文件
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=report_{execution_id}_{datetime.now().strftime("%Y%m%d")}.pdf',
                'Content-Length': len(pdf_data),
                'Access-Control-Expose-Headers': 'Content-Disposition'
            }
        )

    except json.JSONDecodeError as e:
        api_logger.error(f"JSON decode error: {e}")
        return jsonify({'error': 'Data format error', 'code': 'JSON_ERROR'}), 500
    except Exception as e:
        api_logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate PDF report', 'details': str(e), 'code': 'PDF_GENERATION_ERROR'}), 500


@pdf_export_bp.route('/api/export/html', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def export_html_report():
    """
    导出测试报告为 HTML（用于微信小程序预览）

    Query Parameters:
    - executionId: 测试执行 ID

    Returns:
    - HTML content
    """
    user_id = get_current_user_id() or 'anonymous'
    execution_id = request.args.get('executionId', '')

    if not execution_id:
        return jsonify({'error': 'executionId is required'}), 400

    try:
        # 获取报告数据（与 PDF 导出相同）
        from wechat_backend.models import get_deep_intelligence_result
        deep_result = get_deep_intelligence_result(execution_id)

        if not deep_result:
            return jsonify({'error': 'Test result not found'}), 404

        # 生成 HTML 内容
        html_content = generate_html_report(deep_result, execution_id)

        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'inline; filename=report_{execution_id}.html',
            }
        )

    except Exception as e:
        api_logger.error(f"Error generating HTML report: {e}")
        return jsonify({'error': 'Failed to generate HTML report', 'details': str(e)}), 500


def generate_html_report(data: Dict[str, Any], execution_id: str) -> str:
    """生成 HTML 报告内容"""
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GEO 品牌战略诊断报告 - {data.get('brand_name', '未知品牌')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; padding: 20px; background: #f5f6fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a2e; font-size: 24px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        h2 {{ color: #667eea; font-size: 18px; margin-top: 30px; }}
        .summary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric-value {{ font-size: 32px; font-weight: bold; }}
        .metric-label {{ font-size: 12px; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #667eea; color: white; }}
        tr:nth-child(even) {{ background: #f5f6fa; }}
        .footer {{ margin-top: 40px; text-align: center; color: #999; font-size: 12px; }}
        .score-good {{ color: #10b981; }}
        .score-medium {{ color: #f59e0b; }}
        .score-bad {{ color: #ef4444; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>GEO 品牌战略诊断报告</h1>
        <p>执行 ID: {execution_id}</p>
        <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="metric">
                <div class="metric-value">{data.get('overall_score', 0)}</div>
                <div class="metric-label">品牌健康度</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data.get('sov', 0)}%</div>
                <div class="metric-label">AI 声量占比</div>
            </div>
            <div class="metric">
                <div class="metric-value">{(data.get('avg_sentiment', 0)):.2f}</div>
                <div class="metric-label">情感均值</div>
            </div>
        </div>

        <h2>基本信息</h2>
        <table>
            <tr><th>测试品牌</th><td>{data.get('brand_name', '-')}</td></tr>
            <tr><th>测试日期</th><td>{data.get('test_date', '-')}</td></tr>
            <tr><th>AI 模型</th><td>{', '.join(data.get('ai_models_used', []))}</td></tr>
        </table>

        <div class="footer">
            <p>云程企航 · AI 搜索品牌影响力监测</p>
        </div>
    </div>
</body>
</html>
"""


# 注册 Blueprint
def register_blueprints(app):
    """注册 PDF 导出 Blueprint"""
    app.register_blueprint(pdf_export_bp)
    api_logger.info('PDF Export Blueprint registered')
