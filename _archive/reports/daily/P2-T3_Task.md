系统重构 阶段二 - P2-T3 频段分布统计算法
任务背景
当前阶段：阶段二（核心业务功能实现）- Week 3-5
阶段目标：交付真实的统计分析报告
已完成任务：

阶段一所有任务已完成并合并（P1-T1 到 P1-T10）

P2-T1 AI平台标准化数据交互层（已合并）- 提供统一的AI响应格式

P2-T2 数据清洗管道实现（已合并）- 提供结构化的清洗后数据

当前任务：P2-T3 - 频段分布统计算法

参考文档
重构基线：第 1.2 节 - 报告内容标准、第 2.1.2 节 - 数据清洗与统计分析

开发规范：第 2.3 节 - 函数规范、第 2.4 节 - 异常处理规范、第 2.5 节 - 日志规范

实施路线图：第 2.2.2 节 - P2-T3 详细设计

P2-T2输出：CleanedData 数据模型（包含实体信息、GEO数据等）

核心要求（通用部分）
1. 严格遵守重构基线
业务导向：所有代码必须服务于"让用户获取真实品牌诊断报告"这一核心目标

数据真实性：统计必须基于真实API响应数据，不得伪造或模拟

统计准确性：所有计算结果必须精确，误差为0

可解释性：统计方法必须清晰 documented，便于理解和验证

2. 严格遵守开发规范
目录结构：所有 v2 代码必须放在 wechat_backend/v2/ 目录下

命名规范：类名 PascalCase，函数名 snake_case，常量 UPPER_SNAKE_CASE

类型注解：所有函数必须有完整的类型注解

函数长度：每个函数不超过 50 行，复杂逻辑必须拆分

圈复杂度：每个函数圈复杂度不超过 10

异常处理：必须使用自定义异常类，禁止空的 except 块

日志规范：必须使用结构化日志，记录统计过程中的关键步骤

特性开关：所有新功能必须通过特性开关控制，默认关闭

3. 与前期任务的集成
依赖 P2-T2：必须使用 CleanedData 作为输入数据源

依赖 P1-T6：统计结果需通过原始数据持久化机制保存

依赖 P2-T1：处理不同AI平台的响应时，数据已标准化

当前任务：P2-T3 - 频段分布统计算法
任务描述
实现频段分布统计算法，分析品牌在不同AI平台、不同问题下的露出情况。这是诊断报告中最核心的统计指标，直接反映品牌在AI时代的"存在感"。

核心职责：

品牌露出频次统计：统计主品牌在各个AI平台响应中被提及的次数

露出占比分析：计算主品牌在总响应中的占比（整体及分平台）

竞品对比分析：对比主品牌与竞品的露出情况

多维度统计：支持按AI平台、按问题、按时间维度统计

趋势分析基础：为后续趋势对比准备历史数据

可视化数据准备：生成适合前端图表展示的数据格式

业务价值
频段分布统计的价值在于：

量化存在感：将"品牌在AI中的提及"转化为可量化的指标

竞争分析：直观对比与竞品的差距

优化依据：为GEO优化提供数据支撑

趋势追踪：长期监测品牌露出变化

ROI衡量：评估品牌营销活动对AI认知的影响

具体需求
文件路径
text
wechat_backend/v2/analytics/
├── __init__.py
├── frequency/
│   ├── __init__.py
│   ├── calculator.py                    # 频段分布计算主类
│   ├── models.py                         # 频段分布数据模型
│   ├── aggregators/
│   │   ├── __init__.py
│   │   ├── base.py                        # 聚合器基类
│   │   ├── platform_aggregator.py         # 按平台聚合
│   │   ├── question_aggregator.py         # 按问题聚合
│   │   ├── time_aggregator.py             # 按时间聚合
│   │   └── competitor_aggregator.py       # 竞品对比聚合
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── chart_formatter.py             # 图表数据格式化
│   │   └── report_formatter.py            # 报告数据格式化
│   └── errors.py                          # 统计相关异常

tests/unit/analytics/frequency/
├── test_calculator.py
├── test_platform_aggregator.py
├── test_question_aggregator.py
├── test_competitor_aggregator.py
└── test_formatters.py

tests/integration/
└── test_frequency_analytics_integration.py
第一部分：数据模型定义
python
# wechat_backend/v2/analytics/frequency/models.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class BrandExposure:
    """品牌露出统计"""
    brand_name: str                           # 品牌名称
    total_mentions: int = 0                    # 总提及次数
    platforms: Dict[str, int] = field(default_factory=dict)  # 各平台提及次数
    questions: Dict[str, int] = field(default_factory=dict)  # 各问题提及次数
    first_mention: Optional[datetime] = None   # 首次提及时间
    last_mention: Optional[datetime] = None    # 最后提及时间
    
    @property
    def platform_count(self) -> int:
        """涉及的平台数量"""
        return len(self.platforms)
    
    @property
    def question_count(self) -> int:
        """涉及的问题数量"""
        return len(self.questions)


@dataclass
class ExposureDistribution:
    """
    露出分布统计
    
    这是频段分布分析的核心数据结构
    """
    # 整体统计
    total_responses: int = 0                    # 总响应数
    total_mentions: int = 0                      # 总提及次数
    brands_involved: int = 0                      # 涉及品牌数
    
    # 品牌分布
    brand_distribution: Dict[str, float] = field(default_factory=dict)  # 品牌占比（百分比）
    brand_counts: Dict[str, int] = field(default_factory=dict)          # 品牌计数
    
    # 平台分布
    platform_distribution: Dict[str, Dict[str, float]] = field(default_factory=dict)  # 各平台内品牌占比
    
    # 问题分布
    question_distribution: Dict[str, Dict[str, float]] = field(default_factory=dict)  # 各问题内品牌占比
    
    # 排名信息
    ranking: List[Dict[str, Any]] = field(default_factory=list)  # 品牌排名列表
    
    # 元数据
    computed_at: datetime = field(default_factory=datetime.now)
    data_source: str = "cleaned_data"            # 数据来源
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于报告）"""
        return {
            'summary': {
                'total_responses': self.total_responses,
                'total_mentions': self.total_mentions,
                'brands_involved': self.brands_involved,
            },
            'brand_distribution': self.brand_distribution,
            'brand_counts': self.brand_counts,
            'platform_distribution': self.platform_distribution,
            'question_distribution': self.question_distribution,
            'ranking': self.ranking,
            'computed_at': self.computed_at.isoformat(),
        }
    
    def to_chart_data(self) -> Dict[str, Any]:
        """转换为图表数据格式（供前端使用）"""
        # 饼图数据
        pie_data = [
            {'name': brand, 'value': count}
            for brand, count in self.brand_counts.items()
        ]
        
        # 柱状图数据（按平台）
        bar_data = []
        for platform, brands in self.platform_distribution.items():
            for brand, percentage in brands.items():
                bar_data.append({
                    'platform': platform,
                    'brand': brand,
                    'percentage': percentage
                })
        
        return {
            'pie_chart': pie_data,
            'bar_chart': bar_data,
            'ranking': self.ranking[:10],  # 只返回前10名
        }


@dataclass
class CompetitiveAnalysis:
    """竞品对比分析"""
    
    main_brand: str                              # 主品牌
    competitors: List[str] = field(default_factory=list)  # 竞品列表
    
    # 对比数据
    exposure_comparison: Dict[str, int] = field(default_factory=dict)  # 露出次数对比
    share_comparison: Dict[str, float] = field(default_factory=dict)   # 占比对比
    
    # 平台优势
    platform_advantages: Dict[str, str] = field(default_factory=dict)  # 各平台的优势品牌
    
    # 差距分析
    gap_analysis: Dict[str, Any] = field(default_factory=dict)         # 差距分析
    
    # 时间趋势（如果有历史数据）
    trend_comparison: Optional[Dict[str, List]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'main_brand': self.main_brand,
            'competitors': self.competitors,
            'exposure_comparison': self.exposure_comparison,
            'share_comparison': self.share_comparison,
            'platform_advantages': self.platform_advantages,
            'gap_analysis': self.gap_analysis,
            'trend_comparison': self.trend_comparison,
        }
第二部分：异常定义
python
# wechat_backend/v2/analytics/frequency/errors.py

class FrequencyAnalysisError(Exception):
    """频段分析基础异常"""
    
    def __init__(self, message: str, execution_id: str = None, details: Dict = None):
        self.message = message
        self.execution_id = execution_id
        self.details = details or {}
        super().__init__(f"[{execution_id or 'unknown'}] {message}")


class InsufficientDataError(FrequencyAnalysisError):
    """数据不足异常"""
    pass


class InvalidBrandError(FrequencyAnalysisError):
    """无效品牌异常"""
    pass


class AggregationError(FrequencyAnalysisError):
    """聚合计算异常"""
    pass


class DataValidationError(FrequencyAnalysisError):
    """数据验证异常"""
    pass


class FormattingError(FrequencyAnalysisError):
    """格式化异常"""
    pass
第三部分：聚合器基类
python
# wechat_backend/v2/analytics/frequency/aggregators/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from collections import defaultdict

from wechat_backend.v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend.v2.analytics.frequency.models import ExposureDistribution
from wechat_backend.v2.analytics.frequency.errors import AggregationError


class BaseAggregator(ABC):
    """
    聚合器基类
    
    负责按不同维度聚合品牌露出数据。
    所有具体的聚合器必须继承此类。
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        
        # 默认配置
        self.config.setdefault('include_partial', True)      # 是否包含部分数据
        self.config.setdefault('min_confidence', 0.5)        # 最低置信度
        self.config.setdefault('deduplicate', True)          # 是否去重
    
    @abstractmethod
    def aggregate(self, data: List[CleanedData]) -> Dict[str, Any]:
        """
        执行聚合计算
        
        Args:
            data: 清洗后的数据列表
            
        Returns:
            聚合结果字典
        """
        pass
    
    def validate_data(self, data: List[CleanedData]) -> bool:
        """
        验证输入数据
        
        子类可重写此方法添加特定验证逻辑
        """
        if not data:
            return False
        return True
    
    def filter_by_confidence(self, data: List[CleanedData]) -> List[CleanedData]:
        """根据置信度过滤数据"""
        if not self.config['include_partial']:
            return [d for d in data if d.quality and d.quality.overall_score >= self.config['min_confidence']]
        return data
    
    def extract_entities(self, cleaned_data: CleanedData) -> List[str]:
        """从清洗数据中提取实体名称"""
        return [e.entity_name for e in cleaned_data.entities]
    
    def log_aggregation_start(self, data_size: int):
        """记录聚合开始"""
        logger.info(
            "aggregation_started",
            extra={
                'aggregator': self.name,
                'data_size': data_size,
                'config': self.config
            }
        )
    
    def log_aggregation_complete(self, result_size: int, duration_ms: float):
        """记录聚合完成"""
        logger.info(
            "aggregation_completed",
            extra={
                'aggregator': self.name,
                'result_size': result_size,
                'duration_ms': duration_ms
            }
        )
    
    def log_aggregation_error(self, error: Exception):
        """记录聚合错误"""
        logger.error(
            "aggregation_failed",
            extra={
                'aggregator': self.name,
                'error': str(error),
                'error_type': type(error).__name__
            }
        )
第四部分：按平台聚合器
python
# wechat_backend/v2/analytics/frequency/aggregators/platform_aggregator.py

from collections import defaultdict
from typing import List, Dict, Any
import time

from wechat_backend/v2.analytics.frequency.aggregators.base import BaseAggregator
from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.analytics.frequency.errors import AggregationError


class PlatformAggregator(BaseAggregator):
    """
    按平台聚合器
    
    统计各AI平台中品牌的露出情况，包括：
    1. 各平台总响应数
    2. 各平台内品牌提及次数
    3. 各平台内品牌占比
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('platform_aggregator', config)
        
        self.config.setdefault('include_platforms', [])  # 指定平台，为空则包含所有
    
    def aggregate(self, data: List[CleanedData]) -> Dict[str, Any]:
        """
        按平台聚合数据
        
        Returns:
            {
                'platforms': ['deepseek', 'doubao', ...],
                'total_by_platform': {'deepseek': 100, ...},
                'mentions_by_platform': {
                    'deepseek': {'品牌A': 10, '品牌B': 5, ...}
                },
                'percentage_by_platform': {
                    'deepseek': {'品牌A': 10.0, '品牌B': 5.0, ...}
                }
            }
        """
        start_time = time.time()
        self.log_aggregation_start(len(data))
        
        try:
            if not self.validate_data(data):
                return self._empty_result()
            
            # 按平台分组
            platform_data = defaultdict(list)
            for item in data:
                platform = item.model  # model字段标识AI平台
                
                # 如果指定了平台列表，只包含指定平台
                if self.config['include_platforms'] and platform not in self.config['include_platforms']:
                    continue
                
                platform_data[platform].append(item)
            
            # 统计各平台
            total_by_platform = {}
            mentions_by_platform = {}
            percentage_by_platform = {}
            
            for platform, items in platform_data.items():
                # 总响应数
                total_by_platform[platform] = len(items)
                
                # 品牌提及次数
                mentions = defaultdict(int)
                for item in items:
                    entities = self.extract_entities(item)
                    for entity in entities:
                        mentions[entity] += 1
                
                mentions_by_platform[platform] = dict(mentions)
                
                # 计算占比
                total_mentions = sum(mentions.values())
                if total_mentions > 0:
                    percentages = {
                        brand: round(count / total_mentions * 100, 2)
                        for brand, count in mentions.items()
                    }
                else:
                    percentages = {}
                
                percentage_by_platform[platform] = percentages
            
            result = {
                'platforms': list(platform_data.keys()),
                'total_by_platform': total_by_platform,
                'mentions_by_platform': mentions_by_platform,
                'percentage_by_platform': percentage_by_platform,
            }
            
            duration = (time.time() - start_time) * 1000
            self.log_aggregation_complete(len(result['platforms']), duration)
            
            return result
            
        except Exception as e:
            self.log_aggregation_error(e)
            raise AggregationError(
                f"Platform aggregation failed: {str(e)}",
                details={'data_size': len(data)}
            )
    
    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'platforms': [],
            'total_by_platform': {},
            'mentions_by_platform': {},
            'percentage_by_platform': {},
        }
第五部分：按问题聚合器
python
# wechat_backend/v2/analytics/frequency/aggregators/question_aggregator.py

from collections import defaultdict
from typing import List, Dict, Any
import time

from wechat_backend/v2.analytics.frequency.aggregators.base import BaseAggregator
from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.analytics.frequency.errors import AggregationError


class QuestionAggregator(BaseAggregator):
    """
    按问题聚合器
    
    统计各问题下品牌的露出情况，帮助分析品牌在不同话题下的表现。
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('question_aggregator', config)
        
        self.config.setdefault('group_similar', False)  # 是否合并相似问题
        self.config.setdefault('similarity_threshold', 0.8)
    
    def aggregate(self, data: List[CleanedData]) -> Dict[str, Any]:
        """
        按问题聚合数据
        
        Returns:
            {
                'questions': ['问题1', '问题2', ...],
                'total_by_question': {'问题1': 100, ...},
                'mentions_by_question': {
                    '问题1': {'品牌A': 10, '品牌B': 5, ...}
                },
                'percentage_by_question': {
                    '问题1': {'品牌A': 10.0, '品牌B': 5.0, ...}
                }
            }
        """
        start_time = time.time()
        self.log_aggregation_start(len(data))
        
        try:
            if not self.validate_data(data):
                return self._empty_result()
            
            # 按问题分组
            question_data = defaultdict(list)
            for item in data:
                question = item.question
                
                # 如果需要合并相似问题
                if self.config['group_similar']:
                    question = self._normalize_question(question)
                
                question_data[question].append(item)
            
            # 统计各问题
            total_by_question = {}
            mentions_by_question = {}
            percentage_by_question = {}
            
            for question, items in question_data.items():
                # 总响应数
                total_by_question[question] = len(items)
                
                # 品牌提及次数
                mentions = defaultdict(int)
                for item in items:
                    entities = self.extract_entities(item)
                    for entity in entities:
                        mentions[entity] += 1
                
                mentions_by_question[question] = dict(mentions)
                
                # 计算占比
                total_mentions = sum(mentions.values())
                if total_mentions > 0:
                    percentages = {
                        brand: round(count / total_mentions * 100, 2)
                        for brand, count in mentions.items()
                    }
                else:
                    percentages = {}
                
                percentage_by_question[question] = percentages
            
            result = {
                'questions': list(question_data.keys()),
                'total_by_question': total_by_question,
                'mentions_by_question': mentions_by_question,
                'percentage_by_question': percentage_by_question,
            }
            
            duration = (time.time() - start_time) * 1000
            self.log_aggregation_complete(len(result['questions']), duration)
            
            return result
            
        except Exception as e:
            self.log_aggregation_error(e)
            raise AggregationError(
                f"Question aggregation failed: {str(e)}",
                details={'data_size': len(data)}
            )
    
    def _normalize_question(self, question: str) -> str:
        """归一化问题（用于相似问题合并）"""
        # 去除标点符号
        import re
        question = re.sub(r'[^\w\s]', '', question)
        # 转为小写
        question = question.lower()
        # 去除多余空格
        question = ' '.join(question.split())
        return question
    
    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'questions': [],
            'total_by_question': {},
            'mentions_by_question': {},
            'percentage_by_question': {},
        }
第六部分：竞品对比聚合器
python
# wechat_backend/v2/analytics/frequency/aggregators/competitor_aggregator.py

from collections import defaultdict
from typing import List, Dict, Any, Optional
import time

from wechat_backend/v2.analytics.frequency.aggregators.base import BaseAggregator
from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.analytics.frequency.models import CompetitiveAnalysis
from wechat_backend/v2.analytics.frequency.errors import AggregationError, InvalidBrandError


class CompetitorAggregator(BaseAggregator):
    """
    竞品对比聚合器
    
    对比主品牌与竞品的露出情况，包括：
    1. 总体露出对比
    2. 各平台优势分析
    3. 差距量化
    4. 趋势对比（如有历史数据）
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('competitor_aggregator', config)
        
        # 必须配置主品牌
        if 'main_brand' not in self.config:
            raise ValueError("main_brand must be specified in config")
        
        self.config.setdefault('competitors', [])
        self.config.setdefault('include_platform_analysis', True)
        self.config.setdefault('gap_threshold', 0.2)  # 20%以上视为显著差距
    
    def aggregate(self, data: List[CleanedData]) -> CompetitiveAnalysis:
        """
        执行竞品对比分析
        
        Returns:
            CompetitiveAnalysis 对象
        """
        start_time = time.time()
        self.log_aggregation_start(len(data))
        
        try:
            if not self.validate_data(data):
                return self._empty_analysis()
            
            main_brand = self.config['main_brand']
            competitors = self.config['competitors']
            all_brands = [main_brand] + competitors
            
            # 1. 总体露出统计
            exposure_counts = defaultdict(int)
            platform_counts = defaultdict(lambda: defaultdict(int))
            
            for item in data:
                entities = self.extract_entities(item)
                platform = item.model
                
                for entity in entities:
                    if entity in all_brands:
                        exposure_counts[entity] += 1
                        platform_counts[platform][entity] += 1
            
            # 2. 计算占比
            total_mentions = sum(exposure_counts.values())
            share_comparison = {}
            if total_mentions > 0:
                share_comparison = {
                    brand: round(count / total_mentions * 100, 2)
                    for brand, count in exposure_counts.items()
                }
            
            # 3. 平台优势分析
            platform_advantages = {}
            if self.config['include_platform_analysis']:
                for platform, brand_counts in platform_counts.items():
                    if brand_counts:
                        # 找出该平台露出最多的品牌
                        top_brand = max(brand_counts.items(), key=lambda x: x[1])[0]
                        platform_advantages[platform] = top_brand
            
            # 4. 差距分析
            gap_analysis = self._analyze_gaps(
                exposure_counts,
                main_brand,
                competitors
            )
            
            # 5. 构建结果
            analysis = CompetitiveAnalysis(
                main_brand=main_brand,
                competitors=competitors,
                exposure_comparison=dict(exposure_counts),
                share_comparison=share_comparison,
                platform_advantages=platform_advantages,
                gap_analysis=gap_analysis
            )
            
            duration = (time.time() - start_time) * 1000
            self.log_aggregation_complete(len(all_brands), duration)
            
            return analysis
            
        except Exception as e:
            self.log_aggregation_error(e)
            raise AggregationError(
                f"Competitor aggregation failed: {str(e)}",
                details={'data_size': len(data), 'main_brand': self.config['main_brand']}
            )
    
    def _analyze_gaps(
        self,
        exposure_counts: Dict[str, int],
        main_brand: str,
        competitors: List[str]
    ) -> Dict[str, Any]:
        """
        分析品牌间差距
        
        Returns:
            {
                'gaps': {'竞品A': 10, ...},  # 绝对值差距
                'gap_percentages': {'竞品A': 20.5, ...},  # 百分比差距
                'significant_gaps': ['竞品A'],  # 显著差距的品牌
                'leading': True/False,  # 是否领先
                'average_gap': 15.3,  # 平均差距
            }
        """
        main_count = exposure_counts.get(main_brand, 0)
        
        gaps = {}
        gap_percentages = {}
        significant_gaps = []
        
        for comp in competitors:
            comp_count = exposure_counts.get(comp, 0)
            
            # 绝对值差距
            gap = main_count - comp_count
            gaps[comp] = gap
            
            # 百分比差距
            if comp_count > 0:
                gap_pct = round((main_count - comp_count) / comp_count * 100, 2)
            else:
                gap_pct = 100.0 if main_count > 0 else 0.0
            gap_percentages[comp] = gap_pct
            
            # 判断是否显著差距
            if abs(gap_pct) > self.config['gap_threshold'] * 100:
                significant_gaps.append(comp)
        
        # 计算平均差距
        avg_gap = sum(gaps.values()) / len(gaps) if gaps else 0
        
        return {
            'gaps': gaps,
            'gap_percentages': gap_percentages,
            'significant_gaps': significant_gaps,
            'leading': main_count >= max(exposure_counts.values()) if exposure_counts else False,
            'average_gap': round(avg_gap, 2),
        }
    
    def validate_data(self, data: List[CleanedData]) -> bool:
        """验证数据，确保主品牌存在"""
        if not super().validate_data(data):
            return False
        
        # 检查数据中是否包含主品牌（可选，不是强制要求）
        main_brand = self.config['main_brand']
        has_main = any(
            main_brand in self.extract_entities(item)
            for item in data
        )
        
        if not has_main:
            logger.warning(f"Main brand '{main_brand}' not found in data")
        
        return True
    
    def _empty_analysis(self) -> CompetitiveAnalysis:
        """返回空分析结果"""
        return CompetitiveAnalysis(
            main_brand=self.config['main_brand'],
            competitors=self.config['competitors']
        )
第七部分：频段分布计算主类
python
# wechat_backend/v2/analytics/frequency/calculator.py

from typing import List, Dict, Any, Optional
import time
from collections import defaultdict

from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.analytics.frequency.models import ExposureDistribution
from wechat_backend/v2.analytics.frequency.aggregators.platform_aggregator import PlatformAggregator
from wechat_backend/v2.analytics.frequency.aggregators.question_aggregator import QuestionAggregator
from wechat_backend/v2.analytics.frequency.aggregators.competitor_aggregator import CompetitorAggregator
from wechat_backend/v2.analytics.frequency.errors import (
    FrequencyAnalysisError,
    InsufficientDataError,
    DataValidationError
)


class FrequencyCalculator:
    """
    频段分布计算器
    
    负责协调各个聚合器，生成完整的频段分布分析报告。
    这是频段分析的核心入口类。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化频段计算器
        
        Args:
            config: 全局配置
        """
        self.config = config or {}
        
        # 默认配置
        self.config.setdefault('min_data_points', 1)  # 最小数据点要求
        self.config.setdefault('include_platform_analysis', True)
        self.config.setdefault('include_question_analysis', True)
        self.config.setdefault('include_competitor_analysis', True)
        self.config.setdefault('main_brand', None)  # 主品牌（用于竞品分析）
        self.config.setdefault('competitors', [])   # 竞品列表
        
        # 初始化聚合器
        self.platform_aggregator = PlatformAggregator(
            self.config.get('platform_config', {})
        )
        self.question_aggregator = QuestionAggregator(
            self.config.get('question_config', {})
        )
        
        # 竞品聚合器需要主品牌信息
        if self.config['main_brand']:
            competitor_config = self.config.get('competitor_config', {})
            competitor_config['main_brand'] = self.config['main_brand']
            competitor_config['competitors'] = self.config['competitors']
            self.competitor_aggregator = CompetitorAggregator(competitor_config)
        else:
            self.competitor_aggregator = None
    
    async def calculate(
        self,
        data: List[CleanedData],
        execution_id: Optional[str] = None
    ) -> ExposureDistribution:
        """
        执行频段分布计算
        
        Args:
            data: 清洗后的数据列表
            execution_id: 执行ID（用于日志追踪）
            
        Returns:
            露出分布统计结果
            
        Raises:
            InsufficientDataError: 数据不足
            DataValidationError: 数据验证失败
        """
        start_time = time.time()
        
        logger.info(
            "frequency_calculation_started",
            extra={
                'execution_id': execution_id,
                'data_size': len(data),
                'config': self.config
            }
        )
        
        try:
            # 1. 验证数据
            if not data:
                raise InsufficientDataError(
                    "No data provided for frequency calculation",
                    execution_id=execution_id
                )
            
            if len(data) < self.config['min_data_points']:
                raise InsufficientDataError(
                    f"Insufficient data points: {len(data)} < {self.config['min_data_points']}",
                    execution_id=execution_id
                )
            
            # 2. 按平台聚合
            platform_result = {}
            if self.config['include_platform_analysis']:
                platform_result = self.platform_aggregator.aggregate(data)
            
            # 3. 按问题聚合
            question_result = {}
            if self.config['include_question_analysis']:
                question_result = self.question_aggregator.aggregate(data)
            
            # 4. 计算整体品牌分布
            brand_counts = self._calculate_brand_counts(data)
            brand_distribution = self._calculate_percentages(brand_counts)
            
            # 5. 生成排名
            ranking = self._generate_ranking(brand_counts)
            
            # 6. 构建结果对象
            distribution = ExposureDistribution(
                total_responses=len(data),
                total_mentions=sum(brand_counts.values()),
                brands_involved=len(brand_counts),
                brand_distribution=brand_distribution,
                brand_counts=brand_counts,
                platform_distribution=platform_result.get('percentage_by_platform', {}),
                question_distribution=question_result.get('percentage_by_question', {}),
                ranking=ranking,
                data_source="cleaned_data"
            )
            
            duration = (time.time() - start_time) * 1000
            logger.info(
                "frequency_calculation_completed",
                extra={
                    'execution_id': execution_id,
                    'duration_ms': duration,
                    'brands_count': len(brand_counts),
                    'total_mentions': distribution.total_mentions
                }
            )
            
            return distribution
            
        except Exception as e:
            logger.error(
                "frequency_calculation_failed",
                extra={
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            raise
    
    async def calculate_with_competitors(
        self,
        data: List[CleanedData],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算频段分布并包含竞品分析
        
        Returns:
            {
                'distribution': ExposureDistribution,
                'competitive_analysis': CompetitiveAnalysis
            }
        """
        # 1. 基础频段分布
        distribution = await self.calculate(data, execution_id)
        
        # 2. 竞品分析（如果配置了）
        competitive_analysis = None
        if self.competitor_aggregator:
            competitive_analysis = self.competitor_aggregator.aggregate(data)
        
        return {
            'distribution': distribution,
            'competitive_analysis': competitive_analysis
        }
    
    def _calculate_brand_counts(self, data: List[CleanedData]) -> Dict[str, int]:
        """计算各品牌出现次数"""
        counts = defaultdict(int)
        
        for item in data:
            entities = self.platform_aggregator.extract_entities(item)
            for entity in entities:
                counts[entity] += 1
        
        return dict(counts)
    
    def _calculate_percentages(self, counts: Dict[str, int]) -> Dict[str, float]:
        """计算百分比"""
        total = sum(counts.values())
        if total == 0:
            return {}
        
        return {
            brand: round(count / total * 100, 2)
            for brand, count in counts.items()
        }
    
    def _generate_ranking(self, counts: Dict[str, int]) -> List[Dict[str, Any]]:
        """生成品牌排名"""
        sorted_brands = sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        ranking = []
        for rank, (brand, count) in enumerate(sorted_brands, 1):
            ranking.append({
                'rank': rank,
                'brand': brand,
                'mentions': count,
                'is_main': brand == self.config.get('main_brand')
            })
        
        return ranking
    
    def set_main_brand(self, brand: str, competitors: List[str] = None):
        """设置主品牌（用于竞品分析）"""
        self.config['main_brand'] = brand
        if competitors is not None:
            self.config['competitors'] = competitors
        
        # 重新初始化竞品聚合器
        competitor_config = self.config.get('competitor_config', {})
        competitor_config['main_brand'] = brand
        competitor_config['competitors'] = competitors or []
        self.competitor_aggregator = CompetitorAggregator(competitor_config)
第八部分：图表数据格式化
python
# wechat_backend/v2/analytics/frequency/formatters/chart_formatter.py

from typing import Dict, Any, List
from wechat_backend/v2.analytics.frequency.models import ExposureDistribution


class ChartFormatter:
    """
    图表数据格式化器
    
    将频段分布数据转换为前端图表库（如 ECharts）所需的格式。
    """
    
    @staticmethod
    def format_pie_chart(
        distribution: ExposureDistribution,
        limit: int = 10,
        others_label: str = "其他"
    ) -> Dict[str, Any]:
        """
        格式化饼图数据
        
        Args:
            distribution: 露出分布数据
            limit: 最多显示的品牌数
            others_label: "其他"类别的标签
            
        Returns:
            ECharts 饼图数据格式
        """
        # 按计数排序
        sorted_items = sorted(
            distribution.brand_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 取前 limit 个
        top_items = sorted_items[:limit]
        
        # 剩余的合并为"其他"
        others_count = sum(count for _, count in sorted_items[limit:])
        
        series_data = [
            {'name': brand, 'value': count}
            for brand, count in top_items
        ]
        
        if others_count > 0:
            series_data.append({'name': others_label, 'value': others_count})
        
        return {
            'title': {
                'text': '品牌露出分布',
                'subtext': f'总计 {distribution.total_mentions} 次提及'
            },
            'tooltip': {
                'trigger': 'item',
                'formatter': '{b}: {c} ({d}%)'
            },
            'series': [
                {
                    'name': '品牌露出',
                    'type': 'pie',
                    'radius': '50%',
                    'data': series_data,
                    'label': {
                        'show': True,
                        'formatter': '{b}: {d}%'
                    }
                }
            ]
        }
    
    @staticmethod
    def format_bar_chart(
        distribution: ExposureDistribution,
        platform: str = None
    ) -> Dict[str, Any]:
        """
        格式化柱状图数据
        
        Args:
            distribution: 露出分布数据
            platform: 指定平台（None表示整体）
            
        Returns:
            ECharts 柱状图数据格式
        """
        if platform and platform in distribution.platform_distribution:
            # 特定平台的数据
            platform_data = distribution.platform_distribution[platform]
            brands = list(platform_data.keys())
            percentages = list(platform_data.values())
            title = f'{platform} 平台品牌露出占比'
        else:
            # 整体数据
            brands = list(distribution.brand_distribution.keys())
            percentages = list(distribution.brand_distribution.values())
            title = '整体品牌露出占比'
        
        return {
            'title': {'text': title},
            'tooltip': {
                'trigger': 'axis',
                'formatter': '{b}: {c}%'
            },
            'xAxis': {
                'type': 'category',
                'data': brands,
                'axisLabel': {'rotate': 45}
            },
            'yAxis': {
                'type': 'value',
                'name': '占比 (%)',
                'max': 100
            },
            'series': [
                {
                    'name': '占比',
                    'type': 'bar',
                    'data': percentages,
                    'itemStyle': {
                        'color': '#5470c6'
                    }
                }
            ]
        }
    
    @staticmethod
    def format_stacked_bar_chart(
        distribution: ExposureDistribution
    ) -> Dict[str, Any]:
        """
        格式化堆叠柱状图（各平台品牌分布）
        
        Returns:
            ECharts 堆叠柱状图数据
        """
        # 获取所有品牌
        all_brands = set()
        for platform_data in distribution.platform_distribution.values():
            all_brands.update(platform_data.keys())
        
        brands = sorted(all_brands)
        platforms = list(distribution.platform_distribution.keys())
        
        series = []
        for brand in brands:
            data = []
            for platform in platforms:
                percentage = distribution.platform_distribution[platform].get(brand, 0)
                data.append(percentage)
            
            series.append({
                'name': brand,
                'type': 'bar',
                'stack': 'total',
                'data': data,
                'label': {'show': True}
            })
        
        return {
            'title': {'text': '各平台品牌露出分布'},
            'tooltip': {
                'trigger': 'axis',
                'formatter': '{b}<br/>{c}%'
            },
            'xAxis': {
                'type': 'category',
                'data': platforms
            },
            'yAxis': {
                'type': 'value',
                'name': '占比 (%)',
                'max': 100
            },
            'series': series
        }
    
    @staticmethod
    def format_ranking_table(
        distribution: ExposureDistribution,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        格式化排名表格数据
        
        Returns:
            表格行数据列表
        """
        ranking = distribution.ranking[:limit]
        
        table_data = []
        for item in ranking:
            table_data.append({
                'rank': item['rank'],
                'brand': item['brand'],
                'mentions': item['mentions'],
                'percentage': distribution.brand_distribution.get(item['brand'], 0),
                'is_main': item.get('is_main', False)
            })
        
        return table_data
第九部分：报告数据格式化
python
# wechat_backend/v2/analytics/frequency/formatters/report_formatter.py

from typing import Dict, Any, List
from wechat_backend/v2.analytics.frequency.models import ExposureDistribution, CompetitiveAnalysis


class ReportFormatter:
    """
    报告数据格式化器
    
    将频段分布数据转换为最终报告所需的格式。
    """
    
    @staticmethod
    def format_for_report(
        distribution: ExposureDistribution,
        competitive_analysis: CompetitiveAnalysis = None
    ) -> Dict[str, Any]:
        """
        格式化为报告数据
        
        这是最终返回给前端的数据格式
        """
        # 执行摘要
        executive_summary = ReportFormatter._generate_executive_summary(
            distribution,
            competitive_analysis
        )
        
        # 核心统计数据
        core_stats = ReportFormatter._format_core_stats(distribution)
        
        # 品牌分布详情
        brand_details = ReportFormatter._format_brand_details(distribution)
        
        # 平台分布
        platform_details = ReportFormatter._format_platform_details(distribution)
        
        # 问题分布
        question_details = ReportFormatter._format_question_details(distribution)
        
        # 竞品分析（如果有）
        competitor_details = None
        if competitive_analysis:
            competitor_details = ReportFormatter._format_competitor_analysis(
                competitive_analysis
            )
        
        return {
            'summary': executive_summary,
            'core_stats': core_stats,
            'brand_distribution': brand_details,
            'platform_distribution': platform_details,
            'question_distribution': question_details,
            'competitor_analysis': competitor_details,
            'metadata': {
                'computed_at': distribution.computed_at.isoformat(),
                'total_responses': distribution.total_responses,
                'brands_involved': distribution.brands_involved,
                'version': distribution.version
            }
        }
    
    @staticmethod
    def _generate_executive_summary(
        distribution: ExposureDistribution,
        competitive_analysis: CompetitiveAnalysis = None
    ) -> Dict[str, Any]:
        """生成执行摘要"""
        # 找出露出最多的品牌
        top_brand = None
        top_count = 0
        if distribution.brand_counts:
            top_brand, top_count = max(
                distribution.brand_counts.items(),
                key=lambda x: x[1]
            )
        
        # 计算集中度（前3品牌占比）
        sorted_counts = sorted(
            distribution.brand_counts.values(),
            reverse=True
        )
        top3_sum = sum(sorted_counts[:3])
        concentration = round(top3_sum / distribution.total_mentions * 100, 2) if distribution.total_mentions > 0 else 0
        
        # 主品牌表现（如果有）
        main_brand_performance = None
        if competitive_analysis and competitive_analysis.main_brand:
            main_count = distribution.brand_counts.get(competitive_analysis.main_brand, 0)
            main_percentage = distribution.brand_distribution.get(competitive_analysis.main_brand, 0)
            
            # 排名
            rank = None
            for i, item in enumerate(distribution.ranking, 1):
                if item['brand'] == competitive_analysis.main_brand:
                    rank = i
                    break
            
            main_brand_performance = {
                'brand': competitive_analysis.main_brand,
                'mentions': main_count,
                'percentage': main_percentage,
                'rank': rank
            }
        
        return {
            'top_brand': top_brand,
            'top_brand_mentions': top_count,
            'total_mentions': distribution.total_mentions,
            'brands_count': distribution.brands_involved,
            'concentration': concentration,
            'main_brand': main_brand_performance
        }
    
    @staticmethod
    def _format_core_stats(distribution: ExposureDistribution) -> Dict[str, Any]:
        """格式化核心统计"""
        return {
            'total_responses': distribution.total_responses,
            'total_mentions': distribution.total_mentions,
            'brands_involved': distribution.brands_involved,
            'avg_mentions_per_response': round(
                distribution.total_mentions / distribution.total_responses, 2
            ) if distribution.total_responses > 0 else 0,
            'mentions_per_brand': {
                'max': max(distribution.brand_counts.values()) if distribution.brand_counts else 0,
                'min': min(distribution.brand_counts.values()) if distribution.brand_counts else 0,
                'avg': round(
                    sum(distribution.brand_counts.values()) / len(distribution.brand_counts), 2
                ) if distribution.brand_counts else 0
            }
        }
    
    @staticmethod
    def _format_brand_details(distribution: ExposureDistribution) -> List[Dict[str, Any]]:
        """格式化品牌详情"""
        details = []
        for item in distribution.ranking:
            details.append({
                'rank': item['rank'],
                'brand': item['brand'],
                'mentions': item['mentions'],
                'percentage': distribution.brand_distribution.get(item['brand'], 0),
                'platforms': ReportFormatter._get_brand_platforms(
                    distribution,
                    item['brand']
                )
            })
        return details
    
    @staticmethod
    def _format_platform_details(distribution: ExposureDistribution) -> List[Dict[str, Any]]:
        """格式化平台详情"""
        details = []
        for platform, percentages in distribution.platform_distribution.items():
            # 该平台的总响应数
            total_responses = len([
                p for p in distribution.platform_distribution.keys()
                if p == platform
            ])  # 简化，实际需要从原始数据获取
            
            # 找出该平台露出最多的品牌
            top_brand = max(percentages.items(), key=lambda x: x[1])[0] if percentages else None
            
            details.append({
                'platform': platform,
                'total_responses': total_responses,
                'top_brand': top_brand,
                'brands': [
                    {'brand': b, 'percentage': p}
                    for b, p in percentages.items()
                ]
            })
        return details
    
    @staticmethod
    def _format_question_details(distribution: ExposureDistribution) -> List[Dict[str, Any]]:
        """格式化问题详情"""
        details = []
        for question, percentages in distribution.question_distribution.items():
            # 该问题下露出最多的品牌
            top_brand = max(percentages.items(), key=lambda x: x[1])[0] if percentages else None
            
            details.append({
                'question': question[:100] + '...' if len(question) > 100 else question,
                'top_brand': top_brand,
                'brands': [
                    {'brand': b, 'percentage': p}
                    for b, p in percentages.items()
                ]
            })
        return details
    
    @staticmethod
    def _format_competitor_analysis(analysis: CompetitiveAnalysis) -> Dict[str, Any]:
        """格式化竞品分析"""
        return {
            'main_brand': analysis.main_brand,
            'competitors': analysis.competitors,
            'exposure_comparison': analysis.exposure_comparison,
            'share_comparison': analysis.share_comparison,
            'platform_advantages': analysis.platform_advantages,
            'gap_analysis': analysis.gap_analysis,
            'summary': {
                '领先' if analysis.gap_analysis.get('leading') else '落后',
                '平均差距': analysis.gap_analysis.get('average_gap', 0),
                '显著差距品牌': analysis.gap_analysis.get('significant_gaps', [])
            }
        }
    
    @staticmethod
    def _get_brand_platforms(
        distribution: ExposureDistribution,
        brand: str
    ) -> List[Dict[str, Any]]:
        """获取品牌在各平台的表现"""
        platforms = []
        for platform, percentages in distribution.platform_distribution.items():
            if brand in percentages:
                platforms.append({
                    'platform': platform,
                    'percentage': percentages[brand]
                })
        
        # 按占比排序
        platforms.sort(key=lambda x: x['percentage'], reverse=True)
        return platforms
第十部分：与报告服务集成
python
# wechat_backend/v2/services/report_generation_service.py（新增）

from typing import List, Dict, Any, Optional
from wechat_backend/v2.analytics.frequency.calculator import FrequencyCalculator
from wechat_backend/v2.analytics.frequency.formatters.report_formatter import ReportFormatter
from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
from wechat_backend/v2.analytics.frequency.errors import InsufficientDataError


class ReportGenerationService:
    """
    报告生成服务
    
    负责协调各个分析模块，生成完整的诊断报告。
    """
    
    def __init__(self):
        self.frequency_calculator = FrequencyCalculator()
        self.result_repo = DiagnosisResultRepository()
    
    async def generate_report(
        self,
        execution_id: str,
        report_id: int,
        main_brand: str,
        competitors: List[str] = None
    ) -> Dict[str, Any]:
        """
        生成完整报告
        
        Args:
            execution_id: 执行ID
            report_id: 报告ID
            main_brand: 主品牌
            competitors: 竞品列表
            
        Returns:
            完整报告数据
        """
        logger.info(
            "report_generation_started",
            extra={
                'execution_id': execution_id,
                'report_id': report_id,
                'main_brand': main_brand
            }
        )
        
        # 1. 获取原始数据
        results = self.result_repo.get_by_execution_id(execution_id)
        
        # 2. 转换为清洗数据（实际应该从数据库读取清洗后的数据）
        # 这里简化处理，假设已经有清洗数据
        cleaned_data = await self._get_cleaned_data(execution_id)
        
        if not cleaned_data:
            raise InsufficientDataError(
                f"No cleaned data found for execution {execution_id}",
                execution_id=execution_id
            )
        
        # 3. 设置主品牌和竞品
        self.frequency_calculator.set_main_brand(main_brand, competitors or [])
        
        # 4. 执行频段分析
        result = await self.frequency_calculator.calculate_with_competitors(
            cleaned_data,
            execution_id
        )
        
        distribution = result['distribution']
        competitive_analysis = result.get('competitive_analysis')
        
        # 5. 格式化为报告
        report_data = ReportFormatter.format_for_report(
            distribution,
            competitive_analysis
        )
        
        # 6. 添加报告元数据
        report_data['report_meta'] = {
            'execution_id': execution_id,
            'report_id': report_id,
            'generated_at': datetime.now().isoformat(),
            'version': '2.0'
        }
        
        logger.info(
            "report_generation_completed",
            extra={
                'execution_id': execution_id,
                'report_id': report_id,
                'brands_count': distribution.brands_involved
            }
        )
        
        return report_data
    
    async def _get_cleaned_data(self, execution_id: str) -> List[CleanedData]:
        """
        获取清洗后的数据
        
        实际应该从专门的 cleaned_results 表读取
        这里简化实现
        """
        # TODO: 实现从数据库读取清洗数据
        # 暂时返回空列表
        return []
第十一部分：特性开关配置
python
# wechat_backend/v2/feature_flags.py（更新）

FEATURE_FLAGS = {
    # 阶段一已完成的功能（默认开启）
    'diagnosis_v2_state_machine': True,
    'diagnosis_v2_timeout': True,
    'diagnosis_v2_retry': True,
    'diagnosis_v2_dead_letter': True,
    'diagnosis_v2_api_logging': True,
    'diagnosis_v2_data_persistence': True,
    'diagnosis_v2_report_stub': True,
    
    # 阶段二已完成的开关
    'diagnosis_v2_ai_adapters': True,           # P2-T1已完成
    'diagnosis_v2_cleaning_pipeline': True,      # P2-T2已完成
    
    # 阶段二新增开关
    'diagnosis_v2_frequency_analysis': False,    # 频段分析总开关
    'diagnosis_v2_frequency_platform': False,    # 平台聚合
    'diagnosis_v2_frequency_question': False,    # 问题聚合
    'diagnosis_v2_frequency_competitor': False,  # 竞品分析
    
    # 灰度控制
    'diagnosis_v2_gray_users': [],
    'diagnosis_v2_gray_percentage': 0,
    
    # 降级开关
    'diagnosis_v2_fallback_to_v1': True,
}
测试要求
单元测试覆盖场景
python
# tests/unit/analytics/frequency/test_calculator.py

class TestFrequencyCalculator:
    """测试频段分布计算器"""
    
    @pytest.mark.asyncio
    async def test_calculate_with_valid_data(self):
        """测试有效数据的计算"""
        # 准备测试数据
        data = create_test_cleaned_data()
        
        calculator = FrequencyCalculator()
        result = await calculator.calculate(data)
        
        assert isinstance(result, ExposureDistribution)
        assert result.total_responses == len(data)
        assert result.total_mentions > 0
    
    @pytest.mark.asyncio
    async def test_calculate_with_empty_data(self):
        """测试空数据处理"""
        calculator = FrequencyCalculator()
        
        with pytest.raises(InsufficientDataError):
            await calculator.calculate([])
    
    def test_brand_counts_calculation(self):
        """测试品牌计数计算"""
        data = create_test_cleaned_data()
        calculator = FrequencyCalculator()
        
        counts = calculator._calculate_brand_counts(data)
        assert isinstance(counts, dict)
        assert len(counts) > 0
    
    def test_percentage_calculation(self):
        """测试百分比计算"""
        counts = {'品牌A': 10, '品牌B': 5, '品牌C': 5}
        calculator = FrequencyCalculator()
        
        percentages = calculator._calculate_percentages(counts)
        assert percentages['品牌A'] == 50.0
        assert percentages['品牌B'] == 25.0
        assert percentages['品牌C'] == 25.0
    
    def test_ranking_generation(self):
        """测试排名生成"""
        counts = {'品牌B': 5, '品牌A': 10, '品牌C': 3}
        calculator = FrequencyCalculator()
        
        ranking = calculator._generate_ranking(counts)
        assert ranking[0]['brand'] == '品牌A'
        assert ranking[0]['rank'] == 1
        assert ranking[1]['brand'] == '品牌B'
        assert ranking[2]['brand'] == '品牌C'
python
# tests/unit/analytics/frequency/test_platform_aggregator.py

class TestPlatformAggregator:
    """测试平台聚合器"""
    
    def test_aggregate_by_platform(self):
        """测试按平台聚合"""
        data = create_test_cleaned_data()
        aggregator = PlatformAggregator()
        
        result = aggregator.aggregate(data)
        
        assert 'platforms' in result
        assert 'total_by_platform' in result
        assert 'mentions_by_platform' in result
        assert 'percentage_by_platform' in result
    
    def test_platform_filtering(self):
        """测试平台过滤"""
        data = create_test_cleaned_data()
        aggregator = PlatformAggregator({
            'include_platforms': ['deepseek']
        })
        
        result = aggregator.aggregate(data)
        
        # 应该只包含 deepseek
        for platform in result['platforms']:
            assert platform == 'deepseek'
python
# tests/unit/analytics/frequency/test_competitor_aggregator.py

class TestCompetitorAggregator:
    """测试竞品聚合器"""
    
    def test_aggregate_with_competitors(self):
        """测试竞品分析"""
        data = create_test_cleaned_data()
        aggregator = CompetitorAggregator({
            'main_brand': '品牌A',
            'competitors': ['品牌B', '品牌C']
        })
        
        result = aggregator.aggregate(data)
        
        assert isinstance(result, CompetitiveAnalysis)
        assert result.main_brand == '品牌A'
        assert '品牌B' in result.competitors
    
    def test_gap_analysis(self):
        """测试差距分析"""
        aggregator = CompetitorAggregator({
            'main_brand': '品牌A',
            'competitors': ['品牌B']
        })
        
        exposure_counts = {'品牌A': 10, '品牌B': 5}
        gaps = aggregator._analyze_gaps(exposure_counts, '品牌A', ['品牌B'])
        
        assert gaps['gaps']['品牌B'] == 5
        assert gaps['leading'] is True
        assert gaps['average_gap'] == 5.0
python
# tests/unit/analytics/frequency/test_formatters.py

class TestChartFormatter:
    """测试图表格式化器"""
    
    def test_format_pie_chart(self):
        """测试饼图格式化"""
        distribution = create_test_distribution()
        
        chart = ChartFormatter.format_pie_chart(distribution)
        
        assert 'series' in chart
        assert chart['series'][0]['type'] == 'pie'
        assert len(chart['series'][0]['data']) > 0
    
    def test_format_bar_chart(self):
        """测试柱状图格式化"""
        distribution = create_test_distribution()
        
        chart = ChartFormatter.format_bar_chart(distribution)
        
        assert 'xAxis' in chart
        assert 'yAxis' in chart
        assert chart['yAxis']['name'] == '占比 (%)'


class TestReportFormatter:
    """测试报告格式化器"""
    
    def test_format_for_report(self):
        """测试报告格式化"""
        distribution = create_test_distribution()
        
        report = ReportFormatter.format_for_report(distribution)
        
        assert 'summary' in report
        assert 'core_stats' in report
        assert 'brand_distribution' in report
        assert 'metadata' in report
集成测试
python
# tests/integration/test_frequency_analytics_integration.py

class TestFrequencyAnalyticsIntegration:
    """频段分析集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_frequency_analysis(self):
        """测试端到端频段分析"""
        # 1. 准备测试数据（模拟从数据库读取）
        cleaned_data = create_test_cleaned_data()
        
        # 2. 创建计算器
        calculator = FrequencyCalculator({
            'main_brand': '品牌A',
            'competitors': ['品牌B', '品牌C']
        })
        
        # 3. 执行计算
        result = await calculator.calculate_with_competitors(cleaned_data)
        
        # 4. 验证结果
        assert 'distribution' in result
        assert 'competitive_analysis' in result
        
        distribution = result['distribution']
        assert distribution.total_responses > 0
        
        # 5. 格式化为报告
        report = ReportFormatter.format_for_report(
            distribution,
            result['competitive_analysis']
        )
        
        # 6. 验证报告结构
        assert report['summary']['total_mentions'] > 0
        assert len(report['brand_distribution']) > 0
输出要求
1. 完整代码实现
wechat_backend/v2/analytics/frequency/calculator.py

wechat_backend/v2/analytics/frequency/models.py

wechat_backend/v2/analytics/frequency/errors.py

wechat_backend/v2/analytics/frequency/aggregators/base.py

wechat_backend/v2/analytics/frequency/aggregators/platform_aggregator.py

wechat_backend/v2/analytics/frequency/aggregators/question_aggregator.py

wechat_backend/v2/analytics/frequency/aggregators/competitor_aggregator.py

wechat_backend/v2/analytics/frequency/formatters/chart_formatter.py

wechat_backend/v2/analytics/frequency/formatters/report_formatter.py

wechat_backend/v2/services/report_generation_service.py（新增）

wechat_backend/v2/feature_flags.py（更新）

2. 测试代码
tests/unit/analytics/frequency/test_calculator.py

tests/unit/analytics/frequency/test_platform_aggregator.py

tests/unit/analytics/frequency/test_question_aggregator.py

tests/unit/analytics/frequency/test_competitor_aggregator.py

tests/unit/analytics/frequency/test_formatters.py

tests/integration/test_frequency_analytics_integration.py

3. 提交信息
bash
feat(analytics): implement frequency distribution analysis algorithms

- Add FrequencyCalculator as main entry point for brand exposure analysis
- Implement platform aggregator for per-AI platform statistics
- Add question aggregator for per-question brand distribution
- Implement competitor aggregator with gap analysis
- Add chart formatters for ECharts-compatible data structures
- Add report formatter for final report generation
- Integrate with P2-T2 cleaned data models
- Add comprehensive unit and integration tests with 92% coverage

Closes #203
Refs: 2026-02-27-重构基线.md, 2026-02-27-重构实施路线图.md

Change-Id: I3456789012abcdef
4. PR 描述模板
markdown
## 变更说明
实现频段分布统计算法，用于分析品牌在AI平台响应中的露出情况。

主要功能：
1. 频段分布计算器 - 协调各聚合器，生成完整分布数据
2. 平台聚合器 - 按AI平台统计品牌露出
3. 问题聚合器 - 按诊断问题统计品牌露出
4. 竞品聚合器 - 对比主品牌与竞品的露出情况
5. 差距分析 - 量化品牌间的差距
6. 图表格式化 - 生成ECharts兼容的数据格式
7. 报告格式化 - 生成最终报告数据结构

## 关联文档
- 重构基线：第 1.2 节 - 报告内容标准
- 实施路线图：P2-T3
- 开发规范：第 2.3 节 - 函数规范

## 测试计划
- [x] 单元测试已添加（覆盖率 92%）
- [x] 集成测试已添加
- [ ] 真实数据测试（需在预发布环境验证）

### 测试结果
单元测试：28 passed, 0 failed
集成测试：3 passed, 0 failed
覆盖率：92%
关键场景验证：

品牌计数准确 ✓

百分比计算精确 ✓

排名生成正确 ✓

竞品差距分析 ✓

图表格式正确 ✓

text

## 验收标准
- [x] 统计计算结果精确（误差0）
- [x] 支持多维度聚合（平台/问题）
- [x] 竞品对比功能完整
- [x] 与P2-T2清洗数据正确集成
- [x] 测试覆盖率 > 85%

## 回滚方案
关闭特性开关 `diagnosis_v2_frequency_analysis` 即可禁用频段分析功能。

```python
FEATURE_FLAGS['diagnosis_v2_frequency_analysis'] = False
依赖关系
依赖 P2-T2 清洗管道（提供CleanedData）

本任务完成后，P2-T4 情感分析将基于此模块的结构

P2-T8 前端渲染将使用本模块的格式化数据

text

---

## 注意事项

1. **计算精度**：所有百分比计算必须精确到小数点后两位，误差为0
2. **性能优化**：聚合操作要考虑数据量，避免内存溢出
3. **可扩展性**：聚合器设计要支持新增维度
4. **空值处理**：妥善处理数据缺失情况
5. **并发安全**：计算器应该是无状态的，可以并发使用
6. **日志记录**：关键计算步骤要有结构化日志
7. **测试覆盖**：边界条件（空数据、单条数据、大量数据）都要覆盖

---

## 验证清单（交付前自查）

### 代码完整性
- [ ] 所有聚合器继承自基类
- [ ] 计算器正确协调各聚合器
- [ ] 格式化器输出符合前端要求
- [ ] 异常类层次清晰

### 计算准确性
- [ ] 品牌计数准确
- [ ] 百分比计算精确
- [ ] 排名正确
- [ ] 竞品差距分析合理

### 多维度支持
- [ ] 按平台聚合
- [ ] 按问题聚合
- [ ] 竞品对比
- [ ] 支持自定义配置

### 错误处理
- [ ] 空数据处理
- [ ] 数据不足时抛出明确异常
- [ ] 无效品牌处理

### 测试覆盖
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试通过
- [ ] 边界条件测试覆盖

### 文档
- [ ] 代码有完整 docstring
- [ ] 使用示例完整
- [ ] 配置说明清晰
