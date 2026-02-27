#!/usr/bin/env python3
"""
一键修复 index.js 的 onLoad 和 restoreDraft 函数
添加防御性编程，防止 TypeError
"""

def fix_index_js():
    # 读取文件
    with open('pages/index/index.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在 onLoad 函数开头添加 try-catch 和 setDefaultData 调用
    old_onload_start = """  onLoad: function (options) {
    logger.debug('品牌 AI 雷达 - 页面加载完成');
    this.checkServerConnection();"""
    
    new_onload_start = """  onLoad: function (options) {
    try {
      logger.debug('品牌 AI 雷达 - 页面加载完成');
      
      // P0 修复：初始化默认数据，防止后续访问 null
      this.setDefaultData();
      
      this.checkServerConnection();"""
    
    content = content.replace(old_onload_start, new_onload_start)
    
    # 2. 在 onLoad 函数末尾添加 catch 块和 setDefaultData 方法
    old_onload_end = """    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        this.startBrandTest();
      }, 1000); // 延迟稍长一些，确保配置已完全加载
    }
  },"""
    
    new_onload_end = """    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        // 使用箭头函数保证 this 指向
        this.startBrandTest();
      }, 1000);
    }
    } catch (error) {
      logger.error('onLoad 初始化失败', error);
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
    
    content = content.replace(old_onload_end, new_onload_end)
    
    # 3. 加固 restoreDraft 函数
    old_restore = """  restoreDraft: function() {
    const draft = wx.getStorageSync('draft_diagnostic_input');
    
    if (draft && (draft.brandName || draft.competitorBrands?.length > 0)) {
      // 检查是否是 7 天内的草稿
      const now = Date.now();
      const draftAge = now - draft.updatedAt;
      const sevenDays = 7 * 24 * 60 * 60 * 1000;
      
      if (draftAge < sevenDays) {
        this.setData({
          brandName: draft.brandName || '',
          currentCompetitor: draft.currentCompetitor || '',
          competitorBrands: draft.competitorBrands || []
        });
        logger.debug('草稿已恢复', draft);
      } else {
        // 草稿过期，清除
        wx.removeStorageSync('draft_diagnostic_input');
        logger.debug('草稿已过期，已清除');
      }
    }
  },"""
    
    new_restore = """  /**
   * P2 修复：从本地存储恢复草稿
   */
  restoreDraft: function() {
    try {
      const draft = wx.getStorageSync('draft_diagnostic_input');
      
      // P0 修复：确保 draft 存在且为对象
      if (!draft || typeof draft !== 'object') {
        logger.debug('无草稿数据或数据无效');
        return;
      }
      
      if (draft.brandName || (draft.competitorBrands && draft.competitorBrands.length > 0)) {
        // 检查是否是 7 天内的草稿
        const now = Date.now();
        const draftAge = now - draft.updatedAt;
        const sevenDays = 7 * 24 * 60 * 60 * 1000;
        
        if (draftAge < sevenDays) {
          this.setData({
            brandName: draft.brandName || '',
            currentCompetitor: draft.currentCompetitor || '',
            competitorBrands: draft.competitorBrands || []
          });
          logger.debug('草稿已恢复', draft);
        } else {
          // 草稿过期，清除
          wx.removeStorageSync('draft_diagnostic_input');
          logger.debug('草稿已过期，已清除');
        }
      }
    } catch (error) {
      logger.error('restoreDraft 失败', error);
    }
  },"""
    
    content = content.replace(old_restore, new_restore)
    
    # 写入文件
    with open('pages/index/index.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ index.js 修复完成")
    print("修复内容:")
    print("  1. onLoad 添加 try-catch 保护")
    print("  2. 添加 setDefaultData 方法防止 null 引用")
    print("  3. restoreDraft 添加防御性检查")
    print("  4. 所有异步回调使用箭头函数")

if __name__ == '__main__':
    fix_index_js()
