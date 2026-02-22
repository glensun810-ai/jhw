-- 数据存储架构优化脚本
-- 执行日期：2026-02-22
-- 执行人：AI Assistant (数据存储专家)

-- 开始事务
BEGIN TRANSACTION;

-- 1. 删除未使用的表（数据已在 JSON 中）
DROP TABLE IF EXISTS competitive_analysis;
DROP TABLE IF EXISTS negative_sources;
DROP TABLE IF EXISTS report_metadata;

-- 2. 保留 task_statuses 表（有持久化需求）
-- 但需要添加注释说明当前状态
-- 当前使用 execution_store (内存)，未来可实现持久化

-- 3. 添加 JSON 索引加速查询
CREATE INDEX IF NOT EXISTS idx_test_records_execution_id 
ON test_records (json_extract(results_summary, '$.execution_id'));

CREATE INDEX IF NOT EXISTS idx_test_records_brand_name 
ON test_records (json_extract(results_summary, '$.brand_name'));

CREATE INDEX IF NOT EXISTS idx_test_records_overall_score 
ON test_records (json_extract(results_summary, '$.overall_score'));

CREATE INDEX IF NOT EXISTS idx_test_records_test_date 
ON test_records (test_date DESC);

-- 4. 创建视图简化常用查询
DROP VIEW IF EXISTS v_test_summary;
CREATE VIEW v_test_summary AS
SELECT 
    id,
    brand_name,
    test_date,
    overall_score,
    total_tests,
    json_extract(results_summary, '$.execution_id') as execution_id,
    json_extract(results_summary, '$.brand_scores') as brand_scores,
    json_extract(results_summary, '$.competitive_analysis') as competitive_analysis,
    json_extract(results_summary, '$.negative_sources') as negative_sources,
    is_summary_compressed,
    is_detailed_compressed
FROM test_records
ORDER BY test_date DESC;

-- 提交事务
COMMIT;

-- 验证
SELECT '优化完成' as status;
SELECT COUNT(*) as test_records_count FROM test_records;
SELECT COUNT(*) as task_statuses_count FROM task_statuses;
SELECT name as table_name FROM sqlite_master WHERE type='table' ORDER BY name;
SELECT name as index_name FROM sqlite_master WHERE type='index' AND tbl_name='test_records' ORDER BY name;
