# 品牌诊断系统全面测试计划

## 测试团队组成

- **首席测试专家**：负责测试策略、用例设计、结果验证
- **首席架构师**：负责系统架构审查、数据流验证
- **全栈工程师**：负责问题修复、代码优化
- **后端工程师**：负责 API 测试、数据完整性
- **前端工程师**：负责 UI 测试、用户体验

## 测试目标

确保品牌诊断系统能够：
1. ✅ 正确接收用户输入（品牌、问题、模型）
2. ✅ 调用 AI API 获取真实响应
3. ✅ 解析并保存完整的 GEO 分析结果
4. ✅ 生成全面的品牌洞察报告
5. ✅ 在前端完整展示所有结果字段

## 测试范围

### 1. 后端 API 测试
- [ ] `/api/test/start` - 启动诊断
- [ ] `/test/status/{execution_id}` - 查询状态
- [ ] `/api/test-progress` - 获取进度
- [ ] 数据完整性验证

### 2. 前端数据流测试
- [ ] 轮询逻辑正确性
- [ ] 状态解析准确性
- [ ] 数据处理完整性
- [ ] 结果展示准确性

### 3. 结果字段完整性验证
- [ ] detailed_results 数组
- [ ] geo_data 对象（所有字段）
- [ ] quality_score 和 quality_level
- [ ] competitive_analysis
- [ ] brand_scores
- [ ] semantic_drift_data
- [ ] recommendation_data

### 4. 端到端集成测试
- [ ] 完整诊断流程
- [ ] 报告生成
- [ ] 数据持久化
- [ ] 错误处理

## 测试用例

### 用例 1：单问题单模型诊断

**输入**：
```json
{
  "brandName": "趣车良品",
  "competitorBrands": ["承美车居"],
  "selectedModels": ["doubao"],
  "customQuestions": ["深圳新能源汽车改装门店推荐"]
}
```

**预期输出**：
```json
{
  "execution_id": "xxx",
  "status": "completed",
  "stage": "completed",
  "progress": 100,
  "is_completed": true,
  "detailed_results": [
    {
      "brand": "趣车良品",
      "model": "doubao",
      "question": "深圳新能源汽车改装门店推荐",
      "response": { ... },
      "geo_data": {
        "brand_mentioned": boolean,
        "rank": number,
        "sentiment": number,
        "cited_sources": array,
        "interception": string
      },
      "quality_score": number,
      "quality_level": string,
      "quality_details": { ... }
    }
  ],
  "competitive_analysis": { ... },
  "brand_scores": { ... }
}
```

### 用例 2：多问题多模型诊断

**输入**：
```json
{
  "brandName": "趣车良品",
  "selectedModels": ["doubao", "qwen", "deepseek"],
  "customQuestions": [
    "深圳新能源汽车改装门店推荐",
    "趣车良品的改装质量怎么样"
  ]
}
```

**预期输出**：
- detailed_results 数组长度 = 2 问题 × 3 模型 = 6 条结果
- 每条结果包含完整的 geo_data 和 quality_info

### 用例 3：低质量结果处理

**场景**：AI 未提及用户品牌

**预期**：
- quality_score < 30
- quality_level = 'very_low'
- stage = 'completed'（不是 'failed'）
- 结果仍然展示给用户

### 用例 4：真正失败场景

**场景**：API Key 错误、网络超时

**预期**：
- stage = 'failed'
- error 字段包含错误信息
- progress = 0
- is_completed = false

## 测试执行步骤

### 步骤 1：后端健康检查
```bash
curl http://127.0.0.1:5001/api/health
```

### 步骤 2：启动诊断
```bash
curl -X POST http://127.0.0.1:5001/api/test/start \
  -H "Content-Type: application/json" \
  -d '{
    "brand_list": ["趣车良品", "承美车居"],
    "selectedModels": ["doubao"],
    "custom_question": "深圳新能源汽车改装门店推荐"
  }'
```

### 步骤 3：轮询状态
```bash
curl http://127.0.0.1:5001/test/status/{execution_id}
```

### 步骤 4：验证结果字段
检查每个结果字段是否存在且格式正确

### 步骤 5：前端展示验证
在浏览器中查看结果页面，确认所有数据显示

## 缺陷跟踪

| ID | 严重程度 | 描述 | 状态 | 负责人 |
|----|----------|------|------|--------|
| BUG-001 | 严重 | 质量低误判为失败 | ✅ 已修复 | 全栈团队 |
| BUG-002 | 严重 | 轮询完成后不停止 | ✅ 已修复 | 前端团队 |
| BUG-003 | 高 | 数据字段丢失 | 待验证 | 后端团队 |
| BUG-004 | 中 | 结果展示不完整 | 待验证 | 前端团队 |

## 验收标准

1. **功能完整性**
   - [ ] 所有 API 端点正常工作
   - [ ] 数据流完整无丢失
   - [ ] 所有结果字段正确展示

2. **性能要求**
   - [ ] 单问题单模型：< 21 秒
   - [ ] 轮询次数：< 30 次
   - [ ] 前端渲染：< 2 秒

3. **用户体验**
   - [ ] 进度提示准确
   - [ ] 错误信息友好
   - [ ] 结果展示清晰

4. **数据完整性**
   - [ ] detailed_results 完整
   - [ ] geo_data 所有字段存在
   - [ ] quality_info 正确计算
   - [ ] competitive_analysis 完整

## 测试报告模板

```markdown
## 测试结果

### 通过率
- 后端 API: X/Y (Z%)
- 前端数据流：X/Y (Z%)
- 字段完整性：X/Y (Z%)
- 端到端：X/Y (Z%)

### 发现的问题
1. [严重] 问题描述
2. [高] 问题描述
3. [中] 问题描述

### 修复状态
- 已修复：X 个
- 待修复：X 个
- 待验证：X 个

### 结论
[通过/不通过]
```
