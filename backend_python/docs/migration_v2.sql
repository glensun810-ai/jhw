-- =============================================
-- 品牌诊断系统 - 数据库迁移脚本 v2.0
-- =============================================
-- 用途：创建报告快照和维度结果表
-- 执行方式：sqlite3 database.db < migration_v2.sql
-- 执行时间：预计 < 1 秒
-- 影响：只创建新表，不影响现有数据
-- 回滚：DROP TABLE report_snapshots; DROP TABLE dimension_results;
-- =============================================

-- 开始事务（确保原子性）
BEGIN TRANSACTION;

-- =============================================
-- 1. 创建报告快照表
-- =============================================
CREATE TABLE IF NOT EXISTS report_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,      -- 执行 ID（与 diagnosis_reports 关联）
    user_id TEXT NOT NULL,                   -- 用户 ID
    report_data TEXT NOT NULL,               -- 完整报告 JSON 快照
    report_hash TEXT NOT NULL,               -- SHA256 哈希（用于一致性验证）
    size_kb INTEGER NOT NULL DEFAULT 0,      -- 快照大小（KB）
    storage_timestamp TEXT NOT NULL,         -- 存储时间戳
    report_version TEXT DEFAULT 'v2.0',      -- 报告版本号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引（提升查询性能）
CREATE INDEX IF NOT EXISTS idx_snapshot_execution_id ON report_snapshots(execution_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_user_id ON report_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON report_snapshots(storage_timestamp);

-- =============================================
-- 2. 创建维度结果表
-- =============================================
CREATE TABLE IF NOT EXISTS dimension_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,              -- 执行 ID（与 diagnosis_reports 关联）
    dimension_name TEXT NOT NULL,            -- 维度名称（如：社交媒体影响力）
    dimension_type TEXT NOT NULL,            -- 维度类型（social_media, news, ai_summary 等）
    source TEXT NOT NULL,                    -- 数据源（weibo, baidu, openai 等）
    status TEXT NOT NULL DEFAULT 'pending',  -- 状态（success, failed, pending）
    score REAL,                              -- 评分（0-100）
    data TEXT,                               -- 详细数据（JSON 格式）
    error_message TEXT,                      -- 错误信息（失败时填写）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引（提升查询性能）
CREATE INDEX IF NOT EXISTS idx_dimension_execution_id ON dimension_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_dimension_type ON dimension_results(dimension_type);
CREATE INDEX IF NOT EXISTS idx_dimension_status ON dimension_results(status);

-- =============================================
-- 3. 创建任务状态表（如果不存在）
-- =============================================
CREATE TABLE IF NOT EXISTS task_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,            -- 执行 ID
    progress INTEGER NOT NULL DEFAULT 0,     -- 进度（0-100）
    stage TEXT NOT NULL DEFAULT 'init',      -- 阶段（init, ai_fetching, completed 等）
    status_text TEXT,                        -- 状态文本（用户友好提示）
    completed_count INTEGER DEFAULT 0,       -- 已完成任务数
    total_count INTEGER DEFAULT 0,           -- 总任务数
    is_completed BOOLEAN DEFAULT 0,          -- 是否完成
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_task_id ON task_statuses(task_id);

-- =============================================
-- 4. 创建触发器（自动更新 updated_at）
-- =============================================

-- report_snapshots 自动更新时间
CREATE TRIGGER IF NOT EXISTS update_report_snapshots_timestamp
AFTER UPDATE ON report_snapshots
BEGIN
    UPDATE report_snapshots SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- dimension_results 自动更新时间
CREATE TRIGGER IF NOT EXISTS update_dimension_results_timestamp
AFTER UPDATE ON dimension_results
BEGIN
    UPDATE dimension_results SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- task_statuses 自动更新时间
CREATE TRIGGER IF NOT EXISTS update_task_statuses_timestamp
AFTER UPDATE ON task_statuses
BEGIN
    UPDATE task_statuses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- =============================================
-- 5. 插入迁移记录（用于追踪）
-- =============================================
CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO migration_log (version, description) 
VALUES ('v2.0', '创建报告快照和维度结果表，支持部分失败和历史一致性');

-- =============================================
-- 6. 验证（可选，用于确认迁移成功）
-- =============================================

-- 验证表是否创建成功
-- SELECT name FROM sqlite_master WHERE type='table' AND name IN ('report_snapshots', 'dimension_results', 'task_statuses');

-- 验证索引是否创建成功
-- SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_snapshot%' OR name LIKE 'idx_dimension%' OR name LIKE 'idx_task%';

-- 提交事务
COMMIT;

-- =============================================
-- 迁移完成提示
-- =============================================
-- 如果看到 " COMMIT" 且无错误，说明迁移成功
-- 可以通过以下命令验证：
-- sqlite3 database.db "SELECT COUNT(*) FROM migration_log;"
-- 应该返回 1
-- =============================================
