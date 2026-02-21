"""AI平台推荐系统"""
from typing import Dict, List, Optional
from wechat_backend.analytics.api_monitor import ApiMonitor


class PlatformRecommendation:
    """平台推荐系统"""
    
    def __init__(self, monitor: ApiMonitor):
        self.monitor = monitor
    
    def recommend_platforms(self, user_preferences: Dict, 
                           task_requirements: Dict) -> List[str]:
        """根据用户偏好和任务需求推荐平台"""
        recommendations = []
        
        # 获取所有可用平台
        available_platforms = [
            platform for platform, config in self.monitor.platform_status.items()
            if self.monitor.check_api_availability(platform)
        ]
        
        # 根据任务类型推荐
        task_type = task_requirements.get('type', 'general')
        priority_factors = {
            'creative': ['chatgpt', 'claude', 'qwen'],
            'technical': ['chatgpt', 'gemini', 'deepseek'],
            'chinese': ['qwen', 'wenxin', 'doubao'],
            'general': ['chatgpt', 'qwen', 'claude']
        }
        
        preferred_order = priority_factors.get(task_type, priority_factors['general'])
        
        # 按优先级排序可用平台
        for platform in preferred_order:
            if platform in available_platforms:
                recommendations.append(platform)
        
        # 添加其他可用平台
        for platform in available_platforms:
            if platform not in recommendations:
                recommendations.append(platform)
        
        return recommendations
    
    def get_cost_efficient_platforms(self, budget_limit: float = None) -> List[str]:
        """获取成本效益高的平台"""
        available_platforms = [
            platform for platform, config in self.monitor.platform_status.items()
            if self.monitor.check_api_availability(platform)
        ]
        
        # 按成本排序（假设成本信息在配置中）
        cost_sorted = sorted(
            available_platforms,
            key=lambda p: getattr(self.monitor.platform_status[p], 'cost_per_token', float('inf'))
        )
        
        if budget_limit:
            affordable_platforms = []
            for platform in cost_sorted:
                cost = getattr(self.monitor.platform_status[platform], 'cost_per_token', float('inf'))
                if cost <= budget_limit:
                    affordable_platforms.append(platform)
            return affordable_platforms
        
        return cost_sorted