/**
 * 虚拟列表组件 - 大数据量报告渲染优化
 * 
 * 功能：
 * 1. 虚拟滚动（只渲染可见区域）
 * 2. 动态分页加载
 * 3. 内存优化
 * 4. 平滑滚动体验
 * 
 * 使用场景：
 * - 报告结果列表（100+ 条目）
 * - 长文本内容
 * - 大量数据表格
 * 
 * @author: 系统架构组
 * @date: 2026-02-28
 * @version: 1.0.0
 */

/**
 * 虚拟列表配置
 */
const VIRTUAL_LIST_CONFIG = {
  // 每项高度（px）
  ITEM_HEIGHT: 80,
  // 缓冲区大小（渲染可见区域上下额外的项数）
  BUFFER_SIZE: 5,
  // 批量加载大小
  BATCH_SIZE: 20,
  // 最大缓存项数
  MAX_CACHED_ITEMS: 100
};

/**
 * 创建虚拟列表管理器
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} 虚拟列表管理器
 */
export function createVirtualList(options = {}) {
  const config = {
    ...VIRTUAL_LIST_CONFIG,
    ...options
  };
  
  // 状态
  let state = {
    items: [],              // 所有数据项
    visibleItems: [],       // 可见数据项
    scrollTop: 0,           // 滚动位置
    containerHeight: 0,     // 容器高度
    startIndex: 0,          // 可见区域起始索引
    endIndex: 0,            // 可见区域结束索引
    totalHeight: 0          // 总高度
  };
  
  // 回调函数
  let onVisibleItemsChange = null;
  
  /**
   * 设置数据项
   */
  function setItems(items) {
    state.items = items;
    state.totalHeight = items.length * config.ITEM_HEIGHT;
    updateVisibleItems();
  }
  
  /**
   * 添加数据项（分页加载）
   */
  function addItems(newItems) {
    state.items = [...state.items, ...newItems];
    state.totalHeight = state.items.length * config.ITEM_HEIGHT;
    
    // 限制缓存大小
    if (state.items.length > config.MAX_CACHED_ITEMS) {
      state.items = state.items.slice(-config.MAX_CACHED_ITEMS);
    }
    
    updateVisibleItems();
  }
  
  /**
   * 更新可见项
   */
  function updateVisibleItems() {
    const { scrollTop, containerHeight } = state;
    
    // 计算可见区域
    const visibleStart = Math.floor(scrollTop / config.ITEM_HEIGHT);
    const visibleCount = Math.ceil(containerHeight / config.ITEM_HEIGHT);
    
    // 添加缓冲区
    const bufferStart = Math.max(0, visibleStart - config.BUFFER_SIZE);
    const bufferEnd = Math.min(
      state.items.length,
      visibleStart + visibleCount + config.BUFFER_SIZE
    );
    
    // 更新状态
    state.startIndex = bufferStart;
    state.endIndex = bufferEnd;
    state.visibleItems = state.items.slice(bufferStart, bufferEnd);
    
    // 通知回调
    if (onVisibleItemsChange) {
      onVisibleItemsChange({
        visibleItems: state.visibleItems,
        startIndex: bufferStart,
        endIndex: bufferEnd,
        totalItems: state.items.length,
        offsetTop: bufferStart * config.ITEM_HEIGHT
      });
    }
  }
  
  /**
   * 处理滚动事件
   */
  function onScroll(event) {
    const { scrollTop } = event.detail || event;
    state.scrollTop = scrollTop;
    updateVisibleItems();
    
    // 检查是否需要加载更多（滚动到接近底部）
    const scrollThreshold = state.totalHeight - scrollTop - containerHeight;
    if (scrollThreshold < config.ITEM_HEIGHT * 10 && options.onLoadMore) {
      options.onLoadMore();
    }
  }
  
  /**
   * 设置容器高度
   */
  function setContainerHeight(height) {
    state.containerHeight = height;
    updateVisibleItems();
  }
  
  /**
   * 滚动到指定位置
   */
  function scrollTo(index) {
    state.scrollTop = index * config.ITEM_HEIGHT;
    updateVisibleItems();
  }
  
  /**
   * 滚动到顶部
   */
  function scrollToTop() {
    state.scrollTop = 0;
    updateVisibleItems();
  }
  
  /**
   * 滚动到底部
   */
  function scrollToBottom() {
    state.scrollTop = state.totalHeight - state.containerHeight;
    updateVisibleItems();
  }
  
  /**
   * 设置可见项变化回调
   */
  function onVisibleItemsChangeCallback(callback) {
    onVisibleItemsChange = callback;
  }
  
  /**
   * 获取状态
   */
  function getState() {
    return {
      ...state,
      itemHeight: config.ITEM_HEIGHT,
      bufferSize: config.BUFFER_SIZE
    };
  }
  
  /**
   * 清空列表
   */
  function clear() {
    state = {
      items: [],
      visibleItems: [],
      scrollTop: 0,
      containerHeight: 0,
      startIndex: 0,
      endIndex: 0,
      totalHeight: 0
    };
    
    if (onVisibleItemsChange) {
      onVisibleItemsChange({
        visibleItems: [],
        startIndex: 0,
        endIndex: 0,
        totalItems: 0,
        offsetTop: 0
      });
    }
  }
  
  // 初始化
  if (options.initialItems) {
    setItems(options.initialItems);
  }
  
  if (options.containerHeight) {
    setContainerHeight(options.containerHeight);
  }
  
  return {
    setItems,
    addItems,
    onScroll,
    setContainerHeight,
    scrollTo,
    scrollToTop,
    scrollToBottom,
    onVisibleItemsChangeCallback,
    getState,
    clear
  };
}

/**
 * 虚拟列表 WXML 模板助手
 */
export const virtualListTemplate = {
  /**
   * 生成虚拟列表样式
   */
  generateStyle(offsetTop, totalHeight) {
    return `
      position: relative;
      height: ${totalHeight}px;
    `;
  },
  
  /**
   * 生成内容容器样式
   */
  generateContentStyle(offsetTop) {
    return `
      position: absolute;
      top: ${offsetTop}px;
      left: 0;
      right: 0;
    `;
  },
  
  /**
   * 生成滚动容器样式
   */
  generateContainerStyle(height) {
    return `
      height: ${height}px;
      overflow-y: scroll;
      position: relative;
    `;
  }
};

/**
 * 分页加载配置
 */
const PAGINATION_CONFIG = {
  // 每页大小
  PAGE_SIZE: 20,
  // 预加载阈值（剩余项数）
  PRELOAD_THRESHOLD: 10,
  // 最大页数
  MAX_PAGES: 10
};

/**
 * 创建分页加载器
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} 分页加载器
 */
export function createPaginationLoader(options = {}) {
  const config = {
    ...PAGINATION_CONFIG,
    ...options
  };
  
  // 状态
  let state = {
    currentPage: 1,
    totalPages: 0,
    totalItems: 0,
    items: [],
    isLoading: false,
    hasMore: true
  };
  
  // 数据加载函数
  let loadPageFn = null;
  
  /**
   * 设置加载函数
   */
  function setLoadFunction(fn) {
    loadPageFn = fn;
  }
  
  /**
   * 加载指定页
   */
  async function loadPage(page) {
    if (state.isLoading || !loadPageFn) {
      return;
    }
    
    state.isLoading = true;
    
    try {
      const result = await loadPageFn(page, config.PAGE_SIZE);
      
      state.items = [...state.items, ...result.items];
      state.currentPage = page;
      state.totalItems = result.total;
      state.totalPages = Math.ceil(result.total / config.PAGE_SIZE);
      state.hasMore = state.currentPage < state.totalPages;
      state.isLoading = false;
      
      return {
        success: true,
        items: state.items
      };
    } catch (error) {
      state.isLoading = false;
      console.error('[PaginationLoader] Load page error:', error);
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * 加载下一页
   */
  async function loadNextPage() {
    if (!state.hasMore || state.isLoading) {
      return null;
    }
    
    return await loadPage(state.currentPage + 1);
  }
  
  /**
   * 重新加载
   */
  async function reload() {
    state = {
      currentPage: 1,
      totalPages: 0,
      totalItems: 0,
      items: [],
      isLoading: false,
      hasMore: true
    };
    
    return await loadPage(1);
  }
  
  /**
   * 获取状态
   */
  function getState() {
    return {
      ...state,
      pageSize: config.PAGE_SIZE,
      preloadThreshold: config.PRELOAD_THRESHOLD
    };
  }
  
  /**
   * 检查是否需要加载更多
   */
  function shouldLoadMore(loadedCount) {
    const remaining = state.totalItems - loadedCount;
    return remaining <= config.PRELOAD_THRESHOLD && state.hasMore;
  }
  
  return {
    setLoadFunction,
    loadPage,
    loadNextPage,
    reload,
    getState,
    shouldLoadMore
  };
}

/**
 * 报告数据优化器
 * 
 * 用于优化大型报告数据的渲染
 */
export class ReportDataOptimizer {
  constructor(options = {}) {
    this.config = {
      ...VIRTUAL_LIST_CONFIG,
      ...options
    };
    
    this.virtualList = createVirtualList({
      ...this.config,
      onLoadMore: options.onLoadMore
    });
    
    this.paginationLoader = createPaginationLoader({
      pageSize: this.config.BATCH_SIZE
    });
  }
  
  /**
   * 优化报告数据
   */
  optimizeReportData(reportData) {
    if (!reportData) {
      return null;
    }
    
    // 提取可列表数据
    const listData = this.extractListData(reportData);
    
    // 设置到虚拟列表
    this.virtualList.setItems(listData);
    
    return {
      ...reportData,
      listData: {
        total: listData.length,
        visible: this.virtualList.getState().visibleItems,
        hasMore: true
      }
    };
  }
  
  /**
   * 提取列表数据
   */
  extractListData(reportData) {
    const listData = [];
    
    // 从报告维度中提取数据
    if (reportData.dimensions) {
      reportData.dimensions.forEach((dimension, index) => {
        listData.push({
          id: dimension.id || index,
          type: 'dimension',
          data: dimension,
          title: dimension.dimension_name || dimension.name,
          score: dimension.overall_score,
          summary: dimension.summary
        });
      });
    }
    
    // 从 AI 调用结果中提取数据
    if (reportData.aiResults) {
      reportData.aiResults.forEach((result, index) => {
        listData.push({
          id: `ai-${index}`,
          type: 'ai_result',
          data: result,
          model: result.model,
          platform: result.platform,
          status: result.success ? 'success' : 'error'
        });
      });
    }
    
    return listData;
  }
  
  /**
   * 获取可见数据
   */
  getVisibleData() {
    return this.virtualList.getState().visibleItems;
  }
  
  /**
   * 加载更多
   */
  loadMore() {
    return this.paginationLoader.loadNextPage();
  }
  
  /**
   * 重置
   */
  reset() {
    this.virtualList.clear();
    this.paginationLoader.reload();
  }
}

/**
 * 性能监控
 */
export function monitorRenderPerformance(componentName) {
  const startTime = performance.now();
  
  return {
    mark(label) {
      console.log(`[Performance] ${componentName} - ${label}: ${performance.now() - startTime}ms`);
    },
    
    end() {
      const duration = performance.now() - startTime;
      console.log(`[Performance] ${componentName} - Total render time: ${duration.toFixed(2)}ms`);
      
      // 警告慢渲染
      if (duration > 100) {
        console.warn(`[Performance] ${componentName} - Slow render detected: ${duration.toFixed(2)}ms`);
      }
      
      return duration;
    }
  };
}
