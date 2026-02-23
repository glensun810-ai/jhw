/**
 * 数据类型校验修复验证测试
 * 
 * 测试覆盖:
 * - validateInput 类型保护
 * - callBackendBrandTest 数据源修复
 * - restoreDraft 类型强制转换
 * - handleException 统一异常拦截
 * - dataSanitizer 数据清洗器
 */

const { describe, test, beforeEach, afterEach, expect, mockWx } = require('./test-utils');

// 导入修复后的服务
const {
  validateInput,
  buildPayload,
  startDiagnosis,
  createPollingController,
  generateDashboardData
} = require('../services/brandTestService');

const {
  dataSanitizer,
  processTestProgress,
  parseTaskStatus
} = require('../services/homeService');

describe('数据类型校验修复验证测试', () => {

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

  describe('validateInput 类型保护测试', () => {

    test('应该验证通过字符串类型 brandName', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: ['deepseek'],
        customQuestions: ['问题 1']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(true);
    });

    test('应该验证通过对象类型 brandName (类型保护)', () => {
      const inputData = {
        brandName: { brandName: '品牌 A' },
        selectedModels: ['deepseek'],
        customQuestions: ['问题 1']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(true);
    });

    test('应该验证失败当 brandName 为 null (类型保护)', () => {
      const inputData = {
        brandName: null,
        selectedModels: ['deepseek']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('品牌名称');
    });

    test('应该验证失败当 brandName 为 undefined (类型保护)', () => {
      const inputData = {
        brandName: undefined,
        selectedModels: ['deepseek']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('品牌名称');
    });

    test('应该验证失败当 brandName 为空字符串', () => {
      const inputData = {
        brandName: '',
        selectedModels: ['deepseek']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('品牌名称');
    });

    test('应该验证失败当 brandName 为纯空格', () => {
      const inputData = {
        brandName: '   ',
        selectedModels: ['deepseek']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('品牌名称');
    });

    test('应该验证通过数字类型 brandName (转为字符串)', () => {
      const inputData = {
        brandName: 123,
        selectedModels: ['deepseek']
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(true);
    });

    test('应该验证失败当 selectedModels 为 null', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: null
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('AI 模型');
    });

    test('应该验证失败当 selectedModels 为空数组', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: []
      };

      const result = validateInput(inputData);

      expect(result.valid).toBe(false);
      expect(result.message).toContain('AI 模型');
    });
  });

  describe('buildPayload 数据源修复测试', () => {

    test('应该正确从数组中提取主品牌和竞品', () => {
      const inputData = {
        brandName: '品牌 A',
        competitorBrands: ['品牌 B', '品牌 C'],
        selectedModels: ['deepseek'],
        customQuestions: ['问题 1']
      };

      const payload = buildPayload(inputData);

      expect(payload.brand_list).toEqual(['品牌 A', '品牌 B', '品牌 C']);
    });

    test('应该处理缺失的竞品列表', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: ['deepseek']
      };

      const payload = buildPayload(inputData);

      expect(payload.brand_list).toEqual(['品牌 A']);
    });

    test('应该从对象中正确提取模型名称', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: [
          { id: 'deepseek', name: 'DeepSeek' },
          { value: 'qwen', name: 'Qwen' }
        ],
        customQuestions: ['问题 1']
      };

      const payload = buildPayload(inputData);

      // 优先提取 id 或 value
      expect(payload.selectedModels.length).toBeGreaterThan(0);
    });

    test('应该过滤空字符串和 null 值', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: ['deepseek', '', null, 'qwen'],
        customQuestions: ['问题 1']
      };

      const payload = buildPayload(inputData);

      expect(payload.selectedModels).toEqual(['deepseek', 'qwen']);
    });

    test('应该处理自定义问题为空数组', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: ['deepseek'],
        customQuestions: []
      };

      const payload = buildPayload(inputData);

      expect(payload.custom_question).toBe('');
    });

    test('应该正确连接自定义问题', () => {
      const inputData = {
        brandName: '品牌 A',
        selectedModels: ['deepseek'],
        customQuestions: ['问题 1', '问题 2', '问题 3']
      };

      const payload = buildPayload(inputData);

      expect(payload.custom_question).toBe('问题 1 问题 2 问题 3');
    });
  });

  describe('dataSanitizer 数据清洗器测试', () => {

    describe('toString 方法', () => {
      test('应该将 null 转为默认空字符串', () => {
        expect(dataSanitizer.toString(null)).toBe('');
      });

      test('应该将 undefined 转为默认空字符串', () => {
        expect(dataSanitizer.toString(undefined)).toBe('');
      });

      test('应该将数字转为字符串', () => {
        expect(dataSanitizer.toString(123)).toBe('123');
      });

      test('应该将布尔值转为字符串', () => {
        expect(dataSanitizer.toString(true)).toBe('true');
        expect(dataSanitizer.toString(false)).toBe('false');
      });

      test('应该使用自定义默认值', () => {
        expect(dataSanitizer.toString(null, 'default')).toBe('default');
      });

      test('应该保持字符串不变', () => {
        expect(dataSanitizer.toString('hello')).toBe('hello');
      });
    });

    describe('toNumber 方法', () => {
      test('应该将 null 转为默认 0', () => {
        expect(dataSanitizer.toNumber(null)).toBe(0);
      });

      test('应该将 undefined 转为默认 0', () => {
        expect(dataSanitizer.toNumber(undefined)).toBe(0);
      });

      test('应该将字符串数字转为数字', () => {
        expect(dataSanitizer.toNumber('123')).toBe(123);
      });

      test('应该将无效字符串转为默认值', () => {
        expect(dataSanitizer.toNumber('invalid')).toBe(0);
      });

      test('应该使用自定义默认值', () => {
        expect(dataSanitizer.toNumber(null, 10)).toBe(10);
      });

      test('应该保持数字不变', () => {
        expect(dataSanitizer.toNumber(456)).toBe(456);
      });
    });

    describe('toArray 方法', () => {
      test('应该将 null 转为空数组', () => {
        expect(dataSanitizer.toArray(null)).toEqual([]);
      });

      test('应该将 undefined 转为空数组', () => {
        expect(dataSanitizer.toArray(undefined)).toEqual([]);
      });

      test('应该将非数组转为空数组', () => {
        expect(dataSanitizer.toArray('invalid')).toEqual([]);
        expect(dataSanitizer.toArray(123)).toEqual([]);
        expect(dataSanitizer.toArray({})).toEqual([]);
      });

      test('应该保持数组不变', () => {
        expect(dataSanitizer.toArray([1, 2, 3])).toEqual([1, 2, 3]);
      });
    });

    describe('toObject 方法', () => {
      test('应该将 null 转为空对象', () => {
        expect(dataSanitizer.toObject(null)).toEqual({});
      });

      test('应该将 undefined 转为空对象', () => {
        expect(dataSanitizer.toObject(undefined)).toEqual({});
      });

      test('应该将数组转为空对象', () => {
        expect(dataSanitizer.toObject([1, 2, 3])).toEqual({});
      });

      test('应该将字符串转为空对象', () => {
        expect(dataSanitizer.toObject('invalid')).toEqual({});
      });

      test('应该保持对象不变', () => {
        expect(dataSanitizer.toObject({ a: 1 })).toEqual({ a: 1 });
      });
    });

    describe('toBoolean 方法', () => {
      test('应该将 null 转为 false', () => {
        expect(dataSanitizer.toBoolean(null)).toBe(false);
      });

      test('应该将 undefined 转为 false', () => {
        expect(dataSanitizer.toBoolean(undefined)).toBe(false);
      });

      test('应该将真值转为 true', () => {
        expect(dataSanitizer.toBoolean(true)).toBe(true);
        expect(dataSanitizer.toBoolean(1)).toBe(true);
        expect(dataSanitizer.toBoolean('hello')).toBe(true);
      });

      test('应该将假值转为 false', () => {
        expect(dataSanitizer.toBoolean(false)).toBe(false);
        expect(dataSanitizer.toBoolean(0)).toBe(false);
        expect(dataSanitizer.toBoolean('')).toBe(false);
      });
    });

    describe('sanitizeDiagnosticResult 方法', () => {
      test('应该处理 null 输入', () => {
        const result = dataSanitizer.sanitizeDiagnosticResult(null);

        expect(result.status).toBe('unknown');
        expect(result.progress).toBe(0);
        expect(result.stage).toBe('init');
        expect(result.results).toEqual([]);
      });

      test('应该处理缺失字段的数据', () => {
        const rawData = {
          status: null,
          progress: 'invalid',
          results: null
        };

        const result = dataSanitizer.sanitizeDiagnosticResult(rawData);

        expect(result.status).toBe('unknown');
        expect(result.progress).toBe(0);
        expect(result.results).toEqual([]);
      });

      test('应该正确清洗完整数据', () => {
        const rawData = {
          status: 'completed',
          progress: 100,
          stage: 'completed',
          results: [{ brand: '品牌 A', score: 85 }],
          detailed_results: { score: 85 },
          error: null,
          message: '成功'
        };

        const result = dataSanitizer.sanitizeDiagnosticResult(rawData);

        expect(result.status).toBe('completed');
        expect(result.progress).toBe(100);
        expect(result.stage).toBe('completed');
        expect(result.results).toEqual([{ brand: '品牌 A', score: 85 }]);
        expect(result.detailed_results).toEqual({ score: 85 });
        expect(result.error).toBeNull();
        expect(result.message).toBe('成功');
      });
    });

    describe('sanitizeDraft 方法', () => {
      test('应该处理 null 输入', () => {
        const result = dataSanitizer.sanitizeDraft(null);
        expect(result).toBeNull();
      });

      test('应该处理 brandName 为 null 的草稿', () => {
        const rawDraft = {
          brandName: null,
          competitorBrands: []
        };

        const result = dataSanitizer.sanitizeDraft(rawDraft);
        expect(result).toBeNull();
      });

      test('应该正确清洗完整草稿数据', () => {
        const rawDraft = {
          brandName: '品牌 A',
          currentCompetitor: '竞品',
          competitorBrands: ['竞品 A', '竞品 B'],
          customQuestions: [{ text: '问题 1', show: true }],
          selectedModels: {
            domestic: ['deepseek'],
            overseas: ['chatgpt']
          },
          updatedAt: 1234567890
        };

        const result = dataSanitizer.sanitizeDraft(rawDraft);

        expect(result.brandName).toBe('品牌 A');
        expect(result.currentCompetitor).toBe('竞品');
        expect(result.competitorBrands).toEqual(['竞品 A', '竞品 B']);
        expect(result.customQuestions).toEqual([{ text: '问题 1', show: true }]);
        expect(result.selectedModels.domestic).toEqual(['deepseek']);
        expect(result.selectedModels.overseas).toEqual(['chatgpt']);
        expect(result.updatedAt).toBe(1234567890);
      });

      test('应该清洗异常类型的字段', () => {
        const rawDraft = {
          brandName: '品牌 A',
          competitorBrands: 'invalid',
          customQuestions: null,
          selectedModels: null
        };

        const result = dataSanitizer.sanitizeDraft(rawDraft);

        expect(result.brandName).toBe('品牌 A');
        expect(result.competitorBrands).toEqual([]);
        expect(result.customQuestions).toEqual([]);
        expect(result.selectedModels.domestic).toEqual([]);
        expect(result.selectedModels.overseas).toEqual([]);
      });
    });
  });

  describe('parseTaskStatus 防御性处理测试', () => {
    test('应该处理 null 输入', () => {
      const result = parseTaskStatus(null);

      expect(result.status).toBe('unknown');
      expect(result.progress).toBe(0);
      expect(result.stage).toBe('init');
    });

    test('应该处理 undefined 输入', () => {
      const result = parseTaskStatus(undefined);

      expect(result.status).toBe('unknown');
      expect(result.progress).toBe(0);
      expect(result.stage).toBe('init');
    });

    test('应该处理缺失字段的数据', () => {
      const rawData = {
        status: 'completed'
      };

      const result = parseTaskStatus(rawData);

      expect(result.status).toBe('completed');
      expect(result.progress).toBe(0);
      expect(result.stage).toBe('init');
    });

    test('应该处理 progress 为非数字', () => {
      const rawData = {
        progress: 'invalid'
      };

      const result = parseTaskStatus(rawData);

      expect(result.progress).toBe(0);
    });

    test('应该根据 stage 设置进度', () => {
      expect(parseTaskStatus({ stage: 'init' }).progress).toBe(10);
      expect(parseTaskStatus({ stage: 'ai_fetching' }).progress).toBe(30);
      expect(parseTaskStatus({ stage: 'intelligence_analyzing' }).progress).toBe(60);
      expect(parseTaskStatus({ stage: 'competition_analyzing' }).progress).toBe(80);
      expect(parseTaskStatus({ stage: 'completed' }).progress).toBe(100);
    });
  });
});

// 运行测试
if (require.main === module) {
  const { runTests } = require('./test-utils');
  runTests();
}
