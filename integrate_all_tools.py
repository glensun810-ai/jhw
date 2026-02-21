#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加新工具类引用
old_imports = '''const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');
const StageEstimator = require('../../utils/stageEstimator');'''

new_imports = '''const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');
const StageEstimator = require('../../utils/stageEstimator');
const NetworkMonitor = require('../../utils/networkMonitor');
const ProgressNotifier = require('../../utils/progressNotifier');
const TaskWeightProcessor = require('../../utils/taskWeightProcessor');'''

content = content.replace(old_imports, new_imports)

# 2. 添加实例变量
old_instances = '''  /**
   * 【P1-6 新增】分阶段预估器
   */
  stageEstimator: null,

  data: {'''

new_instances = '''  /**
   * 【P1-6 新增】分阶段预估器
   */
  stageEstimator: null,
  
  /**
   * 【P2-9 新增】网络监测器
   */
  networkMonitor: null,
  
  /**
   * 【P2-10 新增】进度通知器
   */
  progressNotifier: null,
  
  /**
   * 【P2 新增】任务权重处理器
   */
  taskWeightProcessor: null,

  data: {'''

content = content.replace(old_instances, new_instances)

# 3. 在 data 中添加网络质量字段
old_data_fields = '''    //【P2-7 新增】进度解释文案
    progressExplanation: ''
  },'''

new_data_fields = '''    //【P2-7 新增】进度解释文案
    progressExplanation: '',
    //【P2-9 新增】网络质量
    networkQuality: 'unknown',
    networkQualityText: '',
    //【P2-10 新增】订阅状态
    isSubscribed: false
  },'''

content = content.replace(old_data_fields, new_data_fields)

# 4. 在 onLoad 中初始化新工具
old_init = '''      //【P1-6 新增】初始化分阶段预估器
      this.stageEstimator = new StageEstimator();'''

new_init = '''      //【P1-6 新增】初始化分阶段预估器
      this.stageEstimator = new StageEstimator();
      
      //【P2-9 新增】初始化网络监测器
      this.networkMonitor = new NetworkMonitor();
      
      //【P2-10 新增】初始化进度通知器
      this.progressNotifier = new ProgressNotifier();
      
      //【P2 新增】初始化任务权重处理器
      this.taskWeightProcessor = new TaskWeightProcessor();
      
      // 获取网络质量
      this.getNetworkQuality();
      
      // 检查订阅状态
      this.checkSubscription();'''

content = content.replace(old_init, new_init)

# 5. 添加 getNetworkQuality 和 checkSubscription 方法
old_method = '''  /**
   * 【P2-8 新增】取消诊断功能
   */
  cancelDiagnosis: function() {'''

new_method = '''  /**
   * 【P2-9 新增】获取网络质量
   */
  getNetworkQuality: function() {
    wx.getNetworkType({
      success: (res) => {
        const networkType = res.networkType;
        const quality = this.networkMonitor.getQualityLevel();
        
        this.setData({
          networkQuality: quality.level,
          networkQualityText: `${quality.text} (${networkType})`
        });
      }
    });
  },

  /**
   * 【P2-10 新增】检查订阅状态
   */
  checkSubscription: function() {
    // 从本地存储读取订阅状态
    const subscribed = wx.getStorageSync('message_subscribed') || false;
    this.setData({
      isSubscribed: subscribed
    });
  },

  /**
   * 【P2-10 新增】请求订阅消息
   */
  requestMessageSubscription: function() {
    this.progressNotifier.requestSubscription().then((res) => {
      if (res.success && res.subscribed) {
        wx.setStorageSync('message_subscribed', true);
        this.setData({
          isSubscribed: true
        });
        wx.showToast({
          title: '订阅成功，完成后会通知您',
          icon: 'success'
        });
      }
    });
  },

  /**
   * 【P2-8 新增】取消诊断功能
   */
  cancelDiagnosis: function() {'''

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已集成所有新工具类')
