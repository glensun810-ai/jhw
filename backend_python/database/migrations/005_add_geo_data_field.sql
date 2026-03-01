-- ============================================================
-- 迁移脚本：添加 geo_data 字段到 diagnosis_results 表
-- 创建日期：2026-03-01
-- 版本：005
--
-- 问题：cache_warmup_tasks.py 中查询 geo_data 字段失败
-- 错误：no such column: geo_data
--
-- 解决方案：
-- 1. 添加 geo_data 字段（如果不存在）
-- 2. 为现有记录设置默认值
-- ============================================================

-- 开始事务
BEGIN TRANSACTION;

-- 添加 geo_data 字段
-- 注意：SQLite 3.35.0+ 支持 ADD COLUMN，如果字段已存在会报错
-- 如果执行失败，说明字段已存在，可以忽略错误
ALTER TABLE diagnosis_results ADD COLUMN geo_data TEXT DEFAULT '{}';

-- 更新现有记录的 geo_data 字段（如果为空）
UPDATE diagnosis_results
SET geo_data = '{}'
WHERE geo_data IS NULL;

-- 提交事务
COMMIT;

-- ============================================================
-- 验证
-- ============================================================

-- 验证 geo_data 字段是否存在
SELECT '✅ geo_data 字段验证：' || 
    CASE 
        WHEN COUNT(*) > 0 THEN '成功'
        ELSE '失败'
    END AS status
FROM PRAGMA_TABLE_INFO('diagnosis_results') 
WHERE name = 'geo_data';

-- 显示 geo_data 字段信息
SELECT name, type, "notnull", dflt_value
FROM PRAGMA_TABLE_INFO('diagnosis_results')
WHERE name = 'geo_data';

-- 显示记录数
SELECT 'diagnosis_results 记录数：' || COUNT(*) AS record_count
FROM diagnosis_results;
