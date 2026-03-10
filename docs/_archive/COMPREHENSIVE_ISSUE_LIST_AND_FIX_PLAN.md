# AI 品牌诊断系统 - 全面问题清单与修复计划

**文档版本：** v2.0  
**创建日期：** 2026 年 2 月 26 日  
**优先级定义：**
- **P0-阻断性**：导致系统完全无法产出诊断报告，必须立即修复
- **P1-严重**：可能导致部分结果丢失或用户体验严重下降，本周内修复
- **P2-一般**：影响系统稳定性和可维护性，迭代内修复
- **P3-优化**：性能和技术债务问题，规划修复

---

## 执行摘要

### 核心原则
1. **诊断报告产出绝对优先** - 任何错误都不能阻止报告生成
2. **单个 AI 平台失败不影响整体** - 配额用尽等错误应优雅降级
3. **所有异常都有提醒标记** - 但不停止报告生成

### 问题统计

| 优先级 | 数量 | 状态 |
|--------|------|------|
| P0-阻断性 | 5 | 待修复 |
| P1-严重 | 8 | 待修复 |
| P2-一般 | 12 | 待修复 |
| P3-优化 | 10 | 待修复 |

**系统健康度评分：68/100**

---

## P0-阻断性问题 (必须立即修复)

### P0-001: asyncio.run() 在已有事件循环中抛出 RuntimeError

**模块：** 后端执行引擎  
**文件：** `backend_python/wechat_backend/nxm_execution_engine.py` (第 140 行)  
**影响：** 100% 诊断失败，完全无法产出报告  
**发生概率：** 高（在异步混合场景中）

**问题代码：**
```python
ai_result = asyncio.run(
    ai_executor.execute_with_fallback(
        task_func=client.send_prompt,
        task_name=f"{brand}-{model_name}",
        source=model_name,
        prompt=prompt
    )
)
```

**风险描述：**
- `asyncio.run()` 会创建新的事件循环，但在已有事件循环的线程中会抛出 `RuntimeError`
- 当上层调用栈中存在事件循环时，整个诊断流程崩溃

**修复方案：**
```python
import asyncio
import threading

def run_async_in_thread(coro):
    """在线程中安全运行异步代码"""
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# 使用方式
ai_result = await asyncio.get_event_loop().run_in_executor(
    None, 
    lambda: run_async_in_thread(
        ai_executor.execute_with_fallback(...)
    )
)
```

**预估工时：** 2 小时  
**验收标准：** 在任何线程/异步环境下都能正常执行诊断

---

### P0-002: 认证错误过早熔断导致结果丢失

**模块：** 前端轮询服务  
**文件：** `services/brandTestService.js` (第 238-245 行)  
**影响：** 临时网络波动导致轮询停止，但后端诊断仍在执行  
**发生概率：** 中（网络不稳定环境）

**问题代码：**
```javascript
let consecutiveAuthErrors = 0;
const MAX_AUTH_ERRORS = 2;  // 连续 2 次错误即熔断

if (errorInfo.isAuthError) {
  consecutiveAuthErrors++;
  if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
    controller.stop();
    console.error('认证错误熔断，停止轮询');
```

**风险描述：**
- 连续 2 次 401/403 错误即停止轮询
- 但后端诊断可能仍在执行，用户失去查看结果的机会

**修复方案：**
```javascript
// 增加重试次数并实现指数退避
const MAX_AUTH_ERRORS = 5;
const authErrorRetryDelay = Math.min(1000 * Math.pow(2, consecutiveAuthErrors), 10000);

// 在熔断前尝试刷新 token
if (consecutiveAuthErrors >= MAX_AUTH_ERRORS - 2) {
  await refreshToken();
}

// 即使轮询停止，也尝试从 Storage 恢复结果
if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
  const cachedResults = loadResultsFromStorage(executionId);
  if (cachedResults) {
    onComplete(cachedResults);
  }
}
```

**预估工时：** 2 小时  
**验收标准：** 网络波动后能恢复轮询或从缓存恢复结果

---

### P0-003: AI 错误类型映射不完整导致降级失效

**模块：** AI 适配器层  
**文件：** `backend_python/src/adapters/doubao_adapter.py` (第 230-245 行)  
**影响：** 配额用尽时无法自动切换到备用模型  
**发生概率：** 中（API 返回非标准错误信息时）

**问题代码：**
```python
def _map_error_message(self, error_message: str) -> AIErrorType:
    error_message_lower = error_message.lower()
    if "quota" in error_message_lower or "credit" in error_message_lower:
        return AIErrorType.INSUFFICIENT_QUOTA
    # 可能漏判非标准错误信息
    return AIErrorType.UNKNOWN_ERROR
```

**风险描述：**
- 错误类型映射依赖关键词匹配，可能漏判
- `UNKNOWN_ERROR` 不会触发特定的降级策略

**修复方案：**
```python
# 增强错误识别，使用正则表达式和语义分析
ERROR_PATTERNS = {
    AIErrorType.INSUFFICIENT_QUOTA: [
        r'quota', r'credit', r'余额', r'配额', r'限额',
        r'insufficient.*balance', r'not enough.*credit'
    ],
    AIErrorType.INVALID_API_KEY: [
        r'invalid.*api', r'unauthorized', r'401', r'认证失败',
        r'api.*key.*错误', r'密钥.*无效'
    ],
    AIErrorType.RATE_LIMIT_EXCEEDED: [
        r'rate.*limit', r'too.*many.*request', r'429', r'频率限制',
        r'请求.*频繁', r'speed.*limit'
    ],
}

def _map_error_message(self, error_message: str) -> AIErrorType:
    import re
    error_str = str(error_message).lower()
    
    # 检查 HTTP 状态码
    if '401' in error_str:
        return AIErrorType.INVALID_API_KEY
    if '429' in error_str:
        return AIErrorType.RATE_LIMIT_EXCEEDED
    if '503' in error_str or '502' in error_str:
        return AIErrorType.SERVICE_UNAVAILABLE
    
    # 正则匹配
    for error_type, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, error_str):
                return error_type
    
    # 语义增强：检查是否包含错误码
    if re.search(r'\b(error|err|fail|failed)\b', error_str):
        # 尝试从上下文中推断
        if any(word in error_str for word in ['money', 'pay', 'billing']):
            return AIErrorType.INSUFFICIENT_QUOTA
    
    return AIErrorType.UNKNOWN_ERROR
```

**预估工时：** 3 小时  
**验收标准：** 所有常见错误都能正确识别并触发相应降级策略

---

### P0-004: 结果持久化失败时数据完全丢失

**模块：** 后端执行引擎  
**文件：** `backend_python/wechat_backend/nxm_execution_engine.py` (第 178-200 行)  
**影响：** 服务重启时所有进度数据丢失  
**发生概率：** 中（服务不稳定时）

**问题代码：**
```python
try:
    save_dimension_result(...)
    save_task_status(...)
except Exception as persist_err:
    # 持久化失败不影响主流程，仅记录日志
    api_logger.error(f"持久化失败：{persist_err}")
    # 但没有备用存储机制！
```

**风险描述：**
- 实时持久化是"最佳努力"模式，失败时只记录日志
- 如果服务在结果返回前崩溃，所有进度数据丢失
- 用户需要重新开始完整诊断

**修复方案：**
```python
# 实现预写日志（WAL）机制
import pickle
import os

WAL_FILE = '/tmp/nxm_wal_{execution_id}.pkl'

def write_wal(execution_id: str, results: List[Dict], completed: int, total: int):
    """预写日志 - 在内存持久化前写入磁盘"""
    try:
        wal_path = WAL_FILE.format(execution_id=execution_id)
        with open(wal_path, 'wb') as f:
            pickle.dump({
                'execution_id': execution_id,
                'results': results,
                'completed': completed,
                'total': total,
                'timestamp': time.time()
            }, f)
        api_logger.info(f"WAL 已写入：{wal_path}")
    except Exception as e:
        api_logger.error(f"WAL 写入失败：{e}")

def read_wal(execution_id: str) -> Optional[Dict]:
    """读取预写日志"""
    try:
        wal_path = WAL_FILE.format(execution_id=execution_id)
        if os.path.exists(wal_path):
            with open(wal_path, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        api_logger.error(f"WAL 读取失败：{e}")
    return None

# 在执行引擎中使用
# 每次 AI 调用成功后立即写入 WAL
write_wal(execution_id, results, completed, total_tasks)

# 服务启动时检查未完成的执行
def recover_from_wal():
    """从 WAL 恢复未完成的执行"""
    import glob
    wal_files = glob.glob('/tmp/nxm_wal_*.pkl')
    for wal_file in wal_files:
        # 检查 WAL 是否过期（超过 24 小时）
        # 如果未过期，尝试恢复执行
```

**预估工时：** 4 小时  
**验收标准：** 服务重启后能从 WAL 恢复进度，用户无需重新诊断

---

### P0-005: 前端数据加载竞态条件导致空结果展示

**模块：** 前端结果页  
**文件：** `pages/results/results.js` (第 105-150 行)  
**影响：** 用户看到"暂无数据"，即使后端已完成诊断  
**发生概率：** 低（但在慢网络环境下可能发生）

**问题代码：**
```javascript
onLoad: async function(options) {
  const executionId = options.executionId;
  
  // 优先尝试从缓存加载
  const cachedResults = wx.getStorageSync('last_diagnostic_results');
  if (cachedResults && cachedResults.timestamp) {
    this.setData({ reportData: cachedResults });
    return;  // 提前返回
  }

  // 从 Storage 加载
  let storageData = loadDiagnosisResult(executionId);
  // 如果 storageData 为空，页面显示"暂无数据"
  // 但 API 数据可能正在加载中...
}
```

**风险描述：**
- 多个加载源（缓存、Storage、API）之间存在竞态
- 如果缓存数据过期但 API 数据尚未加载完成，页面可能显示空状态

**修复方案：**
```javascript
onLoad: async function(options) {
  const executionId = options.executionId;
  
  // 显示加载中状态
  this.setData({ isLoading: true, showLoadingSpinner: true });
  
  // 并行加载所有数据源
  const [cachedResults, storageData, apiData] = await Promise.allSettled([
    this.loadFromCache(),
    this.loadFromStorage(executionId),
    this.loadFromApi(executionId)
  ]);
  
  // 选择最优结果（优先级：API > Storage > Cache）
  let bestResult = null;
  
  if (apiData.status === 'fulfilled' && apiData.value && apiData.value.results) {
    bestResult = apiData.value;
  } else if (storageData.status === 'fulfilled' && storageData.value) {
    bestResult = storageData.value;
  } else if (cachedResults.status === 'fulfilled' && cachedResults.value) {
    bestResult = cachedResults.value;
  }
  
  // 如果有结果，展示数据
  if (bestResult) {
    this.setData({ 
      reportData: bestResult,
      isLoading: false,
      showLoadingSpinner: false
    });
  } else {
    // 所有数据源都失败，显示错误提示
    this.setData({ 
      isLoading: false,
      showLoadingSpinner: false,
      showErrorBanner: true,
      errorMessage: '加载诊断结果失败，请重试'
    });
  }
}
```

**预估工时：** 3 小时  
**验收标准：** 在任何网络条件下都能正确展示结果或明确的错误提示

---

## P1-严重问题 (本周内修复)

### P1-001: 质量评分服务在空结果时返回零分而非错误标记

**模块：** 质量评分服务  
**文件：** `backend_python/wechat_backend/services/quality_scorer.py` (第 44-55 行)  
**影响：** 用户看到"质量较差"而非"诊断失败"提示  
**发生概率：** 中（所有 AI 调用失败时）

**问题代码：**
```python
def calculate(self, results: List[Dict], completion_rate: int) -> Dict:
    if not results:
        return {
            'quality_score': 0,
            'quality_level': 'poor',
            'details': {...}
        }
    # 正常评分逻辑...
```

**修复方案：**
```python
def calculate(self, results: List[Dict], completion_rate: int) -> Dict:
    if not results:
        return {
            'quality_score': 0,
            'quality_level': 'failed',  # 新增 failed 等级
            'has_valid_results': False,  # 明确标记无有效结果
            'details': {
                'completion_score': 0,
                'completeness_score': 0,
                'source_score': 0,
                'sentiment_score': 0,
                'error_message': '未获取任何有效诊断结果'
            }
        }
```

**预估工时：** 1 小时

---

### P1-002: 流式渲染在大数据量时阻塞 UI 线程

**模块：** 流式报告聚合器  
**文件：** `services/streamingReportAggregator.js` (第 85-120 行)  
**影响：** 小程序触发"页面长时间无响应"警告  
**发生概率：** 低（结果数超过 100 条时）

**修复方案：** 使用 `setTimeout` 分片计算
```javascript
async *stream() {
  // 将大数据集分片处理
  const CHUNK_SIZE = 20;
  for (let i = 0; i < this.rawResults.length; i += CHUNK_SIZE) {
    const chunk = this.rawResults.slice(i, i + CHUNK_SIZE);
    this.cleanedResults.push(...sanitizeResults(chunk));
    
    // 让出 UI 线程
    await new Promise(resolve => setTimeout(resolve, 0));
    yield yieldStage('cleaning', { progress: (i + CHUNK_SIZE) / this.rawResults.length });
  }
  // ...其他阶段同样处理
}
```

**预估工时：** 2 小时

---

### P1-003: 电路断路器恢复超时硬编码

**模块：** 电路断路器  
**文件：** `backend_python/wechat_backend/circuit_breaker.py` (第 35-50 行)  
**影响：** 所有平台使用相同恢复超时，不够灵活  

**修复方案：** 根据错误类型动态调整
```python
def get_recovery_timeout(self, error_type: AIErrorType) -> int:
    """根据错误类型返回恢复超时"""
    timeout_map = {
        AIErrorType.INSUFFICIENT_QUOTA: 300,  # 5 分钟（配额充值需要时间）
        AIErrorType.RATE_LIMIT_EXCEEDED: 60,   # 1 分钟
        AIErrorType.SERVICE_UNAVAILABLE: 120,  # 2 分钟
        AIErrorType.SERVER_ERROR: 180,         # 3 分钟
        AIErrorType.INVALID_API_KEY: -1,       # 不自动恢复，需要人工干预
    }
    return timeout_map.get(error_type, 30)  # 默认 30 秒
```

**预估工时：** 1.5 小时

---

### P1-004: 前端轮询间隔动态调整算法过于激进

**模块：** 前端轮询服务  
**文件：** `services/brandTestService.js` (第 300 行附近)  
**影响：** 150ms 间隔可能对后端造成压力  

**修复方案：**
```javascript
const getPollingInterval = (progress, stage, lastResponseTime = 100) => {
  // 根据进度和阶段动态调整
  if (progress < 10) {
    return 2000;  // 初期慢速轮询
  } else if (progress < 50) {
    return 1000;  // 中期正常轮询
  } else if (progress < 90) {
    return 500;   // 后期加速
  } else {
    return 200;   // 完成前快速轮询
  }
};
```

**预估工时：** 1 小时

---

### P1-005: 结果去重逻辑可能导致有效数据丢失

**模块：** 结果聚合器  
**文件：** `backend_python/wechat_backend/nxm_result_aggregator.py`  
**影响：** 不同模型的相似结果被误删  

**修复方案：** 改进去重算法，考虑模型差异
```python
def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """去重时保留不同模型的结果"""
    seen = {}
    deduplicated = []
    
    for result in results:
        # 使用 品牌 + 问题 + 模型 作为唯一键
        key = f"{result.get('brand')}_{result.get('question')}_{result.get('model')}"
        
        if key not in seen:
            seen[key] = True
            deduplicated.append(result)
    
    return deduplicated
```

**预估工时：** 1.5 小时

---

### P1-006: 错误日志中可能包含敏感信息

**模块：** 容错执行器  
**文件：** `backend_python/wechat_backend/fault_tolerant_executor.py` (第 180 行)  
**影响：** API Key 可能泄露到日志中  

**修复方案：**
```python
def _format_error_details(self, exception: Exception, task_name: str, source: str) -> str:
    """格式化详细错误信息（脱敏处理）"""
    error_str = str(exception)
    
    # 脱敏 API Key
    error_str = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-***REDACTED***', error_str)
    error_str = re.sub(r'api[_-]?key[=:]\s*[\'"]?[a-zA-Z0-9]{20,}[\'"]?', 'api_key=***REDACTED***', error_str, flags=re.IGNORECASE)
    
    error_details = [
        f"Task: {task_name}",
        f"Source: {source or 'unknown'}",
        f"Error Type: {type(exception).__name__}",
        f"Error Message: {error_str}",  # 使用脱敏后的错误信息
        f"Traceback:\n{traceback.format_exc()}"
    ]
    
    return " | ".join(error_details)
```

**预估工时：** 1 小时

---

### P1-007: 数据库连接未使用连接池

**模块：** 数据库层  
**文件：** 多个数据库操作文件  
**影响：** 高并发时可能耗尽 SQLite 连接  

**修复方案：** 实现连接池
```python
import sqlite3
from contextlib import contextmanager
from queue import Queue
import threading

class SQLiteConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.pool = Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        
        # 预创建连接
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)

# 使用方式
db_pool = SQLiteConnectionPool('diagnosis.db')

with db_pool.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM results")
```

**预估工时：** 3 小时

---

### P1-008: 前端 Storage 键名不一致

**模块：** 存储管理器  
**文件：** `utils/storage-manager.js`  
**影响：** 数据混乱，Storage 容量快速耗尽  

**修复方案：** 统一键名命名规范
```javascript
// 统一键名常量
const STORAGE_KEYS = {
  DIAGNOSIS_RESULT: (executionId) => `diagnosis:result:${executionId}`,
  LATEST_DIAGNOSIS: 'diagnosis:latest',
  DRAFT_INPUT: 'diagnosis:draft:input',
  USER_CONFIG: 'diagnosis:user:config',
  PLATFORM_PREFS: 'diagnosis:user:platforms',
  CACHE_STATS: 'diagnosis:cache:stats'
};

// 实现 LRU 缓存淘汰
function cleanupExpiredData() {
  const keys = wx.getStorageInfoSync().keys;
  const diagnosisKeys = keys.filter(k => k.startsWith('diagnosis:result:'));
  
  // 按时间戳排序，保留最近 10 个
  const results = diagnosisKeys.map(k => ({
    key: k,
    data: wx.getStorageSync(k)
  })).filter(r => r.data && r.data.timestamp);
  
  results.sort((a, b) => b.data.timestamp - a.data.timestamp);
  
  // 删除超过 10 个的结果
  results.slice(10).forEach(r => {
    wx.removeStorageSync(r.key);
    console.log(`清理过期结果：${r.key}`);
  });
}
```

**预估工时：** 2 小时

---

## P2-一般问题 (迭代内修复)

### P2-001: 日志系统实现不一致
**文件：** 多个适配器文件  
**修复：** 统一日志接口，使用结构化日志

### P2-002: AI 平台工厂模式动态导入缺乏缓存
**文件：** `backend_python/src/adapters/factory.py`  
**修复：** 实现导入缓存机制

### P2-003: 前端错误提示文本过长被截断
**文件：** `services/brandTestService.js`  
**修复：** 限制提示文本长度，使用分页展示

### P2-004: 缺少 AI 调用指标收集
**修复：** 收集成功率、延迟、成本指标

### P2-005: 结果页缺少配额用尽的明确提示
**修复：** 在结果卡片中添加配额状态标记

### P2-006: 诊断进度 SSE 推送未完全启用
**修复：** 启用 SSE 并禁用轮询降级

### P2-007: AI 响应缓存未实现
**修复：** 对相同品牌 + 问题组合缓存结果

### P2-008: 缺少性能监控仪表板
**修复：** 实现实时监控和告警

### P2-009: 前端加载状态指示器不明显
**修复：** 添加骨架屏和进度动画

### P2-010: 结果页缺少数据刷新机制
**修复：** 添加手动刷新按钮和自动刷新

### P2-011: 错误边界处理不完善
**修复：** 在组件级别添加错误边界

### P2-012: 配置管理缺少版本控制
**修复：** 实现配置版本管理和回滚

---

## P3-优化建议 (规划修复)

### P3-001: 实现 AI 调用预热机制
在诊断开始前预热 AI 适配器

### P3-002: 优化 Storage 压缩策略
对大结果集使用 gzip 压缩

### P3-003: 实现结果预取机制
在诊断完成前预加载结果页框架

### P3-004: 添加诊断进度可视化
在首页显示实时进度条

### P3-005: 优化粒子背景动画性能
减少动画帧率或禁用低性能设备动画

### P3-006: 实现智能降级策略
根据历史成功率自动选择最优平台

### P3-007: 添加 A/B 测试框架
测试不同的错误提示和 UI 文案

### P3-008: 优化首屏加载时间
使用代码分割和懒加载

### P3-009: 实现离线模式
支持离线查看历史诊断结果

### P3-010: 添加性能预算监控
监控并告警性能退化

---

## 修复优先级矩阵

| 问题编号 | 影响程度 | 发生概率 | 修复难度 | 优先级得分 | 修复顺序 |
|---------|---------|---------|---------|-----------|---------|
| P0-001 | 10 | 8 | 3 | 96 | 1 |
| P0-002 | 9 | 6 | 2 | 81 | 2 |
| P0-003 | 8 | 7 | 4 | 78 | 3 |
| P0-004 | 9 | 5 | 5 | 72 | 4 |
| P0-005 | 7 | 5 | 3 | 52 | 5 |
| P1-001 | 7 | 6 | 2 | 50 | 6 |
| P1-002 | 6 | 4 | 3 | 36 | 7 |
| P1-003 | 5 | 6 | 2 | 36 | 8 |
| P1-004 | 5 | 5 | 2 | 30 | 9 |
| P1-005 | 6 | 4 | 2 | 29 | 10 |

---

## 验收标准

### 核心验收标准
1. **任何单个 AI 平台失败不影响整体报告生成**
2. **配额用尽时在结果中明确标记，不影响其他平台结果**
3. **所有异常都有用户友好的提示和解决建议**
4. **诊断报告产出率 > 99%**（即使部分结果缺失）
5. **用户无需重新诊断即可看到可用结果**

### 技术指标
- 诊断完成率：> 99%
- 平均诊断时间：< 5 分钟
- 错误提示覆盖率：100%
- 数据持久化成功率：> 99.9%
- 前端加载成功率：> 99%

---

## 团队分工

| 模块 | 负责人 | 协同 |
|------|-------|------|
| 后端执行引擎 | 首席架构师 | 全栈工程师 |
| AI 适配器层 | 全栈工程师 | 性能专家 |
| 前端轮询 | 全栈工程师 | 测试工程师 |
| 数据持久化 | 首席架构师 | 全栈工程师 |
| 质量评分 | 测试工程师 | 全栈工程师 |
| 错误处理 | 测试工程师 | 全栈工程师 |

---

## 时间表

| 阶段 | 时间 | 目标 |
|------|------|------|
| P0 修复 | 第 1 周 | 完成所有 P0 问题修复 |
| P1 修复 | 第 2 周 | 完成所有 P1 问题修复 |
| P2 修复 | 第 3-4 周 | 完成 50% P2 问题修复 |
| P3 优化 | 第 2 季度 | 按需实施 |

---

**文档维护：** 首席架构师  
**最后更新：** 2026 年 2 月 26 日  
**下次审查：** 2026 年 3 月 5 日
