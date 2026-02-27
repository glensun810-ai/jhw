-- Migration: Add complete API response fields to diagnosis_results
-- 迁移目标：添加完整的 API 响应字段，确保存储所有 AI 调用详情
-- 
-- 符合重构规范：
-- - 规则 7.1.1: 向后兼容（仅添加新字段）
-- - 规则 7.2.1: 提供迁移脚本
-- - 规则 7.2.2: 提供 downgrade 方法（记录）
-- - 规则 7.3.1: 添加必要索引
--
-- 作者：系统架构组
-- 日期：2026-02-27
-- 版本：v2.0.0

-- ==================== 升级迁移 ====================

-- 1. 添加 API 响应完整字段
ALTER TABLE diagnosis_results ADD COLUMN raw_response TEXT;
ALTER TABLE diagnosis_results ADD COLUMN response_metadata TEXT;

-- 2. 添加 Token 统计字段
ALTER TABLE diagnosis_results ADD COLUMN tokens_used INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN completion_tokens INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN cached_tokens INTEGER DEFAULT 0;

-- 3. 添加响应详情字段
ALTER TABLE diagnosis_results ADD COLUMN finish_reason TEXT DEFAULT 'stop';
ALTER TABLE diagnosis_results ADD COLUMN request_id TEXT;
ALTER TABLE diagnosis_results ADD COLUMN model_version TEXT;
ALTER TABLE diagnosis_results ADD COLUMN reasoning_content TEXT;

-- 4. 添加 API 信息字段
ALTER TABLE diagnosis_results ADD COLUMN api_endpoint TEXT;
ALTER TABLE diagnosis_results ADD COLUMN service_tier TEXT DEFAULT 'default';

-- 5. 添加重试信息字段
ALTER TABLE diagnosis_results ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN is_fallback BOOLEAN DEFAULT 0;

-- 6. 添加时间戳字段
ALTER TABLE diagnosis_results ADD COLUMN updated_at TEXT;

-- 7. 更新现有记录（设置 updated_at）
UPDATE diagnosis_results 
SET updated_at = created_at 
WHERE updated_at IS NULL;

-- 8. 创建索引（提高查询性能）
CREATE INDEX IF NOT EXISTS idx_results_created_at ON diagnosis_results(created_at);
CREATE INDEX IF NOT EXISTS idx_results_model ON diagnosis_results(model);
CREATE INDEX IF NOT EXISTS idx_results_status ON diagnosis_results(status);
CREATE INDEX IF NOT EXISTS idx_results_execution_status ON diagnosis_results(execution_id, status);

-- ==================== 降级迁移 ====================
-- 注意：SQLite 不支持 DROP COLUMN，需要重建表
-- 如需回滚，请执行以下步骤：
--
-- 1. 创建临时表（保留原有数据）
-- CREATE TABLE diagnosis_results_backup AS SELECT * FROM diagnosis_results;
--
-- 2. 重建原表结构（不含新字段）
-- CREATE TABLE diagnosis_results_new (...);
--
-- 3. 迁移数据
-- INSERT INTO diagnosis_results_new SELECT id, report_id, execution_id, brand, question, model, 
--    response_content, response_latency, geo_data, quality_score, quality_level, 
--    quality_details, status, error_message, created_at 
-- FROM diagnosis_results_backup;
--
-- 4. 替换表
-- DROP TABLE diagnosis_results;
-- ALTER TABLE diagnosis_results_new RENAME TO diagnosis_results;
--
-- 5. 清理
-- DROP TABLE diagnosis_results_backup;

-- ==================== 验证查询 ====================
-- 执行后可验证字段是否添加成功：
-- PRAGMA table_info(diagnosis_results);
