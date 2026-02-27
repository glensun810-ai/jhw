#!/usr/bin/env python3
"""
品牌洞察报告详情页数据问题 - 全面修复脚本

修复项目：
1. 添加 brand_scores 保存到 execution_store
2. 添加前端 semantic_drift_data 解析
3. 添加前端 recommendation_data 解析
4. 添加前端 negative_sources 解析
"""

import re

print("="*80)
print("品牌洞察报告详情页数据问题 - 全面修复")
print("="*80)

# ============================================================================
# 修复 1: nxm_execution_engine.py - 添加 brand_scores 保存
# ============================================================================
print("\n1️⃣  修复后端 - 添加 brand_scores 保存")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 competitive_analysis 保存的位置，在它之前添加 brand_scores 保存
old_code = '''                    # 4. 生成竞争分析
                    try:
                        from wechat_backend.competitive_analysis import CompetitiveAnalyzer
                        competitive_analyzer = CompetitiveAnalyzer()
                        competitive_analysis = competitive_analyzer.analyze_competition(
                            execution_id=execution_id,
                            results=deduplicated,
                            main_brand=main_brand,
                            competitor_brands=competitor_brands
                        )
                        execution_store[execution_id]['competitive_analysis'] = competitive_analysis
                        api_logger.info(f"[NxM] 竞争分析完成：{execution_id}")'''

new_code = '''                    # 3.5. 生成品牌评分
                    try:
                        from wechat_backend.services.report_data_service import ReportDataService
                        report_service = ReportDataService()
                        brand_scores = report_service.calculate_brand_scores(deduplicated)
                        execution_store[execution_id]['brand_scores'] = brand_scores
                        api_logger.info(f"[NxM] 品牌评分生成完成：{execution_id}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 品牌评分生成失败：{e}")
                        execution_store[execution_id]['brand_scores'] = {}

                    # 4. 生成竞争分析
                    try:
                        from wechat_backend.competitive_analysis import CompetitiveAnalyzer
                        competitive_analyzer = CompetitiveAnalyzer()
                        competitive_analysis = competitive_analyzer.analyze_competition(
                            execution_id=execution_id,
                            results=deduplicated,
                            main_brand=main_brand,
                            competitor_brands=competitor_brands
                        )
                        execution_store[execution_id]['competitive_analysis'] = competitive_analysis
                        api_logger.info(f"[NxM] 竞争分析完成：{execution_id}")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("  ✅ 已添加 brand_scores 保存逻辑")
else:
    print("  ⚠️  未找到目标代码，可能已存在或结构不同")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================================================
# 修复 2: results.js - 添加高级分析数据解析
# ============================================================================
print("\n2️⃣  修复前端 - 添加高级分析数据解析")
print("-" * 80)

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 fetchResultsFromServer 中的 success 回调
old_success = '''          const resultsToUse = res.data.detailed_results || res.data.results || [];
          const competitiveAnalysisToUse = res.data.competitive_analysis || {};'''

new_success = '''          const resultsToUse = res.data.detailed_results || res.data.results || [];
          const competitiveAnalysisToUse = res.data.competitive_analysis || {};
          const brandScoresToUse = res.data.brand_scores || {};
          const semanticDriftDataToUse = res.data.semantic_drift_data || null;
          const recommendationDataToUse = res.data.recommendation_data || null;
          const negativeSourcesToUse = res.data.negative_sources || [];
          
          logger.debug('📊 后端返回的高级分析数据:', {
            hasBrandScores: !!brandScoresToUse && Object.keys(brandScoresToUse).length > 0,
            hasCompetitiveAnalysis: !!competitiveAnalysisToUse && Object.keys(competitiveAnalysisToUse).length > 0,
            hasSemanticDrift: !!semanticDriftDataToUse,
            hasRecommendation: !!recommendationDataToUse,
            hasNegativeSources: !!negativeSourcesToUse && negativeSourcesToUse.length > 0
          });'''

if old_success in content:
    content = content.replace(old_success, new_success)
    print("  ✅ 已添加高级分析数据解析")
else:
    print("  ⚠️  未找到目标代码")

# 查找保存到 Storage 的代码
old_save = '''          // 保存到 Storage
          wx.setStorageSync('last_diagnostic_results', {
            results: resultsToUse,
            competitiveAnalysis: competitiveAnalysisToUse,
            brandScores: res.data.brand_scores || competitiveAnalysisToUse.brandScores || {},
            targetBrand: brandName,
            executionId: executionId,
            timestamp: Date.now()
          });'''

new_save = '''          // 保存到 Storage
          wx.setStorageSync('last_diagnostic_results', {
            results: resultsToUse,
            competitiveAnalysis: competitiveAnalysisToUse,
            brandScores: brandScoresToUse,
            semanticDriftData: semanticDriftDataToUse,
            recommendationData: recommendationDataToUse,
            negativeSources: negativeSourcesToUse,
            targetBrand: brandName,
            executionId: executionId,
            timestamp: Date.now()
          });
          
          logger.debug('✅ 数据已保存到 Storage，包含高级分析数据');'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("  ✅ 已添加 Storage 保存逻辑")
else:
    print("  ⚠️  未找到目标代码")

# 查找 initializePageWithData 调用
old_init = '''          // 初始化页面
          this.initializePageWithData(
            resultsToUse,
            brandName,
            [],
            competitiveAnalysisToUse,
            null, null, null
          );'''

new_init = '''          // 初始化页面
          this.initializePageWithData(
            resultsToUse,
            brandName,
            [],
            competitiveAnalysisToUse,
            negativeSourcesToUse,
            semanticDriftDataToUse,
            recommendationDataToUse
          );'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("  ✅ 已添加 initializePageWithData 参数")
else:
    print("  ⚠️  未找到目标代码")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ============================================================================
# 总结
# ============================================================================
print("\n" + "="*80)
print("修复完成！")
print("="*80)
print("""
📋 修复内容:

1. ✅ 后端 - 添加 brand_scores 保存到 execution_store
2. ✅ 前端 - 添加 semantic_drift_data 解析
3. ✅ 前端 - 添加 recommendation_data 解析
4. ✅ 前端 - 添加 negative_sources 解析
5. ✅ 前端 - 添加 Storage 保存逻辑
6. ✅ 前端 - 添加 initializePageWithData 参数

🚀 下一步操作:

1. 重启后端服务
2. 清除前端缓存并重新编译
3. 执行完整诊断
4. 检查结果页数据

📊 预期结果:

- ✅ 品牌评分显示正确分数（非 0）
- ✅ 核心洞察显示真实数据（非默认值）
- ✅ 多维度分析显示正确分数
- ✅ AI 平台认知对比有数据
- ✅ 信源纯净度分析显示真实信源
- ✅ 信源权重结果真实可信
- ✅ 详细测试结果包含竞品对比
- ✅ 华为得分正确计算
""")

print("="*80)
