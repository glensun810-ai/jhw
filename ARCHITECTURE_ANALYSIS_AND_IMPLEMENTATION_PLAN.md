# 进化湾 GEO 品牌 AI 雷达 - 架构理解与实施计划

**文档版本**: 1.0  
**创建日期**: 2026-03-22  
**作者**: 首席架构师  
**状态**: 待审核

---

## 执行摘要

### 项目定位

**进化湾 GEO 品牌 AI 雷达**是一个基于微信小程序的 SaaS 平台，专注于**生成式引擎优化 (GEO)** 的深度归因分析。系统通过调用多个 AI 平台（DeepSeek、豆包、通义千问、智谱等）对品牌进行多维度诊断，生成包含露出排位、信源归因、证据链穿透的深度情报报告。

### 核心价值主张

| 价值维度 | 说明 |
|---------|------|
| **露出分析** | 解决"谁排第一，谁被拦截"的问题 - 物理排位解析 |
| **信源归因** | 解决"AI 听谁说的"问题 - 深度信源穿透 |
| **证据链** | 定点追溯风险内容源头 - 负面评价溯源 |
| **认知差距** | 解决"品牌与竞品在 AI 认知中的差异"问题 |

### 当前系统状态

**✅ 已实现能力**:
- 多 AI 平台适配器架构（DeepSeek、豆包、通义、智谱、文心一言等）
- 异步诊断任务执行引擎（N×M 并发模型）
- WebSocket + HTTP 轮询双模进度推送
- 诊断报告存储与检索系统
- 5 层防御体系（统一响应格式、数据验证、错误处理）
- 历史诊断记录管理
- 基础评分维度计算

**⚠️ 已识别问题**:
- 平均每报告结果数仅 2.97 条（预期≥12 条）
- 核心指标数据缺失（SOV、情感得分、物理排名等）
- 评分维度数据为占位符
- 问题诊断墙为空
- 前端默认配置过于保守（只选 1 模型 +1 问题）

---

## 一、项目需求理解

### 1.1 业务需求

#### 目标用户
- 品牌方市场/公关负责人
- 数字营销代理商
- 企业战略决策者

#### 核心场景
```
场景 1: 品牌诊断
用户输入品牌名 → 选择 AI 模型 → 输入测试问题 → 
系统调用多 AI 平台 → 生成深度情报报告 → 用户查看分析结果

场景 2: 竞品对比
用户输入自有品牌 + 竞品列表 → 系统对比各品牌在 AI 中的认知差异 → 
生成竞争态势分析

场景 3: 历史追踪
用户查看历史诊断记录 → 对比不同时间点的品牌表现 → 
识别趋势变化
```

#### 关键业务指标
| 指标 | 当前值 | 目标值 | 差距 |
|------|-------|-------|------|
| 平均每报告结果数 | 2.97 | ≥12 | -75% |
| 核心指标填充率 | 0% | 100% | -100% |
| 评分维度填充率 | 0% | 100% | -100% |
| 问题诊断墙填充率 | 0% | 100% | -100% |

### 1.2 功能需求

#### P0 核心功能（必须）
1. **多模型诊断执行**
   - 支持至少 4 个 AI 平台同时诊断
   - 每个模型执行 3 个标准问题
   - 预期输出：4 模型 × 3 问题 = 12 条结果

2. **实时进度推送**
   - WebSocket 实时推送（优先）
   - HTTP 轮询降级（兼容）
   - 分阶段状态更新（init → ai_fetching → ranking_analysis → source_tracing → completed）

3. **深度情报报告**
   - 露出与排位分析（ranking_list, brand_details, unlisted_competitors）
   - 深度信源归因（source_pool, citation_rank）
   - 证据链穿透（evidence_chain）
   - 对比分析（common_keywords, unique_keywords, differentiation_gap）

4. **历史诊断管理**
   - 历史列表查询（分页、筛选、排序）
   - 历史报告详情查看
   - 本地缓存 + API 同步

#### P1 重要功能（应该）
1. **核心指标计算**
   - 声量份额 (SOV): (品牌提及数 / 总提及数) × 100
   - 情感得分：(正面数 - 负面数) / 总提及数 × 100
   - 物理排名：按提及数排序的品牌位次
   - 影响力得分：SOV×0.4 + 情感×0.3 + (1/排名)×100×0.3

2. **评分维度算法**
   - 权威度 (Authority): AI 平台权威性、信源质量、回答专业度
   - 可见度 (Visibility): 提及频率、排名位置、曝光度
   - 纯净度 (Purity): 负面提及比例、品牌关联准确度
   - 一致性 (Consistency): 跨模型一致性、信息准确度

3. **问题诊断墙**
   - 风险识别（高/中/低风险分级）
   - 建议生成（基于风险类型匹配模板）
   - 优先级排序

#### P2 改进功能（可以）
1. **用户体验优化**
   - 报告加载时间 <2 秒
   - 结果长按复制
   - 空状态引导
   - 分享图生成
   - PDF 导出

2. **数据可视化增强**
   - 品牌分布饼图
   - 情感分布柱状图
   - 趋势分析折线图
   - 竞品对比雷达图

3. **性能优化**
   - 结果缓存（Redis）
   - 异步报告生成
   - 指标预计算

---

## 二、系统架构梳理

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        微信小程序前端                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 首页        │  │ 诊断记录    │  │ 报告详情页              │  │
│  │ - 品牌输入  │  │ - 列表      │  │ - 核心指标卡            │  │
│  │ - 模型选择  │  │ - 筛选      │  │ - 评分维度              │  │
│  │ - 问题输入  │  │ - 搜索      │  │ - 问题诊断墙            │  │
│  │ - 启动诊断  │  │ - 分页      │  │ - 详细结果              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│           │                │                  │                  │
│           ▼                ▼                  ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    前端服务层                                ││
│  │  - diagnosisService.js (诊断服务)                           ││
│  │  - pollingManager.js (轮询管理)                             ││
│  │  - webSocketClient.js (WebSocket 客户端)                     ││
│  │  - unifiedResponseHandler.js (统一响应处理)                  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端服务层 (Flask)                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    API 网关层                                 ││
│  │  - /api/diagnosis/start         启动诊断                    ││
│  │  - /api/diagnosis/status        查询状态                    ││
│  │  - /api/diagnosis/report/{id}   获取报告                    ││
│  │  - /api/diagnosis/history       历史记录                    ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    业务服务层                                ││
│  │  - DiagnosisService          诊断编排服务                   ││
│  │  - MetricsCalculator         核心指标计算                   ││
│  │  - DimensionScorer           评分维度计算                   ││
│  │  - DiagnosticWallGenerator   诊断墙生成                     ││
│  │  - ReportAggregator          报告聚合服务                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    执行引擎层                                ││
│  │  - NXMConcurrentEngine       N×M 并发执行引擎                ││
│  │  - MultiModelExecutor        多模型执行器                   ││
│  │  - ResultAggregator          结果聚合器                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    AI 适配器层                                ││
│  │  - AIAdapterFactory          工厂模式                       ││
│  │  - DeepSeekAdapter           DeepSeek 适配器                 ││
│  │  - DoubaoAdapter             豆包适配器                     ││
│  │  - QwenAdapter               通义千问适配器                 ││
│  │  - ZhipuAdapter              智谱适配器                     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据持久层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SQLite      │  │ Redis       │  │ 文件系统                │  │
│  │ - 诊断报告  │  │ - 缓存      │  │ - 日志                  │  │
│  │ - 诊断结果  │  │ - 会话      │  │ - 导出文件              │  │
│  │ - 任务状态  │  │ - 队列      │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

#### 诊断执行流程
```
1. 前端提交诊断请求
   POST /api/diagnosis/start
   Body: {brand_list, selected_models, custom_questions}

2. 后端验证配置
   - 验证最少模型数 (≥2)
   - 验证最少问题数 (≥2)
   - 生成 execution_id

3. 启动 N×M 并发引擎
   execution_id = uuid.uuid4()
   total_tasks = len(models) × len(questions)
   
4. 并发执行 AI 调用
   for model in models:
       for question in questions:
           execute_async(model, question, execution_id)

5. 实时进度推送
   WebSocket: {progress: 50, stage: "ai_fetching", status_text: "..."}
   
6. 结果聚合与保存
   - 保存到 diagnosis_results 表
   - 更新 diagnosis_reports 表状态

7. 返回完整报告
   GET /api/diagnosis/report/{execution_id}
```

#### 报告查看流程
```
1. 前端请求报告
   GET /api/diagnosis/report/{execution_id}

2. 后端查询数据库
   SELECT * FROM diagnosis_reports WHERE execution_id = ?
   SELECT * FROM diagnosis_results WHERE execution_id = ?

3. 报告聚合服务处理
   - 计算核心指标 (MetricsCalculator)
   - 计算评分维度 (DimensionScorer)
   - 生成诊断墙 (DiagnosticWallGenerator)

4. 返回完整报告
   {
     "report": {...},
     "results": [...],
     "metrics": {...},
     "dimension_scores": {...},
     "diagnosticWall": {...}
   }
```

### 2.3 数据库 Schema

#### 核心表结构

```sql
-- 诊断报告主表
CREATE TABLE diagnosis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,
    brand_name TEXT NOT NULL,
    user_id TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    stage TEXT DEFAULT 'init',
    selected_models TEXT,  -- JSON
    custom_questions TEXT, -- JSON
    overall_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 诊断结果表
CREATE TABLE diagnosis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    model TEXT NOT NULL,
    question TEXT NOT NULL,
    raw_response TEXT,
    extracted_brand TEXT,
    ranking_position INTEGER,
    sentiment_score REAL,
    word_count INTEGER,
    sources TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES diagnosis_reports(execution_id)
);

-- 任务状态表
CREATE TABLE task_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    progress INTEGER DEFAULT 0,
    stage TEXT NOT NULL,
    status_text TEXT,
    completed_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 深度情报结果表
CREATE TABLE deep_intelligence_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    exposure_analysis TEXT,      -- JSON
    source_intelligence TEXT,    -- JSON
    evidence_chain TEXT,         -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES task_statuses(task_id)
);
```

### 2.4 技术栈清单

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| **前端** | 微信小程序原生开发 | - |
| **前端框架** | 原生 WXML/WXSS/JS | - |
| **后端框架** | Flask | 3.1.2+ |
| **后端语言** | Python | 3.14+ |
| **数据库** | SQLite | 3.x |
| **缓存** | Redis (可选) | - |
| **实时通信** | WebSocket | - |
| **AI 平台** | DeepSeek/豆包/通义/智谱 | - |
| **部署** | 微信云开发 | - |

---

## 三、当前系统问题诊断

### 3.1 P0 关键问题

#### 问题 1: 诊断结果数量严重不足

**现状**:
- 平均每报告 2.97 条结果
- 最新诊断甚至只有 1 条结果
- 预期应为 12 条（4 模型 × 3 问题）

**根因分析**:
```javascript
// 前端默认配置（pages/index/index.js）
data: {
  selectedModels: [
    {name: 'deepseek', checked: true}  // ❌ 只勾选 1 个模型
  ],
  customQuestions: [
    '深圳新能源汽车改装门店推荐？'  // ❌ 只有 1 个问题
  ]
}
// 结果：1 模型 × 1 问题 = 1 条结果
```

**影响**:
- 用户体验：报告内容单薄，价值感低
- 商业价值：无法体现多模型对比优势
- 数据分析：样本量不足，统计意义弱

**修复方案**:
1. 修改前端默认配置（勾选 4 个模型，填充 3 个问题）
2. 后端验证最少模型/问题数
3. 用户引导文案优化

---

#### 问题 2: 核心指标数据缺失

**现状**:
```javascript
// 前端期望的数据结构
{
  sovShare: 0,        // ❌ 缺失
  sentimentScore: 0,  // ❌ 缺失
  physicalRank: 0,    // ❌ 缺失
  influenceScore: 0   // ❌ 缺失
}
```

**根因**:
- 后端未实现指标计算服务
- 前端使用占位符显示

**修复方案**:
1. 实现 MetricsCalculator 服务
2. 定义指标计算公式
3. 前端正确映射字段

---

#### 问题 3: 评分维度数据为占位符

**现状**:
```javascript
// 前端期望的数据结构
{
  dimension_scores: {
    authority: 0,    // ❌ 缺失
    visibility: 0,   // ❌ 缺失
    purity: 0,       // ❌ 缺失
    consistency: 0   // ❌ 缺失
  }
}
```

**修复方案**:
1. 实现 DimensionScorer 服务
2. 建立评分标准
3. 从 AI 回答中提取维度特征

---

#### 问题 4: 问题诊断墙为空

**现状**:
- 高风险问题：0 条
- 中风险问题：0 条
- 建议：0 条

**修复方案**:
1. 实现 DiagnosticWallGenerator 服务
2. 建立风险规则库
3. 实现建议生成逻辑

---

### 3.2 P1 重要问题

#### 问题 5: 用户体验优化空间

| 问题 | 当前状态 | 期望状态 |
|------|---------|---------|
| 报告加载时间 | 3-5 秒 | <2 秒 |
| 结果展开交互 | 单击展开 | 支持长按复制 |
| 空状态引导 | 简单提示 | 操作引导 |
| 分享功能 | 未实现 | 生成分享图 |
| 导出功能 | 未实现 | PDF/图片导出 |

---

#### 问题 6: 数据可视化不足

**缺失图表**:
- 品牌分布饼图
- 情感分布柱状图
- 趋势分析折线图
- 竞品对比雷达图

---

### 3.3 技术债务

| 债务项 | 影响 | 优先级 |
|-------|------|--------|
| 代码重复 | 维护成本高 | P2 |
| 错误处理不统一 | 调试困难 | P1 |
| 日志系统分散 | 问题定位慢 | P1 |
| 测试覆盖率低 | 回归风险高 | P2 |
| 文档不完善 | 新人上手慢 | P2 |

---

## 四、实施计划

### 4.1 阶段划分

#### 第一阶段：P0 核心问题修复（本周完成）

**目标**: 提升诊断结果数量，填充核心指标数据

| 任务 | 负责人 | 预计工时 | 状态 |
|------|-------|---------|------|
| 1.1 前端默认配置优化 | 前端工程师 | 2h | ⏳ 待开始 |
| 1.2 后端验证逻辑增强 | 后端工程师 | 2h | ⏳ 待开始 |
| 1.3 核心指标计算服务实现 | 算法工程师 | 4h | ⏳ 待开始 |
| 1.4 前端数据映射修复 | 前端工程师 | 2h | ⏳ 待开始 |
| 1.5 集成测试与验证 | 测试工程师 | 2h | ⏳ 待开始 |

**验收标准**:
- 新诊断报告平均结果数 ≥ 10 条
- 核心指标卡显示真实数据
- 数据与数据库一致

---

#### 第二阶段：P1 重要功能实现（下周完成）

**目标**: 实现评分维度算法和问题诊断墙

| 任务 | 负责人 | 预计工时 | 状态 |
|------|-------|---------|------|
| 2.1 评分维度算法实现 | 算法工程师 | 6h | ⏳ 待开始 |
| 2.2 问题诊断墙服务实现 | 后端工程师 | 4h | ⏳ 待开始 |
| 2.3 前端数据绑定 | 前端工程师 | 3h | ⏳ 待开始 |
| 2.4 风险规则库建立 | 产品经理 | 3h | ⏳ 待开始 |
| 2.5 集成测试 | 测试工程师 | 2h | ⏳ 待开始 |

**验收标准**:
- 评分维度显示 0-100 分
- 问题诊断墙至少 1 条高风险 +3 条建议
- 进度条正确显示

---

#### 第三阶段：P2 改进功能（下月完成）

**目标**: 用户体验优化和数据可视化增强

| 任务 | 负责人 | 预计工时 | 状态 |
|------|-------|---------|------|
| 3.1 加载性能优化 | 前端工程师 | 4h | ⏳ 待开始 |
| 3.2 结果长按复制 | 前端工程师 | 2h | ⏳ 待开始 |
| 3.3 空状态引导优化 | 前端工程师 | 2h | ⏳ 待开始 |
| 3.4 分享图生成 | 前端工程师 | 6h | ⏳ 待开始 |
| 3.5 PDF 导出 | 后端工程师 | 6h | ⏳ 待开始 |
| 3.6 数据可视化图表 | 前端工程师 | 8h | ⏳ 待开始 |

**验收标准**:
- 报告加载时间 <2 秒
- 支持长按复制文本
- 可生成分享图
- 可导出 PDF

---

#### 第四阶段：技术债务清理（下季度）

**目标**: 提升代码质量和系统可维护性

| 任务 | 负责人 | 预计工时 | 状态 |
|------|-------|---------|------|
| 4.1 代码重构 | 后端工程师 | 16h | ⏳ 待开始 |
| 4.2 测试用例补充 | 测试工程师 | 16h | ⏳ 待开始 |
| 4.3 文档完善 | 技术文档工程师 | 8h | ⏳ 待开始 |
| 4.4 监控告警增强 | 运维工程师 | 8h | ⏳ 待开始 |

---

### 4.2 详细实施步骤

#### 任务 1.1: 前端默认配置优化

**文件**: `brand_ai-seach/miniprogram/pages/index/index.js`

**修改内容**:
```javascript
// 修改前
data: {
  selectedModels: [
    {name: 'deepseek', checked: true}
  ],
  customQuestions: ['深圳新能源汽车改装门店推荐？']
}

// 修改后
data: {
  selectedModels: [
    {name: 'deepseek', checked: true},
    {name: 'doubao', checked: true},
    {name: 'qwen', checked: true},
    {name: 'zhipu', checked: true}
  ],
  customQuestions: [
    '品牌介绍与定位',
    '竞争优势分析',
    '用户口碑评价'
  ]
}
```

**验证步骤**:
1. 打开小程序首页
2. 检查默认勾选的模型数量
3. 检查默认填充的问题数量

---

#### 任务 1.3: 核心指标计算服务实现

**文件**: `backend_python/wechat_backend/services/metrics_calculator.py`

**实现内容**:
```python
class MetricsCalculator:
    """核心指标计算器"""
    
    def calculate_sov(self, brand: str, all_brands: List[str]) -> float:
        """
        计算声量份额 (Share of Voice)
        SOV = (品牌提及数 / 总提及数) × 100
        """
        brand_count = sum(1 for b in all_brands if b == brand)
        total_count = len(all_brands)
        return (brand_count / total_count * 100) if total_count > 0 else 0
    
    def calculate_sentiment(self, results: List[Dict]) -> float:
        """
        计算情感得分
        Sentiment = (正面数 - 负面数) / 总提及数 × 100
        """
        positive = sum(1 for r in results if r.get('sentiment', 0) > 0.3)
        negative = sum(1 for r in results if r.get('sentiment', 0) < -0.3)
        total = len(results)
        return ((positive - negative) / total * 100) if total > 0 else 0
    
    def calculate_rank(self, brand: str, brand_counts: Dict[str, int]) -> int:
        """
        计算物理排名
        按提及数降序排序的位次
        """
        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (b, _) in enumerate(sorted_brands, 1):
            if b == brand:
                return i
        return len(sorted_brands) + 1
    
    def calculate_influence(self, sov: float, sentiment: float, rank: int) -> float:
        """
        计算影响力得分
        Influence = SOV×0.4 + 情感×0.3 + (1/排名)×100×0.3
        """
        rank_score = (1 / rank * 100) if rank > 0 else 0
        return sov * 0.4 + sentiment * 0.3 + rank_score * 0.3
```

**集成方式**:
```python
# report_aggregator.py
from wechat_backend.services.metrics_calculator import MetricsCalculator

class ReportAggregator:
    def _calculate_core_metrics(self, results, brand_name, sov_data):
        calculator = MetricsCalculator()
        
        # 提取所有品牌
        all_brands = [r.get('extracted_brand') for r in results if r.get('extracted_brand')]
        
        # 计算 SOV
        sov = calculator.calculate_sov(brand_name, all_brands)
        
        # 计算情感
        sentiment = calculator.calculate_sentiment(results)
        
        # 计算排名
        brand_counts = {}
        for b in all_brands:
            brand_counts[b] = brand_counts.get(b, 0) + 1
        rank = calculator.calculate_rank(brand_name, brand_counts)
        
        # 计算影响力
        influence = calculator.calculate_influence(sov, sentiment, rank)
        
        return {
            'sov': round(sov, 1),
            'sentiment': round(sentiment, 1),
            'rank': rank,
            'influence': round(influence, 1)
        }
```

---

#### 任务 2.1: 评分维度算法实现

**文件**: `backend_python/wechat_backend/services/dimension_scorer.py`

**实现内容**:
```python
class DimensionScorer:
    """评分维度计算器"""
    
    def score_authority(self, results: List[Dict]) -> int:
        """
        权威度评分 (0-100)
        - AI 平台权威性权重：DeepSeek(30), 豆包 (25), 通义 (25), 智谱 (20)
        - 信源引用数量：每引用 1 个权威信源 +5 分
        - 回答专业度：基于回答长度和结构化程度
        """
        platform_weights = {
            'deepseek': 30, 'doubao': 25, 'qwen': 25, 'zhipu': 20
        }
        
        # 平台权威性得分
        platform_score = 0
        for r in results:
            model = r.get('model', '').lower()
            for platform, weight in platform_weights.items():
                if platform in model:
                    platform_score += weight
                    break
        
        # 信源引用得分
        source_score = 0
        for r in results:
            sources = r.get('sources', [])
            source_score += min(len(sources) * 5, 20)  # 最多 20 分
        
        # 专业度得分（基于回答长度）
        professionalism_score = 0
        for r in results:
            word_count = r.get('word_count', 0)
            if word_count > 500:
                professionalism_score += 10
            elif word_count > 200:
                professionalism_score += 5
        
        total = platform_score + source_score + professionalism_score
        return min(round(total / len(results)), 100) if results else 50
    
    def score_visibility(self, results: List[Dict], brand_name: str) -> int:
        """
        可见度评分 (0-100)
        - 提及频率：每提及 1 次 +10 分
        - 排名位置：第 1 名 +50 分，第 2 名 +30 分，第 3 名 +10 分
        - 曝光度：基于回答长度
        """
        # 提及频率得分
        mention_count = sum(1 for r in results if brand_name in r.get('extracted_brand', ''))
        frequency_score = min(mention_count * 10, 50)
        
        # 排名位置得分
        rank_score = 50 if mention_count >= 3 else (30 if mention_count >= 2 else 10)
        
        # 曝光度得分
        total_words = sum(r.get('word_count', 0) for r in results)
        exposure_score = min(total_words // 100, 20)
        
        return min(frequency_score + rank_score + exposure_score, 100)
    
    def score_purity(self, results: List[Dict], brand_name: str) -> int:
        """
        纯净度评分 (0-100)
        - 负面提及比例：每 10% 负面 -10 分
        - 品牌关联准确度：基于提取的品牌名与输入品牌名的一致性
        """
        # 负面提及扣分
        negative_ratio = sum(1 for r in results if r.get('sentiment', 0) < -0.3) / len(results) if results else 0
        negative_penalty = int(negative_ratio * 50)
        
        # 品牌关联准确度
        accuracy_count = sum(1 for r in results if r.get('extracted_brand', '') == brand_name)
        accuracy_score = int((accuracy_count / len(results) * 50)) if results else 25
        
        return max(accuracy_score - negative_penalty, 0)
    
    def score_consistency(self, results: List[Dict]) -> int:
        """
        一致性评分 (0-100)
        - 跨模型一致性：各模型评价的方差
        - 信息准确度：基于多个维度的综合判断
        """
        if len(results) < 2:
            return 50
        
        # 计算情感得分的方差
        sentiments = [r.get('sentiment', 0) for r in results]
        avg_sentiment = sum(sentiments) / len(sentiments)
        variance = sum((s - avg_sentiment) ** 2 for s in sentiments) / len(sentiments)
        
        # 方差越小，一致性越高
        consistency_score = max(100 - variance * 50, 0)
        
        return round(consistency_score)
```

---

#### 任务 2.2: 问题诊断墙服务实现

**文件**: `backend_python/wechat_backend/services/diagnostic_wall_generator.py`

**实现内容**:
```python
class DiagnosticWallGenerator:
    """问题诊断墙生成器"""
    
    # 风险识别规则
    RISK_RULES = {
        'low_sov': {
            'threshold': 20,
            'level': 'high',
            'text': '声量份额过低',
            'recommendations': [
                '增加品牌曝光渠道，提升内容营销投入',
                '优化 SEO/SEM 策略，提高搜索可见度',
                '与 KOL/KOC 合作，扩大品牌影响力'
            ]
        },
        'negative_sentiment': {
            'threshold': -0.3,
            'level': 'high',
            'text': '负面情感偏高',
            'recommendations': [
                '加强用户关系管理，及时响应用户反馈',
                '优化产品和服务质量，减少负面体验',
                '建立危机公关机制，快速处理负面舆情'
            ]
        },
        'low_rank': {
            'threshold': 3,
            'level': 'medium',
            'text': '排名落后竞品',
            'recommendations': [
                '分析竞品优势，制定差异化策略',
                '加大品牌投入，提升市场声量',
                '优化产品定位，强化核心卖点'
            ]
        },
        'inconsistency': {
            'threshold': 0.5,
            'level': 'medium',
            'text': '模型评价不一致',
            'recommendations': [
                '统一品牌传播口径，确保信息一致性',
                '加强品牌故事建设，提升认知清晰度',
                '监测各渠道品牌呈现，及时纠正偏差'
            ]
        }
    }
    
    def generate(self, metrics: Dict, dimension_scores: Dict) -> Dict:
        """
        生成问题诊断墙
        
        参数:
        - metrics: 核心指标 {sov, sentiment, rank, influence}
        - dimension_scores: 评分维度 {authority, visibility, purity, consistency}
        
        返回:
        {
            'risk_levels': {
                'high': [...],
                'medium': [...],
                'low': [...]
            },
            'priority_recommendations': [...]
        }
        """
        risks = {'high': [], 'medium': [], 'low': []}
        recommendations = []
        
        # 检查声量份额
        if metrics.get('sov', 100) < self.RISK_RULES['low_sov']['threshold']:
            risk_info = self.RISK_RULES['low_sov']
            risks[risk_info['level']].append({
                'type': 'low_sov',
                'text': risk_info['text'],
                'value': metrics.get('sov', 0),
                'threshold': risk_info['threshold']
            })
            recommendations.extend(risk_info['recommendations'])
        
        # 检查情感得分
        if metrics.get('sentiment', 0) < self.RISK_RULES['negative_sentiment']['threshold']:
            risk_info = self.RISK_RULES['negative_sentiment']
            risks[risk_info['level']].append({
                'type': 'negative_sentiment',
                'text': risk_info['text'],
                'value': metrics.get('sentiment', 0),
                'threshold': risk_info['threshold']
            })
            recommendations.extend(risk_info['recommendations'])
        
        # 检查排名
        if metrics.get('rank', 1) > self.RISK_RULES['low_rank']['threshold']:
            risk_info = self.RISK_RULES['low_rank']
            risks[risk_info['level']].append({
                'type': 'low_rank',
                'text': risk_info['text'],
                'value': metrics.get('rank', 0),
                'threshold': risk_info['threshold']
            })
            recommendations.extend(risk_info['recommendations'])
        
        # 检查一致性
        if dimension_scores.get('consistency', 100) < 50:
            risk_info = self.RISK_RULES['inconsistency']
            risks[risk_info['level']].append({
                'type': 'inconsistency',
                'text': risk_info['text'],
                'value': dimension_scores.get('consistency', 0),
                'threshold': 50
            })
            recommendations.extend(risk_info['recommendations'])
        
        # 去重推荐
        unique_recommendations = list(dict.fromkeys(recommendations))
        
        return {
            'risk_levels': risks,
            'priority_recommendations': unique_recommendations[:5]  # 最多 5 条
        }
```

---

## 五、成功指标

### 5.1 产品指标

| 指标 | 当前值 | 目标值 | 提升 | 测量方式 |
|------|-------|-------|------|---------|
| 平均每报告结果数 | 2.97 | ≥10 | +237% | 数据库统计 |
| 核心指标填充率 | 0% | 100% | +100% | 前端检查 |
| 评分维度填充率 | 0% | 100% | +100% | 前端检查 |
| 问题诊断墙填充率 | 0% | 100% | +100% | 前端检查 |

### 5.2 用户体验指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|-------|-------|---------|
| 报告加载时间 | 3-5 秒 | <2 秒 | 前端性能监控 |
| 用户满意度 | - | ≥4.5/5 | 用户调研 |
| 分享率 | - | ≥10% | 分享按钮点击率 |

### 5.3 技术指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|-------|-------|---------|
| API 错误率 | <1% | <0.5% | 后端日志 |
| 页面崩溃率 | <0.5% | <0.1% | 前端监控 |
| 首屏加载时间 | 2 秒 | <1 秒 | 性能测试 |

---

## 六、风险与缓解

### 6.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|-----|------|---------|
| AI API 限流 | 中 | 高 | 多平台负载均衡，增加重试机制 |
| 数据库性能 | 低 | 中 | 索引优化、缓存层引入 |
| 前端兼容性 | 低 | 低 | 充分测试，灰度发布 |
| WebSocket 连接不稳定 | 中 | 中 | HTTP 轮询降级，自动重连 |

### 6.2 产品风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|-----|------|---------|
| 用户不接受默认配置 | 中 | 中 | A/B 测试、用户引导优化 |
| 指标算法不准确 | 中 | 高 | 专家评审、迭代优化、用户反馈 |
| 诊断墙建议过于通用 | 高 | 中 | 结合行业特性定制建议模板 |

### 6.3 实施风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|-----|------|---------|
| 开发进度延迟 | 中 | 中 | 每日站会，及时调整优先级 |
| 测试不充分 | 中 | 高 | 自动化测试，回归测试清单 |
| 上线后发现问题 | 低 | 高 | 灰度发布，快速回滚机制 |

---

## 七、团队协作

### 7.1 角色与职责

| 角色 | 职责 | 人员 |
|------|------|------|
| 首席架构师 | 技术方案设计、代码审查 | - |
| 后端工程师 | API 开发、服务实现 | - |
| 前端工程师 | 页面开发、交互优化 | - |
| 算法工程师 | 指标计算、评分算法 | - |
| 测试工程师 | 测试用例、质量验证 | - |
| 产品经理 | 需求定义、验收测试 | - |

### 7.2 沟通机制

| 会议 | 频率 | 参与人 | 内容 |
|------|------|--------|------|
| 每日站会 | 每天 15min | 全体 | 进度同步、问题暴露 |
| 技术评审 | 每周 1 次 | 技术团队 | 方案评审、代码审查 |
| 产品评审 | 每周 1 次 | 产品 + 技术 | 需求评审、验收演示 |
| 项目复盘 | 每阶段结束 | 全体 | 经验总结、改进计划 |

---

## 八、附录

### 8.1 相关文件

- [API 契约](./api_contract.json)
- [API 规范](./API_Spec_v2.0.json)
- [诊断报告优化计划](./DIAGNOSIS_REPORT_OPTIMIZATION_PLAN.md)
- [P0 架构修复](./P0_ARCHITECTURE_FIX.md)
- [诊断历史优化完成](./DIAGNOSIS_HISTORY_OPTIMIZATION_COMPLETE.md)

### 8.2 数据查询

```sql
-- 诊断报告统计
SELECT status, COUNT(*) as cnt
FROM diagnosis_reports
GROUP BY status;

-- 每报告平均结果数
SELECT AVG(result_count)
FROM (
  SELECT execution_id, COUNT(*) as result_count
  FROM diagnosis_results
  GROUP BY execution_id
);

-- 最近诊断配置
SELECT execution_id, selected_models, custom_questions
FROM diagnosis_reports
ORDER BY created_at DESC
LIMIT 10;
```

### 8.3 术语表

| 术语 | 定义 |
|------|------|
| GEO | Generative Engine Optimization，生成式引擎优化 |
| SOV | Share of Voice，声量份额 |
| N×M | N 个模型 × M 个问题的并发执行模式 |
| WebSocket | 实时双向通信协议 |
| 诊断墙 | 风险识别和建议展示区域 |

---

**文档结束**

---

## 下一步行动

1. **立即行动**（今天）:
   - [ ] 召集团队会议，传达本实施计划
   - [ ] 分配任务，明确责任人
   - [ ] 启动第一阶段（P0 修复）

2. **本周完成**:
   - [ ] 任务 1.1-1.5 全部完成
   - [ ] 通过验收测试

3. **下周完成**:
   - [ ] 任务 2.1-2.5 全部完成
   - [ ] 通过验收测试

4. **持续进行**:
   - [ ] 每日站会同步进度
   - [ ] 每周技术评审
   - [ ] 持续集成和测试

---

**批准人**: _______________  
**日期**: _______________
