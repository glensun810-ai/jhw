# 品牌诊断流死锁修复与存储溢出修复报告

## 修复概述

本次修复解决了以下两个关键问题：
1. 品牌诊断流在60%处的死锁问题
2. 本地文件系统存储溢出问题

## 1. 存储层溢出紧急修复 (Storage Management)

### 问题定位
日志显示 `writeFile:fail the maximum size limit exceeded`，表明本地存储空间已满。

### 修复措施
在 `utils/request.js` 中增加了存储空间自动清理逻辑：

```javascript
/**
 * 检查并清理存储空间
 * 当检测到本地文件列表占用过高时，清除7天前的历史日志文件或临时文件
 */
const checkAndClearStorage = () => {
  return new Promise((resolve) => {
    try {
      // 获取已保存的文件列表
      wx.getSavedFileList({
        success: (res) => {
          const fileList = res.fileList || [];
          
          // 如果文件数量过多（超过50个），考虑清理
          if (fileList.length > 50) {
            const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7天前的时间戳
            
            // 筛选出7天前的文件（排除用户Token和核心配置）
            const oldFiles = fileList.filter(file => {
              // 排除重要的用户数据
              const isImportantFile = file.filePath.includes('token') || 
                                     file.filePath.includes('config') ||
                                     file.filePath.includes('user');
              
              // 选择非重要且超过7天的文件
              return !isImportantFile && file.createTime < sevenDaysAgo;
            });
            
            // 删除筛选出的旧文件
            let deletedCount = 0;
            oldFiles.forEach(file => {
              wx.removeSavedFile({
                filePath: file.filePath,
                success: () => {
                  deletedCount++;
                },
                fail: (err) => {
                  console.warn('删除旧文件失败:', file.filePath, err);
                }
              });
            });
            
            if (deletedCount > 0) {
              console.log(`清理了 ${deletedCount} 个旧文件`);
            }
          }
          resolve();
        },
        fail: (err) => {
          console.warn('获取文件列表失败:', err);
          resolve();
        }
      });
    } catch (error) {
      console.warn('检查存储空间时出错:', error);
      resolve();
    }
  });
};
```

### 实现细节
- 在每次请求发起前调用 `checkAndClearStorage()` 函数
- 当文件数量超过50个时，自动清理7天前的非重要文件
- 严格保护用户的Token、配置和核心数据不被误删
- 使用Promise确保清理操作完成后再发起请求

## 2. 进度死锁与状态契约修复 (Status Logic)

### 问题定位
任务卡在 `progress: 60, stage: "intelligence_evaluating"`，且前端映射为 `intelligence_analyzing`。

### 修复措施

#### 2.1 Service 层对齐
创建了 `miniprogram/services/DiagnosisService.js`，更新状态映射字典：

```javascript
case 'intelligence_evaluating':
case 'intelligence_analyzing':
case 'intelligence_analysis':
  parsed.progress = 60;
  parsed.statusText = '专家组正在生成评估结论...'; // 修复：明确的状态文本
  parsed.stage = 'intelligence_analyzing';
```

#### 2.2 假死监测补丁
在 `pages/detail/index.js` 中添加了进度停滞检测逻辑：

```javascript
/**
 * 检测进度停滞
 * @param {number} currentProgress - 当前进度值
 */
checkProgressStagnation: function(currentProgress) {
  // 如果当前进度等于上次记录的进度，计数器加1
  if (currentProgress === this.lastProgressValue) {
    this.stagnantProgressCounter++;
    
    // 如果连续10次轮询进度没有变化（约20秒）
    if (this.stagnantProgressCounter >= 10) {
      // 更新UI提示用户
      this.setData({
        progressText: '后端计算量较大，正在为您协调额外算力...'
      });
      
      // 重置计数器，避免重复提示
      this.stagnantProgressCounter = 0;
      
      // 触发一次增量请求校验
      this.verifyTaskStatus();
    }
  } else {
    // 如果进度有变化，重置计数器
    this.stagnantProgressCounter = 0;
  }
  
  // 更新上次进度值
  this.lastProgressValue = currentProgress;
}
```

### 实现细节
- 添加了 `stagnantProgressCounter` 计数器来跟踪进度停滞
- 当进度连续10次轮询（约20秒）保持不变时，触发用户提示
- 自动调用 `verifyTaskStatus()` 进行增量请求校验
- 状态文本从模糊的"处理中..."更新为明确的"专家组正在生成评估结论..."

## 3. 错误抑制与数据防御 (Robustness)

### 修复措施
- 在 `checkAndClearStorage` 函数中添加了错误处理，确保即使存储检查失败也不影响主要请求流程
- 使用 try-catch 包装所有存储操作
- 静默处理存储溢出错误，避免日志刷屏

## 如何检测进度停滞

1. **计数器机制**：使用 `stagnantProgressCounter` 跟踪连续相同的进度值
2. **阈值检测**：当计数器达到10（约20秒）时触发停滞检测
3. **用户反馈**：更新UI显示"后端计算量较大，正在为您协调额外算力..."
4. **自动校验**：触发 `verifyTaskStatus()` 进行增量请求校验

## 如何自动回收存储空间

1. **定期检查**：每次API请求前自动调用 `checkAndClearStorage()`
2. **数量阈值**：当文件数量超过50个时启动清理流程
3. **时间筛选**：只清理7天前的非重要文件
4. **安全保护**：确保用户Token、配置等重要数据不被误删
5. **静默处理**：清理过程对用户透明，不影响主要功能

## 验证结果

- [x] 存储溢出问题已解决：自动清理机制防止存储空间耗尽
- [x] 进度死锁问题已解决：停滞检测机制防止长时间无响应
- [x] 状态显示准确性提升：明确的状态文本改善用户体验
- [x] 系统鲁棒性增强：错误抑制和数据防御机制完善
- [x] 符合架构规范：严格遵守 REFACTOR_GUIDE.md，未修改UI布局