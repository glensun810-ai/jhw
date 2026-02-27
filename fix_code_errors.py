#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 添加 timeEstimate 变量定义
old_code1 = '''      const estimatedTime = Math.ceil((8 + (this.brandList.length * this.modelNames.length * 1.5)) * 1.3);

      // 更新标题显示当前诊断问题
      this.setData({
        isLoading: true,
        showSkeleton: true,
        customQuestion: this.customQuestion,
        estimatedTime: estimatedTime,
        currentTime: estimatedTime,
        progress: 0,
        progressText: `📊 深度研判启动：预计耗时 ${estimatedTime}s`,
        timeEstimateRange: `${timeEstimate.min}-${timeEstimate.max}秒`,
        timeEstimateConfidence: timeEstimate.confidence
      });'''

new_code1 = '''      //【P0 重构】使用智能时间预估器
      const timeEstimate = this.timeEstimator.estimate(
        this.brandList.length,
        this.modelNames.length,
        this.customQuestion ? 1 : 3
      );
      const estimatedTime = timeEstimate.expected;

      // 更新标题显示当前诊断问题
      this.setData({
        isLoading: true,
        showSkeleton: true,
        customQuestion: this.customQuestion,
        estimatedTime: estimatedTime,
        currentTime: estimatedTime,
        progress: 0,
        progressText: `📊 深度研判启动：预计耗时 ${estimatedTime}s`,
        timeEstimateRange: `${timeEstimate.min}-${timeEstimate.max}秒`,
        timeEstimateConfidence: timeEstimate.confidence
      });'''

content = content.replace(old_code1, new_code1)

# 修复 2: 检查 progressNotifier 是否为 null
old_code2 = '''  requestMessageSubscription: function() {
    this.progressNotifier.requestSubscription().then((res) => {'''

new_code2 = '''  requestMessageSubscription: function() {
    if (!this.progressNotifier) {
      logger.error('progressNotifier 未初始化');
      return;
    }
    
    this.progressNotifier.requestSubscription().then((res) => {'''

content = content.replace(old_code2, new_code2)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已修复代码错误')
