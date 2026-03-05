# API Field Naming Convention Fix Plan

## 问题描述

前后端数据交换点存在字段命名不一致问题：
- **前端**: 使用 camelCase (如 `selectedModels`, `customQuestions`)
- **后端**: 使用 snake_case (如 `execution_id`, `brand_name`, `selected_models`)

## 影响范围

### 1. 后端 API 响应字段 (需要转换为 camelCase)

| 当前字段 (snake_case) | 目标字段 (camelCase) | 出现位置 | 优先级 |
|---------------------|---------------------|---------|--------|
| `execution_id` | `executionId` | 所有 API 响应 | P0 |
| `report_id` | `reportId` | 所有 API 响应 | P0 |
| `brand_name` | `brandName` | 报告数据、状态响应 | P0 |
| `competitor_brands` | `competitorBrands` | 报告数据、配置 | P0 |
| `selected_models` | `selectedModels` | 报告数据、配置 | P0 |
| `custom_questions` | `customQuestions` | 报告数据、配置 | P0 |
| `is_completed` | `isCompleted` | 状态响应 | P1 |
| `created_at` | `createdAt` | 时间戳字段 | P1 |
| `completed_at` | `completedAt` | 时间戳字段 | P1 |
| `should_stop_polling` | `shouldStopPolling` | 轮询控制 | P1 |

### 2. 前端请求字段 (保持不变，已是 camelCase)

| 字段 | 说明 | 位置 |
|-----|------|------|
| `selectedModels` | 选中的 AI 模型列表 | `/api/perform-brand-test` |
| `customQuestions` | 自定义问题列表 | `/api/perform-brand-test` |

### 3. 后端内部处理 (保持 snake_case)

后端数据库操作、内部函数参数等**保持 snake_case**，仅在 API 边界层转换。

## 修复策略

### 方案 A: 后端统一返回 camelCase (推荐) ✅

**优点:**
1. 符合前端 JavaScript 开发习惯
2. 与项目文档规范一致 (见 `2026-02-27-重构开发规范.md`)
3. 减少前端适配代码

**缺点:**
1. 需要修改后端多个视图文件

**实施:**
- 在 API 响应层进行字段转换
- 保持数据库和内部处理使用 snake_case

### 方案 B: 前端适配 snake_case

**优点:**
1. 后端无需修改

**缺点:**
1. 前端代码风格不一致
2. 需要大量前端适配代码
3. 违反项目规范

**不推荐** ❌

## 修复清单

### 核心 API 文件

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `backend_python/wechat_backend/views/diagnosis_api.py` | 响应字段转 camelCase | ⏳ |
| `backend_python/wechat_backend/views/diagnosis_views.py` | 响应字段转 camelCase | ⏳ |
| `backend_python/wechat_backend/views/diagnosis_views_v2.py` | 响应字段转 camelCase | ⏳ |
| `backend_python/wechat_backend/views/sync_views.py` | 响应字段转 camelCase | ⏳ |

### 辅助函数

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `backend_python/wechat_backend/views/brand_test_helpers.py` | 配置数据转 camelCase | ⏳ |
| `backend_python/wechat_backend/diagnosis_report_service.py` | 报告数据转 camelCase | ⏳ |
| `backend_python/wechat_backend/state_manager.py` | 状态响应转 camelCase | ⏳ |

### 云函数

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `miniprogram/cloudfunctions/startDiagnosis/index.js` | 响应字段映射 | ⏳ |
| `miniprogram/cloudfunctions/getDiagnosisReport/index.js` | 响应字段映射 | ⏳ |

## 转换工具函数

创建统一的字段转换工具：

```python
# backend_python/utils/field_converter.py

def to_camel_case(snake_str: str) -> str:
    """
    将 snake_case 转换为 camelCase
    
    Examples:
        execution_id -> executionId
        brand_name -> brandName
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_response_to_camel(data: dict) -> dict:
    """
    将 API 响应字典的键名转换为 camelCase
    
    Args:
        data: 原始字典 (snake_case keys)
    
    Returns:
        转换后的字典 (camelCase keys)
    """
    if not isinstance(data, dict):
        return data
    
    camel_data = {}
    for key, value in data.items():
        # 递归处理嵌套字典和列表
        if isinstance(value, dict):
            camel_data[to_camel_case(key)] = convert_response_to_camel(value)
        elif isinstance(value, list):
            camel_data[to_camel_case(key)] = [
                convert_response_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            camel_data[to_camel_case(key)] = value
    
    return camel_data
```

## 实施步骤

### Step 1: 创建字段转换工具
- 文件：`backend_python/utils/field_converter.py`
- 优先级：P0

### Step 2: 修改核心 API 响应
- 修改 `diagnosis_api.py` 中的响应
- 修改 `diagnosis_views.py` 中的响应
- 优先级：P0

### Step 3: 修改辅助函数
- 修改 `brand_test_helpers.py` 中的配置数据
- 修改 `state_manager.py` 中的状态响应
- 优先级：P0

### Step 4: 修改云函数
- 修改云函数中的字段映射
- 优先级：P1

### Step 5: 测试验证
- 启动诊断流程测试
- 检查轮询状态更新
- 验证报告数据展示
- 优先级：P0

## 验证清单

- [ ] 诊断启动 API 返回 `executionId` 而不是 `execution_id`
- [ ] 状态轮询 API 返回 `brandName`, `competitorBrands` 等
- [ ] 报告数据 API 返回所有字段为 camelCase
- [ ] 前端能正确解析新格式数据
- [ ] 历史报告数据兼容
- [ ] 数据库查询不受影响

## 回滚方案

如遇到问题，可通过以下方式快速回滚：
1. 移除字段转换逻辑
2. 前端临时添加 snake_case 适配层
3. 使用特性开关控制转换

## 参考文档

- `2026-02-27-重构开发规范.md` - 命名规范
- `docs/2026-02-22_诊断报告数据需求与存储交叉验证报告.md` - 字段一致性讨论
- `FRONTEND_MODIFICATION_GUIDELINES.md` - 前端修改规范

---

**创建时间**: 2026-03-04
**负责人**: 首席全栈工程师
**状态**: 待实施
