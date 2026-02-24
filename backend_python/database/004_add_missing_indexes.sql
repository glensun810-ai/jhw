-- =============================================================================
-- 2026-02-24 数据库索引修复脚本
-- 问题：P0-002 数据库表缺少索引，导致查询性能慢
-- 修复：添加关键查询字段的索引
-- =============================================================================

-- 1. deep_intelligence_results 表索引
-- 用于根据 execution_id 快速查询诊断结果
CREATE INDEX IF NOT EXISTS idx_deep_intelligence_execution_id 
ON deep_intelligence_results (execution_id);

-- 2. task_statuses 表索引
-- 用于轮询任务状态
CREATE INDEX IF NOT EXISTS idx_task_statuses_task_id 
ON task_statuses (task_id);

-- 任务状态查询优化
CREATE INDEX IF NOT EXISTS idx_task_statuses_status 
ON task_statuses (status);

-- 3. test_records 表索引（如果不存在）
-- 用于历史记录查询
CREATE INDEX IF NOT EXISTS idx_test_records_execution_id 
ON test_records (execution_id);

CREATE INDEX IF NOT EXISTS idx_test_records_brand_name 
ON test_records (brand_name);

CREATE INDEX IF NOT EXISTS idx_test_records_test_date 
ON test_records (test_date DESC);

-- 4. 复合索引（可选，根据查询模式）
-- 用于同时根据 execution_id 和 status 查询
CREATE INDEX IF NOT EXISTS idx_task_statuses_execution_status
ON task_statuses (task_id, status);

-- =============================================================================
-- 验证索引创建
-- =============================================================================

-- 查看所有索引
SELECT name, tbl_name, sql 
FROM sqlite_master 
WHERE type='index' AND tbl_name IN ('deep_intelligence_results', 'task_statuses', 'test_records')
ORDER BY tbl_name, name;

-- 查看表大小和索引效果
SELECT 
    'deep_intelligence_results' as table_name, 
    COUNT(*) as row_count 
FROM deep_intelligence_results
UNION ALL
SELECT 
    'task_statuses' as table_name, 
    COUNT(*) as row_count 
FROM task_statuses
UNION ALL
SELECT 
    'test_records' as table_name, 
    COUNT(*) as row_count 
FROM test_records;
