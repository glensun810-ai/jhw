#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 2: 优化轮询逻辑

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改 startPolling 方法 - 固定轮询间隔
old_polling = '''  /**
   * 启动轮询
   */
  startPolling: function() {
    // 初始化矩阵框架，显示加载状态
    this.initializeMatrixFramework();

    // 记录开始时间
    this.startTime = Date.now();

    // 添加进度停滞检测相关变量
    this.stagnantProgressCounter = 0; // 进度停滞计数器
    this.lastProgressValue = 0; // 上一次的进度值

    // Log polling start with DEBUG_AI_CODE
    if (ENABLE_DEBUG_AI_CODE) {
      debugLog('POLLING_START', this.executionId, `Starting polling for task ${this.executionId}`); // #DEBUG_CLEAN
    }

    // 添加轮询间隔管理
    this.currentPollInterval = 3000; // 初始间隔 3 秒
    this.pollAttemptCount = 0; // 轮询尝试计数
    this.maxPollAttempts = 100; // 最大轮询次数

    // 创建一个辅助函数来处理轮询逻辑
    const performPoll = async () => {
      if (this.pollInterval === null) return; // 如果轮询已停止，则退出

      try {
        const statusData = await this.fetchTaskStatus(this.executionId);

        if (statusData) {
          // 使用服务层解析任务状态数据
          const parsedStatus = parseTaskStatus(statusData);

          // 动态调整轮询间隔基于进度
          let newInterval = this.currentPollInterval;
          if (statusData.progress < 20) {
            newInterval = 3000; // 前 20% 进度，3 秒轮询一次
          } else if (statusData.progress < 50) {
            newInterval = 4000; // 20%-50% 进度，4 秒轮询一次
          } else if (statusData.progress < 80) {
            newInterval = 5000; // 50%-80% 进度，5 秒轮询一次
          } else {
            newInterval = 6000; // 80% 以上进度，6 秒轮询一次
          }

          // 如果间隔发生变化，重新设置轮询
          if (newInterval !== this.currentPollInterval) {
            this.currentPollInterval = newInterval;
            clearInterval(this.pollInterval);
            this.pollInterval = setInterval(performPoll, this.currentPollInterval);
            return; // 重新设置轮询后退出当前执行
          }

          // Log polling response with DEBUG_AI_CODE
          if (ENABLE_DEBUG_AI_CODE) {
            debugLog('POLLING_RESPONSE', this.executionId, `Received status: progress=${statusData.progress}, is_completed=${statusData.is_completed}, interval=${this.currentPollInterval}ms`); // #DEBUG_CLEAN
          }

          // 检查任务是否完成
          const isCompleted = statusData.is_completed ||
                             parsedStatus.stage === 'completed';

          if (isCompleted) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;

            // 更新界面显示结果
            this.setData({
              progress: 100,
              statusText: '分析完成',
              isLoading: false
            });

            // P0-1 修复：跳转到正确的结果页面路径，并传递完整数据
            // 从 detailed_results 或 results 中提取数据
            const resultsData = statusData.detailed_results || statusData.results || [];

            // 保存到本地存储，避免 URL 过长
            wx.setStorageSync('latestTestResults_' + this.executionId, resultsData);
            wx.setStorageSync('latestTargetBrand', this.brandList[0] || '');
            wx.setStorageSync('latestCompetitorBrands', this.brandList.slice(1) || []);

            logger.debug('✅ 任务完成，测试结果已保存:', {
              executionId: this.executionId,
              resultsCount: resultsData.length,
              brands: this.brandList
            });

            // 跳转到结果页面（修复路径）
            wx.navigateTo({
              url: `/pages/results/results?executionId=${this.executionId}&brandName=${encodeURIComponent(this.brandList[0] || '')}`
            });
            return;
          }

          // 检查任务是否失败
          if (statusData.status === 'failed') {
            clearInterval(this.pollInterval);
            this.pollInterval = null;

            // 更新界面显示失败状态
            this.setData({
              progress: statusData.progress || 0,
              statusText: '任务失败',
              isLoading: false
            });

            // 显示失败信息
            const errorMessage = statusData.error || '任务执行失败';
            wx.showToast({
              title: errorMessage,
              icon: 'none',
              duration: 3000
            });
            return;
          }

          // 更新进度和状态文本
          this.setData({
            progress: parsedStatus.progress,
            statusText: parsedStatus.statusText
          });

          // 检测进度停滞
          this.checkProgressStagnation(statusData.progress);
        }
      } catch (error) {
        logger.error('轮询错误:', error);
        this.pollAttemptCount++;

        // 如果错误次数过多，停止轮询
        if (this.pollAttemptCount >= this.maxPollAttempts) {
          clearInterval(this.pollInterval);
          this.pollInterval = null;
          this.setData({
            statusText: '获取进度失败',
            isLoading: false
          });
          wx.showToast({
            title: '获取进度失败，请稍后重试',
            icon: 'none'
          });
        }
      }
    };

    // 开始轮询
    this.pollInterval = setInterval(performPoll, this.currentPollInterval);
  },'''

new_polling = '''  /**
   * 【P0 重构】启动轮询 - 优化版
   */
  startPolling: function() {
    // 初始化矩阵框架，显示加载状态
    this.initializeMatrixFramework();

    // 记录开始时间
    this.startTime = Date.now();

    // 添加进度停滞检测相关变量
    this.stagnantProgressCounter = 0;
    this.lastProgressValue = 0;

    // Log polling start with DEBUG_AI_CODE
    if (ENABLE_DEBUG_AI_CODE) {
      debugLog('POLLING_START', this.executionId, `Starting polling for task ${this.executionId}`);
    }

    //【P0 优化】固定轮询间隔为 2 秒
    this.currentPollInterval = 2000;
    this.pollAttemptCount = 0;
    this.maxPollAttempts = 100;

    const performPoll = async () => {
      if (this.pollInterval === null) return;

      try {
        const statusData = await this.fetchTaskStatus(this.executionId);

        if (statusData) {
          const parsedStatus = parseTaskStatus(statusData);

          // Log polling response with DEBUG_AI_CODE
          if (ENABLE_DEBUG_AI_CODE) {
            debugLog('POLLING_RESPONSE', this.executionId, 
              `Progress: ${statusData.progress}%, Completed: ${statusData.completedTasks || 0}/${statusData.totalTasks || 0}`);
          }

          //【P0 优化】使用进度管理器更新进度
          if (this.progressManager) {
            // 优先使用 completedTasks/totalTasks
            if (statusData.completedTasks !== undefined && statusData.totalTasks !== undefined) {
              this.progressManager.updateProgress(statusData.completedTasks);
            } else {
              // 降级使用 progress 百分比
              const totalTasks = this.questionList?.length * this.modelList?.length || 9;
              const completedTasks = Math.round((parsedStatus.progress / 100) * totalTasks);
              this.progressManager.updateProgress(completedTasks);
            }
          } else {
            // 降级使用原有逻辑
            this.setData({
              progress: parsedStatus.progress,
              statusText: parsedStatus.statusText
            });
          }

          // 检查任务是否完成
          const isCompleted = statusData.is_completed || parsedStatus.stage === 'completed';

          if (isCompleted) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;

            //【P0 优化】使用进度管理器标记完成
            if (this.progressManager) {
              this.progressManager.complete();
            }

            this.setData({
              isLoading: false
            });

            // 保存到本地存储
            const resultsData = statusData.detailed_results || statusData.results || [];
            wx.setStorageSync('latestTestResults_' + this.executionId, resultsData);
            wx.setStorageSync('latestTargetBrand', this.brandList[0] || '');
            wx.setStorageSync('latestCompetitorBrands', this.brandList.slice(1) || []);

            logger.debug('✅ 任务完成，测试结果已保存');

            // 跳转到结果页面
            wx.navigateTo({
              url: `/pages/results/results?executionId=${this.executionId}&brandName=${encodeURIComponent(this.brandList[0] || '')}`
            });
            return;
          }

          // 检查任务是否失败
          if (statusData.status === 'failed') {
            clearInterval(this.pollInterval);
            this.pollInterval = null;

            this.setData({
              isLoading: false
            });

            const errorMessage = statusData.error || '任务执行失败';
            wx.showToast({
              title: errorMessage,
              icon: 'none',
              duration: 3000
            });
            return;
          }

          // 检测进度停滞
          this.checkProgressStagnation(parsedStatus.progress);
        }
      } catch (error) {
        logger.error('轮询错误:', error);
        this.pollAttemptCount++;

        if (this.pollAttemptCount >= this.maxPollAttempts) {
          clearInterval(this.pollInterval);
          this.pollInterval = null;
          this.setData({
            isLoading: false
          });
          wx.showToast({
            title: '获取进度失败，请稍后重试',
            icon: 'none'
          });
        }
      }
    };

    // 开始轮询
    this.pollInterval = setInterval(performPoll, this.currentPollInterval);
  },'''

content = content.replace(old_polling, new_polling)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 2 完成：轮询逻辑已优化')
