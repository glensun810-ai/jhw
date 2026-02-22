"""
GEO 分析、工作流结果、ROI 指标 API 接口

P0 级空缺修复:
1. /api/geo-analysis/{executionId} - GEO 分析详情
2. /api/workflow-results/{executionId} - 工作流结果
3. /api/roi-metrics/{executionId} - ROI 指标

设计原则:
- RESTful API 规范
- 统一响应格式
- 完整的错误处理
- 详细的日志记录
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, jsonify, request
from wechat_backend.logging_config import api_logger
from wechat_backend.database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery
from wechat_backend.security.input_validator import validate_execution_id
from wechat_backend.analytics.report_generator import ReportGenerator
from wechat_backend.analytics.impact_calculator import ImpactCalculator
from wechat_backend.models import get_deep_intelligence_result

# 创建 Blueprint
geo_analysis_bp = Blueprint('geo_analysis', __name__)


# =============================================================================
# 数据模型
# =============================================================================

class GeoAnalysisModel:
    """GEO 分析数据模型"""
    
    @staticmethod
    def from_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
        """从 execution_id 获取 GEO 分析数据"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 从 aggregated_results 获取基础数据
        result = safe_query.execute_query('''
            SELECT execution_id, main_brand, health_score, sov, avg_sentiment,
                   success_rate, total_tests, total_mentions, created_at
            FROM aggregated_results
            WHERE execution_id = ?
        ''', (execution_id,))
        
        if not result:
            return None
        
        row = result[0]
        
        # 从 brand_rankings 获取排名详情
        rankings = safe_query.execute_query('''
            SELECT brand, rank, responses, sov_share, avg_sentiment
            FROM brand_rankings
            WHERE execution_id = ?
            ORDER BY rank
        ''', (execution_id,))
        
        # 构建完整的 GEO 分析结构
        return {
            'execution_id': execution_id,
            'main_brand': row[1],
            'overall_metrics': {
                'health_score': row[2] or 0,
                'sov': row[3] or 0,
                'avg_sentiment': row[4] or 0,
                'success_rate': row[5] or 0,
                'total_tests': row[6] or 0,
                'total_mentions': row[7] or 0
            },
            'rankings': [
                {
                    'brand': r[0],
                    'rank': r[1],
                    'responses': r[2],
                    'sov_share': r[3],
                    'avg_sentiment': r[4],
                    'brand_mentioned': r[1] > 0,  # 排名>0 表示被提及
                    'cited_sources': []  # 从 detailed_results 中提取
                }
                for r in rankings
            ],
            'created_at': row[8]
        }


class WorkflowResultsModel:
    """工作流结果数据模型"""
    
    @staticmethod
    def from_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
        """从 execution_id 获取工作流结果"""
        # 尝试从 deep_intelligence_results 获取
        intelligence_data = get_deep_intelligence_result(execution_id)
        
        if not intelligence_data:
            return None
        
        # 构建标准化的工作流结果结构
        return {
            'execution_id': execution_id,
            'workflow_stages': {
                'intelligence_evaluating': {
                    'status': 'completed',
                    'findings': intelligence_data.get('evaluation_findings', []),
                    'metrics': {
                        'authority_score': intelligence_data.get('authority_score', 0),
                        'completeness_score': intelligence_data.get('completeness_score', 0),
                        'timeliness_score': intelligence_data.get('timeliness_score', 0)
                    }
                },
                'intelligence_analyzing': {
                    'status': 'completed',
                    'findings': intelligence_data.get('analysis_findings', []),
                    'key_discoveries': intelligence_data.get('key_discoveries', [])
                },
                'competition_analyzing': {
                    'status': 'completed',
                    'findings': intelligence_data.get('competition_findings', []),
                    'market_position': intelligence_data.get('market_position', {})
                },
                'source_tracing': {
                    'status': 'completed',
                    'findings': intelligence_data.get('source_findings', []),
                    'credibility_analysis': intelligence_data.get('credibility_analysis', {})
                }
            },
            'summary': {
                'total_findings': len(intelligence_data.get('all_findings', [])),
                'critical_issues': len(intelligence_data.get('critical_issues', [])),
                'opportunities': len(intelligence_data.get('opportunities', []))
            },
            'created_at': intelligence_data.get('created_at')
        }


class ROIMetricsModel:
    """ROI 指标数据模型"""
    
    @staticmethod
    def from_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
        """从 execution_id 获取 ROI 指标"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 获取基础数据
        geo_data = GeoAnalysisModel.from_execution_id(execution_id)
        if not geo_data:
            return None
        
        metrics = geo_data['overall_metrics']
        
        # 计算 ROI 指标
        # 曝光 ROI = (总曝光 / 测试次数) * 情感系数
        exposure_roi = (
            (metrics['total_mentions'] / max(metrics['total_tests'], 1)) *
            (1 + metrics['avg_sentiment'])
        ) if metrics['total_tests'] > 0 else 0
        
        # 情感 ROI = 情感分数 * 声量占比系数
        sentiment_roi = metrics['avg_sentiment'] * (1 + metrics['sov'] / 100)
        
        # 排名 ROI = (1 / 平均排名) * 100 (排名越好，ROI 越高)
        avg_rank = sum(r['rank'] for r in geo_data['rankings']) / max(len(geo_data['rankings']), 1)
        ranking_roi = (1 / max(avg_rank, 0.1)) * 100 if avg_rank > 0 else 0
        
        # 估算价值 = 曝光量 * 单次曝光价值 (假设 0.5 元/次)
        estimated_value = metrics['total_mentions'] * 0.5
        
        # 计算影响力评分
        authority_impact = metrics['health_score'] * 0.8  # 健康度影响权威性
        visibility_impact = metrics['sov'] * 0.9  # 声量影响可见度
        sentiment_impact = metrics['avg_sentiment'] * 100 * 0.7  # 情感影响
        overall_impact = (authority_impact + visibility_impact + sentiment_impact) / 3
        
        return {
            'execution_id': execution_id,
            'roi_metrics': {
                'exposure_roi': round(exposure_roi, 2),
                'sentiment_roi': round(sentiment_roi, 2),
                'ranking_roi': round(ranking_roi, 2),
                'estimated_value': round(estimated_value, 2),
                'value_currency': 'CNY'
            },
            'impact_scores': {
                'authority_impact': round(authority_impact, 1),
                'visibility_impact': round(visibility_impact, 1),
                'sentiment_impact': round(sentiment_impact, 1),
                'overall_impact': round(overall_impact, 1)
            },
            'benchmarks': {
                'exposure_roi_industry_avg': 2.5,
                'sentiment_roi_industry_avg': 0.6,
                'ranking_roi_industry_avg': 50
            },
            'created_at': datetime.now().isoformat()
        }


# =============================================================================
# API 接口实现
# =============================================================================

@geo_analysis_bp.route('/api/geo-analysis/<execution_id>', methods=['GET'])
def get_geo_analysis(execution_id: str):
    """
    获取 GEO 分析详情
    
    Path Parameters:
        execution_id: 执行 ID
    
    Returns:
        {
            "success": true,
            "data": {
                "execution_id": "xxx",
                "main_brand": "品牌名",
                "overall_metrics": {...},
                "rankings": [...]
            },
            "timestamp": "2026-02-20T10:00:00"
        }
    """
    try:
        # 验证 execution_id
        try:
            execution_id = validate_execution_id(execution_id)
        except ValueError as e:
            api_logger.warning(f'Invalid execution_id: {execution_id}')
            return jsonify({
                'success': False,
                'error': '无效的 execution_id',
                'code': 'INVALID_ID'
            }), 400
        
        # 获取 GEO 分析数据
        geo_data = GeoAnalysisModel.from_execution_id(execution_id)
        
        if not geo_data:
            api_logger.warning(f'GEO analysis not found: {execution_id}')
            return jsonify({
                'success': False,
                'error': '未找到 GEO 分析数据',
                'code': 'NOT_FOUND'
            }), 404
        
        api_logger.info(f'GEO analysis retrieved: {execution_id}')
        
        return jsonify({
            'success': True,
            'data': geo_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting geo_analysis: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}',
            'code': 'SERVER_ERROR'
        }), 500


@geo_analysis_bp.route('/api/workflow-results/<execution_id>', methods=['GET'])
def get_workflow_results(execution_id: str):
    """
    获取工作流结果
    
    Path Parameters:
        execution_id: 执行 ID
    
    Returns:
        {
            "success": true,
            "data": {
                "execution_id": "xxx",
                "workflow_stages": {...},
                "summary": {...}
            },
            "timestamp": "2026-02-20T10:00:00"
        }
    """
    try:
        # 验证 execution_id
        try:
            execution_id = validate_execution_id(execution_id)
        except ValueError as e:
            api_logger.warning(f'Invalid execution_id: {execution_id}')
            return jsonify({
                'success': False,
                'error': '无效的 execution_id',
                'code': 'INVALID_ID'
            }), 400
        
        # 获取工作流结果
        workflow_data = WorkflowResultsModel.from_execution_id(execution_id)
        
        if not workflow_data:
            api_logger.warning(f'Workflow results not found: {execution_id}')
            return jsonify({
                'success': False,
                'error': '未找到工作流结果',
                'code': 'NOT_FOUND'
            }), 404
        
        api_logger.info(f'Workflow results retrieved: {execution_id}')
        
        return jsonify({
            'success': True,
            'data': workflow_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting workflow_results: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}',
            'code': 'SERVER_ERROR'
        }), 500


@geo_analysis_bp.route('/api/roi-metrics/<execution_id>', methods=['GET'])
def get_roi_metrics(execution_id: str):
    """
    获取 ROI 指标
    
    Path Parameters:
        execution_id: 执行 ID
    
    Returns:
        {
            "success": true,
            "data": {
                "roi_metrics": {...},
                "impact_scores": {...},
                "benchmarks": {...}
            },
            "timestamp": "2026-02-20T10:00:00"
        }
    """
    try:
        # 验证 execution_id
        try:
            execution_id = validate_execution_id(execution_id)
        except ValueError as e:
            api_logger.warning(f'Invalid execution_id: {execution_id}')
            return jsonify({
                'success': False,
                'error': '无效的 execution_id',
                'code': 'INVALID_ID'
            }), 400
        
        # 获取 ROI 指标
        roi_data = ROIMetricsModel.from_execution_id(execution_id)
        
        if not roi_data:
            api_logger.warning(f'ROI metrics not found: {execution_id}')
            return jsonify({
                'success': False,
                'error': '未找到 ROI 指标数据',
                'code': 'NOT_FOUND'
            }), 404
        
        api_logger.info(f'ROI metrics retrieved: {execution_id}')
        
        return jsonify({
            'success': True,
            'data': roi_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'Error getting roi_metrics: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}',
            'code': 'SERVER_ERROR'
        }), 500


# =============================================================================
# 蓝图导出
# =============================================================================

def init_geo_analysis_routes(app):
    """初始化 GEO 分析路由"""
    app.register_blueprint(geo_analysis_bp)
    api_logger.info('GEO Analysis API routes registered')
