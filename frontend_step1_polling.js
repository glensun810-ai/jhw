#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 步骤 1: 修改 detail/index.js 轮询逻辑

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 data 中添加实时统计和聚合结果字段
old_data = '''    //【P0 新增】进度解释文案
    progressExplanation: '',
    //【P0 新增】网络质量
    networkQuality: 'unknown',
    networkQualityText: '',
    //【P0 新增】订阅状态
    isSubscribed: false
  },'''

new_data = '''    //【P0 新增】进度解释文案
    progressExplanation: '',
    //【P0 新增】网络质量
    networkQuality: 'unknown',
    networkQualityText: '',
    //【P0 新增】订阅状态
    isSubscribed: false,
    
    //【阶段 1】实时统计
    realtimeStats: null,
    brandRankings: [],
    realtimeSov: 0,
    realtimeSentiment: 0,
    
    //【阶段 2】聚合结果
    aggregatedResults: null,
    healthScore: 0,
    detailedResults: []
  },'''

content = content.replace(old_data, new_data)

# 2. 修改轮询逻辑处理实时数据
old_polling = '''          //【P0 优化】使用进度管理器更新进度
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

new_polling = '''          //【P0 优化】使用进度管理器更新进度
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
          }
          
          //【阶段 1】处理实时统计
          if (statusData.realtimeStats) {
            this.setData({
              realtimeStats: statusData.realtimeStats,
              brandRankings: statusData.brandRankings || [],
              realtimeSov: statusData.sov || 0,
              realtimeSentiment: statusData.avgSentiment || 0
            });
            console.log('📊 实时统计更新:', statusData.realtimeStats);
          }
          
          //【阶段 2】处理聚合结果
          if (statusData.aggregatedResults) {
            this.setData({
              aggregatedResults: statusData.aggregatedResults,
              healthScore: statusData.healthScore || 0,
              detailedResults: statusData.detailedResults || []
            });
            console.log('📈 聚合结果更新:', statusData.aggregatedResults);
          }'''

content = content.replace(old_polling, new_polling)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 步骤 1 完成：轮询逻辑已修改')
