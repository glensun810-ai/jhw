/**
 * 懒加载工具模块
 * 支持图片、组件、数据的懒加载
 */

const logger = require('./logger');

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
    effect: options.effect !== false
  };

  // 检查是否支持 IntersectionObserver
  if (!('IntersectionObserver' in wx)) {
    logger.warn('[LazyLoad] 当前环境不支持 IntersectionObserver，使用降级方案');
    return loadAllImages(selector, config);
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const image = entry.target;
        loadImage(image, config);
        observer.unobserve(image);
      }
    });
  }, {
    rootMargin: config.rootMargin,
    threshold: config.threshold
  });

  // 选择所有懒加载图片
  const query = wx.createSelectorQuery();
  query.selectAll(selector).fields({
    dataset: true,
    src: true
  }).exec((res) => {
    if (res[0]) {
      res[0].forEach(item => {
        if (item && item.dataset && item.dataset.src) {
          // 设置占位图
          if (config.placeholder) {
            item.src = config.placeholder;
          }
          // 开始观察
          observer.observe(item);
        }
      });
    }
  });

  logger.debug('[LazyLoad] 图片懒加载已初始化', { selector });

  return {
    disconnect: () => observer.disconnect()
  };
}

/**
 * 加载单张图片
 */
function loadImage(imageElement, config) {
  const realSrc = imageElement.dataset.src;
  
  if (!realSrc) {
    logger.warn('[LazyLoad] 图片缺少 data-src 属性');
    return;
  }

  // 添加淡入效果
  if (config.effect) {
    imageElement.style.opacity = '0';
    imageElement.style.transition = 'opacity 0.3s ease-in';
  }

  imageElement.src = realSrc;

  if (config.effect) {
    imageElement.onload = () => {
      imageElement.style.opacity = '1';
    };
  }

  logger.debug('[LazyLoad] 图片已加载', { src: realSrc });
}

/**
 * 降级方案：加载所有图片
 */
function loadAllImages(selector, config) {
  const query = wx.createSelectorQuery();
  query.selectAll(selector).fields({
    dataset: true
  }).exec((res) => {
    if (res[0]) {
      res[0].forEach(item => {
        if (item && item.dataset && item.dataset.src) {
          loadImage(item, config);
        }
      });
    }
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
