#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 首页集成脚本 - 修改 pages/index/index.js

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/index/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加 InputManager 引用
old_imports = '''const diagnosisStorage = require('../../../services/diagnosisStorage');'''
new_imports = '''const diagnosisStorage = require('../../../services/diagnosisStorage');
const InputManager = require('../../../utils/inputManager');'''

content = content.replace(old_imports, new_imports)

# 2. 添加 inputManager 实例和新的 data 字段
old_data = '''    // 【P0 新增】上次诊断报告状态
    hasLastReport: false,
    lastReportTime: '',
    executionId: null,

    // 控制吸顶效果
    isSticky: false,'''

new_data = '''    // 【P0 新增】上次诊断报告状态
    hasLastReport: false,
    lastReportTime: '',
    executionId: null,

    //【P1 新增】输入保留功能
    hasLastInput: false,
    lastInputTime: '',
    lastInputSummary: '',

    // 控制吸顶效果
    isSticky: false,'''

content = content.replace(old_data, new_data)

# 3. 在 Page 对象中添加 inputManager 实例
old_page = '''Page({
  data: {'''

new_page = '''Page({
  /**
   * 【P1 新增】输入管理器
   */
  inputManager: null,

  data: {'''

content = content.replace(old_page, new_page)

# 4. 在 onLoad 中初始化 inputManager 并恢复输入
old_onload = '''  onLoad: function(options) {
    logger.debug('品牌 AI 雷达 - 页面加载完成');
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
  },'''

new_onload = '''  onLoad: function(options) {
    logger.debug('品牌 AI 雷达 - 页面加载完成');
    
    //【P1 新增】初始化输入管理器
    this.inputManager = new InputManager();
    
    //【P1 新增】恢复上次输入
    this.restoreLastInput();
    
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        this.startBrandTest();
      }, 1000);
    }
  },'''

content = content.replace(old_onload, new_onload)

# 5. 在 onShow 中也恢复输入（确保从其他页面返回时也能恢复）
old_onshow = '''  onShow: function() {
    // 检查是否有从配置管理页面传回的临时配置
    const app = getApp();
    if (app.globalData && app.globalData.tempConfig) {
      this.applyConfig(app.globalData.tempConfig);
      // 清除临时配置
      app.globalData.tempConfig = null;
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
  },'''

content = content.replace(old_onshow, new_onshow)

# 6. 添加 restoreLastInput 方法
old_method = '''  /**
   * 【P0 新增】检查并恢复上次诊断报告
   */
  checkAndRestoreLastDiagnosticReport: function() {'''

new_method = '''  /**
   * 【P1 新增】恢复上次输入
   */
  restoreLastInput: function() {
    if (!this.inputManager) return;
    
    const result = this.inputManager.restoreLastInput();
    
    if (result.success && result.data) {
      const input = result.data;
      
      logger.debug('[InputManager] 恢复上次输入:', input);
      
      // 恢复品牌名称
      this.setData({
        brandName: input.brandName || '',
        competitorBrands: input.competitorBrands || [],
        customQuestions: input.customQuestions || [],
        hasLastInput: true,
        lastInputTime: result.timeAgo,
        lastInputSummary: `${input.brandName || '品牌'} | ${input.competitorBrands?.length || 0}个竞品 | ${input.customQuestions?.length || 0}个问题`
      });
      
      // 恢复模型选择
      if (input.selectedModels) {
        this.restoreModelSelection(input.selectedModels);
      }
      
      wx.showToast({
        title: `已恢复${result.timeAgo}的输入`,
        icon: 'success',
        duration: 2000
      });
    }
  },

  /**
   * 【P1 新增】恢复模型选择
   */
  restoreModelSelection: function(selectedModels) {
    const domestic = selectedModels.domestic || [];
    const overseas = selectedModels.overseas || [];
    
    // 更新国内模型
    const updatedDomestic = this.data.domesticAiModels.map(model => ({
      ...model,
      checked: domestic.includes(model.name)
    }));
    
    // 更新海外模型
    const updatedOverseas = this.data.overseasAiModels.map(model => ({
      ...model,
      checked: overseas.includes(model.name)
    }));
    
    this.setData({
      domesticAiModels: updatedDomestic,
      overseasAiModels: updatedOverseas
    });
  },

  /**
   * 【P1 新增】保存当前输入
   */
  saveCurrentInput: function() {
    if (!this.inputManager) return;
    
    const input = {
      brandName: this.data.brandName,
      competitorBrands: this.data.competitorBrands,
      customQuestions: this.data.customQuestions,
      selectedModels: {
        domestic: this.data.domesticAiModels
          .filter(m => m.checked)
          .map(m => m.name),
        overseas: this.data.overseasAiModels
          .filter(m => m.checked)
          .map(m => m.name)
      }
    };
    
    this.inputManager.saveCurrentInput(input);
  },

  /**
   * 【P1 新增】清空输入
   */
  clearInput: function() {
    wx.showModal({
      title: '确认清空',
      content: '清空后需要重新输入品牌、竞品等信息，确定吗？',
      confirmText: '清空',
      cancelText: '取消',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (res.confirm) {
          // 清空输入管理器
          if (this.inputManager) {
            this.inputManager.clearTempInput();
          }
          
          // 重置页面数据
          this.setData({
            brandName: '',
            competitorBrands: [],
            customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}],
            hasLastInput: false,
            lastInputTime: '',
            lastInputSummary: ''
          });
          
          // 重置模型选择
          const resetDomestic = this.data.domesticAiModels.map(m => ({ ...m, checked: m.name === 'doubao' || m.name === 'qwen' || m.name === 'deepseek' }));
          const resetOverseas = this.data.overseasAiModels.map(m => ({ ...m, checked: m.name === 'chatgpt' }));
          
          this.setData({
            domesticAiModels: resetDomestic,
            overseasAiModels: resetOverseas
          });
          
          wx.showToast({
            title: '已清空输入',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 【P0 新增】检查并恢复上次诊断报告
   */
  checkAndRestoreLastDiagnosticReport: function() {'''

content = content.replace(old_method, new_method)

# 7. 修改输入事件处理，添加自动保存
old_brand_input = '''  onBrandNameInput: function(e) {
    this.setData({ brandName: e.detail.value });
  },'''

new_brand_input = '''  onBrandNameInput: function(e) {
    const value = e.detail.value;
    this.setData({ brandName: value });
    
    //【P1 新增】防抖保存 (500ms)
    clearTimeout(this.saveInputTimer);
    this.saveInputTimer = setTimeout(() => {
      this.saveCurrentInput();
    }, 500);
  },'''

content = content.replace(old_brand_input, new_brand_input)

# 8. 修改竞品输入事件
old_competitor_input = '''  onCompetitorInput: function(e) {
    this.setData({ currentCompetitor: e.detail.value });
  },'''

new_competitor_input = '''  onCompetitorInput: function(e) {
    const value = e.detail.value;
    this.setData({ currentCompetitor: value });
    
    //【P1 新增】防抖保存
    clearTimeout(this.saveInputTimer);
    this.saveInputTimer = setTimeout(() => {
      this.saveCurrentInput();
    }, 500);
  },'''

content = content.replace(old_competitor_input, new_brand_input)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 首页 JS 修改完成')
