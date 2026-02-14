# 微信小程序前端到后端完整流程分析计划

## 1. 前端到后端数据传递流程分析

### 1.1 前端页面结构分析
- **页面路径**: `/miniprogram/pages/index/index.wxml`
- **页面逻辑**: `/miniprogram/pages/index/index.js`
- **样式文件**: `/miniprogram/pages/index/index.wxss`

### 1.2 数据收集流程
- 品牌名称输入
- 竞争品牌输入
- 诊断问题输入
- AI平台选择（豆包平台）
- 提交按钮事件处理

### 1.3 API请求分析
- **请求端点**: `/api/perform-brand-test`
- **请求方法**: POST
- **请求数据结构**:
```json
{
  "brand_list": ["品牌A", "品牌B"],
  "selectedModels": [
    {"name": "豆包", "checked": true}
  ],
  "customQuestions": [
    "介绍一下{brandName}",
    "{brandName}的主要产品是什么？"
  ],
  "userOpenid": "用户ID",
  "userLevel": "Free"
}
```

## 2. 后端处理逻辑分析

### 2.1 API路由分析
- **文件**: `wechat_backend/views.py`
- **函数**: `perform_brand_test()`
- **装饰器**: `@require_auth_optional`, `@rate_limit`, `@monitored_endpoint`

### 2.2 请求处理流程
1. **输入验证**: 使用 `validate_and_sanitize_request`
2. **数据验证**: 验证品牌列表、模型选择、问题等
3. **任务生成**: 使用 `QuestionManager` 和 `TestCaseGenerator`
4. **异步执行**: 使用 `TestExecutor` 执行测试
5. **进度跟踪**: 使用 `execution_store` 存储进度
6. **结果处理**: 调用 `process_and_aggregate_results_with_ai_judge`

### 2.3 核心处理函数
- `process_and_aggregate_results_with_ai_judge()`: 结果聚合引擎
- `TestExecutor.execute_tests()`: 测试执行器
- `AIJudgeClient.evaluate_response()`: AI裁判评估
- `ScoringEngine.calculate()`: 评分引擎

## 3. 逐步测试计划

### 阶段1: 前端数据收集验证
- [ ] 验证前端页面数据收集是否正确
- [ ] 验证提交数据格式是否符合后端要求
- [ ] 验证API请求是否正确发送

### 阶段2: 后端接收处理验证
- [ ] 验证后端是否正确接收请求
- [ ] 验证输入数据是否正确解析
- [ ] 验证数据验证逻辑是否通过

### 阶段3: 业务逻辑处理验证
- [ ] 验证测试用例生成是否正确
- [ ] 验证AI平台调用是否成功
- [ ] 验证结果处理是否正常

### 阶段4: 结果返回验证
- [ ] 验证结果是否正确返回前端
- [ ] 验证进度跟踪是否正常
- [ ] 验证错误处理是否恰当

## 4. 详细测试脚本计划

### 4.1 前端数据验证脚本
- 模拟前端数据收集
- 验证数据格式
- 模拟API请求

### 4.2 后端端点测试脚本
- 直接调用API端点
- 验证请求处理逻辑
- 检查中间件执行情况

### 4.3 业务逻辑单元测试
- 测试测试用例生成器
- 测试AI适配器调用
- 测试结果聚合逻辑

## 5. 预期发现的问题点
- 前端数据格式与后端期望不匹配
- 模型名称映射问题（显示名 vs 实际ID）
- API密钥或配置问题
- 异步处理逻辑错误
- 结果聚合错误