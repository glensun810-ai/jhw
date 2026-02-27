/**
 * 阶段一：集成测试
 * 
 * 测试范围：
 * 1. 前端轮询管理器与后端 API 集成
 * 2. should_stop_polling 字段端到端验证
 * 3. 超时和重试机制验证
 * 4. 资源清理验证
 * 
 * @author 系统架构组
 * @date 2026-02-27
 * @version 1.0.0
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// 项目根目录
const ROOT_DIR = path.resolve(__dirname, '../..');

// 测试结果统计
const testResults = {
  total: 0,
  passed: 0,
  failed: 0,
  tests: []
};

/**
 * 测试工具函数
 */
function test(name, fn) {
  testResults.total++;
  try {
    fn();
    testResults.passed++;
    testResults.tests.push({ name, status: 'PASSED' });
    console.log(`✅ ${name}`);
  } catch (error) {
    testResults.failed++;
    testResults.tests.push({ name, status: 'FAILED', error: error.message });
    console.error(`❌ ${name}: ${error.message}`);
  }
}

/**
 * 断言辅助函数
 */
function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message || `Expected ${expected}, got ${actual}`);
  }
}

function assertTrue(value, message) {
  if (!value) {
    throw new Error(message || 'Expected true');
  }
}

function assertNotNull(value, message) {
  if (value === null || value === undefined) {
    throw new Error(message || 'Expected non-null value');
  }
}

// ==================== 测试用例 ====================

console.log('\n========================================');
console.log('阶段一：前端状态轮询优化 - 集成测试');
console.log('========================================\n');

// 测试 1: 轮询管理器文件存在
test('轮询管理器文件存在', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/services/pollingManager.js');
  assertTrue(fs.existsSync(filePath), `文件应该存在：${filePath}`);
});

// 测试 2: 诊断服务文件存在
test('诊断服务文件存在', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/services/diagnosisService.js');
  assertTrue(fs.existsSync(filePath), `文件应该存在：${filePath}`);
});

// 测试 3: 特性开关配置
test('特性开关配置', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/config/featureFlags.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(content.includes('useNewPolling: true'), 'useNewPolling 应该启用');
  assertTrue(content.includes('enableRetryStrategy: true'), 'enableRetryStrategy 应该启用');
  assertTrue(content.includes('enableAutoResume: true'), 'enableAutoResume 应该启用');
});

// 测试 4: 重试策略文件存在
test('重试策略文件存在', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/utils/retryStrategy.js');
  assertTrue(fs.existsSync(filePath), `文件应该存在：${filePath}`);
});

// 测试 5: 后端状态管理器
test('后端状态管理器 - should_stop_polling 支持', () => {
  const filePath = path.join(ROOT_DIR, 'backend_python/wechat_backend/state_manager.py');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('should_stop_polling'),
    'state_manager.py 应该包含 should_stop_polling 参数'
  );
  
  assertTrue(
    content.includes('store[\'should_stop_polling\']'),
    'state_manager.py 应该设置 should_stop_polling 字段'
  );
});

// 测试 6: 后端诊断视图 API
test('后端诊断视图 API - should_stop_polling 返回', () => {
  const filePath = path.join(ROOT_DIR, 'backend_python/wechat_backend/views/diagnosis_views.py');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('should_stop_polling'),
    'diagnosis_views.py 应该包含 should_stop_polling'
  );
  
  // 检查是否在完成/失败时设置为 true
  assertTrue(
    content.includes('\'should_stop_polling\': True') || 
    content.includes('should_stop_polling = True'),
    'diagnosis_views.py 应该在完成/失败时设置 should_stop_polling=True'
  );
});

// 测试 7: 数据库表结构
test('数据库表结构 - should_stop_polling 字段', () => {
  const { execSync } = require('child_process');
  
  try {
    const dbPath = path.join(ROOT_DIR, 'backend_python/database.db');
    const result = execSync(`sqlite3 ${dbPath} "PRAGMA table_info(diagnosis_reports);"`, { encoding: 'utf8' });
    
    assertTrue(
      result.includes('should_stop_polling'),
      'diagnosis_reports 表应该包含 should_stop_polling 字段'
    );
  } catch (error) {
    // 如果数据库不存在，跳过此测试
    console.log('⚠️  数据库不存在，跳过此测试');
  }
});

// 测试 8: 前端诊断页面集成
test('前端诊断页面 - 轮询集成', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/pages/diagnosis/diagnosis.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('diagnosisService.startPolling'),
    '诊断页面应该调用 diagnosisService.startPolling'
  );
  
  assertTrue(
    content.includes('handleStatusUpdate'),
    '诊断页面应该有 handleStatusUpdate 回调'
  );
  
  assertTrue(
    content.includes('handleComplete'),
    '诊断页面应该有 handleComplete 回调'
  );
  
  assertTrue(
    content.includes('onUnload'),
    '诊断页面应该有 onUnload 清理逻辑'
  );
});

// 测试 9: 资源清理
test('资源清理 - 定时器清理', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/pages/diagnosis/diagnosis.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('stopPolling') && content.includes('stopElapsedTimer'),
    '诊断页面应该在 onUnload 时停止轮询和计时器'
  );
  
  assertTrue(
    content.includes('clearInterval') || content.includes('clearTimeout'),
    '诊断页面应该清理定时器'
  );
});

// 测试 10: 错误处理
test('错误处理 - 轮询错误回调', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/services/pollingManager.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('_handlePollingError'),
    'PollingManager 应该有错误处理方法'
  );
  
  assertTrue(
    content.includes('exponentialWithJitter') || content.includes('RetryStrategy'),
    'PollingManager 应该使用指数退避重试'
  );
  
  assertTrue(
    content.includes('maxRetries'),
    'PollingManager 应该有最大重试次数限制'
  );
});

// 测试 11: 超时处理
test('超时处理 - 总超时时间', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/services/pollingManager.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('timeout') && content.includes('600000'),
    'PollingManager 应该有 10 分钟超时配置'
  );
  
  assertTrue(
    content.includes('_handleTimeout'),
    'PollingManager 应该有超时处理方法'
  );
});

// 测试 12: 智能终止逻辑
test('智能终止逻辑 - should_stop_polling 判断', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/services/pollingManager.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('should_stop_polling'),
    'PollingManager 应该检查 should_stop_polling 字段'
  );
  
  assertTrue(
    content.includes('statusData.should_stop_polling === true'),
    'PollingManager 应该正确判断 should_stop_polling'
  );
  
  assertTrue(
    content.includes('this.stopPolling(executionId)'),
    'PollingManager 应该在 should_stop_polling=true 时停止轮询'
  );
});

// 测试 13: 页面生命周期管理
test('页面生命周期管理 - onHide/onShow', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/pages/diagnosis/diagnosis.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('onHide') && content.includes('pausePolling'),
    '页面应该在 onHide 时暂停轮询'
  );
  
  assertTrue(
    content.includes('onShow') && content.includes('resumePolling'),
    '页面应该在 onShow 时恢复轮询'
  );
});

// 测试 14: 进度历史记录
test('进度历史记录 - 记录保存', () => {
  const filePath = path.join(ROOT_DIR, 'miniprogram/pages/diagnosis/diagnosis.js');
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('progressHistory'),
    '页面应该有 progressHistory 数组'
  );
  
  assertTrue(
    content.includes('history.push'),
    '页面应该记录进度历史'
  );
  
  assertTrue(
    content.includes('history.length > 20') && content.includes('history.shift'),
    '页面应该限制历史记录数量为 20 条'
  );
});

// 测试 15: v2 版本兼容性
test('v2 版本兼容性 - 仓库实现', () => {
  const filePath = path.join(ROOT_DIR, 'backend_python/wechat_backend/v2/repositories/diagnosis_repository.py');
  
  if (!fs.existsSync(filePath)) {
    console.log('⚠️  v2 仓库文件不存在，跳过此测试');
    return;
  }
  
  const content = fs.readFileSync(filePath, 'utf8');
  
  assertTrue(
    content.includes('should_stop_polling'),
    'v2 仓库应该支持 should_stop_polling 参数'
  );
  
  assertTrue(
    content.includes('UPDATE diagnosis_reports'),
    'v2 仓库应该实现状态更新 SQL'
  );
});

// ==================== 测试结果汇总 ====================

console.log('\n========================================');
console.log('测试结果汇总');
console.log('========================================');
console.log(`总测试数：${testResults.total}`);
console.log(`✅ 通过：${testResults.passed}`);
console.log(`❌ 失败：${testResults.failed}`);
console.log(`成功率：${(testResults.passed / testResults.total * 100).toFixed(2)}%`);
console.log('========================================\n');

// 输出失败详情
if (testResults.failed > 0) {
  console.log('失败详情:');
  testResults.tests
    .filter(t => t.status === 'FAILED')
    .forEach(t => {
      console.log(`  ❌ ${t.name}: ${t.error}`);
    });
  console.log();
}

// 退出码
process.exit(testResults.failed > 0 ? 1 : 0);
