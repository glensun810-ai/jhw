/**
 * 品牌诊断端到端集成测试
 * 
 * 测试完整诊断流程：从启动到获取结果
 * 覆盖率目标：核心流程 100%
 */

const { loadDiagnosisData } = require('../dataLoaderService');
const { parseTaskStatus } = require('../taskStatusService');

// Mock wx API
global.wx = {
  getStorageSync: jest.fn(),
  setStorageSync: jest.fn(),
  removeStorageSync: jest.fn(),
  showLoading: jest.fn(),
  hideLoading: jest.fn(),
  showModal: jest.fn(),
  showToast: jest.fn()
};

// Mock 依赖
jest.mock('../storage-manager', () => ({
  loadDiagnosisResult: jest.fn()
}));

jest.mock('../utils/request', () => ({
  get: jest.fn()
}));

const { loadDiagnosisResult } = require('../storage-manager');
const { get } = require('../utils/request');

describe('品牌诊断集成测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('完整诊断流程', () => {
    test('从启动到获取结果的完整流程', async () => {
      // 场景 1: 缓存命中
      const mockStorageData = {
        version: '2.0',
        data: {
          results: [
            { brand: '华为', geo_data: { rank: 1, sentiment: 0.8 } },
            { brand: '华为', geo_data: { rank: 2, sentiment: 0.7 } }
          ],
          competitive_analysis: {},
          brand_scores: {}
        },
        timestamp: Date.now()
      };
      loadDiagnosisResult.mockReturnValue(mockStorageData);

      const result = await loadDiagnosisData('test-execution-id');

      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(true);
      expect(result.data.results.length).toBe(2);
      expect(loadDiagnosisResult).toHaveBeenCalledWith('test-execution-id');
    });

    test('缓存未命中时从 API 加载', async () => {
      // 场景 2: 缓存未命中，从 API 加载
      loadDiagnosisResult.mockReturnValue(null);

      const mockApiData = {
        detailed_results: [
          { brand: '华为', geo_data: { rank: 1, sentiment: 0.8 } }
        ],
        competitive_analysis: {},
        brand_scores: {},
        quality_score: 85,
        quality_level: 'good'
      };
      get.mockResolvedValue(mockApiData);

      const result = await loadDiagnosisData('test-execution-id');

      expect(result.success).toBe(true);
      expect(result.fromCache).toBe(false);
      expect(result.data.quality_score).toBe(85);
      expect(get).toHaveBeenCalledWith('/test/status/test-execution-id');
    });

    test('部分完成场景', async () => {
      // 场景 3: 部分完成（有警告）
      loadDiagnosisResult.mockReturnValue(null);

      const mockPartialData = {
        detailed_results: [
          { brand: '华为', geo_data: { rank: 1, sentiment: 0.8 } },
          { brand: '华为', geo_data: { rank: 2, sentiment: 0.7 } },
          { brand: '华为', geo_data: { rank: 3, sentiment: 0.6 } }
        ],
        competitive_analysis: {},
        brand_scores: {},
        warning: '部分结果缺失：3/10',
        missing_count: 7,
        quality_score: 62,
        quality_level: 'fair'
      };
      get.mockResolvedValue(mockPartialData);

      const result = await loadDiagnosisData('test-execution-id');

      expect(result.success).toBe(true);
      expect(result.data.warning).toBe('部分结果缺失：3/10');
      expect(result.data.missing_count).toBe(7);
      expect(result.data.quality_score).toBe(62);
    });

    test('完全失败场景', async () => {
      // 场景 4: 完全失败
      loadDiagnosisResult.mockReturnValue(null);
      get.mockRejectedValue(new Error('AI 平台调用失败'));

      const result = await loadDiagnosisData('test-execution-id');

      expect(result.success).toBe(false);
      expect(result.error).toContain('AI 平台调用失败');
    });
  });

  describe('进度状态解析集成', () => {
    const startTime = Date.now() - 120000; // 2 分钟前

    test('完整诊断进度流程', () => {
      // 模拟完整的诊断进度变化
      const stages = [
        { stage: 'init', expectedProgress: 10, expectedText: '任务初始化中' },
        { stage: 'ai_fetching', results: [{}], expectedProgress: 30, expectedText: '正在连接 AI' },
        { stage: 'intelligence_analyzing', results: [{}, {}], expectedProgress: 60, expectedText: '深度分析' },
        { stage: 'competition_analyzing', results: [{}, {}, {}], expectedProgress: 80, expectedText: '竞争分析' },
        { stage: 'completed', results: [{}, {}, {}, {}], expectedProgress: 100, expectedText: '诊断完成' }
      ];

      stages.forEach(({ stage, results, expectedProgress, expectedText }) => {
        const status = parseTaskStatus({ stage, results }, startTime);
        
        expect(status.progress).toBeGreaterThanOrEqual(expectedProgress - 5);
        expect(status.progress).toBeLessThanOrEqual(expectedProgress + 5);
        expect(status.detailText).toBeTruthy();
        expect(status.remainingTime).toBeTruthy();
      });
    });

    test('部分完成状态解析', () => {
      const status = parseTaskStatus({
        stage: 'completed',
        results: [{}, {}],
        warning: '部分结果缺失',
        missing_count: 8,
        quality_score: 62
      }, startTime);

      expect(status.is_completed).toBe(true);
      expect(status.resultsCount).toBe(2);
      expect(status.detailText).toContain('诊断完成');
    });

    test('失败状态解析', () => {
      const status = parseTaskStatus({
        stage: 'failed',
        error: 'AI 平台调用失败'
      }, startTime);

      expect(status.is_completed).toBe(false);
      expect(status.progress).toBe(0);
      expect(status.detailText).toBe('AI 平台调用失败');
    });
  });

  describe('边界条件测试', () => {
    test('空 executionId', async () => {
      const result = await loadDiagnosisData('');
      expect(result.success).toBe(false);
      expect(result.error).toContain('缺少 executionId');
    });

    test('空结果数组', async () => {
      loadDiagnosisResult.mockReturnValue(null);
      get.mockResolvedValue({
        detailed_results: [],
        competitive_analysis: {},
        brand_scores: {}
      });

      const result = await loadDiagnosisData('test-id');
      expect(result.success).toBe(false);
      expect(result.error).toBe('API 返回空结果');
    });

    test('超时错误', async () => {
      loadDiagnosisResult.mockReturnValue(null);
      get.mockRejectedValue(new Error('timeout'));

      const result = await loadDiagnosisData('test-id');
      expect(result.success).toBe(false);
      expect(result.error).toContain('timeout');
    });

    test('网络错误', async () => {
      loadDiagnosisResult.mockReturnValue(null);
      get.mockRejectedValue(new Error('request:fail'));

      const result = await loadDiagnosisData('test-id');
      expect(result.success).toBe(false);
      expect(result.error).toContain('request:fail');
    });
  });

  describe('性能测试', () => {
    test('缓存加载性能', async () => {
      const mockData = {
        version: '2.0',
        data: { results: [{ brand: 'test' }] }
      };
      loadDiagnosisResult.mockReturnValue(mockData);

      const start = Date.now();
      for (let i = 0; i < 100; i++) {
        await loadDiagnosisData('test-id');
      }
      const duration = Date.now() - start;

      expect(duration).toBeLessThan(5000); // 100 次加载应在 5 秒内完成
      console.log(`缓存加载性能：${duration}ms / 100 次 = ${duration/100}ms/次`);
    });

    test('状态解析性能', () => {
      const start = Date.now();
      for (let i = 0; i < 1000; i++) {
        parseTaskStatus({
          stage: 'intelligence_analyzing',
          progress: 60,
          results: Array(10).fill({})
        }, start);
      }
      const duration = Date.now() - start;

      expect(duration).toBeLessThan(1000); // 1000 次解析应在 1 秒内完成
      console.log(`状态解析性能：${duration}ms / 1000 次 = ${duration/1000}ms/次`);
    });
  });
});
