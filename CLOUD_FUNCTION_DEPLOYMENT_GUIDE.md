# 云函数部署指南

## 问题诊断

**错误信息**:
```
cloud.callFunction:fail Error: errCode: -501000 | errMsg: FunctionName parameter could not be found.
```

**原因**: 云函数 `getDiagnosisReport` 未部署到微信云开发环境

---

## 解决方案

### 方案一：部署云函数（推荐）

#### 1. 准备工作

1. **安装微信开发者工具**
   - 下载地址：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
   - 版本要求：最新版（稳定版）

2. **配置云开发环境**
   - 打开微信开发者工具
   - 打开项目：`/Users/sgl/PycharmProjects/PythonProject`
   - 点击工具栏「云开发」按钮
   - 开通云开发环境（如未开通）
   - 记录云环境 ID（如：`cloud1-xxx`）

3. **安装云函数依赖**
   ```bash
   # 进入云函数目录
   cd /Users/sgl/PycharmProjects/PythonProject/miniprogram/cloudfunctions/getDiagnosisReport

   # 安装依赖（如果未安装）
   npm install

   # 检查依赖是否正确安装
   ls -la node_modules/
   ```

#### 2. 上传云函数

**方法 A: 使用微信开发者工具（推荐）**

1. 打开微信开发者工具
2. 在左侧文件树中找到 `cloudfunctions/getDiagnosisReport` 目录
3. 右键点击 `getDiagnosisReport` 文件夹
4. 选择「上传并部署：云端安装依赖」
5. 等待上传完成（状态栏显示「上传成功」）

**方法 B: 使用命令行工具**

```bash
# 安装微信云开发 CLI 工具
npm install -g @cloudbase/cli

# 登录（使用微信扫码）
tcb login

# 上传云函数
tcb fn deploy getDiagnosisReport --env <你的云环境 ID>
```

#### 3. 配置云函数环境变量

1. 登录微信云开发控制台：https://console.cloud.tencent.com/wechat
2. 进入「云函数」页面
3. 找到 `getDiagnosisReport` 函数
4. 点击「配置」标签页
5. 添加环境变量：
   - `API_BASE_URL`: 你的后端 API 地址
     - 开发环境：`http://localhost:5001`（需内网穿透）
     - 生产环境：`https://api.your-domain.com`
   - `PROD_API_URL`: 生产环境 API 地址（可选）

6. 点击「保存」并「重新部署」

#### 4. 验证部署

**方法 A: 在云开发控制台测试**

1. 进入云函数详情页面
2. 点击「测试」标签页
3. 输入测试事件：
   ```json
   {
     "executionId": "test-123456"
   }
   ```
4. 点击「测试」按钮
5. 查看执行结果和日志

**方法 B: 在小程序中测试**

1. 在小程序中执行诊断
2. 查看控制台日志
3. 确认云函数调用成功

---

### 方案二：使用 HTTP 模式（临时方案）

如果暂时无法部署云函数，可以修改前端直接使用 HTTP 请求：

#### 修改 diagnosisService.js

```javascript
// 原代码（第 437 行）：
const res = await wx.cloud.callFunction({
  name: 'getDiagnosisReport',
  data: { executionId: executionId }
});

// 修改为：
const res = await wx.request({
  url: 'https://your-backend-api.com/api/diagnosis/report/' + executionId,
  method: 'GET',
  header: {
    'Content-Type': 'application/json'
  }
});

const result = res.data;
```

**注意**: 需要配置合法域名（小程序管理后台）

---

### 方案三：使用后端直连（开发环境）

开发环境下可以直接调用后端 API，绕过云函数：

#### 修改 diagnosisService.js

```javascript
async getFullReport(executionId) {
  try {
    console.log('[DiagnosisService] Getting full report:', executionId);

    // 开发环境：直接调用后端 API
    if (__wxConfig && __wxConfig.envVersion === 'develop') {
      const res = await wx.request({
        url: 'http://localhost:5001/api/diagnosis/report/' + executionId,
        method: 'GET',
        header: {
          'Content-Type': 'application/json'
        }
      });
      
      const result = res.data;
      console.log('[DiagnosisService] Full report received:', result);
      
      if (!result) {
        throw new Error('云函数返回为空');
      }
      
      if (result.error_code || result.error) {
        const error = new Error(result.error_message || result.error || '获取报告失败');
        error.code = result.error_code || 'REPORT_ERROR';
        throw error;
      }
      
      return this._normalizeReport(result);
    }

    // 生产环境：使用云函数
    const res = await wx.cloud.callFunction({
      name: 'getDiagnosisReport',
      data: {
        executionId: executionId
      }
    });
    
    // ... 后续处理逻辑不变
  } catch (error) {
    console.error('[DiagnosisService] Failed to get full report:', error);
    throw error;
  }
}
```

---

## 完整云函数列表

本项目需要部署以下云函数：

| 云函数名称 | 路径 | 状态 |
|-----------|------|------|
| getDiagnosisReport | cloudfunctions/getDiagnosisReport | ❌ 未部署 |
| getDiagnosisStatus | cloudfunctions/getDiagnosisStatus | ❌ 未部署 |
| startDiagnosis | cloudfunctions/startDiagnosis | ❌ 未部署 |

**批量上传命令**:

```bash
cd /Users/sgl/PycharmProjects/PythonProject/miniprogram/cloudfunctions

# 上传所有云函数
for fn in getDiagnosisReport getDiagnosisStatus startDiagnosis; do
  echo "Uploading $fn..."
  cd $fn && npm install && cd ..
  tcb fn deploy $fn --env <你的云环境 ID>
done
```

---

## 常见问题

### Q1: 上传后仍然提示 Function not found

**原因**: 云环境 ID 不匹配

**解决**:
1. 检查小程序的 `project.config.json` 中的 `cloudfunctionRoot` 配置
2. 确认云函数上传到的云环境 ID 与小程序使用的云环境一致
3. 在云开发控制台确认云函数状态为「部署成功」

### Q2: 云函数调用超时

**原因**: 后端 API 响应慢或网络问题

**解决**:
1. 在云函数控制台增加超时时间（默认 3 秒，建议改为 30 秒）
2. 检查后端 API 是否正常响应
3. 查看云函数日志，定位慢查询

### Q3: 云函数返回 501030 (errCode: -501030)

**原因**: 云函数未正确初始化

**解决**:
1. 检查 `index.js` 中的 `cloud.init()` 调用
2. 确认 `wx-server-sdk` 版本正确
3. 重新上传并部署云函数

### Q4: 本地开发如何调试云函数？

**方法**:
1. 使用微信开发者工具的「云函数本地调试」功能
2. 在云函数目录右键选择「本地调试」
3. 设置断点，单步调试

---

## 快速部署脚本

创建 `deploy-cloudfunctions.sh`:

```bash
#!/bin/bash

# 云函数部署脚本
# 用法：./deploy-cloudfunctions.sh <云环境 ID>

CLOUD_ENV=$1

if [ -z "$CLOUD_ENV" ]; then
  echo "用法：$0 <云环境 ID>"
  echo "示例：$0 cloud1-xxx"
  exit 1
fi

echo "开始部署云函数到环境：$CLOUD_ENV"

# 进入云函数目录
cd "$(dirname "$0")/miniprogram/cloudfunctions"

# 部署每个云函数
for fn in getDiagnosisReport getDiagnosisStatus startDiagnosis; do
  echo ""
  echo "========================================"
  echo "部署云函数：$fn"
  echo "========================================"
  
  if [ ! -d "$fn" ]; then
    echo "错误：云函数目录 $fn 不存在"
    continue
  fi
  
  # 安装依赖
  echo "[$fn] 安装依赖..."
  cd "$fn" && npm install && cd ..
  
  # 上传部署
  echo "[$fn] 上传到云端..."
  tcb fn deploy "$fn" --env "$CLOUD_ENV"
  
  if [ $? -eq 0 ]; then
    echo "[$fn] ✅ 部署成功"
  else
    echo "[$fn] ❌ 部署失败"
  fi
done

echo ""
echo "========================================"
echo "部署完成"
echo "========================================"
```

使用方法：
```bash
chmod +x deploy-cloudfunctions.sh
./deploy-cloudfunctions.sh cloud1-xxx
```

---

## 验证清单

部署完成后，请确认：

- [ ] 所有云函数状态为「部署成功」
- [ ] 云函数环境变量已配置
- [ ] 小程序能成功调用云函数
- [ ] 云函数日志中无错误
- [ ] 后端 API 能正常响应

---

**文档生成时间**: 2026-03-13  
**版本**: v1.0
