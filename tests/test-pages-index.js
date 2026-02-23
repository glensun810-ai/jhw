/**
 * pages/index/index.js 页面交互测试
 *
 * 测试覆盖：
 * - onLoad 生命周期
 * - startBrandTest 交互
 * - restoreDraft 草稿恢复
 * - saveCurrentInput 输入保存
 */

const { describe, test, beforeEach, afterEach, expect, mockWx, createMockFn } = require('./test-utils');
const { createMockPageContext, simulatePageLoad, simulateUserAction, verifySetDataCalled } = require('./test-page-utils');

// Mock 服务模块
const mockServices = {
  initializeDefaults: function(pageContext) {
    pageContext.setData({
      config: {
        estimate: { duration: '30s', steps: 5 },
        brandName: '',
        competitorBrands: [],
        customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
      }
    });
  },
  checkServerConnection: async function(pageContext) {
    pageContext.setData({ serverStatus: '已连接' });
    return true;
  },
  loadUserPlatformPreferences: function(pageContext) {
    pageContext.setData({
      domesticAiModels: [{ name: 'DeepSeek', checked: true }],
      overseasAiModels: [{ name: 'ChatGPT', checked: false }]
    });
  },
  restoreDraft: function() {
    return null; // 无草稿
  },
  saveDraft: function(data) {
    return true;
  }
};

describe('pages/index/index.js 页面交互测试', () => {

  beforeEach(() => {
    // 清空 Mock
    Object.keys(mockWx).forEach(key => {
      if (mockWx[key] && mockWx[key].mockClear) {
        mockWx[key].mockClear();
      }
    });
    
    // 重置 Storage Mock
    mockWx.getStorageSync.mockReturnValue(null);
    mockWx.setStorageSync.mockReturnValue(true);
  });

  describe('onLoad 生命周期测试', () => {
    test('应该正确初始化页面', async () => {
      const pageContext = createMockPageContext();
      
      // 模拟 onLoad
      await simulatePageLoad({
        onLoad: function(options) {
          mockServices.initializeDefaults(this);
          mockServices.checkServerConnection(this);
          mockServices.loadUserPlatformPreferences(this);
        }
      }, {});
      
      // 验证初始化数据
      expect(pageContext.data.config).toBeDefined();
      expect(pageContext.data.serverStatus).toBe('已连接');
    });

    test('应该处理快速启动参数', async () => {
      const pageContext = createMockPageContext();
      let startBrandTestCalled = false;
      
      await simulatePageLoad({
        onLoad: function(options) {
          mockServices.initializeDefaults(this);
          
          if (options && options.quickSearch === 'true') {
            setTimeout(() => {
              startBrandTestCalled = true;
            }, 1000);
          }
        }
      }, { quickSearch: 'true' });
      
      // 等待快速启动
      await new Promise(resolve => setTimeout(resolve, 1100));
      
      expect(startBrandTestCalled).toBe(true);
    });

    test('应该处理初始化失败', async () => {
      const pageContext = createMockPageContext();
      
      // Mock 失败场景
      mockWx.showToast.mockImplementation(() => {});
      
      await simulatePageLoad({
        onLoad: function(options) {
          try {
            throw new Error('初始化失败');
          } catch (error) {
            this.setData({
              serverStatus: '初始化失败'
            });
            mockWx.showToast({
              title: '初始化失败，请刷新重试',
              icon: 'none'
            });
          }
        }
      }, {});
      
      expect(pageContext.data.serverStatus).toBe('初始化失败');
      expect(mockWx.showToast.calls.length).toBe(1);
    });
  });

  describe('startBrandTest 交互测试', () => {
    test('应该验证品牌名称', async () => {
      const pageContext = createMockPageContext({
        brandName: '',
        domesticAiModels: [{ name: 'deepseek', checked: true }],
        customQuestions: [{ text: '问题 1', show: true }]
      });
      
      mockWx.showToast.mockImplementation(() => {});
      
      // 模拟启动诊断
      const startBrandTest = function() {
        const brandName = this.data.brandName.trim();
        if (!brandName) {
          mockWx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
          return;
        }
      };
      
      startBrandTest.call(pageContext);
      
      expect(mockWx.showToast.calls.length).toBe(1);
      expect(mockWx.showToast.calls[0][0].title).toContain('品牌名称');
    });

    test('应该验证 AI 模型选择', async () => {
      const pageContext = createMockPageContext({
        brandName: '品牌 A',
        domesticAiModels: [{ name: 'deepseek', checked: false }],
        customQuestions: [{ text: '问题 1', show: true }]
      });
      
      mockWx.showToast.mockImplementation(() => {});
      
      const startBrandTest = function() {
        const brandName = this.data.brandName.trim();
        if (!brandName) {
          mockWx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
          return;
        }
        
        let selectedModels = this.data.domesticAiModels.filter(m => m.checked);
        if (selectedModels.length === 0) {
          mockWx.showToast({ title: '请选择至少一个 AI 模型', icon: 'error' });
          return;
        }
      };
      
      startBrandTest.call(pageContext);
      
      expect(mockWx.showToast.calls.length).toBe(1);
      expect(mockWx.showToast.calls[0][0].title).toContain('AI 模型');
    });

    test('应该正确启动诊断', async () => {
      const pageContext = createMockPageContext({
        brandName: '品牌 A',
        competitorBrands: ['品牌 B'],
        domesticAiModels: [{ name: 'deepseek', checked: true }],
        customQuestions: [{ text: '问题 1', show: true }]
      });
      
      mockWx.showLoading.mockImplementation(() => {});
      
      const startBrandTest = function() {
        const brandName = this.data.brandName.trim();
        if (!brandName) {
          mockWx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
          return;
        }
        
        this.setData({
          isTesting: true,
          testProgress: 0,
          progressText: '正在启动 AI 认知诊断...'
        });
        
        mockWx.showLoading({ title: '启动诊断...' });
      };
      
      startBrandTest.call(pageContext);
      
      expect(pageContext.data.isTesting).toBe(true);
      expect(pageContext.data.testProgress).toBe(0);
      expect(mockWx.showLoading.calls.length).toBe(1);
    });
  });

  describe('restoreDraft 草稿恢复测试', () => {
    test('应该恢复草稿数据', async () => {
      const draftData = {
        brandName: '恢复品牌',
        currentCompetitor: '',
        competitorBrands: ['竞品 A'],
        customQuestions: [{ text: '恢复问题', show: true }],
        selectedModels: {
          domestic: ['deepseek'],
          overseas: []
        },
        updatedAt: Date.now()
      };
      
      mockWx.getStorageSync.mockReturnValue(draftData);
      
      const pageContext = createMockPageContext({
        domesticAiModels: [{ name: 'deepseek', checked: false, disabled: false }],
        overseasAiModels: [],
        customQuestions: [{ text: '', show: true }]
      });
      
      // 模拟草稿恢复
      const restoreDraft = function() {
        const draft = mockWx.getStorageSync('draft_diagnostic_input');
        
        if (draft && draft.brandName) {
          const now = Date.now();
          const draftAge = now - (draft.updatedAt || 0);
          const sevenDays = 7 * 24 * 60 * 60 * 1000;
          
          if (draftAge < sevenDays) {
            this.setData({
              brandName: draft.brandName || '',
              competitorBrands: draft.competitorBrands || [],
              customQuestions: draft.customQuestions || []
            });
          }
        }
      };
      
      restoreDraft.call(pageContext);
      
      expect(pageContext.data.brandName).toBe('恢复品牌');
      expect(pageContext.data.competitorBrands).toContain('竞品 A');
    });

    test('应该跳过过期草稿', async () => {
      const oldDraft = {
        brandName: '过期品牌',
        updatedAt: Date.now() - (8 * 24 * 60 * 60 * 1000) // 8 天前
      };
      
      mockWx.getStorageSync.mockReturnValue(oldDraft);
      mockWx.removeStorageSync.mockImplementation(() => {});
      
      const pageContext = createMockPageContext({
        brandName: '当前品牌'
      });
      
      const restoreDraft = function() {
        const draft = mockWx.getStorageSync('draft_diagnostic_input');
        
        if (draft && draft.brandName) {
          const now = Date.now();
          const draftAge = now - (draft.updatedAt || 0);
          const sevenDays = 7 * 24 * 60 * 60 * 1000;
          
          if (draftAge >= sevenDays) {
            mockWx.removeStorageSync('draft_diagnostic_input');
            return;
          }
        }
      };
      
      restoreDraft.call(pageContext);
      
      // 草稿过期，不应恢复
      expect(pageContext.data.brandName).toBe('当前品牌');
      expect(mockWx.removeStorageSync.calls.length).toBe(1);
    });
  });

  describe('saveCurrentInput 输入保存测试', () => {
    test('应该保存当前输入', async () => {
      const pageContext = createMockPageContext({
        brandName: '保存品牌',
        currentCompetitor: '竞品',
        competitorBrands: ['竞品 A'],
        customQuestions: [{ text: '问题', show: true }],
        domesticAiModels: [{ name: 'deepseek', checked: true }],
        overseasAiModels: [{ name: 'chatgpt', checked: false }]
      });
      
      mockWx.setStorageSync.mockImplementation(() => {});
      
      const saveCurrentInput = function() {
        const { brandName, currentCompetitor, competitorBrands, customQuestions, domesticAiModels, overseasAiModels } = this.data;
        
        const selectedDomestic = domesticAiModels
          .filter(model => model.checked)
          .map(model => model.name);
        
        const selectedOverseas = overseasAiModels
          .filter(model => model.checked)
          .map(model => model.name);
        
        mockWx.setStorageSync('draft_diagnostic_input', {
          brandName: brandName || '',
          currentCompetitor: currentCompetitor || '',
          competitorBrands: competitorBrands || [],
          customQuestions: customQuestions || [],
          selectedModels: {
            domestic: selectedDomestic,
            overseas: selectedOverseas
          },
          updatedAt: Date.now()
        });
      };
      
      saveCurrentInput.call(pageContext);
      
      expect(mockWx.setStorageSync.calls.length).toBe(1);
      expect(mockWx.setStorageSync.calls[0][0]).toBe('draft_diagnostic_input');
    });
  });
});

// 运行测试
if (require.main === module) {
  const { runTests } = require('./test-utils');
  runTests();
}
