/**
 * 页面过渡动画工具模块
 * 提供统一的页面导航和动画控制
 */

// 动画类型枚举
const ANIMATION_TYPES = {
  // 淡入淡出
  FADE: 'fade',
  // 从右向左滑入（前进导航）
  SLIDE_LEFT: 'slide-left',
  // 从左向右滑入（后退导航）
  SLIDE_RIGHT: 'slide-right',
  // 从下向上滑入
  SLIDE_UP: 'slide-up',
  // 从上向下滑入
  SLIDE_DOWN: 'slide-down',
  // 放大呈现
  ZOOM: 'zoom',
  // 缩小消失
  ZOOM_OUT: 'zoom-out',
  // 旋转进入
  ROTATE: 'rotate',
  // Y 轴翻转
  FLIP_Y: 'flip-y',
  // X 轴翻转
  FLIP_X: 'flip-x',
  // 弹性动画
  BOUNCE: 'bounce',
  // 无动画
  NONE: 'none'
};

// 动画时长配置（毫秒）
const ANIMATION_DURATION = {
  FAST: 200,
  NORMAL: 350,
  SLOW: 500
};

/**
 * 页面过渡动画管理器
 */
const PageTransition = {
  // 当前页面路径栈
  pageStack: [],
  
  // 是否正在过渡
  isTransitioning: false,
  
  // 默认动画类型
  defaultAnimation: ANIMATION_TYPES.SLIDE_LEFT,
  
  // 后退动画类型
  backAnimation: ANIMATION_TYPES.SLIDE_RIGHT,
  
  /**
   * 初始化页面过渡动画
   */
  init() {
    console.log('[PageTransition] 初始化页面过渡动画系统');
    
    // 获取当前页面栈
    const pages = getCurrentPages();
    if (pages.length > 0) {
      this.pageStack = pages.map(page => page.route);
    }
    
    // 为所有页面添加加载动画
    this.applyPageLoadAnimation();
  },
  
  /**
   * 应用页面加载动画
   */
  applyPageLoadAnimation() {
    const pages = getCurrentPages();
    if (pages.length > 0) {
      const currentPage = pages[pages.length - 1];
      if (currentPage && currentPage.setData) {
        // 延迟添加动画类，确保 DOM 已渲染
        setTimeout(() => {
          currentPage.setData({
            pageTransitionClass: 'fade-enter-active',
            pageLoaded: true
          });
        }, 50);
      }
    }
  },
  
  /**
   * 导航到指定页面（带动画）
   * @param {string} url - 页面路径
   * @param {string} animation - 动画类型（可选）
   * @param {boolean} isBack - 是否是返回操作（可选）
   */
  navigateTo(url, animation = null, isBack = false) {
    if (this.isTransitioning) {
      console.warn('[PageTransition] 正在过渡中，请稍后再试');
      return;
    }
    
    this.isTransitioning = true;
    
    // 确定动画类型
    const animType = animation || (isBack ? this.backAnimation : this.defaultAnimation);
    
    console.log(`[PageTransition] 导航到：${url}, 动画：${animType}`);
    
    // 执行导航
    wx.navigateTo({
      url: url,
      success: () => {
        this.pageStack.push(url);
        setTimeout(() => {
          this.isTransitioning = false;
        }, ANIMATION_DURATION.NORMAL);
      },
      fail: (err) => {
        console.error('[PageTransition] 导航失败:', err);
        this.isTransitioning = false;
      }
    });
  },
  
  /**
   * 返回上一页（带动画）
   * @param {number} delta - 返回的页面数（可选，默认为 1）
   * @param {string} animation - 动画类型（可选）
   */
  navigateBack(delta = 1, animation = null) {
    if (this.isTransitioning) {
      console.warn('[PageTransition] 正在过渡中，请稍后再试');
      return;
    }
    
    this.isTransitioning = true;
    
    const animType = animation || this.backAnimation;
    
    console.log(`[PageTransition] 返回 ${delta} 页，动画：${animType}`);
    
    wx.navigateBack({
      delta: delta,
      fail: (err) => {
        console.error('[PageTransition] 返回失败:', err);
        this.isTransitioning = false;
      }
    });
    
    if (this.pageStack.length > delta) {
      this.pageStack.splice(this.pageStack.length - delta, delta);
    }
    
    setTimeout(() => {
      this.isTransitioning = false;
    }, ANIMATION_DURATION.NORMAL);
  },
  
  /**
   * 重定向到指定页面（带动画）
   * @param {string} url - 页面路径
   * @param {string} animation - 动画类型（可选）
   */
  redirectTo(url, animation = null) {
    if (this.isTransitioning) {
      console.warn('[PageTransition] 正在过渡中，请稍后再试');
      return;
    }
    
    this.isTransitioning = true;
    
    const animType = animation || this.defaultAnimation;
    
    console.log(`[PageTransition] 重定向到：${url}, 动画：${animType}`);
    
    wx.redirectTo({
      url: url,
      success: () => {
        if (this.pageStack.length > 0) {
          this.pageStack[this.pageStack.length - 1] = url;
        }
        setTimeout(() => {
          this.isTransitioning = false;
        }, ANIMATION_DURATION.NORMAL);
      },
      fail: (err) => {
        console.error('[PageTransition] 重定向失败:', err);
        this.isTransitioning = false;
      }
    });
  },
  
  /**
   * 关闭所有页面并打开到指定页面
   * @param {string} url - 页面路径
   * @param {string} animation - 动画类型（可选）
   */
  switchTab(url, animation = null) {
    if (this.isTransitioning) {
      console.warn('[PageTransition] 正在过渡中，请稍后再试');
      return;
    }
    
    this.isTransitioning = true;
    
    console.log(`[PageTransition] 切换到 Tab: ${url}`);
    
    wx.switchTab({
      url: url,
      success: () => {
        this.pageStack = [url];
        setTimeout(() => {
          this.isTransitioning = false;
        }, ANIMATION_DURATION.NORMAL);
      },
      fail: (err) => {
        console.error('[PageTransition] 切换 Tab 失败:', err);
        this.isTransitioning = false;
      }
    });
  },
  
  /**
   * 关闭当前页面（带动画）
   */
  closeCurrentPage() {
    this.navigateBack(1);
  },
  
  /**
   * 获取动画类型
   * @param {string} name - 动画名称
   * @returns {string} 动画类型值
   */
  getAnimationType(name) {
    return ANIMATION_TYPES[name] || this.defaultAnimation;
  },
  
  /**
   * 设置默认动画
   * @param {string} animation - 动画类型
   */
  setDefaultAnimation(animation) {
    this.defaultAnimation = animation;
    console.log(`[PageTransition] 设置默认动画为：${animation}`);
  },
  
  /**
   * 设置后退动画
   * @param {string} animation - 动画类型
   */
  setBackAnimation(animation) {
    this.backAnimation = animation;
    console.log(`[PageTransition] 设置后退动画为：${animation}`);
  }
};

/**
 * 页面过渡 Mixin
 * 可在页面的 Page() 配置中混入使用
 */
const PageTransitionMixin = {
  data: {
    // 页面过渡动画类
    pageTransitionClass: '',
    // 页面是否已加载
    pageLoaded: false,
    // 过渡动画持续时间（毫秒）
    transitionDuration: 350
  },
  
  onLoad() {
    // 页面加载时应用进入动画
    this.applyEnterAnimation();
  },
  
  onUnload() {
    // 页面卸载时应用退出动画
    this.applyExitAnimation();
  },
  
  /**
   * 应用进入动画
   */
  applyEnterAnimation() {
    const pages = getCurrentPages();
    const currentPage = pages[pages.length - 1];
    const prevPage = pages[pages.length - 2];
    
    // 判断是前进还是后退
    const isBack = prevPage && prevPage.route === this.data.prevPageRoute;
    
    // 设置动画类
    const enterClass = isBack ? 'slide-right-enter-active' : 'slide-left-enter-active';
    
    setTimeout(() => {
      this.setData({
        pageTransitionClass: enterClass,
        pageLoaded: true
      });
    }, 50);
  },
  
  /**
   * 应用退出动画
   */
  applyExitAnimation() {
    const pages = getCurrentPages();
    const nextPage = pages[pages.length - 1];
    
    // 设置退出动画类
    this.setData({
      pageTransitionClass: 'fade-exit-active'
    });
  },
  
  /**
   * 导航到指定页面
   * @param {string} url - 页面路径
   * @param {string} animation - 动画类型（可选）
   */
  navigateTo(url, animation) {
    this.setData({ prevPageRoute: this.route });
    PageTransition.navigateTo(url, animation);
  },
  
  /**
   * 返回上一页
   * @param {number} delta - 返回的页面数（可选）
   */
  navigateBack(delta) {
    PageTransition.navigateBack(delta);
  },
  
  /**
   * 重定向到指定页面
   * @param {string} url - 页面路径
   */
  redirectTo(url) {
    PageTransition.redirectTo(url);
  }
};

// 导出
module.exports = {
  ANIMATION_TYPES,
  ANIMATION_DURATION,
  PageTransition,
  PageTransitionMixin
};
