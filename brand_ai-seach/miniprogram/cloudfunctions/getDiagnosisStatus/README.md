# getDiagnosisStatus 云函数

获取诊断任务状态的云函数。

## 功能

1. 调用后端 API 获取任务状态
2. 返回给前端轮询使用

## 部署

### 开发环境

1. 确保后端服务运行在 `http://localhost:5001`
2. 在微信开发者工具中右键点击 `getDiagnosisStatus` 目录
3. 选择"上传并部署：云端安装依赖"

### 生产环境

1. 修改 `index.js` 中的 `API_BASE_URL` 为生产环境地址
2. 在微信开发者工具中右键点击 `getDiagnosisStatus` 目录
3. 选择"上传并部署：云端安装依赖"

## 调用示例

```javascript
wx.cloud.callFunction({
  name: 'getDiagnosisStatus',
  data: {
    executionId: 'xxx-xxx-xxx'
  },
  success: res => {
    console.log('获取状态成功', res.result);
  },
  fail: err => {
    console.error('获取状态失败', err);
  }
});
```

## 返回数据

```json
{
  "success": true,
  "data": {
    "task_id": "xxx",
    "progress": 50,
    "stage": "ai_fetching",
    "status": "processing",
    "is_completed": false,
    "should_stop_polling": false,
    ...
  }
}
```

## 注意事项

1. 确保云开发环境已正确配置
2. 确保后端 API 可访问（生产环境需配置域名白名单）
3. 建议开启 CDN 加速提高响应速度
