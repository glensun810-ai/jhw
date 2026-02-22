#!/usr/bin/env node

/**
 * 前端测试运行器
 * 
 * 使用方法：
 * node tests/run-tests.js
 * 
 * 运行所有测试：
 * node tests/run-tests.js --all
 * 
 * 运行特定测试：
 * node tests/run-tests.js test-dataProcessorService.js
 */

const fs = require('fs');
const path = require('path');

// 测试文件列表
const testFiles = [
  'test-dataProcessorService.js',
  'test-brandTestService.js'
  // 后续添加更多测试文件
];

/**
 * 运行测试文件
 */
async function runTestFile(testFile) {
  const filePath = path.join(__dirname, testFile);
  
  if (!fs.existsSync(filePath)) {
    console.error(`❌ 测试文件不存在：${testFile}`);
    return null;
  }

  console.log(`\n📁 运行测试：${testFile}`);
  console.log('='.repeat(60));

  try {
    // 加载测试模块
    require(filePath);
    
    // 运行测试
    const { runTests } = require('./test-utils');
    const results = await runTests();
    
    return results;
  } catch (error) {
    console.error(`❌ 测试执行失败：${error.message}`);
    console.error(error.stack);
    return {
      total: 0,
      passed: 0,
      failed: 0,
      coverage: '0%'
    };
  }
}

/**
 * 生成测试报告
 */
function generateReport(allResults) {
  const totalTests = allResults.reduce((sum, r) => sum + r.total, 0);
  const totalPassed = allResults.reduce((sum, r) => sum + r.passed, 0);
  const totalFailed = allResults.reduce((sum, r) => sum + r.failed, 0);

  console.log('\n');
  console.log('╔' + '═'.repeat(58) + '╗');
  console.log('║' + ' '.repeat(20) + '测试报告' + ' '.repeat(20) + '║');
  console.log('╠' + '═'.repeat(58) + '╣');
  console.log(`║ 总测试数：${totalTests}`.padEnd(59) + '║');
  console.log(`║ 通过：${totalPassed}`.padEnd(59) + '║');
  console.log(`║ 失败：${totalFailed}`.padEnd(59) + '║');
  
  const coverage = totalTests > 0 ? ((totalPassed / totalTests) * 100).toFixed(2) : 0;
  console.log(`║ 覆盖率：${coverage}%`.padEnd(59) + '║');
  console.log('╚' + '═'.repeat(58) + '╝');

  return {
    total: totalTests,
    passed: totalPassed,
    failed: totalFailed,
    coverage: coverage + '%'
  };
}

/**
 * 主函数
 */
async function main() {
  console.log('\n');
  console.log('🧪 '.repeat(20));
  console.log('开始运行前端测试...');
  console.log('🧪 '.repeat(20));

  const args = process.argv.slice(2);
  let filesToRun = [];

  if (args.includes('--all') || args.length === 0) {
    // 运行所有测试
    filesToRun = testFiles;
  } else {
    // 运行指定测试
    filesToRun = args.filter(arg => arg.endsWith('.js'));
  }

  if (filesToRun.length === 0) {
    console.log('⚠️  没有找到测试文件');
    return;
  }

  console.log(`\n📋 测试文件：${filesToRun.length} 个`);
  filesToRun.forEach(file => console.log(`   - ${file}`));

  const allResults = [];

  for (const testFile of filesToRun) {
    const results = await runTestFile(testFile);
    if (results) {
      allResults.push(results);
    }
  }

  // 生成报告
  const finalReport = generateReport(allResults);

  // 保存报告
  const reportPath = path.join(__dirname, 'test-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    files: filesToRun,
    results: finalReport
  }, null, 2));

  console.log(`\n💾 报告已保存：${reportPath}`);

  // 退出码
  if (finalReport.failed > 0) {
    process.exit(1);
  }
}

// 运行
main().catch(error => {
  console.error('测试运行失败:', error);
  process.exit(1);
});
