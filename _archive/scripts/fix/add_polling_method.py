#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加 updatePollingInterval 方法
old_method = '''  /**
   * 【P0 新增】更新知识提示
   */
  updateKnowledgeTip: function() {'''

new_method = '''  /**
   * 【P0 重构】更新轮询间隔
   */
  updatePollingInterval: function(progress) {
    // 进度快时加快轮询，给用户流畅感
    if (progress >= this.pollingConfig.fastProgress.threshold) {
      return this.pollingConfig.fastProgress.interval;
    }
    
    // 进度慢时适当放慢，减少服务器压力
    if (progress < this.pollingConfig.slowProgress.threshold) {
      return this.pollingConfig.slowProgress.interval;
    }
    
    return this.pollingConfig.baseInterval;
  },

  /**
   * 【P0 新增】更新知识提示
   */
  updateKnowledgeTip: function() {'''

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加 updatePollingInterval 方法')
