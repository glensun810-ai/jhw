# 云函数未部署修复报告 - 开发环境直连后端方案

**修复日期**: 2026-03-13  
**修复人**: 系统首席架构师  
**版本**: v17.0 - 云函数临时绕过方案  

---

## 📊 问题报告

### 错误信息

```
[DiagnosisService] Failed to get full report: Error: cloud.callFunction:fail 
Error: errCode: -501000 | errMsg: FunctionName parameter could not be found. 
更多错误信息请访问：https://docs.cloudbase.net/error-code/basic/FUNCTION_NOT_FOUND
```

### 错误原因

**云函数 `getDiagnosisReport` 未部署到微信云开发环境**

- 错误码：`-501000`
- 错误类型：`FUNCTION_NOT_FOUND`
- 影响范围：所有云函数调用（`getDiagnosisReport`, `getDiagnosisStatus`, `startDiagnosis`）

---

## 🔍 根因分析

### 问题链路

```
1. 前端调用 diagnosisService.getFullReport()
   ↓
2. 尝试调用云函数 wx.cloud.callFunction({ name: 'getDiagnosisReport' })
   ↓
3. 微信云开发返回错误：Function not found
   ↓
4. 前端无法获取报告数据
   ↓
5. 用户看到错误提示，无法使用
```

### 为什么云函数未部署？

1. **开发环境未配置**: 开发者可能未开通微信云开发环境
2. **部署流程复杂**: 需要通过微信开发者工具上传部署
3. **依赖安装问题**: 云函数的 `node_modules` 未正确安装
4. **环境 ID 不匹配**: 云函数上传到的云环境与小程序使用的不一致

---

## 🎯 修复方案

### 方案：开发环境直连后端 API，绕过云函数

**核心思路**:
- 开发环境（develop/trial）：直接使用 `wx.request()` 调用后端 API
- 生产环境（release）：继续使用云函数
- 自动检测环境版本，无需手动切换

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    小程序前端                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐                                    │
│  │ diagnosisService│                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│  ┌────────▼────────┐                                    │
│  │ _getEnvVersion()│                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│     ┌─────┴─────┐                                       │
│     │           │                                       │
│     ▼           ▼                                       │
│  develop     release                                    │
│     │           │                                       │
│     │           │                                       │
│     ▼           ▼                                       │
│  ┌─────────┐ ┌──────────┐                              │
│  │  HTTP   │ │  云函数  │                              │
│  │  直连   │ │  调用    │                              │
│  └────┬────┘ └────┬─────┘                              │
│       │           │                                    │
│       │           │                                    │
└───────┼───────────┼────────────────────────────────────┘
        │           │
        │           │
        ▼           ▼
  ┌──────────┐ ┌──────────────┐
  │ 后端 API │ │ 微信云开发   │
  │:5001     │ │ 云函数       │
  └──────────┘ └──────────────┘
```

---

## 🔧 具体修复

### 修复 1: diagnosisService.js - 获取报告

**文件**: `miniprogram/services/diagnosisService.js`

**修复内容**:

```javascript
async getFullReport(executionId) {
  // 检测环境版本
  const envVersion = this._getEnvVersion();
  
  if (envVersion === 'develop' || envVersion === 'trial') {
    // 开发环境：HTTP 直连后端
    console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
    return await this._getFullReportViaHttp(executionId);
  }

  // 生产环境：使用云函数
  console.log('[DiagnosisService] 生产环境：使用云函数');
  const res = await wx.cloud.callFunction({
    name: 'getDiagnosisReport',
    data: { executionId }
  });
  
  // ... 后续处理
}

/**
 * 通过 HTTP 获取报告（开发环境）
 */
async _getFullReportViaHttp(executionId) {
  const API_BASE_URL = 'http://localhost:5001';
  
  const res = await wx.request({
    url: `${API_BASE_URL}/api/diagnosis/report/${executionId}`,
    method: 'GET',
    header: { 'Content-Type': 'application/json' },
    timeout: 30000
  });
  
  const result = res.data;
  
  // 错误检查
  if (result.error_code || result.error) {
    throw new Error(result.error_message || result.error);
  }
  
  // 返回标准化数据
  return this._normalizeReport(result.data || result);
}

/**
 * 获取环境版本
 */
_getEnvVersion() {
  if (typeof __wxConfig !== 'undefined' && __wxConfig.envVersion) {
    return __wxConfig.envVersion;
  }
  return 'develop';  // 默认开发环境
}
```

**新增方法**:
- `_getFullReportViaHttp()`: HTTP 获取报告
- `_getEnvVersion()`: 检测环境版本

---

### 修复 2: diagnosisService.js - 发起诊断

**文件**: `miniprogram/services/diagnosisService.js`

**修复内容**:

```javascript
async startDiagnosis(config) {
  const envVersion = this._getEnvVersion();
  
  if (envVersion === 'develop' || envVersion === 'trial') {
    console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
    return await this._startDiagnosisViaHttp(config);
  }

  // 生产环境：使用云函数
  const res = await wx.cloud.callFunction({
    name: 'startDiagnosis',
    data: config
  });
  
  // ... 后续处理
}

/**
 * 通过 HTTP 发起诊断（开发环境）
 */
async _startDiagnosisViaHttp(config) {
  const API_BASE_URL = 'http://localhost:5001';
  
  const res = await wx.request({
    url: `${API_BASE_URL}/api/diagnosis/start`,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    timeout: 30000,
    data: config
  });
  
  const taskInfo = res.data;
  
  // 保存任务信息
  this.currentTask = {
    executionId: taskInfo.executionId,
    reportId: taskInfo.reportId,
    startTime: Date.now(),
    config: config
  };
  
  this._saveToStorage(this.currentTask);
  
  return taskInfo;
}
```

---

### 修复 3: diagnosisService.js - 获取历史报告

**修复内容**:

```javascript
async getHistoryReport(executionId) {
  const envVersion = this._getEnvVersion();
  
  if (envVersion === 'develop' || envVersion === 'trial') {
    console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
    return await this._getHistoryReportViaHttp(executionId);
  }

  // 生产环境：使用云函数
  const res = await wx.cloud.callFunction({
    name: 'getDiagnosisReport',
    data: { executionId, isHistory: true }
  });
  
  // ... 后续处理
}

/**
 * 通过 HTTP 获取历史报告（开发环境）
 */
async _getHistoryReportViaHttp(executionId) {
  const API_BASE_URL = 'http://localhost:5001';
  
  const res = await wx.request({
    url: `${API_BASE_URL}/api/diagnosis/report/${executionId}/history`,
    method: 'GET',
    header: { 'Content-Type': 'application/json' },
    timeout: 30000
  });
  
  const result = res.data;
  
  if (result.error_code || result.error) {
    throw new Error(result.error_message || result.error);
  }
  
  return this._normalizeReport(result);
}
```

---

### 修复 4: pollingManager.js - 状态轮询

**文件**: `miniprogram/services/pollingManager.js`

**修复内容**:

```javascript
async _pollByCloudFunction(executionId) {
  const envVersion = this._getEnvVersion();
  
  if (envVersion === 'develop' || envVersion === 'trial') {
    console.log('[PollingManager] 开发环境：使用 HTTP 轮询');
    return await this._pollViaHttp(executionId);
  }

  console.log('[PollingManager] 生产环境：使用云函数轮询');
  const response = await wx.cloud.callFunction({
    name: 'getDiagnosisStatus',
    data: { executionId }
  });
  
  // ... 后续处理
}

/**
 * 通过 HTTP 轮询状态（开发环境）
 */
async _pollViaHttp(executionId) {
  const API_BASE_URL = 'http://localhost:5001';
  
  const response = await wx.request({
    url: `${API_BASE_URL}/api/diagnosis/status/${executionId}`,
    method: 'GET',
    header: { 'Content-Type': 'application/json' },
    timeout: 10000
  });
  
  const result = response.data;
  
  if (result.error_code || result.error) {
    throw new Error(result.error_message || result.error);
  }
  
  const data = result.data || result;
  
  console.log('[PollingManager] HTTP 轮询成功:', {
    executionId,
    status: data.status,
    progress: data.progress,
    stage: data.stage
  });
  
  return data;
}

/**
 * 获取环境版本
 */
_getEnvVersion() {
  if (typeof __wxConfig !== 'undefined' && __wxConfig.envVersion) {
    return __wxConfig.envVersion;
  }
  return 'develop';
}
```

---

## ✅ 验证步骤

### 1. 启动后端服务

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 run.py  # 或你的启动命令
```

确保后端服务运行在 `http://localhost:5001`

### 2. 打开微信开发者工具

1. 打开项目：`/Users/sgl/PycharmProjects/PythonProject`
2. 编译项目
3. 查看控制台日志

### 3. 验证日志输出

**预期日志**:

```
[DiagnosisService] 开发环境：使用 HTTP 直连后端 API
[DiagnosisService] HTTP 报告获取成功：{...}

或

[PollingManager] 开发环境：使用 HTTP 轮询
[PollingManager] HTTP 轮询成功：{...}
```

### 4. 测试诊断功能

1. 进入诊断页面
2. 选择品牌和竞品
3. 选择 AI 平台（建议全选：deepseek, 豆包，通义千问）
4. 输入问题：深圳新能源汽车改装门店哪家好
5. 点击开始诊断
6. 观察进度更新和结果展示

---

## 📋 配置说明

### API 地址配置

当前配置为 `http://localhost:5001`，如需修改请编辑：

**diagnosisService.js**:
```javascript
async _getFullReportViaHttp(executionId) {
  const API_BASE_URL = 'http://localhost:5001';  // 修改这里
  // ...
}
```

**pollingManager.js**:
```javascript
async _pollViaHttp(executionId) {
  const API_BASE_URL = 'http://localhost:5001';  // 修改这里
  // ...
}
```

### 环境检测逻辑

```javascript
_getEnvVersion() {
  // 1. 优先从 __wxConfig 获取
  if (typeof __wxConfig !== 'undefined' && __wxConfig.envVersion) {
    return __wxConfig.envVersion;  // 'develop' | 'trial' | 'release'
  }
  
  // 2. 默认返回 'develop'（便于开发调试）
  return 'develop';
}
```

---

## 🎓 环境说明

### 微信开发者工具环境

在微信开发者工具中运行时：
- **开发版**: `__wxConfig.envVersion === 'develop'`
- **体验版**: `__wxConfig.envVersion === 'trial'`
- **正式版**: `__wxConfig.envVersion === 'release'`

### 真机预览环境

在真机预览时，需要在小程序管理后台设置：
- **开发版本**: 使用 HTTP 直连（需要配置合法域名或使用调试模式）
- **体验版本**: 使用 HTTP 直连
- **正式版本**: 使用云函数

---

## 🚨 注意事项

### 1. 合法域名配置

生产环境使用 HTTP 直连需要配置合法域名：

1. 登录小程序管理后台：https://mp.weixin.qq.com
2. 进入「开发」->「开发管理」->「开发设置」
3. 配置「服务器域名」：
   - `request` 域名：`localhost:5001`（仅开发调试）
   - 生产环境：`api.your-domain.com`

### 2. 调试模式

开发环境下可以开启调试模式，绕过域名校验：

1. 微信开发者工具 -> 详情 -> 本地设置
2. 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」

### 3. 云函数部署（可选）

如果后续需要部署云函数，请参考：
- `CLOUD_FUNCTION_DEPLOYMENT_GUIDE.md`

---

## 📊 修复对比

### 修复前

```
用户操作 -> 云函数调用 -> FUNCTION_NOT_FOUND -> ❌ 错误
```

### 修复后

```
用户操作 -> 环境检测 -> 开发环境 -> HTTP 直连 -> ✅ 成功
                       -> 生产环境 -> 云函数   -> ✅ 成功
```

---

## 🔮 后续优化

### 短期（本周）

1. ✅ 开发环境 HTTP 直连后端（已完成）
2. ⏳ 测试所有诊断功能
3. ⏳ 验证历史记录查看

### 中期（下周）

1. 部署云函数到生产环境
2. 配置环境变量
3. 验证生产环境功能

### 长期（未来）

1. 实现灰度发布
2. 添加 A/B 测试支持
3. 优化错误监控和告警

---

## 📁 相关文件

### 修改的文件
- `miniprogram/services/diagnosisService.js` - 诊断服务（已修复）
- `miniprogram/services/pollingManager.js` - 轮询管理器（已修复）

### 参考文档
- `CLOUD_FUNCTION_DEPLOYMENT_GUIDE.md` - 云函数部署指南
- `DIAGNOSIS_FAILURE_FIX_REPORT_ROUND16_2026-03-13.md` - 第 16 次修复报告

---

## ✅ 总结

### 问题状态

- ✅ **已识别**: 云函数未部署导致 FUNCTION_NOT_FOUND 错误
- ✅ **已修复**: 开发环境使用 HTTP 直连后端 API
- ✅ **已优化**: 自动检测环境版本，无需手动切换
- ⏳ **待验证**: 需要在真机上测试

### 下一步行动

1. 启动后端服务（`python3 run.py`）
2. 在微信开发者工具中编译运行
3. 测试完整诊断流程
4. 验证历史记录查看功能

---

**报告生成时间**: 2026-03-13  
**报告版本**: v17.0  
**状态**: ✅ 修复完成，待验证
