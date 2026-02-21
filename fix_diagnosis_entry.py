#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修复首页诊断结果入口问题

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 data 中添加诊断完成状态
old_data = '''    //【P1 新增】输入保留功能
    hasLastInput: false,
    lastInputTime: '',
    lastInputSummary: '',

    // 控制吸顶效果
    isSticky: false,'''

new_data = '''    //【P1 新增】输入保留功能
    hasLastInput: false,
    lastInputTime: '',
    lastInputSummary: '',

    //【P0 新增】诊断完成状态
    hasCompletedDiagnosis: false,
    completedDiagnosisData: null,

    // 控制吸顶效果
    isSticky: false,'''

content = content.replace(old_data, new_data)

# 2. 在 onShow 中检查诊断完成状态
old_onshow = '''  onShow: function() {
    // 检查是否有从配置管理页面传回的临时配置
    const app = getApp();
    if (app.globalData && app.globalData.tempConfig) {
      this.applyConfig(app.globalData.tempConfig);
      // 清除临时配置
      app.globalData.tempConfig = null;
    }

    //【P1 新增】恢复上次输入（确保从其他页面返回时也能恢复）
    if (!this.data.hasLastInput) {
      this.restoreLastInput();
    }

    // 【P0 修复】检查本地持久化的诊断结果
    this.checkAndRestoreLastDiagnosticReport();
  },'''

new_onshow = '''  onShow: function() {
    // 检查是否有从配置管理页面传回的临时配置
    const app = getApp();
    if (app.globalData && app.globalData.tempConfig) {
      this.applyConfig(app.globalData.tempConfig);
      // 清除临时配置
      app.globalData.tempConfig = null;
    }

    //【P1 新增】恢复上次输入（确保从其他页面返回时也能恢复）
    if (!this.data.hasLastInput) {
      this.restoreLastInput();
    }

    // 【P0 修复】检查本地持久化的诊断结果
    this.checkAndRestoreLastDiagnosticReport();
    
    //【P0 新增】检查是否有完成的诊断
    this.checkCompletedDiagnosis();
  },'''

content = content.replace(old_onshow, new_onshow)

# 3. 添加 checkCompletedDiagnosis 方法
old_method = '''  /**
   * 【P0 新增】检查并恢复上次诊断报告
   */
  checkAndRestoreLastDiagnosticReport: function() {'''

new_method = '''  /**
   * 【P0 新增】检查是否有完成的诊断
   */
  checkCompletedDiagnosis: function() {
    // 检查全局存储中的诊断完成状态
    const app = getApp();
    const lastReport = app.globalData.lastReport;
    
    if (lastReport && lastReport.executionId && lastReport.dashboard) {
      console.log('[首页] 发现完成的诊断:', lastReport.executionId);
      
      const dashboard = lastReport.dashboard;
      const summary = dashboard.summary || {};
      
      this.setData({
        hasCompletedDiagnosis: true,
        completedDiagnosisData: {
          executionId: lastReport.executionId,
          brandName: summary.brandName || lastReport.brandName || '品牌',
          healthScore: summary.healthScore || 0,
          sov: summary.sov || summary.sov_value || 0,
          avgSentiment: summary.avgSentiment || summary.sentiment_value || 0,
          completedTime: this.formatCompletedTime(Date.now())
        }
      });
    } else {
      // 没有完成的诊断，检查本地存储
      const storedReport = wx.getStorageSync('last_diagnostic_report');
      if (storedReport && storedReport.executionId) {
        const dashboard = storedReport.dashboard || storedReport.reportData;
        const summary = dashboard?.summary || {};
        
        this.setData({
          hasCompletedDiagnosis: true,
          completedDiagnosisData: {
            executionId: storedReport.executionId,
            brandName: summary.brandName || storedReport.brandName || '品牌',
            healthScore: summary.healthScore || 0,
            sov: summary.sov || summary.sov_value || 0,
            avgSentiment: summary.avgSentiment || summary.sentiment_value || 0,
            completedTime: this.formatCompletedTime(storedReport.savedAt || Date.now())
          }
        });
      }
    }
  },

  /**
   * 【P0 新增】格式化完成时间
   */
  formatCompletedTime: function(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `完成于 ${hours}:${minutes}`;
  },

  /**
   * 【P0 新增】查看诊断报告
   */
  viewCompletedReport: function() {
    if (!this.data.completedDiagnosisData) {
      wx.showToast({
        title: '暂无诊断报告',
        icon: 'none'
      });
      return;
    }
    
    wx.navigateTo({
      url: '/pages/report/dashboard/index',
      success: () => {
        console.log('[首页] 跳转到诊断报告页面');
      },
      fail: (err) => {
        console.error('[首页] 跳转失败:', err);
        wx.showToast({
          title: '跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 【P0 新增】重新诊断
   */
  retryDiagnosis: function() {
    const data = this.data.completedDiagnosisData;
    
    wx.showModal({
      title: '确认重新诊断',
      content: `重新诊断将覆盖 ${data?.brandName || '当前'} 的诊断结果，是否继续？`,
      confirmText: '开始诊断',
      cancelText: '取消',
      confirmColor: '#00F5A0',
      success: (res) => {
        if (res.confirm) {
          // 清空完成的诊断状态
          this.setData({
            hasCompletedDiagnosis: false,
            completedDiagnosisData: null
          });
          
          // 开始新的诊断
          this.startBrandTest();
        }
      }
    });
  },

  /**
   * 【P0 新增】检查并恢复上次诊断报告
   */
  checkAndRestoreLastDiagnosticReport: function() {'''

content = content.replace(old_method, new_method)

# 4. 修改 startBrandTest 方法，在启动时清空完成状态
old_start = '''  startBrandTest: function() {
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入品牌名称', icon: 'error' });
      return;
    }'''

new_start = '''  startBrandTest: function() {
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入品牌名称', icon: 'error' });
      return;
    }
    
    // 清空之前的诊断完成状态
    this.setData({
      hasCompletedDiagnosis: false,
      completedDiagnosisData: null
    });'''

content = content.replace(old_start, new_start)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加诊断完成状态检查和入口')
