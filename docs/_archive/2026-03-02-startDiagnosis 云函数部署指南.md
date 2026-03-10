# startDiagnosis 云函数部署指南

## 概述

本文档详细说明如何将 `startDiagnosis` 云函数部署到微信云开发环境，确保前端请求能够正确转发到后端 API。

## 部署前准备

### 1. 确认环境配置

#### 开发环境
- 本地运行后端 API：`http://localhost:5001`
- 微信开发者工具已安装并登录
- 小程序 AppID 已配置：`wxfd3b695920a78e1b`

#### 生产环境
- 后端 API 已部署到生产服务器
- 域名已备案并配置 HTTPS
- 云开发环境已开通

### 2. 配置生产环境 API 地址

在部署到生产环境前，需要配置正确的后端 API 地址。

#### 方法一：在云函数中直接配置（推荐）

编辑 `miniprogram/cloudfunctions/startDiagnosis/index.js`：

```javascript
// 将此行
const API_BASE_URL_PROD = process.env.API_BASE_URL || 'https://your-domain.com';

// 修改为实际域名，例如：
const API_BASE_URL_PROD = process.env.API_BASE_URL || 'https://api.jinshuai.wang';
```

#### 方法二：使用云函数环境变量

1. 登录微信云开发控制台
2. 进入「云函数」页面
3. 点击 `startDiagnosis` 云函数
4. 在「配置」标签页中添加环境变量：
   - 变量名：`API_BASE_URL`
   - 值：`https://api.jinshuai.wang`

### 3. 检查依赖

确保所有依赖已安装：

```bash
cd miniprogram/cloudfunctions/startDiagnosis
npm install
```

依赖清单：
- `wx-server-sdk`: ~2.6.3（微信云函数 SDK）
- `axios`: ^1.13.6（HTTP 请求库）

## 部署步骤

### 步骤 1：在微信开发者工具中打开项目

1. 启动微信开发者工具
2. 导入项目：`/Users/sgl/PycharmProjects/PythonProject`
3. 确认项目配置正确（AppID: `wxfd3b695920a78e1b`）

### 步骤 2：上传并部署云函数

#### 方式一：使用微信开发者工具 GUI（推荐）

1. 在左侧文件树中找到 `miniprogram/cloudfunctions/startDiagnosis` 文件夹
2. 右键点击 `startDiagnosis` 文件夹
3. 选择「上传并部署：云端安装依赖」
4. 等待上传完成（约 10-30 秒）
5. 查看上传日志，确认无错误

#### 方式二：使用命令行工具

```bash
# 安装微信云开发 CLI 工具（如果未安装）
npm install -g @cloudbase/cli

# 登录微信云开发
tcb login

# 部署云函数
cd miniprogram/cloudfunctions/startDiagnosis
tcb fn deploy startDiagnosis --install-dependency
```

### 步骤 3：验证部署

#### 在微信开发者工具控制台测试

打开微信开发者工具控制台，执行：

```javascript
// 测试调用云函数
wx.cloud.callFunction({
  name: 'startDiagnosis',
  data: {
    brand_list: ['华为', '小米', 'OPPO'],
    selectedModels: [
      { name: 'doubao', checked: true },
      { name: 'deepseek', checked: true }
    ],
    custom_question: '请分析华为的品牌优势和市场定位？',
    userLevel: 'Free'
  }
}).then(res => {
  console.log('调用成功:', res);
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

#### 预期响应

成功响应示例：

```javascript
{
  result: {
    success: true,
    execution_id: "550e8400-e29b-41d4-a716-446655440000",
    report_id: 12345,
    message: "诊断任务已启动",
    elapsedTime: 1234,
    status: "success"
  }
}
```

失败响应示例：

```javascript
{
  result: {
    success: false,
    error: "后端 API 错误 (500): {...}",
    errorCode: "BACKEND_ERROR",
    statusCode: 500
  }
}
```

### 步骤 4：查看云函数日志

1. 登录微信云开发控制台：https://console.cloud.tencent.com/cloud
2. 进入「云函数」->「云函数列表」
3. 点击 `startDiagnosis` 云函数
4. 查看「日志」标签页
5. 筛选最近的调用记录，检查是否有错误

常见日志内容：

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

## 前端集成

### 在小程序中调用云函数

#### 方式一：直接调用

```javascript
// 在页面 JS 中
Page({
  async startDiagnosis() {
    try {
      const res = await wx.cloud.callFunction({
        name: 'startDiagnosis',
        data: {
          brand_list: this.data.brandList,
          selectedModels: this.data.selectedModels,
          custom_question: this.data.question,
          userLevel: this.data.userLevel
        }
      });

      if (res.result && res.result.success) {
        const executionId = res.result.execution_id;
        console.log('诊断启动成功，执行 ID:', executionId);

        // 跳转到诊断进度页面
        wx.navigateTo({
          url: `/pages/diagnosis/diagnosis?executionId=${executionId}`
        });
      } else {
        wx.showToast({
          title: res.result?.error || '启动失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('云函数调用失败:', error);
      wx.showToast({
        title: '网络错误，请稍后重试',
        icon: 'none'
      });
    }
  }
});
```

#### 方式二：使用 diagnosisService 封装

```javascript
// services/diagnosisService.js
import diagnosisService from '../../services/diagnosisService';

// 在页面中调用
async handleStartDiagnosis() {
  try {
    const taskInfo = await diagnosisService.startDiagnosis({
      brand_list: this.data.brandList,
      selectedModels: this.data.selectedModels,
      custom_question: this.data.question
    });

    console.log('任务已启动:', taskInfo.execution_id);

    // 开始轮询进度
    diagnosisService.startPolling({
      onStatus: (status) => {
        this.setData({ progress: status.progress, stage: status.stage });
      },
      onComplete: (result) => {
        console.log('诊断完成:', result);
        // 跳转到报告页面
        wx.navigateTo({
          url: `/pages/report/report?id=${result.report_id}`
        });
      },
      onError: (error) => {
        console.error('错误:', error);
        wx.showToast({
          title: error.message,
          icon: 'none'
        });
      }
    });
  } catch (error) {
    console.error('启动失败:', error);
    wx.showToast({
      title: error.message,
      icon: 'none'
    });
  }
}
```

## 故障排查

### 问题 1：云函数调用超时

**现象：**
```
Error: cloud.callFunction:timeout
```

**可能原因：**
- 后端 API 响应慢（超过 30 秒）
- 网络连接问题
- 云函数超时时间设置过短

**解决方案：**
1. 增加云函数超时时间（在 `package.json` 中）：
   ```json
   {
     "cloudConfig": {
       "timeout": 60
     }
   }
   ```
2. 检查后端 API 性能日志
3. 配置 VPC 内网访问（如果后端在云服务器）

### 问题 2：后端 API 返回 401/403

**现象：**
```
[startDiagnosis] 后端错误响应：401 {"error": "Unauthorized"}
```

**可能原因：**
- 后端 API 需要认证但未提供
- IP 白名单限制
- CORS 配置问题

**解决方案：**
1. 在后端 API 中添加云函数 IP 白名单
2. 如果 API 需要认证，在请求头中添加 Token：
   ```javascript
   const response = await axios.post(
     `${API_BASE_URL}/api/perform-brand-test`,
     normalizedParams,
     {
       timeout: API_TIMEOUT,
       headers: {
         'Content-Type': 'application/json',
         'Authorization': `Bearer ${process.env.API_TOKEN}`
       }
     }
   );
   ```

### 问题 3：云函数返回 NO_RESPONSE

**现象：**
```
{
  success: false,
  error: '未收到后端 API 响应，请检查网络连接或后端服务状态',
  errorCode: 'NO_RESPONSE'
}
```

**可能原因：**
- 后端 API 未启动
- 域名无法访问（DNS 问题）
- 防火墙阻止请求

**解决方案：**
1. 检查后端服务是否运行：
   ```bash
   curl -I https://api.jinshuai.wang
   ```
2. 检查域名 DNS 解析
3. 检查云服务器安全组配置（确保 5001 端口开放）
4. 在云函数日志中查看详细错误信息

### 问题 4：参数验证失败

**现象：**
```
{
  success: false,
  error: 'brand_list 必须是非空数组',
  errorCode: 'INVALID_PARAMS'
}
```

**解决方案：**
1. 检查前端传递的参数格式
2. 在小程序端进行预验证
3. 查看云函数日志中的参数详情

### 问题 5：CORS 错误（开发环境）

**现象：**
```
Access to XMLHttpRequest at 'http://localhost:5001' from origin 'https://servicewechat.com' has been blocked by CORS policy
```

**解决方案：**
1. 在后端 Flask 应用中配置 CORS：
   ```python
   from flask_cors import CORS
   app = Flask(__name__)
   CORS(app, resources={r"/api/*": {"origins": "*"}})
   ```
2. 或者在开发时使用微信开发者工具的「不校验合法域名」选项

## 性能优化

### 1. 使用 VPC 内网访问

如果后端 API 部署在腾讯云 CVM，建议配置 VPC 内网访问：

1. 在云开发控制台配置 VPC
2. 修改 API 地址为内网地址
3. 降低网络延迟，提高稳定性

### 2. 增加云函数内存

如果诊断任务启动较慢，可以增加云函数内存：

```json
{
  "cloudConfig": {
    "memory": 1024  // 从 512MB 增加到 1024MB
  }
}
```

### 3. 实现请求重试

在云函数中添加重试逻辑：

```javascript
const axiosRetry = require('axios-retry');

axiosRetry(axios, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay
});
```

## 监控与告警

### 1. 启用云函数监控

在云开发控制台：
1. 进入「云函数」->「startDiagnosis」
2. 查看「监控」标签页
3. 关注指标：
   - 调用次数
   - 错误次数
   - 平均耗时
   - 超时次数

### 2. 配置告警

1. 在云开发控制台配置告警策略
2. 设置阈值：
   - 错误率 > 5%
   - 平均耗时 > 5 秒
   - 超时率 > 1%
3. 配置通知方式（邮件、短信、微信）

### 3. 日志分析

定期查看云函数日志，分析常见问题：

```bash
# 在云开发控制台使用日志查询
# 查询错误日志
[startDiagnosis] ========== 诊断启动失败 ==========

# 查询慢请求
[startDiagnosis] 后端 API 响应时间：[5-9]\d{3} ms
```

## 版本管理

### 1. 云函数版本

每次上传会生成新版本，可以在云开发控制台：
1. 查看历史版本
2. 回滚到旧版本
3. 比较版本差异

### 2. 灰度发布

对于重要更新，建议灰度发布：

1. 上传新版本
2. 在云开发控制台配置灰度策略（例如 10% 流量）
3. 观察监控和日志
4. 确认无问题后全量发布

## 安全检查清单

部署前确认：

- [ ] 生产环境 API 地址已正确配置
- [ ] 敏感信息（密钥、Token）未硬编码在代码中
- [ ] 已启用 HTTPS
- [ ] 云函数超时时间合理（30-60 秒）
- [ ] 已配置错误处理和日志记录
- [ ] 前端已处理云函数调用失败场景
- [ ] 后端 API 已配置云函数 IP 白名单（如果需要）

## 相关文档

- [微信云开发文档](https://developers.weixin.qq.com/miniprogram/dev/wxcloud/basis/getting-started.html)
- [云函数开发指南](https://developers.weixin.qq.com/miniprogram/dev/wxcloud/guide/functions.html)
- [getDiagnosisStatus 云函数文档](../getDiagnosisStatus/README.md)
- [diagnosisService 使用文档](../../services/diagnosisService.js)

## 更新日志

### v1.0.0 (2026-03-02)
- 初始版本
- 支持开发和生产环境配置
- 完整的参数验证和错误处理
- 详细的日志记录

## 联系支持

如有问题，请联系系统架构组或查看项目文档。
