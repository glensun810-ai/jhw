"""
Dashboard API 模块 - 品牌诊断报告看板数据

功能：
1. Dashboard 聚合数据查询
2. ROI 指标和影响力评分
3. 品牌分析数据补充

作者：系统架构组
日期：2026-03-06
版本：1.0.0
"""

from flask import Blueprint, request, jsonify, g
from typing import Dict, Any, Optional
from datetime import datetime

from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.monitoring.monitoring_decorator import monitored_endpoint
from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository

# 导入 Dashboard 格式转换函数
try:
    from wechat_backend.views.diagnosis_views import convert_to_dashboard_format
except ImportError:
    # 如果从 diagnosis_views 导入失败，尝试从 views_geo_analysis 导入
    try:
        from wechat_backend.views.views_geo_analysis import convert_to_dashboard_format
    except ImportError:
        # 如果都失败，使用空函数
        def convert_to_dashboard_format(aggregate_result, all_brands, main_brand, additional_data=None):
            """备用转换函数"""
            api_logger.warning("convert_to_dashboard_format not found, using empty function")
            return {}


# ==================== Dashboard 数据增强函数 ====================

def enrich_dashboard_with_roi(dashboard_data: dict, execution_id: str) -> dict:
    """
    P0 级空缺修复：为 Dashboard 数据添加 ROI 指标和影响力评分

    Args:
        dashboard_data: 原始 Dashboard 数据
        execution_id: 执行 ID

    Returns:
        增强后的 Dashboard 数据
    """
    try:
        from wechat_backend.views.views_geo_analysis import ROIMetricsModel

        # 获取 ROI 指标
        roi_data = ROIMetricsModel.from_execution_id(execution_id)

        if roi_data:
            # 添加 ROI 指标
            dashboard_data['roi_metrics'] = roi_data['roi_metrics']
            dashboard_data['impact_scores'] = roi_data['impact_scores']
            dashboard_data['benchmarks'] = roi_data.get('benchmarks', {})

            api_logger.info(f"Dashboard enriched with ROI metrics for execution: {execution_id}")
        else:
            # 如果无法获取 ROI 数据，提供默认值
            dashboard_data['roi_metrics'] = {
                'exposure_roi': 0,
                'sentiment_roi': 0,
                'ranking_roi': 0,
                'estimated_value': 0
            }
            dashboard_data['impact_scores'] = {
                'authority_impact': 0,
                'visibility_impact': 0,
                'sentiment_impact': 0,
                'overall_impact': 0
            }
            api_logger.warning(f"Could not enrich ROI metrics for execution: {execution_id}")

    except Exception as e:
        api_logger.error(f"Error enriching dashboard with ROI: {e}")
        # 保持原数据，不抛出异常
        if 'roi_metrics' not in dashboard_data:
            dashboard_data['roi_metrics'] = {
                'exposure_roi': 0,
                'sentiment_roi': 0,
                'ranking_roi': 0,
                'estimated_value': 0
            }
        if 'impact_scores' not in dashboard_data:
            dashboard_data['impact_scores'] = {
                'authority_impact': 0,
                'visibility_impact': 0,
                'sentiment_impact': 0,
                'overall_impact': 0
            }

    # 【P1 修复 - 2026-03-06】补充品牌分析相关字段
    dashboard_data = enrich_dashboard_with_brand_analysis(dashboard_data, execution_id)

    return dashboard_data


def enrich_dashboard_with_brand_analysis(dashboard_data: dict, execution_id: str) -> dict:
    """
    P1 级修复：为 Dashboard 数据添加品牌分析相关字段

    Args:
        dashboard_data: 原始 Dashboard 数据
        execution_id: 执行 ID

    Returns:
        增强后的 Dashboard 数据
    """
    try:
        # 从 diagnosis_report_repository 获取后台分析结果
        report_repo = DiagnosisReportRepository()
        report = report_repo.get_by_execution_id(execution_id)
        
        # 【P1 修复】提取品牌分析数据
        if report:
            # brandAnalysis - 品牌分析数据
            if 'brandAnalysis' not in dashboard_data or dashboard_data['brandAnalysis'] is None:
                dashboard_data['brandAnalysis'] = report.get('brandAnalysis')
            
            # userBrandAnalysis - 用户品牌分析
            if 'userBrandAnalysis' not in dashboard_data or dashboard_data['userBrandAnalysis'] is None:
                dashboard_data['userBrandAnalysis'] = report.get('userBrandAnalysis')
            
            # competitorAnalysis - 竞品分析列表
            if 'competitorAnalysis' not in dashboard_data or dashboard_data['competitorAnalysis'] is None:
                dashboard_data['competitorAnalysis'] = report.get('competitorAnalysis', [])
            
            # comparison - 品牌对比数据
            if 'comparison' not in dashboard_data or dashboard_data['comparison'] is None:
                dashboard_data['comparison'] = report.get('comparison')
            
            # top3Brands - Top3 品牌排名
            if 'top3Brands' not in dashboard_data or dashboard_data['top3Brands'] is None:
                dashboard_data['top3Brands'] = report.get('top3Brands', [])
            
            api_logger.info(f"Dashboard enriched with brand analysis for execution: {execution_id}")
        else:
            # 提供默认值
            dashboard_data.setdefault('brandAnalysis', None)
            dashboard_data.setdefault('userBrandAnalysis', None)
            dashboard_data.setdefault('competitorAnalysis', [])
            dashboard_data.setdefault('comparison', None)
            dashboard_data.setdefault('top3Brands', [])
            api_logger.warning(f"Could not enrich brand analysis for execution: {execution_id}")

    except Exception as e:
        api_logger.error(f"Error enriching dashboard with brand analysis: {e}")
        # 保持原数据，提供默认值
        dashboard_data.setdefault('brandAnalysis', None)
        dashboard_data.setdefault('userBrandAnalysis', None)
        dashboard_data.setdefault('competitorAnalysis', [])
        dashboard_data.setdefault('comparison', None)
        dashboard_data.setdefault('top3Brands', [])

    return dashboard_data


# ==================== Dashboard API 路由 ====================

# 创建独立的 Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/aggregate', methods=['GET'])
@require_auth_optional
@rate_limit(limit=30, window=60, per='endpoint')
@monitored_endpoint('/api/dashboard/aggregate', require_auth=False, validate_inputs=True)
def get_dashboard_aggregate():
        """
        获取 Dashboard 聚合数据 (增强版 - P0 级空缺修复)

        查询参数:
            executionId: 执行 ID (可选，如果提供则从数据库获取)
            userOpenid: 用户 OpenID (可选)

        返回:
            {
                "success": true,
                "dashboard": {
                    "summary": {...},
                    "questionCards": [...],
                    "toxicSources": [...],
                    "roi_metrics": {...},
                    "impact_scores": {...},
                    "brandAnalysis": {...},
                    "userBrandAnalysis": {...},
                    "competitorAnalysis": [...],
                    "top3Brands": [...]
                }
            }
        """
        try:
            execution_id = request.args.get('executionId')
            user_openid = request.args.get('userOpenid', 'anonymous')

            api_logger.info(f"请求 Dashboard 聚合数据：executionId={execution_id}, userOpenid={user_openid}")

            # 使用 DiagnosisReportRepository 获取报告数据
            report_repo = DiagnosisReportRepository()
            report = report_repo.get_by_execution_id(execution_id)

            if report:
                api_logger.info(f"从数据库获取执行 ID {execution_id} 的报告")

                # 检查是否已经是 Dashboard 格式
                if 'dashboard' in report:
                    dashboard_data = report['dashboard']

                    # P0 增强：添加 ROI 指标和影响力评分
                    dashboard_data = enrich_dashboard_with_roi(dashboard_data, execution_id)

                    return jsonify({
                        'success': True,
                        'dashboard': dashboard_data
                    })
                else:
                    # 从报告中提取原始结果并转换为 Dashboard 格式
                    results = report.get('results', [])
                    brand_name = report.get('brand_name', '未知品牌')
                    competitors = report.get('competitor_brands', [])
                    
                    # 构建 additional_data
                    additional_data = {
                        'semantic_drift_data': report.get('semantic_drift_data'),
                        'recommendation_data': report.get('recommendation_data'),
                        'negative_sources': report.get('negative_sources'),
                        'competitive_analysis': report.get('competitive_analysis'),
                        'brand_analysis': report.get('brandAnalysis'),
                        'user_brand_analysis': report.get('userBrandAnalysis'),
                        'comparison': report.get('comparison'),
                        'top_3_brands': report.get('top3Brands', [])
                    }

                    # 转换为 Dashboard 格式
                    dashboard_data = convert_to_dashboard_format(
                        results,
                        brand_name,
                        competitors
                    )

                    # P0 增强：添加 ROI 指标和影响力评分
                    dashboard_data = enrich_dashboard_with_roi(dashboard_data, execution_id)

                    return jsonify({
                        'success': True,
                        'dashboard': dashboard_data
                    })

            # 如果没有找到报告，返回错误
            api_logger.warning(f"未找到 Dashboard 数据：executionId={execution_id}")
            return jsonify({
                'success': False,
                'error': '未找到测试数据，请先执行品牌测试',
                'code': 'NO_DATA'
            }), 404

        except Exception as e:
            api_logger.error(f"获取 Dashboard 聚合数据失败：{e}")
            return jsonify({
                'success': False,
                'error': f'服务器错误：{str(e)}'
            }), 500
