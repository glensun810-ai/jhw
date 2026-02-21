#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 Page({后添加 timeEstimator 实例
old_page = '''Page({
  data: {'''

new_page = '''Page({
  /**
   * 【P0 新增】时间预估器实例
   */
  timeEstimator: null,

  data: {'''

content = content.replace(old_page, new_page)

# 2. 在 data 中添加新的字段
old_data = '''    //【P0 新增】诊断知识
    knowledgeTip: '',
    knowledgeIndex: 0
  },'''

new_data = '''    //【P0 新增】诊断知识
    knowledgeTip: '',
    knowledgeIndex: 0,
    //【P0 新增】时间预估范围
    timeEstimateRange: '',
    timeEstimateConfidence: 0
  },'''

content = content.replace(old_data, new_data)

# 3. 在 onLoad 中初始化时间预估器
old_onload = '''      // 计算预估时间：基础 8 秒 + (品牌数 * 模型数 * 1.5 秒) * 1.3 倍安全系数
      const estimatedTime = Math.ceil((8 + (this.brandList.length * this.modelNames.length * 1.5)) * 1.3);'''

new_onload = '''      //【P0 重构】使用智能时间预估器
      this.timeEstimator = new TimeEstimator();
      const timeEstimate = this.timeEstimator.estimate(
        this.brandList.length,
        this.modelNames.length,
        this.customQuestion ? 1 : 3
      );
      const estimatedTime = timeEstimate.expected;'''

content = content.replace(old_onload, new_onload)

# 4. 添加预估范围显示
old_setdata = '''      this.setData({
        isLoading: true,
        showSkeleton: true,
        customQuestion: this.customQuestion,
        estimatedTime: estimatedTime,
        currentTime: estimatedTime,
        progress: 0,
        progressText: `📊 深度研判启动：预计耗时 ${estimatedTime}s`
      });'''

new_setdata = '''      this.setData({
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

content = content.replace(old_setdata, new_setdata)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已集成时间预估器')
