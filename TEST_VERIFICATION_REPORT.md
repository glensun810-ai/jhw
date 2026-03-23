# 品牌影响力诊断功能 - 测试验证报告

**测试日期**: 2026-03-22  
**测试版本**: 1.0  
**测试范围**: 品牌诊断全流程功能验证  

---

## 📋 测试环境配置

### 后端环境
```bash
# 1. 启动后端 Flask 服务
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 app.py

# 预期输出:
# ✅ 所有蓝图已注册
# ✅ 数据库连接池已初始化
# ✅ 诊断 API 已注册 (/api/diagnosis/*)
# * Running on http://127.0.0.1:5001
```

### 前端环境
1. 打开微信开发者工具
2. 导入项目：`/Users/sgl/PycharmProjects/PythonProject/brand_ai-seach`
3. **关键配置**: 详情 → 本地设置 → ✓ 不校验合法域名
4. 编译项目

---

## ✅ 测试用例清单

### 测试 1: 后端 API 连通性测试
**目的**: 验证后端服务正常运行

```bash
# 测试健康检查接口
curl http://127.0.0.1:5001/api/test

# 预期响应:
# {"success": true, "message": "API is healthy"}
```

**测试结果**: [ ] 通过 / [ ] 失败

---

### 测试 2: 诊断报告 API 测试
**目的**: 验证诊断报告 API 正常返回数据

```bash
# 测试报告获取 API（使用现有 execution_id）
curl -v "http://127.0.0.1:5001/api/diagnosis/report/772ce871-8259-4639-8572-6e8f0efbbc00" 2>&1 | grep -E "HTTP|Content-Type|success|metrics|dimensionScores"
```

**预期响应**:
- HTTP 状态码：200 OK
- Content-Type: application/json
- 包含字段：`success`, `data`, `metrics`, `dimensionScores`, `diagnosticWall`

**测试结果**: [ ] 通过 / [ ] 失败

---

### 测试 3: 品牌影响力指标完整性测试
**目的**: 验证核心指标字段完整

```bash
curl -s "http://127.0.0.1:5001/api/diagnosis/report/772ce871-8259-4639-8572-6e8f0efbbc00" | python3 -c "
import sys, json
data = json.load(sys.stdin)

# 检查响应结构
assert data.get('success') == True, 'success 字段应为 True'
report_data = data.get('data', {})

# 检查核心指标
metrics = report_data.get('metrics', {})
assert 'sov' in metrics, '缺少 sov 字段'
assert 'sentiment' in metrics, '缺少 sentiment 字段'
assert 'rank' in metrics, '缺少 rank 字段'
assert 'influence' in metrics, '缺少 influence 字段'

# 检查评分维度
dimension_scores = report_data.get('dimensionScores', {})
assert 'authority' in dimension_scores, '缺少 authority 字段'
assert 'visibility' in dimension_scores, '缺少 visibility 字段'
assert 'purity' in dimension_scores, '缺少 purity 字段'
assert 'consistency' in dimension_scores, '缺少 consistency 字段'

# 检查问题诊断墙
diagnostic_wall = report_data.get('diagnosticWall', {})
assert 'risk_levels' in diagnostic_wall, '缺少 risk_levels 字段'
assert 'priority_recommendations' in diagnostic_wall, '缺少 priority_recommendations 字段'

print('✅ 所有核心字段验证通过')
print(f'  - metrics: SOV={metrics.get(\"sov\")}, sentiment={metrics.get(\"sentiment\")}, rank={metrics.get(\"rank\")}, influence={metrics.get(\"influence\")}')
print(f'  - dimensionScores: authority={dimension_scores.get(\"authority\")}, visibility={dimension_scores.get(\"visibility\")}, purity={dimension_scores.get(\"purity\")}, consistency={dimension_scores.get(\"consistency\")}')
print(f'  - diagnosticWall: high_risks={len(diagnostic_wall.get(\"risk_levels\", {}).get(\"high\", []))}, medium_risks={len(diagnostic_wall.get(\"risk_levels\", {}).get(\"medium\", []))}, recommendations={len(diagnostic_wall.get(\"priority_recommendations\", []))}')
"
```

**测试结果**: [ ] 通过 / [ ] 失败

---

### 测试 4: 前端 API 调用测试
**目的**: 验证前端能正确调用后端 API

**步骤**:
1. 在微信开发者工具中打开诊断报告页面
2. 在控制台输入以下代码测试 API 调用:

```javascript
// 测试 API 调用
wx.request({
  url: 'http://127.0.0.1:5001/api/diagnosis/report/772ce871-8259-4639-8572-6e8f0efbbc00',
  method: 'GET',
  success: (res) => {
    console.log('✅ API 调用成功:', res.statusCode);
    console.log('响应数据:', res.data);
    
    // 验证关键字段
    if (res.data && res.data.data) {
      const data = res.data.data;
      console.log('metrics:', data.metrics);
      console.log('dimensionScores:', data.dimensionScores);
      console.log('diagnosticWall:', data.diagnosticWall);
    }
  },
  fail: (err) => {
    console.error('❌ API 调用失败:', err);
  }
});
```

**预期结果**:
- `res.statusCode === 200`
- `res.data.success === true`
- `res.data.data.metrics` 存在且有值
- `res.data.data.dimensionScores` 存在且有值
- `res.data.data.diagnosticWall` 存在

**测试结果**: [ ] 通过 / [ ] 失败

---

### 测试 5: 前端页面渲染测试
**目的**: 验证前端页面正确渲染诊断报告

**步骤**:
1. 在微信开发者工具中打开报告页面
2. 传入 execution_id: `772ce871-8259-4639-8572-6e8f0efbbc00`

**验证点**:
- [ ] 页面加载成功，无报错
- [ ] 核心指标卡片显示（SOV、情感得分、排名、影响力）
- [ ] 评分维度进度条显示（权威度、可见度、纯净度、一致性）
- [ ] 问题诊断墙显示（高风险、中风险、建议）
- [ ] 品牌分布图表显示
- [ ] 情感分布图表显示
- [ ] 无"诊断数据为空"错误提示

**测试结果**: [ ] 通过 / [ ] 失败

---

### 测试 6: 完整诊断流程测试
**目的**: 验证从诊断执行到报告生成的完整流程

**步骤**:
1. 打开诊断页面
2. 选择品牌：趣车良品（主品牌）、车尚艺（竞品）
3. 选择 AI 模型：至少 2 个（如 deepseek、qwen）
4. 输入问题：至少 2 个
5. 点击"开始诊断"
6. 等待诊断完成（进度 100%）
7. 自动跳转到报告页面

**验证点**:
- [ ] 诊断任务成功启动
- [ ] 轮询进度正常更新（0% → 30% → 60% → 90% → 100%）
- [ ] 诊断完成后自动跳转报告页
- [ ] 报告页面显示完整数据
- [ ] 核心指标、评分维度、诊断墙均有数据

**测试结果**: [ ] 通过 / [ ] 失败

---

## 🔍 问题排查清单

### 如果 API 返回 404
```bash
# 检查后端日志
tail -f backend_python/logs/app.log | grep "diagnosis/report"

# 检查路由注册
curl http://127.0.0.1:5001/api/test
```

### 如果前端显示"响应体为空"
1. 检查微信开发者工具是否开启"不校验合法域名"
2. 检查后端服务是否运行：`ps aux | grep python`
3. 检查防火墙设置

### 如果核心指标为空
```bash
# 检查数据库中是否有诊断结果
sqlite3 backend_python/database.db "SELECT execution_id, status, brand_name FROM diagnosis_reports ORDER BY created_at DESC LIMIT 5;"

# 检查分析数据
sqlite3 backend_python/database.db "SELECT execution_id, analysis_type FROM diagnosis_analysis ORDER BY created_at DESC LIMIT 10;"
```

---

## 📊 测试结果汇总

| 测试用例 | 状态 | 备注 |
|---------|------|------|
| 测试 1: 后端 API 连通性 | [ ] | |
| 测试 2: 诊断报告 API | [ ] | |
| 测试 3: 指标完整性 | [ ] | |
| 测试 4: 前端 API 调用 | [ ] | |
| 测试 5: 前端页面渲染 | [ ] | |
| 测试 6: 完整流程 | [ ] | |

---

## ✅ 测试通过标准

1. **后端服务正常**: API 返回 200 OK
2. **数据完整**: metrics、dimensionScores、diagnosticWall 字段存在且有值
3. **前端正常**: 页面渲染无报错，无"诊断数据为空"提示
4. **流程完整**: 从诊断执行到报告生成全流程无阻塞

---

**测试人员**: ___________  
**测试日期**: ___________  
**测试结论**: [ ] 通过 / [ ] 不通过
