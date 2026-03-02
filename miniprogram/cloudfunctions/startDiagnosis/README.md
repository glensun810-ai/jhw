# startDiagnosis 云函数

启动品牌诊断任务的云函数入口。

## 功能说明

- 接收前端诊断请求参数
- 调用后端 API 启动诊断任务
- 返回执行 ID 给前端用于轮询进度

## 目录结构

```
startDiagnosis/
├── index.js          # 云函数入口文件
├── package.json      # 依赖配置
└── README.md         # 本文档
```

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| brand_list | Array<string> | 是 | 品牌列表，第一个为主品牌，其余为竞品 |
| selectedModels | Array<Object> | 是 | 选中的 AI 模型列表 |
| custom_question | string | 是 | 自定义问题（与 customQuestions 二选一） |
| customQuestions | Array<string> | 否 | 自定义问题列表（与 custom_question 二选一） |
| userOpenid | string | 否 | 用户 OpenID（默认从云函数上下文获取） |
| userLevel | string | 否 | 用户等级，默认 'Free' |

### selectedModels 格式

```javascript
[
  { name: 'doubao', checked: true },
  { name: 'deepseek', checked: true },
  { name: 'qwen', checked: false }
]
```

## 返回结果

### 成功响应

```javascript
{
  success: true,
  execution_id: "uuid-string",  // 用于轮询进度
  report_id: 12345,              // 报告 ID（可选）
  message: "诊断任务已启动",
  elapsedTime: 1234,             // 耗时（毫秒）
  status: "success"
}
```

### 失败响应

```javascript
{
  success: false,
  error: "错误描述",
  errorCode: "ERROR_CODE",
  statusCode: 500        // 可选，HTTP 状态码
}
```

## 使用示例

### 小程序端调用

```javascript
// 在小程序页面中
wx.cloud.callFunction({
  name: 'startDiagnosis',
  data: {
    brand_list: ['华为', '小米', 'OPPO'],
    selectedModels: [
      { name: 'doubao', checked: true },
      { name: 'deepseek', checked: true }
    ],
    custom_question: '请分析华为的品牌优势和市场定位？',
    userLevel: 'Premium'
  }
}).then(res => {
  if (res.result.success) {
    console.log('诊断启动成功:', res.result.execution_id);
    
    // 使用 execution_id 轮询进度
    const executionId = res.result.execution_id;
    // 跳转到诊断进度页面
    wx.navigateTo({
      url: `/pages/diagnosis/diagnosis?executionId=${executionId}`
    });
  } else {
    console.error('诊断启动失败:', res.result.error);
    wx.showToast({
      title: res.result.error,
      icon: 'none'
    });
  }
}).catch(err => {
  console.error('云函数调用失败:', err);
  wx.showToast({
    title: '网络错误，请稍后重试',
    icon: 'none'
  });
});
```

### 配合 diagnosisService 使用

```javascript
import diagnosisService from '../../services/diagnosisService';

// 使用封装的服务
try {
  const taskInfo = await diagnosisService.startDiagnosis({
    brand_list: ['华为', '小米'],
    selectedModels: [{ name: 'doubao', checked: true }],
    custom_question: '请分析华为的品牌优势'
  });
  
  console.log('任务已启动:', taskInfo.execution_id);
  
  // 开始轮询进度
  diagnosisService.startPolling({
    onStatus: (status) => {
      console.log('进度更新:', status);
    },
    onComplete: (result) => {
      console.log('诊断完成:', result);
    },
    onError: (error) => {
      console.error('错误:', error);
    }
  });
} catch (error) {
  console.error('启动失败:', error);
}
```

## 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| INVALID_PARAMS | 参数验证失败 | 检查请求参数格式和内容 |
| BACKEND_ERROR | 后端 API 错误 | 检查后端服务状态和日志 |
| NO_RESPONSE | 未收到后端响应 | 检查网络连接和 API 地址配置 |
| UNKNOWN_ERROR | 未知错误 | 查看详细错误日志 |

## 配置说明

### API 地址配置

在 `index.js` 中修改 API 地址：

```javascript
// 开发环境
const API_BASE_URL_DEV = 'http://localhost:5001';

// 生产环境（请替换为实际域名）
const API_BASE_URL_PROD = 'https://your-domain.com';
```

### 超时配置

```javascript
const API_TIMEOUT = 30000; // 30 秒
```

### 云函数资源配置

在 `package.json` 中配置：

```json
{
  "cloudConfig": {
    "timeout": 30,    // 超时时间（秒）
    "memory": 512,    // 内存（MB）
    "vpc": false,
    "layers": []
  }
}
```

## 部署说明

### 1. 安装依赖

```bash
cd miniprogram/cloudfunctions/startDiagnosis
npm install
```

### 2. 上传云函数

在微信开发者工具中：
1. 右键点击 `startDiagnosis` 文件夹
2. 选择「上传并部署：云端安装依赖」

### 3. 验证部署

在微信开发者工具控制台测试：

```javascript
wx.cloud.callFunction({
  name: 'startDiagnosis',
  data: {
    brand_list: ['测试品牌'],
    selectedModels: [{ name: 'doubao', checked: true }],
    custom_question: '测试问题'
  }
}).then(console.log).catch(console.error);
```

## 日志查看

在微信云开发控制台查看云函数日志：
1. 打开微信云开发控制台
2. 进入「云函数」页面
3. 点击 `startDiagnosis`
4. 查看「日志」标签页

## 故障排查

### 问题：云函数调用超时

**可能原因：**
- 后端 API 响应慢
- 网络连接问题

**解决方案：**
- 增加 `API_TIMEOUT` 值
- 检查后端服务性能
- 配置 VPC 内网访问

### 问题：后端 API 返回 401

**可能原因：**
- 缺少认证信息
- Token 过期

**解决方案：**
- 在请求头中添加认证信息
- 实现 Token 刷新机制

### 问题：参数验证失败

**可能原因：**
- 参数格式不正确
- 缺少必填参数

**解决方案：**
- 参考本文档的请求参数说明
- 在小程序端进行预验证

## 相关文件

- [diagnosisService.js](../../services/diagnosisService.js) - 前端诊断服务封装
- [getDiagnosisStatus](../getDiagnosisStatus/README.md) - 获取诊断状态云函数
- [diagnosis_views.py](../../../backend_python/wechat_backend/views/diagnosis_views.py) - 后端诊断 API

## 更新日志

### v1.0.0 (2026-03-02)
- 初始版本
- 支持启动品牌诊断任务
- 完整的参数验证和错误处理
- 详细的日志记录

## 作者

系统架构组

## 许可证

MIT
