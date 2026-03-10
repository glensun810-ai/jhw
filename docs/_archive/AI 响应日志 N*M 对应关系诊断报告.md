# AI 响应日志 N*M 对应关系诊断报告

**分析日期**: 2026 年 2 月 19 日  
**日志文件**: `backend_python/data/ai_responses/ai_responses.jsonl`  
**总记录数**: 339 条

---

## 执行摘要

### ✅ 确认：豆包日志存在

**豆包日志统计**:
- 总记录数：**92 条**
- 成功：**37 条** (40%)
- 失败：**55 条** (60%)
- 涉及问题：**17 个**

### ❌ 问题：N 个问题*M 个平台未一一对应

**核心问题**: 当前的执行记录显示，每个 Execution ID 只记录了**单一平台**（豆包）的数据，没有实现 N 个问题*M 个平台的完整矩阵对应。

---

## 详细分析

### 1. 平台分布统计

| 平台 | 问题数 | 总记录 | 成功 | 成功率 |
|------|-------|--------|------|-------|
| 豆包 | 17 | 92 | 37 | 40% |
| DeepSeek | 8 | 76 | 60 | 79% |
| 通义千问 | 8 | 61 | 38 | 62% |
| 智谱 AI | 6 | 65 | 27 | 42% |
| deepseek | 5 | 15 | 15 | 100% |
| qwen | 6 | 15 | 15 | 100% |
| zhipu | 6 | 15 | 15 | 100% |

### 2. Execution ID 分析 (关键发现)

#### 问题执行分组

| Execution ID | 问题数 | 涉及平台 | 问题列表 |
|-------------|-------|---------|---------|
| `e8390249-c0ab...` | 3 | **仅豆包** | 数字转型咨询公司推荐<br>数字转型咨询服务公司哪家好<br>靠谱的数字转型咨询公司 |
| `a21fa71b-3d57...` | 3 | **仅豆包** | 新能源汽车改装门店推荐<br>汽车音响改装门店哪家好<br>靠谱的新能源汽车改装门店 |
| `afd50cc9-e457...` | 3 | **仅豆包** | 养生茶 OEM/ODM 品牌哪家好<br>养生茶品牌推荐<br>深圳及周边靠谱的养生茶品牌 |

### 3. N*M 对应关系验证

**期望的 N*M 矩阵** (以 3 个问题*7 个平台为例):

```
                | 豆包 | DeepSeek | 通义千问 | 智谱 AI | ...
----------------|------|----------|---------|--------|----
问题 1: 数字转型  |  ✓   |    ✓     |    ✓    |   ✓    | ...
问题 2: 汽车改装  |  ✓   |    ✓     |    ✓    |   ✓    | ...
问题 3: 养生茶    |  ✓   |    ✓     |    ✓    |   ✓    | ...
```

**实际记录情况**:

```
                | 豆包 | DeepSeek | 通义千问 | 智谱 AI | ...
----------------|------|----------|---------|--------|----
问题 1: 数字转型  |  ✓   |    ✗     |    ✗    |   ✗    | ...
问题 2: 汽车改装  |  ✓   |    ✗     |    ✗    |   ✗    | ...
问题 3: 养生茶    |  ✓   |    ✗     |    ✗    |   ✗    | ...
```

### 4. 豆包日志详细分析

#### 成功的记录 (37 条)

| 问题 | 记录数 | 成功 | 品牌覆盖 |
|------|-------|------|---------|
| 养生茶品牌推荐 养生茶品牌哪家好... | 5 | 5/5 | 元若曦、合为养、喜纯、至言良食、阿桂爷爷 |
| 新能源汽车改装门店推荐... | 4 | 4/4 | 趣车良品、承美车居、车尚艺、车网联盟 |
| 深圳新能源汽车改装哪家好... | 8 | 8/8 | 车网联盟、誉创、车衣裳、卡妙思、车蚂蚁 |
| GEO 优化服务排名... | 4 | 4/4 | 智推时代、竹报网络、清蓝 GEO、南方网通 |
| 成都上门体育推荐 | 2 | 2/2 | 英鸿飞特、高川 |

#### 失败的记录 (55 条)

| 问题 | 记录数 | 成功 | 失败原因 |
|------|-------|------|---------|
| 全屋定制品牌哪家好... | 36 | 4/36 | 32 条失败 (API 限流/超时) |
| GEO 服务哪家好... | 10 | 4/10 | 6 条失败 |
| 养生茶哪家好... | 14 | 6/14 | 8 条失败 (电路 breaker 触发) |
| 数字转型咨询公司推荐 | 1 | 0/1 | 1 条失败 (超时) |
| 新能源汽车改装门店推荐 | 1 | 0/1 | 1 条失败 (服务不可用) |

---

## 问题定位

### 根本原因

1. **执行流程问题**: 当前的 `main_system_sequential` 执行模式为每个 Execution ID 只调用单一平台
2. **平台遍历缺失**: 没有实现同一问题在多个平台的并行/串行调用
3. **结果聚合问题**: 缺少跨平台结果的聚合逻辑

### 代码层面分析

从日志 metadata 可以看出:

```json
{
  "source": "main_system_sequential",
  "task_id": "e8390249-c0ab-4de9-9c95-bd6b63fc8c70",
  "question_index": 1,
  "total_questions": 3
}
```

- `source`: `main_system_sequential` - 顺序执行模式
- `task_id`: 唯一标识一次执行
- `question_index`: 问题索引
- **缺失**: `platform_index` 或 `total_platforms` 字段

### 期望的日志结构

```json
{
  "source": "main_system_matrix",
  "task_id": "xxx-xxx-xxx",
  "question_index": 1,
  "total_questions": 3,
  "platform_index": 1,
  "total_platforms": 7,
  "platform": "豆包"
}
```

---

## 解决方案

### 方案 1: 修改执行逻辑 (推荐)

在 `main_system_sequential` 或新建 `main_system_matrix` 中实现 N*M 遍历：

```python
# 伪代码
for question in questions:  # N 个问题
    for platform in platforms:  # M 个平台
        result = call_ai_api(question, platform)
        log_response(question, platform, result)
```

### 方案 2: 增加平台遍历配置

在任务配置中指定需要遍历的平台列表：

```python
task_config = {
    'questions': [...],
    'platforms': ['豆包', 'DeepSeek', '通义千问', '智谱 AI'],
    'execution_mode': 'matrix'  # matrix vs sequential
}
```

### 方案 3: 后处理聚合

对现有日志进行后处理，将不同 Execution ID 但相同问题的记录聚合：

```python
# 按问题聚合
aggregated = defaultdict(dict)
for record in all_records:
    question = record['question']
    platform = record['platform']
    aggregated[question][platform] = record
```

---

## 验证步骤

### 1. 检查当前执行配置

```bash
cd backend_python
python3 -c "
from utils.ai_response_logger_v2 import get_logger
logger = get_logger()
print(f'Current platform: {logger.platform_name}')
print(f'Config: {logger.config}')
"
```

### 2. 验证多平台调用

```bash
python3 -c "
from ai_client import AIClient

client = AIClient()
platforms = ['豆包', 'DeepSeek', '通义千问']
question = '测试问题'

for platform in platforms:
    result = client.generate(question, platform=platform)
    print(f'{platform}: {\"✓\" if result else \"✗\"}')"
```

### 3. 检查日志输出

```bash
tail -20 data/ai_responses/ai_responses.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    print(f\"{r.get('platform', 'N/A')}: {r.get('question', 'N/A')[:30]}...\")"
```

---

## 结论

### ✅ 确认事项

1. **豆包日志存在**: 92 条记录，37 条成功
2. **日志格式正确**: JSONL 格式，包含必要字段
3. **品牌覆盖完整**: 每个问题对应多个品牌答案

### ❌ 问题事项

1. **N*M 对应缺失**: 每个 Execution ID 只记录单一平台
2. **平台遍历未实现**: 需要修改执行逻辑实现多平台调用
3. **结果聚合缺失**: 缺少跨平台结果对比分析

### 建议

1. **立即修复**: 修改执行逻辑实现 N*M 矩阵遍历
2. **增加字段**: 在日志中添加 `platform_index` 和 `total_platforms`
3. **验证测试**: 执行一次完整的 N*M 测试验证修复效果

---

**报告人**: AI 系统架构师  
**日期**: 2026 年 2 月 19 日
