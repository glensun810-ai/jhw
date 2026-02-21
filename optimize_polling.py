#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换轮询配置
old_config = '''    // 添加轮询间隔管理
    this.currentPollInterval = 3000; // 初始间隔 3 秒
    this.pollAttemptCount = 0; // 轮询尝试计数
    this.maxPollAttempts = 100; // 最大轮询次数'''

new_config = '''    //【P0 重构】轮询间隔管理 - 固定间隔 + 智能调整
    this.pollingConfig = {
      baseInterval: 2000,  // 基础 2 秒
      fastProgress: { threshold: 80, interval: 1000 },  // 80% 后 1 秒一次
      slowProgress: { threshold: 20, interval: 3000 }   // 20% 前 3 秒一次
    };
    this.currentPollInterval = this.pollingConfig.baseInterval;
    this.pollAttemptCount = 0;
    this.maxPollAttempts = 100;'''

content = content.replace(old_config, new_config)

# 2. 替换动态调整逻辑
old_logic = '''          // 动态调整轮询间隔基于进度
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
          }'''

new_logic = '''          //【P0 重构】智能调整轮询间隔 - 进度快时加快轮询
          const newInterval = this.updatePollingInterval(statusData.progress);
          
          if (newInterval !== this.currentPollInterval) {
            this.currentPollInterval = newInterval;
            clearInterval(this.pollInterval);
            this.pollInterval = setInterval(performPoll, this.currentPollInterval);
            return;
          }'''

content = content.replace(old_logic, new_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已优化轮询间隔设计')
ENDSCRIPT