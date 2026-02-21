#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 添加 useLastInput 方法

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加 useLastInput 方法
old_method = '''  /**
   * 【P1 新增】清空输入
   */
  clearInput: function() {'''

new_method = '''  /**
   * 【P1 新增】使用上次输入
   */
  useLastInput: function() {
    // 已经有输入，直接开始诊断
    wx.showToast({
      title: '已加载上次输入',
      icon: 'success'
    });
    
    // 滚动到诊断按钮
    wx.pageScrollTo({
      scrollTop: 1000,
      duration: 300
    });
  },

  /**
   * 【P1 新增】清空输入
   */
  clearInput: function() {'''

content = content.replace(old_method, new_method)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 添加 useLastInput 方法')
