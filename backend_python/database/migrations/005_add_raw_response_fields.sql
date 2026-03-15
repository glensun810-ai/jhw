-- Migration: Add raw_response and brand extraction fields to diagnosis_results
-- 迁移目标：添加原始 AI 响应字段和品牌提取信息字段
--
-- 作者：系统架构组
-- 日期：2026-03-13
-- 版本：v2.1.0

-- ==================== 升级迁移 ====================

-- 1. 添加原始 AI 响应字段
ALTER TABLE diagnosis_results ADD COLUMN raw_response TEXT;

-- 2. 添加品牌提取信息字段
ALTER TABLE diagnosis_results ADD COLUMN extracted_brand TEXT;
ALTER TABLE diagnosis_results ADD COLUMN extraction_method TEXT;

-- 3. 添加模型平台字段（用于区分不同 AI 平台）
ALTER TABLE diagnosis_results ADD COLUMN platform TEXT;

-- 4. 创建索引（提高查询性能）
CREATE INDEX IF NOT EXISTS idx_results_brand ON diagnosis_results(brand);
CREATE INDEX IF NOT EXISTS idx_results_extracted_brand ON diagnosis_results(extracted_brand);

-- ==================== 降级迁移 ====================
-- 注意：SQLite 不支持 DROP COLUMN，需要重建表
-- 如需回滚，请参考 migration 004 的降级方案

-- ==================== 验证查询 ====================
-- PRAGMA table_info(diagnosis_results);
