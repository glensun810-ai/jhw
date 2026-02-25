"""
品牌诊断报告存储架构优化 - API 集成补丁

使用方法：
在 wechat_backend/app.py 中的 `app.register_blueprint(wechat_bp)` 之后添加：

```python
# Register 诊断 API Blueprint（存储架构优化版本）
try:
    from wechat_backend.views.diagnosis_api import register_diagnosis_api
    register_diagnosis_api(app)
    api_logger.info("✅ 诊断 API Blueprint 注册成功")
except Exception as e:
    api_logger.error(f"❌ 诊断 API Blueprint 注册失败：{e}")
```

在 wechat_backend/views/diagnosis_views.py 中的 run_async_test 函数内，
找到执行完成后（result 调用后）添加：

```python
# 使用新存储层保存报告
try:
    from wechat_backend.diagnosis_report_service import get_report_service
    
    service = get_report_service()
    
    # 1. 创建报告
    config = {
        'brand_name': main_brand,
        'competitor_brands': competitor_brands,
        'selected_models': selected_models,
        'custom_questions': raw_questions
    }
    report_id = service.create_report(execution_id, user_id or 'anonymous', config)
    
    # 2. 添加结果
    results = execution_store[execution_id].get('results', [])
    service.add_results_batch(report_id, execution_id, results)
    
    # 3. 添加分析数据
    analysis_data = {}
    if 'competitive_analysis' in execution_store[execution_id]:
        analysis_data['competitive_analysis'] = execution_store[execution_id]['competitive_analysis']
    if 'brand_scores' in execution_store[execution_id]:
        analysis_data['brand_scores'] = execution_store[execution_id]['brand_scores']
    service.add_analyses_batch(report_id, execution_id, analysis_data)
    
    # 4. 完成报告
    full_report = {
        'report': execution_store[execution_id],
        'results': results,
        'analysis': analysis_data
    }
    service.complete_report(execution_id, full_report)
    
    api_logger.info(f"✅ 使用新存储层保存报告：{execution_id}")
except Exception as storage_err:
    api_logger.error(f"❌ 存储层保存失败：{storage_err}")
    # 不影响原有逻辑，继续执行
```

作者：首席全栈工程师
日期：2026-02-28
"""

# 这个文件是补丁说明，不是实际代码
