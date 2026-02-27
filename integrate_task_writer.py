#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 集成 TaskResultWriter 到 detail 页面

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加 TaskResultWriter 引用
old_imports = '''const ProgressManager = require('../../utils/progressManager');'''
new_imports = '''const ProgressManager = require('../../utils/progressManager');
const TaskResultWriter = require('../../utils/taskResultWriter');'''

content = content.replace(old_imports, new_imports)

# 2. 添加 taskResultWriter 实例
old_instances = '''  /**
   * 【P0 新增】进度管理器
   */
  progressManager: null,

  data: {'''

new_instances = '''  /**
   * 【P0 新增】进度管理器
   */
  progressManager: null,
  
  /**
   * 【P0 新增】任务结果写入器
   */
  taskResultWriter: null,

  data: {'''

content = content.replace(old_instances, new_instances)

# 3. 在 onLoad 中初始化写入器
old_onload = '''      //【P0 新增】初始化进度管理器
      const questionCount = this.customQuestion ? 1 : 3;
      const modelCount = this.modelNames.length;
      this.progressManager = new ProgressManager(this);
      this.progressManager.init(questionCount, modelCount);

      // 启动轮询 (不再使用 startProgressAnimation)
      this.startPolling();'''

new_onload = '''      //【P0 新增】初始化进度管理器
      const questionCount = this.customQuestion ? 1 : 3;
      const modelCount = this.modelNames.length;
      this.progressManager = new ProgressManager(this);
      this.progressManager.init(questionCount, modelCount);
      
      //【P0 新增】初始化任务结果写入器
      this.taskResultWriter = new TaskResultWriter(this, this.executionId);

      // 启动轮询 (不再使用 startProgressAnimation)
      this.startPolling();'''

content = content.replace(old_onload, new_onload)

# 4. 在轮询中实时写入结果
old_polling_check = '''          //【P0 优化】使用进度管理器更新进度
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
          }'''

new_polling_check = '''          //【P0 优化】使用进度管理器更新进度
          if (this.progressManager) {
            // 优先使用 completedTasks/totalTasks
            if (statusData.completedTasks !== undefined && statusData.totalTasks !== undefined) {
              this.progressManager.updateProgress(statusData.completedTasks);
              
              //【P0 新增】实时写入已完成的任务结果
              if (statusData.completedTaskList && Array.isArray(statusData.completedTaskList)) {
                this.taskResultWriter.writeBatch(statusData.completedTaskList);
              }
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
          }'''

content = content.replace(old_polling_check, new_polling_check)

# 5. 在任务完成时使用写入器的结果
old_complete = '''            // 保存到本地存储
            const resultsData = statusData.detailed_results || statusData.results || [];
            wx.setStorageSync('latestTestResults_' + this.executionId, resultsData);
            wx.setStorageSync('latestTargetBrand', this.brandList[0] || '');
            wx.setStorageSync('latestCompetitorBrands', this.brandList.slice(1) || []);

            logger.debug('✅ 任务完成，测试结果已保存');'''

new_complete = '''            //【P0 优化】使用写入器的结果（包含所有实时写入的任务）
            const resultsData = this.taskResultWriter.getAllResults();
            
            // 保存到本地存储
            wx.setStorageSync('latestTestResults_' + this.executionId, resultsData);
            wx.setStorageSync('latestTargetBrand', this.brandList[0] || '');
            wx.setStorageSync('latestCompetitorBrands', this.brandList.slice(1) || []);

            logger.debug('✅ 任务完成，测试结果已保存，总结果数:', resultsData.length);'''

content = content.replace(old_complete, new_complete)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ TaskResultWriter 已集成')
