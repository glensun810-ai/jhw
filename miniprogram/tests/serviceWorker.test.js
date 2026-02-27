/**
 * Service Worker 测试文件
 * 
 * 测试离线缓存功能
 */

const cacheManager = require('../utils/cacheManager');
const cacheConfig = require('../config/cacheConfig');

/**
 * Service Worker 测试套件
 */
describe('Service Worker 离线缓存测试', () => {
  // 模拟 wx API
  const mockWx = {
    setStorageSync: jest.fn(),
    getStorageSync: jest.fn(),
    removeStorageSync: jest.fn(),
    clearStorageSync: jest.fn()
  };

  // 替换全局 wx 对象
  global.wx = mockWx;

  beforeEach(() => {
    // 重置所有 mock
    jest.clearAllMocks();
  });

  describe('缓存配置测试', () => {
    test('应该导出正确的缓存版本', () => {
      expect(cacheConfig.CACHE_CONFIG.version).toBeDefined();
      expect(typeof cacheConfig.CACHE_CONFIG.version).toBe('string');
    });

    test('应该定义所有缓存类型', () => {
      const expectedTypes = ['static', 'api', 'user', 'temp'];
      const actualTypes = Object.keys(cacheConfig.CACHE_CONFIG.caches);
      
      expectedTypes.forEach(type => {
        expect(actualTypes).toContain(type);
      });
    });

    test('API 白名单应该包含预期路径', () => {
      const whitelist = cacheConfig.CACHE_CONFIG.apiWhitelist;
      expect(whitelist).toContain('/api/home');
      expect(whitelist).toContain('/api/history');
      expect(whitelist).toContain('/api/user');
    });

    test('API 黑名单应该包含预期路径', () => {
      const blacklist = cacheConfig.CACHE_CONFIG.apiBlacklist;
      expect(blacklist).toContain('/api/auth');
      expect(blacklist).toContain('/api/login');
    });
  });

  describe('缓存管理器测试', () => {
    test('设置缓存应该成功', async () => {
      const key = 'test_key';
      const data = { test: 'data' };

      const result = await cacheManager.set(key, data);

      expect(result).toBe(true);
      expect(mockWx.setStorageSync).toHaveBeenCalled();
    });

    test('获取缓存应该返回正确数据', async () => {
      const key = 'test_key';
      const data = { test: 'data' };
      const cacheData = {
        data,
        timestamp: Date.now(),
        expiration: 5 * 60 * 1000
      };

      mockWx.getStorageSync.mockReturnValue(JSON.stringify(cacheData));

      const result = await cacheManager.get(key);

      expect(result).toEqual(data);
      expect(mockWx.getStorageSync).toHaveBeenCalledWith(key);
    });

    test('过期缓存应该返回 null', async () => {
      const key = 'test_key';
      const oldTimestamp = Date.now() - (10 * 60 * 1000); // 10 分钟前
      const cacheData = {
        data: { test: 'data' },
        timestamp: oldTimestamp,
        expiration: 5 * 60 * 1000 // 5 分钟过期
      };

      mockWx.getStorageSync.mockReturnValue(JSON.stringify(cacheData));

      const result = await cacheManager.get(key);

      expect(result).toBeNull();
      expect(mockWx.removeStorageSync).toHaveBeenCalledWith(key);
    });

    test('删除缓存应该成功', async () => {
      const key = 'test_key';

      const result = await cacheManager.remove(key);

      expect(result).toBe(true);
      expect(mockWx.removeStorageSync).toHaveBeenCalledWith(key);
    });

    test('清空缓存应该成功', async () => {
      const result = await cacheManager.clear();

      expect(result).toBe(true);
      expect(mockWx.clearStorageSync).toHaveBeenCalled();
    });

    test('批量设置缓存应该正确统计结果', async () => {
      mockWx.setStorageSync.mockReturnValue(true);

      const items = [
        { key: 'key1', data: 'data1' },
        { key: 'key2', data: 'data2' },
        { key: 'key3', data: 'data3' }
      ];

      const result = await cacheManager.setBatch(items);

      expect(result.success).toBe(3);
      expect(result.failed).toBe(0);
      expect(mockWx.setStorageSync).toHaveBeenCalledTimes(3);
    });

    test('批量获取缓存应该返回正确数据', async () => {
      const cacheData = {
        data: 'test',
        timestamp: Date.now(),
        expiration: 5 * 60 * 1000
      };
      mockWx.getStorageSync.mockReturnValue(JSON.stringify(cacheData));

      const keys = ['key1', 'key2', 'key3'];
      const result = await cacheManager.getBatch(keys);

      expect(Object.keys(result).length).toBe(3);
      expect(result['key1']).toBe('test');
      expect(result['key2']).toBe('test');
      expect(result['key3']).toBe('test');
    });

    test('缓存信息应该包含正确的元数据', async () => {
      const key = 'test_key';
      const timestamp = Date.now() - (2 * 60 * 1000); // 2 分钟前
      const expiration = 5 * 60 * 1000; // 5 分钟过期
      const cacheData = {
        data: { test: 'data' },
        timestamp,
        expiration
      };

      mockWx.getStorageSync.mockReturnValue(JSON.stringify(cacheData));

      const info = await cacheManager.info(key);

      expect(info).toBeDefined();
      expect(info.key).toBe(key);
      expect(info.timestamp).toBe(timestamp);
      expect(info.expiration).toBe(expiration);
      expect(info.age).toBeGreaterThan(0);
      expect(info.remaining).toBeLessThan(expiration);
      expect(info.isExpired).toBe(false);
    });
  });

  describe('缓存策略测试', () => {
    test('白名单 API 应该被缓存', () => {
      const shouldCache = cacheConfig.shouldCacheApi('/api/home/data', 'GET');
      expect(shouldCache).toBe(true);
    });

    test('黑名单 API 不应该被缓存', () => {
      const shouldCache = cacheConfig.shouldCacheApi('/api/auth/login', 'GET');
      expect(shouldCache).toBe(false);
    });

    test('非 GET 请求不应该被缓存', () => {
      const shouldCache = cacheConfig.shouldCacheApi('/api/home/data', 'POST');
      expect(shouldCache).toBe(false);
    });

    test('静态资源路径应该被正确识别', () => {
      expect(cacheConfig.isStaticAsset('/pages/index/index')).toBe(true);
      expect(cacheConfig.isStaticAsset('/components/error-toast/error-toast')).toBe(true);
      expect(cacheConfig.isStaticAsset('/services/reportService')).toBe(true);
      expect(cacheConfig.isStaticAsset('/api/home')).toBe(false);
    });
  });

  describe('缓存过期时间测试', () => {
    test('API 缓存过期时间应该为 5 分钟', () => {
      const expiration = cacheConfig.getCacheExpiration('api');
      expect(expiration).toBe(5 * 60 * 1000);
    });

    test('用户数据缓存过期时间应该为 30 分钟', () => {
      const expiration = cacheConfig.getCacheExpiration('user');
      expect(expiration).toBe(30 * 60 * 1000);
    });

    test('静态资源缓存过期时间应该为 24 小时', () => {
      const expiration = cacheConfig.getCacheExpiration('static');
      expect(expiration).toBe(24 * 60 * 60 * 1000);
    });

    test('未知类型应该使用默认过期时间', () => {
      const expiration = cacheConfig.getCacheExpiration('unknown');
      expect(expiration).toBe(1 * 60 * 1000); // temp 类型的默认值
    });
  });
});

/**
 * 手动测试函数（可在小程序中运行）
 */
const manualTests = {
  /**
   * 测试缓存基本功能
   */
  async testBasicCache() {
    console.log('=== 测试基本缓存功能 ===');
    
    // 设置缓存
    const setResult = await cacheManager.set('test_key', { name: 'test', value: 123 });
    console.log('设置缓存:', setResult);
    
    // 获取缓存
    const getData = await cacheManager.get('test_key');
    console.log('获取缓存:', getData);
    
    // 获取缓存信息
    const getInfo = await cacheManager.info('test_key');
    console.log('缓存信息:', getInfo);
    
    // 删除缓存
    const removeResult = await cacheManager.remove('test_key');
    console.log('删除缓存:', removeResult);
    
    // 验证删除
    const afterDelete = await cacheManager.get('test_key');
    console.log('删除后获取:', afterDelete);
    
    console.log('=== 测试完成 ===');
  },

  /**
   * 测试缓存过期
   */
  async testCacheExpiration() {
    console.log('=== 测试缓存过期 ===');
    
    // 设置一个立即过期的缓存
    await cacheManager.set('expire_test', { data: 'test' }, {
      expiration: 1000 // 1 秒过期
    });
    
    console.log('设置 1 秒过期的缓存');
    
    // 立即获取
    const immediate = await cacheManager.get('expire_test');
    console.log('立即获取:', immediate);
    
    // 等待 2 秒后获取
    console.log('等待 2 秒...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const afterExpire = await cacheManager.get('expire_test');
    console.log('2 秒后获取:', afterExpire);
    
    console.log('=== 测试完成 ===');
  },

  /**
   * 测试批量操作
   */
  async testBatchOperations() {
    console.log('=== 测试批量操作 ===');
    
    // 批量设置
    const items = [
      { key: 'batch_1', data: { id: 1 } },
      { key: 'batch_2', data: { id: 2 } },
      { key: 'batch_3', data: { id: 3 } }
    ];
    
    const setResult = await cacheManager.setBatch(items);
    console.log('批量设置结果:', setResult);
    
    // 批量获取
    const getResult = await cacheManager.getBatch(['batch_1', 'batch_2', 'batch_3']);
    console.log('批量获取结果:', getResult);
    
    // 批量删除
    const deleteResult = await cacheManager.removeBatch(['batch_1', 'batch_2', 'batch_3']);
    console.log('批量删除结果:', deleteResult);
    
    console.log('=== 测试完成 ===');
  },

  /**
   * 测试缓存策略
   */
  testCacheStrategy() {
    console.log('=== 测试缓存策略 ===');
    
    const testCases = [
      { path: '/api/home/data', method: 'GET', expected: true },
      { path: '/api/history/list', method: 'GET', expected: true },
      { path: '/api/auth/login', method: 'GET', expected: false },
      { path: '/api/diagnosis/submit', method: 'POST', expected: false },
      { path: '/pages/index/index', method: 'GET', expected: true },
      { path: '/components/skeleton/skeleton', method: 'GET', expected: true }
    ];
    
    testCases.forEach(({ path, method, expected }) => {
      let result;
      if (cacheConfig.isStaticAsset(path)) {
        result = true;
      } else {
        result = cacheConfig.shouldCacheApi(path, method);
      }
      
      const status = result === expected ? '✓' : '✗';
      console.log(`${status} ${method} ${path}: ${result} (期望：${expected})`);
    });
    
    console.log('=== 测试完成 ===');
  }
};

// 导出测试函数
module.exports = {
  manualTests
};
