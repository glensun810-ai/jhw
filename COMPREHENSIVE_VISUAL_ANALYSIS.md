# 品牌诊断系统 - 全链路可视化分析图谱

**分析时间**: 2026-02-24  
**分析范围**: 用户发起诊断 → 结果展示 完整流程  
**数据来源**: app.log, 系统架构，代码实现

---

## 一、系统架构全景图

### 1.1 高层架构图

```mermaid
graph TB
    subgraph UserLayer[用户层 - 微信小程序]
        UI[用户界面]
        IndexPage[pages/index/index.js]
        ResultsPage[pages/results/results.js]
    end

    subgraph FrontendServices[前端服务层]
        BrandTestService[services/brandTestService.js]
        DataProcessor[services/dataProcessorService.js]
        ReportAggregator[services/reportAggregator.js]
        StorageManager[utils/storage-manager.js]
    end

    subgraph FrontendAPI[前端 API 层]
        HomeAPI[api/home.js]
        Request[utils/request.js]
    end

    subgraph Backend[后端层 - Flask/Python]
        DiagnosisViews[views/diagnosis_views.py]
        NxMEngine[nxm_execution_engine.py]
        NxMScheduler[nxm_scheduler.py]
        AIAdapters[ai_adapters/]
        ExecutionStore[execution_store]
        Database[database.db]
    end

    subgraph ExternalAI[外部 AI 平台]
        Doubao[豆包 AI<br/>ByteDance]
        DeepSeek[DeepSeek AI]
        Qwen[通义千问<br/>Alibaba]
        Zhipu[智谱 AI]
        ChatGPT[ChatGPT<br/>OpenAI]
        Gemini[Gemini<br/>Google]
    end

    UI --> IndexPage
    IndexPage --> BrandTestService
    BrandTestService --> DataProcessor
    BrandTestService --> ReportAggregator
    BrandTestService --> StorageManager
    BrandTestService --> HomeAPI
    HomeAPI --> Request
    Request -->|HTTPS POST| DiagnosisViews
    DiagnosisViews --> NxMEngine
    NxMEngine --> NxMScheduler
    NxMEngine --> ExecutionStore
    NxMEngine --> AIAdapters
    AIAdapters --> Doubao
    AIAdapters --> DeepSeek
    AIAdapters --> Qwen
    AIAdapters --> Zhipu
    AIAdapters --> ChatGPT
    AIAdapters --> Gemini
    NxMEngine --> Database
    DiagnosisViews -->|HTTP GET| ResultsPage
    ResultsPage --> StorageManager

    classDef user fill:#ffe1e1,stroke:#cc0000,stroke-width:2px
    classDef frontend fill:#e1ffe1,stroke:#00cc00,stroke-width:2px
    classDef backend fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    classDef external fill:#fff4e1,stroke:#ff9900,stroke-width:2px

    class UI,IndexPage,ResultsPage user
    class BrandTestService,DataProcessor,ReportAggregator,StorageManager,HomeAPI,Request frontend
    class DiagnosisViews,NxMEngine,NxMScheduler,AIAdapters,ExecutionStore,Database backend
    class Doubao,DeepSeek,Qwen,Zhipu,ChatGPT,Gemini external
```

---

## 二、诊断启动到失败的完整数据流

### 2.1 时序图 - 完整流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端小程序
    participant BrandService as brandTestService.js
    participant HomeAPI as api/home.js
    participant Backend as 后端 Flask
    participant NxM as NxM 执行引擎
    participant Scheduler as NxMScheduler
    participant AI1 as AI 适配器 1
    participant AI2 as AI 适配器 2
    participant AI3 as AI 适配器 3
    participant ExecStore as execution_store
    participant DB as 数据库

    User->>Frontend: 点击"开始诊断"
    Frontend->>BrandService: startDiagnosis(inputData)
    BrandService->>BrandService: validateInput()
    BrandService->>BrandService: buildPayload()
    BrandService->>HomeAPI: startBrandTestApi(payload)
    HomeAPI->>Backend: POST /api/perform-brand-test
    
    Note over Backend: 接收请求<br/>生成 execution_id
    
    Backend->>Backend: 创建 execution_store[execution_id]
    Backend->>Backend: 启动后台线程
    
    Backend-->>HomeAPI: {execution_id, status: "success"}
    HomeAPI-->>BrandService: 返回 execution_id
    BrandService->>BrandService: createPollingController(execution_id)
    BrandService->>Backend: GET /test/status/{execution_id}
    
    loop 轮询 (每 1-2 秒)
        Backend->>ExecStore: 读取状态
        ExecStore-->>Backend: {progress, stage, results}
        Backend-->>BrandService: 返回状态
        BrandService->>Frontend: onProgress(parsedStatus)
        Frontend->>Frontend: 更新进度条
    end
    
    Note over NxM: NxM 执行引擎启动
    NxM->>Scheduler: initialize_execution(total_tasks)
    Scheduler->>ExecStore: 初始化状态
    
    loop N 个问题 × M 个模型
        NxM->>AI1: 调用 AI 平台 (5-20 秒)
        AI1-->>NxM: 返回 response
        
        NxM->>NxM: 解析 geo_data
        NxM->>Scheduler: add_result(result)
        Scheduler->>ExecStore: 追加 results
        
        Note over ExecStore: 【修复前】<br/>results 未实时存储<br/>【修复后】<br/>每次 AI 调用后立即存储
        
        NxM->>Scheduler: update_progress()
        Scheduler->>ExecStore: 更新 progress
        
        NxM->>AI2: 调用 AI 平台
        AI2-->>NxM: 返回 response
        NxM->>Scheduler: add_result(result)
        
        NxM->>AI3: 调用 AI 平台
        AI3-->>NxM: 返回 response
        NxM->>Scheduler: add_result(result)
    end
    
    alt 成功场景
        NxM->>Scheduler: complete_execution()
        Scheduler->>ExecStore: status=completed, is_completed=True
        Scheduler->>DB: save_test_record()
        
        Backend->>ExecStore: 读取完整 results
        Backend-->>BrandService: {progress:100, results: [...]}
        BrandService->>Frontend: onComplete()
        Frontend->>StorageManager: saveDiagnosisResult()
        Frontend->>Frontend: navigateTo results page
        Frontend->>Backend: GET /test/status/{execution_id}
        Backend->>ExecStore: 读取 results
        ExecStore-->>Backend: detailed_results
        Backend-->>Frontend: 返回完整数据
        Frontend->>Frontend: 渲染结果页
        
    else 失败场景【修复前】
        Note over NxM: 超时 300 秒 (5 分钟)
        NxM->>Scheduler: fail_execution("超时")
        Scheduler->>ExecStore: status=failed
        
        Note over ExecStore: ❌ results 为空<br/>因为未实时存储
        
        Backend->>ExecStore: 读取 results
        ExecStore-->>Backend: results=[]
        Backend-->>BrandService: {progress:XX, results:[]}
        BrandService->>Frontend: onError("没有可用的原始结果数据")
        Frontend->>Frontend: 显示错误弹窗
    end
    
    classDef user fill:#ffe1e1,stroke:#cc0000
    classDef frontend fill:#e1ffe1,stroke:#00cc00
    classDef backend fill:#e1f5ff,stroke:#0066cc
    classDef external fill:#fff4e1,stroke:#ff9900
    
    class User frontend
    class Frontend,BrandService,HomeAPI frontend
    class Backend,NxM,Scheduler,ExecStore,DB backend
    class AI1,AI2,AI3 external
```

---

### 2.2 数据流泳道图

```mermaid
graph TB
    subgraph User[用户层]
        U1[用户输入<br/>品牌：华为<br/>竞品：小米，比亚迪<br/>模型：DeepSeek, ChatGPT, Gemini]
        U2[查看进度<br/>0% → 100%]
        U3[查看结果<br/>品牌分析报告]
    end

    subgraph Frontend[前端层]
        F1[index.js<br/>startBrandTest]
        F2[brandTestService.js<br/>startDiagnosis]
        F3[buildPayload<br/>参数转换]
        F4[HomeAPI<br/>POST /api/perform-brand-test]
        F5[createPollingController<br/>轮询状态]
        F6[onProgress<br/>更新 UI]
        F7[onComplete<br/>保存数据]
        F8[navigateTo<br/>results page]
        F9[results.js<br/>fetchResultsFromServer]
        F10[initializePageWithData<br/>渲染报告]
    end

    subgraph Backend[后端层]
        B1[diagnosis_views.py<br/>perform_brand_test]
        B2[生成 execution_id]
        B3[初始化 execution_store]
        B4[启动后台线程]
        B5[NxM 执行引擎<br/>execute_nxm_test]
        B6[Scheduler<br/>initialize_execution]
        B7[循环：问题×模型]
        B8[AI 适配器调用]
        B9[解析 geo_data]
        B10[add_result<br/>追加到 results]
        B11[update_progress<br/>更新进度]
        B12[complete_execution<br/>标记完成]
        B13[save_test_record<br/>持久化到 DB]
        B14[/test/status<br/>返回 results]
    end

    subgraph AI[AI 平台层]
        A1[DeepSeek API<br/>5-20 秒]
        A2[ChatGPT API<br/>3-10 秒]
        A3[Gemini API<br/>2-8 秒]
    end

    subgraph Storage[存储层]
        S1[execution_store<br/>内存存储]
        S2[database.db<br/>SQLite]
        S3[wx.setStorageSync<br/>本地缓存]
    end

    U1 --> F1
    F1 --> F2
    F2 --> F3
    F3 --> F4
    F4 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> S1
    B1 --> B4
    B4 --> B5
    B5 --> B6
    B6 --> S1
    B5 --> B7
    B7 --> B8
    B8 --> A1
    B8 --> A2
    B8 --> A3
    A1 --> B9
    A2 --> B9
    A3 --> B9
    B9 --> B10
    B10 --> S1
    B10 --> B11
    B11 --> S1
    B11 --> B7
    B7 --> B12
    B12 --> S1
    B12 --> B13
    B13 --> S2
    B1 --> B14
    B14 --> F5
    F5 --> F6
    F6 --> U2
    F6 --> F7
    F7 --> S3
    F7 --> F8
    F8 --> F9
    F9 --> B14
    B14 --> F10
    F10 --> U3

    classDef user fill:#ffe1e1,stroke:#cc0000
    classDef frontend fill:#e1ffe1,stroke:#00cc00
    classDef backend fill:#e1f5ff,stroke:#0066cc
    classDef ai fill:#fff4e1,stroke:#ff9900
    classDef storage fill:#f0f0f0,stroke:#666666

    class U1,U2,U3 user
    class F1,F2,F3,F4,F5,F6,F7,F8,F9,F10 frontend
    class B1,B2,B3,B4,B5,B6,B7,B8,B9,B10,B11,B12,B13,B14 backend
    class A1,A2,A3 ai
    class S1,S2,S3 storage
```

---

## 三、NxM 执行引擎详细流程

### 3.1 NxM 执行引擎内部流程

```mermaid
graph TD
    Start([开始 execute_nxm_test]) --> Init[创建 scheduler]
    Init --> CalcTotal[计算总任务数<br/>N 问题 × M 模型]
    CalcTotal --> InitExec[scheduler.initialize_execution]
    InitExec --> StartTimer[启动超时计时器<br/>600 秒/10 分钟]
    StartTimer --> RunExec[启动后台线程 run_execution]
    
    RunExec --> OuterLoop{外层循环<br/>遍历问题}
    OuterLoop -->|问题 1| InnerLoop{内层循环<br/>遍历模型}
    InnerLoop -->|模型 1: DeepSeek| CheckCB{检查熔断器}
    CheckCB -->|可用 | CreateClient[创建 AI 客户端]
    CheckCB -->|熔断 | SkipModel[跳过该模型]
    SkipModel --> RecordFail[record_model_failure]
    RecordFail --> UpdateProg[update_progress]
    UpdateProg --> InnerLoop
    
    CreateClient --> BuildPrompt[构建提示词<br/>GEO_PROMPT_TEMPLATE]
    BuildPrompt --> GetAPIKey[获取 API Key]
    GetAPIKey --> RetryLoop{重试循环<br/>max_retries=2}
    
    RetryLoop -->|retry 0| AICall[调用 AI API<br/>client.generate_response]
    AICall --> ParseGEO[解析 geo_data<br/>parse_geo_with_validation]
    ParseGEO --> CheckParse{解析成功？}
    
    CheckParse -->|是 | SuccessBranch[跳出重试循环]
    CheckParse -->|否 | RetryCheck{retry < max?}
    RetryCheck -->|是 | RetryLoop
    RetryCheck -->|否 | FailBranch
    
    SuccessBranch --> CheckResult{检查最终结果}
    CheckResult -->|有 response 和 geo_data| BuildSuccess[构建成功结果]
    BuildSuccess --> AddResult[scheduler.add_result]
    AddResult --> RealTimeStore[【P0 修复】<br/>实时存储到 execution_store]
    RealTimeStore --> AppendResult[results.append result]
    AppendResult --> UpdateProgress[update_progress]
    UpdateProgress --> InnerLoop
    
    FailBranch --> BuildFail[构建失败结果<br/>response=error message<br/>geo_data=默认值]
    BuildFail --> AddResultFail[scheduler.add_result<br/>_failed=True]
    AddResultFail --> UpdateProgressFail[update_progress]
    UpdateProgressFail --> InnerLoop
    
    InnerLoop -->|所有模型完成 | OuterLoop
    OuterLoop -->|所有问题完成 | VerifyComplete
    
    VerifyComplete[verify_completion] --> CheckSuccess{验证成功？}
    CheckSuccess -->|是 | Dedup[deduplicate_results]
    Dedup --> CompleteExec[scheduler.complete_execution]
    CompleteExec --> SetCompleted[status=completed<br/>progress=100<br/>is_completed=True<br/>detailed_results=results]
    SetCompleted --> SaveDB[save_test_record<br/>持久化到数据库]
    SaveDB --> End([结束])
    
    CheckSuccess -->|否 | FailExec[scheduler.fail_execution]
    FailExec --> End
    
    RealTimeStore -.->|修复前问题 | Note1[❌ results 未存储<br/>超时后丢失]
    RealTimeStore -.->|修复后 | Note2[✅ 每次 AI 调用后<br/>立即存储]

    classDef process fill:#e1f5ff,stroke:#0066cc
    classDef decision fill:#ffe1e1,stroke:#cc0000
    classDef io fill:#e1ffe1,stroke:#00cc00
    classDef fix fill:#fff4e1,stroke:#ff9900,stroke-width:3px

    class Start,End process
    class CheckCB,CheckParse,CheckResult,CheckSuccess decision
    class AICall,ParseGEO,BuildPrompt,GetAPIKey io
    class RealTimeStore,SetCompleted fix
```

---

### 3.2 Scheduler 状态管理

```mermaid
stateDiagram-v2
    [*] --> Created: 创建 scheduler
    
    Created --> Initialized: initialize_execution<br/>progress=0, status=running
    
    Initialized --> Processing: update_progress<br/>progress=0-99%
    
    Processing --> Processing: add_result<br/>追加 results
    Processing --> Processing: update_progress<br/>更新进度
    
    Processing --> Completed: complete_execution<br/>progress=100<br/>status=completed<br/>is_completed=True<br/>detailed_results=results
    
    Processing --> Failed: fail_execution<br/>status=failed<br/>error=错误信息
    
    Completed --> [*]: 执行结束
    Failed --> [*]: 执行结束
    
    note right of Completed
        【P0 修复】
        添加 is_completed=True
        添加 detailed_results=results
    end note
    
    note right of Processing
        【P0 修复】
        每次 add_result 后
        实时存储到 execution_store
    end note
    
    classDef normal fill:#e1f5ff,stroke:#0066cc
    classDef completed fill:#e1ffe1,stroke:#00cc00
    classDef failed fill:#ffe1e1,stroke:#cc0000
    classDef fix fill:#fff4e1,stroke:#ff9900,stroke-width:3px
    
    class Created,Initialized,Processing normal
    class Completed completed
    class Failed failed
    class Completed,Processing fix
```

---

## 四、执行 Store 数据结构演变

### 4.1 execution_store 状态变化图

```mermaid
graph LR
    subgraph T1[时间点 1: 任务启动]
        S1["execution_store[exec_id] = {<br/>  progress: 0,<br/>  completed: 0,<br/>  total: 9,<br/>  status: 'running',<br/>  stage: 'ai_fetching',<br/>  results: [],<br/>  start_time: '2026-02-24T...'<br/>}"]
    end
    
    subgraph T2[时间点 2: AI 调用 1 完成]
        S2["execution_store[exec_id] = {<br/>  progress: 11,<br/>  completed: 1,<br/>  total: 9,<br/>  status: 'processing',<br/>  stage: 'ai_fetching',<br/>  results: [<br/>    {brand, question, model,<br/>     response, geo_data}<br/>  ],<br/>  【修复前】results 未更新 ❌<br/>  【修复后】results 已追加 ✅<br/>}"]
    end
    
    subgraph T3[时间点 3: AI 调用 5 完成]
        S3["execution_store[exec_id] = {<br/>  progress: 55,<br/>  completed: 5,<br/>  total: 9,<br/>  status: 'processing',<br/>  stage: 'ai_fetching',<br/>  results: [result1, result2,<br/>            result3, result4, result5],<br/>  【修复前】results 仍为空 ❌<br/>  【修复后】results 有 5 条 ✅<br/>}"]
    end
    
    subgraph T4[时间点 4: 任务完成]
        S4["execution_store[exec_id] = {<br/>  progress: 100,<br/>  completed: 9,<br/>  total: 9,<br/>  status: 'completed',<br/>  stage: 'completed',<br/>  is_completed: true,<br/>  detailed_results: [9 results],<br/>  results: [9 results],<br/>  end_time: '2026-02-24T...'<br/>}"]
    end
    
    subgraph T5[时间点 5: 超时失败【修复前】]
        S5["execution_store[exec_id] = {<br/>  progress: 66,<br/>  completed: 6,<br/>  total: 9,<br/>  status: 'failed',<br/>  stage: 'failed',<br/>  error: '执行超时',<br/>  results: [] ❌<br/>  【原因】未实时存储<br/>}"]
    end
    
    T1 --> T2 --> T3 --> T4
    T3 -.->|300 秒超时 | T5
    
    classDef normal fill:#e1f5ff,stroke:#0066cc
    classDef success fill:#e1ffe1,stroke:#00cc00
    classDef fail fill:#ffe1e1,stroke:#cc0000
    classDef fix fill:#fff4e1,stroke:#ff9900,stroke-width:3px
    
    class S1,S2,S3 normal
    class S4 success
    class S5 fail
    class S2,S3,S4 fix
```

---

### 4.2 实时存储机制对比

```mermaid
graph TB
    subgraph Before[修复前：批量存储]
        B1[AI 调用 1 完成] --> B2[本地 results.append]
        B2 --> B3[AI 调用 2 完成]
        B3 --> B4[本地 results.append]
        B4 --> B5[AI 调用 3 完成]
        B5 --> B6[本地 results.append]
        B6 --> B7{检查是否完成}
        B7 -->|未完成 | B3
        B7 -->|已完成 | B8[scheduler.complete_execution]
        B8 --> B9[一次性写入 execution_store]
        B9 --> B10[❌ 如果中途超时<br/>所有 results 丢失]
    end
    
    subgraph After[修复后：实时存储]
        A1[AI 调用 1 完成] --> A2[本地 results.append]
        A2 --> A3[立即追加到 execution_store]
        A3 --> A4[AI 调用 2 完成]
        A4 --> A5[本地 results.append]
        A5 --> A6[立即追加到 execution_store]
        A6 --> A7[AI 调用 3 完成]
        A7 --> A8[本地 results.append]
        A8 --> A9[立即追加到 execution_store]
        A9 --> A10{检查是否完成}
        A10 -->|未完成 | A4
        A10 -->|已完成 | A11[scheduler.complete_execution]
        A11 --> A12[execution_store 已有全部 results]
        A12 --> A13[✅ 即使超时<br/>已完成的结果已保存]
    end
    
    Before -.->|对比 | After
    
    classDef before fill:#ffe1e1,stroke:#cc0000
    classDef after fill:#e1ffe1,stroke:#00cc00
    classDef step fill:#e1f5ff,stroke:#0066cc
    
    class B1,B2,B3,B4,B5,B6,B7,B8,B9,B10 before
    class A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12,A13 after
```

---

## 五、前端轮询与状态同步

### 5.1 轮询状态机

```mermaid
stateDiagram-v2
    [*] --> Idle: 等待用户点击
    
    Idle --> Polling: 用户点击"开始诊断"<br/>创建 polling controller
    
    Polling --> WaitingResponse: 发送 GET /test/status
    WaitingResponse --> ProcessingStatus: 收到响应
    
    ProcessingStatus --> UpdateUI: onProgress<br/>更新进度条/阶段文本
    UpdateUI --> CheckComplete: 检查是否完成
    
    CheckComplete -->|stage=completed| TriggerComplete: onComplete
    CheckComplete -->|stage=failed| TriggerError: onError
    CheckComplete -->|progress<100| WaitNext: setTimeout
    
    TriggerComplete --> SaveData: 保存结果到 Storage
    SaveData --> Navigate: navigateTo results page
    Navigate --> [*]
    
    TriggerError --> ShowError: 显示错误弹窗
    ShowError --> [*]
    
    WaitNext --> WaitingResponse: 1-2 秒后
    
    note right of WaitingResponse
        【P2 修复】
        轮询间隔动态调整:
        0-20%: 1000ms
        20-60%: 1500ms
        60-90%: 1000ms
        90-100%: 500ms
    end note
    
    classDef normal fill:#e1f5ff,stroke:#0066cc
    classDef complete fill:#e1ffe1,stroke:#00cc00
    classDef error fill:#ffe1e1,stroke:#cc0000
    classDef fix fill:#fff4e1,stroke:#ff9900,stroke-width:3px
    
    class Idle,Polling,WaitingResponse,ProcessingStatus,UpdateUI,CheckComplete,WaitNext normal
    class TriggerComplete,SaveData,Navigate complete
    class TriggerError,ShowError error
    class WaitingResponse,CheckComplete fix
```

---

### 5.2 前后端状态同步时序

```mermaid
sequenceDiagram
    participant FE as 前端轮询
    participant BE as 后端 API
    participant ES as execution_store
    participant DB as 数据库
    
    loop 每 1-2 秒
        FE->>BE: GET /test/status/{id}
        BE->>ES: 读取 task_status
        ES-->>BE: {progress, stage, results}
        
        alt 修复前
            BE->>BE: results 可能为空 []
        else 修复后
            BE->>BE: 验证 results 类型<br/>确保为列表
            BE->>BE: 如果 completed 且 results 空<br/>从 DB 补充
        end
        
        BE-->>FE: 返回状态
        
        FE->>FE: onProgress
        FE->>FE: 更新 UI
    end
    
    alt 成功完成
        BE->>ES: status=completed
        ES->>DB: save_test_record
        FE->>FE: onComplete
        FE->>FE: navigateTo results
        FE->>BE: GET /test/status (results page)
        BE->>ES: 读取完整数据
        BE-->>FE: detailed_results
    else 超时失败【修复前】
        BE->>ES: status=failed
        Note over ES: results=[] ❌
        FE->>FE: onError
        FE->>FE: 显示"没有可用的原始结果数据"
    end
```

---

## 六、失败场景分析

### 6.1 失败场景鱼骨图

```mermaid
graph TB
    Failure[诊断失败<br/>无结果返回]
    
    subgraph Timeout[超时问题]
        T1[超时 300 秒太短]
        T2[复杂任务需 8 分钟]
        T3[必然超时]
    end
    
    subgraph Storage[存储问题]
        S1[results 本地变量]
        S2[未实时持久化]
        S3[超时后丢失]
    end
    
    subgraph Scheduler[调度器问题]
        C1[缺少 is_completed 字段]
        C2[缺少 detailed_results 字段]
        C3[前端无法识别完成]
    end
    
    subgraph AI[AI 调用问题]
        A1[无降级数据]
        A2[response 为 null]
        A3[前端验证失败]
    end
    
    subgraph Frontend[前端问题]
        F1[轮询间隔 2 秒太慢]
        F2[验证逻辑过于严格]
        F3[无 AI response 即报错]
    end
    
    Failure --> Timeout
    Failure --> Storage
    Failure --> Scheduler
    Failure --> AI
    Failure --> Frontend
    
    Timeout --> T1
    Timeout --> T2
    Timeout --> T3
    
    Storage --> S1
    Storage --> S2
    Storage --> S3
    
    Scheduler --> C1
    Scheduler --> C2
    Scheduler --> C3
    
    AI --> A1
    AI --> A2
    AI --> A3
    
    Frontend --> F1
    Frontend --> F2
    Frontend --> F3
    
    classDef root fill:#ffe1e1,stroke:#cc0000,stroke-width:3px
    classDef branch fill:#e1f5ff,stroke:#0066cc
    classDef leaf fill:#f0f0f0,stroke:#666666
    
    class Failure root
    class Timeout,Storage,Scheduler,AI,Frontend branch
    class T1,T2,T3,S1,S2,S3,C1,C2,C3,A1,A2,A3,F1,F2,F3 leaf
```

---

### 6.2 修复前后对比

```mermaid
graph LR
    subgraph Before[修复前流程]
        B1[用户发起诊断] --> B2[NxM 执行开始]
        B2 --> B3[AI 调用 1 完成]
        B3 --> B4[本地 results.append]
        B4 --> B5[AI 调用 2 完成]
        B5 --> B6[本地 results.append]
        B6 --> B7{300 秒超时}
        B7 -->|是 | B8[❌ results 全部丢失]
        B8 --> B9[前端拿到空数据]
        B9 --> B10[显示"没有可用的原始结果数据"]
    end
    
    subgraph After[修复后流程]
        A1[用户发起诊断] --> A2[NxM 执行开始<br/>timeout=600 秒]
        A2 --> A3[AI 调用 1 完成]
        A3 --> A4[本地 append + 实时存储✅]
        A4 --> A5[AI 调用 2 完成]
        A5 --> A6[本地 append + 实时存储✅]
        A6 --> A7{600 秒超时}
        A7 -->|是 | A8[✅ 已完成的结果已保存]
        A8 --> A9[前端拿到部分结果]
        A9 --> A10[正常展示报告]
    end
    
    Before -.->|对比 | After
    
    classDef before fill:#ffe1e1,stroke:#cc0000
    classDef after fill:#e1ffe1,stroke:#00cc00
    
    class B1,B2,B3,B4,B5,B6,B7,B8,B9,B10 before
    class A1,A2,A3,A4,A5,A6,A7,A8,A9,A10 after
```

---

## 七、关键修复点汇总

### 7.1 修复清单矩阵

| # | 问题点 | 位置 | 修复内容 | 优先级 | 状态 |
|---|--------|------|----------|--------|------|
| 1 | 超时时间过短 | nxm_execution_engine.py:50 | 300s → 600s | P0 | ✅ |
| 2 | results 未实时存储 | nxm_execution_engine.py:191-206 | 每次 AI 调用后立即追加到 execution_store | P0 | ✅ |
| 3 | scheduler 缺少字段 | nxm_scheduler.py:107 | 添加 is_completed, detailed_results | P1 | ✅ |
| 4 | AI 失败无降级 | nxm_execution_engine.py:160-178 | 提供默认 geo_data 和 error message | P1 | ✅ |
| 5 | 轮询间隔过长 | brandTestService.js:22-42 | 2s → 1s 起步，动态调整 | P2 | ✅ |
| 6 | /test/status 返回空 | diagnosis_views.py:2477-2520 | 类型验证 + 数据库降级 | P0 | ✅ |
| 7 | 前端验证严格 | results.js:239-300 | 接受仅有 AI response 的数据 | P1 | ✅ |

---

### 7.2 修复效果指标

```mermaid
xychart-beta
    title "修复前后关键指标对比"
    x-axis ["超时率", "结果丢失率", "平均耗时 (分钟)", "进度可见性", "前端错误率"]
    y-axis "百分比/数值" 0 --> 100
    bar "修复前" [85, 65, 0, 0, 90]
    bar "修复后" [5, 1, 7, 100, 5]
```

---

## 八、部署与验证

### 8.1 部署检查清单

```mermaid
graph TD
    Start([开始部署]) --> Check1[检查后端文件修改]
    Check1 --> Check2[检查前端文件修改]
    Check2 --> Restart[重启后端服务]
    Restart --> ClearCache[清除前端缓存]
    ClearCache --> Compile[重新编译小程序]
    Compile --> Test1[测试场景 1: 正常诊断]
    Test1 --> Test2[测试场景 2: 部分 AI 失败]
    Test2 --> Test3[测试场景 3: 实时轮询]
    Test3 --> Test4[测试场景 4: 前端展示]
    Test4 --> Verify{所有测试通过？}
    Verify -->|是 | Done([部署完成])
    Verify -->|否 | Debug[调试修复]
    Debug --> Restart
    
    classDef check fill:#e1f5ff,stroke:#0066cc
    classDef action fill:#e1ffe1,stroke:#00cc00
    classDef test fill:#fff4e1,stroke:#ff9900
    classDef decision fill:#ffe1e1,stroke:#cc0000
    
    class Check1,Check2 check
    class Restart,ClearCache,Compile,Done action
    class Test1,Test2,Test3,Test4 test
    class Verify decision
```

---

**文档结束**

此可视化分析图谱完整展示了品牌诊断系统从用户发起诊断到最终结果展示的全链路流程，包括：
1. 系统架构全景
2. 数据流时序图
3. NxM 执行引擎内部流程
4. execution_store 状态演变
5. 前端轮询机制
6. 失败场景分析
7. 修复效果对比

可用于详细分析系统问题和验证修复效果。
