"""
趋势预测服务 - 基于历史数据进行品牌表现预测
"""
from typing import List, Dict, Any, Optional
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
import logging
from typing import List, Dict, Any, Tuple
warnings.filterwarnings('ignore')


class PredictionService:
    """
    趋势预测服务 - 利用历史数据实现趋势预测和风险识别
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.logger = logging.getLogger(__name__)

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
            # 【冷启动策略】如果数据不足，生成模拟历史数据
            simulated_data = self._generate_simulated_history(data[-1] if data else 50.0)
            return self.exponential_smoothing_forecast(simulated_data, alpha, forecast_periods)

        # 初始化
        smoothed_value = data[0]
        
        # 计算历史数据的平滑值
        for value in data[1:]:
            smoothed_value = alpha * value + (1 - alpha) * smoothed_value

        # 预测未来值（使用最后一个平滑值作为预测）
        forecasts = []
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
            # 【冷启动策略】如果数据不足，生成模拟历史数据
            simulated_data = self._generate_simulated_history(data[-1] if data else 50.0)
            return self.linear_regression_forecast(simulated_data, forecast_periods)

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

    def predict_scores_trend(self, historical_scores: List[float], periods: int = 7) -> Dict[str, Any]:
        """
        预测品牌评分趋势

        Args:
            historical_scores: 历史评分数据
            periods: 预测期数

        Returns:
            预测结果字典
        """
        if not historical_scores:
            # 【冷启动策略】如果没有历史数据，生成模拟数据
            simulated_scores = self._generate_simulated_history(75.0)  # 假设初始分数为75
            return self.predict_scores_trend(simulated_scores, periods)

        # 使用指数平滑预测
        exp_smooth_forecasts = self.exponential_smoothing_forecast(historical_scores, alpha=0.3, forecast_periods=periods)
        
        # 使用线性回归预测
        lin_reg_forecasts, slope = self.linear_regression_forecast(historical_scores, periods)

        # 综合两种方法的预测结果
        combined_forecasts = [(exp_smooth_forecasts[i] + lin_reg_forecasts[i]) / 2 for i in range(periods)]

        # 计算置信区间
        if len(historical_scores) > 2:
            residuals = [historical_scores[i] - (slope * i + historical_scores[0]) for i in range(len(historical_scores))]
            std_error = np.std(residuals) if residuals else 5.0  # 默认误差为5
            confidence_intervals = [(max(0, forecast - 1.96 * std_error), min(100, forecast + 1.96 * std_error))
                                   for forecast in combined_forecasts]
        else:
            # 如果历史数据不足，使用较宽的置信区间
            confidence_intervals = [(max(0, forecast - 15), min(100, forecast + 15))
                                   for forecast in combined_forecasts]

        # 判断趋势方向
        if slope < -0.1:
            trend_direction = 'improving'
        elif slope > 0.1:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'

        return {
            'forecast_points': combined_forecasts,
            'confidence_intervals': confidence_intervals,
            'trend_direction': trend_direction,
            'trend_strength': abs(slope),
            'method_weights': {'exponential_smoothing': 0.5, 'linear_regression': 0.5},
            'historical_data_points': len(historical_scores)
        }

    def _generate_simulated_history(self, current_value: float, num_points: int = 10) -> List[float]:
        """
        【冷启动策略】生成模拟历史数据
        
        Args:
            current_value: 当前值
            num_points: 生成的数据点数量
            
        Returns:
            模拟的历史数据列表
        """
        # TODO: Replace with real history data in production
        self.logger.info(f"[PredictionService] Generating simulated history for cold start with current value: {current_value}")
        
        # 生成围绕当前值的正态分布波动数据
        # 让数据有一些趋势变化，而不是完全随机
        simulated_data = []
        base_value = current_value
        volatility = base_value * 0.1  # 波动率为当前值的10%
        
        # 生成一些随机波动，但保持一定的趋势
        trend_factor = np.random.uniform(-0.5, 0.5)  # 随机趋势因子
        
        for i in range(num_points):
            # 添加趋势和随机波动
            value = base_value + (i * trend_factor) + np.random.normal(0, volatility)
            # 确保值在合理范围内（例如0-100）
            value = max(0, min(100, value))
            simulated_data.append(value)
        
        return simulated_data

    def predict_multi_dimensional_trends(self, historical_data: Dict[str, List[float]], periods: int = 7) -> Dict[str, Any]:
        """
        预测多维度趋势（如权威度、可见度、情感等）

        Args:
            historical_data: 包含多个维度的历史数据字典
            periods: 预测期数

        Returns:
            多维度预测结果
        """
        predictions = {}
        
        for dimension, scores in historical_data.items():
            predictions[dimension] = self.predict_scores_trend(scores, periods)
        
        return {
            'dimensions': predictions,
            'overall_trend': self._calculate_overall_trend(predictions),
            'forecast_horizon': periods
        }

    def _calculate_overall_trend(self, predictions: Dict[str, Any]) -> str:
        """
        计算整体趋势方向

        Args:
            predictions: 各维度的预测结果

        Returns:
            整体趋势方向
        """
        trend_counts = {'improving': 0, 'declining': 0, 'stable': 0}
        
        for dim_name, pred_data in predictions.items():
            trend_dir = pred_data.get('trend_direction', 'stable')
            trend_counts[trend_dir] += 1
        
        # 返回多数趋势
        dominant_trend = max(trend_counts, key=trend_counts.get)
        return dominant_trend

    def generate_prediction_report(self, historical_data: Dict[str, List[float]], brand_name: str) -> Dict[str, Any]:
        """
        生成完整的预测报告

        Args:
            historical_data: 历史数据
            brand_name: 品牌名称

        Returns:
            预测报告
        """
        # 执行多维度预测
        multi_dim_predictions = self.predict_multi_dimensional_trends(historical_data, periods=7)
        
        # 提取关键指标
        forecast_points = {}
        for dim, pred in multi_dim_predictions['dimensions'].items():
            forecast_points[dim] = pred['forecast_points']
        
        # 计算风险评估
        risk_assessment = self._assess_prediction_risks(multi_dim_predictions)
        
        return {
            'brand_name': brand_name,
            'prediction_summary': {
                'overall_trend': multi_dim_predictions['overall_trend'],
                'forecast_horizon_days': multi_dim_predictions['forecast_horizon'],
                'confidence_level': self._calculate_confidence_level(historical_data)
            },
            'forecast_details': forecast_points,
            'risk_assessment': risk_assessment,
            'historical_data_summary': {
                'data_points_per_dimension': {dim: len(scores) for dim, scores in historical_data.items()},
                'latest_values': {dim: scores[-1] if scores else 0 for dim, scores in historical_data.items()}
            }
        }

    def _calculate_confidence_level(self, historical_data: Dict[str, List[float]]) -> str:
        """
        计算预测置信度等级

        Args:
            historical_data: 历史数据

        Returns:
            置信度等级 ('high', 'medium', 'low')
        """
        total_points = sum(len(scores) for scores in historical_data.values())
        num_dimensions = len(historical_data)
        
        if total_points / num_dimensions >= 20:
            return 'high'
        elif total_points / num_dimensions >= 10:
            return 'medium'
        else:
            return 'low'

    def _assess_prediction_risks(self, predictions: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估预测风险

        Args:
            predictions: 预测结果

        Returns:
            风险评估
        """
        # 计算各维度的波动性
        volatilities = {}
        for dim, pred_data in predictions['dimensions'].items():
            forecast_values = pred_data['forecast_points']
            if len(forecast_values) > 1:
                volatility = np.std(np.diff(forecast_values))  # 计算预测值的变化率标准差
                volatilities[dim] = volatility
            else:
                volatilities[dim] = 0.0

        # 识别高风险维度
        high_risk_dimensions = [dim for dim, vol in volatilities.items() if vol > 5.0]  # 波动阈值可调整

        return {
            'volatility_by_dimension': volatilities,
            'high_risk_dimensions': high_risk_dimensions,
            'overall_risk_level': 'high' if high_risk_dimensions else 'low',
            'recommendations': self._generate_risk_recommendations(high_risk_dimensions)
        }

    def _generate_risk_recommendations(self, high_risk_dimensions: List[str]) -> List[str]:
        """
        生成风险应对建议

        Args:
            high_risk_dimensions: 高风险维度列表

        Returns:
            建议列表
        """
        recommendations = []
        
        if not high_risk_dimensions:
            recommendations.append("预测结果较为稳定，建议持续监控关键指标")
        else:
            recommendations.append(f"检测到以下维度存在较高波动风险: {', '.join(high_risk_dimensions)}")
            recommendations.append("建议加强对上述维度的监测和优化")
            recommendations.append("考虑制定应急预案以应对可能的下滑趋势")
        
        return recommendations


# 测试函数
def test_prediction_service():
    """
    测试预测服务
    """
    service = PredictionService()
    
    # 测试下降趋势
    print("测试下降趋势预测...")
    declining_scores = [85, 82, 80, 78, 75, 73, 70, 68, 65, 63]
    result = service.predict_scores_trend(declining_scores, periods=7)
    print(f"预测结果: {result['forecast_points']}")
    print(f"趋势方向: {result['trend_direction']}")
    print(f"趋势强度: {result['trend_strength']:.2f}")
    print()
    
    # 测试冷启动策略
    print("测试冷启动策略...")
    single_score = [75.0]  # 只有一个数据点
    cold_start_result = service.predict_scores_trend(single_score, periods=5)
    print(f"冷启动预测结果: {cold_start_result['forecast_points']}")
    print(f"历史数据点数: {cold_start_result['historical_data_points']}")
    print()
    
    # 测试多维度预测
    print("测试多维度预测...")
    multi_dim_data = {
        'authority_score': [80, 78, 79, 77, 76, 75, 74],
        'visibility_score': [70, 72, 71, 73, 72, 74, 73],
        'sentiment_score': [75, 76, 74, 75, 77, 76, 78]
    }
    multi_result = service.predict_multi_dimensional_trends(multi_dim_data, periods=5)
    print(f"整体趋势: {multi_result['overall_trend']}")
    for dim, pred in multi_result['dimensions'].items():
        print(f"{dim} 预测: {pred['forecast_points'][:3]}...")  # 只显示前3个预测值
    print()
    
    # 生成完整报告
    print("生成完整预测报告...")
    report = service.generate_prediction_report(multi_dim_data, "测试品牌")
    print(f"品牌: {report['brand_name']}")
    print(f"整体趋势: {report['prediction_summary']['overall_trend']}")
    print(f"置信等级: {report['prediction_summary']['confidence_level']}")
    print(f"风险等级: {report['risk_assessment']['overall_risk_level']}")


if __name__ == "__main__":
    test_prediction_service()