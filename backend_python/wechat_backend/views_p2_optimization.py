"""
P2 级空缺修复：趋势预测增强、货币化分析 API

新增 API 接口:
1. /api/trend-forecast/{executionId} - 趋势预测增强 (置信区间、情景分析)
2. /api/monetization-analysis/{executionId} - 货币化分析

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
from database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery
from wechat_backend.security.input_validator import validate_execution_id

# 创建 Blueprint
p2_optimization_bp = Blueprint('p2_optimization', __name__)


# =============================================================================
# 数据模型
# =============================================================================

class TrendForecastModel:
    """趋势预测数据模型"""
    
    @staticmethod
    def from_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
        """从 execution_id 获取趋势预测数据"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 获取基础数据
        result = safe_query.execute_query('''
            SELECT execution_id, main_brand, health_score, created_at
            FROM aggregated_results
            WHERE execution_id = ?
        ''', (execution_id,))
        
        if not result:
            return None
        
        row = result[0]
        health_score = row[2] or 0
        created_at = row[3]
        
        # 生成预测数据
        forecast_points = TrendForecastModel._generate_forecast(health_score, created_at)
        
        # 情景分析
        scenario_analysis = TrendForecastModel._generate_scenario_analysis(health_score)
        
        # 置信区间
        confidence_interval = TrendForecastModel._calculate_confidence_interval(health_score)
        
        # 趋势强度
        trend_strength = TrendForecastModel._calculate_trend_strength(health_score)
        
        # 拐点分析
        inflection_points = TrendForecastModel._identify_inflection_points(health_score)
        
        return {
            'execution_id': execution_id,
            'main_brand': row[1],
            'current_score': health_score,
            'forecast_points': forecast_points,
            'confidence': confidence_interval['confidence'],
            'confidence_interval': confidence_interval['interval'],
            'trend': 'improving' if health_score > 50 else 'declining',
            'trend_strength': trend_strength,
            'inflection_points': inflection_points,
            'scenario_analysis': scenario_analysis,
            'created_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def _generate_forecast(current_score, start_date) -> List[Dict[str, Any]]:
        """生成预测点"""
        forecast = []
        base_date = datetime.fromisoformat(start_date) if isinstance(start_date, str) else datetime.now()
        
        # 生成未来 4 周的预测
        for week in range(1, 5):
            forecast_date = base_date + timedelta(weeks=week)
            
            # 简单线性预测 (实际应使用更复杂的模型)
            improvement_rate = 0.05 if current_score < 80 else 0.02
            forecast_score = min(100, current_score * (1 + improvement_rate * week))
            
            forecast.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'week': week,
                'score': round(forecast_score, 1),
                'lower_bound': round(forecast_score * 0.9, 1),
                'upper_bound': round(forecast_score * 1.1, 1)
            })
        
        return forecast
    
    @staticmethod
    def _generate_scenario_analysis(current_score) -> Dict[str, Any]:
        """生成情景分析"""
        return {
            'best_case': {
                'score': min(100, round(current_score * 1.15, 1)),
                'probability': 0.3,
                'description': '品牌策略全面优化，情感倾向显著提升'
            },
            'base_case': {
                'score': min(100, round(current_score * 1.05, 1)),
                'probability': 0.5,
                'description': '维持当前策略，稳步提升'
            },
            'worst_case': {
                'score': max(0, round(current_score * 0.85, 1)),
                'probability': 0.2,
                'description': '市场竞争加剧，品牌声量下降'
            }
        }
    
    @staticmethod
    def _calculate_confidence_interval(current_score) -> Dict[str, Any]:
        """计算置信区间"""
        # 分数越高，置信度越高
        confidence = min(0.95, 0.5 + (current_score / 200))
        
        # 置信区间宽度
        margin = (1 - confidence) * 20
        
        return {
            'confidence': round(confidence, 2),
            'interval': {
                'lower': round(current_score - margin, 1),
                'upper': round(current_score + margin, 1)
            }
        }
    
    @staticmethod
    def _calculate_trend_strength(current_score) -> str:
        """计算趋势强度"""
        if current_score >= 80:
            return 'strong'
        elif current_score >= 60:
            return 'moderate'
        elif current_score >= 40:
            return 'weak'
        else:
            return 'very_weak'
    
    @staticmethod
    def _identify_inflection_points(current_score) -> List[Dict[str, Any]]:
        """识别拐点"""
        inflection_points = []
        
        # 简化版拐点识别
        if current_score < 50:
            inflection_points.append({
                'type': 'warning',
                'score_threshold': 50,
                'description': '品牌健康度低于 50，需要立即采取行动'
            })
        
        if current_score > 70:
            inflection_points.append({
                'type': 'opportunity',
                'score_threshold': 80,
                'description': '接近优秀水平，加大投入可实现突破'
            })
        
        return inflection_points


class MonetizationAnalysisModel:
    """货币化分析数据模型"""
    
    @staticmethod
    def from_execution_id(execution_id: str) -> Optional[Dict[str, Any]]:
        """从 execution_id 获取货币化分析数据"""
        safe_query = SafeDatabaseQuery(DB_PATH)
        
        # 获取基础数据
        result = safe_query.execute_query('''
            SELECT execution_id, main_brand, total_mentions, sov, avg_sentiment
            FROM aggregated_results
            WHERE execution_id = ?
        ''', (execution_id,))
        
        if not result:
            return None
        
        row = result[0]
        total_mentions = row[2] or 0
        sov = row[3] or 0
        avg_sentiment = row[4] or 0
        
        # 计算货币化指标
        estimated_media_value = MonetizationAnalysisModel._calculate_media_value(total_mentions, avg_sentiment)
        cost_per_impression = MonetizationAnalysisModel._calculate_cpi(total_mentions)
        organic_vs_paid = MonetizationAnalysisModel._analyze_organic_vs_paid(total_mentions)
        roi_projection = MonetizationAnalysisModel._project_roi(sov, avg_sentiment)
        
        return {
            'execution_id': execution_id,
            'main_brand': row[1],
            'monetization_metrics': {
                'estimated_media_value': estimated_media_value,
                'value_currency': 'CNY',
                'cost_per_impression': cost_per_impression,
                'organic_vs_paid': organic_vs_paid,
                'roi_projection': roi_projection
            },
            'breakdown': {
                'by_platform': MonetizationAnalysisModel._platform_breakdown(total_mentions),
                'by_sentiment': MonetizationAnalysisModel._sentiment_breakdown(total_mentions, avg_sentiment)
            },
            'recommendations': MonetizationAnalysisModel._generate_recommendations(estimated_media_value, roi_projection),
            'created_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def _calculate_media_value(total_mentions, avg_sentiment) -> float:
        """估算媒体价值"""
        # 假设每次正面提及价值 500 元，中性 200 元，负面 -100 元
        positive_value = total_mentions * avg_sentiment * 500
        neutral_value = total_mentions * (1 - abs(avg_sentiment - 0.5) * 2) * 200
        negative_value = total_mentions * (1 - avg_sentiment) * (-100)
        
        return round(positive_value + neutral_value + negative_value, 2)
    
    @staticmethod
    def _calculate_cpi(total_mentions) -> float:
        """计算单次曝光成本"""
        if total_mentions == 0:
            return 0
        
        # 假设总投入 10000 元
        total_cost = 10000
        return round(total_cost / total_mentions, 2)
    
    @staticmethod
    def _analyze_organic_vs_paid(total_mentions) -> Dict[str, Any]:
        """分析自然流量与付费流量比例"""
        # 简化版分析
        organic_percentage = min(80, 50 + (total_mentions / 10))
        paid_percentage = 100 - organic_percentage
        
        return {
            'organic_percentage': round(organic_percentage, 1),
            'paid_percentage': round(paid_percentage, 1),
            'organic_value': round(total_mentions * organic_percentage / 100, 0),
            'paid_value': round(total_mentions * paid_percentage / 100, 0)
        }
    
    @staticmethod
    def _project_roi(sov, avg_sentiment) -> Dict[str, float]:
        """预测 ROI"""
        base_roi = 2.0
        
        # 声量占比影响
        sov_factor = sov / 30  # 30% 为基准
        
        # 情感影响
        sentiment_factor = avg_sentiment / 0.5  # 0.5 为基准
        
        return {
            '3_month_roi': round(base_roi * sov_factor * sentiment_factor * 0.8, 2),
            '6_month_roi': round(base_roi * sov_factor * sentiment_factor * 1.2, 2),
            '12_month_roi': round(base_roi * sov_factor * sentiment_factor * 2.0, 2)
        }
    
    @staticmethod
    def _platform_breakdown(total_mentions) -> Dict[str, Any]:
        """平台分布"""
        platforms = ['知乎', '小红书', '什么值得买', '百度', '谷歌']
        breakdown = {}
        
        remaining = total_mentions
        for i, platform in enumerate(platforms):
            if i == len(platforms) - 1:
                count = remaining
            else:
                count = int(total_mentions * (0.3 - i * 0.05))
                remaining -= count
            
            breakdown[platform] = {
                'mentions': count,
                'estimated_value': round(count * 300, 2)
            }
        
        return breakdown
    
    @staticmethod
    def _sentiment_breakdown(total_mentions, avg_sentiment) -> Dict[str, Any]:
        """情感分布"""
        positive = int(total_mentions * avg_sentiment)
        negative = int(total_mentions * (1 - avg_sentiment) * 0.3)
        neutral = total_mentions - positive - negative
        
        return {
            'positive': {
                'count': positive,
                'value': round(positive * 500, 2)
            },
            'neutral': {
                'count': max(0, neutral),
                'value': round(max(0, neutral) * 200, 2)
            },
            'negative': {
                'count': max(0, negative),
                'value': round(max(0, negative) * (-100), 2)
            }
        }
    
    @staticmethod
    def _generate_recommendations(media_value, roi_projection) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        
        if media_value > 50000:
            recommendations.append({
                'action': '加大高价值平台投入',
                'rationale': f'当前媒体价值 {media_value:.0f} 元，具备规模化基础',
                'expected_impact': 'high'
            })
        
        if roi_projection['12_month_roi'] > 4.0:
            recommendations.append({
                'action': '长期投入品牌建设',
                'rationale': '长期 ROI 预测优秀，适合持续投入',
                'expected_impact': 'high'
            })
        
        return recommendations or [{
            'action': '维持当前策略',
            'rationale': '各项指标均衡',
            'expected_impact': 'medium'
        }]


# =============================================================================
# API 接口实现
# =============================================================================

@p2_optimization_bp.route('/api/trend-forecast/<execution_id>', methods=['GET'])
def get_trend_forecast(execution_id: str):
    """获取趋势预测增强数据"""
    try:
        execution_id = validate_execution_id(execution_id)
        
        data = TrendForecastModel.from_execution_id(execution_id)
        
        if not data:
            return jsonify({
                'success': False,
                'error': '未找到趋势预测数据',
                'code': 'NOT_FOUND'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'INVALID_ID'
        }), 400
    except Exception as e:
        api_logger.error(f'Error getting trend_forecast: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}',
            'code': 'SERVER_ERROR'
        }), 500


@p2_optimization_bp.route('/api/monetization-analysis/<execution_id>', methods=['GET'])
def get_monetization_analysis(execution_id: str):
    """获取货币化分析"""
    try:
        execution_id = validate_execution_id(execution_id)
        
        data = MonetizationAnalysisModel.from_execution_id(execution_id)
        
        if not data:
            return jsonify({
                'success': False,
                'error': '未找到货币化分析数据',
                'code': 'NOT_FOUND'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'INVALID_ID'
        }), 400
    except Exception as e:
        api_logger.error(f'Error getting monetization_analysis: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误：{str(e)}',
            'code': 'SERVER_ERROR'
        }), 500


# =============================================================================
# 蓝图导出
# =============================================================================

def init_p2_optimization_routes(app):
    """初始化 P2 优化路由"""
    app.register_blueprint(p2_optimization_bp)
    api_logger.info('P2 Optimization API routes registered')
