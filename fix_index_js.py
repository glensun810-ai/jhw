#!/usr/bin/env python3
"""
修复 index.js 的 onLoad 函数，添加防御性编程
"""

import re

# 读取文件
with open('pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复 onLoad 函数，添加 try-catch 和 setDefaultData 调用
old_onload = """  onLoad: function (options) {
    console.log('品牌 AI 雷达 - 页面加载完成');
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        this.startBrandTest();
      }, 1000); // 延迟稍长一些，确保配置已完全加载
    }
  },"""

new_onload = """  onLoad: function (options) {
    try {
      console.log('品牌 AI 雷达 - 页面加载完成');
      
      // P0 修复：初始化默认数据，防止后续访问 null
      this.setDefaultData();
      
      this.checkServerConnection();
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();

      // 检查是否需要立即启动快速搜索
      if (options && options.quickSearch === 'true') {
        // 延迟执行，确保页面已完全加载
        setTimeout(() => {
          // 使用箭头函数保证 this 指向
          this.startBrandTest();
        }, 1000);
      }
    } catch (error) {
      console.error('onLoad 初始化失败', error);
      // 确保即使出错也能显示基本界面
      this.setDefaultData();
    }
  },

  /**
   * P0 修复：设置默认数据，防止 null 引用
   */
  setDefaultData: function() {
    // 确保 config 有默认值
    const defaultConfig = {
      estimate: {
        duration: '30s',
        steps: 5
      },
      brandName: '',
      competitorBrands: [],
      customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
    };

    // 只有在 data 中不存在时才设置默认值
    if (!this.data.config || !this.data.config.estimate) {
      this.setData({
        config: defaultConfig
      });
    }
  },"""

content = content.replace(old_onload, new_onload)

# 2. 加固 restoreDraft 函数，确保初始数据
old_restore = """  restoreDraft: function() {
    const draft = wx.getStorageSync('draft_diagnostic_input');
    
    if (draft && (draft.brandName || draft.competitorBrands?.length > 0)) {"""

new_restore = """  restoreDraft: function() {
    try {
      const draft = wx.getStorageSync('draft_diagnostic_input');
      
      // P0 修复：确保 draft 存在且为对象
      if (!draft || typeof draft !== 'object') {
        console.log('无草稿数据或数据无效');
        return;
      }
      
      if (draft.brandName || (draft.competitorBrands && draft.competitorBrands.length > 0)) {"""

content = content.replace(old_restore, new_restore)

# 3. 修复 restoreDraft 结尾
old_restore_end = """      }
    }
  },

  addCompetitor: function() {"""

new_restore_end = """        console.log('草稿已恢复', draft);
      } else {
        // 草稿过期，清除
        wx.removeStorageSync('draft_diagnostic_input');
        console.log('草稿已过期，已清除');
      }
    } catch (error) {
      console.error('restoreDraft 失败', error);
    }
  },

  addCompetitor: function() {"""

content = content.replace(old_restore_end, new_restore_end)

# 写入文件
with open('pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ index.js 修复完成")
