/**
 * dataLoaderService 单元测试
 * 测试覆盖率目标：90%
 */

const { loadDiagnosisData, loadFromStorage, loadFromApi, LOAD_CONFIG, LoadResult } = require('../dataLoaderService');

// Mock wx API
global.wx = {
  getStorageSync: jest.fn(),
  setStorageSync: jest.fn(),
  removeStorageSync: jest.fn()
};

// Mock require
jest.mock('../storage-manager', () => ({
  loadDiagnosisResult: jest.fn()
}));

jest.mock('../utils/request', () => ({
  get: jest.fn()
}));

const { loadDiagnosisResult } = require('../storage-manager');
const { get } = require('../utils/request');

describe('dataLoaderService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('LoadResult', () => {
    test('创建成功结果', () => {
      const data = { results: [{ brand: 'test' }] };
      const result = LoadResult.success(data, true);
      
      expect(result.success).toBe(true);
      expect(result.data).toEqual(data);
      expect(result.fromCache).toBe(true);
      expect(result.error).toBeNull();
    });

    test('创建错误结果', () => {
      const result = LoadResult.error('测试错误');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('测试错误');
      expect(result.data).toBeNull();
    });
  });

  describe('loadFromStorage', () => {
    test('缺少 executionId 时返回错误', () => {
      const result = loadFromStorage('');
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('缺少 executionId');
    });

    test('Storage 无数据时返回错误', () => {
      loadDiagnosisResult.mockReturnValue(null);
      
      const result = loadFromStorage('test-id');
      
      expect(result.success).toBe(false);
      expect(loadDiagnosisResult).toHaveBeenCalledWith('test-id');
    });

    test('Storage 数据不完整时返回错误', () => {
      loadDiagnosisResult.mockReturnValue({
        version: '2.0',
        data: { results: [] }
      });
      
      const result = loadFromStorage('test-id');
      
      expect(result.success).toBe(false);
    });

    test('Storage 数据完整时返回成功', () => {
      const mockData = {
        version: '2.0',
        data: {
          results: [{ brand: 'test', geo_data: {} }],
          competitive_analysis: {},
          brand_scores: {}
        }
      };
      loadDiagnosisResult.mockReturnValue(mockData);
      
      const result = loadFromStorage('test-id');
      
      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(true);
      expect(result.data).toEqual(mockData.data);
    });
  });

  describe('loadFromApi', () => {
    test('缺少 executionId 时返回错误', async () => {
      const result = await loadFromApi('');
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('缺少 executionId');
    });

    test('API 返回空数据时返回错误', async () => {
      get.mockResolvedValue(null);
      
      const result = await loadFromApi('test-id');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('API 返回空数据');
    });

    test('API 返回空结果时返回错误', async () => {
      get.mockResolvedValue({
        status: 'success',
        results: []
      });
      
      const result = await loadFromApi('test-id');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('API 返回空结果');
    });

    test('API 返回完整数据时返回成功', async () => {
      const mockData = {
        detailed_results: [{ brand: 'test', geo_data: {} }],
        competitive_analysis: {},
        brand_scores: {}
      };
      get.mockResolvedValue(mockData);
      
      const result = await loadFromApi('test-id');
      
      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(false);
      expect(result.data.results).toEqual(mockData.detailed_results);
    });

    test('API 调用失败时返回错误', async () => {
      get.mockRejectedValue(new Error('网络错误'));
      
      const result = await loadFromApi('test-id');
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('网络错误');
    });
  });

  describe('loadDiagnosisData', () => {
    test('forceRefresh 时跳过缓存直接从 API 加载', async () => {
      const mockApiData = {
        results: [{ brand: 'test' }],
        competitive_analysis: {},
        brand_scores: {}
      };
      get.mockResolvedValue(mockApiData);
      
      const result = await loadDiagnosisData('test-id', { forceRefresh: true });
      
      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(false);
      expect(loadDiagnosisResult).not.toHaveBeenCalled();
    });

    test('useCacheOnly 时只从缓存加载', async () => {
      loadDiagnosisResult.mockReturnValue(null);
      
      const result = await loadDiagnosisData('test-id', { useCacheOnly: true });
      
      expect(result.success).toBe(false);
      expect(get).not.toHaveBeenCalled();
    });

    test('缓存命中时返回缓存数据', async () => {
      const mockStorageData = {
        version: '2.0',
        data: {
          results: [{ brand: 'test' }],
          competitive_analysis: {},
          brand_scores: {}
        }
      };
      loadDiagnosisResult.mockReturnValue(mockStorageData);
      
      const result = await loadDiagnosisData('test-id');
      
      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(true);
      expect(get).not.toHaveBeenCalled();
    });

    test('缓存未命中时从 API 加载', async () => {
      loadDiagnosisResult.mockReturnValue(null);
      
      const mockApiData = {
        detailed_results: [{ brand: 'test' }],
        competitive_analysis: {},
        brand_scores: {}
      };
      get.mockResolvedValue(mockApiData);
      
      const result = await loadDiagnosisData('test-id');
      
      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(false);
    });
  });

  describe('LOAD_CONFIG', () => {
    test('配置值正确', () => {
      expect(LOAD_CONFIG.STORAGE_KEY_PREFIX).toBe('diagnosis_');
      expect(LOAD_CONFIG.CACHE_TTL).toBe(60 * 60 * 1000); // 1 小时
      expect(LOAD_CONFIG.ENABLE_CACHE).toBe(true);
    });
  });
});
