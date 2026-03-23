# 诊断报告前端无数据问题 - 第 5 次深度分析最终修复报告

**修复日期**: 2026-03-12  
**问题出现次数**: 第 5 次  
**修复状态**: 🔍 分析中...

---

## 📌 前 4 次修复失败原因分析

| 修复轮次 | 假设的根因 | 修复方案 | 为什么失败 |
|---------|-----------|---------|-----------|
| 第 1 次 | 云函数数据格式不匹配 | 添加数据解包 | ❌ 表面修复 |
| 第 2 次 | 验证失败后 db_results 为空 | 使用内存数据降级 | ❌ 绕过问题 |
| 第 3 次 | results 为空导致分布计算失败 | 添加降级计算方法 | ❌ 掩盖问题 |
| 第 4 次 | SQLite WAL 数据可见性问题 | 强制 WAL 检查点 | ❌ 可能不是唯一根因 |

---

## 🔍 第 5 次分析：新的发现

### 数据流追踪

通过在关键环节添加详细日志，我们发现：

```
阶段 2: AI 调用
  ↓
ai_results = result.get('results', [])  ✅ 有数据
  ↓
阶段 3: 结果保存（使用 DiagnosisTransaction 事务）
  ↓
_execute_in_transaction() → DiagnosisTransaction.__enter__()
  ↓
tx.add_results_batch() → 循环调用 _insert_result()
  ↓
cursor.execute("INSERT INTO diagnosis_results ...")
  ↓
事务提交：conn.commit() 在 DiagnosisTransaction.__exit__()
  ↓
连接归还到连接池
  ↓
阶段 4: 验证阶段
  ↓
ResultValidator.validate() 使用新的连接读取
  ↓
❌ 可能读取不到数据（WAL 可见性问题）
```

### 关键发现

1. **事务管理器使用独立连接**：
   - `DiagnosisTransaction` 使用 `get_connection()` 获取连接
   - 事务提交后连接归还到连接池

2. **验证阶段使用另一个连接**：
   - `ResultValidator` 使用 `get_connection()` 获取连接
   - 可能是连接池中的不同连接

3. **WAL 检查点可能未生效**：
   - 即使调用了 `PRAGMA wal_checkpoint(TRUNCATE)`
   - 如果连接池中有多个连接，其他连接可能仍然看不到数据

### 真正的问题根因

**连接池 + 事务管理 + WAL 模式的综合问题**：

1. 事务使用连接 A 写入数据
2. 事务提交后，连接 A 归还到连接池
3. 验证阶段使用连接 B 读取数据
4. **即使执行了 WAL 检查点，连接 B 的 SQLite 缓存可能仍然没有刷新**

---

## 🔧 正确的解决方案（第 5 次尝试）

### 方案：确保数据可见性的多层次保障

#### 层次 1：强制 WAL 检查点（已有）

```python
conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
```

#### 层次 2：验证阶段使用相同连接读取

修改 `ResultValidator`，使用与保存阶段相同的连接读取数据。

#### 层次 3：增加重试次数和超时时间

```python
# 原配置
max_retries: 3
base_delay: 0.1  # 100ms
timeout: 10.0    # 10 秒

# 新配置
max_retries: 10
base_delay: 0.2  # 200ms
timeout: 30.0    # 30 秒
```

#### 层次 4：添加详细追踪日志

在每个关键环节记录：
- 连接 ID
- 事务状态
- 数据数量
- WAL 检查点状态

---

## 📋 修复实施计划

### 修复 1：增加 ResultValidator 重试配置

```python
# 修改 result_validator.py
self.retry_config = RetryConfig(
    max_retries=10,      # 从 3 增加到 10
    base_delay=0.2,      # 从 100ms 增加到 200ms
    max_delay=3.0,       # 从 2 秒增加到 3 秒
    timeout=30.0,        # 从 10 秒增加到 30 秒
)
```

### 修复 2：验证阶段传递连接

修改 `_phase_results_validating`，传递保存阶段使用的连接给验证阶段。

### 修复 3：添加全链路追踪日志

在每个关键环节记录连接 ID、事务状态、数据数量。

### 修复 4：创建诊断脚本

运行实际诊断，追踪数据流。

---

## ✅ 验证方法

### 1. 运行诊断脚本

```bash
python scripts/trace_diagnosis_flow.py
```

### 2. 查看日志关键字

```bash
# 检查保存环节
grep "阶段 3 完成" logs/backend.log

# 检查 WAL 检查点
grep "WAL 检查点完成" logs/backend.log

# 检查验证环节
grep "阶段 4 验证结果" logs/backend.log

# 如果有问题，会看到：
grep "保存后立即查询为 0" logs/backend.log
grep "db_results 为空" logs/backend.log
```

### 3. 检查数据库

```bash
python scripts/trace_diagnosis_flow.py
```

---

**修复进行中...**
