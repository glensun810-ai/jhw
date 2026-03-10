# AI 品牌诊断系统 - P0 问题快速修复清单

**目标：** 24 小时内完成所有 P0 问题修复  
**创建日期：** 2026 年 2 月 26 日

---

## ✅ 修复前准备

- [ ] 备份当前代码（Git 分支）
- [ ] 准备测试环境
- [ ] 准备测试用例（正常诊断流程）
- [ ] 通知团队成员

---

## 🔴 P0-001: 修复 asyncio.run() 问题

**文件：** `backend_python/wechat_backend/nxm_execution_engine.py`

### 步骤：
- [ ] 1. 在文件顶部添加导入：
  ```python
  import asyncio
  import threading
  ```

- [ ] 2. 添加辅助函数（在文件顶部）：
  ```python
  def run_async_in_thread(coro):
      """在线程中安全运行异步代码"""
      loop = asyncio.new_event_loop()
      try:
          asyncio.set_event_loop(loop)
          return loop.run_until_complete(coro)
      finally:
          loop.close()
  ```

- [ ] 3. 替换第 140 行附近的代码：
  ```python
  # 原代码：
  ai_result = asyncio.run(
      ai_executor.execute_with_fallback(...)
  )
  
  # 新代码：
  ai_result = await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: run_async_in_thread(
          ai_executor.execute_with_fallback(
              task_func=client.send_prompt,
              task_name=f"{brand}-{model_name}",
              source=model_name,
              prompt=prompt
          )
      )
  )
  ```

- [ ] 4. 测试：运行诊断流程，确认不再抛出 RuntimeError

---

## 🔴 P0-002: 修复认证错误过早熔断

**文件：** `services/brandTestService.js`

### 步骤：
- [ ] 1. 找到第 238-245 行附近

- [ ] 2. 修改错误计数器配置：
  ```javascript
  // 原代码：
  const MAX_AUTH_ERRORS = 2;
  
  // 新代码：
  const MAX_AUTH_ERRORS = 5;
  ```

- [ ] 3. 添加指数退避逻辑（在错误处理部分）：
  ```javascript
  if (errorInfo.isAuthError) {
    consecutiveAuthErrors++;
    
    // 尝试刷新 token
    if (consecutiveAuthErrors >= MAX_AUTH_ERRORS - 2) {
      await refreshToken();
    }
    
    // 计算退避延迟
    const authErrorRetryDelay = Math.min(
      1000 * Math.pow(2, consecutiveAuthErrors),
      10000
    );
    
    if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
      // 尝试从 Storage 恢复结果
      const cachedResults = loadDiagnosisResult(executionId);
      if (cachedResults && cachedResults.results) {
        console.log('认证错误熔断，但从 Storage 恢复结果');
        onComplete(cachedResults);
        return;
      }
      
      controller.stop();
      console.error('认证错误熔断，停止轮询');
    }
  }
  ```

- [ ] 4. 测试：模拟网络波动，确认能恢复轮询或展示缓存结果

---

## 🔴 P0-003: 增强 AI 错误识别

**文件：** `backend_python/src/adapters/doubao_adapter.py`

### 步骤：
- [ ] 1. 在文件顶部添加导入：
  ```python
  import re
  ```

- [ ] 2. 找到 `_map_error_message` 方法（约第 230 行）

- [ ] 3. 替换整个方法：
  ```python
  def _map_error_message(self, error_message: str) -> AIErrorType:
      """增强版错误类型映射"""
      error_str = str(error_message).lower()
      
      # 检查 HTTP 状态码
      if '401' in error_str:
          return AIErrorType.INVALID_API_KEY
      if '429' in error_str:
          return AIErrorType.RATE_LIMIT_EXCEEDED
      if '503' in error_str or '502' in error_str:
          return AIErrorType.SERVICE_UNAVAILABLE
      
      # 正则匹配
      ERROR_PATTERNS = {
          AIErrorType.INSUFFICIENT_QUOTA: [
              r'quota', r'credit', r'余额', r'配额', r'限额',
              r'insufficient.*balance', r'not enough.*credit'
          ],
          AIErrorType.INVALID_API_KEY: [
              r'invalid.*api', r'unauthorized', r'认证失败',
              r'api.*key.*错误', r'密钥.*无效'
          ],
          AIErrorType.RATE_LIMIT_EXCEEDED: [
              r'rate.*limit', r'too.*many.*request', r'频率限制',
              r'请求.*频繁'
          ],
      }
      
      for error_type, patterns in ERROR_PATTERNS.items():
          for pattern in patterns:
              if re.search(pattern, error_str):
                  return error_type
      
      # 语义增强
      if any(word in error_str for word in ['money', 'pay', 'billing']):
          return AIErrorType.INSUFFICIENT_QUOTA
      
      return AIErrorType.UNKNOWN_ERROR
  ```

- [ ] 4. 测试：使用各种错误信息，确认正确识别

---

## 🔴 P0-004: 实现预写日志（WAL）

**文件：** `backend_python/wechat_backend/nxm_execution_engine.py`

### 步骤：
- [ ] 1. 在文件顶部添加导入：
  ```python
  import pickle
  import os
  import glob
  ```

- [ ] 2. 添加 WAL 常量（在文件顶部）：
  ```python
  WAL_DIR = '/tmp/nxm_wal'
  os.makedirs(WAL_DIR, exist_ok=True)
  ```

- [ ] 3. 添加 WAL 函数（在文件顶部）：
  ```python
  def write_wal(execution_id: str, results: List[Dict], completed: int, total: int):
      """预写日志"""
      try:
          wal_path = os.path.join(WAL_DIR, f'nxm_wal_{execution_id}.pkl')
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
      """读取 WAL"""
      try:
          wal_path = os.path.join(WAL_DIR, f'nxm_wal_{execution_id}.pkl')
          if os.path.exists(wal_path):
              with open(wal_path, 'rb') as f:
                  return pickle.load(f)
      except Exception as e:
          api_logger.error(f"WAL 读取失败：{e}")
      return None

  def cleanup_expired_wal(max_age_hours: int = 24):
      """清理过期 WAL"""
      try:
          now = time.time()
          wal_files = glob.glob(os.path.join(WAL_DIR, 'nxm_wal_*.pkl'))
          for wal_file in wal_files:
              try:
                  mtime = os.path.getmtime(wal_file)
                  if (now - mtime) > (max_age_hours * 3600):
                      os.remove(wal_file)
                      api_logger.info(f"清理过期 WAL: {wal_file}")
              except Exception:
                  pass
      except Exception as e:
          api_logger.error(f"WAL 清理失败：{e}")
  ```

- [ ] 4. 在执行循环中调用 WAL（在第 178 行附近，每次 AI 调用成功后）：
  ```python
  # 在 results.append(result) 之后添加：
  write_wal(execution_id, results, completed, total_tasks)
  ```

- [ ] 5. 在服务启动时调用清理（在合适的初始化位置）：
  ```python
  cleanup_expired_wal()
  ```

- [ ] 6. 测试：服务重启后检查是否能从 WAL 恢复

---

## 🔴 P0-005: 修复前端数据加载竞态

**文件：** `pages/results/results.js`

### 步骤：
- [ ] 1. 找到 `onLoad` 方法（约第 105 行）

- [ ] 2. 替换整个 onLoad 方法：
  ```javascript
  onLoad: async function(options) {
    const executionId = decodeURIComponent(options.executionId || '');
    
    // 显示加载中状态
    this.setData({ 
      isLoading: true, 
      showLoadingSpinner: true,
      showErrorBanner: false 
    });
    
    // 并行加载所有数据源
    const [cachedResult, storageResult, apiResult] = await Promise.allSettled([
      this.loadFromCache(),
      this.loadFromStorage(executionId),
      this.loadFromApi(executionId)
    ]);
    
    // 选择最优结果（优先级：API > Storage > Cache）
    let bestResult = null;
    let loadError = null;
    
    if (apiResult.status === 'fulfilled' && apiResult.value && apiResult.value.results) {
      bestResult = apiResult.value;
      console.log('✅ 从 API 加载成功');
    } else if (storageResult.status === 'fulfilled' && storageResult.value) {
      bestResult = storageResult.value;
      console.log('✅ 从 Storage 加载成功');
      loadError = apiResult.reason?.message || 'API 加载失败';
    } else if (cachedResult.status === 'fulfilled' && cachedResult.value) {
      bestResult = cachedResult.value;
      console.log('✅ 从缓存加载成功');
      loadError = '使用缓存数据';
    }
    
    // 停止加载动画
    this.setData({ 
      isLoading: false,
      showLoadingSpinner: false 
    });
    
    // 如果有结果，展示数据
    if (bestResult) {
      this.processAndDisplayResults(bestResult);
      
      // 如果有降级提示，显示
      if (loadError) {
        this.setData({
          showFallbackBanner: true,
          fallbackMessage: loadError
        });
      }
    } else {
      // 所有数据源都失败
      this.setData({
        showErrorBanner: true,
        errorMessage: '加载诊断结果失败，请重试'
      });
    }
  },
  
  // 添加辅助方法
  loadFromCache: function() {
    return new Promise((resolve) => {
      try {
        const cached = wx.getStorageSync('last_diagnostic_results');
        resolve(cached || null);
      } catch (e) {
        resolve(null);
      }
    });
  },
  
  loadFromStorage: function(executionId) {
    return new Promise((resolve) => {
      try {
        const { loadDiagnosisResult } = require('../../utils/storage-manager');
        const result = loadDiagnosisResult(executionId);
        resolve(result || null);
      } catch (e) {
        resolve(null);
      }
    });
  },
  
  loadFromApi: function(executionId) {
    return new Promise((resolve, reject) => {
      try {
        const { getTaskStatusApi } = require('../../api/home');
        getTaskStatusApi(executionId)
          .then(res => resolve(res))
          .catch(err => reject(err));
      } catch (e) {
        reject(e);
      }
    });
  },
  
  processAndDisplayResults: function(resultData) {
    // 原有的结果处理逻辑
    // ...
  }
  ```

- [ ] 3. 测试：慢网络环境下确认能正确展示结果

---

## ✅ 修复后验证

### 测试用例：
- [ ] 正常诊断流程（所有 AI 平台成功）
- [ ] 部分 AI 平台配额用尽
- [ ] 所有 AI 平台失败
- [ ] 网络波动导致认证错误
- [ ] 服务重启后恢复进度
- [ ] 前端加载结果页

### 验收标准：
- [ ] 诊断报告产出率 > 99%
- [ ] 任何错误都不中断诊断流程
- [ ] 配额用尽时有明确标记
- [ ] 用户无需重新诊断

---

## ✅ 修复记录

| 问题编号 | 修复人 | 修复时间 | 验证结果 |
|---------|-------|---------|---------|
| P0-001 | 首席架构师 | 2026-02-26 | ✅ 语法检查通过 |
| P0-002 | 首席架构师 | 2026-02-26 | ✅ 语法检查通过 |
| P0-003 | 首席架构师 | 2026-02-26 | ✅ 语法检查通过 |
| P0-004 | 首席架构师 | 2026-02-26 | ✅ 语法检查通过 |
| P0-005 | 首席架构师 | 2026-02-26 | ✅ 语法检查通过 |

---

**备注：** 每完成一个修复，立即提交代码并通知测试工程师验证。
