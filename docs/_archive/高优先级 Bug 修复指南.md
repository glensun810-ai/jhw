# 高优先级 Bug 修复指南

**日期**: 2026-02-23
**优先级**: 🔴 高

---

## BUG-NEW-001: setInterval + async 并发问题

### 问题位置
**文件**: `services/brandTestService.js`
**行号**: 204-280

### 问题描述
```javascript
// ❌ 当前代码（第 204 行）
pollInterval = setInterval(async () => {
  // 问题：setInterval 不会等待 async 完成
  // 如果 API 耗时 5 秒，interval 800ms，会有 6 个并发请求
  const res = await getTaskStatusApi(executionId);
  // ...
}, interval);
```

### 修复方案

**步骤 1**: 打开 `services/brandTestService.js`

**步骤 2**: 找到第 204 行附近的 `createPollingController` 函数

**步骤 3**: 找到这段代码：
```javascript
// 启动定时轮询
pollInterval = setInterval(async () => {
  // ... 约 70 行代码 ...
}, interval);
```

**步骤 4**: 替换为：
```javascript
// 启动定时轮询 - BUG-NEW-001 修复：改用递归 setTimeout
let pollTimeout = null;

const poll = async () => {
  try {
    // 超时检查
    if (Date.now() - startTime > maxDuration) {
      stop();
      console.error('轮询超时 (总超时 10 分钟)');
      if (onError) onError(new Error('诊断超时'));
      return;
    }

    // 无进度超时检查
    if (Date.now() - lastProgressTime > noProgressTimeout) {
      stop();
      console.error('轮询超时 (8 分钟无进度更新)');
      if (onError) onError(new Error('诊断超时'));
      return;
    }

    if (isStopped) return;

    const res = await getTaskStatusApi(executionId);

    if (res && (res.progress !== undefined || res.stage)) {
      const parsedStatus = parseTaskStatus(res);

      if (parsedStatus.progress > 0 || parsedStatus.stage !== 'init') {
        lastProgressTime = Date.now();
      }

      const newInterval = getPollingInterval(parsedStatus.progress, parsedStatus.stage);
      if (newInterval !== interval) {
        interval = newInterval;
        console.log(`[性能优化] 调整轮询间隔：${interval}ms`);
      }

      if (onProgress) onProgress(parsedStatus);

      if (parsedStatus.stage === 'completed' || parsedStatus.stage === 'failed') {
        stop();
        if (parsedStatus.stage === 'completed' && onComplete) {
          onComplete(parsedStatus);
        } else if (onError) {
          onError(new Error(parsedStatus.error || '诊断失败'));
        }
        return;
      }
    }
  } catch (err) {
    console.error('轮询异常:', err);
    if (onError) onError(createUserFriendlyError(err));
  } finally {
    // ✅ 关键修复：确保前一个请求完成后再发起下一个
    if (!isStopped) {
      pollTimeout = setTimeout(poll, interval);
    }
  }
};

// 启动第一次轮询
poll();

// 更新 stop 函数
stop = () => {
  if (pollTimeout) { clearTimeout(pollTimeout); pollTimeout = null; }
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  isStopped = true;
};
```

**步骤 5**: 保存文件

**步骤 6**: 验证语法
```bash
node -c services/brandTestService.js
```

**步骤 7**: 提交代码
```bash
git add services/brandTestService.js
git commit -m "🐛 修复 BUG-NEW-001: setInterval + async 并发问题"
git push
```

---

## BUG-NEW-002: 异步执行引擎未集成

### 问题位置
**文件**: `backend_python/wechat_backend/nxm_execution_engine.py`

### 问题描述
- 已创建 `async_execution_engine.py`
- 但未集成到 `nxm_execution_engine.py`
- 导致 AI 调用仍然同步执行，性能损失 60%

### 修复方案（简略）

**步骤**:
1. 在 `nxm_execution_engine.py` 中导入异步引擎
2. 将双重 for 循环改为异步并发执行
3. 使用 `asyncio.gather()` 并发执行所有 AI 调用

**详细方案见**: `docs/2026-02-23_性能瓶颈分析与优化方案.md`

**预计工时**: 4 小时

---

## BUG-NEW-003: 数据库连接可能泄漏

### 问题位置
**文件**: `backend_python/wechat_backend/views.py`

### 问题描述
```python
# ❌ 当前代码
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT ...")
# 如果中间抛出异常，conn.close() 不会执行
conn.close()
```

### 修复方案

**步骤 1**: 打开 `views.py`

**步骤 2**: 搜索所有数据库连接

**步骤 3**: 使用 try-finally 包裹：
```python
# ✅ 修复后
conn = None
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    # ...
finally:
    if conn:
        conn.close()
```

**步骤 4**: 或使用上下文管理器（推荐）：
```python
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

# 使用
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
```

**预计工时**: 0.5 小时

---

## 修复优先级

1. ✅ **BUG-NEW-001**: 立即修复（1 小时）
2. ⏳ **BUG-NEW-002**: 本周内（4 小时）
3. ⏳ **BUG-NEW-003**: 本周内（0.5 小时）

---

## 验证方法

### BUG-NEW-001 验证
```javascript
// 微信开发者工具控制台
// 观察日志，应该看到：
// "[性能优化] 调整轮询间隔：2000ms"
// 不应该看到并发请求
```

### BUG-NEW-003 验证
```bash
# 查看数据库连接数
sqlite3 backend_python/database.db "SELECT COUNT(*) FROM pragma_database_list;"
# 应该保持稳定，不增长
```

---

**指南生成时间**: 2026-02-23 21:30
**状态**: ⏳ 待修复
