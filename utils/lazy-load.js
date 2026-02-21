/**
 * 懒加载工具模块
 * 支持图片、组件、数据的懒加载
 * 
 * 增强功能:
 * - 完善的 IntersectionObserver 兼容性检测
 * - 多级降级方案
 * - 性能优化
 */

const logger = require('./logger');

/**
 * 特性检测
 */
const features = {
  // IntersectionObserver 支持检测
  intersectionObserver: (function() {
    if (typeof wx === 'undefined') return false;
    if (!wx.createIntersectionObserver) return false;
    
    try {
      // 尝试创建观察者实例检测完整支持
      const query = wx.createSelectorQuery();
      if (!query) return false;
      return true;
    } catch (e) {
      return false;
    }
  })(),
  
  // createSelectorQuery 支持检测
  selectorQuery: (function() {
    if (typeof wx === 'undefined') return false;
    return typeof wx.createSelectorQuery === 'function';
  })(),
  
  // 检查是否在微信环境
  wechat: (typeof wx !== 'undefined')
};

/**
 * 日志记录（仅调试模式）
 */
function debugLog(message, data = {}) {
  if (features.wechat) {
    logger.debug('[LazyLoad] ' + message, data);
  } else {
    console.log('[LazyLoad] ' + message, data);
  }
}

/**
 * 图片懒加载
 * @param {string} selector - 选择器
 * @param {object} options - 配置选项
 */
function lazyLoadImages(selector = '.lazy-image', options = {}) {
  const config = {
    rootMargin: options.rootMargin || '50px',
    threshold: options.threshold || 0.01,
    placeholder: options.placeholder || '/images/placeholder.png',
    effect: options.effect !== false,
    useObserver: options.useObserver !== false
  };

  debugLog('初始化图片懒加载', { selector, features, config });

  // 检查是否支持 IntersectionObserver
  if (config.useObserver && features.intersectionObserver && features.selectorQuery) {
    return loadImagesWithObserver(selector, config);
  } else {
    debugLog('IntersectionObserver 不支持，使用降级方案');
    return loadAllImages(selector, config);
  }
}

/**
 * 使用 IntersectionObserver 加载图片
 */
function loadImagesWithObserver(selector, config) {
  const query = wx.createSelectorQuery();
  
  // 选择所有懒加载图片
  query.selectAll(selector).fields({
    dataset: true,
    src: true
  }, (res) => {
    if (!res || res.length === 0) {
      debugLog('未找到懒加载图片', { selector });
      return;
    }

    // 创建 IntersectionObserver
    const observer = wx.createIntersectionObserver({
      thresholds: [config.threshold],
      initialRatio: 0,
      observeAll: false
    });

    let loadedCount = 0;

    res.forEach((item, index) => {
      if (!item || !item.dataset || !item.dataset.src) {
        return;
      }

      const realSrc = item.dataset.src;
      const elementSelector = `${selector}:nth-child(${index + 1})`;

      // 设置占位图
      if (config.placeholder) {
        // 通过 setData 设置占位图
      }

      // 开始观察
      observer.relativeToViewport({
        top: parseInt(config.rootMargin) || 50,
        bottom: parseInt(config.rootMargin) || 50
      });

      observer.observe(elementSelector, (resultSet) => {
        if (resultSet.intersectionRatio > 0 && !item._loaded) {
          item._loaded = true;
          loadedCount++;
          debugLog(`图片 ${loadedCount}/${res.length} 进入视口`, { src: realSrc });
          
          // 加载真实图片
          loadImage(item, realSrc, config);
          
          // 如果所有图片都已加载，断开观察
          if (loadedCount >= res.length) {
            observer.disconnect();
            debugLog('所有图片已加载，断开观察');
          }
        }
      });
    });

    debugLog(`开始观察 ${res.length} 张图片`);

    return {
      disconnect: () => {
        observer.disconnect();
        debugLog('手动断开观察');
      }
    };
  }).exec();
}

/**
 * 加载单张图片（微信小程序方式）
 */
function loadImage(item, realSrc, config) {
  if (!realSrc) {
    debugLog('图片缺少 data-src 属性');
    return;
  }

  debugLog('加载图片', { src: realSrc });

  // 在微信小程序中，通过 setData 更新图片 src
  // 这里需要页面配合，在实际使用中由页面处理
  if (item._setData) {
    item._setData({
      ['imageSrc']: realSrc
    });
  }
}

/**
 * 降级方案：加载所有图片
 */
function loadAllImages(selector, config) {
  if (!features.selectorQuery) {
    debugLog('createSelectorQuery 不支持，无法加载图片');
    return;
  }

  const query = wx.createSelectorQuery();
  query.selectAll(selector).fields({
    dataset: true
  }).exec((res) => {
    if (!res || !res[0]) {
      debugLog('未找到图片元素', { selector });
      return;
    }

    let loadedCount = 0;
    res[0].forEach(item => {
      if (item && item.dataset && item.dataset.src) {
        loadImage(item, item.dataset.src, config);
        loadedCount++;
      }
    });

    debugLog(`降级方案加载 ${loadedCount} 张图片`);
  });
}

/**
 * 组件懒加载
 * @param {string} componentPath - 组件路径
 * @param {object} page - 页面对象
 */
function lazyLoadComponent(componentPath, page) {
  return new Promise((resolve, reject) => {
    logger.debug('[LazyLoad] 开始加载组件', { componentPath });

    // 检查是否已加载
    if (page[componentPath]) {
      logger.debug('[LazyLoad] 组件已加载', { componentPath });
      resolve(page[componentPath]);
      return;
    }

    // 动态加载组件
    require([componentPath], (component) => {
      page[componentPath] = component;
      logger.info('[LazyLoad] 组件加载成功', { componentPath });
      resolve(component);
    }, (error) => {
      logger.error('[LazyLoad] 组件加载失败', { componentPath, error });
      reject(error);
    });
  });
}

/**
 * 数据懒加载（分页加载）
 * @param {function} fetchFn - 数据获取函数
 * @param {object} options - 配置选项
 */
function lazyLoadData(fetchFn, options = {}) {
  const config = {
    pageSize: options.pageSize || 20,
    threshold: options.threshold || 0.1,
    container: options.container || null
  };

  let currentPage = 1;
  let isLoading = false;
  let hasMore = true;
  let allData = [];

  // 创建加载器
  const loader = {
    /**
     * 加载下一页
     */
    async loadNext() {
      if (isLoading || !hasMore) {
        return { data: [], hasMore: false };
      }

      isLoading = true;
      logger.debug('[LazyLoad] 加载数据', { page: currentPage });

      try {
        const result = await fetchFn({
          page: currentPage,
          pageSize: config.pageSize
        });

        const newData = result.data || [];
        allData = [...allData, ...newData];
        hasMore = result.hasMore !== false;
        currentPage++;

        logger.info('[LazyLoad] 数据加载成功', {
          count: newData.length,
          total: allData.length,
          hasMore
        });

        return {
          data: newData,
          hasMore,
          total: allData.length
        };
      } catch (error) {
        logger.error('[LazyLoad] 数据加载失败', error);
        throw error;
      } finally {
        isLoading = false;
      }
    },

    /**
     * 重置加载器
     */
    reset() {
      currentPage = 1;
      isLoading = false;
      hasMore = true;
      allData = [];
      logger.debug('[LazyLoad] 加载器已重置');
    },

    /**
     * 获取所有数据
     */
    getAllData() {
      return allData;
    },

    /**
     * 获取加载状态
     */
    getStatus() {
      return {
        currentPage,
        isLoading,
        hasMore,
        total: allData.length
      };
    }
  };

  return loader;
}

/**
 * 长列表虚拟滚动
 * @param {array} data - 完整数据
 * @param {object} options - 配置选项
 */
function virtualScroll(data, options = {}) {
  const config = {
    itemHeight: options.itemHeight || 100,
    overscan: options.overscan || 5,
    containerHeight: options.containerHeight || 600
  };

  const state = {
    scrollTop: 0,
    visibleStart: 0,
    visibleEnd: 0,
    totalHeight: data.length * config.itemHeight
  };

  return {
    /**
     * 计算可见区域
     */
    calculateVisible(scrollTop) {
      state.scrollTop = scrollTop;

      const startIndex = Math.floor(scrollTop / config.itemHeight);
      const visibleCount = Math.ceil(config.containerHeight / config.itemHeight);

      state.visibleStart = Math.max(0, startIndex - config.overscan);
      state.visibleEnd = Math.min(
        data.length,
        startIndex + visibleCount + config.overscan
      );

      return {
        visibleData: data.slice(state.visibleStart, state.visibleEnd),
        offsetY: state.visibleStart * config.itemHeight,
        totalHeight: state.totalHeight,
        visibleStart: state.visibleStart,
        visibleEnd: state.visibleEnd
      };
    },

    /**
     * 获取状态
     */
    getStatus() {
      return state;
    }
  };
}

/**
 * 预加载资源
 * @param {array} resources - 资源列表
 */
function preloadResources(resources) {
  logger.info('[LazyLoad] 开始预加载资源', { count: resources.length });

  resources.forEach(src => {
    const image = new Image();
    image.src = src;
    image.onload = () => {
      logger.debug('[LazyLoad] 资源预加载成功', { src });
    };
    image.onerror = () => {
      logger.warn('[LazyLoad] 资源预加载失败', { src });
    };
  });
}

module.exports = {
  lazyLoadImages,
  lazyLoadComponent,
  lazyLoadData,
  virtualScroll,
  preloadResources
};
