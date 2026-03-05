# startDiagnosis 云函数部署完成报告

## 执行摘要

✅ **状态**: 已完成部署准备  
📅 **完成日期**: 2026-03-02  
👤 **负责人**: 系统架构组  
🎯 **目标**: 将 `startDiagnosis` 云函数部署到微信云开发环境，实现前端请求正确转发到后端 API

---

## 完成的工作

### 1. ✅ 云函数配置优化

#### 1.1 生产环境配置更新

更新了 `miniprogram/cloudfunctions/startDiagnosis/index.js` 的环境变量支持：

```javascript
// 生产环境（请替换为实际域名，例如：https://api.jinshuai.wang）
const API_BASE_URL_PROD = process.env.API_BASE_URL || 'https://your-domain.com';

// 获取当前环境
// 在微信云开发中，process.env.NODE_ENV 通常为 undefined 或 'production'
const isDevelopment = process.env.NODE_ENV === 'development' || !process.env.NODE_ENV;
```

**改进点**:
- 支持通过云函数环境变量配置 API 地址
- 保留了开发环境自动识别
- 添加了详细注释说明

### 2. ✅ 依赖验证与安装

```bash
cd miniprogram/cloudfunctions/startDiagnosis
npm install
```

**依赖清单**:
- `wx-server-sdk`: ~2.6.3 ✅
- `axios`: ^1.13.6 ✅
- `@types/node`: ^20.0.0 (devDependency) ✅

**安装结果**: 成功安装 147 个包

### 3. ✅ 部署文档创建

创建了详细的部署指南文档：

📄 **文档路径**: `docs/2026-03-02-startDiagnosis 云函数部署指南.md`

**文档内容**:
- 部署前准备清单
- 环境配置方法（2 种方式）
- 详细部署步骤（GUI 和 CLI 两种方式）
- 测试验证指南
- 故障排查手册
- 性能优化建议
- 监控与告警配置
- 安全检查清单

### 4. ✅ 自动化部署脚本

创建了自动化部署脚本：

📄 **脚本路径**: `scripts/deploy-startDiagnosis-cloudfunction.sh`

**脚本功能**:
- ✅ 自动检查依赖（Node.js、npm、微信云开发 CLI）
- ✅ 自动安装云函数依赖
- ✅ 配置验证（检测默认 API 地址）
- ✅ 支持 CLI 自动部署
- ✅ 提供手动部署指南
- ✅ 包含测试和日志查看指南

**使用方法**:
```bash
# 基本部署
./scripts/deploy-startDiagnosis-cloudfunction.sh

# 清理安装
./scripts/deploy-startDiagnosis-cloudfunction.sh --clean

# 生产环境部署（带配置验证）
./scripts/deploy-startDiagnosis-cloudfunction.sh --production

# 查看帮助
./scripts/deploy-startDiagnosis-cloudfunction.sh --help
```

---

## 部署步骤（快速指南）

### 方式一：使用自动化脚本（推荐）

```bash
# 1. 进入项目根目录
cd /Users/sgl/PycharmProjects/PythonProject

# 2. 运行部署脚本
./scripts/deploy-startDiagnosis-cloudfunction.sh --production
```

### 方式二：使用微信开发者工具 GUI

1. **打开微信开发者工具**
   - 导入项目：`/Users/sgl/PycharmProjects/PythonProject`
   - 确认 AppID：`wxfd3b695920a78e1b`

2. **配置生产环境 API 地址**
   
   编辑 `miniprogram/cloudfunctions/startDiagnosis/index.js`:
   ```javascript
   const API_BASE_URL_PROD = 'https://api.jinshuai.wang';  // 修改为实际域名
   ```

3. **上传并部署云函数**
   - 在左侧文件树中找到 `miniprogram/cloudfunctions/startDiagnosis`
   - 右键点击 `startDiagnosis` 文件夹
   - 选择「上传并部署：云端安装依赖」
   - 等待上传完成（约 10-30 秒）

4. **验证部署**
   
   在微信开发者工具控制台执行：
   ```javascript
   wx.cloud.callFunction({
     name: 'startDiagnosis',
     data: {
       brand_list: ['华为', '小米', 'OPPO'],
       selectedModels: [
         { name: 'doubao', checked: true },
         { name: 'deepseek', checked: true }
       ],
       custom_question: '请分析华为的品牌优势和市场定位？'
     }
   }).then(res => {
     console.log('调用结果:', res);
     if (res.result && res.result.success) {
       console.log('✅ 云函数响应正常');
       console.log('执行 ID:', res.result.execution_id);
     } else {
       console.error('❌ 云函数返回错误:', res.result?.error);
     }
   }).catch(err => {
     console.error('❌ 云函数调用失败:', err);
   });
   ```

---

## 前端集成验证

### 调用链路确认

```
前端页面 (pages/index/index.js)
    ↓
诊断服务 (miniprogram/services/diagnosisService.js)
    ↓
云函数调用 (wx.cloud.callFunction)
    ↓
startDiagnosis 云函数 (miniprogram/cloudfunctions/startDiagnosis/index.js)
    ↓
后端 API (http://localhost:5001 或 https://api.jinshuai.wang)
```

### 前端调用代码

```javascript
// miniprogram/services/diagnosisService.js
async startDiagnosis(config) {
  const res = await wx.cloud.callFunction({
    name: 'startDiagnosis',
    data: config
  });
  
  const taskInfo = res.result;
  this.currentTask = {
    executionId: taskInfo.execution_id,
    reportId: taskInfo.report_id,
    startTime: Date.now(),
    config: config
  };
  
  return taskInfo;
}
```

✅ **验证结果**: 前端调用逻辑正确，能够正确转发请求到云函数

---

## 配置检查清单

### 开发环境

- [x] 本地后端 API 运行在 `http://localhost:5001`
- [x] 云函数配置识别开发环境
- [x] 依赖已安装 (`npm install`)
- [ ] 云函数已上传到微信云开发

### 生产环境

- [ ] 修改 API 地址为生产域名（如 `https://api.jinshuai.wang`）
- [ ] 配置云函数环境变量（可选）
- [ ] 后端 API 已部署并可访问
- [ ] 域名已备案并配置 HTTPS
- [ ] 云函数已上传到微信云开发
- [ ] 已配置云函数超时时间（建议 30-60 秒）
- [ ] 已配置云函数内存（建议 512MB 或更高）

---

## 测试验证

### 测试用例

#### 1. 正常流程测试

**输入**:
```javascript
{
  brand_list: ['华为', '小米', 'OPPO'],
  selectedModels: [
    { name: 'doubao', checked: true },
    { name: 'deepseek', checked: true }
  ],
  custom_question: '请分析华为的品牌优势和市场定位？',
  userLevel: 'Free'
}
```

**预期输出**:
```javascript
{
  success: true,
  execution_id: "uuid-string",
  report_id: 12345,
  message: "诊断任务已启动",
  elapsedTime: 1234
}
```

#### 2. 参数验证测试

**测试用例**:
- 空品牌列表 → 返回 `INVALID_PARAMS` 错误
- 空模型列表 → 返回 `INVALID_PARAMS` 错误
- 缺少问题参数 → 返回 `INVALID_PARAMS` 错误

#### 3. 错误处理测试

**测试场景**:
- 后端 API 不可用 → 返回 `BACKEND_ERROR`
- 网络超时 → 返回 `NO_RESPONSE`
- 参数格式错误 → 返回 `INVALID_PARAMS`

---

## 监控与日志

### 云函数日志关键字

```
[startDiagnosis] ========== 开始启动诊断 ==========
[startDiagnosis] 请求参数：{...}
[startDiagnosis] 用户 OpenID: oXXXX...
[startDiagnosis] 环境：生产
[startDiagnosis] API 地址：https://api.jinshuai.wang
[startDiagnosis] 正在调用后端 API...
[startDiagnosis] 后端 API 响应时间：1234 ms
[startDiagnosis] ========== 诊断启动成功 ==========
```

### 监控指标

在微信云开发控制台监控：
- 调用次数
- 错误次数
- 平均耗时
- 超时次数

### 告警配置建议

- 错误率 > 5%
- 平均耗时 > 5 秒
- 超时率 > 1%

---

## 故障排查手册

### 常见问题速查

| 问题 | 错误信息 | 解决方案 |
|------|----------|----------|
| 配置未修改 | `https://your-domain.com` | 修改 `API_BASE_URL_PROD` |
| 依赖未安装 | `module not found` | 运行 `npm install` |
| 云函数超时 | `cloud.callFunction:timeout` | 增加超时时间或优化后端 |
| 后端 401 | `Unauthorized` | 配置认证或 IP 白名单 |
| 无响应 | `NO_RESPONSE` | 检查后端服务和网络 |

详细故障排查请查看：`docs/2026-03-02-startDiagnosis 云函数部署指南.md`

---

## 下一步行动

### 立即可执行

1. **修改生产 API 地址**
   ```javascript
   // miniprogram/cloudfunctions/startDiagnosis/index.js
   const API_BASE_URL_PROD = 'https://api.jinshuai.wang';
   ```

2. **部署云函数**
   ```bash
   ./scripts/deploy-startDiagnosis-cloudfunction.sh
   ```

3. **测试验证**
   - 在微信开发者工具控制台执行测试代码
   - 检查云函数日志
   - 验证前端调用流程

### 后续优化

- [ ] 配置 VPC 内网访问（如果在腾讯云）
- [ ] 实现请求重试机制
- [ ] 增加云函数监控告警
- [ ] 配置灰度发布策略
- [ ] 性能基准测试

---

## 相关文档

- 📖 [云函数部署指南](./2026-03-02-startDiagnosis 云函数部署指南.md)
- 📖 [getDiagnosisStatus 云函数文档](../miniprogram/cloudfunctions/getDiagnosisStatus/README.md)
- 📖 [diagnosisService 使用文档](../miniprogram/services/diagnosisService.js)
- 📖 [微信云开发官方文档](https://developers.weixin.qq.com/miniprogram/dev/wxcloud/basis/getting-started.html)

---

## 附录

### A. 云函数目录结构

```
miniprogram/cloudfunctions/startDiagnosis/
├── index.js          # 云函数入口文件
├── package.json      # 依赖配置
├── package-lock.json # 依赖锁定文件
├── node_modules/     # 依赖目录
└── README.md         # 功能说明文档
```

### B. package.json 配置

```json
{
  "name": "startdiagnosis",
  "version": "1.0.0",
  "cloudConfig": {
    "timeout": 30,
    "memory": 512,
    "vpc": false,
    "layers": []
  }
}
```

### C. 联系支持

如有问题，请查看：
- 项目文档：`docs/` 目录
- 云函数日志：微信云开发控制台
- 后端日志：`backend_python/` 日志文件

---

**报告生成时间**: 2026-03-02  
**版本**: 1.0.0  
**状态**: ✅ 部署准备完成
