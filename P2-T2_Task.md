系统重构 阶段二 - P2-T2 数据清洗管道实现
任务背景
当前阶段：阶段二（核心业务功能实现）- Week 3-5
阶段目标：交付真实的统计分析报告
已完成任务：

阶段一所有任务已完成并合并（P1-T1 到 P1-T10）

P2-T1 AI平台标准化数据交互层（已合并）- 提供了统一的AI响应格式

当前任务：P2-T2 - 数据清洗管道实现

参考文档
重构基线：第 2.1.2 节 - 数据清洗与统计分析

开发规范：第 2.3 节 - 函数规范、第 2.4 节 - 异常处理规范、第 2.5 节 - 日志规范

实施路线图：第 2.2.2 节 - P2-T2 详细设计

P2-T1输出：AIRequest/AIResponse 数据模型、标准化响应格式

核心要求（通用部分）
1. 严格遵守重构基线
业务导向：所有代码必须服务于"让用户获取真实品牌诊断报告"这一核心目标

数据真实性：清洗过程必须保留原始数据，不得篡改或丢失信息

可追溯性：从清洗后的数据必须能追溯到原始API响应

幂等性：同一原始数据多次清洗应得到相同结果

2. 严格遵守开发规范
目录结构：所有 v2 代码必须放在 wechat_backend/v2/ 目录下

命名规范：类名 PascalCase，函数名 snake_case，常量 UPPER_SNAKE_CASE

类型注解：所有函数必须有完整的类型注解

函数长度：每个函数不超过 50 行，复杂逻辑必须拆分

圈复杂度：每个函数圈复杂度不超过 10

异常处理：必须使用自定义异常类，禁止空的 except 块

日志规范：必须使用结构化日志，记录清洗过程中的关键步骤

特性开关：所有新功能必须通过特性开关控制，默认关闭

3. 与前期任务的集成
依赖 P2-T1：必须处理 AIResponse 标准化格式

依赖 P1-T6：清洗后的数据需通过原始数据持久化机制保存

依赖 P1-T5：清洗过程中的异常需记录到 API 调用日志

当前任务：P2-T2 - 数据清洗管道实现
任务描述
实现数据清洗管道，将 AI 平台返回的原始响应转换为结构化的、可用于统计分析的数据。这是从"原始数据"到"可用数据"的关键转换层。

核心职责：

文本提取：从不同格式的响应中提取纯文本内容

实体识别：识别品牌名称、竞品名称等关键实体

去重处理：去除重复的响应内容

格式验证：验证响应格式是否符合预期

GEO数据准备：为后续GEO分析准备基础数据

质量预评分：基于响应长度、完整性等进行初步质量评估

清洗流程编排：将多个清洗步骤组合成可配置的管道

业务价值
数据清洗管道的价值在于：

数据标准化：将异构的AI响应转换为统一结构

质量保障：过滤无效、不完整的响应

分析准备：为后续统计分析准备好所需字段

错误隔离：清洗过程中的错误不会影响原始数据

可扩展性：新增清洗步骤只需添加到管道，无需修改现有代码

具体需求
文件路径
text
wechat_backend/v2/cleaning/
├── __init__.py
├── pipeline.py                           # 清洗管道主类
├── steps/
│   ├── __init__.py
│   ├── base.py                           # 清洗步骤基类
│   ├── text_extractor.py                  # 文本提取步骤
│   ├── entity_recognizer.py                # 实体识别步骤
│   ├── deduplicator.py                     # 去重步骤
│   ├── validator.py                        # 验证步骤
│   ├── geo_preparer.py                      # GEO数据准备步骤
│   └── quality_scorer.py                    # 质量评分步骤
├── models/
│   ├── __init__.py
│   ├── cleaned_data.py                      # 清洗后数据模型
│   └── pipeline_context.py                   # 管道上下文
├── errors.py                                # 清洗相关异常
└── config.py                                # 清洗配置

tests/unit/cleaning/
├── test_pipeline.py
├── test_text_extractor.py
├── test_entity_recognizer.py
├── test_deduplicator.py
├── test_validator.py
├── test_geo_preparer.py
└── test_quality_scorer.py

tests/integration/
└── test_cleaning_pipeline_integration.py
第一部分：数据模型定义
python
# wechat_backend/v2/cleaning/models/cleaned_data.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class EntityMention:
    """实体提及信息"""
    entity_name: str                         # 实体名称（品牌/竞品）
    entity_type: str                          # 实体类型：'brand', 'competitor'
    start_pos: int                             # 在文本中的起始位置
    end_pos: int                               # 在文本中的结束位置
    confidence: float = 1.0                    # 识别置信度
    context: Optional[str] = None               # 上下文片段


@dataclass
class GeoPreparedData:
    """GEO分析准备数据"""
    text_length: int                           # 文本长度
    sentence_count: int                         # 句子数量
    has_brand_mention: bool = False              # 是否提到品牌
    brand_positions: List[int] = field(default_factory=list)  # 品牌出现位置
    competitor_mentions: Dict[str, int] = field(default_factory=dict)  # 竞品提及次数
    language: str = 'zh'                         # 语言
    contains_numbers: bool = False                # 是否包含数字
    contains_urls: bool = False                   # 是否包含URL


@dataclass
class QualityScore:
    """质量评分"""
    overall_score: float = 0.0                    # 总体评分 0-100
    length_score: float = 0.0                      # 长度评分
    completeness_score: float = 0.0                 # 完整性评分
    relevance_score: float = 0.0                    # 相关性评分
    issues: List[str] = field(default_factory=list)  # 发现的问题
    warnings: List[str] = field(default_factory=list) # 警告信息


@dataclass
class CleanedData:
    """
    清洗后数据模型

    这是经过清洗管道处理后输出的标准格式，
    后续的统计分析都基于此模型。
    """
    # 原始引用
    execution_id: str
    report_id: int
    result_id: Optional[int] = None                 # 关联的原始结果ID

    # 基础信息
    brand: str
    question: str
    model: str

    # 清洗后的文本
    cleaned_text: str                               # 清洗后的纯文本
    original_text: str                              # 原始文本（备份）

    # 实体信息
    entities: List[EntityMention] = field(default_factory=list)

    # GEO准备数据
    geo_data: Optional[GeoPreparedData] = None

    # 质量评分
    quality: Optional[QualityScore] = None

    # 清洗元数据
    cleaning_version: str = '1.0'
    steps_applied: List[str] = field(default_factory=list)  # 应用的清洗步骤
    warnings: List[str] = field(default_factory=list)       # 清洗过程中的警告
    errors: List[str] = field(default_factory=list)         # 清洗过程中的错误

    # 时间信息
    cleaned_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于存储）"""
        return {
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'result_id': self.result_id,
            'brand': self.brand,
            'question': self.question,
            'model': self.model,
            'cleaned_text': self.cleaned_text,
            'original_text': self.original_text,
            'entities': [
                {
                    'entity_name': e.entity_name,
                    'entity_type': e.entity_type,
                    'confidence': e.confidence
                }
                for e in self.entities
            ],
            'geo_data': {
                'text_length': self.geo_data.text_length,
                'sentence_count': self.geo_data.sentence_count,
                'has_brand_mention': self.geo_data.has_brand_mention,
                'brand_positions': self.geo_data.brand_positions,
                'competitor_mentions': self.geo_data.competitor_mentions,
                'language': self.geo_data.language
            } if self.geo_data else None,
            'quality': {
                'overall_score': self.quality.overall_score,
                'length_score': self.quality.length_score,
                'completeness_score': self.quality.completeness_score,
                'relevance_score': self.quality.relevance_score,
                'issues': self.quality.issues,
                'warnings': self.quality.warnings
            } if self.quality else None,
            'cleaning_version': self.cleaning_version,
            'steps_applied': self.steps_applied,
            'warnings': self.warnings,
            'errors': self.errors,
            'cleaned_at': self.cleaned_at.isoformat(),
        }

    @classmethod
    def from_response(cls, response: Any, execution_id: str, report_id: int, brand: str, question: str, model: str) -> 'CleanedData':
        """
        从原始响应创建清洗数据对象（初始化）

        注意：这只是创建空壳，真正的清洗由管道完成
        """
        return cls(
            execution_id=execution_id,
            report_id=report_id,
            brand=brand,
            question=question,
            model=model,
            cleaned_text='',
            original_text='',
        )
python
# wechat_backend/v2/cleaning/models/pipeline_context.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class PipelineContext:
    """
    清洗管道上下文

    在管道执行过程中传递的数据和状态
    """
    # 输入数据
    execution_id: str
    report_id: int
    brand: str
    question: str
    model: str

    # 原始响应
    raw_response: Dict[str, Any]                # 从AIResponse.raw_response
    response_content: str                        # 从AIResponse.content

    # 清洗过程中的中间数据
    intermediate_data: Dict[str, Any] = field(default_factory=dict)

    # 当前清洗步骤
    current_step: str = ''
    steps_completed: List[str] = field(default_factory=list)

    # 问题和警告
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 配置
    config: Dict[str, Any] = field(default_factory=dict)

    # 开始时间
    started_at: datetime = field(default_factory=datetime.now)

    def add_step_result(self, step_name: str, data: Dict[str, Any]):
        """添加步骤结果到中间数据"""
        self.intermediate_data[step_name] = data
        self.steps_completed.append(step_name)
        self.current_step = step_name

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(f"[{self.current_step}] {message}")

    def add_error(self, message: str):
        """添加错误"""
        self.errors.append(f"[{self.current_step}] {message}")

    def get_intermediate(self, step_name: str, key: str, default=None):
        """获取中间数据"""
        step_data = self.intermediate_data.get(step_name, {})
        return step_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志）"""
        return {
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'brand': self.brand,
            'model': self.model,
            'current_step': self.current_step,
            'steps_completed': self.steps_completed,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'duration_ms': (datetime.now() - self.started_at).total_seconds() * 1000,
        }
第二部分：异常定义
python
# wechat_backend/v2/cleaning/errors.py

class CleaningError(Exception):
    """清洗基础异常"""

    def __init__(self, message: str, execution_id: str, step: str = None):
        self.message = message
        self.execution_id = execution_id
        self.step = step
        super().__init__(f"[{execution_id}][{step or 'unknown'}] {message}")


class TextExtractionError(CleaningError):
    """文本提取异常"""
    pass


class EntityRecognitionError(CleaningError):
    """实体识别异常"""
    pass


class ValidationError(CleaningError):
    """验证异常"""
    pass


class QualityScoringError(CleaningError):
    """质量评分异常"""
    pass


class PipelineConfigurationError(CleaningError):
    """管道配置异常"""
    pass


class StepExecutionError(CleaningError):
    """步骤执行异常"""
    pass
第三部分：清洗步骤基类
python
# wechat_backend/v2/cleaning/steps/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import StepExecutionError


class CleaningStep(ABC):
    """
    清洗步骤基类

    所有具体的清洗步骤必须继承此类并实现 process 方法。
    每个步骤应该是：
    1. 幂等的 - 多次执行结果相同
    2. 无副作用的 - 不修改原始数据
    3. 可配置的 - 通过配置控制行为
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化清洗步骤

        Args:
            name: 步骤名称（用于日志和追踪）
            config: 步骤特定配置
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        执行清洗步骤

        Args:
            context: 管道上下文（包含当前状态和中间数据）

        Returns:
            更新后的管道上下文

        Raises:
            StepExecutionError: 步骤执行失败
        """
        pass

    def validate_input(self, context: PipelineContext) -> bool:
        """
        验证输入数据是否满足步骤要求

        子类可重写此方法添加特定验证逻辑
        """
        return True

    def should_skip(self, context: PipelineContext) -> bool:
        """
        判断是否应该跳过此步骤

        子类可重写此方法实现条件执行
        """
        return False

    def get_step_result(self, context: PipelineContext) -> Dict[str, Any]:
        """
        从上下文中获取本步骤之前的结果

        用于步骤间的数据传递
        """
        return context.intermediate_data.get(self.name, {})

    def save_step_result(self, context: PipelineContext, data: Dict[str, Any]):
        """
        保存本步骤的结果到上下文
        """
        context.add_step_result(self.name, data)

    def log_step_start(self, context: PipelineContext):
        """记录步骤开始（结构化日志）"""
        logger.info(
            "cleaning_step_started",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'config': self.config
            }
        )

    def log_step_complete(self, context: PipelineContext, duration_ms: float):
        """记录步骤完成"""
        logger.info(
            "cleaning_step_completed",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'duration_ms': duration_ms,
                'warning_count': len(context.warnings),
                'error_count': len(context.errors),
            }
        )

    def log_step_error(self, context: PipelineContext, error: Exception):
        """记录步骤错误"""
        logger.error(
            "cleaning_step_failed",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'error': str(error),
                'error_type': type(error).__name__,
            }
        )
第四部分：文本提取步骤
python
# wechat_backend/v2/cleaning/steps/text_extractor.py

import re
from typing import Dict, Any
import html

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import TextExtractionError


class TextExtractorStep(CleaningStep):
    """
    文本提取步骤

    从原始响应中提取纯文本，处理：
    1. HTML标签
    2. 转义字符
    3. 多余的空格和换行
    4. 特殊字符
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('text_extractor', config)

        # 默认配置
        self.config.setdefault('strip_html', True)
        self.config.setdefault('unescape_html', True)
        self.config.setdefault('normalize_whitespace', True)
        self.config.setdefault('max_length', 10000)  # 最大文本长度
        self.config.setdefault('min_length', 10)     # 最小有效文本长度

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行文本提取"""

        try:
            # 1. 获取原始文本（从 context.response_content）
            raw_text = context.response_content

            if not raw_text:
                context.add_warning("Empty response content")
                context.intermediate_data[self.name] = {
                    'extracted_text': '',
                    'original_length': 0,
                    'cleaned_length': 0
                }
                return context

            original_length = len(raw_text)

            # 2. 应用清洗规则
            cleaned_text = raw_text

            if self.config['strip_html']:
                cleaned_text = self._strip_html(cleaned_text)

            if self.config['unescape_html']:
                cleaned_text = self._unescape_html(cleaned_text)

            if self.config['normalize_whitespace']:
                cleaned_text = self._normalize_whitespace(cleaned_text)

            # 3. 长度限制
            if len(cleaned_text) > self.config['max_length']:
                cleaned_text = cleaned_text[:self.config['max_length']]
                context.add_warning(f"Text truncated from {len(cleaned_text)} to {self.config['max_length']}")

            # 4. 检查最小长度
            if len(cleaned_text) < self.config['min_length']:
                context.add_warning(f"Cleaned text too short: {len(cleaned_text)} chars")

            # 5. 保存结果
            result = {
                'extracted_text': cleaned_text,
                'original_length': original_length,
                'cleaned_length': len(cleaned_text),
                'truncated': len(cleaned_text) > self.config['max_length'],
            }

            self.save_step_result(context, result)

            # 同时更新 context 中的 response_content 为清洗后的文本
            # 这样后续步骤可以使用清洗后的文本
            context.response_content = cleaned_text

            return context

        except Exception as e:
            context.add_error(f"Text extraction failed: {str(e)}")
            raise TextExtractionError(
                f"Failed to extract text: {str(e)}",
                execution_id=context.execution_id,
                step=self.name
            )

    def _strip_html(self, text: str) -> str:
        """去除 HTML 标签"""
        # 简单的 HTML 标签去除
        text = re.sub(r'<[^>]+>', ' ', text)
        return text

    def _unescape_html(self, text: str) -> str:
        """反转义 HTML 实体"""
        return html.unescape(text)

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将多个空白字符替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text

    def validate_input(self, context: PipelineContext) -> bool:
        """验证输入"""
        if not context.response_content:
            context.add_warning("No response content to extract")
            return False
        return True
第五部分：实体识别步骤
python
# wechat_backend/v2/cleaning/steps/entity_recognizer.py

import re
from typing import List, Dict, Any, Set
from collections import defaultdict

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.models.cleaned_data import EntityMention
from wechat_backend.v2.cleaning.errors import EntityRecognitionError


class EntityRecognizerStep(CleaningStep):
    """
    实体识别步骤

    识别文本中的品牌和竞品名称，记录出现位置。
    使用简单的字符串匹配（后续可升级为NLP）。
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('entity_recognizer', config)

        # 默认配置
        self.config.setdefault('case_sensitive', False)
        self.config.setdefault('min_confidence', 0.8)
        self.config.setdefault('enable_partial_match', False)
        self.config.setdefault('max_entities', 100)  # 最多识别的实体数

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行实体识别"""

        try:
            # 1. 获取清洗后的文本
            text = context.response_content
            if not text:
                context.add_warning("Empty text for entity recognition")
                return context

            # 2. 获取要识别的实体列表
            # 主品牌
            main_brand = context.brand

            # 竞品（需要从配置或上下文中获取）
            # 这里简化处理，实际可能需要从 report 表查询
            competitors = self._get_competitors(context)

            # 3. 执行识别
            entities = []

            # 识别主品牌
            brand_mentions = self._find_entity(text, main_brand, 'brand')
            entities.extend(brand_mentions)

            # 识别竞品
            for competitor in competitors:
                competitor_mentions = self._find_entity(text, competitor, 'competitor')
                entities.extend(competitor_mentions)

            # 4. 去重和排序
            entities = self._deduplicate_entities(entities)
            entities.sort(key=lambda e: e.start_pos)

            # 5. 限制数量
            if len(entities) > self.config['max_entities']:
                entities = entities[:self.config['max_entities']]
                context.add_warning(f"Entity count truncated to {self.config['max_entities']}")

            # 6. 保存结果
            result = {
                'entities': [
                    {
                        'entity_name': e.entity_name,
                        'entity_type': e.entity_type,
                        'start_pos': e.start_pos,
                        'end_pos': e.end_pos,
                        'confidence': e.confidence,
                        'context': e.context
                    }
                    for e in entities
                ],
                'total_entities': len(entities),
                'brand_mentions': sum(1 for e in entities if e.entity_type == 'brand'),
                'competitor_mentions': sum(1 for e in entities if e.entity_type == 'competitor'),
            }

            self.save_step_result(context, result)

            return context

        except Exception as e:
            context.add_error(f"Entity recognition failed: {str(e)}")
            raise EntityRecognitionError(
                f"Failed to recognize entities: {str(e)}",
                execution_id=context.execution_id,
                step=self.name
            )

    def _find_entity(self, text: str, entity_name: str, entity_type: str) -> List[EntityMention]:
        """在文本中查找实体"""
        mentions = []

        if not entity_name or len(entity_name) < 2:
            return mentions

        search_name = entity_name.lower() if not self.config['case_sensitive'] else entity_name
        search_text = text.lower() if not self.config['case_sensitive'] else text

        # 简单字符串查找
        start = 0
        while True:
            pos = search_text.find(search_name, start)
            if pos == -1:
                break

            # 计算上下文（前后各20个字符）
            context_start = max(0, pos - 20)
            context_end = min(len(text), pos + len(entity_name) + 20)
            context = text[context_start:context_end]

            mention = EntityMention(
                entity_name=entity_name,
                entity_type=entity_type,
                start_pos=pos,
                end_pos=pos + len(entity_name),
                confidence=1.0,
                context=context
            )
            mentions.append(mention)

            start = pos + len(entity_name)

        return mentions

    def _get_competitors(self, context: PipelineContext) -> List[str]:
        """获取竞品列表"""
        # 从上下文中获取竞品信息
        # 实际实现可能需要从数据库查询
        # 这里简化为从 config 读取
        return self.config.get('competitors', [])

    def _deduplicate_entities(self, entities: List[EntityMention]) -> List[EntityMention]:
        """去重（相同位置的相同实体只保留一个）"""
        seen = set()
        unique = []

        for e in entities:
            key = (e.start_pos, e.end_pos, e.entity_name)
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def should_skip(self, context: PipelineContext) -> bool:
        """如果没有竞品配置，可能跳过"""
        return len(self._get_competitors(context)) == 0
第六部分：去重步骤
python
# wechat_backend/v2/cleaning/steps/deduplicator.py

import hashlib
from typing import Dict, Any, Set

from wechat_backend/v2/cleaning/steps/base import CleaningStep
from wechat_backend/v2/cleaning/models/pipeline_context import PipelineContext


class DeduplicatorStep(CleaningStep):
    """
    去重步骤

    检测并标记重复内容，避免重复统计。
    使用 SimHash 或简单哈希进行相似度检测。
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('deduplicator', config)

        # 默认配置
        self.config.setdefault('method', 'exact_hash')  # exact_hash, simhash
        self.config.setdefault('similarity_threshold', 0.95)
        self.config.setdefault('store_hashes', True)

        # 用于跨任务去重的哈希存储（实际应该用Redis）
        self._hash_store: Set[str] = set()

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行去重检测"""

        # 1. 获取文本
        text = context.response_content
        if not text:
            context.add_warning("Empty text for deduplication")
            return context

        # 2. 计算哈希
        if self.config['method'] == 'exact_hash':
            content_hash = self._compute_exact_hash(text)
        else:
            content_hash = self._compute_simhash(text)

        # 3. 检查是否重复
        is_duplicate = self._check_duplicate(content_hash, context)

        # 4. 保存结果
        result = {
            'content_hash': content_hash,
            'is_duplicate': is_duplicate,
            'method': self.config['method'],
        }

        self.save_step_result(context, result)

        # 5. 如果是重复内容，添加警告
        if is_duplicate:
            context.add_warning("Duplicate content detected")

        return context

    def _compute_exact_hash(self, text: str) -> str:
        """计算精确哈希"""
        # 归一化文本（去除空格、标点等）
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _compute_simhash(self, text: str) -> str:
        """计算 SimHash（简化版）"""
        # 简化实现，实际应使用真正的 SimHash 算法
        # 这里用分块哈希作为替代
        import hashlib

        chunks = self._split_into_chunks(text, 50)
        hashes = []

        for chunk in chunks:
            h = hashlib.md5(chunk.encode('utf-8')).hexdigest()
            hashes.append(h)

        # 合并哈希
        combined = ''.join(sorted(hashes))
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _normalize_text(self, text: str) -> str:
        """归一化文本（去重前预处理）"""
        # 去除标点符号
        import string
        text = text.translate(str.maketrans('', '', string.punctuation))
        # 转为小写
        text = text.lower()
        # 去除多余空白
        text = ' '.join(text.split())
        return text

    def _split_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """将文本分块"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def _check_duplicate(self, content_hash: str, context: PipelineContext) -> bool:
        """检查是否重复"""
        # 检查是否在当前上下文中重复
        if content_hash in self._hash_store:
            return True

        # 存储哈希供后续使用
        if self.config['store_hashes']:
            self._hash_store.add(content_hash)

        return False

    def should_skip(self, context: PipelineContext) -> bool:
        """如果文本为空，跳过"""
        return not context.response_content
第七部分：验证步骤
python
# wechat_backend/v2/cleaning/steps/validator.py

import re
from typing import Dict, Any, List

from wechat_backend/v2.cleaning.steps.base import CleaningStep
from wechat_backend/v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend/v2.cleaning.errors import ValidationError


class ValidatorStep(CleaningStep):
    """
    验证步骤

    验证清洗后的数据是否符合预期格式和质量要求。
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('validator', config)

        # 默认验证规则
        self.config.setdefault('rules', [
            'min_length',
            'max_length',
            'no_empty',
            'valid_encoding',
            'no_invalid_chars'
        ])

        self.config.setdefault('min_length', 10)
        self.config.setdefault('max_length', 10000)
        self.config.setdefault('invalid_chars', ['\x00', '\x01', '\x02'])  # 控制字符

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行验证"""

        # 1. 获取文本
        text = context.response_content
        if not text:
            context.add_warning("Empty text for validation")
            return context

        # 2. 执行各项验证
        validation_results = {}
        issues = []

        for rule in self.config['rules']:
            rule_method = getattr(self, f'_validate_{rule}', None)
            if rule_method:
                is_valid, message = rule_method(text, context)
                validation_results[rule] = {
                    'passed': is_valid,
                    'message': message
                }
                if not is_valid:
                    issues.append(f"{rule}: {message}")

        # 3. 保存结果
        result = {
            'validation_results': validation_results,
            'is_valid': len(issues) == 0,
            'issues': issues,
            'issue_count': len(issues),
        }

        self.save_step_result(context, result)

        # 4. 如果有问题，添加到上下文警告
        for issue in issues:
            context.add_warning(f"Validation issue: {issue}")

        return context

    def _validate_min_length(self, text: str, context: PipelineContext) -> tuple[bool, str]:
        """验证最小长度"""
        min_len = self.config['min_length']
        if len(text) < min_len:
            return False, f"Text too short: {len(text)} < {min_len}"
        return True, "OK"

    def _validate_max_length(self, text: str, context: PipelineContext) -> tuple[bool, str]:
        """验证最大长度"""
        max_len = self.config['max_length']
        if len(text) > max_len:
            return False, f"Text too long: {len(text)} > {max_len}"
        return True, "OK"

    def _validate_no_empty(self, text: str, context: PipelineContext) -> tuple[bool, str]:
        """验证非空"""
        if not text or not text.strip():
            return False, "Text is empty after stripping"
        return True, "OK"

    def _validate_valid_encoding(self, text: str, context: PipelineContext) -> tuple[bool, str]:
        """验证编码有效"""
        try:
            # 尝试编码再解码，检查是否一致
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            if decoded != text:
                return False, "Encoding mismatch"
            return True, "OK"
        except UnicodeError as e:
            return False, f"Invalid encoding: {str(e)}"

    def _validate_no_invalid_chars(self, text: str, context: PipelineContext) -> tuple[bool, str]:
        """验证无非法字符"""
        invalid_chars = self.config['invalid_chars']
        found = []

        for char in invalid_chars:
            if char in text:
                found.append(repr(char))

        if found:
            return False, f"Found invalid characters: {', '.join(found)}"
        return True, "OK"

    def should_skip(self, context: PipelineContext) -> bool:
        """如果文本为空，跳过"""
        return not context.response_content
第八部分：GEO数据准备步骤
python
# wechat_backend/v2/cleaning/steps/geo_preparer.py

import re
from typing import Dict, Any, List
from collections import Counter

from wechat_backend/v2.cleaning.steps.base import CleaningStep
from wechat_backend/v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend/v2.cleaning.models.cleaned_data import GeoPreparedData


class GeoPreparerStep(CleaningStep):
    """
    GEO数据准备步骤
    为后续的GEO（生成式引擎优化）分析准备基础数据，
    包括文本特征提取、品牌位置记录等。
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('geo_preparer', config)

        # 默认配置
        self.config.setdefault('detect_language', True)
        self.config.setdefault('extract_urls', True)
        self.config.setdefault('extract_numbers', True)
        self.config.setdefault('split_sentences', True)
        self.config.setdefault('max_sentences', 100)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行GEO数据准备"""

        # 1. 获取文本和实体信息
        text = context.response_content
        if not text:
            context.add_warning("Empty text for GEO preparation")
            return context

        # 2. 从实体识别步骤获取品牌位置
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        entities = entity_result.get('entities', [])

        # 3. 提取文本特征
        geo_data = GeoPreparedData(
            text_length=len(text),
            sentence_count=self._count_sentences(text) if self.config['split_sentences'] else 1,
            has_brand_mention=False,
            brand_positions=[],
            competitor_mentions={},
            language=self._detect_language(text) if self.config['detect_language'] else 'zh',
            contains_numbers=self._contains_numbers(text) if self.config['extract_numbers'] else False,
            contains_urls=self._contains_urls(text) if self.config['extract_urls'] else False,
        )

        # 4. 记录品牌位置
        for entity in entities:
            if entity['entity_type'] == 'brand':
                geo_data.has_brand_mention = True
                geo_data.brand_positions.append(entity['start_pos'])
            elif entity['entity_type'] == 'competitor':
                comp_name = entity['entity_name']
                geo_data.competitor_mentions[comp_name] = \
                    geo_data.competitor_mentions.get(comp_name, 0) + 1

        # 5. 保存结果
        result = {
            'geo_data': {
                'text_length': geo_data.text_length,
                'sentence_count': geo_data.sentence_count,
                'has_brand_mention': geo_data.has_brand_mention,
                'brand_positions': geo_data.brand_positions,
                'competitor_mentions': geo_data.competitor_mentions,
                'language': geo_data.language,
                'contains_numbers': geo_data.contains_numbers,
                'contains_urls': geo_data.contains_urls,
            }
        }

        self.save_step_result(context, result)

        return context

    def _count_sentences(self, text: str) -> int:
        """统计句子数量"""
        # 简单按句号、感叹号、问号分割
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > self.config['max_sentences']:
            return self.config['max_sentences']

        return len(sentences)

    def _detect_language(self, text: str) -> str:
        """检测语言（简化版）"""
        # 检查是否包含中文字符
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        # 检查是否主要为英文字母
        elif re.match(r'^[a-zA-Z\s,.!?]+$', text[:100]):
            return 'en'
        else:
            return 'unknown'

    def _contains_numbers(self, text: str) -> bool:
        """是否包含数字"""
        return bool(re.search(r'\d+', text))

    def _contains_urls(self, text: str) -> bool:
        """是否包含URL"""
        url_pattern = r'https?://[^\s]+|www\.[^\s]+'
        return bool(re.search(url_pattern, text))

    def should_skip(self, context: PipelineContext) -> bool:
        """如果没有文本，跳过"""
        return not context.response_content
第九部分：质量评分步骤
python
# wechat_backend/v2/cleaning/steps/quality_scorer.py

from typing import Dict, Any, List

from wechat_backend/v2.cleaning.steps.base import CleaningStep
from wechat_backend/v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend/v2.cleaning.models.cleaned_data import QualityScore


class QualityScorerStep(CleaningStep):
    """
    质量评分步骤

    基于多个维度对清洗后的数据进行质量评分：
    1. 长度评分 - 文本长度是否合适
    2. 完整性评分 - 是否包含必要信息
    3. 相关性评分 - 是否与问题相关（简化版）
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('quality_scorer', config)

        # 评分权重配置
        self.config.setdefault('weights', {
            'length': 0.3,
            'completeness': 0.4,
            'relevance': 0.3,
        })

        self.config.setdefault('ideal_length', 500)  # 理想长度
        self.config.setdefault('min_acceptable_length', 50)
        self.config.setdefault('max_acceptable_length', 2000)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """执行质量评分"""

        # 1. 获取文本
        text = context.response_content
        if not text:
            context.add_warning("Empty text for quality scoring")
            return context

        # 2. 获取其他步骤的结果
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        validation_result = context.intermediate_data.get('validator', {})

        # 3. 计算各维度评分
        length_score = self._calculate_length_score(text)
        completeness_score = self._calculate_completeness_score(text, entity_result)
        relevance_score = self._calculate_relevance_score(text, context)

        # 4. 综合评分
        weights = self.config['weights']
        overall_score = (
            length_score * weights['length'] +
            completeness_score * weights['completeness'] +
            relevance_score * weights['relevance']
        )

        # 5. 收集问题和警告
        issues = []
        warnings = []

        if length_score < 30:
            issues.append("Text too short")
        elif length_score > 95:
            warnings.append("Text may be too long")

        if completeness_score < 50:
            issues.append("Low completeness")

        if relevance_score < 30:
            issues.append("Low relevance to question")

        # 6. 从验证步骤获取已有问题
        if validation_result:
            validation_issues = validation_result.get('issues', [])
            issues.extend(validation_issues)

        # 7. 创建评分对象
        quality = QualityScore(
            overall_score=round(overall_score, 2),
            length_score=round(length_score, 2),
            completeness_score=round(completeness_score, 2),
            relevance_score=round(relevance_score, 2),
            issues=issues[:5],  # 只保留前5个问题
            warnings=warnings[:3],
        )

        # 8. 保存结果
        result = {
            'quality_score': {
                'overall': quality.overall_score,
                'length': quality.length_score,
                'completeness': quality.completeness_score,
                'relevance': quality.relevance_score,
                'issues': quality.issues,
                'warnings': quality.warnings,
            }
        }

        self.save_step_result(context, result)

        # 9. 如果有警告，添加到上下文
        for warning in warnings:
            context.add_warning(f"Quality warning: {warning}")

        return context

    def _calculate_length_score(self, text: str) -> float:
        """计算长度评分"""
        length = len(text)
        ideal = self.config['ideal_length']
        min_accept = self.config['min_acceptable_length']
        max_accept = self.config['max_acceptable_length']

        if length < min_accept:
            # 太短：线性下降
            return max(0, (length / min_accept) * 50)
        elif length > max_accept:
            # 太长：线性下降
            excess = (length - max_accept) / max_accept
            return max(0, 100 - excess * 50)
        else:
            # 在理想范围内：高斯分布
            if length <= ideal:
                return 50 + 50 * (length - min_accept) / (ideal - min_accept)
            else:
                return 100 - 50 * (length - ideal) / (max_accept - ideal)

    def _calculate_completeness_score(self, text: str, entity_result: Dict) -> float:
        """计算完整性评分"""
        score = 70  # 基础分

        # 检查是否有实体
        entities = entity_result.get('entities', [])
        if entities:
            score += 15

        # 检查文本长度
        if len(text) > 100:
            score += 15

        # 限制范围
        return min(100, max(0, score))

    def _calculate_relevance_score(self, text: str, context: PipelineContext) -> float:
        """计算相关性评分（简化版）"""
        score = 60  # 基础分

        # 检查是否包含品牌名
        if context.brand in text:
            score += 20

        # 检查是否包含问题中的关键词
        question_keywords = self._extract_keywords(context.question)
        for keyword in question_keywords:
            if keyword in text:
                score += 5

        return min(100, max(0, score))

    def _extract_keywords(self, text: str) -> List[str]:
        """从问题中提取关键词（简化）"""
        # 简单的分词（按空格和常见分隔符）
        import re
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', text)
        # 过滤太短的词
        return [w for w in words if len(w) > 1][:5]
第十部分：清洗管道主类
python
# wechat_backend/v2/cleaning/pipeline.py

import asyncio
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from wechat_backend/v2/cleaning.steps.base import CleaningStep
from wechat_backend/v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend/v2.cleaning.models.cleaned_data import CleanedData
from wechat_backend/v2.cleaning.errors import PipelineConfigurationError, StepExecutionError
from wechat_backend/v2.adapters.models import AIResponse


class CleaningPipeline:
    """
    清洗管道主类

    负责编排和执行多个清洗步骤，将原始AI响应转换为结构化数据。
    支持：
    1. 步骤的动态配置和编排
    2. 并行/串行执行控制
    3. 错误处理和恢复
    4. 监控和日志
    """

    def __init__(self, name: str = "default", config: Optional[Dict[str, Any]] = None):
        """
        初始化清洗管道

        Args:
            name: 管道名称
            config: 管道级配置
        """
        self.name = name
        self.config = config or {}
        self.steps: List[CleaningStep] = []

        # 默认配置
        self.config.setdefault('stop_on_error', True)      # 错误时停止
        self.config.setdefault('continue_on_warning', True) # 警告时继续
        self.config.setdefault('parallel_steps', False)    # 是否并行执行步骤
        self.config.setdefault('timeout', 30)              # 总超时时间

    def add_step(self, step: CleaningStep) -> 'CleaningPipeline':
        """添加清洗步骤"""
        self.steps.append(step)
        return self

    def add_steps(self, steps: List[CleaningStep]) -> 'CleaningPipeline':
        """批量添加清洗步骤"""
        self.steps.extend(steps)
        return self

    def insert_step(self, index: int, step: CleaningStep) -> 'CleaningPipeline':
        """在指定位置插入步骤"""
        self.steps.insert(index, step)
        return self

    def remove_step(self, step_name: str) -> bool:
        """移除指定名称的步骤"""
        for i, step in enumerate(self.steps):
            if step.name == step_name:
                del self.steps[i]
                return True
        return False

    async def execute(
        self,
        execution_id: str,
        report_id: int,
        brand: str,
        question: str,
        model: str,
        response: AIResponse,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> CleanedData:
        """
        执行清洗管道

        Args:
            execution_id: 执行ID
            report_id: 报告ID
            brand: 品牌名称
            question: 问题
            model: AI模型
            response: 标准化的AI响应
            additional_context: 额外的上下文信息

        Returns:
            清洗后的数据

        Raises:
            PipelineConfigurationError: 管道配置错误
            StepExecutionError: 步骤执行失败
        """

        if not self.steps:
            raise PipelineConfigurationError(
                "No steps configured in pipeline",
                execution_id=execution_id
            )

        # 1. 创建上下文
        context = PipelineContext(
            execution_id=execution_id,
            report_id=report_id,
            brand=brand,
            question=question,
            model=model,
            raw_response=response.raw_response or {},
            response_content=response.content,
            config=self.config,
        )

        # 添加额外上下文
        if additional_context:
            context.intermediate_data.update(additional_context)

        # 2. 记录开始
        start_time = time.time()
        logger.info(
            "cleaning_pipeline_started",
            extra={
                'pipeline': self.name,
                'execution_id': execution_id,
                'step_count': len(self.steps),
            }
        )

        # 3. 串行执行步骤
        try:
            for step in self.steps:
                # 检查是否应该跳过
                if step.should_skip(context):
                    logger.info(
                        "step_skipped",
                        extra={'step': step.name, 'execution_id': execution_id}
                    )
                    continue

                # 验证输入
                if not step.validate_input(context):
                    context.add_warning(f"Step {step.name} input validation failed")
                    if self.config['stop_on_error']:
                        break
                    continue

                # 执行步骤
                step_start = time.time()
                try:
                    context = await step.process(context)
                    step_duration = (time.time() - step_start) * 1000

                    logger.info(
                        "step_completed",
                        extra={
                            'step': step.name,
                            'execution_id': execution_id,
                            'duration_ms': step_duration,
                        }
                    )

                except Exception as e:
                    step_duration = (time.time() - step_start) * 1000
                    logger.error(
                        "step_failed",
                        extra={
                            'step': step.name,
                            'execution_id': execution_id,
                            'duration_ms': step_duration,
                            'error': str(e),
                        }
                    )

                    context.add_error(f"Step {step.name} failed: {str(e)}")

                    if self.config['stop_on_error']:
                        raise StepExecutionError(
                            f"Step {step.name} failed: {str(e)}",
                            execution_id=execution_id,
                            step=step.name
                        ) from e

                    # 继续执行下一个步骤
                    continue

            # 4. 构建清洗后数据
            cleaned_data = self._build_cleaned_data(context)

            # 5. 记录完成
            total_duration = (time.time() - start_time) * 1000
            logger.info(
                "cleaning_pipeline_completed",
                extra={
                    'pipeline': self.name,
                    'execution_id': execution_id,
                    'duration_ms': total_duration,
                    'steps_completed': len(context.steps_completed),
                    'error_count': len(context.errors),
                    'warning_count': len(context.warnings),
                }
            )

            return cleaned_data

        except Exception as e:
            logger.error(
                "cleaning_pipeline_failed",
                extra={
                    'pipeline': self.name,
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            raise

    async def execute_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[CleanedData]:
        """
        批量执行清洗

        Args:
            items: 每个元素包含 execution_id, report_id, brand, question, model, response

        Returns:
            清洗后数据列表
        """
        tasks = []
        for item in items:
            task = self.execute(
                execution_id=item['execution_id'],
                report_id=item['report_id'],
                brand=item['brand'],
                question=item['question'],
                model=item['model'],
                response=item['response']
            )
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    def _build_cleaned_data(self, context: PipelineContext) -> CleanedData:
        """从上下文构建清洗后数据"""

        # 从各个步骤获取结果
        text_result = context.intermediate_data.get('text_extractor', {})
        entity_result = context.intermediate_data.get('entity_recognizer', {})
        geo_result = context.intermediate_data.get('geo_preparer', {})
        quality_result = context.intermediate_data.get('quality_scorer', {})

        # 构建实体列表
        entities = []
        for e in entity_result.get('entities', []):
            from .models.cleaned_data import EntityMention
            entities.append(EntityMention(
                entity_name=e['entity_name'],
                entity_type=e['entity_type'],
                start_pos=e['start_pos'],
                end_pos=e['end_pos'],
                confidence=e.get('confidence', 1.0),
                context=e.get('context')
            ))

        # 构建GEO数据
        geo_data_dict = geo_result.get('geo_data', {})
        from .models.cleaned_data import GeoPreparedData
        geo_data = GeoPreparedData(
            text_length=geo_data_dict.get('text_length', 0),
            sentence_count=geo_data_dict.get('sentence_count', 1),
            has_brand_mention=geo_data_dict.get('has_brand_mention', False),
            brand_positions=geo_data_dict.get('brand_positions', []),
            competitor_mentions=geo_data_dict.get('competitor_mentions', {}),
            language=geo_data_dict.get('language', 'zh'),
            contains_numbers=geo_data_dict.get('contains_numbers', False),
            contains_urls=geo_data_dict.get('contains_urls', False),
        )

        # 构建质量评分
        quality_dict = quality_result.get('quality_score', {})
        from .models.cleaned_data import QualityScore
        quality = QualityScore(
            overall_score=quality_dict.get('overall', 0),
            length_score=quality_dict.get('length', 0),
            completeness_score=quality_dict.get('completeness', 0),
            relevance_score=quality_dict.get('relevance', 0),
            issues=quality_dict.get('issues', []),
            warnings=quality_dict.get('warnings', []),
        )

        # 构建最终数据
        return CleanedData(
            execution_id=context.execution_id,
            report_id=context.report_id,
            brand=context.brand,
            question=context.question,
            model=context.model,
            cleaned_text=context.response_content,
            original_text=text_result.get('original_text', context.response_content),
            entities=entities,
            geo_data=geo_data,
            quality=quality,
            cleaning_version='1.0',
            steps_applied=context.steps_completed,
            warnings=context.warnings,
            errors=context.errors,
        )

    def get_step_names(self) -> List[str]:
        """获取所有步骤名称"""
        return [step.name for step in self.steps]

    def get_step_by_name(self, name: str) -> Optional[CleaningStep]:
        """根据名称获取步骤"""
        for step in self.steps:
            if step.name == name:
                return step
        return None


# 预定义常用管道
def create_default_pipeline() -> CleaningPipeline:
    """创建默认清洗管道"""
    from .steps.text_extractor import TextExtractorStep
    from .steps.entity_recognizer import EntityRecognizerStep
    from .steps.deduplicator import DeduplicatorStep
    from .steps.validator import ValidatorStep
    from .steps.geo_preparer import GeoPreparerStep
    from .steps.quality_scorer import QualityScorerStep

    pipeline = CleaningPipeline("default")
    pipeline.add_steps([
        TextExtractorStep(),
        ValidatorStep(),
        EntityRecognizerStep(),
        DeduplicatorStep(),
        GeoPreparerStep(),
        QualityScorerStep(),
    ])

    return pipeline


def create_minimal_pipeline() -> CleaningPipeline:
    """创建最小清洗管道（只做必要清洗）"""
    from .steps.text_extractor import TextExtractorStep
    from .steps.validator import ValidatorStep

    pipeline = CleaningPipeline("minimal")
    pipeline.add_steps([
        TextExtractorStep(),
        ValidatorStep(),
    ])

    return pipeline
第十一部分：与诊断服务集成
python
# wechat_backend/v2/services/diagnosis_service.py（需要修改）

from wechat_backend.v2.cleaning.pipeline import create_default_pipeline
from wechat_backend.v2.cleaning.models.cleaned_data import CleanedData

class DiagnosisService:
    """诊断服务（集成清洗管道）"""

    def __init__(self):
        # ... 其他初始化
        self.cleaning_pipeline = create_default_pipeline()

    async def execute_ai_call(
        self,
        execution_id: str,
        report_id: int,
        brand: str,
        question: str,
        model: str,
        prompt: str
    ) -> Dict:
        """执行单个 AI 调用并进行清洗"""

        # 1. 获取适配器
        adapter = get_adapter(model)

        # 2. 构建请求
        request = AIRequest(prompt=prompt, model=model)

        # 3. 发送请求
        response = await adapter.send(request)

        # 4. 清洗数据
        cleaned_data = await self.cleaning_pipeline.execute(
            execution_id=execution_id,
            report_id=report_id,
            brand=brand,
            question=question,
            model=model,
            response=response
        )

        # 5. 保存清洗后的数据（可选）
        # 可以保存到专门的 cleaned_results 表

        return {
            'success': response.is_success,
            'brand': brand,
            'question': question,
            'model': model,
            'response': response.to_dict(),
            'cleaned_data': cleaned_data.to_dict(),
        }

    async def execute_batch_with_cleaning(
        self,
        execution_id: str,
        report_id: int,
        tasks: List[Dict]
    ) -> List[Dict]:
        """批量执行并清洗"""

        results = []
        for task in tasks:
            result = await self.execute_ai_call(
                execution_id=execution_id,
                report_id=report_id,
                brand=task['brand'],
                question=task['question'],
                model=task['model'],
                prompt=self._build_prompt(task['brand'], task['question'])
            )
            results.append(result)

        return results
第十二部分：特性开关配置
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
    'diagnosis_v2_ai_adapters': True,        # P2-T1已完成

    # 阶段二新增开关
    'diagnosis_v2_cleaning_pipeline': False,  # 清洗管道总开关
    'diagnosis_v2_cleaning_text_extractor': False,  # 文本提取
    'diagnosis_v2_cleaning_entity_recognizer': False,  # 实体识别
    'diagnosis_v2_cleaning_deduplicator': False,  # 去重
    'diagnosis_v2_cleaning_validator': False,  # 验证
    'diagnosis_v2_cleaning_geo_preparer': False,  # GEO准备
    'diagnosis_v2_cleaning_quality_scorer': False,  # 质量评分

    # 灰度控制
    'diagnosis_v2_gray_users': [],
    'diagnosis_v2_gray_percentage': 0,

    # 降级开关
    'diagnosis_v2_fallback_to_v1': True,
}
测试要求
单元测试覆盖场景
python
# tests/unit/cleaning/test_text_extractor.py

class TestTextExtractorStep:
    """测试文本提取步骤"""

    def test_strip_html(self):
        """测试去除HTML标签"""
        step = TextExtractorStep()
        text = "<p>Hello <b>world</b></p>"
        result = step._strip_html(text)
        assert result == " Hello  world "

    def test_unescape_html(self):
        """测试反转义HTML实体"""
        step = TextExtractorStep()
        text = "Hello &amp; world"
        result = step._unescape_html(text)
        assert result == "Hello & world"

    def test_normalize_whitespace(self):
        """测试规范化空白"""
        step = TextExtractorStep()
        text = "Hello   world\n\t test"
        result = step._normalize_whitespace(text)
        assert result == "Hello world test"

    @pytest.mark.asyncio
    async def test_process_empty_text(self):
        """测试空文本处理"""
        step = TextExtractorStep()
        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="test",
            question="test",
            model="test",
            raw_response={},
            response_content=""
        )

        result = await step.process(context)
        assert "extracted_text" in result.intermediate_data[step.name]
        assert result.intermediate_data[step.name]['extracted_text'] == ""
python
# tests/unit/cleaning/test_entity_recognizer.py

class TestEntityRecognizerStep:
    """测试实体识别步骤"""

    def test_find_entity(self):
        """测试查找实体"""
        step = EntityRecognizerStep()
        text = "苹果公司发布新款iPhone，苹果的股价上涨"

        mentions = step._find_entity(text, "苹果", "brand")
        assert len(mentions) == 2
        assert mentions[0].entity_name == "苹果"
        assert mentions[0].start_pos == 0

    @pytest.mark.asyncio
    async def test_process_with_entities(self):
        """测试处理包含实体的文本"""
        step = EntityRecognizerStep(config={'competitors': ['三星', '华为']})

        context = PipelineContext(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="test",
            model="test",
            raw_response={},
            response_content="苹果和三星在手机市场竞争，华为也有不错的表现"
        )

        result = await step.process(context)
        step_result = result.intermediate_data['entity_recognizer']
        assert step_result['total_entities'] >= 3
        assert step_result['brand_mentions'] >= 1
        assert step_result['competitor_mentions'] >= 2
python
# tests/unit/cleaning/test_pipeline.py

class TestCleaningPipeline:
    """测试清洗管道"""

    @pytest.mark.asyncio
    async def test_pipeline_execution(self):
        """测试管道执行"""
        pipeline = create_default_pipeline()

        response = AIResponse(
            content="<p>苹果公司发布新产品</p>",
            model="test",
            latency_ms=100
        )

        result = await pipeline.execute(
            execution_id="test",
            report_id=1,
            brand="苹果",
            question="测试问题",
            model="test",
            response=response
        )

        assert isinstance(result, CleanedData)
        assert result.cleaned_text == "苹果公司发布新产品"
        assert len(result.entities) > 0

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """测试管道错误处理"""
        pipeline = CleaningPipeline("test", {'stop_on_error': True})

        # 添加一个会失败的步骤
        class FailingStep(CleaningStep):
            async def process(self, context):
                raise Exception("Test error")

        pipeline.add_step(FailingStep("failing"))

        response = AIResponse(content="test", model="test", latency_ms=100)

        with pytest.raises(StepExecutionError):
            await pipeline.execute(
                execution_id="test",
                report_id=1,
                brand="test",
                question="test",
                model="test",
                response=response
            )
集成测试
python
# tests/integration/test_cleaning_pipeline_integration.py

class TestCleaningPipelineIntegration:
    """清洗管道集成测试"""

    @pytest.mark.asyncio
    async def test_pipeline_with_real_adapter(self):
        """测试与真实适配器集成"""
        # 需要 API Key 才能运行
        if not os.getenv('DEEPSEEK_API_KEY'):
            pytest.skip("DEEPSEEK_API_KEY not set")

        # 1. 获取适配器
        adapter = get_adapter('deepseek')

        # 2. 发送请求
        request = AIRequest(prompt="介绍一下苹果公司", model="deepseek-chat")
        response = await adapter.send(request)

        # 3. 清洗数据
        pipeline = create_default_pipeline()
        cleaned = await pipeline.execute(
            execution_id="integration_test",
            report_id=1,
            brand="苹果",
            question="介绍一下苹果公司",
            model="deepseek",
            response=response
        )

        # 4. 验证清洗结果
        assert cleaned.cleaned_text
        assert len(cleaned.cleaned_text) > 0
        assert cleaned.geo_data
        assert cleaned.quality
        assert cleaned.quality.overall_score > 0
输出要求
1. 完整代码实现
wechat_backend/v2/cleaning/pipeline.py

wechat_backend/v2/cleaning/steps/base.py

wechat_backend/v2/cleaning/steps/text_extractor.py

wechat_backend/v2/cleaning/steps/entity_recognizer.py

wechat_backend/v2/cleaning/steps/deduplicator.py

wechat_backend/v2/cleaning/steps/validator.py

wechat_backend/v2/cleaning/steps/geo_preparer.py

wechat_backend/v2/cleaning/steps/quality_scorer.py

wechat_backend/v2/cleaning/models/cleaned_data.py

wechat_backend/v2/cleaning/models/pipeline_context.py

wechat_backend/v2/cleaning/errors.py

wechat_backend/v2/cleaning/config.py

wechat_backend/v2/feature_flags.py（更新）

2. 测试代码
tests/unit/cleaning/test_pipeline.py

tests/unit/cleaning/test_text_extractor.py

tests/unit/cleaning/test_entity_recognizer.py

tests/unit/cleaning/test_deduplicator.py

tests/unit/cleaning/test_validator.py

tests/unit/cleaning/test_geo_preparer.py

tests/unit/cleaning/test_quality_scorer.py

tests/integration/test_cleaning_pipeline_integration.py

3. 提交信息
bash
feat(cleaning): implement data cleaning pipeline for AI responses

- Add base CleaningStep abstract class with common functionality
- Implement text extraction step (HTML stripping, whitespace normalization)
- Add entity recognition for brand and competitor mentions
- Implement deduplication using exact hash and simhash
- Add validation step with configurable rules
- Add GEO data preparation for subsequent analysis
- Implement quality scoring based on multiple dimensions
- Create pipeline orchestrator with step management
- Integrate with P2-T1 AI adapters
- Add comprehensive unit and integration tests

Closes #202
Refs: 2026-02-27-重构基线.md, 2026-02-27-重构实施路线图.md

Change-Id: I2345678901abcdef
4. PR 描述模板
markdown
## 变更说明
实现数据清洗管道，将AI原始响应转换为结构化数据，为后续统计分析做准备。

主要功能：
1. 清洗步骤基类 - 定义统一接口，支持幂等、无副作用执行
2. 文本提取 - 去除HTML、转义字符、规范化空白
3. 实体识别 - 识别品牌和竞品在文本中的位置
4. 去重检测 - 使用哈希和SimHash检测重复内容
5. 数据验证 - 验证长度、编码、非法字符等
6. GEO准备 - 提取文本特征供后续分析
7. 质量评分 - 基于多维度综合评分
8. 管道编排 - 支持步骤的动态配置和执行

## 关联文档
- 重构基线：第 2.1.2 节 - 数据清洗与统计分析
- 实施路线图：P2-T2
- 开发规范：第 2.3 节 - 函数规范、第 2.4 节 - 异常处理

## 测试计划
- [x] 单元测试已添加（覆盖率 91%）
- [x] 集成测试已添加
- [ ] 真实数据测试（需在预发布环境验证）

### 测试结果
单元测试：32 passed, 0 failed
集成测试：2 passed, 0 failed
覆盖率：91%
关键场景验证：

HTML文本清洗 ✓

实体识别准确率 ✓

重复内容检测 ✓

验证规则生效 ✓

质量评分合理 ✓

text

## 验收标准
- [x] 所有清洗步骤独立可测试
- [x] 管道支持步骤动态配置
- [x] 与P2-T1正确集成
- [x] 错误处理完善
- [x] 测试覆盖率 > 85%

## 回滚方案
关闭特性开关 `diagnosis_v2_cleaning_pipeline` 即可禁用清洗管道，系统继续使用原始数据。

```python
FEATURE_FLAGS['diagnosis_v2_cleaning_pipeline'] = False
依赖关系
依赖 P2-T1 AI适配器层（提供标准化响应）

本任务完成后，P2-T3/P2-T4 统计分析将基于清洗后的数据

text

---

## 注意事项

1. **幂等性**：每个清洗步骤必须幂等，多次执行结果相同
2. **无副作用**：不得修改原始数据，只能创建新的数据结构
3. **错误隔离**：一个步骤的失败不应影响其他步骤（除非配置为停止）
4. **性能考虑**：清洗步骤应尽量轻量，避免复杂计算
5. **可配置性**：每个步骤的行为应可通过配置调整
6. **日志记录**：关键操作和异常必须有

---

## 验证清单（交付前自查）

### 代码完整性
- [ ] 所有步骤继承自基类
- [ ] 每个步骤有清晰的职责
- [ ] 管道支持步骤动态添加/移除
- [ ] 上下文传递正确

### 功能完整性
- [ ] 文本提取正确处理HTML
- [ ] 实体识别能识别品牌和竞品
- [ ] 去重检测有效
- [ ] 验证规则可配置
- [ ] GEO数据准备完整
- [ ] 质量评分合理

### 错误处理
- [ ] 步骤执行异常被捕获
- [ ] 错误上下文完整
- [ ] 支持停止/继续两种模式

### 测试覆盖
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试通过
- [ ] 边界条件测试覆盖

### 文档
- [ ] 代码有完整 docstring
- [ ] 使用示例完整
- [ ] 配置说明清晰

