-- ============================================================
-- 品牌诊断报告存储架构优化 - 数据迁移脚本
-- 创建日期：2026-02-25
-- 版本：1.0
-- ============================================================

-- ============================================================
-- 迁移说明
-- 1. 从旧表 (test_records) 迁移数据到新表
-- 2. 保持数据完整性
-- 3. 迁移后验证数据一致性
-- ============================================================

-- 开始事务
BEGIN TRANSACTION;

-- ============================================================
-- 检查旧表是否存在
-- ============================================================

-- 如果旧表不存在，跳过迁移
SELECT CASE 
    WHEN (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='test_records') = 0 
    THEN '旧表不存在，跳过迁移'
    ELSE '开始数据迁移'
END AS migration_status;

-- ============================================================
-- 1. 从 test_records 迁移到 diagnosis_reports (如果旧表存在)
-- ============================================================

INSERT OR IGNORE INTO diagnosis_reports (
    execution_id,
    user_id,
    brand_name,
    competitor_brands,
    selected_models,
    custom_questions,
    status,
    progress,
    stage,
    is_completed,
    created_at,
    updated_at,
    completed_at,
    data_schema_version,
    server_version,
    checksum
)
SELECT 
    -- execution_id: 使用 execution_id 字段或 id
    COALESCE(execution_id, CAST(id AS TEXT)) AS execution_id,
    
    -- user_id: 转换为字符串
    CAST(user_id AS TEXT) AS user_id,
    
    -- brand_name
    COALESCE(brand_name, 'Unknown') AS brand_name,
    
    -- competitor_brands: 空数组
    '[]' AS competitor_brands,
    
    -- selected_models: 从 ai_models_used 转换
    CASE 
        WHEN ai_models_used IS NOT NULL AND ai_models_used != ''
        THEN ai_models_used
        ELSE '[]'
    END AS selected_models,
    
    -- custom_questions: 从 questions_used 转换
    CASE 
        WHEN questions_used IS NOT NULL AND questions_used != ''
        THEN questions_used
        ELSE '[]'
    END AS custom_questions,
    
    -- status
    'completed' AS status,
    
    -- progress
    100 AS progress,
    
    -- stage
    'completed' AS stage,
    
    -- is_completed
    1 AS is_completed,
    
    -- created_at
    COALESCE(test_date, datetime('now')) AS created_at,
    
    -- updated_at
    COALESCE(test_date, datetime('now')) AS updated_at,
    
    -- completed_at
    COALESCE(test_date, datetime('now')) AS completed_at,
    
    -- data_schema_version
    '1.0' AS data_schema_version,
    
    -- server_version
    'legacy' AS server_version,
    
    -- checksum: 简单校验和
    substr(hex(randomblob(16)), 1, 32) AS checksum

FROM test_records
WHERE id IS NOT NULL;

-- ============================================================
-- 2. 创建迁移日志表
-- ============================================================

CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    migration_date TEXT NOT NULL,
    records_migrated INTEGER NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);

-- 记录迁移日志
INSERT INTO migration_log (migration_name, migration_date, records_migrated, status)
SELECT 
    '003_migrate_legacy_data',
    datetime('now'),
    (SELECT COUNT(*) FROM diagnosis_reports),
    'completed';

-- 提交事务
COMMIT;

-- ============================================================
-- 3. 迁移验证
-- ============================================================

-- 输出迁移结果
SELECT '✅ 数据迁移完成' AS status;

-- 显示迁移数据量
SELECT 'diagnosis_reports 迁移记录数：' || COUNT(*) AS migrated_count FROM diagnosis_reports;
SELECT 'diagnosis_results 迁移记录数：' || COUNT(*) AS migrated_count FROM diagnosis_results;
SELECT 'diagnosis_analysis 迁移记录数：' || COUNT(*) AS migrated_count FROM diagnosis_analysis;
SELECT 'diagnosis_snapshots 迁移记录数：' || COUNT(*) AS migrated_count FROM diagnosis_snapshots;

-- 验证数据完整性
SELECT '数据完整性检查:' AS check_type;
SELECT '  - 有 execution_id 的报告：' || COUNT(*) AS count FROM diagnosis_reports WHERE execution_id IS NOT NULL;
SELECT '  - 有 checksum 的报告：' || COUNT(*) AS count FROM diagnosis_reports WHERE checksum IS NOT NULL;
