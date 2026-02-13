"""
预测引擎 - 认知趋势模拟与风险预测
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import math
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class PredictionEngine:
    """
    预测引擎 - 利用历史巡航数据实现趋势预测和风险识别
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def exponential_smoothing_forecast(self, data: List[float], alpha: float = 0.3, forecast_periods: int = 7) -> List[float]:
        """
        使用指数平滑法进行趋势预测
        
        Args:
            data: 历史数据序列
            alpha: 平滑系数 (0-1)，越大越重视近期数据
            forecast_periods: 预测期数
            
        Returns:
            预测值列表
        """
        if len(data) < 2:
            return [data[-1] if data else 0.0] * forecast_periods
            
        # 初始化
        smoothed_value = data[0]
        forecasts = []
        
        # 计算历史数据的平滑值
        for value in data[1:]:
            smoothed_value = alpha * value + (1 - alpha) * smoothed_value
            
        # 预测未来值（使用最后一个平滑值作为预测）
        for _ in range(forecast_periods):
            forecasts.append(smoothed_value)
            
        return forecasts
    
    def linear_regression_forecast(self, data: List[float], forecast_periods: int = 7) -> Tuple[List[float], float]:
        """
        使用线性回归进行趋势预测
        
        Args:
            data: 历史数据序列
            forecast_periods: 预测期数
            
        Returns:
            (预测值列表, 趋势斜率)
        """
        if len(data) < 2:
            return [data[-1] if data else 0.0] * forecast_periods, 0.0
            
        # 准备数据
        X = np.array(range(len(data))).reshape(-1, 1)
        y = np.array(data)
        
        # 训练线性回归模型
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测未来值
        last_index = len(data)
        future_indices = np.array(range(last_index, last_index + forecast_periods)).reshape(-1, 1)
        forecasts = model.predict(future_indices).tolist()
        
        # 返回预测值和趋势斜率
        return forecasts, model.coef_[0]
    
    def predict_ranking_trend(self, historical_ranks: List[int], days: int = 7) -> Dict[str, Any]:
        """
        预测品牌排名趋势
        
        Args:
            historical_ranks: 历史排名数据（数字越小表示排名越高）
            days: 预测天数
            
        Returns:
            预测结果字典
        """
        if not historical_ranks:
            return {
                'predicted_ranks': [1] * days,
                'confidence_interval': [(1, 1)] * days,
                'trend_direction': 'stable',
                'trend_strength': 0.0
            }
        
        # 使用线性回归预测
        forecasts, slope = self.linear_regression_forecast(historical_ranks, days)
        
        # 确保排名为正整数
        predicted_ranks = [max(1, round(f)) for f in forecasts]
        
        # 计算置信区间（基于标准误差）
        if len(historical_ranks) > 2:
            residuals = [historical_ranks[i] - (slope * i + historical_ranks[0]) for i in range(len(historical_ranks))]
            std_error = np.std(residuals) if residuals else 1.0
            confidence_interval = [(max(1, round(rank - 1.96 * std_error)), round(rank + 1.96 * std_error)) 
                                 for rank in predicted_ranks]
        else:
            confidence_interval = [(max(1, rank-2), rank+2) for rank in predicted_ranks]
        
        # 判断趋势方向
        if slope < -0.1:
            trend_direction = 'improving'  # 排名上升（数字变小）
        elif slope > 0.1:
            trend_direction = 'declining'  # 排名下降（数字变大）
        else:
            trend_direction = 'stable'
        
        return {
            'predicted_ranks': predicted_ranks,
            'confidence_interval': confidence_interval,
            'trend_direction': trend_direction,
            'trend_strength': abs(slope)
        }
    
    def identify_cognitive_risks(self, evidence_chain: List[Dict[str, Any]],
                                historical_ranks: List[int]) -> List[Dict[str, Any]]:
        """
        识别认知风险点

        Args:
            evidence_chain: 证据链数据
            historical_ranks: 历史排名数据

        Returns:
            风险因素列表
        """
        risks = []
        seen_risks = set()  # Track unique risks to avoid duplicates

        # 分析负面证据
        for evidence in evidence_chain:
            if evidence.get('risk_level', '').upper() in ['HIGH', 'MEDIUM']:
                negative_fragment = evidence.get('negative_fragment', '')
                associated_url = evidence.get('associated_url', '')
                source_name = evidence.get('source_name', '')
                risk_level = evidence.get('risk_level', 'Medium')

                # Create a unique identifier for this risk
                risk_identifier = (negative_fragment, associated_url, source_name)

                # Skip if we've already processed this risk
                if risk_identifier in seen_risks:
                    continue

                seen_risks.add(risk_identifier)

                # 评估风险对排名的潜在影响
                impact_score = self._calculate_risk_impact(negative_fragment, risk_level)

                # 如果有历史排名数据，评估趋势
                if historical_ranks and len(historical_ranks) >= 2:
                    recent_decline = self._assess_recent_decline(historical_ranks)
                    if recent_decline > 0:  # 有排名下降趋势
                        amplified_impact = impact_score * (1 + recent_decline * 0.1)
                    else:
                        amplified_impact = impact_score
                else:
                    amplified_impact = impact_score

                risk_entry = {
                    'risk_factor': negative_fragment[:100] + "..." if len(negative_fragment) > 100 else negative_fragment,
                    'associated_url': associated_url,
                    'source_name': source_name,
                    'risk_level': risk_level,
                    'potential_impact_on_rank': amplified_impact,
                    'estimated_rank_degradation': round(amplified_impact)
                }

                risks.append(risk_entry)

        # 按潜在影响排序
        risks.sort(key=lambda x: x['potential_impact_on_rank'], reverse=True)

        return risks
    
    def _calculate_risk_impact(self, negative_fragment: str, risk_level: str) -> float:
        """
        计算风险影响分数
        
        Args:
            negative_fragment: 负面内容片段
            risk_level: 风险级别
            
        Returns:
            影响分数
        """
        # 基础分数根据风险级别
        level_multiplier = {'HIGH': 3.0, 'MEDIUM': 2.0, 'LOW': 1.0}
        base_score = level_multiplier.get(risk_level.upper(), 2.0)
        
        # 根据负面内容的关键字增加分数
        keywords = ['安全', '漏洞', '欺诈', '虚假', '违法', '问题', '缺陷', '故障', '风险', '隐患']
        keyword_score = sum(1 for keyword in keywords if keyword in negative_fragment)
        
        # 内容长度也可能反映严重性
        length_factor = min(len(negative_fragment) / 100, 2.0)  # 最多2倍
        
        return base_score + keyword_score * 0.5 + length_factor
    
    def _assess_recent_decline(self, historical_ranks: List[int]) -> float:
        """
        评估最近的排名下降趋势
        
        Args:
            historical_ranks: 历史排名数据
            
        Returns:
            下降趋势强度（正值表示下降）
        """
        if len(historical_ranks) < 2:
            return 0.0
        
        # 计算最近几个数据点的趋势
        recent_points = min(5, len(historical_ranks))
        recent_ranks = historical_ranks[-recent_points:]
        
        # 使用线性回归计算趋势
        X = np.array(range(len(recent_ranks))).reshape(-1, 1)
        y = np.array(recent_ranks)
        
        model = LinearRegression()
        model.fit(X, y)
        
        # 斜率为正表示排名下降（数字变大），负值表示排名上升（数字变小）
        slope = model.coef_[0]
        return max(0, slope)  # 只返回正值（下降趋势）
    
    def predict_weekly_rank_with_risks(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        预测下周排名并识别风险因素
        
        Args:
            historical_data: 历史数据，包含排名和证据链信息
            
        Returns:
            预测结果和风险因素
        """
        # 提取历史排名
        historical_ranks = []
        all_evidence = []
        
        for data_point in historical_data:
            if 'rank' in data_point and data_point['rank'] is not None:
                historical_ranks.append(int(data_point['rank']))
            if 'evidence_chain' in data_point:
                all_evidence.extend(data_point['evidence_chain'])
        
        # 预测下周排名
        rank_prediction = self.predict_ranking_trend(historical_ranks, days=7)
        
        # 识别风险因素
        risks = self.identify_cognitive_risks(all_evidence, historical_ranks)
        
        return {
            'prediction_summary': {
                'predicted_rank_range': {
                    'best_case': min(rank_prediction['predicted_ranks']),
                    'worst_case': max(rank_prediction['predicted_ranks']),
                    'most_likely': rank_prediction['predicted_ranks'][0]  # First day prediction
                },
                'confidence_level': 'high' if len(historical_ranks) > 10 else 'medium' if len(historical_ranks) > 5 else 'low',
                'trend_direction': rank_prediction['trend_direction'],
                'trend_strength': rank_prediction['trend_strength']
            },
            'weekly_forecast': [
                {
                    'day': i + 1,
                    'predicted_rank': rank_prediction['predicted_ranks'][i],
                    'confidence_interval': rank_prediction['confidence_interval'][i]
                }
                for i in range(7)
            ],
            'risk_factors': risks,
            'historical_data_points': len(historical_ranks)
        }


# Example usage and testing
if __name__ == "__main__":
    # Create prediction engine
    engine = PredictionEngine()
    
    # Example: Declining trend data
    declining_ranks = [2, 3, 3, 4, 5, 5, 6, 7, 8, 8, 9, 10]  # Getting worse (higher numbers)
    
    # Predict next 7 days
    result = engine.predict_ranking_trend(declining_ranks, days=7)
    print("Declining trend prediction:")
    print(f"Predicted ranks: {result['predicted_ranks']}")
    print(f"Trend direction: {result['trend_direction']}")
    print(f"Trend strength: {result['trend_strength']:.2f}")
    print()
    
    # Example: Evidence chain with negative factors
    evidence_chain = [
        {
            'negative_fragment': '该品牌智能锁存在安全隐患，容易被破解',
            'associated_url': 'https://example.com/security-report',
            'source_name': '安全评测网站',
            'risk_level': 'High'
        },
        {
            'negative_fragment': '售后服务差，用户投诉较多',
            'associated_url': 'https://example.com/user-feedback',
            'source_name': '用户论坛',
            'risk_level': 'Medium'
        }
    ]
    
    # Identify risks
    risks = engine.identify_cognitive_risks(evidence_chain, declining_ranks)
    print("Identified risks:")
    for risk in risks:
        print(f"- {risk['risk_factor'][:50]}... (Impact: {risk['potential_impact_on_rank']:.2f})")