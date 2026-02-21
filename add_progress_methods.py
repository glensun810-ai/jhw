#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到插入位置
old_code = '''    // 更新上次进度值
    this.lastProgressValue = currentProgress;
  },

  /**
   * 触发增量请求校验
   */
  verifyTaskStatus: function() {'''

new_code = '''    // 更新上次进度值
    this.lastProgressValue = currentProgress;
  },

  /**
   * 【P0 新增】更新进度详情
   */
  updateProgressDetails: function(statusData, parsedStatus) {
    const totalTasks = this.brandList.length * this.modelNames.length;
    const completedTasks = Math.floor((parsedStatus.progress / 100) * totalTasks);
    const pendingTasks = totalTasks - completedTasks - 1;
    
    // 计算剩余时间
    const elapsed = (Date.now() - this.startTime) / 1000;
    const progressRatio = parsedStatus.progress / 100;
    const estimatedTotal = elapsed / (progressRatio || 0.01);
    const remaining = Math.max(0, estimatedTotal - elapsed);
    
    // 获取当前任务描述
    let currentTaskDesc = '';
    if (parsedStatus.stage === 'analyzing') {
      currentTaskDesc = '正在分析 AI 平台响应';
    } else if (parsedStatus.stage === 'aggregating') {
      currentTaskDesc = '正在聚合分析结果';
    } else if (parsedStatus.stage === 'generating') {
      currentTaskDesc = '正在生成诊断报告';
    } else {
      currentTaskDesc = parsedStatus.statusText || '诊断进行中';
    }
    
    this.setData({
      remainingTime: Math.round(remaining),
      completedTasks: completedTasks,
      totalTasks: totalTasks,
      currentTask: currentTaskDesc,
      pendingTasks: Math.max(0, pendingTasks)
    });
  },

  /**
   * 【P0 新增】后台运行功能
   */
  runInBackground: function() {
    wx.showModal({
      title: '后台运行确认',
      content: '诊断将在后台继续运行，完成后会通知您。确定要返回首页吗？',
      confirmText: '确定',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 返回首页
          wx.redirectTo({
            url: '/pages/index/index'
          });
        }
      }
    });
  },

  /**
   * 触发增量请求校验
   */
  verifyTaskStatus: function() {'''

content = content.replace(old_code, new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加进度更新和后台运行方法')
