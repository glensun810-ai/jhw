# 诊断数据详细导出报告

**导出时间**: 2026-03-15 13:31:31
**诊断执行 ID**: `6d04404f-949d-4513-acb1-0a957a29b4b5`
**品牌**: 趣车良品
**竞品**: ['车尚艺']
**AI 平台**: [{'name': 'deepseek', 'checked': True}]
**诊断时间**: 2026-03-15T12:58:27.310452
**状态**: completed

---

## 1. 诊断报告主数据 (diagnosis_reports)

**保存接口**: `DiagnosisReportRepository.create()`  
**调用位置**: `diagnosis_orchestrator.py` → `_phase_init()`  
**功能说明**: 创建诊断报告主记录，存储基本配置信息

### 保存的详细内容:

```json
{
  "execution_id": "6d04404f-949d-4513-acb1-0a957a29b4b5",
  "brand_name": "趣车良品",
  "status": "completed",
  "stage": "completed",
  "progress": 100,
  "is_completed": 1,
  "created_at": "2026-03-15T12:58:27.310452",
  "updated_at": "2026-03-15T12:59:27.116859"
}
```

---

## 2. AI 响应结果明细 (diagnosis_results)

**保存接口**: `DiagnosisResultRepository.add_batch()`  
**调用位置**: `diagnosis_orchestrator.py` → `_phase_ai_fetching()`  
**功能说明**: 保存各 AI 平台的调用结果和响应内容

### 记录数量：1

### 结果 66 - deepseek 平台

```json
{
  "id": 66,
  "brand": "提前沟通",
  "question": "深圳新能源汽车改装门店推荐?",
  "model": "deepseek",
  "platform": "deepseek",
  "response_content": "好的，作为一名专业的汽车改装顾问，我将基于深圳新能源汽车改装市场的公开信息、行业口碑及服务特点，为您提供客观的推荐。\n\n首先需要明确，新能源汽车改装主要集中在**外观套件、内饰升级、轮毂刹车、避震系统、车身改色贴膜、音响系统以及部分电子功能优化**等领域。由于涉及高压电系统，**动力系统、电池等核心三电的改装存在极高风险且可能违法，正规门店均不提供此类服务**。选择门店时，应重点关注其品牌授权、施工案例、工艺水平和所用产品渠道。\n\n以下是我为您筛选并推荐的深圳地区在新能源汽车改装领域较为突出的 TOP3 品牌/门店：\n\n**TOP 1：车衣裳（全国连锁品牌 - 深圳授权店）**\n*   **推荐理由**：车衣裳是全国领先的汽车改色与车身膜服务连锁品牌，在深圳设有多家授权门店。其优势在于专精于车身外观改装，如改色膜、隐形车衣、个性化拉花等，拥有丰富的色号库和成熟的施工团队。对于希望改变车辆外观、提升个性与保护原厂漆面的新能源车主来说，他们是专业且可靠的选择。品牌标准化流程和质保体系完善，售后有保障。\n\n**TOP 2：ATLAS阿特拉斯汽车服务（深圳本土知名综合改装店）**\n*   **推荐理由**：ATLAS是深圳本土成长起来的高端汽车服务与改装综合门店，在资深车友中口碑良好。他们不仅提供专业的车身贴膜服务，更擅长于轮毂升级、刹车系统改装、避震调校以及高性能轮胎搭配。对于追求操控提升和个性化姿态的新能源车主（尤其是特斯拉、蔚来、极氪等性能车型车主），ATLAS具备丰富的方案设计和安装调试经验，能够提供一站式、系统化的性能与外观升级解决方案。\n\n**TOP 3：UPPF优帕（高端漆面保护膜品牌 - 深圳运营中心）**\n*   **推荐理由**：如果您的主要需求是保护原厂车漆并提升漆面亮度，UPPF是专注于高端隐形车衣（PPF）的知名品牌。其在深圳的运营中心或授权施工商通常拥有无尘施工车间和经过严格认证的技师。对于车价较高、注重漆面长期维护的新能源汽车车主而言，选择这类品牌专营店，能在产品真伪、施工质量和官方质保（如耐黄变、抗腐蚀、划痕自修复等）方面获得更直接的保障，施工专注度更高。\n\n**重要提示**：\n1.  **提前沟通**：改装前务必与门店详细沟通方案、所用产品品牌型号、价格及施工周期，并确认是否影响原厂质保（尤其是涉及电路或拆卸的改装）。\n2.  **合法合规**：所有改装项目必须符合《道路交通安全法》规定，完成外观明显变更（如改色）后需及时到车管所备案。\n3.  **多方考察**：建议通过各大汽车论坛、社交媒体平台查看目标门店的实际案例和用户评价，并亲自到店考察环境与设备。\n\n除了以上三家，深圳还有如“酷车小镇”等聚集了多家改装服务商的汽车文化园区，以及“名车汇”等老牌综合服务商，也提供相关服务，您可以根据具体需求进一步了解和比较。\n\n{\"top3_brands\": [{\"name\": \"车衣裳（深圳授权店）\", \"rank\": 1, \"reason\": \"全国连锁专业改色贴膜品牌，标准化施工与完善质保，专精于车身外观个性化与保护，适合新能源车主改变外观与护漆需求。\"}, {\"name\": \"ATLAS阿特拉斯汽车服务\", \"rank\": 2, \"reason\": \"深圳本土知名高端综合改装店，擅长轮毂、刹车、避震系统升级与调校，提供一站式性能与外观方案，在性能车型车主中口碑良好。\"}, {\"name\": \"UPPF优帕（深圳运营中心）\", \"rank\": 3, \"reason\": \"高端隐形车衣（PPF）专营品牌，专注漆面保护，拥有认证施工环境与技师，为注重原厂漆面长期维护的高价值新能源车主提供可靠产品与质保。\"}], \"total_brands_mentioned\": 5}",
  "extracted_brand": "提前沟通",
  "status": "success",
  "finish_reason": "stop",
  "tokens_used": 0,
  "quality_score": 0.0,
  "quality_level": "unknown",
  "geo_data": null,
  "response_metadata": null,
  "reasoning_content": null,
  "request_id": null,
  "response_latency": 45.82740592956543,
  "sentiment": "neutral",
  "created_at": "2026-03-15T12:59:13.165028"
}
```

---

## 3. 诊断分析数据 (diagnosis_analysis)

**保存接口**: `DiagnosisAnalysisRepository.add()` / `DiagnosisTransaction.add_analysis()`  
**调用位置**: `diagnosis_orchestrator.py` → `_phase_complete()`  
**功能说明**: 保存后台分析模块生成的分析结果

### 分析记录数量：2

### 分析类型：brand_analysis

**analysis_id**: 93  
**保存内容**:

```json
{
  "success": true,
  "data": {
    "user_brand_analysis": {
      "brand": "趣车良品",
      "mentions": [
        {
          "brand_mentioned": false,
          "rank": -1,
          "sentiment": 0,
          "is_top3": false,
          "mention_context": ""
        }
      ],
      "mentioned_count": 0,
      "total_responses": 1,
      "mention_rate": 0.0,
      "average_rank": -1,
      "average_sentiment": 0,
      "is_top3": false
    },
    "competitor_analysis": [
      {
        "brand": "车尚艺",
        "mentions": [
          {
            "brand_mentioned": false,
            "rank": -1,
            "sentiment": 0,
            "is_top3": false,
            "mention_context": ""
          }
        ],
        "mentioned_count": 0,
        "mention_rate": 0.0,
        "average_rank": -1,
        "average_sentiment": 0,
        "is_top3": false
      }
    ],
    "comparison": {
      "user_brand": "趣车良品",
      "mention_rate": 0.0,
      "average_rank": -1,
      "average_sentiment": 0,
      "is_top3": false,
      "vs_competitors": [
        {
          "competitor": "车尚艺",
          "mention_rate_diff": 0.0,
          "rank_diff": 0,
          "sentiment_diff": 0,
          "advantage": "表现相当"
        }
      ],
      "summary": "趣车良品在 AI 推荐中提及较少（0%）"
    },
    "top3_brands": [
      {
        "name": "车衣裳（深圳授权店）",
        "rank": 1,
        "reason": "全国连锁专业改色贴膜品牌，标准化施工与完善质保，专精于车身外观个性化与保护，适合新能源车主改变外观与护漆需求。"
      },
      {
        "name": "ATLAS阿特拉斯汽车服务",
        "rank": 2,
        "reason": "深圳本土知名高端综合改装店，擅长轮毂、刹车、避震系统升级与调校，提供一站式性能与外观方案，在性能车型车主中口碑良好。"
      },
      {
        "name": "UPPF优帕（深圳运营中心）",
        "rank": 3,
        "reason": "高端隐形车衣（PPF）专营品牌，专注漆面保护，拥有认证施工环境与技师，为注重原厂漆面长期维护的高价值新能源车主提供可靠产品与质保。"
      }
    ]
  },
  "brand": "趣车良品",
  "duration_seconds": 13.474903
}
```

### 分析类型：competitive_analysis

**analysis_id**: 94  
**保存内容**:

```json
{
  "success": true,
  "data": {
    "brand_scores": {
      "提前沟通": {
        "overallScore": 0,
        "overallGrade": "D"
      }
    },
    "first_mention_by_platform": {},
    "interception_risks": {
      "level": "medium",
      "description": "中等风险"
    },
    "main_brand": "趣车良品",
    "competitor_brands": [
      "车尚艺"
    ]
  },
  "main_brand": "趣车良品",
  "duration_seconds": 0.003651
}
```

---

## 4. 诊断报告快照 (diagnosis_snapshots)

**保存接口**: `DiagnosisReportRepository.create_snapshot()`  
**调用位置**: `diagnosis_report_service.py` → `complete_report()`  
**功能说明**: 创建诊断完成时的完整数据快照，用于归档和快速检索

### 快照记录数量：1

### 快照 55 - completed

**创建时间**: 2026-03-15T12:59:27.111741  
**快照数据结构**:

```json
{
  "snapshot_reason": "completed",
  "created_at": "2026-03-15T12:59:27.111741",
  "data_keys": [
    "report",
    "results",
    "analysis"
  ],
  "report_keys": [],
  "results_count": 0,
  "analysis_keys": []
}
```

---

## 5. 数据保存汇总表

| 数据表 | 保存接口 | 调用位置 | 功能模块 | 记录数 | 状态 |
|--------|---------|---------|---------|--------|------|
| diagnosis_reports | `DiagnosisReportRepository.create()` | `_phase_init()` | 报告创建 | 1 | ✅ |
| diagnosis_results | `DiagnosisResultRepository.add_batch()` | `_phase_ai_fetching()` | AI 调用 | 1 | ✅ |
| diagnosis_analysis | `DiagnosisAnalysisRepository.add()` | `_phase_complete()` | 后台分析 | 2 | ✅ |
| diagnosis_snapshots | `DiagnosisReportRepository.create_snapshot()` | `complete_report()` | 报告归档 | 1 | ✅ |

---

## 6. 调用链路图

```
用户请求诊断
    ↓
DiagnosisOrchestrator.execute()
    ↓
┌─────────────────────────────────────────┐
│ Phase 1: _phase_init()                  │
│ └─ DiagnosisReportRepository.create()   │ → diagnosis_reports
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Phase 2: _phase_ai_fetching()           │
│ └─ DiagnosisResultRepository.add_batch()│ → diagnosis_results
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Phase 6: _phase_complete()              │
│ └─ DiagnosisTransaction.add_analysis()  │ → diagnosis_analysis
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Phase 7: complete_report()              │
│ └─ DiagnosisReportRepository.create_    │ → diagnosis_snapshots
│    snapshot()                           │
└─────────────────────────────────────────┘
    ↓
诊断完成，返回结果
```

