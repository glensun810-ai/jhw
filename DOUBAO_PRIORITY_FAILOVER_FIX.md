# 豆包多模型优先级故障转移修复报告

**修复日期**: 2026-02-24  
**问题级别**: 🔴 P0 关键修复  
**修复状态**: ✅ **已完成**

---

## 📊 问题分析

### 用户需求
配置了 4 个豆包模型 ID，期望行为：
1. ✅ 按优先级顺序调用（优先级 1 → 2 → 3 → 4）
2. ✅ 第一个耗尽时自动切换到第二个
3. ✅ 第二个耗尽时自动切换到第三个
4. ✅ 以此类推，直到所有模型都耗尽
5. ❌ **不要**因为第一个用完就卡死
6. ❌ **不要**一次性调用所有模型（浪费配额）

### 原有问题

#### 问题 1: 健康检查消耗配额 ❌
```python
def _init_adapter(self):
    for model_id in self.priority_models:
        adapter = DoubaoAdapter(...)
        adapter._health_check()  # ❌ 消耗配额！
```

**影响**: 初始化时就可能耗尽所有模型配额

---

#### 问题 2: 故障转移逻辑不完善 ❌
```python
def send_prompt(self, prompt, **kwargs):
    response = self.selected_adapter.send_prompt(prompt)
    
    if response.error_type in [SERVICE_UNAVAILABLE, SERVER_ERROR]:
        self._retry_with_next_model()  # ❌ 只检查错误类型，不检查 429
```

**影响**: 429 配额耗尽错误不会触发切换

---

#### 问题 3: 没有记录已耗尽模型 ❌
```python
# 没有记录哪个模型已经配额耗尽
# 每次都可能尝试已耗尽的模型
```

**影响**: 重复尝试已耗尽的模型，浪费时间

---

## 🔧 修复方案

### 修复 1: 添加已耗尽模型记录 ✅

```python
def __init__(self, ...):
    # 【P0 修复】记录 429 错误的模型（配额耗尽）
    self.exhausted_models: set = set()
```

**效果**: 
- ✅ 记录哪些模型已经配额耗尽
- ✅ 避免重复尝试已耗尽的模型

---

### 修复 2: 移除健康检查 ✅

```python
def _init_adapter(self) -> bool:
    for i, model_id in enumerate(self.priority_models):
        # 【P0 修复】跳过已耗尽的模型
        if model_id in self.exhausted_models:
            api_logger.info(f"⏭️  跳过已耗尽模型：{model_id}")
            continue
        
        # 创建适配器实例（不执行健康检查，避免消耗配额）
        adapter = DoubaoAdapter(...)
        # ❌ 删除：adapter._health_check()
```

**效果**:
- ✅ 初始化时不消耗配额
- ✅ 跳过已耗尽的模型

---

### 修复 3: 429 错误触发切换 ✅

```python
def send_prompt(self, prompt, **kwargs) -> AIResponse:
    max_retries = len(self.priority_models)
    retry_count = 0
    
    while retry_count < max_retries:
        response = self.selected_adapter.send_prompt(prompt, **kwargs)
        
        if response.success:
            return response
        
        # 【P0 修复】检查是否是 429 配额耗尽错误
        is_429 = False
        if '429' in str(response.error_message) or 'SetLimitExceeded' in str(response.error_message):
            is_429 = True
            api_logger.warning(f"🔥 模型 {self.selected_model} 配额耗尽 (429)")
        
        # 如果失败且错误类型是服务不可用或 429，尝试切换模型
        if is_429 or response.error_type in [SERVICE_UNAVAILABLE, SERVER_ERROR]:
            if self._retry_with_next_model(self.selected_model, is_429_error=is_429):
                retry_count += 1
                continue  # 使用新模型重试
        
        return response
```

**效果**:
- ✅ 检测到 429 错误时自动切换
- ✅ 标记耗尽的模型，避免重复尝试
- ✅ 重试所有可用模型，直到成功

---

### 修复 4: 只切换下一个模型 ✅

```python
def _retry_with_next_model(self, failed_model: str, is_429_error: bool = False) -> bool:
    # 【P0 修复】如果是 429 错误，标记为已耗尽
    if is_429_error:
        self.exhausted_models.add(failed_model)
        api_logger.warning(f"🔒 模型 {failed_model} 配额耗尽，已锁定")
    
    failed_index = self.priority_models.index(failed_model)
    
    # 【P0 修复】只尝试下一个模型，不循环尝试所有
    for i in range(failed_index + 1, min(failed_index + 2, len(self.priority_models))):
        next_model = self.priority_models[i]
        
        # 【P0 修复】跳过已耗尽的模型
        if next_model in self.exhausted_models:
            api_logger.info(f"⏭️  跳过已耗尽模型：{next_model}")
            continue
        
        # 创建新适配器（不执行健康检查）
        adapter = DoubaoAdapter(...)
        self.selected_adapter = adapter
        self.selected_model = next_model
        
        return True  # 成功切换
    
    return False  # 无更多可用模型
```

**效果**:
- ✅ 只切换下一个模型，不一次性尝试所有
- ✅ 跳过已耗尽的模型
- ✅ 429 错误时锁定模型

---

## 📊 工作流程

### 修复前
```
初始化
  ↓
健康检查模型 1 → 消耗配额 ❌
  ↓
健康检查模型 2 → 消耗配额 ❌
  ↓
健康检查模型 3 → 消耗配额 ❌
  ↓
健康检查模型 4 → 消耗配额 ❌
  ↓
所有配额耗尽，无法调用 ❌
```

### 修复后
```
初始化
  ↓
选择模型 1（不健康检查）
  ↓
调用 API
  ├─ 成功 → 返回结果 ✅
  └─ 429 错误 → 标记模型 1 耗尽，切换到模型 2
       ↓
  调用 API
       ├─ 成功 → 返回结果 ✅
       └─ 429 错误 → 标记模型 2 耗尽，切换到模型 3
            ↓
       调用 API
            ├─ 成功 → 返回结果 ✅
            └─ 429 错误 → 标记模型 3 耗尽，切换到模型 4
                 ↓
            调用 API
                 ├─ 成功 → 返回结果 ✅
                 └─ 429 错误 → 标记模型 4 耗尽
                      ↓
                 所有模型耗尽，返回错误 ❌
```

---

## 📝 修改文件清单

| 文件 | 修改内容 | 行数变化 |
|------|----------|----------|
| `doubao_priority_adapter.py` | 添加 exhausted_models 记录 | +3 |
| `doubao_priority_adapter.py` | 移除健康检查 | -3 |
| `doubao_priority_adapter.py` | 修改 _init_adapter | +10 |
| `doubao_priority_adapter.py` | 修改 _retry_with_next_model | +15 |
| `doubao_priority_adapter.py` | 修改 send_prompt | +40 |
| **总计** | **5 处修改** | **+65 行** |

---

## ✅ 验证标准

### 预期日志输出

#### 场景 1: 模型 1 成功
```
[DoubaoPriority] 尝试初始化适配器，优先级模型列表：['model-1', 'model-2', ...]
[DoubaoPriority] 尝试模型 1/4: model-1
[DoubaoPriority] ✅ 模型 model-1 可用，已选中
[DoubaoPriority] 使用模型 model-1 发送请求 (尝试 1/4)
[DoubaoPriority] ✅ 模型 model-1 调用成功
```

#### 场景 2: 模型 1 耗尽，切换到模型 2
```
[DoubaoPriority] 使用模型 model-1 发送请求 (尝试 1/4)
[DoubaoPriority] 🔥 模型 model-1 配额耗尽 (429)
[DoubaoPriority] 模型 model-1 调用失败，尝试切换模型
[DoubaoPriority] 🔒 模型 model-1 配额耗尽，已锁定
[DoubaoPriority] 切换到下一个优先级模型：model-2
[DoubaoPriority] ✅ 成功切换到模型 model-2
[DoubaoPriority] 切换成功，使用新模型 model-2 重试
[DoubaoPriority] ✅ 模型 model-2 调用成功
```

#### 场景 3: 所有模型耗尽
```
[DoubaoPriority] 🔥 模型 model-1 配额耗尽 (429)
[DoubaoPriority] 🔒 模型 model-1 配额耗尽，已锁定
[DoubaoPriority] ✅ 成功切换到模型 model-2
[DoubaoPriority] 🔥 模型 model-2 配额耗尽 (429)
[DoubaoPriority] 🔒 模型 model-2 配额耗尽，已锁定
[DoubaoPriority] ✅ 成功切换到模型 model-3
[DoubaoPriority] 🔥 模型 model-3 配额耗尽 (429)
[DoubaoPriority] 🔒 模型 model-3 配额耗尽，已锁定
[DoubaoPriority] ✅ 成功切换到模型 model-4
[DoubaoPriority] 🔥 模型 model-4 配额耗尽 (429)
[DoubaoPriority] 🔒 模型 model-4 配额耗尽，已锁定
[DoubaoPriority] ❌ 无更多可用模型
```

---

## 🚀 部署步骤

### 1. 重启后端服务
```bash
cd backend_python
pkill -f "python.*app.py" || true
python -m uvicorn app:app --host 0.0.0.0 --port 5001 --reload
```

### 2. 清除前端缓存
微信开发者工具 → 工具 → 清除缓存 → 清除全部缓存

### 3. 重新编译
点击微信开发者工具的"编译"按钮

### 4. 测试诊断
1. 在首页输入品牌名称
2. 选择"豆包"AI 模型
3. 点击"开始诊断"
4. 观察后端日志

---

## 📊 修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 初始化消耗配额 | ❌ 是 | ✅ 否 |
| 429 触发切换 | ❌ 否 | ✅ 是 |
| 记录耗尽模型 | ❌ 否 | ✅ 是 |
| 跳过耗尽模型 | ❌ 否 | ✅ 是 |
| 只切换下一个 | ❌ 否 | ✅ 是 |
| 支持 4 个模型轮询 | ❌ 否 | ✅ 是 |

---

## 🎯 配置示例

### .env 文件配置
```bash
# 启用豆包自动选择
DOUBAO_AUTO_SELECT=true

# 配置 4 个优先级模型（按优先级顺序）
DOUBAO_MODEL_PRIORITY_1=ep-20260212000000-gd5tq
DOUBAO_MODEL_PRIORITY_2=doubao-seed-1-8-251228
DOUBAO_MODEL_PRIORITY_3=doubao-seed-2-0-mini-260215
DOUBAO_MODEL_PRIORITY_4=doubao-seed-2-0-pro-260215
```

---

## 📞 技术支持

**修复负责人**: 首席测试工程师 & 首席全栈开发工程师  
**修复日期**: 2026-02-24  
**文档版本**: v1.0  

---

**🎉 修复完成！现在豆包多模型可以按优先级自动切换，不会因为第一个耗尽就卡死！**

**核心改进**:
1. ✅ 初始化时不消耗配额
2. ✅ 429 错误自动切换下一个模型
3. ✅ 记录并跳过已耗尽的模型
4. ✅ 只切换下一个，不一次性尝试所有
5. ✅ 支持 4 个模型轮询，充分利用配额
