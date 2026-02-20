/**
 * 测试辅助工具 - 进度系统测试专用
 * 
 * 功能:
 * 1. 自动记录测试数据
 * 2. 生成测试报告
 * 3. 数据对比分析
 */

class TestHelper {
  constructor() {
    this.testData = [];
    this.currentTest = null;
  }

  /**
   * 开始测试
   */
  startTest(testId, testName) {
    this.currentTest = {
      testId,
      testName,
      startTime: Date.now(),
      records: []
    };
    console.log(`📝 开始测试：${testId} - ${testName}`);
  }

  /**
   * 记录测试数据
   */
  record(data) {
    if (!this.currentTest) {
      console.error('❌ 请先调用 startTest()');
      return;
    }

    const record = {
      timestamp: Date.now(),
      elapsed: (Date.now() - this.currentTest.startTime) / 1000,
      ...data
    };

    this.currentTest.records.push(record);
    console.log('📊 记录数据:', record);
  }

  /**
   * 结束测试
   */
  endTest() {
    if (!this.currentTest) {
      console.error('❌ 没有正在进行的测试');
      return null;
    }

    this.currentTest.endTime = Date.now();
    this.currentTest.duration = (this.currentTest.endTime - this.currentTest.startTime) / 1000;

    this.testData.push(this.currentTest);
    const report = this.generateReport(this.currentTest);
    
    console.log(`✅ 测试完成：${this.currentTest.testId}`);
    console.log('📊 测试报告:', report);

    this.currentTest = null;
    return report;
  }

  /**
   * 生成测试报告
   */
  generateReport(test) {
    const report = {
      testId: test.testId,
      testName: test.testName,
      duration: test.duration,
      recordCount: test.records.length,
      analysis: {}
    };

    // 时间预估分析
    if (test.records.some(r => r.estimatedTime)) {
      const estimates = test.records.filter(r => r.estimatedTime);
      const actuals = test.records.filter(r => r.actualTime);
      
      if (estimates.length > 0 && actuals.length > 0) {
        const avgEstimate = estimates.reduce((s, r) => s + r.estimatedTime, 0) / estimates.length;
        const avgActual = actuals.reduce((s, r) => s + r.actualTime, 0) / actuals.length;
        const deviation = Math.abs(avgEstimate - avgActual) / avgActual * 100;
        
        report.analysis.timeEstimation = {
          avgEstimate: Math.round(avgEstimate),
          avgActual: Math.round(avgActual),
          deviation: Math.round(deviation * 100) / 100 + '%',
          passed: deviation < 20
        };
      }
    }

    // 轮询间隔分析
    if (test.records.some(r => r.pollInterval)) {
      const intervals = test.records.map(r => r.pollInterval);
      const uniqueIntervals = [...new Set(intervals)];
      
      report.analysis.pollingInterval = {
        intervals: uniqueIntervals,
        avgInterval: Math.round(intervals.reduce((a, b) => a + b, 0) / intervals.length),
        stable: uniqueIntervals.length <= 3
      };
    }

    // 剩余时间平滑度分析
    if (test.records.some(r => r.remainingTime)) {
      const remaining = test.records.map(r => r.remainingTime);
      let maxJump = 0;
      for (let i = 1; i < remaining.length; i++) {
        const jump = Math.abs(remaining[i] - remaining[i-1]);
        if (jump > maxJump) maxJump = jump;
      }
      
      report.analysis.smoothness = {
        maxJump: maxJump,
        passed: maxJump < 30
      };
    }

    return report;
  }

  /**
   * 获取所有测试数据
   */
  getAllTestData() {
    return this.testData;
  }

  /**
   * 清除测试数据
   */
  clearData() {
    this.testData = [];
    this.currentTest = null;
  }

  /**
   * 导出测试报告
   */
  exportReport() {
    const summary = {
      totalTests: this.testData.length,
      passedTests: this.testData.filter(t => {
        const report = this.generateReport(t);
        return Object.values(report.analysis || {}).every(a => a.passed !== false);
      }).length,
      tests: this.testData.map(t => this.generateReport(t))
    };

    console.log('📊 测试汇总:', summary);
    return summary;
  }
}

// 创建全局测试助手实例
const testHelper = new TestHelper();

module.exports = { TestHelper, testHelper };
