-- 阶段 3: 实时持久化数据库表结构
-- 执行：sqlite3 data/brand_test.db < phase3_database_schema.sql

-- 聚合结果表
CREATE TABLE IF NOT EXISTS aggregated_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    main_brand TEXT NOT NULL,
    health_score REAL DEFAULT 0,
    sov REAL DEFAULT 0,
    avg_sentiment REAL DEFAULT 0,
    success_rate REAL DEFAULT 0,
    total_tests INTEGER DEFAULT 0,
    total_mentions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_aggregated_execution ON aggregated_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_brand ON aggregated_results(main_brand);
CREATE INDEX IF NOT EXISTS idx_aggregated_created ON aggregated_results(created_at);

-- P2-10: 复合索引 - 加速按 execution_id 和时间的查询
CREATE INDEX IF NOT EXISTS idx_aggregated_execution_created ON aggregated_results(execution_id, created_at);
-- P2-10: 复合索引 - 加速按品牌和分数的查询
CREATE INDEX IF NOT EXISTS idx_aggregated_brand_score ON aggregated_results(main_brand, health_score);

-- 品牌排名表
CREATE TABLE IF NOT EXISTS brand_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    rank INTEGER DEFAULT 0,
    responses INTEGER DEFAULT 0,
    sov_share REAL DEFAULT 0,
    avg_sentiment REAL DEFAULT 0,
    avg_rank REAL DEFAULT -1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(execution_id, brand)
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_rankings_execution ON brand_rankings(execution_id);
CREATE INDEX IF NOT EXISTS idx_rankings_brand ON brand_rankings(brand);
CREATE INDEX IF NOT EXISTS idx_rankings_rank ON brand_rankings(rank);

-- P2-10: 复合索引 - 加速按执行 ID 和排名的查询
CREATE INDEX IF NOT EXISTS idx_rankings_execution_rank ON brand_rankings(execution_id, rank);
-- P2-10: 复合索引 - 加速按执行 ID 和品牌的查询
CREATE INDEX IF NOT EXISTS idx_rankings_execution_brand ON brand_rankings(execution_id, brand);

-- 问题统计表
CREATE TABLE IF NOT EXISTS question_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    question TEXT NOT NULL,
    total_responses INTEGER DEFAULT 0,
    main_brand_mentions INTEGER DEFAULT 0,
    mention_rate REAL DEFAULT 0,
    competitor_mentions TEXT DEFAULT '{}',  -- JSON 格式存储
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(execution_id, question)
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_questions_execution ON question_stats(execution_id);

-- 模型统计表
CREATE TABLE IF NOT EXISTS model_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    model TEXT NOT NULL,
    total_responses INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    avg_word_count REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(execution_id, model)
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_models_execution ON model_stats(execution_id);
CREATE INDEX IF NOT EXISTS idx_models_model ON model_stats(model);

-- 执行日志表 (用于调试和监控)
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    log_level TEXT NOT NULL,  -- INFO, WARNING, ERROR
    log_message TEXT NOT NULL,
    log_data TEXT DEFAULT '{}',  -- JSON 格式存储额外数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_logs_execution ON execution_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON execution_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON execution_logs(created_at);

-- P2-10: 复合索引 - 加速按执行 ID 和级别的查询
CREATE INDEX IF NOT EXISTS idx_logs_execution_level ON execution_logs(execution_id, log_level);
-- P2-10: 复合索引 - 加速按时间和级别的查询
CREATE INDEX IF NOT EXISTS idx_logs_created_level ON execution_logs(created_at, log_level);

-- 性能监控表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,  -- task_duration, api_latency, etc.
    metric_value REAL NOT NULL,
    metric_unit TEXT DEFAULT '',  -- ms, seconds, etc.
    metadata TEXT DEFAULT '{}',  -- JSON 格式存储额外数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_metrics_execution ON performance_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON performance_metrics(metric_name);

-- P2-10: 复合索引 - 加速按执行 ID 和指标名称的查询
CREATE INDEX IF NOT EXISTS idx_metrics_execution_name ON performance_metrics(execution_id, metric_name);
-- P2-10: 复合索引 - 加速按时间和指标的查询
CREATE INDEX IF NOT EXISTS idx_metrics_created_name ON performance_metrics(created_at, metric_name);

-- 创建视图：执行统计概览
CREATE VIEW IF NOT EXISTS execution_summary AS
SELECT 
    execution_id,
    main_brand,
    health_score,
    sov,
    avg_sentiment,
    success_rate,
    total_tests,
    total_mentions,
    created_at,
    (julianday(CURRENT_TIMESTAMP) - julianday(created_at)) * 24 * 60 AS minutes_since_creation
FROM aggregated_results
ORDER BY created_at DESC;

-- 创建视图：品牌排名概览
CREATE VIEW IF NOT EXISTS brand_ranking_summary AS
SELECT 
    execution_id,
    brand,
    rank,
    responses,
    sov_share,
    avg_sentiment,
    avg_rank,
    created_at
FROM brand_rankings
WHERE rank <= 3  -- 只显示前 3 名
ORDER BY execution_id, rank;

-- 插入示例数据 (用于测试)
-- INSERT INTO aggregated_results (execution_id, main_brand, health_score, sov, avg_sentiment, total_tests)
-- VALUES ('test-exec-001', '华为', 75.0, 44.44, 0.52, 9);

-- 插入示例品牌排名
-- INSERT INTO brand_rankings (execution_id, brand, rank, responses, sov_share, avg_sentiment, avg_rank)
-- VALUES 
--     ('test-exec-001', '华为', 1, 4, 44.44, 0.52, 2.3),
--     ('test-exec-001', '小米', 2, 3, 33.33, 0.48, 3.5),
--     ('test-exec-001', 'OPPO', 3, 2, 22.22, 0.45, 4.0);
