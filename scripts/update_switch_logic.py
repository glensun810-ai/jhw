#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改切换逻辑：不清空选中状态，只控制生效范围
"""

with open('pages/index/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的 switchMarketTab 方法（清空选中状态）
old_switch_market_tab = '''  /**
   * 【新增】切换市场 Tab
   * 核心防御逻辑：切换市场时立即清空当前已绑定的 selectedModels
   */
  switchMarketTab: function(e) {
    const newMarket = e.currentTarget.dataset.market;
    const currentMarket = this.data.selectedMarketTab;
    
    // 如果点击的是当前已选中的 Tab，不做任何操作
    if (newMarket === currentMarket) {
      return;
    }
    
    console.log(`[市场切换] 从 ${currentMarket} 切换到 ${newMarket}`);
    
    // 核心防御：清空当前市场的所有选中状态
    const keyToClear = currentMarket === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
    const modelsToClear = Array.isArray(this.data[keyToClear]) ? this.data[keyToClear] : [];
    const clearedModels = modelsToClear.map(model => ({ ...model, checked: false }));
    
    this.setData({
      [keyToClear]: clearedModels,
      selectedMarketTab: newMarket
    });
    
    this.updateSelectedModelCount();
    this.saveCurrentInput();
    
    wx.showToast({
      title: `已切换到${newMarket === 'domestic' ? '国内' : '海外'}AI 平台`,
      icon: 'none',
      duration: 1500
    });
  },'''

# 新的 switchMarketTab 方法（保留选中状态）
new_switch_market_tab = '''  /**
   * 【新增】切换市场 Tab
   * 优化逻辑：切换市场时保留选中状态，只控制生效范围
   * - 国内 Tab 激活时：只提交国内平台的选中项
   * - 海外 Tab 激活时：只提交海外平台的选中项
   */
  switchMarketTab: function(e) {
    const newMarket = e.currentTarget.dataset.market;
    const currentMarket = this.data.selectedMarketTab;
    
    // 如果点击的是当前已选中的 Tab，不做任何操作
    if (newMarket === currentMarket) {
      return;
    }
    
    console.log(`[市场切换] 从 ${currentMarket} 切换到 ${newMarket}`);
    
    // 只切换 Tab，不清空选中状态
    this.setData({
      selectedMarketTab: newMarket
    });
    
    // 更新选中数量显示（只计算当前 Tab 的选中项）
    this.updateSelectedModelCount();
    this.saveCurrentInput();
    
    wx.showToast({
      title: `已切换到${newMarket === 'domestic' ? '国内' : '海外'}AI 平台`,
      icon: 'none',
      duration: 1500
    });
  },'''

if old_switch_market_tab in content:
    content = content.replace(old_switch_market_tab, new_switch_market_tab)
    print("✅ 已更新 switchMarketTab 方法（保留选中状态）")
else:
    print("❌ 未找到旧的 switchMarketTab 方法")

# 更新 updateSelectedModelCount 方法，只计算当前 Tab 的选中数
old_update_count = '''  updateSelectedModelCount: function() {
    // P3 修复：确保数据是数组
    const domesticAiModels = Array.isArray(this.data.domesticAiModels) ? this.data.domesticAiModels : [];
    const overseasAiModels = Array.isArray(this.data.overseasAiModels) ? this.data.overseasAiModels : [];

    const selectedDomesticCount = domesticAiModels.filter(model => model.checked).length;
    const selectedOverseasCount = overseasAiModels.filter(model => model.checked).length;
    const totalCount = selectedDomesticCount + selectedOverseasCount;
    this.setData({ selectedModelCount: totalCount });
  },'''

new_update_count = '''  updateSelectedModelCount: function() {
    // P3 修复：确保数据是数组
    const domesticAiModels = Array.isArray(this.data.domesticAiModels) ? this.data.domesticAiModels : [];
    const overseasAiModels = Array.isArray(this.data.overseasAiModels) ? this.data.overseasAiModels : [];

    const selectedDomesticCount = domesticAiModels.filter(model => model.checked).length;
    const selectedOverseasCount = overseasAiModels.filter(model => model.checked).length;
    
    // 【优化】只显示当前 Tab 的选中数量
    const currentMarket = this.data.selectedMarketTab;
    const displayCount = currentMarket === 'domestic' ? selectedDomesticCount : selectedOverseasCount;
    
    this.setData({ 
      selectedModelCount: displayCount,
      totalSelectedCount: selectedDomesticCount + selectedOverseasCount  // 保存总数用于提示
    });
  },'''

if old_update_count in content:
    content = content.replace(old_update_count, new_update_count)
    print("✅ 已更新 updateSelectedModelCount 方法（只显示当前 Tab 选中数）")
else:
    print("❌ 未找到旧的 updateSelectedModelCount 方法")

# 更新 getCurrentMarketSelectedModels 方法的注释
old_comment = '''  /**
   * 【新增】获取当前市场选中的模型 ID 列表
   * 提交给后端的 Payload 中，selectedModels 只包含当前 Tab 下被选中的模型 ID
   */'''

new_comment = '''  /**
   * 【核心逻辑】获取当前市场选中的模型 ID 列表
   * 提交给后端的 Payload 中，selectedModels 只包含当前 Tab 下被选中的模型 ID
   * 
   * 交互逻辑说明：
   * - 用户可以在国内和海外 Tab 下都选择平台
   * - 切换 Tab 时，已选择的平台不会被清空
   * - 但提交时，只提交当前激活 Tab 下的选中平台
   * - 例如：当前在"国内"Tab，即使"海外"Tab 有选中，也不会提交
   */'''

if old_comment in content:
    content = content.replace(old_comment, new_comment)
    print("✅ 已更新 getCurrentMarketSelectedModels 注释（说明交互逻辑）")
else:
    print("❌ 未找到注释")

with open('pages/index/index.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ JS 文件更新完成!")
print("\n📋 修改内容:")
print("  1. ✅ switchMarketTab: 切换时不清空选中状态")
print("  2. ✅ updateSelectedModelCount: 只显示当前 Tab 的选中数")
print("  3. ✅ getCurrentMarketSelectedModels: 只返回当前 Tab 的选中模型")
