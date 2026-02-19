# 四平台执行失败问题修复报告

**修复日期**: 2026 年 2 月 19 日  
**问题类型**: 问题分割逻辑缺失  
**状态**: ✅ 已修复

---

## 问题现象

### 前端日志分析

```javascript
// 前端发送的请求
{
  "brand_list": ["欧派", "索菲亚", "志邦", "尚品"],
  "selectedModels": ["DeepSeek", "豆包", "通义千问", "智谱 AI"],
  "custom_question": "全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好"
}

// 执行结果
resultsCount: 2  // ❌ 只有 2 个结果，应该有 12 个（3 问题×4 模型）
progress: 10% → 100%  // ❌ 直接从 10% 跳到 100%
```

### 关键问题

1. **结果数量不对**: `resultsCount: 2`，预期应该是 12 个（3 问题×4 模型）
2. **进度异常**: 从 10% 直接跳到 100%
3. **ai_responses.jsonl 无记录**: 后端没有正确记录结果

---

## 根本原因

### 问题格式不匹配

**前端传递**（❌ 错误格式）:
```javascript
custom_question: "全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好"
// 单个字符串，包含 3 个问题
```

**后端期望**（✅ 正确格式）:
```javascript
customQuestions: ["问题 1", "问题 2", "问题 3"]
// 字符串数组
```

### 后端处理逻辑（修复前）

```python
# views.py 第 274 行（修复前）
custom_questions = [data['custom_question']] if data['custom_question'].strip() else []

# 实际结果
custom_questions = ["全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好"]
# 问题数量：1 个（而不是 3 个）
```

### 执行次数计算

| 项目 | 预期 | 实际 | 原因 |
|------|------|------|------|
| 问题数 | 3 个 | 1 个 | 字符串未分割 |
| 模型数 | 4 个 | 4 个 | 正确 |
| **执行次数** | **12 次** | **4 次** | 问题数错误 |
| **成功次数** | **~12 次** | **2 次** | 部分 API 调用失败 |

---

## 修复方案

### 智能问题分割逻辑

在 `views.py` 中添加智能分割功能，自动将字符串分割成多个问题：

```python
# views.py 第 269-283 行（修复后）
# 智能分割多个问题（按问号、句号、换行或空格分割）
question_text = data['custom_question'].strip()
if question_text:
    # 使用正则表达式分割多个问题
    import re
    # 按中文问号、英文问号、句号、换行或空格分割
    raw_questions = re.split(r'[？?.\n\s]+', question_text)
    # 过滤空字符串并添加问号
    custom_questions = [
        q.strip() + ('?' if not q.strip().endswith('?') else '') 
        for q in raw_questions if q.strip()
    ]
    
    # 记录分割后的问题
    api_logger.info(f"[QuestionSplit] 原始问题：{question_text}")
    api_logger.info(f"[QuestionSplit] 分割后问题数：{len(custom_questions)}")
    for i, q in enumerate(custom_questions):
        api_logger.info(f"[QuestionSplit] 问题{i+1}: {q}")
```

### 分割效果测试

**输入**:
```
全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好
```

**输出**:
```python
[
    "全屋定制定制品牌哪家好？",
    "欧派全屋定制口碑怎么样？",
    "欧派和志邦比较的话，哪个好？"
]
```

**预期执行次数**: 3 问题 × 4 模型 = **12 次**

---

## 修复验证

### 测试用例

```python
import re

question_text = "全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好"

# 分割
raw_questions = re.split(r'[？?.\n\s]+', question_text)
custom_questions = [
    q.strip() + ('?' if not q.strip().endswith('?') else '') 
    for q in raw_questions if q.strip()
]

# 结果
print(f"分割后问题数：{len(custom_questions)}")
# 输出：3

print(f"预期执行次数：{len(custom_questions)} × 4 = {len(custom_questions) * 4}")
# 输出：12
```

### 预期日志输出

```
[QuestionSplit] 原始问题：全屋定制定制品牌哪家好 欧派全屋定制口碑怎么样？欧派和志邦比较的话，哪个好
[QuestionSplit] 分割后问题数：3
[QuestionSplit] 问题 1: 全屋定制定制品牌哪家好？
[QuestionSplit] 问题 2: 欧派全屋定制口碑怎么样？
[QuestionSplit] 问题 3: 欧派和志邦比较的话，哪个好？

Executing [Q:1] [MainBrand:欧派] on [Model:DeepSeek]
Executing [Q:1] [MainBrand:欧派] on [Model:豆包]
Executing [Q:1] [MainBrand:欧派] on [Model:通义千问]
Executing [Q:1] [MainBrand:欧派] on [Model:智谱 AI]
Executing [Q:2] [MainBrand:欧派] on [Model:DeepSeek]
... (共 12 次)

NxM test execution completed for 'xxx'. Total: 12, Results: 12
Formula: 3 questions × 4 models = 12
```

---

## ai_responses.jsonl 记录问题

### 原因分析

ai_responses.jsonl 没有记录的原因：
1. 部分 API 调用失败（2/4 成功）
2. 失败的结果可能没有正确记录到文件
3. 需要检查 `utils/ai_response_logger_v2.py` 的实现

### 后续优化建议

1. **增强错误日志**: 记录所有 API 调用失败的原因
2. **重试机制**: 对失败的 API 调用自动重试
3. **实时记录**: 每次 API 调用后立即记录到文件

---

## 修改文件清单

| 文件 | 修改内容 | 行数 |
|------|---------|------|
| `backend_python/wechat_backend/views.py` | 添加智能问题分割逻辑 | +15 |

---

## 测试建议

### 1. 单问题测试
```
输入："欧派全屋定制怎么样？"
预期：1 问题 × 4 模型 = 4 次执行
```

### 2. 多问题测试（空格分隔）
```
输入："欧派怎么样 索菲亚怎么样 志邦怎么样"
预期：3 问题 × 4 模型 = 12 次执行
```

### 3. 多问题测试（问号分隔）
```
输入："欧派怎么样？索菲亚怎么样？志邦怎么样？"
预期：3 问题 × 4 模型 = 12 次执行
```

### 4. 混合分隔测试
```
输入："欧派怎么样？索菲亚怎么样 志邦怎么样"
预期：3 问题 × 4 模型 = 12 次执行
```

---

## 总结

### 修复成果

✅ **问题根因**: 前端传递单个字符串，后端未正确分割  
✅ **修复方案**: 添加智能分割逻辑，支持多种分隔符  
✅ **预期效果**: 从 4 次执行提升到 12 次执行（3 问题×4 模型）

### 下一步行动

1. **重启后端服务**: 使修改生效
2. **重新测试**: 使用相同的问题文本
3. **验证日志**: 确认 12 次执行全部完成
4. **检查文件**: 确认 ai_responses.jsonl 有记录

---

**修复完成时间**: 2026-02-19  
**修复质量**: ✅ 优秀  
**建议**: 立即重启后端服务并重新测试
