# 全局任务执行超时问题综合修复报告

## 问题概述

根据errorlog.md日志分析，系统存在全局任务执行超时问题，导致16个测试用例执行总耗时681.86秒，超过了600秒的全局超时限制。由于选择了豆包模型，系统使用了顺序执行策略（max_workers: 1），导致总执行时间超过了超时限制。

## 修复措施

### 1. 分批次保存机制 (Checkpoint Saving)

**目标**: 每完成一个模型立即保存结果到数据库，避免因超时导致已完成任务结果丢失。

**实现**:
- 修改 [TestExecutor](file:///Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/test_engine/executor.py#L15-L157) 类的 `execute_tests` 方法
- 在 `progress_callback` 回调函数中添加即时保存逻辑
- 每当一个测试任务成功完成后，立即调用 `save_test_record` 保存结果到数据库
- 保存的数据包含执行ID、品牌名称、AI模型、问题和响应等信息

**效果**: 即使发生超时，已完成的测试结果也不会丢失。

### 2. 全局超时限制调整

**目标**: 将全局超时限制从600秒调整为动态计算，适应更多测试用例。

**实现**:
- 修改 `views.py` 文件中的 `run_async_test` 函数
- 实现动态超时计算：`dynamic_timeout = min(1200, 600 + len(all_test_cases) * 30)`
- 基础超时时间600秒，每个测试额外增加30秒，最高不超过1200秒

**效果**: 超时限制更具弹性，能够适应不同数量的测试用例。

### 3. 并发降级策略优化

**目标**: 优化并发策略，在保证稳定性的同时提高执行效率。

**实现**:
- 修改 `views.py` 文件中的执行策略判断逻辑
- 仅对包含豆包平台的情况使用并发度2（原为1），而非完全顺序执行
- 对不包含豆包的平台使用并发度3
- 保留对豆包平台的特殊处理，但适度提高并发度

**效果**: 在保持稳定性的同时，提高了整体执行效率。

### 4. 重试逻辑优化

**目标**: 优化重试机制，避免重试进一步消耗总时间配额。

**实现**:
- 修改 `scheduler.py` 文件中的重试逻辑
- 将最大等待时间限制为5秒（原为指数增长，可能达到数分钟）
- 在最后一次尝试后不再等待
- 使用 `min(2 ** attempt, 5)` 确保等待时间不会过长

**效果**: 减少重试对总执行时间的影响，避免不必要的等待。

## 技术细节

### TestExecutor 类修改

在 `execute_tests` 方法中添加了 `user_openid` 参数，并在 `progress_callback` 中实现了即时保存：

```python
# 实现分批次保存：每完成一个测试就立即保存到数据库
try:
    # 提取模型名称，将其格式化为一致的格式
    model_name = task.ai_model
    if model_name.lower() in ['豆包', 'doubao']:
        model_display_name = '豆包'
    elif model_name.lower() in ['deepseek', 'deepseekr1']:
        model_display_name = 'DeepSeek'
    elif model_name.lower() in ['qwen', '通义千问', '千问']:
        model_display_name = '通义千问'
    elif model_name.lower() in ['zhipu', '智谱ai', '智谱']:
        model_display_name = '智谱AI'
    else:
        model_display_name = model_name
    
    # 创建一个单独的测试结果记录并保存到数据库
    single_test_result = {
        'brand_name': task.brand_name,
        'question': task.question,
        'ai_model': model_display_name,
        'response': result.get('result', ''),
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'execution_id': execution_id
    }
    
    # 保存单个测试结果到数据库
    record_id = save_test_record(
        user_openid=user_openid,
        brand_name=task.brand_name,
        ai_models_used=[model_display_name],
        questions_used=[task.question],
        overall_score=0,  # 暂时设为0，因为这是单个测试的结果
        total_tests=1,
        results_summary={'individual_test': True, 'task_id': task.id, 'execution_id': execution_id},
        detailed_results=[single_test_result]
    )
    
    api_logger.info(f"Saved individual test result to database with ID: {record_id}")
    
except Exception as e:
    api_logger.error(f"Failed to save individual test result to database: {e}")
```

### 动态超时计算

在 `views.py` 中实现动态超时：

```python
# 动态计算超时时间：基础600秒 + 每个测试额外30秒（最多可调整到1200秒）
dynamic_timeout = min(1200, 600 + len(all_test_cases) * 30)  # 每个测试增加30秒
results = executor.execute_tests(all_test_cases, api_key, lambda eid, p: progress_callback(execution_id, p), timeout=dynamic_timeout, user_openid=user_id or "anonymous")
```

### 优化的执行策略

```python
# 【优化】检测是否包含豆包平台，如果是则使用顺序执行避免超时，其他平台可并发执行
has_doubao_only = any(
    'doubao' in model.get('name', '').lower() or 
    '豆包' in model.get('name', '')
    for model in selected_models
)

# 对于仅包含豆包的情况，使用顺序执行以确保稳定性
# 对于包含其他平台的情况，可以适当提升并发度
if has_doubao_only:
    # 包含豆包时使用较低的并发度以确保稳定性
    executor = TestExecutor(max_workers=2, strategy=ExecutionStrategy.CONCURRENT)
    api_logger.info(f"[ExecutionStrategy] Detected Doubao platform, using CONCURRENT execution with max_workers=2 for stability")
else:
    # 不包含豆包时可以使用更高的并发度
    executor = TestExecutor(max_workers=3, strategy=ExecutionStrategy.CONCURRENT)
    api_logger.info(f"[ExecutionStrategy] Using CONCURRENT execution with max_workers=3")
```

### 改进的重试逻辑

```python
# 【优化】改进重试逻辑，减少对总时间的影响
# 使用较短的指数退避策略，避免长时间等待
if attempt < task.max_retries - 1:  # 不在最后一次尝试后等待
    sleep_time = min(2 ** attempt, 5)  # 最多等待5秒，避免长时间阻塞
    time.sleep(sleep_time)
```

## 修复验证

### 预期效果

1. **分批次保存**: 即使发生超时，已完成的测试结果也会被保存到数据库
2. **动态超时**: 根据测试用例数量自动调整超时时间，减少超时概率
3. **优化并发**: 适度提高并发度，在稳定性和效率之间取得平衡
4. **改进重试**: 减少重试等待时间，避免过多占用总执行时间

### 性能改进

- 减少了因超时导致的数据丢失风险
- 提高了系统的容错能力
- 在保证稳定性的前提下提升了执行效率
- 优化了资源利用，减少了不必要的等待时间

## 总结

通过以上四个方面的综合优化，系统现在能够更好地处理大量测试用例的执行任务，显著降低了超时风险，并确保了即使在超时情况下已完成的工作也不会丢失。这些改进提高了系统的可靠性和用户体验。