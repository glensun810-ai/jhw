-- ============================================================
-- 品牌诊断报告完整性增强 - 数据库表结构迁移
-- 创建日期：2026-03-13
-- 版本：1.1
-- 
-- 目标：
-- 1. 添加缺失的字段以支持完整的诊断报告检索
-- 2. 添加响应元数据字段（tokens, finish_reason, request_id 等）
-- 3. 添加重试和降级标记字段
-- ============================================================

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. 诊断结果明细表字段增强
-- ============================================================

-- 添加响应元数据字段
ALTER TABLE diagnosis_results ADD COLUMN response_metadata TEXT;

-- 添加 Token 统计字段
ALTER TABLE diagnosis_results ADD COLUMN tokens_used INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN completion_tokens INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN cached_tokens INTEGER DEFAULT 0;

-- 添加 API 响应详情字段
ALTER TABLE diagnosis_results ADD COLUMN finish_reason TEXT DEFAULT 'stop';
ALTER TABLE diagnosis_results ADD COLUMN request_id TEXT;
ALTER TABLE diagnosis_results ADD COLUMN model_version TEXT;
ALTER TABLE diagnosis_results ADD COLUMN reasoning_content TEXT;

-- 添加 API 信息字段
ALTER TABLE diagnosis_results ADD COLUMN api_endpoint TEXT;
ALTER TABLE diagnosis_results ADD COLUMN service_tier TEXT DEFAULT 'default';

-- 添加重试和降级标记
ALTER TABLE diagnosis_results ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE diagnosis_results ADD COLUMN is_fallback BOOLEAN DEFAULT 0;

-- 添加更新时间字段
ALTER TABLE diagnosis_results ADD COLUMN updated_at TEXT;

-- ============================================================
-- 2. 创建索引以优化查询性能
-- ============================================================

-- 为新增的查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_results_updated_at ON diagnosis_results(updated_at);
CREATE INDEX IF NOT EXISTS idx_results_quality_score ON diagnosis_results(quality_score);
CREATE INDEX IF NOT EXISTS idx_results_status_exec ON diagnosis_results(status, execution_id);

-- ============================================================
-- 3. 数据迁移（如果表已有数据）
-- ============================================================

-- 更新现有记录的 updated_at 字段
UPDATE diagnosis_results 
SET updated_at = created_at 
WHERE updated_at IS NULL;

-- 更新现有记录的 tokens_used（如果有 response_metadata）
UPDATE diagnosis_results 
SET 
    tokens_used = COALESCE(json_extract(response_metadata, '$.usage.total_tokens'), 0),
    prompt_tokens = COALESCE(json_extract(response_metadata, '$.usage.prompt_tokens'), 0),
    completion_tokens = COALESCE(json_extract(response_metadata, '$.usage.completion_tokens'), 0),
    cached_tokens = COALESCE(json_extract(response_metadata, '$.usage.prompt_tokens_details.cached_tokens'), 0),
    finish_reason = COALESCE(json_extract(response_metadata, '$.choices[0].finish_reason'), 'stop'),
    request_id = json_extract(response_metadata, '$.request_id'),
    model_version = json_extract(response_metadata, '$.model'),
    api_endpoint = json_extract(response_metadata, '$.api_endpoint'),
    service_tier = COALESCE(json_extract(response_metadata, '$.service_tier'), 'default')
WHERE response_metadata IS NOT NULL;

-- ============================================================
-- 4. 验证迁移结果
-- ============================================================

-- 检查表结构
SELECT '✅ 诊断结果表字段增强完成' AS migration_status;

-- 显示新增字段
SELECT 
    'diagnosis_results 表字段统计:' AS info,
    COUNT(*) AS total_columns
FROM PRAGMA_TABLE_INFO('diagnosis_results');

-- 显示记录统计
SELECT 
    'diagnosis_results 表记录统计:' AS info,
    COUNT(*) AS total_records,
    COUNT(DISTINCT execution_id) AS unique_executions
FROM diagnosis_results;

-- ============================================================
-- 迁移完成
-- ============================================================
