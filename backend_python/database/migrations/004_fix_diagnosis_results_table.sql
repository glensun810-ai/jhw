-- ============================================================
-- 品牌诊断完整闭环修复 - 数据库表结构修复
-- 创建日期：2026-02-25
-- 版本：1.0
-- 
-- 问题：diagnosis_results 表结构不正确，缺少必要字段
-- 解决：重建表结构，确保与代码一致
-- ============================================================

-- 开始事务
BEGIN TRANSACTION;

-- 1. 备份现有数据（如果有）
CREATE TABLE IF NOT EXISTS diagnosis_results_backup AS 
SELECT * FROM diagnosis_results WHERE 1=0;

INSERT INTO diagnosis_results_backup 
SELECT * FROM diagnosis_results;

-- 2. 删除旧表
DROP TABLE IF EXISTS diagnosis_results;

-- 3. 创建新表（正确的结构）
CREATE TABLE diagnosis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    execution_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    question TEXT NOT NULL,
    model TEXT NOT NULL,
    response_content TEXT NOT NULL,
    response_latency REAL,
    geo_data TEXT NOT NULL,
    quality_score REAL NOT NULL DEFAULT 0,
    quality_level TEXT NOT NULL DEFAULT 'unknown',
    quality_details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
);

-- 4. 创建索引
CREATE INDEX IF NOT EXISTS idx_results_report_id ON diagnosis_results(report_id);
CREATE INDEX IF NOT EXISTS idx_results_execution_id ON diagnosis_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_results_brand ON diagnosis_results(brand);

-- 5. 恢复数据（如果有备份）
INSERT INTO diagnosis_results (
    report_id, execution_id, brand, question, model, 
    response_content, response_latency, geo_data, 
    quality_score, quality_level, quality_details, 
    status, error_message, created_at
)
SELECT 
    1,  -- 默认 report_id，后续会更新
    execution_id,
    brand_name as brand,
    '' as question,
    '' as model,
    results as response_content,
    NULL as response_latency,
    COALESCE(geo_data, '{}') as geo_data,
    0 as quality_score,
    'unknown' as quality_level,
    '{}' as quality_details,
    'success' as status,
    NULL as error_message,
    created_at
FROM diagnosis_results_backup;

-- 6. 清理备份表
DROP TABLE IF EXISTS diagnosis_results_backup;

-- 提交事务
COMMIT;

-- ============================================================
-- 验证
-- ============================================================

-- 输出迁移结果
SELECT '✅ 数据库表结构修复完成' AS status;

-- 显示新表结构
SELECT 'diagnosis_results 字段数：' || COUNT(*) AS column_count 
FROM PRAGMA_TABLE_INFO('diagnosis_results');

-- 显示记录数
SELECT 'diagnosis_results 记录数：' || COUNT(*) AS record_count 
FROM diagnosis_results;
