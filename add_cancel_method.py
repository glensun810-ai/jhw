#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加取消诊断方法
old_method = '''  /**
   * 【P2-7 新增】生成进度解释文案
   */
  generateProgressExplanation: function(parsedStatus, stageDesc) {'''

new_method = '''  /**
   * 【P2-8 新增】取消诊断功能
   */
  cancelDiagnosis: function() {
    wx.showModal({
      title: '确认取消诊断',
      content: '取消后当前诊断将不会保存，确定要取消吗？',
      confirmText: '确定取消',
      cancelText: '继续诊断',
      confirmColor: '#F44336',
      success: (res) => {
        if (res.confirm) {
          // 停止轮询
          if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
          }
          
          // 返回首页
          wx.redirectTo({
            url: '/pages/index/index',
            success: () => {
              wx.showToast({
                title: '已取消诊断',
                icon: 'success'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 【P2-7 新增】生成进度解释文案
   */
  generateProgressExplanation: function(parsedStatus, stageDesc) {'''

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加取消诊断方法')
