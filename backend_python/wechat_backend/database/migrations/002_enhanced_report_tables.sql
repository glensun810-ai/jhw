-- ================================================================
-- GEO 品牌诊断报告导出功能增强 - 数据库迁移脚本
-- 版本：v2.0
-- 日期：2026-02-21
-- 说明：添加竞品分析、负面信源、ROI 指标等表结构
-- ================================================================

-- 1. 修改 test_results 表，添加新字段
-- ================================================================

-- 竞品分析数据 (JSON 格式)
ALTER TABLE test_results ADD COLUMN competitor_analysis TEXT;

-- 负面信源数据 (JSON 格式)
ALTER TABLE test_results ADD COLUMN negative_sources TEXT;

-- ROI 指标数据 (JSON 格式)
ALTER TABLE test_results ADD COLUMN roi_metrics TEXT;

-- 行动计划数据 (JSON 格式)
ALTER TABLE test_results ADD COLUMN action_plan TEXT;

-- 执行摘要 (TEXT 格式)
ALTER TABLE test_results ADD COLUMN executive_summary TEXT;

-- 报告生成时间
ALTER TABLE test_results ADD COLUMN report_generated_at TEXT;

-- 报告版本
ALTER TABLE test_results ADD COLUMN report_version TEXT DEFAULT '2.0';


-- 2. 创建竞品分析表
-- ================================================================

CREATE TABLE IF NOT EXISTS competitive_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    competitor_name TEXT NOT NULL,
    
    -- 综合评分
    overall_score REAL,
    
    -- 四维度评分
    authority_score REAL,
    visibility_score REAL,
    purity_score REAL,
    consistency_score REAL,
    
    -- 各平台评分 (JSON 格式)
    platform_scores TEXT,
    
    -- 分析结果
    strengths TEXT,      -- 优势 (JSON 数组)
    weaknesses TEXT,     -- 劣势 (JSON 数组)
    opportunities TEXT,  -- 机会 (JSON 数组)
    threats TEXT,        -- 威胁 (JSON 数组)
    
    -- 元数据
    analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    analysis_model TEXT,
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_competitive_execution ON competitive_analysis(execution_id);
CREATE INDEX IF NOT EXISTS idx_competitive_name ON competitive_analysis(competitor_name);
CREATE INDEX IF NOT EXISTS idx_competitive_score ON competitive_analysis(overall_score DESC);


-- 3. 创建负面信源表
-- ================================================================

CREATE TABLE IF NOT EXISTS negative_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    
    -- 信源信息
    source_name TEXT NOT NULL,      -- 信源名称 (如：知乎、小红书)
    source_url TEXT,                -- 信源 URL
    source_type TEXT,               -- 信源类型 (article, video, social_media, etc.)
    
    -- 内容信息
    content_summary TEXT,           -- 内容摘要
    content_snippet TEXT,           -- 内容片段
    sentiment_score REAL,           -- 情感得分 (-1.0 到 1.0)
    
    -- 影响评估
    severity TEXT CHECK(severity IN ('critical', 'high', 'medium', 'low')),
    impact_scope TEXT CHECK(impact_scope IN ('high', 'medium', 'low')),
    estimated_reach INTEGER,        -- 预估触达人数
    
    -- 时间信息
    discovered_at TEXT,             -- 发现时间
    published_at TEXT,              -- 发布时间
    
    -- 应对建议
    recommendation TEXT,            -- 应对建议
    action_required TEXT,           -- 需要采取的行动
    priority_score REAL,            -- 优先级评分 (0-100)
    
    -- 状态跟踪
    status TEXT CHECK(status IN ('pending', 'in_progress', 'resolved', 'ignored')) DEFAULT 'pending',
    assigned_to TEXT,               -- 负责人
    resolved_at TEXT,               -- 解决时间
    resolution_notes TEXT,          -- 解决说明
    
    -- 元数据
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_negative_execution ON negative_sources(execution_id);
CREATE INDEX IF NOT EXISTS idx_negative_severity ON negative_sources(severity);
CREATE INDEX IF NOT EXISTS idx_negative_status ON negative_sources(status);
CREATE INDEX IF NOT EXISTS idx_negative_priority ON negative_sources(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_negative_brand ON negative_sources(brand_name);


-- 4. 创建 ROI 指标表
-- ================================================================

CREATE TABLE IF NOT EXISTS roi_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    
    -- 曝光 ROI
    exposure_roi REAL,              -- 曝光投资回报率
    total_impressions INTEGER,      -- 总曝光次数
    estimated_value REAL,           -- 估算曝光价值 (元)
    
    -- 情感 ROI
    sentiment_roi REAL,             -- 情感投资回报率
    positive_mentions INTEGER,      -- 正面提及数
    negative_mentions INTEGER,      -- 负面提及数
    neutral_mentions INTEGER,       -- 中性提及数
    sentiment_score REAL,           -- 情感得分
    
    -- 排名 ROI
    ranking_roi REAL,               -- 排名投资回报率
    avg_ranking REAL,               -- 平均排名
    top_3_count INTEGER,            -- 前 3 名次数
    top_10_count INTEGER,           -- 前 10 名次数
    
    -- 综合指标
    overall_roi REAL,               -- 综合 ROI
    roi_grade TEXT,                 -- ROI 等级 (A+, A, B, C, D)
    
    -- 行业对比
    industry_avg_exposure_roi REAL,
    industry_avg_sentiment_roi REAL,
    industry_avg_ranking_roi REAL,
    
    -- 元数据
    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    calculation_model TEXT,
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_roi_execution ON roi_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_roi_overall ON roi_metrics(overall_roi DESC);
CREATE INDEX IF NOT EXISTS idx_roi_grade ON roi_metrics(roi_grade);


-- 5. 创建行动计划表
-- ================================================================

CREATE TABLE IF NOT EXISTS action_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    
    -- 行动信息
    action_title TEXT NOT NULL,         -- 行动标题
    action_description TEXT,            -- 行动描述
    action_category TEXT,               -- 行动类别 (content, seo, pr, monitoring, etc.)
    
    -- 时间规划
    phase TEXT CHECK(phase IN ('short_term', 'mid_term', 'long_term')),
    start_week INTEGER,                 -- 开始周次
    duration_weeks INTEGER,             -- 持续周数
    estimated_hours INTEGER,            -- 预估工时
    
    -- 资源需求
    required_roles TEXT,                -- 需要角色 (JSON 数组)
    estimated_budget REAL,              -- 预估预算 (元)
    required_tools TEXT,                -- 需要工具 (JSON 数组)
    
    -- 优先级
    priority TEXT CHECK(priority IN ('critical', 'high', 'medium', 'low')),
    priority_score REAL,                -- 优先级评分 (0-100)
    effort_level TEXT CHECK(effort_level IN ('low', 'medium', 'high')),
    impact_level TEXT CHECK(impact_level IN ('low', 'medium', 'high')),
    
    -- 预期效果
    expected_outcome TEXT,              -- 预期结果
    success_metrics TEXT,               -- 成功指标 (JSON 数组)
    expected_score_improvement REAL,    -- 预期评分提升
    
    -- 执行步骤
    action_steps TEXT,                  -- 执行步骤 (JSON 数组)
    
    -- 状态跟踪
    status TEXT CHECK(status IN ('planned', 'in_progress', 'completed', 'cancelled')) DEFAULT 'planned',
    completed_at TEXT,
    completion_notes TEXT,
    
    -- 元数据
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_action_execution ON action_plans(execution_id);
CREATE INDEX IF NOT EXISTS idx_action_phase ON action_plans(phase);
CREATE INDEX IF NOT EXISTS idx_action_priority ON action_plans(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_action_status ON action_plans(status);


-- 6. 创建执行摘要表
-- ================================================================

CREATE TABLE IF NOT EXISTS executive_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    
    -- 核心指标
    overall_health_score REAL,          -- 总体健康度评分
    health_grade TEXT,                  -- 健康等级 (A+, A, B, C, D)
    score_change REAL,                  -- 评分变化 (与上期对比)
    
    -- 核心发现
    key_findings TEXT,                  -- 核心发现 (JSON 数组，3-5 条)
    top_strengths TEXT,                 -- 主要优势 (JSON 数组)
    top_concerns TEXT,                  -- 主要关注点 (JSON 数组)
    top_risks TEXT,                     -- 主要风险 (JSON 数组)
    
    -- 优先级建议
    priority_recommendations TEXT,      -- 优先级建议 (JSON 数组)
    quick_wins TEXT,                    -- 快速见效行动 (JSON 数组)
    strategic_initiatives TEXT,         -- 战略举措 (JSON 数组)
    
    -- 估算价值
    estimated_brand_value REAL,         -- 估算品牌价值 (元/月)
    value_change REAL,                  -- 价值变化
    
    -- 摘要文本
    summary_text TEXT,                  -- 完整摘要文本
    
    -- 元数据
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    generated_by TEXT,                  -- 生成模型
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_summary_execution ON executive_summaries(execution_id);
CREATE INDEX IF NOT EXISTS idx_summary_score ON executive_summaries(overall_health_score DESC);
CREATE INDEX IF NOT EXISTS idx_summary_grade ON executive_summaries(health_grade);


-- 7. 创建报告生成日志表
-- ================================================================

CREATE TABLE IF NOT EXISTS report_generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    report_type TEXT,                   -- pdf, html, excel
    report_level TEXT,                  -- basic, detailed, full
    sections_requested TEXT,            -- 请求的章节 (JSON 数组)
    
    -- 性能指标
    generation_time_ms INTEGER,         -- 生成时间 (毫秒)
    file_size_bytes INTEGER,            -- 文件大小 (字节)
    
    -- 状态
    status TEXT CHECK(status IN ('success', 'failed', 'timeout')),
    error_message TEXT,
    
    -- 元数据
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    generated_by TEXT,                  -- 用户 ID
    
    -- 外键约束
    FOREIGN KEY (execution_id) REFERENCES test_results(execution_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_report_log_execution ON report_generation_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_report_log_status ON report_generation_logs(status);
CREATE INDEX IF NOT EXISTS idx_report_log_time ON report_generation_logs(generated_at DESC);


-- 8. 插入行业基准数据 (示例数据)
-- ================================================================

CREATE TABLE IF NOT EXISTS industry_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    industry TEXT NOT NULL,             -- 行业
    metric_name TEXT NOT NULL,          -- 指标名称
    benchmark_value REAL,               -- 基准值
    percentile_25 REAL,                 -- 25 分位数
    percentile_50 REAL,                 -- 50 分位数 (中位数)
    percentile_75 REAL,                 -- 75 分位数
    data_source TEXT,                   -- 数据来源
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 插入示例基准数据
INSERT OR REPLACE INTO industry_benchmarks (industry, metric_name, benchmark_value, percentile_25, percentile_50, percentile_75, data_source) VALUES
('technology', 'exposure_roi', 3.5, 2.0, 3.5, 5.0, 'industry_report_2026'),
('technology', 'sentiment_roi', 0.65, 0.4, 0.65, 0.85, 'industry_report_2026'),
('technology', 'ranking_roi', 55, 30, 55, 75, 'industry_report_2026'),
('retail', 'exposure_roi', 2.8, 1.5, 2.8, 4.2, 'industry_report_2026'),
('retail', 'sentiment_roi', 0.55, 0.35, 0.55, 0.75, 'industry_report_2026'),
('retail', 'ranking_roi', 45, 25, 45, 65, 'industry_report_2026'),
('finance', 'exposure_roi', 4.2, 2.5, 4.2, 6.0, 'industry_report_2026'),
('finance', 'sentiment_roi', 0.70, 0.5, 0.70, 0.90, 'industry_report_2026'),
('finance', 'ranking_roi', 60, 40, 60, 80, 'industry_report_2026'),
('general', 'exposure_roi', 2.5, 1.5, 2.5, 3.5, 'industry_report_2026'),
('general', 'sentiment_roi', 0.60, 0.4, 0.60, 0.80, 'industry_report_2026'),
('general', 'ranking_roi', 50, 30, 50, 70, 'industry_report_2026');

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_benchmark_industry ON industry_benchmarks(industry);
CREATE INDEX IF NOT EXISTS idx_benchmark_metric ON industry_benchmarks(metric_name);


-- ================================================================
-- 迁移完成验证
-- ================================================================

-- 验证表创建
SELECT 'competitive_analysis' as table_name, COUNT(*) as row_count FROM competitive_analysis
UNION ALL
SELECT 'negative_sources', COUNT(*) FROM negative_sources
UNION ALL
SELECT 'roi_metrics', COUNT(*) FROM roi_metrics
UNION ALL
SELECT 'action_plans', COUNT(*) FROM action_plans
UNION ALL
SELECT 'executive_summaries', COUNT(*) FROM executive_summaries
UNION ALL
SELECT 'report_generation_logs', COUNT(*) FROM report_generation_logs
UNION ALL
SELECT 'industry_benchmarks', COUNT(*) FROM industry_benchmarks;

-- 输出迁移信息
SELECT 'Database migration completed successfully! Version: 2.0' as migration_status;
