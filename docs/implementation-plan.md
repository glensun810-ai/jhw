# AI 品牌诊断系统 - 产品架构优化实施方案

**文档版本**: v1.0  
**创建日期**: 2026-03-10  
**文档类型**: 实施规划  
**总预计工时**: 12.5 人天  

---

## 一、实施总览

### 1.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 1        Phase 2        Phase 3        Phase 4       Phase 5    │
│  基础重构       记录增强       统计分析       个人中心      测试上线   │
│  2 天           3 天           5 天           1.5 天        1 天        │
│  P0             P0             P1             P1            P0         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 里程碑计划

| 里程碑 | 日期 | 交付物 | 验收标准 |
|-------|------|--------|---------|
| M1: 基础重构完成 | T+2 | TabBar 更新、导航重构 | 4 个 Tab 正常切换 |
| M2: 记录增强完成 | T+5 | 诊断记录 + 报告整合 | 详情页展示完整报告 |
| M3: 统计分析完成 | T+10 | 4 个分析维度页面 | 数据可视化正常 |
| M4: 个人中心完成 | T+11.5 | 收藏整合完成 | 收藏功能正常 |
| M5: 正式上线 | T+12.5 | 全量发布 | 无 P0/P1 级 Bug |

---

## 二、Phase 1: 基础重构（2 天）

### 1.1 任务清单

| 任务 ID | 任务名称 | 优先级 | 工时 | 负责人 | 状态 |
|--------|---------|--------|------|--------|------|
| T1.1 | TabBar 配置更新 | P0 | 0.5h | 待分配 | ⏳ |
| T1.2 | 新增 analytics 页面骨架 | P0 | 1h | 待分配 | ⏳ |
| T1.3 | 导航服务重构 | P0 | 2h | 待分配 | ⏳ |
| T1.4 | 全局状态管理 | P0 | 2h | 待分配 | ⏳ |
| T1.5 | Tab 切换动画优化 | P1 | 1.5h | 待分配 | ⏳ |
| T1.6 | 旧页面兼容处理 | P1 | 1h | 待分配 | ⏳ |

### 1.2 详细实施步骤

#### T1.1: TabBar 配置更新（0.5h）

**文件**: `app.json`

**变更内容**:
```json
{
  "pages": [
    "pages/index/index",
    "pages/history/history",
    "pages/history-detail/history-detail",
    // 新增页面
    "pages/analytics/analytics",
    "pages/analytics/brand-compare/brand-compare",
    "pages/analytics/trend-analysis/trend-analysis",
    "pages/analytics/platform-compare/platform-compare",
    "pages/analytics/question-analysis/question-analysis",
    // ... 其他页面
  ],
  "tabBar": {
    "color": "#999999",
    "selectedColor": "#4A7BFF",
    "backgroundColor": "#121826",
    "borderStyle": "black",
    "list": [
      {
        "pagePath": "pages/index/index",
        "text": "AI 搜索",
        "iconPath": "assets/tabbar/search.png",
        "selectedIconPath": "assets/tabbar/search-active.png"
      },
      {
        "pagePath": "pages/history/history",
        "text": "诊断记录",
        "iconPath": "assets/tabbar/record.png",
        "selectedIconPath": "assets/tabbar/record-active.png"
      },
      {
        "pagePath": "pages/analytics/analytics",
        "text": "统计分析",
        "iconPath": "assets/tabbar/analytics.png",
        "selectedIconPath": "assets/tabbar/analytics-active.png"
      },
      {
        "pagePath": "pages/user-profile/user-profile",
        "text": "我的",
        "iconPath": "assets/tabbar/profile.png",
        "selectedIconPath": "assets/tabbar/profile-active.png"
      }
    ]
  }
}
```

**验收标准**:
- [ ] 4 个 Tab 正常显示
- [ ] 点击 Tab 可正常切换
- [ ] 选中状态图标正确

---

#### T1.2: 新增 analytics 页面骨架（1h）

**新建文件**:

**1. `pages/analytics/analytics.js`**
```javascript
/**
 * 统计分析 - 主页面
 * 功能：多维度数据分析入口
 */
Page({
  data: {
    // 分析维度 Tab
  analysisTabs: [
      { id: 'brand', name: '品牌对比', icon: '📊' },
      { id: 'trend', name: '趋势分析', icon: '📈' },
      { id: 'platform', name: 'AI 平台', icon: '🤖' },
      { id: 'question', name: '问题聚合', icon: '❓' }
    ],
    currentTab: 'brand',
    loading: false,
    hasData: false
  },

  onLoad: function(options) {
    console.log('统计分析页面加载');
    this.initPage();
  },

  onShow: function() {
    // 每次显示时检查数据
    this.checkDataStatus();
  },

  onPullDownRefresh: function() {
    this.refreshData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 初始化页面
   */
  async initPage() {
    try {
      this.setData({ loading: true });
      
      // 检查是否有足够的诊断数据
      const hasEnoughData = await this.checkDiagnosisCount();
      
      if (!hasEnoughData) {
        this.setData({ 
          hasData: false,
          loading: false 
        });
        return;
      }
      
      // 加载默认分析数据
      await this.loadAnalysisData('brand');
      
      this.setData({ 
        hasData: true,
        loading: false 
      });
    } catch (error) {
      console.error('初始化失败:', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 检查诊断记录数量
   */
  async checkDiagnosisCount() {
    return new Promise((resolve) => {
      const history = wx.getStorageSync('diagnosis_history') || [];
      resolve(history.length >= 1); // 至少 1 条记录
    });
  },

  /**
   * 切换分析维度
   */
  onTabChange: function(e) {
    const { tabId } = e.currentTarget.dataset;
    
    if (tabId === this.data.currentTab) return;
    
    this.setData({ currentTab: tabId });
    this.loadAnalysisData(tabId);
  },

  /**
   * 加载分析数据
   */
  async loadAnalysisData(tabId) {
    this.setData({ loading: true });
    
    try {
      // 根据 tabId 加载不同数据
      switch (tabId) {
        case 'brand':
          await this.loadBrandCompare();
          break;
        case 'trend':
          await this.loadTrendAnalysis();
          break;
        case 'platform':
          await this.loadPlatformCompare();
          break;
        case 'question':
          await this.loadQuestionAnalysis();
          break;
      }
    } catch (error) {
      console.error(`加载${tabId}数据失败:`, error);
    } finally {
      this.setData({ loading: false });
    }
  },

  /**
   * 刷新数据
   */
  async refreshData() {
    await this.loadAnalysisData(this.data.currentTab);
  },

  /**
   * 检查数据状态
   */
  checkDataStatus() {
    // 实现数据 freshness 检查
  },

  /**
   * 跳转到子页面
   */
  navigateToDetail: function(e) {
    const { type } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/analytics/${type}/${type}`
    });
  }
});
```

**2. `pages/analytics/analytics.wxml`**
```xml
<view class="analytics-container">
  <!-- 空状态 -->
  <view wx:if="{{!hasData}}" class="empty-state">
    <image class="empty-icon" src="/assets/icons/empty-analytics.png" />
    <text class="empty-title">暂无分析数据</text>
    <text class="empty-desc">完成至少 1 次品牌诊断后即可查看分析报告</text>
    <button class="go-diagnose" bindtap="goToDiagnosis">去诊断</button>
  </view>

  <!-- 正常内容 -->
  <view wx:else class="content">
    <!-- 顶部 Tab -->
    <view class="analysis-tabs">
      <view 
        wx:for="{{analysisTabs}}" 
        wx:key="id"
        class="tab-item {{currentTab === item.id ? 'active' : ''}}"
        data-tab-id="{{item.id}}"
        bindtap="onTabChange"
      >
        <text class="tab-icon">{{item.icon}}</text>
        <text class="tab-name">{{item.name}}</text>
      </view>
    </view>

    <!-- 内容区域 -->
    <scroll-view class="content-scroll" scroll-y enhanced show-scrollbar="{{false}}">
      <view class="content-wrapper">
        <!-- 品牌对比 -->
        <view wx:if="{{currentTab === 'brand'}}" class="tab-content">
          <view class="card">
            <view class="card-header">
              <text class="card-title">品牌综合评分对比</text>
            </view>
            <view class="card-body">
              <!-- 图表占位 -->
              <view class="chart-placeholder">
                <text>品牌评分柱状图</text>
              </view>
            </view>
          </view>
        </view>

        <!-- 趋势分析 -->
        <view wx:if="{{currentTab === 'trend'}}" class="tab-content">
          <view class="card">
            <view class="card-header">
              <text class="card-title">品牌声量趋势</text>
            </view>
            <view class="card-body">
              <view class="chart-placeholder">
                <text>声量趋势折线图</text>
              </view>
            </view>
          </view>
        </view>

        <!-- AI 平台对比 -->
        <view wx:if="{{currentTab === 'platform'}}" class="tab-content">
          <view class="card">
            <view class="card-header">
              <text class="card-title">不同 AI 平台认知差异</text>
            </view>
            <view class="card-body">
              <view class="chart-placeholder">
                <text>平台对比雷达图</text>
              </view>
            </view>
          </view>
        </view>

        <!-- 问题聚合 -->
        <view wx:if="{{currentTab === 'question'}}" class="tab-content">
          <view class="card">
            <view class="card-header">
              <text class="card-title">高频问题 TOP10</text>
            </view>
            <view class="card-body">
              <view class="question-list">
                <view class="question-item">
                  <text class="question-rank">1</text>
                  <text class="question-text">品牌知名度如何</text>
                  <text class="question-count">156 次</text>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>

  <!-- 加载状态 -->
  <view wx:if="{{loading}}" class="loading-mask">
    <view class="loading-spinner"></view>
    <text>加载中...</text>
  </view>
</view>
```

**3. `pages/analytics/analytics.wxss`**
```scss
.analytics-container {
  min-height: 100vh;
  background: #f5f6f7;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
  
  .empty-icon {
    width: 200rpx;
    height: 200rpx;
    margin-bottom: 40rpx;
  }
  
  .empty-title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 20rpx;
  }
  
  .empty-desc {
    font-size: 28rpx;
    color: #999;
    margin-bottom: 60rpx;
  }
  
  .go-diagnose {
    width: 300rpx;
    height: 88rpx;
    line-height: 88rpx;
    background: linear-gradient(135deg, #4A7BFF, #6B94FF);
    color: #fff;
    border-radius: 44rpx;
  }
}

.analysis-tabs {
  display: flex;
  background: #fff;
  padding: 20rpx 30rpx;
  border-bottom: 1rpx solid #eee;
  
  .tab-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-right: 60rpx;
    padding: 10rpx 20rpx;
    border-radius: 12rpx;
    transition: all 0.3s;
    
    &.active {
      background: rgba(74, 123, 255, 0.1);
      
      .tab-name {
        color: #4A7BFF;
        font-weight: 600;
      }
    }
    
    .tab-icon {
      font-size: 40rpx;
      margin-bottom: 8rpx;
    }
    
    .tab-name {
      font-size: 24rpx;
      color: #666;
    }
  }
}

.content-scroll {
  height: calc(100vh - 200rpx);
}

.card {
  margin: 30rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  
  .card-header {
    padding: 30rpx;
    border-bottom: 1rpx solid #f5f5f5;
    
    .card-title {
      font-size: 30rpx;
      font-weight: 600;
      color: #333;
    }
  }
  
  .card-body {
    padding: 30rpx;
  }
}

.chart-placeholder {
  height: 400rpx;
  background: #f9f9f9;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  
  text {
    color: #999;
    font-size: 28rpx;
  }
}

.loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 999;
  
  .loading-spinner {
    width: 60rpx;
    height: 60rpx;
    border: 4rpx solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

**4. `pages/analytics/analytics.json`**
```json
{
  "navigationBarTitleText": "统计分析",
  "enablePullDownRefresh": true,
  "backgroundColor": "#f5f6f7"
}
```

**验收标准**:
- [ ] 页面骨架完整
- [ ] Tab 切换正常
- [ ] 空状态显示正确

---

#### T1.3: 导航服务重构（2h）

**文件**: `services/navigationService.js`

**变更内容**:
```javascript
/**
 * 导航服务 - 重构版
 * 统一管理所有页面跳转逻辑
 */

const navigationService = {
  /**
   * 跳转到诊断记录列表
   */
  navigateToHistory: function(options = {}) {
    const { animation = true } = options;
    wx.switchTab({
      url: '/pages/history/history',
      fail: (err) => {
        console.error('跳转到诊断记录失败:', err);
      }
    });
  },

  /**
   * 跳转到诊断记录详情（报告页）
   */
  navigateToReportDetail: function(executionId, brandName, options = {}) {
    const { animation = true, events = {} } = options;
    
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`,
      events: events,
      fail: (err) => {
        console.error('跳转到报告详情失败:', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 跳转到统计分析
   */
  navigateToAnalytics: function(options = {}) {
    const { tabId = '' } = options;
    
    if (tabId) {
      wx.switchTab({
        url: `/pages/analytics/analytics?tabId=${tabId}`,
        fail: (err) => {
          console.error('跳转到统计分析失败:', err);
        }
      });
    } else {
      wx.switchTab({
        url: '/pages/analytics/analytics',
        fail: (err) => {
          console.error('跳转到统计分析失败:', err);
        }
      });
    }
  },

  /**
   * 跳转到个人中心
   */
  navigateToProfile: function() {
    wx.switchTab({
      url: '/pages/user-profile/user-profile',
      fail: (err) => {
        console.error('跳转到个人中心失败:', err);
      }
    });
  },

  /**
   * 跳转到收藏列表
   */
  navigateToFavorites: function() {
    wx.navigateTo({
      url: '/pages/user-profile/subpages/favorites/favorites',
      fail: (err) => {
        console.error('跳转到收藏列表失败:', err);
      }
    });
  },

  /**
   * 跳转到配置管理
   */
  navigateToConfig: function() {
    wx.navigateTo({
      url: '/pages/config-manager/config-manager',
      fail: (err) => {
        console.error('跳转到配置管理失败:', err);
      }
    });
  },

  /**
   * 跳转到使用指南
   */
  navigateToGuide: function() {
    wx.navigateTo({
      url: '/pages/user-guide/user-guide',
      fail: (err) => {
        console.error('跳转到使用指南失败:', err);
      }
    });
  },

  /**
   * 跳转到 AI 搜索首页
   */
  navigateToHome: function() {
    wx.switchTab({
      url: '/pages/index/index',
      fail: (err) => {
        console.error('跳转回首页失败:', err);
      }
    });
  },

  /**
   * 返回上一页
   */
  navigateBack: function(delta = 1) {
    wx.navigateBack({
      delta: delta,
      fail: (err) => {
        console.error('返回失败:', err);
      }
    });
  },

  /**
   * 重定向到页面（关闭当前页）
   */
  redirectTo: function(url) {
    wx.redirectTo({
      url: url,
      fail: (err) => {
        console.error('重定向失败:', err);
      }
    });
  },

  /**
   * 关闭所有页面，打开到某个页面
   */
  reLaunch: function(url) {
    wx.reLaunch({
      url: url,
      fail: (err) => {
        console.error('reLaunch 失败:', err);
      }
    });
  }
};

module.exports = navigationService;
```

**验收标准**:
- [ ] 所有导航方法可用
- [ ] 错误处理完善
- [ ] 日志记录完整

---

#### T1.4: 全局状态管理（2h）

**新建文件**: `services/pageStateService.js`

```javascript
/**
 * 页面状态管理服务
 * 解决 Tab 切换时状态丢失问题
 */

const STORAGE_PREFIX = 'page_state_';

const pageStateService = {
  /**
   * 保存页面状态
   */
  saveState: function(pageKey, state) {
    try {
      const serializedState = JSON.stringify({
        data: state,
        timestamp: Date.now()
      });
      wx.setStorageSync(STORAGE_PREFIX + pageKey, serializedState);
      console.log(`✅ 页面状态已保存：${pageKey}`);
    } catch (error) {
      console.error(`保存页面状态失败：${pageKey}`, error);
    }
  },

  /**
   * 获取页面状态
   */
  getState: function(pageKey) {
    try {
      const serializedState = wx.getStorageSync(STORAGE_PREFIX + pageKey);
      if (!serializedState) {
        return null;
      }
      
      const { data, timestamp } = JSON.parse(serializedState);
      
      // 检查状态是否过期（24 小时）
      const isExpired = Date.now() - timestamp > 24 * 60 * 60 * 1000;
      if (isExpired) {
        this.clearState(pageKey);
        return null;
      }
      
      return data;
    } catch (error) {
      console.error(`获取页面状态失败：${pageKey}`, error);
      return null;
    }
  },

  /**
   * 清除页面状态
   */
  clearState: function(pageKey) {
    try {
      wx.removeStorageSync(STORAGE_PREFIX + pageKey);
      console.log(`✅ 页面状态已清除：${pageKey}`);
    } catch (error) {
      console.error(`清除页面状态失败：${pageKey}`, error);
    }
  },

  /**
   * 清除所有页面状态
   */
  clearAllStates: function() {
    try {
      const keys = wx.getStorageInfoSync().keys;
      keys.forEach(key => {
        if (key.startsWith(STORAGE_PREFIX)) {
          wx.removeStorageSync(key);
        }
      });
      console.log('✅ 所有页面状态已清除');
    } catch (error) {
      console.error('清除所有页面状态失败', error);
    }
  },

  /**
   * 获取所有页面状态键
   */
  getAllStateKeys: function() {
    try {
      const keys = wx.getStorageInfoSync().keys;
      return keys.filter(key => key.startsWith(STORAGE_PREFIX));
    } catch (error) {
      console.error('获取状态键失败', error);
      return [];
    }
  }
};

// 页面键常量
pageStateService.PAGE_KEYS = {
  INDEX: 'index',
  HISTORY: 'history',
  ANALYTICS: 'analytics',
  PROFILE: 'profile'
};

module.exports = pageStateService;
```

**在 app.js 中集成**:
```javascript
// app.js
const pageStateService = require('./services/pageStateService');

App({
  globalData: {
    serverUrl: 'http://localhost:5000',
    userInfo: null,
    // 页面状态缓存（内存）
    pageStateCache: {}
  },

  onLaunch: function() {
    console.log('App Launch');
    // 初始化时清理过期状态
    this.cleanupExpiredStates();
  },

  /**
   * 保存页面状态（统一入口）
   */
  savePageState: function(pageKey, state) {
    // 同时保存到内存和 Storage
    this.globalData.pageStateCache[pageKey] = state;
    pageStateService.saveState(pageKey, state);
  },

  /**
   * 获取页面状态（统一入口）
   */
  getPageState: function(pageKey) {
    // 优先从内存获取，没有则从 Storage 获取
    return this.globalData.pageStateCache[pageKey] || 
           pageStateService.getState(pageKey);
  },

  /**
   * 清理过期状态
   */
  cleanupExpiredStates: function() {
    pageStateService.clearAllStates();
  },

  /**
   * 获取最新诊断结果（全局方法）
   */
  getLatestDiagnosis: function() {
    return wx.getStorageSync('latestDiagnosis') || null;
  },

  /**
   * 保存最新诊断结果
   */
  saveLatestDiagnosis: function(diagnosis) {
    wx.setStorageSync('latestDiagnosis', {
      ...diagnosis,
      savedAt: Date.now()
    });
  }
});
```

**验收标准**:
- [ ] 状态保存/恢复功能正常
- [ ] 过期状态自动清理
- [ ] 内存和 Storage 同步

---

#### T1.5: Tab 切换动画优化（1.5h）

**文件**: `app.wxss`（全局样式）

**新增内容**:
```scss
/* Tab 切换页面过渡动画 */
.page-transition {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 页面容器基础样式 */
.page-container {
  min-height: 100vh;
  background: #f5f6f7;
}

/* 卡片通用样式 */
.card {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin: 30rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.card-header {
  padding: 30rpx;
  border-bottom: 1rpx solid #f5f5f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
}

.card-body {
  padding: 30rpx;
}

.card-footer {
  padding: 20rpx 30rpx;
  background: #f9f9f9;
  border-top: 1rpx solid #f5f5f5;
}

/* 空状态通用样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
  text-align: center;
}

.empty-icon {
  width: 200rpx;
  height: 200rpx;
  margin-bottom: 40rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 20rpx;
}

.empty-desc {
  font-size: 28rpx;
  color: #999;
  line-height: 1.6;
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx;
}

.loading-spinner {
  width: 60rpx;
  height: 60rpx;
  border: 4rpx solid rgba(74, 123, 255, 0.2);
  border-top-color: #4A7BFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #999;
}

/* 按钮通用样式 */
.btn-primary {
  background: linear-gradient(135deg, #4A7BFF, #6B94FF);
  color: #fff;
  border: none;
  border-radius: 44rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
}

.btn-secondary {
  background: #fff;
  color: #4A7BFF;
  border: 2rpx solid #4A7BFF;
  border-radius: 44rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
}

.btn-danger {
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 44rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
}
```

**验收标准**:
- [ ] Tab 切换有平滑过渡效果
- [ ] 动画流畅不卡顿

---

#### T1.6: 旧页面兼容处理（1h）

**文件**: `pages/saved-results/saved-results.js`

**变更**: 添加兼容提示
```javascript
// 在 onLoad 中添加
onLoad: function(options) {
  // 检查是否从旧入口进入
  const fromOldEntry = options.fromOldEntry;
  
  if (fromOldEntry) {
    wx.showModal({
      title: '功能调整提示',
      content: '收藏报告功能已整合到"我的"页面，下次可从"我的"→"我的收藏"进入',
      showCancel: false,
      confirmText: '知道了'
    });
  }
  
  this.loadSavedResults();
}
```

**验收标准**:
- [ ] 旧入口可正常访问
- [ ] 显示功能调整提示

---

### 1.3 Phase 1 交付物清单

| 文件类型 | 文件路径 | 状态 |
|---------|---------|------|
| 配置 | `app.json` | ✅ 待更新 |
| 页面 | `pages/analytics/analytics.*` | ✅ 待创建 |
| 服务 | `services/navigationService.js` | ✅ 待重构 |
| 服务 | `services/pageStateService.js` | ✅ 待创建 |
| 应用 | `app.js` | ✅ 待更新 |
| 样式 | `app.wxss` | ✅ 待更新 |

---

## 三、Phase 2: 诊断记录增强（3 天）

### 2.1 任务清单

| 任务 ID | 任务名称 | 优先级 | 工时 | 负责人 | 状态 |
|--------|---------|--------|------|--------|------|
| T2.1 | 历史记录列表页优化 | P0 | 2h | 待分配 | ⏳ |
| T2.2 | 报告详情功能整合 | P0 | 4h | 待分配 | ⏳ |
| T2.3 | 收藏/取消收藏功能 | P0 | 2h | 待分配 | ⏳ |
| T2.4 | 分享/导出功能整合 | P1 | 3h | 待分配 | ⏳ |
| T2.5 | 报告可视化组件 | P1 | 4h | 待分配 | ⏳ |
| T2.6 | 删除功能优化 | P2 | 1h | 待分配 | ⏳ |

### 2.2 核心变更

#### T2.2: 报告详情功能整合（重点）

**文件**: `pages/history-detail/history-detail.js`

**整合原报告看板功能**:
```javascript
// 在现有代码基础上新增
Page({
  // ... 现有代码 ...

  /**
   * 加载完整报告数据（新增）
   */
  async loadFullReport(executionId) {
    try {
      const token = wx.getStorageSync('token');
      
      return new Promise((resolve, reject) => {
        wx.request({
          url: `${getApp().globalData.serverUrl}/api/test-history`,
          header: {
            'Authorization': token ? `Bearer ${token}` : ''
          },
          data: { executionId },
          success: (res) => {
            if (res.statusCode === 200 && res.data.status === 'success') {
              const reportData = res.data.records?.[0] || {};
              
              // 处理报告数据
              const processedData = this.processReportData(reportData);
              
              this.setData({
                dashboardData: processedData.dashboardData,
                questionCards: processedData.questionCards,
                toxicSources: processedData.toxicSources,
                scoreData: processedData.scoreData,
                competitionData: processedData.competitionData,
                loading: false
              });
              
              resolve(processedData);
            } else {
              reject(new Error('加载失败'));
            }
          },
          fail: reject
        });
      });
    } catch (error) {
      console.error('加载完整报告失败:', error);
      throw error;
    }
  },

  /**
   * 处理报告数据（新增）
   */
  processReportData(rawData) {
    // 实现数据转换逻辑
    return {
      dashboardData: rawData.dashboard || {},
      questionCards: rawData.questions || [],
      toxicSources: rawData.sources || [],
      scoreData: rawData.scores || {},
      competitionData: rawData.competition || {}
    };
  },

  /**
   * 收藏/取消收藏（新增）
   */
  async toggleFavorite() {
    const { executionId, brandName } = this.data;
    const isFavorited = this.data.isFavorited;
    
    try {
      if (isFavorited) {
        // 取消收藏
        await this.removeFromFavorites(executionId);
        this.setData({ isFavorited: false });
        wx.showToast({
          title: '已取消收藏',
          icon: 'success'
        });
      } else {
        // 添加收藏
        await this.addToFavorites(executionId, brandName);
        this.setData({ isFavorited: true });
        wx.showToast({
          title: '收藏成功',
          icon: 'success'
        });
      }
    } catch (error) {
      console.error('收藏操作失败:', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 添加到收藏（新增）
   */
  async addToFavorites(executionId, brandName) {
    // 实现收藏逻辑
    const favorites = wx.getStorageSync('favorites') || [];
    favorites.unshift({
      executionId,
      brandName,
      favoritedAt: Date.now()
    });
    wx.setStorageSync('favorites', favorites);
  },

  /**
   * 从收藏移除（新增）
   */
  async removeFromFavorites(executionId) {
    const favorites = wx.getStorageSync('favorites') || [];
    const filtered = favorites.filter(f => f.executionId !== executionId);
    wx.setStorageSync('favorites', filtered);
  }
});
```

---

## 四、Phase 3: 统计分析开发（5 天）

### 3.1 任务清单

| 任务 ID | 任务名称 | 优先级 | 工时 | 负责人 | 状态 |
|--------|---------|--------|------|--------|------|
| T3.1 | 品牌对比子页面 | P0 | 1.5 天 | 待分配 | ⏳ |
| T3.2 | 趋势分析子页面 | P0 | 1.5 天 | 待分配 | ⏳ |
| T3.3 | AI 平台对比子页面 | P1 | 1 天 | 待分配 | ⏳ |
| T3.4 | 问题聚合子页面 | P1 | 1 天 | 待分配 | ⏳ |

### 3.2 子页面结构

```
pages/analytics/
├── analytics.js/wxml/wxss/json      # 主页面
├── brand-compare/
│   ├── brand-compare.js
│   ├── brand-compare.wxml
│   ├── brand-compare.wxss
│   └── brand-compare.json
├── trend-analysis/
│   ├── trend-analysis.js
│   ├── trend-analysis.wxml
│   ├── trend-analysis.wxss
│   └── trend-analysis.json
├── platform-compare/
│   ├── platform-compare.js
│   ├── platform-compare.wxml
│   ├── platform-compare.wxss
│   └── platform-compare.json
└── question-analysis/
    ├── question-analysis.js
    ├── question-analysis.wxml
    ├── question-analysis.wxss
    └── question-analysis.json
```

---

## 五、Phase 4: 个人中心重构（1.5 天）

### 4.1 任务清单

| 任务 ID | 任务名称 | 优先级 | 工时 | 负责人 | 状态 |
|--------|---------|--------|------|--------|------|
| T4.1 | 个人中心页面更新 | P0 | 0.5h | 待分配 | ⏳ |
| T4.2 | 收藏子页面创建 | P0 | 3h | 待分配 | ⏳ |
| T4.3 | 功能入口整合 | P1 | 2h | 待分配 | ⏳ |
| T4.4 | 设置页面优化 | P2 | 1.5h | 待分配 | ⏳ |

---

## 六、Phase 5: 测试与上线（1 天）

### 5.1 测试清单

| 测试类型 | 测试内容 | 负责人 | 状态 |
|---------|---------|--------|------|
| 功能测试 | Tab 切换、导航跳转 | 待分配 | ⏳ |
| 兼容性测试 | 不同设备、系统版本 | 待分配 | ⏳ |
| 性能测试 | 页面加载速度、内存占用 | 待分配 | ⏳ |
| 回归测试 | 原有功能验证 | 待分配 | ⏳ |
| 用户测试 | 真实用户体验 | 待分配 | ⏳ |

### 5.2 上线检查清单

- [ ] 代码审查完成
- [ ] 所有测试通过
- [ ] 性能指标达标
- [ ] 文档更新完成
- [ ] 用户通知准备
- [ ] 回滚方案准备

---

## 七、风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 开发延期 | 中 | 高 | 每日站会、及时调整 |
| 性能问题 | 中 | 中 | 提前性能测试、优化 |
| 用户不适应 | 高 | 中 | 新手引导、帮助中心 |
| 数据兼容 | 低 | 高 | 数据迁移脚本、向下兼容 |

---

## 八、资源需求

### 8.1 人力资源

| 角色 | 人数 | 投入时间 |
|-----|------|---------|
| 前端开发 | 1-2 | 100% |
| 后端开发 | 1 | 50% |
| UI 设计 | 1 | 30% |
| 测试 | 1 | 50% |
| 产品 | 1 | 20% |

### 8.2 工具资源

- 微信开发者工具
- Git 版本控制
- 项目管理工具（Jira/Trello）
- 设计工具（Figma/Sketch）

---

**文档维护**: 技术团队  
**最后更新**: 2026-03-10  
**版本**: v1.0
