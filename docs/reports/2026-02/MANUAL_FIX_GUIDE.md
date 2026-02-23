# index.js 手动修复指南

由于自动替换不可靠，请手动执行以下修复：

## 1. onLoad 函数修复（第 130-145 行）

**原代码**:
```javascript
onLoad: function (options) {
  console.log('品牌 AI 雷达 - 页面加载完成');
  this.checkServerConnection();
  this.updateSelectedModelCount();
  this.updateSelectedQuestionCount();

  // 检查是否需要立即启动快速搜索
  if (options && options.quickSearch === 'true') {
    setTimeout(() => {
      this.startBrandTest();
    }, 1000);
  }
},
```

**修改为**:
```javascript
onLoad: function (options) {
  try {
    console.log('品牌 AI 雷达 - 页面加载完成');
    
    // P0 修复：初始化默认数据，防止后续访问 null
    this.setDefaultData();
    
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      setTimeout(() => {
        this.startBrandTest();
      }, 1000);
    }
  } catch (error) {
    console.error('onLoad 初始化失败', error);
    this.setDefaultData();
  }
},

/**
 * P0 修复：设置默认数据，防止 null 引用
 */
setDefaultData: function() {
  const defaultConfig = {
    estimate: {
      duration: '30s',
      steps: 5
    },
    brandName: '',
    competitorBrands: [],
    customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
  };

  if (!this.data.config || !this.data.config.estimate) {
    this.setData({
      config: defaultConfig
    });
  }
},
```

## 2. restoreDraft 函数修复（约第 360 行）

**原代码**:
```javascript
restoreDraft: function() {
  const draft = wx.getStorageSync('draft_diagnostic_input');
  
  if (draft && (draft.brandName || draft.competitorBrands?.length > 0)) {
    const now = Date.now();
    const draftAge = now - draft.updatedAt;
    const sevenDays = 7 * 24 * 60 * 60 * 1000;
    
    if (draftAge < sevenDays) {
      this.setData({
        brandName: draft.brandName || '',
        currentCompetitor: draft.currentCompetitor || '',
        competitorBrands: draft.competitorBrands || []
      });
      console.log('草稿已恢复', draft);
    } else {
      wx.removeStorageSync('draft_diagnostic_input');
      console.log('草稿已过期，已清除');
    }
  }
},
```

**修改为**:
```javascript
restoreDraft: function() {
  try {
    const draft = wx.getStorageSync('draft_diagnostic_input');
    
    // P0 修复：确保 draft 存在且为对象
    if (!draft || typeof draft !== 'object') {
      console.log('无草稿数据或数据无效');
      return;
    }
    
    if (draft.brandName || (draft.competitorBrands && draft.competitorBrands.length > 0)) {
      const now = Date.now();
      const draftAge = now - draft.updatedAt;
      const sevenDays = 7 * 24 * 60 * 60 * 1000;
      
      if (draftAge < sevenDays) {
        this.setData({
          brandName: draft.brandName || '',
          currentCompetitor: draft.currentCompetitor || '',
          competitorBrands: draft.competitorBrands || []
        });
        console.log('草稿已恢复', draft);
      } else {
        wx.removeStorageSync('draft_diagnostic_input');
        console.log('草稿已过期，已清除');
      }
    }
  } catch (error) {
    console.error('restoreDraft 失败', error);
  }
},
```

## 验证

修复后执行：
```bash
node -c pages/index/index.js
```

应该显示无错误。
