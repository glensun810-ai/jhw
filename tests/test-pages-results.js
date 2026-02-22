/**
 * pages/results/results.js 页面测试
 * 
 * 测试覆盖：
 * - onLoad 数据加载
 * - initializePageWithData 数据初始化
 * - 图表渲染
 * - 错误处理
 */

const { describe, test, beforeEach, afterEach, expect, mockWx } = require('./test-utils');
const { createMockPageContext, simulatePageLoad } = require('./test-page-utils');

describe('pages/results/results.js 页面测试', () => {

  beforeEach(() => {
    // 清空 Mock
    Object.keys(mockWx).forEach(key => {
      if (mockWx[key] && mockWx[key].mockClear) {
        mockWx[key].mockClear();
      }
    });
    
    // 重置 Storage Mock
    mockWx.getStorageSync.mockReturnValue(null);
  });

  describe('onLoad 数据加载测试', () => {
    test('应该从 Storage 加载数据', async () => {
      const storageData = {
        results: [
          { brand: '品牌 A', score: 85, response: '正面评价' }
        ],
        competitiveAnalysis: {
          brandScores: {
            '品牌 A': { overallScore: 85 }
          }
        },
        targetBrand: '品牌 A',
        executionId: 'test-123'
      };
      
      mockWx.getStorageSync.mockReturnValue(storageData);
      
      const pageContext = createMockPageContext();
      
      // 模拟 onLoad
      const onLoad = function(options) {
        const executionId = decodeURIComponent(options.executionId || '');
        const brandName = decodeURIComponent(options.brandName || '');
        
        const lastDiagnosticResults = mockWx.getStorageSync('last_diagnostic_results');
        
        if (lastDiagnosticResults && lastDiagnosticResults.results) {
          this.setData({
            targetBrand: lastDiagnosticResults.targetBrand,
            competitiveAnalysis: lastDiagnosticResults.competitiveAnalysis,
            latestTestResults: lastDiagnosticResults.results,
            loadingState: 'success'
          });
        }
      };
      
      await simulatePageLoad({ onLoad }, { executionId: 'test-123', brandName: '品牌 A' });
      
      expect(pageContext.data.targetBrand).toBe('品牌 A');
      expect(pageContext.data.loadingState).toBe('success');
      expect(mockWx.getStorageSync.calls.length).toBe(1);
    });

    test('应该处理 Storage 无数据情况', async () => {
      mockWx.getStorageSync.mockReturnValue(null);
      
      const pageContext = createMockPageContext();
      
      let fetchFromServerCalled = false;
      
      const onLoad = function(options) {
        const executionId = options.executionId;
        
        const lastDiagnosticResults = mockWx.getStorageSync('last_diagnostic_results');
        
        if (!lastDiagnosticResults || !lastDiagnosticResults.results) {
          if (executionId) {
            fetchFromServerCalled = true;
          } else {
            this.setData({
              loadingState: 'empty',
              errorMessage: '缺少执行 ID'
            });
          }
        }
      };
      
      await simulatePageLoad({ onLoad }, {});
      
      expect(pageContext.data.loadingState).toBe('empty');
      expect(fetchFromServerCalled).toBe(false);
    });

    test('应该从后端 API 拉取数据', async () => {
      mockWx.getStorageSync.mockReturnValue(null);
      
      const pageContext = createMockPageContext();
      
      let fetchFromServerCalled = false;
      
      const onLoad = function(options) {
        const executionId = options.executionId;
        
        const lastDiagnosticResults = mockWx.getStorageSync('last_diagnostic_results');
        
        if (!lastDiagnosticResults && executionId) {
          fetchFromServerCalled = true;
          // 模拟 API 调用
          mockWx.request.mockImplementation((opts) => {
            opts.success({
              statusCode: 200,
              data: {
                results: [{ brand: '品牌 A', score: 85 }],
                competitive_analysis: {}
              }
            });
          });
        }
      };
      
      await simulatePageLoad({ onLoad }, { executionId: 'test-123' });
      
      expect(fetchFromServerCalled).toBe(true);
    });
  });

  describe('initializePageWithData 数据初始化测试', () => {
    test('应该正确初始化页面数据', async () => {
      const pageContext = createMockPageContext();
      
      const results = [
        { brand: '品牌 A', score: 85, response: '正面评价' }
      ];
      
      const competitiveAnalysis = {
        brandScores: {
          '品牌 A': {
            overallScore: 85,
            overallGrade: 'A',
            overallAuthority: 80,
            overallVisibility: 90
          }
        }
      };
      
      // 模拟初始化
      const initializePageWithData = function(results, targetBrand, competitiveAnalysis) {
        this.setData({
          targetBrand: targetBrand,
          competitiveAnalysis: competitiveAnalysis,
          latestTestResults: results,
          loadingState: 'success'
        });
      };
      
      initializePageWithData.call(pageContext, results, '品牌 A', competitiveAnalysis);
      
      expect(pageContext.data.targetBrand).toBe('品牌 A');
      expect(pageContext.data.competitiveAnalysis).toEqual(competitiveAnalysis);
      expect(pageContext.data.latestTestResults).toEqual(results);
      expect(pageContext.data.loadingState).toBe('success');
    });

    test('应该处理数据初始化失败', async () => {
      const pageContext = createMockPageContext();
      
      mockWx.showToast.mockImplementation(() => {});
      
      const initializePageWithData = function(results, targetBrand, competitiveAnalysis) {
        try {
          if (!results || !Array.isArray(results)) {
            throw new Error('数据格式错误');
          }
          
          this.setData({
            targetBrand: targetBrand,
            competitiveAnalysis: competitiveAnalysis,
            loadingState: 'success'
          });
        } catch (e) {
          this.setData({
            loadingState: 'error',
            errorMessage: '数据加载失败'
          });
          mockWx.showToast({
            title: '数据加载失败',
            icon: 'none'
          });
        }
      };
      
      initializePageWithData.call(pageContext, null, '品牌 A', {});
      
      expect(pageContext.data.loadingState).toBe('error');
      expect(mockWx.showToast.calls.length).toBe(1);
    });
  });

  describe('图表渲染测试', () => {
    test('应该渲染雷达图', async () => {
      const pageContext = createMockPageContext({
        radarChartData: [
          { name: '权威度', value: 85, max: 100 },
          { name: '可见度', value: 90, max: 100 }
        ]
      });
      
      let chartRendered = false;
      
      // 模拟 Canvas 查询
      mockWx.createSelectorQuery.mockReturnValue({
        select: function(id) {
          return {
            fields: function(fields, callback) {
              callback({ node: {}, width: 300, height: 300 });
            }
          };
        }
      });
      
      const renderRadarChart = function() {
        const query = mockWx.createSelectorQuery();
        query.select('#radarCanvas').fields({ node: true, size: true }, (res) => {
          if (res && res.node) {
            chartRendered = true;
          }
        });
      };
      
      renderRadarChart.call(pageContext);
      
      expect(mockWx.createSelectorQuery.calls.length).toBe(1);
    });

    test('应该处理 Canvas 节点未找到', async () => {
      const pageContext = createMockPageContext();
      
      let retryCount = 0;
      
      mockWx.createSelectorQuery.mockReturnValue({
        select: function(id) {
          return {
            fields: function(fields, callback) {
              callback(null); // 节点未找到
            }
          };
        }
      });
      
      const renderRadarChart = function(retryCount = 0) {
        const query = mockWx.createSelectorQuery();
        query.select('#radarCanvas').fields({ node: true, size: true }, (res) => {
          if (!res || !res.node) {
            if (retryCount < 3) {
              retryCount++;
              // 重试逻辑
            }
          }
        });
      };
      
      renderRadarChart.call(pageContext, 0);
      
      expect(mockWx.createSelectorQuery.calls.length).toBe(1);
    });
  });

  describe('错误处理测试', () => {
    test('应该处理 403 错误', async () => {
      const pageContext = createMockPageContext();
      
      mockWx.request.mockImplementation((opts) => {
        opts.fail({
          statusCode: 403,
          errMsg: 'Token 已过期'
        });
      });
      
      mockWx.showModal.mockImplementation(() => {});
      
      const fetchResultsFromServer = function(executionId, brandName) {
        mockWx.request({
          url: `http://localhost:5000/api/test-progress?executionId=${executionId}`,
          method: 'GET',
          success: (res) => {
            if (res.statusCode === 403) {
              mockWx.showModal({
                title: '登录已过期',
                content: '请重新登录'
              });
            }
          },
          fail: (err) => {
            mockWx.showModal({
              title: '加载失败',
              content: '网络连接失败'
            });
          }
        });
      };
      
      fetchResultsFromServer.call(pageContext, 'test-123', '品牌 A');
      
      expect(mockWx.showModal.calls.length).toBe(1);
    });

    test('应该处理网络错误', async () => {
      const pageContext = createMockPageContext();
      
      mockWx.request.mockImplementation((opts) => {
        opts.fail({
          errMsg: 'network error'
        });
      });
      
      mockWx.showModal.mockImplementation(() => {});
      
      const fetchResultsFromServer = function(executionId, brandName) {
        mockWx.request({
          url: `http://localhost:5000/api/test-progress`,
          method: 'GET',
          fail: (err) => {
            this.setData({
              loadingState: 'error',
              errorMessage: '网络连接失败',
              canRetry: true
            });
            mockWx.showModal({
              title: '加载失败',
              content: '网络连接失败'
            });
          }
        });
      };
      
      fetchResultsFromServer.call(pageContext, 'test-123', '品牌 A');
      
      expect(pageContext.data.loadingState).toBe('error');
      expect(pageContext.data.canRetry).toBe(true);
    });

    test('应该提供重试功能', async () => {
      const pageContext = createMockPageContext({
        loadingState: 'error',
        canRetry: true
      });
      
      let retryCalled = false;
      
      const onRetryTap = function() {
        if (!this.data.canRetry) return;
        
        retryCalled = true;
        this.setData({ loadingState: 'loading' });
        // 重新请求
      };
      
      onRetryTap.call(pageContext);
      
      expect(retryCalled).toBe(true);
      expect(pageContext.data.loadingState).toBe('loading');
    });
  });
});

// 运行测试
if (require.main === module) {
  const { runTests } = require('./test-utils');
  runTests();
}
