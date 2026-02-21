#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加 StageEstimator 引用
old_imports = '''const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');'''

new_imports = '''const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');
const StageEstimator = require('../../utils/stageEstimator');'''

content = content.replace(old_imports, new_imports)

# 2. 添加实例变量
old_instances = '''  /**
   * 【P1-4 新增】进度验证器
   */
  progressValidator: null,

  data: {'''

new_instances = '''  /**
   * 【P1-4 新增】进度验证器
   */
  progressValidator: null,
  
  /**
   * 【P1-6 新增】分阶段预估器
   */
  stageEstimator: null,

  data: {'''

content = content.replace(old_instances, new_instances)

# 3. 在 data 中添加阶段文案
old_data_fields = '''    //【P1-4 新增】进度验证状态
    progressValidationStatus: 'normal',
    progressWarnings: []
  },'''

new_data_fields = '''    //【P1-4 新增】进度验证状态
    progressValidationStatus: 'normal',
    progressWarnings: [],
    //【P1-6 新增】阶段说明
    stageDescription: '',
    //【P2-7 新增】进度解释文案
    progressExplanation: ''
  },'''

content = content.replace(old_data_fields, new_data_fields)

# 4. 在 onLoad 中初始化
old_init = '''      //【P1-4 新增】初始化进度验证器
      this.progressValidator = new ProgressValidator();'''

new_init = '''      //【P1-4 新增】初始化进度验证器
      this.progressValidator = new ProgressValidator();
      
      //【P1-6 新增】初始化分阶段预估器
      this.stageEstimator = new StageEstimator();'''

content = content.replace(old_init, new_init)

# 5. 更新 updateProgressDetails 方法添加阶段说明
old_method_end = '''    // 获取当前任务描述
    let currentTaskDesc = '';
    if (parsedStatus.stage === 'analyzing') {
      currentTaskDesc = '正在分析 AI 平台响应';
    } else if (parsedStatus.stage === 'aggregating') {
      currentTaskDesc = '正在聚合分析结果';
    } else if (parsedStatus.stage === 'generating') {
      currentTaskDesc = '正在生成诊断报告';
    } else {
      currentTaskDesc = parsedStatus.statusText || '诊断进行中';
    }'''

new_method_end = '''    // 获取当前任务描述
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
    
    //【P1-6 新增】获取阶段说明
    const stageDesc = this.stageEstimator.getStageDescription(parsedStatus.stage);
    
    //【P2-7 新增】生成进度解释文案
    const explanation = this.generateProgressExplanation(parsedStatus, stageDesc);
    
    this.setData({
      stageDescription: stageDesc,
      progressExplanation: explanation
    });'''

content = content.replace(old_method_end, new_method_end)

# 6. 添加 generateProgressExplanation 方法
old_addmethod = '''  /**
   * 【P0 重构】更新轮询间隔
   */
  updatePollingInterval: function(progress) {'''

new_addmethod = '''  /**
   * 【P2-7 新增】生成进度解释文案
   */
  generateProgressExplanation: function(parsedStatus, stageDesc) {
    const progress = parsedStatus.progress;
    
    if (progress < 20) {
      return '刚开始诊断，正在收集各 AI 平台的基础数据...';
    } else if (progress < 50) {
      return '诊断进行中，已分析部分 AI 平台响应...';
    } else if (progress < 80) {
      return '诊断过半，正在聚合多个平台的数据...';
    } else if (progress < 95) {
      return '接近尾声，正在生成最终诊断报告...';
    } else {
      return '即将完成，正在做最后的数据校验...';
    }
  },

  /**
   * 【P0 重构】更新轮询间隔
   */
  updatePollingInterval: function(progress) {'''

content = content.replace(old_addmethod, new_addmethod)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已集成分阶段预估器和解释文案')
