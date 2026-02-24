-- ============================================================
-- 品牌诊断报告存储架构优化 - 数据库索引脚本
-- 创建日期：2026-02-25
-- 版本：1.0
-- ============================================================

-- ============================================================
-- 1. diagnosis_reports 表索引
-- ============================================================

-- 用户 ID 索引 - 加速用户历史查询
CREATE INDEX IF NOT EXISTS idx_reports_user_id 
ON diagnosis_reports(user_id);

-- 创建时间索引 - 加速按时间排序
CREATE INDEX IF NOT EXISTS idx_reports_created_at 
ON diagnosis_reports(created_at);

-- 品牌名称索引 - 加速按品牌筛选
CREATE INDEX IF NOT EXISTS idx_reports_brand_name 
ON diagnosis_reports(brand_name);

-- 状态索引 - 加速状态筛选
CREATE INDEX IF NOT EXISTS idx_reports_status 
ON diagnosis_reports(status);

-- 执行 ID 索引（UNIQUE 约束已创建，此处为查询优化）
CREATE INDEX IF NOT EXISTS idx_reports_execution_id 
ON diagnosis_reports(execution_id);

-- 复合索引：用户 + 时间（常用查询）
CREATE INDEX IF NOT EXISTS idx_reports_user_created 
ON diagnosis_reports(user_id, created_at DESC);

-- ============================================================
-- 2. diagnosis_results 表索引
-- ============================================================

-- 执行 ID 索引 - 加速按执行 ID 查询结果
CREATE INDEX IF NOT EXISTS idx_results_execution_id 
ON diagnosis_results(execution_id);

-- 报告 ID 索引 - 加速关联查询
CREATE INDEX IF NOT EXISTS idx_results_report_id 
ON diagnosis_results(report_id);

-- 品牌索引 - 加速按品牌筛选
CREATE INDEX IF NOT EXISTS idx_results_brand 
ON diagnosis_results(brand);

-- 模型索引 - 加速按模型筛选
CREATE INDEX IF NOT EXISTS idx_results_model 
ON diagnosis_results(model);

-- 状态索引 - 加速状态筛选
CREATE INDEX IF NOT EXISTS idx_results_status 
ON diagnosis_results(status);

-- 复合索引：执行 ID+ 品牌（常用查询）
CREATE INDEX IF NOT EXISTS idx_results_exec_brand 
ON diagnosis_results(execution_id, brand);

-- ============================================================
-- 3. diagnosis_analysis 表索引
-- ============================================================

-- 执行 ID 索引 - 加速按执行 ID 查询分析
CREATE INDEX IF NOT EXISTS idx_analysis_execution_id 
ON diagnosis_analysis(execution_id);

-- 报告 ID 索引 - 加速关联查询
CREATE INDEX IF NOT EXISTS idx_analysis_report_id 
ON diagnosis_analysis(report_id);

-- 分析类型索引 - 加速按类型筛选
CREATE INDEX IF NOT EXISTS idx_analysis_type 
ON diagnosis_analysis(analysis_type);

-- 复合索引：执行 ID+ 类型（常用查询）
CREATE INDEX IF NOT EXISTS idx_analysis_exec_type 
ON diagnosis_analysis(execution_id, analysis_type);

-- ============================================================
-- 4. diagnosis_snapshots 表索引
-- ============================================================

-- 执行 ID 索引 - 加速按执行 ID 查询快照
CREATE INDEX IF NOT EXISTS idx_snapshots_execution_id 
ON diagnosis_snapshots(execution_id);

-- 报告 ID 索引 - 加速关联查询
CREATE INDEX IF NOT EXISTS idx_snapshots_report_id 
ON diagnosis_snapshots(report_id);

-- 创建时间索引 - 加速按时间排序
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at 
ON diagnosis_snapshots(created_at);

-- 复合索引：执行 ID+ 创建时间（历史追溯）
CREATE INDEX IF NOT EXISTS idx_snapshots_exec_created 
ON diagnosis_snapshots(execution_id, created_at DESC);

-- ============================================================
-- 索引创建完成检查
-- ============================================================

-- 输出索引创建结果
SELECT '✅ 诊断报告数据库索引创建完成' AS status;
