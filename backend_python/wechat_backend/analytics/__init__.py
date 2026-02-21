"""
分析模块初始化

P1 修复：规范化所有导入路径为绝对路径
"""

# 调试信息（启动时查看）
import sys
import os
# print(f"DEBUG: sys.path is {sys.path}")
# print(f"DEBUG: Current dir content: {os.listdir(os.path.dirname(__file__))}")

# 核心分析组件
from wechat_backend.analytics.rank_analyzer import RankAnalyzer
from wechat_backend.analytics.source_aggregator import SourceAggregator
from wechat_backend.analytics.impact_calculator import ImpactCalculator
from wechat_backend.analytics.report_generator import ReportGenerator
from wechat_backend.analytics.api_monitor import ApiMonitor
from wechat_backend.analytics.asset_intelligence_engine import AssetIntelligenceEngine

# 外部依赖组件（位于 wechat_backend 子目录）
from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor, process_brand_source_intelligence
from wechat_backend.analytics.prediction_engine import PredictionEngine
from wechat_backend.ai_adapters.workflow_manager import WorkflowManager

__all__ = [
    'RankAnalyzer',
    'SourceAggregator',
    'SourceIntelligenceProcessor',
    'process_brand_source_intelligence',
    'ImpactCalculator',
    'ReportGenerator',
    'ApiMonitor',
    'PredictionEngine',
    'WorkflowManager',
    'AssetIntelligenceEngine'
]
