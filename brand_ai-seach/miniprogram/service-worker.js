/**
 * Service Worker - 离线缓存管理
 * 
 * 功能：
 * 1. 静态资源缓存（小程序页面、组件、样式）
 * 2. API 响应缓存（GET 请求）
 * 3. 缓存版本管理和自动更新
 * 4. 离线 fallback 页面支持
 */

// ==================== 缓存配置 ====================
const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `wechat-app-cache-${CACHE_VERSION}`;
const STATIC_CACHE_NAME = `wechat-app-static-${CACHE_VERSION}`;
const API_CACHE_NAME = `wechat-app-api-${CACHE_VERSION}`;
const USER_CACHE_NAME = `wechat-app-user-${CACHE_VERSION}`;

// 缓存大小限制（API 缓存最多保存 50 个响应）
const API_CACHE_MAX_SIZE = 50;
const USER_CACHE_MAX_SIZE = 20;

// 静态资源缓存列表（核心页面和组件）
const STATIC_ASSETS = [
  // 核心页面
  '/pages/index/index',
  '/pages/history/history',
  '/pages/saved-results/saved-results',
  '/pages/user-profile/user-profile',
  
  // 报告相关页面
  '/pages/report/dashboard/index',
  '/pages/report-v2/report-v2',
  
  // 常用组件
  '/components/error-toast/error-toast',
  '/components/skeleton/skeleton',
  '/components/virtual-list/virtualList',
  '/components/keyword-cloud/keyword-cloud',
  '/components/sentiment-chart/sentiment-chart',
  '/components/brand-distribution/brand-distribution',
  
  // 核心服务
  '/services/reportService',
  '/services/diagnosisService',
  '/services/webSocketClient',
  '/services/pollingManager',
  
  // 工具类
  '/utils/errorHandler',
  '/utils/retryStrategy',
  '/utils/uiHelper',
  
  // 配置
  '/config/featureFlags'
];

// API 缓存白名单（只缓存这些 GET 请求）
const API_CACHE_WHITELIST = [
  '/api/home',
  '/api/history',
  '/api/user',
  '/api/brand',
  '/api/competitive-analysis',
  '/api/data-sync',
  '/api/export'
];

// 不需要缓存的 API
const API_NO_CACHE = [
  '/api/auth',
  '/api/login',
  '/api/logout',
  '/api/diagnosis/start',
  '/api/diagnosis/submit',
  '/api/diagnosis/status'
];

// ==================== 安装事件 ====================
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker 安装中...', CACHE_VERSION);
  
  event.waitUntil(
    Promise.all([
      // 缓存静态资源
      caches.open(STATIC_CACHE_NAME).then((cache) => {
        console.log('[SW] 缓存静态资源');
        return cache.addAll(STATIC_ASSETS.map(path => {
          // 微信小程序中需要添加完整路径
          return path;
        })).catch((error) => {
          console.log('[SW] 部分资源缓存失败（可能不存在）:', error);
          // 忽略缓存失败，继续执行
        });
      }),
      
      // 跳过等待，立即激活
      self.skipWaiting()
    ])
  );
});

// ==================== 激活事件 ====================
self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker 激活中...');
  
  event.waitUntil(
    Promise.all([
      // 清理旧版本缓存
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // 如果是旧版本的缓存，则删除
            if (
              cacheName !== CACHE_NAME &&
              cacheName !== STATIC_CACHE_NAME &&
              cacheName !== API_CACHE_NAME
            ) {
              console.log('[SW] 删除旧缓存:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      
      // 限制 API 缓存大小
      limitApiCacheSize(),
      
      // 立即接管所有客户端
      self.clients.claim()
    ])
  );
});

// ==================== 请求拦截 ====================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // 只处理 https 和 http 请求
  if (!/^https?:$/i.test(url.protocol)) {
    return;
  }
  
  // 微信小程序的请求可能没有完整 URL
  const requestPath = url.pathname;
  
  // 判断请求类型
  if (isStaticAsset(requestPath)) {
    // 静态资源：缓存优先
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          console.log('[SW] [静态资源] 从缓存加载:', requestPath);
          return cachedResponse;
        }
        
        // 缓存未命中，从网络加载
        return fetchAndCache(request, STATIC_CACHE_NAME);
      }).catch((error) => {
        console.log('[SW] [静态资源] 加载失败:', requestPath, error);
        // 返回离线 fallback（如果有）
        return caches.match('/offline');
      })
    );
  } else if (isApiRequest(requestPath)) {
    // API 请求：根据配置决定是否缓存
    if (shouldCacheApi(requestPath, request.method)) {
      event.respondWith(
        caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('[SW] [API] 从缓存加载:', requestPath);
            // 后台更新缓存
            fetchAndCache(request, API_CACHE_NAME, true);
            return cachedResponse;
          }
          
          // 缓存未命中，从网络加载
          return fetchAndCache(request, API_CACHE_NAME);
        }).catch((error) => {
          console.log('[SW] [API] 加载失败:', requestPath, error);
          // 尝试返回旧的缓存数据
          return getStaleApiData(requestPath);
        })
      );
    }
    // 不缓存的 API 请求，直接通过网络
  }
  // 其他请求（如图片等），使用默认行为
});

// ==================== 辅助函数 ====================

/**
 * 判断是否为静态资源请求
 */
function isStaticAsset(path) {
  // 小程序页面路径
  const pagePatterns = [
    /^\/pages\//,
    /^\/components\//,
    /^\/services\//,
    /^\/utils\//,
    /^\/config\//,
  ];
  
  return pagePatterns.some(pattern => pattern.test(path));
}

/**
 * 判断是否为 API 请求
 */
function isApiRequest(path) {
  return path.startsWith('/api/');
}

/**
 * 判断 API 请求是否应该被缓存
 */
function shouldCacheApi(path, method) {
  // 只缓存 GET 请求
  if (method !== 'GET') {
    return false;
  }
  
  // 检查是否在白名单中
  const isInWhitelist = API_CACHE_WHITELIST.some(whitelistPath => 
    path.startsWith(whitelistPath)
  );
  
  // 检查是否在黑名单中
  const isInBlacklist = API_NO_CACHE.some(noCachePath => 
    path.startsWith(noCachePath)
  );
  
  return isInWhitelist && !isInBlacklist;
}

/**
 * 从网络加载并缓存响应
 * @param {Request} request - 请求对象
 * @param {string} cacheName - 缓存名称
 * @param {boolean} isBackground - 是否为后台更新
 */
async function fetchAndCache(request, cacheName, isBackground = false) {
  try {
    const response = await fetch(request);
    
    // 只缓存成功的响应
    if (response.ok) {
      const cache = await caches.open(cacheName);
      
      // 如果是 API 缓存，需要克隆响应（因为响应流只能读取一次）
      const responseToCache = response.clone();
      
      if (!isBackground) {
        cache.put(request, responseToCache);
        console.log('[SW] 缓存新响应:', request.url);
        
        // 如果是 API 缓存，限制大小
        if (cacheName === API_CACHE_NAME) {
          await limitApiCacheSize();
        }
      }
    }
    
    return response;
  } catch (error) {
    console.log('[SW] 网络请求失败:', request.url, error);
    throw error;
  }
}

/**
 * 限制 API 缓存大小
 */
async function limitApiCacheSize() {
  try {
    const cache = await caches.open(API_CACHE_NAME);
    const keys = await cache.keys();
    
    if (keys.length > API_CACHE_MAX_SIZE) {
      // 删除最旧的缓存（FIFO）
      const deleteCount = keys.length - API_CACHE_MAX_SIZE;
      for (let i = 0; i < deleteCount; i++) {
        await cache.delete(keys[i]);
      }
      console.log('[SW] 已清理 API 缓存，删除', deleteCount, '个旧条目');
    }
  } catch (error) {
    console.log('[SW] 限制 API 缓存大小时出错:', error);
  }
}

/**
 * 获取过期的 API 数据（作为 fallback）
 */
async function getStaleApiData(requestPath) {
  try {
    // 尝试从 API 缓存中获取任何匹配的数据
    const cache = await caches.open(API_CACHE_NAME);
    const keys = await cache.keys();
    
    // 查找路径相似的缓存
    for (const key of keys) {
      if (key.url.includes(requestPath)) {
        const cachedResponse = await cache.match(key);
        if (cachedResponse) {
          console.log('[SW] 返回过期 API 数据:', requestPath);
          return cachedResponse;
        }
      }
    }
  } catch (error) {
    console.log('[SW] 获取过期 API 数据失败:', error);
  }
  
  // 返回网络错误响应
  return new Response('Network error', {
    status: 503,
    statusText: 'Service Unavailable'
  });
}

// ==================== 消息处理 ====================

/**
 * 处理来自客户端的消息
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      // 立即激活新的 Service Worker
      self.skipWaiting();
      break;
      
    case 'CLEAR_CACHE':
      // 清除指定缓存
      clearCache(payload.cacheName).then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
      
    case 'GET_CACHE_STATUS':
      // 获取缓存状态
      getCacheStatus().then((status) => {
        event.ports[0].postMessage(status);
      });
      break;
      
    case 'PRECACHE_URLS':
      // 预缓存指定 URL 列表
      precacheUrls(payload.urls).then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
      
    default:
      console.log('[SW] 未知消息类型:', type);
  }
});

/**
 * 清除指定缓存
 */
async function clearCache(cacheName) {
  if (cacheName) {
    await caches.delete(cacheName);
    console.log('[SW] 已清除缓存:', cacheName);
  } else {
    // 清除所有缓存
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
    console.log('[SW] 已清除所有缓存');
  }
}

/**
 * 获取缓存状态
 */
async function getCacheStatus() {
  const cacheNames = await caches.keys();
  const status = {};
  
  for (const name of cacheNames) {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    status[name] = keys.length;
  }
  
  return {
    caches: status,
    version: CACHE_VERSION,
    isActive: true
  };
}

/**
 * 预缓存指定 URL 列表
 */
async function precacheUrls(urls) {
  const cache = await caches.open(STATIC_CACHE_NAME);
  const urlsToCache = urls.filter(url => url);
  
  try {
    await cache.addAll(urlsToCache);
    console.log('[SW] 预缓存完成:', urlsToCache.length, '个 URL');
  } catch (error) {
    console.log('[SW] 部分预缓存失败:', error);
  }
}

console.log('[SW] Service Worker 已加载');
