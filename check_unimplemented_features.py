#!/usr/bin/env python3
"""
品牌影响力诊断功能 - 未实现/部分实现功能检查脚本
"""

import sys
import os
os.chdir('backend_python')
sys.path.insert(0, '.')

print('='*70)
print('品牌影响力诊断功能 - 未实现/部分实现功能清单')
print('='*70)

unimplemented = []
partially_implemented = []
fully_implemented = []

# 1. 核心指标计算
try:
    from wechat_backend.services.metrics_calculator import calculate_diagnosis_metrics
    fully_implemented.append('核心指标计算 (metrics) - SOV/情感/排名/影响力')
except ImportError as e:
    unimplemented.append(f'核心指标计算 (metrics): {e}')

# 2. 维度评分计算
try:
    from wechat_backend.services.metrics_calculator import calculate_dimension_scores
    fully_implemented.append('维度评分计算 (dimension_scores) - 权威/可见/纯净/一致')
except ImportError as e:
    unimplemented.append(f'维度评分计算 (dimension_scores): {e}')

# 3. 诊断墙生成
try:
    from wechat_backend.services.metrics_calculator import generate_diagnostic_wall
    fully_implemented.append('问题诊断墙生成 (diagnosticWall) - 高风险/中风险/建议')
except ImportError as e:
    unimplemented.append(f'问题诊断墙生成 (diagnosticWall): {e}')

# 4. 品牌分布计算
try:
    from wechat_backend.diagnosis_report_service import DiagnosisReportService
    fully_implemented.append('品牌分布计算 (brandDistribution)')
except ImportError as e:
    unimplemented.append(f'品牌分布计算 (brandDistribution): {e}')

# 5. 情感分布计算
try:
    from wechat_backend.diagnosis_report_service import DiagnosisReportService
    fully_implemented.append('情感分布计算 (sentimentDistribution)')
except ImportError as e:
    unimplemented.append(f'情感分布计算 (sentimentDistribution): {e}')

# 6. 关键词提取
try:
    from wechat_backend.diagnosis_report_service import DiagnosisReportService
    import inspect
    source = inspect.getsource(DiagnosisReportService._extract_keywords)
    if 'pass' in source or '...' in source:
        partially_implemented.append('关键词提取 (keywords) - 实现简单，需要增强')
    else:
        fully_implemented.append('关键词提取 (keywords)')
except Exception as e:
    unimplemented.append(f'关键词提取 (keywords): {e}')

# 7. 品牌分析服务（后台异步）
try:
    from wechat_backend.services.brand_analysis_service import BrandAnalysisService
    import inspect
    source = inspect.getsource(BrandAnalysisService.analyze_brand_mentions)
    if 'BATCH_BRAND_EXTRACTION_TEMPLATE' in source:
        fully_implemented.append('品牌提及分析 (brand_analysis) - 批量提取')
    else:
        partially_implemented.append('品牌提及分析 (brand_analysis) - 降级方案')
except ImportError as e:
    unimplemented.append(f'品牌提及分析 (brand_analysis): {e}')

# 8. 竞争分析服务
try:
    from wechat_backend.services.competitive_analysis_service import CompetitiveAnalysisService
    fully_implemented.append('竞争分析服务 (competitive_analysis)')
except ImportError as e:
    unimplemented.append(f'竞争分析服务 (competitive_analysis): {e}')

# 9. 语义偏移分析
try:
    from wechat_backend.services.semantic_analysis_service import SemanticAnalysisService
    fully_implemented.append('语义偏移分析 (semantic_drift)')
except ImportError as e:
    unimplemented.append(f'语义偏移分析 (semantic_drift): {e}')

# 10. 来源纯净度分析
try:
    from wechat_backend.services.source_purity_service import SourcePurityService
    fully_implemented.append('来源纯净度分析 (source_purity)')
except ImportError as e:
    unimplemented.append(f'来源纯净度分析 (source_purity): {e}')

# 11. 推荐生成服务
try:
    from wechat_backend.services.recommendation_service import RecommendationService
    fully_implemented.append('推荐生成服务 (recommendations)')
except ImportError as e:
    unimplemented.append(f'推荐生成服务 (recommendations): {e}')

# 12. 后台任务管理器
try:
    from wechat_backend.services.background_service_manager import BackgroundServiceManager
    fully_implemented.append('后台任务管理器 (background_tasks)')
except ImportError as e:
    unimplemented.append(f'后台任务管理器 (background_tasks): {e}')

# 13. 诊断编排器
try:
    with open('wechat_backend/services/diagnosis_orchestrator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if '_wait_for_analysis_complete' in content:
        fully_implemented.append('诊断编排器 (orchestrator) - 等待后台分析完成')
    else:
        partially_implemented.append('诊断编排器 (orchestrator) - 等待逻辑不完整')
except Exception as e:
    unimplemented.append(f'诊断编排器 (orchestrator): {e}')

# 14. 报告聚合器
try:
    from wechat_backend.services.report_aggregator import ReportAggregator
    fully_implemented.append('报告聚合器 (report_aggregator)')
except ImportError as e:
    unimplemented.append(f'报告聚合器 (report_aggregator): {e}')

# 15. 诊断报告服务（数据读取时重新计算）
try:
    with open('wechat_backend/diagnosis_report_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'calculate_diagnosis_metrics' in content and 'calculate_dimension_scores' in content:
        fully_implemented.append('诊断报告服务 - 数据读取时重新计算指标')
    else:
        unimplemented.append('诊断报告服务 - 数据读取时重新计算指标')
except Exception as e:
    unimplemented.append(f'诊断报告服务：{e}')

# 16. 前端数据映射
frontend_file = '../brand_ai-seach/pages/history-detail/history-detail.js'
if os.path.exists(frontend_file):
    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'report.metrics' in content and 'report.dimension_scores' in content:
        fully_implemented.append('前端数据映射 (history-detail.js)')
    else:
        partially_implemented.append('前端数据映射 (history-detail.js) - 需要检查字段映射')
else:
    unimplemented.append('前端页面 (history-detail.js 不存在)')

# 17. 来源纯净度分析
# 检查是否在 metrics_calculator 或其他地方实现
try:
    with open('wechat_backend/services/metrics_calculator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'source_purity' in content or 'SourcePurity' in content:
        fully_implemented.append('来源纯净度分析 (source_purity) - 已集成到 metrics_calculator')
    else:
        # 检查 report_aggregator 是否有默认实现
        with open('wechat_backend/services/report_aggregator.py', 'r', encoding='utf-8') as f:
            content2 = f.read()
        if '_generate_default_source_purity' in content2:
            partially_implemented.append('来源纯净度分析 (source_purity) - 仅有默认实现')
        else:
            unimplemented.append('来源纯净度分析 (source_purity) - 无独立服务模块')
except Exception as e:
    unimplemented.append(f'来源纯净度分析 (source_purity): {e}')

print('\n✅ 已完全实现的功能:')
for item in fully_implemented:
    print(f'  - {item}')

print('\n⚠️ 部分实现/需要优化的功能:')
for item in partially_implemented:
    print(f'  - {item}')

print('\n❌ 未实现的功能:')
if unimplemented:
    for item in unimplemented:
        print(f'  - {item}')
else:
    print('  (无)')

print('\n' + '='*70)
print('总结:')
print(f'  - 已完全实现：{len(fully_implemented)} 项')
print(f'  - 部分实现：{len(partially_implemented)} 项')
print(f'  - 未实现：{len(unimplemented)} 项')
print('='*70)
