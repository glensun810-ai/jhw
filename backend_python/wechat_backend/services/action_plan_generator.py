#!/usr/bin/env python3
"""
行动计划生成器 - 增强版
基于诊断结果智能生成可执行的行动计划

版本：v2.0
日期：2026-02-21
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from wechat_backend.logging_config import api_logger


class ActionPlanGenerator:
    """
    行动计划生成器
    基于诊断结果智能生成可执行的行动计划
    """
    
    # 行动模板库
    ACTION_TEMPLATES = {
        # 负面信源处理
        'negative_source_response': {
            'category': 'pr',
            'title': '处理{source}负面内容',
            'description': '针对{source}平台的负面内容进行应对',
            'phase': 'short_term',
            'duration_weeks': 2,
            'estimated_hours': 20,
            'priority': 'critical',
            'action_steps': [
                '监测负面内容传播情况',
                '准备官方回应声明',
                '联系平台方沟通处理',
                '跟踪处理结果并复盘'
            ],
            'required_roles': ['公关经理', '内容专员'],
            'success_metrics': ['负面内容删除或下沉', '正面内容占比提升']
        },
        
        # 内容优化
        'content_optimization': {
            'category': 'content',
            'title': '优化{platform}品牌内容',
            'description': '提升品牌在{platform}的内容质量和曝光',
            'phase': 'mid_term',
            'duration_weeks': 4,
            'estimated_hours': 40,
            'priority': 'high',
            'action_steps': [
                '分析平台内容偏好和算法',
                '制定内容优化策略',
                '创建高质量品牌内容',
                '持续监测和优化表现'
            ],
            'required_roles': ['内容经理', 'SEO 专员'],
            'success_metrics': ['内容曝光量提升 30%', '正面提及增加 20%']
        },
        
        # 权威平台建设
        'authority_building': {
            'category': 'authority',
            'title': '建设权威平台品牌形象',
            'description': '在权威平台建立和维护品牌正面形象',
            'phase': 'mid_term',
            'duration_weeks': 8,
            'estimated_hours': 60,
            'priority': 'high',
            'action_steps': [
                '识别关键权威平台（百科、问答等）',
                '完善品牌官方信息',
                '建立专家背书和合作',
                '定期更新和维护内容'
            ],
            'required_roles': ['品牌经理', '公关专员'],
            'success_metrics': ['权威平台评分提升至 80+', '品牌信息准确率 95%+']
        },
        
        # 监测体系
        'monitoring_system': {
            'category': 'monitoring',
            'title': '建立 AI 搜索品牌监测体系',
            'description': '建立常态化的 AI 搜索品牌表现监测机制',
            'phase': 'mid_term',
            'duration_weeks': 4,
            'estimated_hours': 30,
            'priority': 'medium',
            'action_steps': [
                '选择监测工具和平台',
                '设置监测指标和阈值',
                '建立定期报告机制',
                '培训相关人员使用'
            ],
            'required_roles': ['数字营销总监', '数据分析师'],
            'success_metrics': ['监测覆盖率 90%+', '预警响应时间<24 小时']
        },
        
        # GEO 战略
        'geo_strategy': {
            'category': 'strategy',
            'title': '制定 GEO 优化战略',
            'description': '制定系统的生成式引擎优化战略',
            'phase': 'long_term',
            'duration_weeks': 12,
            'estimated_hours': 100,
            'priority': 'medium',
            'action_steps': [
                '调研行业 GEO 最佳实践',
                '制定 GEO 战略框架',
                '分配资源和预算',
                '实施和迭代优化'
            ],
            'required_roles': ['CMO', '战略顾问'],
            'success_metrics': ['GEO 成熟度达到行业领先', '品牌 AI 可见性提升 50%']
        },
        
        # 危机公关
        'crisis_management': {
            'category': 'pr',
            'title': '危机公关应对',
            'description': '针对严重负面事件的危机公关应对',
            'phase': 'short_term',
            'duration_weeks': 4,
            'estimated_hours': 80,
            'priority': 'critical',
            'action_steps': [
                '成立危机应对小组',
                '制定危机应对策略',
                '统一对外沟通口径',
                '持续跟踪和修复声誉'
            ],
            'required_roles': ['公关总监', '法务顾问', '高管'],
            'success_metrics': ['负面声量下降 50%+', '品牌信任度恢复']
        }
    }
    
    def __init__(self):
        self.logger = api_logger
    
    def generate_action_plan(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成行动计划
        
        Args:
            report_data: 完整报告数据
        
        Returns:
            行动计划字典
        """
        brand_name = report_data.get('reportMetadata', {}).get('brandName', '品牌')
        health_data = report_data.get('brandHealth', {})
        negative_sources = report_data.get('negativeSources', {})
        competitive_data = report_data.get('competitiveAnalysis', {})
        roi_data = report_data.get('roiAnalysis', {})
        
        all_actions = []
        
        # 1. 基于负面信源生成紧急行动
        negative_actions = self._generate_negative_source_actions(
            brand_name, 
            negative_sources
        )
        all_actions.extend(negative_actions)
        
        # 2. 基于竞品对比生成竞争行动
        competitive_actions = self._generate_competitive_actions(
            brand_name,
            health_data,
            competitive_data
        )
        all_actions.extend(competitive_actions)
        
        # 3. 基于 ROI 生成优化行动
        roi_actions = self._generate_roi_actions(
            brand_name,
            roi_data
        )
        all_actions.extend(roi_actions)
        
        # 4. 基于健康度生成常规行动
        health_actions = self._generate_health_actions(
            brand_name,
            health_data
        )
        all_actions.extend(health_actions)
        
        # 5. 按阶段分类
        short_term = [a for a in all_actions if a.get('phase') == 'short_term']
        mid_term = [a for a in all_actions if a.get('phase') == 'mid_term']
        long_term = [a for a in all_actions if a.get('phase') == 'long_term']
        
        # 6. 计算资源需求
        total_hours = sum(a.get('estimated_hours', 0) for a in all_actions)
        total_budget = self._calculate_total_budget(all_actions)
        
        # 7. 预期效果评估
        expected_improvement = self._estimate_improvement(health_data, all_actions)
        
        return {
            'short_term': short_term,
            'mid_term': mid_term,
            'long_term': long_term,
            'all_actions': all_actions,
            'summary': {
                'total_actions': len(all_actions),
                'short_term_count': len(short_term),
                'mid_term_count': len(mid_term),
                'long_term_count': len(long_term),
                'total_estimated_hours': total_hours,
                'total_estimated_budget': total_budget,
                'expected_score_improvement': expected_improvement
            },
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_negative_source_actions(self, brand_name: str, 
                                          negative_sources: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于负面信源生成行动"""
        actions = []
        sources = negative_sources.get('sources', [])
        summary = negative_sources.get('summary', {})
        
        # 高危负面信源 - 立即处理
        critical_count = summary.get('critical_count', 0) + summary.get('high_count', 0)
        
        if critical_count > 0:
            for source in sources[:3]:  # 最多处理前 3 个
                if source.get('severity') in ['critical', 'high']:
                    template = self.ACTION_TEMPLATES['negative_source_response'].copy()
                    action = self._instantiate_template(
                        template,
                        {'source': source.get('source_name', '某平台')},
                        priority='critical' if source.get('severity') == 'critical' else 'high'
                    )
                    action['estimated_budget'] = action['estimated_hours'] * 500  # 每小时 500 元
                    actions.append(action)
        
        return actions
    
    def _generate_competitive_actions(self, brand_name: str, health_data: Dict[str, Any],
                                      competitive_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于竞品对比生成行动"""
        actions = []
        comparison = competitive_data.get('comparison_summary', {})
        competitors = competitive_data.get('competitors', [])
        
        my_rank = comparison.get('my_rank', 1)
        gap_to_leader = comparison.get('gap_to_leader', 0)
        
        # 如果排名靠后或差距大，生成竞争行动
        if my_rank > 2 or gap_to_leader > 10:
            # 内容优化行动
            template = self.ACTION_TEMPLATES['content_optimization'].copy()
            action = self._instantiate_template(
                template,
                {'platform': '主流 AI 平台'},
                priority='high'
            )
            action['estimated_budget'] = action['estimated_hours'] * 300
            actions.append(action)
            
            # 权威平台建设
            if gap_to_leader > 15:
                template = self.ACTION_TEMPLATES['authority_building'].copy()
                action = self._instantiate_template(template, {}, priority='high')
                action['estimated_budget'] = action['estimated_hours'] * 400
                actions.append(action)
        
        return actions
    
    def _generate_roi_actions(self, brand_name: str, roi_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于 ROI 指标生成行动"""
        actions = []
        
        overall_roi = roi_data.get('overall_roi', 0)
        industry_comparison = roi_data.get('industry_comparison', {})
        
        # 如果 ROI 低于行业平均，生成优化行动
        if industry_comparison.get('exposure_roi_vs_industry', 0) < 0:
            template = self.ACTION_TEMPLATES['monitoring_system'].copy()
            action = self._instantiate_template(template, {}, priority='medium')
            action['estimated_budget'] = action['estimated_hours'] * 200
            actions.append(action)
        
        return actions
    
    def _generate_health_actions(self, brand_name: str, 
                                 health_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于健康度生成常规行动"""
        actions = []
        
        overall_score = health_data.get('overall_score', 0)
        dimension_scores = health_data.get('dimension_scores', {})
        
        # 如果总体分数较低，生成战略行动
        if overall_score < 70:
            template = self.ACTION_TEMPLATES['geo_strategy'].copy()
            action = self._instantiate_template(template, {}, priority='medium')
            action['estimated_budget'] = action['estimated_hours'] * 600
            actions.append(action)
        
        # 如果某个维度特别弱，生成专项提升行动
        weak_dimensions = [
            (k, v) for k, v in dimension_scores.items() 
            if v < 60
        ]
        
        for dim_key, dim_score in weak_dimensions:
            dim_name = {
                'authority': '权威性',
                'visibility': '可见性',
                'purity': '纯净度',
                'consistency': '一致性'
            }.get(dim_key, dim_key)
            
            action = {
                'title': f'提升{dim_name}维度',
                'description': f'针对{dim_name}维度（当前{dim_score}分）进行专项提升',
                'category': 'optimization',
                'phase': 'mid_term',
                'start_week': 5,
                'duration_weeks': 6,
                'estimated_hours': 50,
                'priority': 'medium',
                'priority_score': 65,
                'effort_level': 'medium',
                'impact_level': 'high',
                'expected_outcome': f'{dim_name}评分提升至 75+',
                'success_metrics': [f'{dim_name}评分 >= 75'],
                'action_steps': [
                    f'分析{dim_name}维度影响因素',
                    '制定专项提升方案',
                    '实施优化措施',
                    '监测效果并调整'
                ],
                'required_roles': ['品牌经理', '专员'],
                'estimated_budget': 25000
            }
            actions.append(action)
        
        return actions
    
    def _instantiate_template(self, template: Dict[str, Any], 
                              replacements: Dict[str, str],
                              priority: str = None) -> Dict[str, Any]:
        """实例化行动模板"""
        import re
        
        action = {}
        
        # 复制基础字段
        for key, value in template.items():
            if isinstance(value, str):
                # 字符串替换
                action[key] = value
                for k, v in replacements.items():
                    action[key] = action[key].replace(f'{{{k}}}', v)
            elif isinstance(value, list):
                action[key] = value.copy()
            else:
                action[key] = value
        
        # 覆盖优先级
        if priority:
            action['priority'] = priority
        
        # 计算优先级分数
        action['priority_score'] = self._calculate_priority_score(
            action.get('priority', 'medium'),
            action.get('impact_level', 'medium'),
            action.get('effort_level', 'medium')
        )
        
        return action
    
    def _calculate_priority_score(self, priority: str, impact: str, effort: str) -> float:
        """计算优先级分数"""
        priority_weights = {
            'critical': 40,
            'high': 30,
            'medium': 20,
            'low': 10
        }
        
        impact_weights = {
            'high': 30,
            'medium': 20,
            'low': 10
        }
        
        effort_penalty = {
            'low': 30,
            'medium': 20,
            'high': 10
        }
        
        score = (
            priority_weights.get(priority, 20) +
            impact_weights.get(impact, 20) +
            effort_penalty.get(effort, 20)
        )
        
        return min(100, score)
    
    def _calculate_total_budget(self, actions: List[Dict[str, Any]]) -> float:
        """计算总预算"""
        return sum(a.get('estimated_budget', 0) for a in actions)
    
    def _estimate_improvement(self, health_data: Dict[str, Any], 
                              actions: List[Dict[str, Any]]) -> float:
        """评估预期效果"""
        current_score = health_data.get('overall_score', 0)
        
        # 基于行动数量和优先级估算提升
        critical_actions = sum(1 for a in actions if a.get('priority') == 'critical')
        high_actions = sum(1 for a in actions if a.get('priority') == 'high')
        medium_actions = sum(1 for a in actions if a.get('priority') == 'medium')
        
        # 每个行动的预期贡献
        improvement = (
            critical_actions * 5 +
            high_actions * 3 +
            medium_actions * 1.5
        )
        
        # 上限为 20 分或当前分数的 20%
        max_improvement = min(20, current_score * 0.2)
        
        return min(improvement, max_improvement)


# 全局生成器实例
_action_plan_generator = None


def get_action_plan_generator() -> ActionPlanGenerator:
    """获取行动计划生成器实例"""
    global _action_plan_generator
    if _action_plan_generator is None:
        _action_plan_generator = ActionPlanGenerator()
    return _action_plan_generator
