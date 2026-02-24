# 品牌诊断系统 - 紧急修复指南

**问题**: 前端轮询失败，报错"诊断失败"  
**时间**: 2026-02-24  
**级别**: 🔴 紧急

---

## 🚨 立即执行步骤

### 步骤 1: 清除所有缓存

**微信开发者工具**:
1. 点击菜单栏 **工具** → **清除缓存**
2. 勾选 **清除全部缓存**
3. 点击 **清除** 按钮

### 步骤 2: 重新编译项目

**微信开发者工具**:
1. 点击工具栏的 **编译** 按钮
2. 等待编译完成
3. 观察控制台是否有以下日志：
   ```
   [parseTaskStatus] 解析结果：{...}
   ```

### 步骤 3: 测试诊断

1. 在首页输入品牌名称（如"华为"）
2. 选择 1 个 AI 模型（先只选 1 个测试）
3. 点击"开始诊断"
4. **立即打开控制台**
5. 观察是否有 `[parseTaskStatus]` 日志

---

## 📊 诊断问题

### 如果有 `[parseTaskStatus]` 日志

说明前端代码已生效，请复制日志内容，格式应该类似：
```
[parseTaskStatus] 解析结果：{
  stage: "xxx",
  progress: XX,
  is_completed: true/false,
  status: "xxx",
  results_count: X,
  detailed_results_count: X
}
```

### 如果没有 `[parseTaskStatus]` 日志

说明前端代码**没有生效**，请执行：

1. **完全重启微信开发者工具**:
   - 关闭微信开发者工具
   - 重新打开
   - 重新编译项目

2. **检查文件是否保存**:
   ```bash
   # 在终端执行
   cat /Users/sgl/PycharmProjects/PythonProject/services/taskStatusService.js | grep "console.log"
   ```
   
   应该看到输出包含 `[parseTaskStatus]` 的行

3. **手动添加调试日志**:
   如果文件已修改但没有生效，在 `brandTestService.js` 第 235 行附近添加：
   ```javascript
   console.log('[DEBUG] 收到轮询响应:', res);
   const parsedStatus = parseTaskStatus(res);
   console.log('[DEBUG] 解析后的状态:', parsedStatus);
   ```

---

## 🔍 后端检查

如果前端代码已生效但仍然失败，请检查后端日志：

### 检查后端返回的 stage 值

后端应该返回以下值之一：
- `init`
- `ai_fetching`
- `intelligence_analyzing`
- `competition_analyzing`
- `completed`
- `failed`

**错误示例**:
```json
{
  "stage": "",           // ❌ 空字符串
  "stage": null,         // ❌ null
  "stage": "COMPLETED"   // ❌ 大写（应该小写）
}
```

### 检查后端返回的 is_completed 值

应该返回布尔值：
```json
{
  "is_completed": true   // ✅
  "is_completed": false  // ✅
}
```

---

## 📝 临时解决方案

如果问题仍然存在，可以临时修改轮询终止条件：

**文件**: `services/brandTestService.js`  
**位置**: 第 254 行附近

**修改前**:
```javascript
if (parsedStatus.stage === 'completed' || parsedStatus.stage === 'failed' || parsedStatus.is_completed === true) {
```

**修改后**:
```javascript
// 【临时修复】放宽终止条件
if (parsedStatus.stage === 'completed' || 
    parsedStatus.stage === 'failed' || 
    parsedStatus.is_completed === true ||
    parsedStatus.progress >= 100) {
```

这样可以确保进度达到 100% 时也会停止轮询。

---

## 📞 联系支持

如果以上步骤都无法解决问题，请提供：
1. 控制台完整日志（包括 `[parseTaskStatus]` 输出）
2. 后端 `/test/status` 接口返回的完整 JSON
3. 网络面板中 `/test/status` 请求的响应内容

---

**最后更新**: 2026-02-24
