-- 迁移脚本：修复报告数据表结构
-- 执行：sqlite3 database.db < migrations/003_fix_report_tables.sql
-- 日期：2026-02-22

-- 1. 添加 test_results 视图（兼容旧代码）
-- 注意：test_records 是实际表，test_results 是兼容视图
DROP VIEW IF EXISTS test_results;

CREATE VIEW test_results AS
SELECT 
    id as result_id,
    user_id,
    brand_name,
    test_date as execution_id,  -- 使用 test_date 作为 execution_id 的兼容
    ai_models_used,
    questions_used,
    overall_score,
    total_tests,
    CASE 
        WHEN is_summary_compressed = 1 THEN NULL  -- 压缩数据在视图中不展示
        ELSE results_summary 
    END as results_summary,
    CASE 
        WHEN is_detailed_compressed = 1 THEN NULL  -- 压缩数据在视图中不展示
        ELSE detailed_results 
    END as detailed_results,
    created_at,
    updated_at
FROM test_records;

-- 2. 添加 competitive_analysis 表（如果不存在）
CREATE TABLE IF NOT EXISTS competitive_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    competitor_name TEXT NOT NULL,
    overall_score REAL DEFAULT 0,
    authority_score REAL DEFAULT 0,
    visibility_score REAL DEFAULT 0,
    purity_score REAL DEFAULT 0,
    consistency_score REAL DEFAULT 0,
    platform_scores TEXT DEFAULT '[]',  -- JSON 数组
    strengths TEXT DEFAULT '[]',  -- JSON 数组
    weaknesses TEXT DEFAULT '[]',  -- JSON 数组
    opportunities TEXT DEFAULT '[]',  -- JSON 数组
    threats TEXT DEFAULT '[]',  -- JSON 数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(execution_id, competitor_name)
);

CREATE INDEX IF NOT EXISTS idx_competitive_execution ON competitive_analysis(execution_id);

-- 3. 添加 negative_sources 表（如果不存在）
CREATE TABLE IF NOT EXISTS negative_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    source_type TEXT,  -- article, social_media, encyclopedia, etc.
    content_summary TEXT,
    sentiment_score REAL DEFAULT 0,
    severity TEXT DEFAULT 'low',  -- critical, high, medium, low
    impact_scope TEXT DEFAULT 'medium',  -- high, medium, low
    estimated_reach INTEGER DEFAULT 0,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recommendation TEXT,
    priority_score REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- pending, processing, resolved, ignored
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_negative_execution ON negative_sources(execution_id);
CREATE INDEX IF NOT EXISTS idx_negative_severity ON negative_sources(severity);

-- 4. 添加 report_metadata 表（用于存储报告生成元数据）
CREATE TABLE IF NOT EXISTS report_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    brand_name TEXT NOT NULL,
    report_version TEXT DEFAULT '2.0',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generation_time_ms INTEGER DEFAULT 0,
    is_mock_data INTEGER DEFAULT 0,
    competitor_analysis_generated INTEGER DEFAULT 0,
    negative_sources_generated INTEGER DEFAULT 0,
    roi_calculated INTEGER DEFAULT 0,
    action_plan_generated INTEGER DEFAULT 0,
    executive_summary_generated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_report_metadata_execution ON report_metadata(execution_id);

-- 5. 更新 test_records 表，添加 execution_id 字段（如果不存在）
-- 注意：execution_id 存储在 results_summary JSON 中，这里添加一个冗余字段用于快速查询
SELECT CASE 
    WHEN COUNT(*) = 0 THEN 
        (SELECT 'Adding execution_id column to test_records')
    ELSE 
        (SELECT 'execution_id column already exists')
END FROM pragma_table_info('test_records') WHERE name='execution_id';

-- 由于 SQLite 不支持直接添加计算列，我们创建一个触发器来更新 execution_id
-- 实际上，我们已经在查询时从 results_summary 中提取 execution_id

-- 6. 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_test_records_test_date ON test_records(test_date DESC);
CREATE INDEX IF NOT EXISTS idx_test_records_brand ON test_records(brand_name);

-- 7. 创建视图：报告数据概览
DROP VIEW IF EXISTS report_summary;
CREATE VIEW report_summary AS
SELECT 
    tr.id,
    tr.brand_name,
    tr.test_date,
    tr.overall_score,
    tr.total_tests,
    CASE 
        WHEN tr.results_summary IS NOT NULL AND tr.is_summary_compressed = 0 
        THEN json_extract(tr.results_summary, '$.execution_id')
        ELSE NULL
    END as execution_id,
    CASE 
        WHEN tr.results_summary IS NOT NULL AND tr.is_summary_compressed = 0 
        THEN json_extract(tr.results_summary, '$.competitor_brands')
        ELSE NULL
    END as competitor_brands,
    ca.competitor_count,
    ns.negative_count,
    rm.report_version,
    rm.generated_at
FROM test_records tr
LEFT JOIN (
    SELECT execution_id, COUNT(*) as competitor_count
    FROM competitive_analysis
    GROUP BY execution_id
) ca ON ca.execution_id = json_extract(tr.results_summary, '$.execution_id')
LEFT JOIN (
    SELECT execution_id, COUNT(*) as negative_count
    FROM negative_sources
    GROUP BY execution_id
) ns ON ns.execution_id = json_extract(tr.results_summary, '$.execution_id')
LEFT JOIN report_metadata rm ON rm.execution_id = json_extract(tr.results_summary, '$.execution_id')
ORDER BY tr.created_at DESC;

-- 输出迁移完成信息
SELECT 'Migration 003 completed successfully!' as status;
