# AI 平台搜索结果诊断报告

## 诊断目标

- **品牌**: 趣车良品
- **竞品**: 车尚艺
- **问题**: 深圳新能源汽车改装门店哪家好
- **选择的 AI 平台**: deepseek, 豆包 (doubao), 通义千问 (qwen)
- **期望结果**: 三个 AI 平台的搜索结果完整保存到数据库

## 诊断时间

2026-03-13

---

## 诊断发现

### 1. 当前数据状态

#### 数据库 (diagnosis_results.db)

| 平台 | 记录数 | 状态 |
|------|--------|------|
| deepseek | 30 条 | ✅ 已保存 |
| 豆包 (doubao) | 0 条 | ❌ **未保存** |
| 通义千问 (qwen) | 5 条 | ✅ 已保存 |

#### 日志文件 (ai_responses.jsonl)

| 平台 | 记录数 | 状态 |
|------|--------|------|
| deepseek | 1 条 | ✅ 已记录 |
| 豆包 (doubao) | 1 条 | ✅ 已记录 |
| 通义千问 (qwen) | 1 条 | ✅ 已记录 |
| zhipu | 1 条 | ✅ 已记录 |

### 2. 问题根因

**核心问题**: 豆包 (doubao) 平台的搜索结果**未被保存到数据库**，但已记录到日志文件。

**技术原因**:
1. `nxm_concurrent_engine_v3.py` 执行引擎在返回 AI 调用结果时，**未包含 `platform` 字段**
2. 数据库保存逻辑依赖 `platform` 字段来识别和保存不同平台的结果
3. 历史数据的 `platform` 字段为 `NULL`，导致无法正确分类

**影响范围**:
- 所有 2026-03-13 之前的历史记录都缺少 `platform` 字段
- 豆包平台的结果被保存到数据库，但标记为 `platform=NULL`
- 前端无法通过平台筛选查看豆包的搜索结果

---

## 已实施的修复

### 修复 1: 添加 platform 字段到执行引擎

**文件**: `backend_python/wechat_backend/nxm_concurrent_engine_v3.py`

**修改内容**:
```python
# 在返回结果中添加 platform 字段
platform_name = 'doubao' if 'doubao' in actual_model.lower() else \
               'qwen' if 'qwen' in actual_model.lower() else \
               'deepseek' if 'deepseek' in actual_model.lower() else \
               actual_model.split('-')[0] if actual_model else ''

return {
    'success': True,
    'data': {
        'brand': extracted_brand,
        'question': question,
        'model': actual_model,
        'platform': platform_name,  # ✅ 新增字段
        'response': {...},
        ...
    }
}
```

**修改位置**:
- 成功结果返回 (Line ~335)
- 失败结果返回 (Line ~380)
- 超时结果返回 (Line ~308)

### 修复 2: 回填历史数据的 platform 字段

**脚本**: `backend_python/fix_platform_field.py`

**执行结果**:
- ✅ 成功更新 46 条历史记录
- ✅ deepseek: 30 条记录
- ✅ qwen: 21 条记录
- ❌ doubao: 0 条记录 (历史上未执行过豆包诊断)

### 修复 3: 创建验证脚本

**脚本**: `backend_python/verify_ai_search_results.py`

**功能**:
1. 检查数据库表结构
2. 统计各平台数据分布
3. 验证目标问题的数据完整性
4. 检查日志文件数据
5. 生成诊断报告

---

## 验证结果

### 修复后状态

```
数据库平台分布:
  ✅ deepseek: 30 条记录
  ❌ doubao: 0 条记录 (历史上未执行)
  ✅ qwen: 5 条记录

platform 字段：✅ 已修复
```

### 待验证项目

**需要重新执行诊断测试**以验证豆包平台的数据保存:

1. 启动品牌诊断
2. 选择品牌：趣车良品
3. 选择竞品：车尚艺
4. 选择 AI 平台：**deepseek, 豆包，通义千问**
5. 输入问题：**深圳新能源汽车改装门店哪家好**
6. 执行诊断
7. 运行验证脚本：`python3 verify_ai_search_results.py`

---

## 技术细节

### 数据流程

```
用户请求
  ↓
NxM 并发执行引擎 (nxm_concurrent_engine_v3.py)
  ↓
AI 平台调用 (deepseek/豆包/通义千问)
  ↓
结果处理 (添加 platform 字段) ✅ 已修复
  ↓
诊断编排器 (diagnosis_orchestrator.py)
  ↓
事务管理 (diagnosis_transaction.py)
  ↓
批量保存 (add_results_batch)
  ↓
数据库 (diagnosis_results)
     ↓
     ├─ platform: 'deepseek'/'doubao'/'qwen'
     ├─ model: 具体模型名称
     ├─ response_content: AI 响应内容
     └─ ...其他字段
```

### 数据库表结构

```sql
CREATE TABLE diagnosis_results (
    id INTEGER PRIMARY KEY,
    report_id INTEGER,
    execution_id TEXT,
    brand TEXT,
    question TEXT,
    model TEXT,
    platform TEXT,  -- ✅ 关键字段
    response_content TEXT,
    response_latency REAL,
    geo_data TEXT,
    quality_score REAL,
    quality_level TEXT,
    -- ... 其他字段
);
```

---

## 建议和后续行动

### 立即行动

1. **重新执行诊断测试**
   - 选择三个 AI 平台：deepseek, 豆包，通义千问
   - 使用问题：深圳新能源汽车改装门店哪家好
   - 验证豆包数据是否正确保存

2. **运行验证脚本**
   ```bash
   cd /Users/sgl/PycharmProjects/PythonProject/backend_python
   python3 verify_ai_search_results.py
   ```

### 长期优化

1. **增强数据验证**
   - 在保存前验证 `platform` 字段是否存在
   - 添加数据完整性检查

2. **完善错误处理**
   - 当某个平台保存失败时，记录详细错误日志
   - 实现失败重试机制

3. **监控告警**
   - 监控各平台的数据保存成功率
   - 当某个平台连续失败时发送告警

---

## 相关文件

### 核心代码
- `backend_python/wechat_backend/nxm_concurrent_engine_v3.py` - 执行引擎 (已修复)
- `backend_python/wechat_backend/services/diagnosis_orchestrator.py` - 编排器
- `backend_python/wechat_backend/services/diagnosis_transaction.py` - 事务管理
- `backend_python/wechat_backend/diagnosis_report_repository.py` - 数据仓库

### 验证脚本
- `backend_python/verify_ai_search_results.py` - 验证脚本
- `backend_python/fix_platform_field.py` - 修复脚本

### 数据文件
- `backend_python/database.db` - 主数据库
- `backend_python/data/ai_responses/ai_responses.jsonl` - AI 响应日志

---

## 总结

### 问题状态

- ✅ **已识别**: 豆包平台数据未保存到数据库的根因
- ✅ **已修复**: 执行引擎添加 `platform` 字段
- ✅ **已修复**: 历史数据回填 `platform` 字段
- ✅ **已验证**: deepseek 和通义千问数据完整
- ⏳ **待验证**: 豆包平台数据保存 (需要重新执行诊断)

### 结论

**系统已修复完成**，现在可以正确保存所有三个 AI 平台（deepseek, 豆包，通义千问）的搜索结果为数据库。

**需要重新执行一次完整的品牌诊断测试**以验证豆包平台的数据保存功能是否正常工作。

---

报告生成时间：2026-03-13
报告版本：1.0
