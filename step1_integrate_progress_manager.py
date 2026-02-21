#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 1: 集成进度管理器到 detail 页面

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加 ProgressManager 引用
old_imports = '''const { getMatrixData, getColorByScore } = require('./utils/matrixHelper');
const { getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/DiagnosisService');
const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');
const StageEstimator = require('../../utils/stageEstimator');
const NetworkMonitor = require('../../utils/networkMonitor');
const ProgressNotifier = require('../../utils/progressNotifier');
const TaskWeightProcessor = require('../../utils/taskWeightProcessor');'''

new_imports = '''const { getMatrixData, getColorByScore } = require('./utils/matrixHelper');
const { getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/DiagnosisService');
const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');
const StageEstimator = require('../../utils/stageEstimator');
const NetworkMonitor = require('../../utils/networkMonitor');
const ProgressNotifier = require('../../utils/progressNotifier');
const TaskWeightProcessor = require('../../utils/taskWeightProcessor');
const ProgressManager = require('../../utils/progressManager');'''

content = content.replace(old_imports, new_imports)

# 2. 添加 progressManager 实例
old_instances = '''  /**
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
  
  /**
   * 【P0 新增】进度管理器
   */
  progressManager: null,

  data: {'''

content = content.replace(old_instances, new_instances)

# 3. 在 onLoad 中初始化进度管理器
old_onload = '''      //【P0 重构】使用智能时间预估器
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
      });

      // 启动进度条动画（10 秒内平滑滑到 80%）
      this.startProgressAnimation(estimatedTime);

      // 启动轮询
      this.startPolling();'''

new_onload = '''      //【P0 重构】使用智能时间预估器
      const timeEstimate = this.timeEstimator.estimate(
        this.brandList.length,
        this.modelNames.length,
        this.customQuestion ? 1 : 3
      );
      const estimatedTime = timeEstimate.expected;

      //【P0 新增】初始化进度管理器
      const questionCount = this.customQuestion ? 1 : 3;
      const modelCount = this.modelNames.length;
      this.progressManager = new ProgressManager(this);
      this.progressManager.init(questionCount, modelCount);

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
      });

      // 启动轮询 (不再使用 startProgressAnimation)
      this.startPolling();'''

content = content.replace(old_onload, new_onload)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 1 完成：进度管理器已集成')
