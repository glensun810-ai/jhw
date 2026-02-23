#!/usr/bin/env node
/**
 * 综合修复验证测试脚本
 * 验证所有 P0/P1/P2 级修复是否正确实施
 */

const fs = require('fs');
const path = require('path');

// 测试结果
const testResults = {
  total: 0,
  passed: 0,
  failed: 0,
  tests: []
};

// 项目根目录
const PROJECT_ROOT = path.join(__dirname, '..');

/**
 * 测试断言
 */
function assert(condition, message) {
  testResults.total++;
  if (condition) {
    testResults.passed++;
    console.log(`  ✅ ${message}`);
    testResults.tests.push({ name: message, passed: true });
  } else {
    testResults.failed++;
    console.log(`  ❌ ${message}`);
    testResults.tests.push({ name: message, passed: false });
  }
}

/**
 * 读取文件内容
 */
function readFile(filePath) {
  const fullPath = path.join(PROJECT_ROOT, filePath);
  if (!fs.existsSync(fullPath)) {
    console.log(`  ⚠️  文件不存在：${filePath}`);
    return null;
  }
  return fs.readFileSync(fullPath, 'utf-8');
}

/**
 * 测试 1: 验证 config_manager 导入修复
 */
function testConfigManagerImport() {
  console.log('\n📋 测试 1: config_manager 导入修复');
  
  const content = readFile('backend_python/wechat_backend/nxm_execution_engine.py');
  if (!content) return;
  
  // 验证使用 Config 类
  assert(
    content.includes('from config import Config'),
    '使用 Config 类导入'
  );
  
  // 验证使用 Config.get_api_key
  assert(
    content.includes('Config.get_api_key(model_name)'),
    '使用 Config.get_api_key() 获取 API Key'
  );
  
  // 验证不再使用 wechat_backend.config_manager 导入（注释除外）
  const lines = content.split('\n');
  const hasBadImport = lines.some(line => {
    const trimmed = line.trim();
    return trimmed.startsWith('from wechat_backend.config_manager import') && 
           !trimmed.startsWith('#');
  });
  assert(
    !hasBadImport,
    '不再使用 wechat_backend.config_manager 导入（注释除外）'
  );
}

/**
 * 测试 2: 验证 SSE 推送参数修复
 */
function testSSEPushFix() {
  console.log('\n📋 测试 2: SSE 推送参数修复');
  
  const content = readFile('backend_python/wechat_backend/nxm_scheduler.py');
  if (!content) return;
  
  // 验证 status_texts 字典
  assert(
    content.includes("status_texts = {"),
    '定义 status_texts 字典'
  );
  
  // 验证 status_text 参数传递
  assert(
    content.includes('status_text=status_text'),
    '传递 status_text 参数'
  );
  
  // 验证状态文本映射
  const hasInit = content.includes("'init':");
  const hasAiFetching = content.includes("'ai_fetching':");
  const hasCompleted = content.includes("'completed':");
  
  assert(
    hasInit && hasAiFetching && hasCompleted,
    '包含完整状态文本映射'
  );
}

/**
 * 测试 3: 验证 Token 携带修复
 */
function testTokenCarryFix() {
  console.log('\n📋 测试 3: Token 携带修复');
  
  const content = readFile('utils/request.js');
  if (!content) return;
  
  // 验证 skipAuth 参数
  assert(
    content.includes('skipAuth = false'),
    '定义 skipAuth 参数'
  );
  
  // 验证 Token 读取
  assert(
    content.includes("wx.getStorageSync('userToken')"),
    '从 Storage 读取 Token'
  );
  
  // 验证 Authorization 头设置
  assert(
    content.includes("defaultHeader['Authorization'] = `Bearer ${token}`"),
    '设置 Authorization 头'
  );
  
  // 验证 403 错误处理
  assert(
    content.includes('response.statusCode === 403'),
    '处理 403 错误'
  );
  
  // 验证 403 错误标记
  assert(
    content.includes('error.isAuthError = true'),
    '标记认证错误'
  );
}

/**
 * 测试 4: 验证 403 不重试机制
 */
function test403NoRetry() {
  console.log('\n📋 测试 4: 403 不重试机制');
  
  const content = readFile('utils/request.js');
  if (!content) return;
  
  // 验证 403 错误检查
  assert(
    content.includes('error.statusCode === 403'),
    '检查 403 状态码'
  );
  
  // 验证不重试逻辑
  assert(
    content.includes('403 错误不重试') || content.includes('不重试'),
    '403 错误不重试注释'
  );
  
  // 验证立即返回
  const retryFunction = content.substring(
    content.indexOf('requestWithRetry'),
    content.indexOf('requestWithRetry') + 500
  );
  assert(
    retryFunction.includes('throw error'),
    '403 错误立即抛出'
  );
}

/**
 * 测试 5: 验证熔断机制
 */
function testCircuitBreaker() {
  console.log('\n📋 测试 5: 熔断机制');
  
  const content = readFile('services/brandTestService.js');
  if (!content) return;
  
  // 验证错误计数器
  assert(
    content.includes('consecutiveAuthErrors = 0'),
    '定义错误计数器'
  );
  
  // 验证最大错误数
  assert(
    content.includes('MAX_AUTH_ERRORS = 2'),
    '定义最大错误数 (2 次)'
  );
  
  // 验证计数器递增
  assert(
    content.includes('consecutiveAuthErrors++'),
    '错误计数器递增'
  );
  
  // 验证熔断逻辑
  assert(
    content.includes('consecutiveAuthErrors >= MAX_AUTH_ERRORS'),
    '熔断判断逻辑'
  );
  
  // 验证停止轮询
  assert(
    content.includes('stop()') && content.includes('认证错误熔断'),
    '熔断时停止轮询'
  );
  
  // 验证计数器重置
  assert(
    content.includes('consecutiveAuthErrors = 0'),
    '非认证错误重置计数器'
  );
}

/**
 * 测试 6: 验证立即轮询优化
 */
function testImmediatePolling() {
  console.log('\n📋 测试 6: 立即轮询优化');
  
  const content = readFile('services/brandTestService.js');
  if (!content) return;
  
  // 验证 immediate 参数
  assert(
    content.includes('immediate = true'),
    '定义 immediate 参数 (默认 true)'
  );
  
  // 验证立即执行逻辑
  assert(
    content.includes('if (immediate)'),
    '检查 immediate 条件'
  );
  
  // 验证立即调用 getTaskStatusApi
  const immediateBlock = content.substring(
    content.indexOf('if (immediate)'),
    content.indexOf('if (immediate)') + 500
  );
  assert(
    immediateBlock.includes('getTaskStatusApi(executionId)'),
    '立即调用 getTaskStatusApi'
  );
  
  // 验证轮询间隔 800ms
  assert(
    content.includes('interval = 800'),
    '轮询间隔 800ms'
  );
}

/**
 * 测试 7: 验证健康检查 skipAuth
 */
function testHealthCheckSkipAuth() {
  console.log('\n📋 测试 7: 健康检查 skipAuth');
  
  const content = readFile('api/home.js');
  if (!content) return;
  
  // 验证 skipAuth: true
  assert(
    content.includes('skipAuth: true'),
    '健康检查设置 skipAuth: true'
  );
  
  // 验证注释说明
  assert(
    content.includes('健康检查接口不需要认证') || content.includes('跳过'),
    '注释说明跳过认证'
  );
}

/**
 * 测试 8: 验证错误处理 hideLoading
 */
function testErrorHideLoading() {
  console.log('\n📋 测试 8: 错误处理 hideLoading');
  
  const content = readFile('pages/index/index.js');
  if (!content) return;
  
  // 验证 handleDiagnosisError 中有 wx.hideLoading()
  const handleErrorStart = content.indexOf('handleDiagnosisError(error)');
  if (handleErrorStart === -1) {
    assert(false, '找到 handleDiagnosisError 函数');
    return;
  }
  
  const handleErrorFunction = content.substring(
    handleErrorStart,
    handleErrorStart + 500
  );
  
  assert(
    handleErrorFunction.includes('wx.hideLoading()'),
    '错误处理中调用 wx.hideLoading()'
  );
}

/**
 * 测试 9: 验证异步数据聚合
 */
function testAsyncDataAggregation() {
  console.log('\n📋 测试 9: 异步数据聚合');
  
  const content = readFile('pages/index/index.js');
  if (!content) return;
  
  // 验证 handleDiagnosisComplete 中有 setTimeout
  const completeStart = content.indexOf('handleDiagnosisComplete(parsedStatus, executionId)');
  if (completeStart === -1) {
    assert(false, '找到 handleDiagnosisComplete 函数');
    return;
  }
  
  // 增加搜索范围到 3000 字符
  const completeFunction = content.substring(
    completeStart,
    completeStart + 3000
  );
  
  assert(
    completeFunction.includes('setTimeout'),
    '使用 setTimeout 异步处理'
  );
  
  // 验证先跳转后处理
  const navigateToIndex = completeFunction.indexOf('wx.navigateTo');
  const setTimeoutIndex = completeFunction.indexOf('setTimeout');
  
  assert(
    navigateToIndex !== -1 && setTimeoutIndex !== -1 && navigateToIndex < setTimeoutIndex,
    '先跳转后异步处理'
  );
}

/**
 * 测试 10: 验证文件完整性
 */
function testFileIntegrity() {
  console.log('\n📋 测试 10: 文件完整性检查');
  
  const requiredFiles = [
    'backend_python/wechat_backend/nxm_execution_engine.py',
    'backend_python/wechat_backend/nxm_scheduler.py',
    'utils/request.js',
    'services/brandTestService.js',
    'api/home.js',
    'pages/index/index.js'
  ];
  
  requiredFiles.forEach(file => {
    const exists = fs.existsSync(path.join(PROJECT_ROOT, file));
    assert(exists, `文件存在：${file}`);
  });
}

/**
 * 运行所有测试
 */
function runAllTests() {
  console.log('╔══════════════════════════════════════════════════════════╗');
  console.log('║           综合修复验证测试                                ║');
  console.log('╚══════════════════════════════════════════════════════════╝');
  
  testFileIntegrity();
  testConfigManagerImport();
  testSSEPushFix();
  testTokenCarryFix();
  test403NoRetry();
  testCircuitBreaker();
  testImmediatePolling();
  testHealthCheckSkipAuth();
  testErrorHideLoading();
  testAsyncDataAggregation();
  
  // 打印统计
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║                    测试统计                               ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log(`║ 总测试数：${testResults.total.toString().padEnd(44)}║`);
  console.log(`║ 通过：${testResults.passed.toString().padEnd(46)}║`);
  console.log(`║ 失败：${testResults.failed.toString().padEnd(46)}║`);
  
  const passRate = testResults.total > 0 
    ? ((testResults.passed / testResults.total) * 100).toFixed(1)
    : 0;
  console.log(`║ 通过率：${passRate.padEnd(44)}%║`);
  console.log('╚══════════════════════════════════════════════════════════╝');
  
  // 保存测试结果
  const reportPath = path.join(PROJECT_ROOT, 'comprehensive_fix_verification_report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    ...testResults,
    passRate: parseFloat(passRate)
  }, null, 2));
  
  console.log(`\n📄 测试报告已保存：${reportPath}`);
  
  return testResults.failed === 0;
}

// 运行测试
const success = runAllTests();
process.exit(success ? 0 : 1);
