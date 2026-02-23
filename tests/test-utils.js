/**
 * 前端测试工具
 * 
 * 功能：
 * - 简化单元测试编写
 * - Mock 微信 API
 * - 断言工具
 */

// 测试结果统计
const testResults = {
  total: 0,
  passed: 0,
  failed: 0,
  suites: []
};

// 当前测试套件
let currentSuite = null;

/**
 * 测试套件
 */
function describe(name, fn) {
  currentSuite = {
    name,
    tests: [],
    beforeAll: null,
    afterAll: null,
    beforeEach: null,
    afterEach: null
  };
  
  testResults.suites.push(currentSuite);
  fn();
  currentSuite = null;
}

/**
 * 测试用例
 */
function test(name, fn) {
  if (!currentSuite) {
    throw new Error('test() 必须在 describe() 内部使用');
  }
  
  currentSuite.tests.push({ name, fn });
}

/**
 * 测试用例别名
 */
const it = test;

/**
 * 前置处理（所有测试前）
 */
function beforeAll(fn) {
  if (currentSuite) {
    currentSuite.beforeAll = fn;
  }
}

/**
 * 后置处理（所有测试后）
 */
function afterAll(fn) {
  if (currentSuite) {
    currentSuite.afterAll = fn;
  }
}

/**
 * 前置处理（每个测试前）
 */
function beforeEach(fn) {
  if (currentSuite) {
    currentSuite.beforeEach = fn;
  }
}

/**
 * 后置处理（每个测试后）
 */
function afterEach(fn) {
  if (currentSuite) {
    currentSuite.afterEach = fn;
  }
}

/**
 * 断言类
 */
class Expect {
  constructor(actual) {
    this.actual = actual;
    this.not = new Proxy({}, {
      get: (target, prop) => {
        this.isNot = true;
        return this[prop]();
      }
    });
  }

  /**
   * 等于
   */
  toBe(expected) {
    const passed = this.actual === expected;
    this.assert(passed, `期望 ${this.actual} 等于 ${expected}`);
  }

  /**
   * 深度等于
   */
  toEqual(expected) {
    const passed = JSON.stringify(this.actual) === JSON.stringify(expected);
    this.assert(passed, `期望 ${JSON.stringify(this.actual)} 等于 ${JSON.stringify(expected)}`);
  }

  /**
   * 为真
   */
  toBeTruthy() {
    const passed = !!this.actual;
    this.assert(passed, `期望 ${this.actual} 为真`);
  }

  /**
   * 为假
   */
  toBeFalsy() {
    const passed = !this.actual;
    this.assert(passed, `期望 ${this.actual} 为假`);
  }

  /**
   * 为空
   */
  toBeNull() {
    const passed = this.actual === null;
    this.assert(passed, `期望 ${this.actual} 为 null`);
  }

  /**
   * 未定义
   */
  toBeUndefined() {
    const passed = this.actual === undefined;
    this.assert(passed, `期望 ${this.actual} 为 undefined`);
  }

  /**
   * 已定义
   */
  toBeDefined() {
    const passed = this.actual !== undefined;
    this.assert(passed, `期望 ${this.actual} 不为 undefined`);
  }

  /**
   * 包含属性
   */
  toHaveProperty(prop) {
    const passed = this.actual && typeof this.actual === 'object' && prop in this.actual;
    this.assert(passed, `期望 ${JSON.stringify(this.actual)} 包含属性 ${prop}`);
  }

  /**
   * 包含
   */
  toContain(expected) {
    const passed = Array.isArray(this.actual)
      ? this.actual.includes(expected)
      : this.actual.includes(expected);
    this.assert(passed, `期望 ${this.actual} 包含 ${expected}`);
  }

  /**
   * 大于
   */
  toBeGreaterThan(expected) {
    const passed = this.actual > expected;
    this.assert(passed, `期望 ${this.actual} 大于 ${expected}`);
  }

  /**
   * 小于
   */
  toBeLessThan(expected) {
    const passed = this.actual < expected;
    this.assert(passed, `期望 ${this.actual} 小于 ${expected}`);
  }

  /**
   * 抛出错误
   */
  toThrow() {
    let passed = false;
    try {
      this.actual();
    } catch (e) {
      passed = true;
    }
    this.assert(passed, '期望函数抛出错误');
  }

  /**
   * 断言方法
   */
  assert(passed, message) {
    testResults.total++;
    
    if (this.isNot) {
      passed = !passed;
    }
    
    if (passed) {
      testResults.passed++;
      console.log(`✅ ${message || '测试通过'}`);
    } else {
      testResults.failed++;
      console.error(`❌ ${message || '测试失败'}`);
      throw new Error(message || '测试失败');
    }
    
    this.isNot = false;
  }
}

/**
 * expect 函数
 */
function expect(actual) {
  return new Expect(actual);
}

/**
 * Mock 函数创建器
 */
function createMockFn() {
  const mockFn = function() {
    mockFn.calls.push(Array.from(arguments));
    // 如果有自定义实现，使用自定义实现
    if (mockFn.implementation) {
      return mockFn.implementation.apply(this, arguments);
    }
    return mockFn.returnValue;
  };
  mockFn.calls = [];
  mockFn.returnValue = undefined;
  mockFn.implementation = null;
  
  /**
   * 设置返回值
   */
  mockFn.mockReturnValue = function(value) {
    mockFn.implementation = null;  // 清除自定义实现
    mockFn.returnValue = value;
    return mockFn;
  };
  
  /**
   * 设置自定义实现
   */
  mockFn.mockImplementation = function(impl) {
    mockFn.implementation = impl;
    return mockFn;
  };
  
  /**
   * 清空调用记录
   */
  mockFn.mockClear = function() {
    mockFn.calls = [];
    mockFn.returnValue = undefined;
    mockFn.implementation = null;
    return mockFn;
  };
  
  /**
   * 重置 Mock 函数
   */
  mockFn.mockReset = function() {
    mockFn.calls = [];
    mockFn.returnValue = undefined;
    mockFn.implementation = null;
    return mockFn;
  };
  
  return mockFn;
}

/**
 * Mock 微信 API
 */
const mockWx = {
  showLoading: createMockFn(),
  hideLoading: createMockFn(),
  showToast: createMockFn(),
  showModal: createMockFn(),
  navigateTo: createMockFn(),
  redirectTo: createMockFn(),
  reLaunch: createMockFn(),
  setStorageSync: createMockFn(),
  getStorageSync: createMockFn(),
  removeStorageSync: createMockFn(),
  clearStorageSync: createMockFn(),
  request: createMockFn()
};

// 全局注入 wx 对象
global.wx = mockWx;

/**
 * 清除所有 Mock
 */
function clearAllMocks() {
  Object.keys(mockWx).forEach(key => {
    if (mockWx[key] && typeof mockWx[key].mockClear === 'function') {
      mockWx[key].mockClear();
    }
  });
}

/**
 * 运行测试套件
 */
async function runTests() {
  console.log('\n🧪 开始运行测试...\n');
  
  for (const suite of testResults.suites) {
    console.log(`\n📦 测试套件：${suite.name}`);
    console.log('─'.repeat(50));
    
    // 运行 beforeAll
    if (suite.beforeAll) {
      await suite.beforeAll();
    }
    
    for (const test of suite.tests) {
      try {
        // 运行 beforeEach
        if (suite.beforeEach) {
          await suite.beforeEach();
        }
        
        // 运行测试
        console.log(`  📝 ${test.name}...`);
        await test.fn();
        console.log(`  ✅ 通过\n`);
        
        // 运行 afterEach
        if (suite.afterEach) {
          await suite.afterEach();
        }
        
        // 清除 Mock
        clearAllMocks();
      } catch (error) {
        console.error(`  ❌ 失败：${error.message}\n`);
      }
    }
    
    // 运行 afterAll
    if (suite.afterAll) {
      await suite.afterAll();
    }
  }
  
  // 打印统计
  console.log('\n' + '='.repeat(50));
  console.log('📊 测试结果统计');
  console.log('='.repeat(50));
  console.log(`总测试数：${testResults.total}`);
  console.log(`✅ 通过：${testResults.passed}`);
  console.log(`❌ 失败：${testResults.failed}`);
  console.log(`覆盖率：${((testResults.passed / testResults.total) * 100).toFixed(2)}%`);
  console.log('='.repeat(50));
  
  return {
    total: testResults.total,
    passed: testResults.passed,
    failed: testResults.failed,
    coverage: ((testResults.passed / testResults.total) * 100).toFixed(2) + '%'
  };
}

// 导出
module.exports = {
  describe,
  test,
  it,
  beforeAll,
  afterAll,
  beforeEach,
  afterEach,
  expect,
  mockWx,
  clearAllMocks,
  runTests,
  createMockFn  // 修复 P1-1/P1-3: 导出 createMockFn
};
