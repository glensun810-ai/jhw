#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 updateProgressDetails 方法
old_method = '''  /**
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
  },'''

new_method = '''  /**
   * 【P0 新增】更新进度详情
   */
  updateProgressDetails: function(statusData, parsedStatus) {
    const totalTasks = this.brandList.length * this.modelNames.length;
    const completedTasks = Math.floor((parsedStatus.progress / 100) * totalTasks);
    const pendingTasks = totalTasks - completedTasks - 1;
    
    const elapsed = (Date.now() - this.startTime) / 1000;
    const now = Date.now();
    
    //【P0-3 新增】使用平滑算法计算剩余时间
    const remainingResult = this.remainingTimeCalc.calculate(
      parsedStatus.progress,
      elapsed
    );
    
    //【P1-4 新增】验证进度真实性
    const validationResult = this.progressValidator.validate(
      parsedStatus.progress,
      now
    );
    
    // 根据验证结果显示警告
    let progressStatus = 'normal';
    let progressWarnings = [];
    
    if (validationResult.status === 'stalled') {
      progressStatus = 'stalled';
      progressWarnings.push('进度暂时停滞，正在加速处理...');
    } else if (validationResult.status === 'slow') {
      progressStatus = 'slow';
      progressWarnings.push('网络较慢，请耐心等待...');
    }
    
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
      remainingTime: remainingResult.seconds,
      smoothedRemainingTime: remainingResult.display,
      completedTasks: completedTasks,
      totalTasks: totalTasks,
      currentTask: currentTaskDesc,
      pendingTasks: Math.max(0, pendingTasks),
      progressValidationStatus: progressStatus,
      progressWarnings: progressWarnings
    });
  },'''

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已更新 updateProgressDetails 方法')
