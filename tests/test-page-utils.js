/**
 * 页面组件测试工具
 * 
 * 功能：
 * - Mock 页面上下文
 * - Mock 小程序 API
 * - 页面生命周期模拟
 */

const { mockWx, createMockFn } = require('./test-utils');

/**
 * 创建 Mock 页面上下文
 */
function createMockPageContext(initialData = {}) {
  const data = { ...initialData };
  const setDataCalls = [];

  return {
    data,
    setData: function(newData, callback) {
      Object.assign(data, newData);
      setDataCalls.push({ data: newData, callback });
      if (callback) callback();
    },
    setDataCalls,
    triggerEvent: createMockFn(),
    selectComponent: createMockFn(),
    createSelectorQuery: createMockFn()
  };
}

/**
 * Mock 小程序生命周期
 */
function mockPageLifecycle(lifecycle) {
  const mocks = {};
  
  Object.keys(lifecycle).forEach(key => {
    mocks[key] = createMockFn();
    mocks[key].mockImplementation(lifecycle[key]);
  });
  
  return mocks;
}

/**
 * 模拟页面加载
 */
async function simulatePageLoad(pageMethods, options = {}) {
  const pageContext = createMockPageContext();
  
  if (pageMethods.onLoad) {
    await pageMethods.onLoad.call(pageContext, options);
  }
  
  if (pageMethods.onShow) {
    await pageMethods.onShow.call(pageContext);
  }
  
  if (pageMethods.onReady) {
    await pageMethods.onReady.call(pageContext);
  }
  
  return pageContext;
}

/**
 * 模拟用户交互
 */
function simulateUserAction(pageContext, methodName, params = {}) {
  if (typeof pageContext[methodName] === 'function') {
    return pageContext[methodName].call(pageContext, params);
  }
  throw new Error(`方法 ${methodName} 不存在`);
}

/**
 * 验证 setData 调用
 */
function verifySetDataCalled(pageContext, expectedData) {
  const calls = pageContext.setDataCalls;
  
  for (const call of calls) {
    for (const key in expectedData) {
      if (call.data[key] !== expectedData[key]) {
        return false;
      }
    }
  }
  
  return true;
}

/**
 * 获取最终状态
 */
function getFinalState(pageContext) {
  return { ...pageContext.data };
}

module.exports = {
  createMockPageContext,
  mockPageLifecycle,
  simulatePageLoad,
  simulateUserAction,
  verifySetDataCalled,
  getFinalState
};
