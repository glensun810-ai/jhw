-- ============================================================
-- 品牌诊断报告存储架构优化 - 数据库表结构脚本
-- 创建日期：2026-02-25
-- 版本：1.0
-- ============================================================

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. 诊断报告主表 (diagnosis_reports)
-- 存储诊断报告的基本信息和配置
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnosis_reports (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 唯一标识
    execution_id TEXT UNIQUE NOT NULL,
    
    -- 用户标识
    user_id TEXT NOT NULL,
    
    -- 诊断配置（不可变）
    brand_name TEXT NOT NULL,
    competitor_brands TEXT NOT NULL,  -- JSON 数组
    selected_models TEXT NOT NULL,    -- JSON 数组
    custom_questions TEXT NOT NULL,   -- JSON 数组
    
    -- 状态
    status TEXT NOT NULL DEFAULT 'processing',
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'init',
    is_completed BOOLEAN NOT NULL DEFAULT 0,
    
    -- 时间戳（不可变）
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    
    -- 版本控制
    data_schema_version TEXT NOT NULL DEFAULT '1.0',
    server_version TEXT NOT NULL,
    
    -- 完整性校验
    checksum TEXT NOT NULL
);

-- ============================================================
-- 2. 诊断结果明细表 (diagnosis_results)
-- 存储每个 AI 调用的详细结果
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnosis_results (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 外键
    report_id INTEGER NOT NULL,
    
    -- 执行标识
    execution_id TEXT NOT NULL,
    
    -- 结果内容（不可变）
    brand TEXT NOT NULL,
    question TEXT NOT NULL,
    model TEXT NOT NULL,
    response_content TEXT NOT NULL,  -- AI 原始回答
    response_latency REAL,           -- 响应时间（秒）
    
    -- GEO 分析
    geo_data TEXT NOT NULL,          -- JSON 对象
    
    -- 质量评分
    quality_score REAL NOT NULL DEFAULT 0,
    quality_level TEXT NOT NULL DEFAULT 'unknown',
    quality_details TEXT NOT NULL,   -- JSON 对象
    
    -- 状态
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    
    -- 时间戳
    created_at TEXT NOT NULL,
    
    -- 外键约束
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id) ON DELETE CASCADE
);

-- ============================================================
-- 3. 诊断分析表 (diagnosis_analysis)
-- 存储高级分析数据（竞争分析、品牌评分等）
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnosis_analysis (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 外键
    report_id INTEGER NOT NULL,
    
    -- 执行标识
    execution_id TEXT NOT NULL,
    
    -- 分析类型
    analysis_type TEXT NOT NULL,  -- competitive_analysis, brand_scores, semantic_drift_data, etc.
    
    -- 分析数据（不可变）
    analysis_data TEXT NOT NULL,  -- JSON 对象
    
    -- 版本控制
    analysis_version TEXT NOT NULL DEFAULT '1.0',
    
    -- 时间戳
    created_at TEXT NOT NULL,
    
    -- 外键约束
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id) ON DELETE CASCADE
);

-- ============================================================
-- 4. 历史快照表 (diagnosis_snapshots)
-- 存储完整报告快照，用于历史追溯
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnosis_snapshots (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 外键
    report_id INTEGER NOT NULL,
    
    -- 执行标识
    execution_id TEXT NOT NULL,
    
    -- 快照内容（完整副本）
    snapshot_data TEXT NOT NULL,  -- 完整 JSON 快照
    
    -- 快照元数据
    snapshot_reason TEXT NOT NULL,  -- 'completed', 'updated', 'archived'
    snapshot_version TEXT NOT NULL,
    
    -- 时间戳
    created_at TEXT NOT NULL,
    
    -- 外键约束
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id) ON DELETE CASCADE
);

-- ============================================================
-- 脚本完成
-- ============================================================

-- 输出创建结果
SELECT '✅ 诊断报告数据库表创建完成' AS status;
SELECT '  - diagnosis_reports: ' || COUNT(*) AS table_status FROM diagnosis_reports;
SELECT '  - diagnosis_results: ' || COUNT(*) AS table_status FROM diagnosis_results;
SELECT '  - diagnosis_analysis: ' || COUNT(*) AS table_status FROM diagnosis_analysis;
SELECT '  - diagnosis_snapshots: ' || COUNT(*) AS table_status FROM diagnosis_snapshots;
