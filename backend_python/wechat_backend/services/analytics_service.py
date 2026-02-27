"""
分析服务

功能：
- 数据分析
- 趋势分析
- 用户行为分析
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger


class AnalyticsService:
    """
    分析服务类
    
    功能：
    - 数据分析
    - 趋势分析
    - 用户行为分析
    """
    
    @staticmethod
    def analyze_trends(
        historical_data: List[Dict[str, Any]],
        days: int = 30
    ) -> Dict[str, Any]:
        """
        分析趋势
        
        参数：
        - historical_data: 历史数据
        - days: 分析天数
        
        返回：
        - trends: 趋势分析结果
        """
        try:
            if not historical_data:
                return {
                    'trend': 'stable',
                    'change_percent': 0,
                    'message': '暂无历史数据'
                }
            
            # 计算平均分变化
            recent_scores = [d.get('score', 0) for d in historical_data[-7:]]
            older_scores = [d.get('score', 0) for d in historical_data[-30:-7]]
            
            if not recent_scores or not older_scores:
                return {
                    'trend': 'stable',
                    'change_percent': 0,
                    'message': '数据不足'
                }
            
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            
            if older_avg == 0:
                change_percent = 0
            else:
                change_percent = ((recent_avg - older_avg) / older_avg) * 100
            
            if change_percent > 5:
                trend = 'improving'
                message = '表现正在提升'
            elif change_percent < -5:
                trend = 'declining'
                message = '表现有所下降'
            else:
                trend = 'stable'
                message = '表现稳定'
            
            return {
                'trend': trend,
                'change_percent': round(change_percent, 2),
                'message': message,
                'recent_avg': round(recent_avg, 2),
                'older_avg': round(older_avg, 2)
            }
            
        except Exception as e:
            api_logger.error(f'[AnalyticsService] 趋势分析失败：{e}')
            return {
                'error': str(e),
                'trend': 'unknown'
            }
    
    @staticmethod
    def analyze_user_behavior(
        user_actions: List[Dict[str, Any]],
        days: int = 7
    ) -> Dict[str, Any]:
        """
        分析用户行为
        
        参数：
        - user_actions: 用户行为列表
        - days: 分析天数
        
        返回：
        - behavior: 行为分析结果
        """
        try:
            if not user_actions:
                return {
                    'total_actions': 0,
                    'avg_actions_per_day': 0,
                    'most_active_time': 'unknown'
                }
            
            # 统计行为
            total_actions = len(user_actions)
            avg_actions_per_day = total_actions / days if days > 0 else 0
            
            # 统计活跃时段
            hour_counts = {}
            for action in user_actions:
                timestamp = action.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        hour = dt.hour
                        hour_counts[hour] = hour_counts.get(hour, 0) + 1
                    except Exception as e:
                        api_logger.error(f"[AnalyticsService] Error parsing timestamp for hour distribution: {e}", exc_info=True)
                        # 时间戳解析失败，跳过该动作
            
            most_active_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0
            
            return {
                'total_actions': total_actions,
                'avg_actions_per_day': round(avg_actions_per_day, 2),
                'most_active_time': f'{most_active_hour}:00',
                'hour_distribution': hour_counts
            }
            
        except Exception as e:
            api_logger.error(f'[AnalyticsService] 用户行为分析失败：{e}')
            return {
                'error': str(e)
            }
    
    @staticmethod
    def generate_summary(
        report_data: Dict[str, Any],
        trends: Optional[Dict[str, Any]] = None,
        behavior: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成分析摘要
        
        参数：
        - report_data: 报告数据
        - trends: 趋势数据
        - behavior: 行为数据
        
        返回：
        - summary: 分析摘要
        """
        summary = {
            'brand_name': report_data.get('brand_name', '品牌'),
            'overall_score': report_data.get('overall_score', 0),
            'generated_at': datetime.now().isoformat()
        }
        
        if trends:
            summary['trends'] = trends
        
        if behavior:
            summary['behavior'] = behavior
        
        return summary


# 导出服务实例
analytics_service = AnalyticsService()
