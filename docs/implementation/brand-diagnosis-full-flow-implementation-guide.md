# 品牌诊断系统完整实现流程指南

**文档编号**: IMP-DIAG-2026-03-09-001  
**创建日期**: 2026-03-09  
**更新日期**: 2026-03-09  
**版本**: 2.0.0  
**状态**: ✅ 生产就绪

---

## 执行摘要

本文档完整梳理了品牌诊断系统从 API 请求接收、AI 调用执行、结果保存、统计分析到前端展示的**端到端实现流程**。基于对现有代码的深入分析，明确了：

1. **API 请求结果记录机制** - 后端如何记录完整的诊断结果
2. **后台统计分析功能** - 各分析模块的执行顺序和依赖关系
3. **数据输出顺序** - 统计结果如何按优先级传递到前端
4. **前端展示维度** - 品牌诊断详细报告的每个展示字段的数据来源

---

## 一、系统架构概览

### 1.1 核心组件与数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           微信小程序前端                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  diagnosis.js → diagnosisService.js → pollingManager.js / WebSocket    │
│                        ↓ (HTTP 轮询 / WebSocket 推送)                     │
│  report-v2.js → reportService.js (获取完整报告)                         │
│                        ↓ 数据渲染                                        │
│  品牌分布图 / 情感分布图 / 关键词云 / 竞品分析 / 优化建议                 │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS / WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                         Flask 后端服务                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  1. 请求接收层 (diagnosis_views.py)                                     │
│     └─ 输入验证 → 执行 ID 生成 → 报告记录创建                              │
│                                                                          │
│  2. 编排调度层 (diagnosis_orchestrator.py)                              │
│     └─ 7 阶段顺序执行：初始化 → AI 调用 → 结果保存 → 验证 → 分析 → 聚合 → 完成  │
│                                                                          │
│  3. AI 调用层 (nxm_concurrent_engine_v3.py)                              │
│     └─ N 品牌 × M 模型 × Q 问题 并行执行                                   │
│                                                                          │
│  4. 结果保存层 (diagnosis_report_service.py)                            │
│     └─ 事务管理 → 批量插入 → 数据完整性验证                               │
│                                                                          │
│  5. 统计分析层 (analytics/)                                              │
│     ├─ 品牌分布分析器 (brand_distribution_analyzer.py)                   │
│     ├─ 信源分析器 (source_intelligence_processor.py)                     │
│     ├─ 竞品分析器 (interception_analyst.py)                              │
│     └─ 推荐生成器 (recommendation_generator.py)                          │
│                                                                          │
│  6. 状态管理层 (state_manager.py)                                        │
│     └─ 内存状态 + 数据库状态 双写同步                                    │
│                                                                          │
│  7. 实时推送层 (websocket_route.py / realtime_push_service.py)          │
│     └─ 进度推送 / 结果推送 / 完成通知                                    │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓ SQLite (WAL 模式)
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据库层                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  diagnosis_reports    - 诊断报告主表                                     │
│  diagnosis_results    - 诊断结果明细表 (每次 AI 调用的完整响应)             │
│  diagnosis_analysis   - 分析结果表 (品牌分析/竞争分析/推荐等)             │
│  diagnosis_snapshots  - 报告快照表 (完整报告 JSON 快照)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 诊断执行 7 阶段

| 阶段 | 名称 | 事务 | 耗时 | 输出 | 前端可见 |
|------|------|------|------|------|----------|
| 1 | 初始化 (init) | 无 | <1s | execution_id, 初始状态 | 进度 0% |
| 2 | AI 调用 (ai_fetching) | 无 | 20-40s | AI 响应结果 (内存) | 进度 30% |
| 3 | 结果保存 (results_saving) | 事务 A | 2-5s | diagnosis_results 表 | 进度 60% |
| 4 | 结果验证 (results_validating) | 无 | <1s | 验证报告 | 进度 70% |
| 5 | 后台分析 (background_analysis) | 异步 | 5-15s | diagnosis_analysis 表 | 进度 80% |
| 6 | 报告聚合 (report_aggregating) | 事务 B | 2-5s | 完整报告 JSON | 进度 90% |
| 7 | 完成 (completed) | 事务 C | <1s | 状态更新 | 进度 100% |

---

## 二、API 请求结果完整记录机制

### 2.1 结果记录的数据结构

**文件**: `backend_python/wechat_backend/v2/models/diagnosis_result.py`

每次 AI 调用的完整结果被记录到 `DiagnosisResult` 模型中，包含以下字段：

```python
@dataclass
class DiagnosisResult:
    # ========== 关联信息 ==========
    report_id: int           # 关联的报告 ID
    execution_id: str        # 任务执行 ID
    
    # ========== 查询参数 ==========
    brand: str              # 品牌名称
    question: str           # 问题内容
    model: str              # AI 模型名称
    
    # ========== 原始响应数据 ==========
    response: Dict[str, Any]        # 完整的 API 响应（JSON）
    response_text: str              # 提取的文本内容
    raw_response: Dict[str, Any]    # 完整原始响应（JSON）
    
    # ========== 响应元数据（Migration 004 新增） ==========
    response_metadata: Dict[str, Any]  # 响应元数据
    tokens_used: int                   # Token 消耗总量
    prompt_tokens: int                 # 输入 Token 数
    completion_tokens: int             # 输出 Token 数
    cached_tokens: int                 # 缓存命中 Token 数
    finish_reason: str                 # 完成原因（stop/length/error）
    request_id: str                    # API 请求 ID
    model_version: str                 # 模型版本
    reasoning_content: str             # 推理内容
    api_endpoint: str                  # API 端点
    service_tier: str                  # 服务等级
    retry_count: int                   # 重试次数
    is_fallback: bool                  # 是否降级
    
    # ========== GEO 分析数据 ==========
    geo_data: Dict[str, Any]    # GEO 分析结果
    exposure: bool              # 是否露出品牌
    sentiment: str              # 情感倾向（positive/neutral/negative）
    keywords: List[str]         # 关键词列表
    
    # ========== 质量评分 ==========
    quality_score: float        # 质量评分（0-100）
    quality_level: str          # 质量等级（high/medium/low/unknown）
    
    # ========== 性能指标 ==========
    latency_ms: int             # API 响应延迟
    
    # ========== 错误信息 ==========
    error_message: str          # 错误信息
    
    # ========== 元数据 ==========
    data_version: str           # 数据结构版本
    created_at: datetime        # 创建时间
    updated_at: datetime        # 更新时间
```

### 2.2 结果保存流程

**文件**: `backend_python/wechat_backend/services/diagnosis_orchestrator.py`

```python
async def _phase_results_saving_transaction(self, results, brand_list, ...) -> PhaseResult:
    """
    阶段 3: 结果保存（独立短事务）
    
    子事务 1: 创建报告记录
    子事务 2: 分批保存结果（每批 10 条，快速提交）
    """
    # 1. 更新状态为结果保存中
    self._update_phase_status(
        status='results_saving',
        stage='results_saving',
        progress=60,
        write_to_db=True
    )
    
    # 2. 子事务 1: 创建报告记录
    report_id = self._execute_in_transaction(
        lambda tx: tx.create_report(execution_id, user_id, config),
        operation_name='create_report'
    )
    
    # 3. 子事务 2: 分批保存结果
    result_ids = []
    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        batch_result = self._execute_in_transaction(
            lambda tx: tx.add_results_batch(report_id, execution_id, batch),
            operation_name=f'add_results_batch_{i // batch_size}'
        )
        result_ids.extend(batch_result)
    
    # 4. 验证数据完整性
    validation_result = self._validate_saved_results(report_id, expected_count)
    
    return PhaseResult(success=True, data={'saved_results': validation_result})
```

### 2.3 结果验证机制

**文件**: `backend_python/wechat_backend/services/diagnosis_orchestrator.py`

```python
async def _phase_results_validating(self, ai_results) -> PhaseResult:
    """
    阶段 4: 结果验证（只读验证，不写数据库）
    
    验证内容:
    1. 结果数量是否匹配预期
    2. 每条结果是否包含必需字段
    3. GEO 数据是否完整
    4. 质量评分是否有效
    """
    # 1. 从数据库查询已保存的结果
    db_results = self._result_repo.get_by_execution_id(execution_id)
    
    # 2. 验证数量
    expected_count = len(brand_list) * len(selected_models) * len(custom_questions)
    if len(db_results) != expected_count:
        return PhaseResult(
            success=False,
            error=f'结果数量不匹配：期望{expected_count}, 实际{len(db_results)}'
        )
    
    # 3. 验证必需字段
    for result in db_results:
        missing_fields = []
        for field in ['brand', 'question', 'model', 'response', 'geo_data']:
            if not result.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            api_logger.warning(
                f"结果缺少必需字段：{missing_fields}, result_id={result['id']}"
            )
    
    # 4. 返回数据库结果供后续使用
    return PhaseResult(
        success=True,
        data={'saved_results': db_results, 'validation_passed': True}
    )
```

---

## 三、后台统计分析功能执行顺序

### 3.1 分析模块依赖关系图

```
                    ┌─────────────────────┐
                    │  阶段 3: 结果保存完成  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  阶段 4: 结果验证    │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 品牌分布分析     │  │ 情感分布分析     │  │ 关键词提取      │
│ (独立)          │  │ (独立)          │  │ (独立)          │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  竞品对比分析        │
                    │  (依赖品牌分布)      │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 语义偏移分析     │  │ 信源纯净度分析   │  │ 优化建议生成    │
│ (依赖关键词)     │  │ (依赖信源数据)   │  │ (依赖所有分析)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 3.2 分析模块执行顺序

**文件**: `backend_python/wechat_backend/services/diagnosis_orchestrator.py`

```python
def _phase_background_analysis_async(self, db_results, brand_list):
    """
    阶段 5: 后台分析（异步执行，不阻塞主流程）
    
    执行顺序:
    1. 品牌分布分析 (独立)
    2. 情感分布分析 (独立)
    3. 关键词提取 (独立)
    4. 竞品对比分析 (依赖品牌分布)
    5. 语义偏移分析 (依赖关键词)
    6. 信源纯净度分析 (依赖信源数据)
    7. 优化建议生成 (依赖所有分析)
    """
    
    def run_analysis():
        try:
            # ===== 第一层：独立分析（可并行） =====
            # 1. 品牌分布分析
            brand_distribution = self._analyze_brand_distribution(db_results)
            
            # 2. 情感分布分析
            sentiment_distribution = self._analyze_sentiment_distribution(db_results)
            
            # 3. 关键词提取
            keywords = self._extract_keywords(db_results)
            
            # ===== 第二层：依赖分析（顺序执行） =====
            # 4. 竞品对比分析（依赖品牌分布）
            competitor_analysis = self._analyze_competitors(
                db_results, brand_list, brand_distribution
            )
            
            # 5. 语义偏移分析（依赖关键词）
            semantic_drift = self._analyze_semantic_drift(keywords)
            
            # 6. 信源纯净度分析（依赖信源数据）
            source_purity = self._analyze_source_purity(db_results)
            
            # ===== 第三层：综合建议（依赖所有分析） =====
            # 7. 优化建议生成
            recommendations = self._generate_recommendations(
                brand_distribution,
                sentiment_distribution,
                competitor_analysis,
                semantic_drift,
                source_purity
            )
            
            # 保存分析结果到数据库
            self._save_analysis_results({
                'brand_distribution': brand_distribution,
                'sentiment_distribution': sentiment_distribution,
                'keywords': keywords,
                'competitor_analysis': competitor_analysis,
                'semantic_drift': semantic_drift,
                'source_purity': source_purity,
                'recommendations': recommendations
            })
            
        except Exception as e:
            api_logger.error(f"后台分析失败：{e}")
            # 后台分析失败不影响主流程
    
    # 异步执行
    Thread(target=run_analysis, daemon=True).start()
```

### 3.3 各分析模块详细实现

#### 3.3.1 品牌分布分析

**文件**: `backend_python/wechat_backend/v2/analytics/brand_distribution_analyzer.py`

```python
class BrandDistributionAnalyzer:
    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        分析品牌频段分布
        
        输入: 诊断结果列表
        输出: 品牌分布字典 {品牌名: 占比%}
        
        示例输出:
        {
            'data': {'德施曼': 45.5, '小米': 30.3, '凯迪仕': 24.2},
            'total_count': 33,
            'warning': None
        }
        """
        # 统计各品牌出现次数
        brand_counts = defaultdict(int)
        for result in results:
            brand = result.get('brand', 'unknown')
            brand_counts[brand] += 1
        
        # 计算占比
        total = sum(brand_counts.values())
        distribution = {}
        for brand, count in brand_counts.items():
            percentage = round(count / total * 100, 2)
            distribution[brand] = percentage
        
        return {'data': distribution, 'total_count': total, 'warning': None}
```

#### 3.3.2 情感分布分析

```python
def _calculate_sentiment_distribution(results):
    """
    计算情感分布
    
    输入: 诊断结果列表（每条结果包含 sentiment 字段）
    输出: 情感分布字典 {情感类型: 数量}
    
    示例输出:
    {
        'data': {'positive': 15, 'neutral': 12, 'negative': 6},
        'total_count': 33
    }
    """
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    
    for result in results:
        sentiment = result.get('sentiment', 'neutral')
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
    
    return {'data': sentiment_counts, 'total_count': len(results)}
```

#### 3.3.3 关键词提取

```python
def _extract_keywords(results, top_n=50):
    """
    提取关键词
    
    输入: 诊断结果列表（每条结果包含 keywords 字段）
    输出: 关键词列表（按频率排序）
    
    示例输出:
    [
        {'word': '安全性', 'count': 12, 'sentiment': 0.8, 'sentiment_label': 'positive'},
        {'word': '性价比', 'count': 8, 'sentiment': 0.5, 'sentiment_label': 'neutral'},
        {'word': '故障', 'count': 5, 'sentiment': -0.7, 'sentiment_label': 'negative'}
    ]
    """
    keyword_freq = defaultdict(int)
    keyword_sentiment = defaultdict(list)
    
    for result in results:
        keywords = result.get('keywords', [])
        sentiment = result.get('sentiment_score', 0)
        
        for kw in keywords:
            keyword_freq[kw] += 1
            keyword_sentiment[kw].append(sentiment)
    
    # 计算平均情感
    keywords_with_sentiment = []
    for kw, count in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]:
        avg_sentiment = sum(keyword_sentiment[kw]) / len(keyword_sentiment[kw])
        keywords_with_sentiment.append({
            'word': kw,
            'count': count,
            'sentiment': round(avg_sentiment, 2),
            'sentiment_label': _classify_sentiment(avg_sentiment)
        })
    
    return keywords_with_sentiment
```

#### 3.3.4 竞品对比分析

```python
def _analyze_competitors(results, brand_list, brand_distribution):
    """
    竞品对比分析
    
    输入: 
    - 诊断结果列表
    - 品牌列表 [主品牌，竞品 1, 竞品 2, ...]
    - 品牌分布数据
    
    输出: 竞品对比分析结果
    
    示例输出:
    {
        'main_brand': '德施曼',
        'main_brand_share': 45.5,
        'competitor_shares': {'小米': 30.3, '凯迪仕': 24.2},
        'rank': 1,
        'total_competitors': 2,
        'top_competitor': '小米'
    }
    """
    main_brand = brand_list[0]
    main_brand_share = brand_distribution.get(main_brand, 0)
    
    competitor_shares = {
        brand: share
        for brand, share in brand_distribution.items()
        if brand != main_brand
    }
    
    # 计算主品牌排名
    sorted_shares = sorted(brand_distribution.items(), key=lambda x: x[1], reverse=True)
    rank = next(
        (i + 1 for i, (brand, _) in enumerate(sorted_shares) if brand == main_brand),
        len(sorted_shares) + 1
    )
    
    return {
        'main_brand': main_brand,
        'main_brand_share': main_brand_share,
        'competitor_shares': competitor_shares,
        'rank': rank,
        'total_competitors': len(competitor_shares),
        'top_competitor': max(competitor_shares.items(), key=lambda x: x[1])[0] if competitor_shares else None
    }
```

#### 3.3.5 优化建议生成

```python
def _generate_recommendations(brand_distribution, sentiment_distribution, 
                               competitor_analysis, semantic_drift, source_purity):
    """
    生成优化建议
    
    输入: 所有分析结果
    输出: 优化建议列表
    
    示例输出:
    {
        'suggestions': [
            {
                'priority': 'high',
                'category': 'brand_exposure',
                'title': '提升品牌露出频次',
                'description': '当前品牌露出占比为 45.5%，低于行业标杆水平（60%）',
                'action_items': ['增加内容投放', '优化 SEO 策略']
            },
            {
                'priority': 'medium',
                'category': 'sentiment',
                'title': '改善情感倾向',
                'description': '负面评价占比 18%，需要关注并处理',
                'action_items': ['舆情监控', '危机公关']
            }
        ]
    }
    """
    suggestions = []
    
    # 基于品牌露出占比生成建议
    if competitor_analysis['main_brand_share'] < 40:
        suggestions.append({
            'priority': 'high',
            'category': 'brand_exposure',
            'title': '提升品牌露出频次',
            'description': f"当前品牌露出占比为{competitor_analysis['main_brand_share']}%, "
                          f"低于行业标杆水平（60%）",
            'action_items': ['增加内容投放', '优化 SEO 策略', '加强内容营销']
        })
    
    # 基于情感分布生成建议
    negative_ratio = sentiment_distribution['data']['negative'] / sentiment_distribution['total_count']
    if negative_ratio > 0.15:
        suggestions.append({
            'priority': 'high',
            'category': 'sentiment',
            'title': '改善情感倾向',
            'description': f'负面评价占比{negative_ratio * 100:.1f}%, 需要关注并处理',
            'action_items': ['舆情监控', '危机公关', '用户体验优化']
        })
    
    # 基于竞品排名生成建议
    if competitor_analysis['rank'] > 2:
        suggestions.append({
            'priority': 'medium',
            'category': 'competitive_position',
            'title': '提升竞争排位',
            'description': f"当前排名第{competitor_analysis['rank']}位，"
                          f"主要竞争对手是{competitor_analysis['top_competitor']}",
            'action_items': ['差异化定位', '优势强化', '弱点改进']
        })
    
    return {'suggestions': suggestions}
```

---

## 四、结果输出顺序与前端展示

### 4.1 完整报告数据结构

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`

```python
def get_full_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
    """
    获取完整报告（前端需要的数据格式）
    
    返回结构:
    {
        'report': {...},              # 报告主数据
        'results': [...],             # 诊断结果明细
        'analysis': {...},            # 分析数据（嵌套结构）
        'brandDistribution': {...},   # 品牌分布（前端格式）
        'sentimentDistribution': {...}, # 情感分布（前端格式）
        'keywords': [...],            # 关键词列表（前端格式）
        'meta': {...},                # 元数据
        'validation': {...},          # 验证信息
        'qualityHints': {...}         # 质量提示
    }
    """
    # 1. 获取报告主数据
    report = self.report_repo.get_by_execution_id(execution_id)
    
    # 2. 获取结果明细
    results = self.result_repo.get_by_execution_id(execution_id)
    
    # 3. 获取分析数据
    analysis = self.analysis_repo.get_by_execution_id(execution_id)
    
    # 4. 计算品牌分布
    brand_distribution = self._calculate_brand_distribution(results)
    
    # 5. 计算情感分布
    sentiment_distribution = self._calculate_sentiment_distribution(results)
    
    # 6. 提取关键词
    keywords = self._extract_keywords(results)
    
    # 7. 构建完整报告
    full_report = {
        'report': report,
        'results': results,
        'analysis': analysis,
        # 前端需要的聚合数据
        'brandDistribution': brand_distribution,
        'sentimentDistribution': sentiment_distribution,
        'keywords': keywords,
        'meta': {
            'data_schema_version': DATA_SCHEMA_VERSION,
            'server_version': '2.0.0',
            'retrieved_at': datetime.now().isoformat()
        },
        'validation': validation,
        'qualityHints': quality_hints
    }
    
    # 8. 转换为 camelCase（前端格式）
    return convert_response_to_camel(full_report)
```

### 4.2 前端展示维度与数据来源映射

**文件**: `miniprogram/pages/report-v2/report-v2.js`

| 前端展示模块 | 展示字段 | 数据来源 | 更新时机 |
|-------------|---------|----------|----------|
| **品牌分布图** | 各品牌占比 | `report.brandDistribution.data` | 阶段 6 完成后 |
| | 总结果数 | `report.brandDistribution.total_count` | 阶段 3 完成后 |
| **情感分布图** | 正面/中性/负面数量 | `report.sentimentDistribution.data` | 阶段 3 完成后 |
| | 情感占比 | 计算得出 | 阶段 3 完成后 |
| **关键词云** | 关键词文本 | `report.keywords[].word` | 阶段 3 完成后 |
| | 词频 | `report.keywords[].count` | 阶段 3 完成后 |
| | 情感标签 | `report.keywords[].sentiment_label` | 阶段 3 完成后 |
| **竞品分析** | 主品牌排名 | `report.analysis.competitive_analysis.rank` | 阶段 5 完成后 |
| | 竞品份额 | `report.analysis.competitive_analysis.competitor_shares` | 阶段 5 完成后 |
| | 主要竞争对手 | `report.analysis.competitive_analysis.top_competitor` | 阶段 5 完成后 |
| **优化建议** | 建议列表 | `report.analysis.recommendations.suggestions` | 阶段 5 完成后 |
| | 优先级 | `report.analysis.recommendations.suggestions[].priority` | 阶段 5 完成后 |
| **诊断明细** | AI 响应内容 | `report.results[].response` | 阶段 3 完成后 |
| | 质量评分 | `report.results[].quality_score` | 阶段 3 完成后 |
| | 情感倾向 | `report.results[].sentiment` | 阶段 3 完成后 |

### 4.3 前端数据获取流程

**文件**: `miniprogram/services/reportService.js`

```javascript
class ReportService {
  /**
   * 获取完整诊断报告
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 报告数据
   */
  async getFullReport(executionId, options = {}) {
    try {
      // 1. 检查缓存（减少重复请求）
      const cached = this._getFromCache(executionId);
      if (cached) {
        return cached;
      }
      
      // 2. 调用云函数获取报告
      const res = await wx.cloud.callFunction({
        name: 'getDiagnosisReport',
        data: { executionId },
        timeout: 30000
      });
      
      const report = res.result;
      
      // 3. 处理失败状态
      if (report.status === 'failed') {
        return this._createFailedReportWithMetadata(report);
      }
      
      // 4. 处理报告数据（统一格式）
      const processedReport = this._processReportData(report);
      
      // 5. 缓存报告
      this._setCache(executionId, processedReport);
      
      return processedReport;
    } catch (error) {
      // 6. 错误处理与重试
      return this._handleError(error, executionId);
    }
  }
  
  /**
   * 处理原始报告数据（统一格式）
   */
  _processReportData(report) {
    // 1. 处理品牌分布数据
    report.brandDistribution = {
      data: report.brandDistribution?.data || report.brandDistribution || {},
      total_count: report.brandDistribution?.total_count || 0
    };
    
    // 2. 处理情感分布数据
    report.sentimentDistribution = {
      data: report.sentimentDistribution?.data || report.sentimentDistribution || {},
      total_count: report.sentimentDistribution?.total_count || 0
    };
    
    // 3. 处理关键词数据
    report.keywords = (report.keywords || []).map(kw => ({
      word: kw.word || kw.text || '',
      count: kw.count || kw.frequency || 0,
      sentiment: kw.sentiment || 0,
      sentiment_label: kw.sentiment_label || 'neutral'
    }));
    
    // 4. 处理竞品分析数据
    report.competitorAnalysis = report.competitorAnalysis || 
                                report.analysis?.competitive_analysis || {};
    
    // 5. 处理优化建议数据
    report.recommendations = report.recommendations || 
                             report.analysis?.recommendations || {};
    
    return report;
  }
}
```

---

## 五、并行与顺序执行策略

### 5.1 执行策略总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│  执行策略矩阵                                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  阶段          │ 执行方式 │ 可并行 │ 依赖关系 │ 事务保护 │ 失败处理       │
│  ─────────────┼──────────┼────────┼──────────┼──────────┼──────────────  │
│  1. 初始化     │ 顺序     │ 否     │ 无       │ 无       │ 阻塞          │
│  2. AI 调用     │ 并行     │ 是     │ 无       │ 无       │ 重试 + 降级    │
│  3. 结果保存   │ 顺序     │ 否     │ 阶段 2    │ 有       │ 回滚          │
│  4. 结果验证   │ 顺序     │ 否     │ 阶段 3    │ 无       │ 警告继续      │
│  5. 后台分析   │ 异步     │ 部分   │ 阶段 4    │ 无       │ 降级继续      │
│  6. 报告聚合   │ 顺序     │ 否     │ 阶段 4    │ 有       │ 阻塞          │
│  7. 完成       │ 顺序     │ 否     │ 阶段 6    │ 有       │ 阻塞          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 AI 调用并行执行

**文件**: `backend_python/wechat_backend/nxm_concurrent_engine_v3.py`

```python
async def execute_parallel_nxm(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict],
    raw_questions: List[str],
    max_concurrent: int = 6
) -> Dict[str, Any]:
    """
    执行 N 品牌 × M 模型 × Q 问题 并行调用
    
    并行策略:
    1. 使用信号量控制并发数（默认 6）
    2. 每个任务独立执行，互不影响
    3. 所有任务完成后统一返回结果
    
    参数:
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品列表
        selected_models: 模型列表
        raw_questions: 问题列表
        max_concurrent: 最大并发数
    
    返回:
        {
            'success': True,
            'results': [...],
            'total_tasks': N*M*Q,
            'completed_tasks': X
        }
    """
    # 1. 构建任务矩阵
    tasks = []
    for brand in [main_brand] + competitor_brands:
        for model in selected_models:
            for question in raw_questions:
                tasks.append({
                    'brand': brand,
                    'model': model,
                    'question': question
                })
    
    # 2. 创建信号量（控制并发数）
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 3. 执行所有任务
    async def execute_with_semaphore(task):
        async with semaphore:
            return await _execute_single_task(task)
    
    results = await asyncio.gather(
        *[execute_with_semaphore(task) for task in tasks],
        return_exceptions=True
    )
    
    # 4. 过滤异常结果
    valid_results = [r for r in results if not isinstance(r, Exception)]
    
    return {
        'success': True,
        'results': valid_results,
        'total_tasks': len(tasks),
        'completed_tasks': len(valid_results)
    }
```

### 5.3 后台分析并行策略

```python
def _phase_background_analysis_async(self, db_results, brand_list):
    """
    阶段 5: 后台分析（异步执行，部分并行）
    
    并行策略:
    第一层（独立分析，可并行）:
    - 品牌分布分析
    - 情感分布分析
    - 关键词提取
    
    第二层（依赖第一层，顺序执行）:
    - 竞品对比分析（依赖品牌分布）
    - 语义偏移分析（依赖关键词）
    - 信源纯净度分析（独立）
    
    第三层（依赖所有层，顺序执行）:
    - 优化建议生成
    """
    
    def run_analysis():
        # 第一层：并行执行独立分析
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_brand = executor.submit(self._analyze_brand_distribution, db_results)
            future_sentiment = executor.submit(self._analyze_sentiment_distribution, db_results)
            future_keywords = executor.submit(self._extract_keywords, db_results)
            
            # 等待第一层完成
            brand_distribution = future_brand.result()
            sentiment_distribution = future_sentiment.result()
            keywords = future_keywords.result()
        
        # 第二层：顺序执行依赖分析
        competitor_analysis = self._analyze_competitors(
            db_results, brand_list, brand_distribution
        )
        semantic_drift = self._analyze_semantic_drift(keywords)
        source_purity = self._analyze_source_purity(db_results)
        
        # 第三层：综合建议
        recommendations = self._generate_recommendations(
            brand_distribution, sentiment_distribution,
            competitor_analysis, semantic_drift, source_purity
        )
        
        # 保存分析结果
        self._save_analysis_results({
            'brand_distribution': brand_distribution,
            'sentiment_distribution': sentiment_distribution,
            'keywords': keywords,
            'competitor_analysis': competitor_analysis,
            'semantic_drift': semantic_drift,
            'source_purity': source_purity,
            'recommendations': recommendations
        })
    
    # 异步执行（不阻塞主流程）
    Thread(target=run_analysis, daemon=True).start()
```

---

## 六、调试指南

### 6.1 按诊断结果逐一调试

#### 6.1.1 品牌分布调试

**检查点**:
1. `diagnosis_results` 表中是否包含所有品牌的记录
2. `brand_distribution_analyzer.py` 是否正确计算占比
3. 前端 `report.brandDistribution.data` 是否有数据

**调试步骤**:
```python
# 1. 检查数据库结果
SELECT brand, COUNT(*) as count 
FROM diagnosis_results 
WHERE execution_id = '目标 execution_id'
GROUP BY brand;

# 2. 检查分析结果
SELECT analysis_type, analysis_data 
FROM diagnosis_analysis 
WHERE execution_id = '目标 execution_id'
AND analysis_type = 'brand_distribution';

# 3. 检查完整报告
# 在 reportService.js 中添加调试日志
console.log('[DEBUG] Brand distribution:', report.brandDistribution);
```

#### 6.1.2 情感分布调试

**检查点**:
1. `diagnosis_results.sentiment` 字段是否有值
2. `sentiment_distribution` 计算是否正确
3. 前端 `report.sentimentDistribution.data` 是否有数据

**调试步骤**:
```python
# 1. 检查情感字段
SELECT sentiment, COUNT(*) as count 
FROM diagnosis_results 
WHERE execution_id = '目标 execution_id'
GROUP BY sentiment;

# 2. 检查分析结果
SELECT analysis_data 
FROM diagnosis_analysis 
WHERE execution_id = '目标 execution_id'
AND analysis_type = 'sentiment_distribution';
```

#### 6.1.3 关键词调试

**检查点**:
1. `diagnosis_results.keywords` 字段是否有值
2. 关键词提取逻辑是否正确
3. 前端 `report.keywords` 是否有数据

**调试步骤**:
```python
# 1. 检查关键词字段
SELECT keywords 
FROM diagnosis_results 
WHERE execution_id = '目标 execution_id'
LIMIT 5;

# 2. 检查关键词提取
# 在 _extract_keywords 函数中添加日志
api_logger.info(f"提取关键词：{keywords}")
```

#### 6.1.4 竞品分析调试

**检查点**:
1. 品牌分布数据是否正确
2. 竞品对比逻辑是否正确
3. 前端 `report.analysis.competitive_analysis` 是否有数据

**调试步骤**:
```python
# 1. 检查竞品分析结果
SELECT analysis_data 
FROM diagnosis_analysis 
WHERE execution_id = '目标 execution_id'
AND analysis_type = 'competitive_analysis';

# 2. 检查前端数据
console.log('[DEBUG] Competitor analysis:', report.analysis?.competitive_analysis);
```

#### 6.1.5 优化建议调试

**检查点**:
1. 所有分析数据是否完整
2. 建议生成逻辑是否正确
3. 前端 `report.analysis.recommendations` 是否有数据

**调试步骤**:
```python
# 1. 检查建议生成结果
SELECT analysis_data 
FROM diagnosis_analysis 
WHERE execution_id = '目标 execution_id'
AND analysis_type = 'recommendations';

# 2. 检查前端数据
console.log('[DEBUG] Recommendations:', report.analysis?.recommendations);
```

### 6.2 日志关键字搜索

**后端日志**:
```bash
# 检查诊断执行流程
grep "\[Orchestrator\]" logs/app.log | grep "目标 execution_id"

# 检查 AI 调用
grep "AI 调用完成" logs/app.log | grep "目标 execution_id"

# 检查结果保存
grep "结果保存" logs/app.log | grep "目标 execution_id"

# 检查后台分析
grep "后台分析" logs/app.log | grep "目标 execution_id"

# 检查报告聚合
grep "报告聚合" logs/app.log | grep "目标 execution_id"
```

**前端日志**:
```javascript
// 在小程序控制台搜索
// "[ReportService]" - 报告服务日志
// "[ReportPageV2]" - 报告页面日志
// "Brand distribution" - 品牌分布日志
// "Sentiment distribution" - 情感分布日志
// "Keywords" - 关键词日志
```

---

## 七、常见问题排查

### 7.1 品牌分布无数据

**可能原因**:
1. AI 调用结果为空
2. 结果保存失败
3. 分析模块未执行

**排查步骤**:
1. 检查 `diagnosis_results` 表是否有记录
2. 检查后台日志是否有分析错误
3. 检查前端是否正确解析数据

### 7.2 情感分布不正确

**可能原因**:
1. AI 响应中情感分析失败
2. 情感字段未正确保存
3. 情感分布计算逻辑错误

**排查步骤**:
1. 检查 AI 响应中是否包含情感数据
2. 检查 `diagnosis_results.sentiment` 字段值
3. 检查 `_calculate_sentiment_distribution` 函数逻辑

### 7.3 关键词云为空

**可能原因**:
1. AI 未返回关键词
2. 关键词提取逻辑错误
3. 前端格式处理错误

**排查步骤**:
1. 检查 AI 响应中是否包含关键词
2. 检查 `diagnosis_results.keywords` 字段值
3. 检查 `_extract_keywords` 函数逻辑
4. 检查前端 `_processReportData` 中的关键词处理

### 7.4 优化建议不显示

**可能原因**:
1. 分析数据不完整
2. 建议生成条件未满足
3. 前端数据路径错误

**排查步骤**:
1. 检查所有分析模块是否执行完成
2. 检查 `_generate_recommendations` 函数逻辑
3. 检查前端 `report.analysis.recommendations` 路径是否正确

---

## 八、性能优化建议

### 8.1 数据库查询优化

```python
# 1. 添加索引
CREATE INDEX idx_results_execution ON diagnosis_results(execution_id);
CREATE INDEX idx_analysis_execution ON diagnosis_analysis(execution_id);

# 2. 批量查询
# 使用 JOIN 一次性获取所有数据
SELECT dr.*, da.analysis_type, da.analysis_data
FROM diagnosis_results dr
LEFT JOIN diagnosis_analysis da ON dr.report_id = da.report_id
WHERE dr.execution_id = ?;
```

### 8.2 缓存策略

```javascript
// 前端缓存优化
class ReportService {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 300000; // 5 分钟
  }
  
  async getFullReport(executionId) {
    // 检查缓存
    const cached = this._getFromCache(executionId);
    if (cached) {
      return cached;
    }
    
    // 获取数据
    const report = await this._fetchReport(executionId);
    
    // 缓存结果
    this._setCache(executionId, report);
    
    return report;
  }
}
```

### 8.3 并行执行优化

```python
# 使用 ThreadPoolExecutor 并行执行独立分析
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    future_brand = executor.submit(self._analyze_brand_distribution, db_results)
    future_sentiment = executor.submit(self._analyze_sentiment_distribution, db_results)
    future_keywords = executor.submit(self._extract_keywords, db_results)
    
    # 并行获取结果
    brand_distribution = future_brand.result()
    sentiment_distribution = future_sentiment.result()
    keywords = future_keywords.result()
```

---

## 九、附录

### A. 关键文件路径

| 组件 | 文件路径 |
|------|----------|
| 诊断视图 | `backend_python/wechat_backend/views/diagnosis_views.py` |
| 诊断编排器 | `backend_python/wechat_backend/services/diagnosis_orchestrator.py` |
| 诊断事务 | `backend_python/wechat_backend/services/diagnosis_transaction.py` |
| 报告服务 | `backend_python/wechat_backend/diagnosis_report_service.py` |
| 品牌分布分析器 | `backend_python/wechat_backend/v2/analytics/brand_distribution_analyzer.py` |
| 状态管理 | `backend_python/wechat_backend/state_manager.py` |
| 诊断页面 | `miniprogram/pages/diagnosis/diagnosis.js` |
| 诊断服务 | `miniprogram/services/diagnosisService.js` |
| 轮询管理 | `miniprogram/services/pollingManager.js` |
| 报告页面 | `miniprogram/pages/report-v2/report-v2.js` |
| 报告服务 | `miniprogram/services/reportService.js` |

### B. 数据库表结构

```sql
-- 诊断报告主表
CREATE TABLE diagnosis_reports (
    id INTEGER PRIMARY KEY,
    execution_id TEXT UNIQUE,
    user_id TEXT,
    brand_name TEXT,
    status TEXT,
    progress INTEGER,
    stage TEXT,
    is_completed BOOLEAN,
    should_stop_polling BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 诊断结果明细表
CREATE TABLE diagnosis_results (
    id INTEGER PRIMARY KEY,
    report_id INTEGER,
    execution_id TEXT,
    brand TEXT,
    question TEXT,
    model TEXT,
    response TEXT,
    geo_data TEXT,
    exposure BOOLEAN,
    sentiment TEXT,
    keywords TEXT,
    quality_score REAL,
    quality_level TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
);

-- 分析结果表
CREATE TABLE diagnosis_analysis (
    id INTEGER PRIMARY KEY,
    report_id INTEGER,
    execution_id TEXT,
    analysis_type TEXT,
    analysis_data TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
);
```

### C. 相关文档

- [前端轮询优化方案](../frontend-polling-optimization.md)
- [品牌诊断系统前端输出失败系统摸底文档](./2026-03-09_品牌诊断系统前端输出失败系统摸底文档.md)
- [API 规范](./api-spec.yaml)

---

**文档维护**: 系统架构组  
**最后更新**: 2026-03-09  
**版本**: 2.0.0
