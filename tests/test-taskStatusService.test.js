/**
 * taskStatusService 单元测试
 * 测试覆盖率目标：90%
 */

const { parseTaskStatus, calculateRemainingTime } = require('../taskStatusService');

describe('taskStatusService', () => {
  describe('calculateRemainingTime', () => {
    test('进度为 0 时返回计算中', () => {
      expect(calculateRemainingTime(0, 100)).toBe('计算中...');
    });

    test('已用时间为 0 时返回计算中', () => {
      expect(calculateRemainingTime(50, 0)).toBe('计算中...');
    });

    test('剩余时间少于 60 秒时返回秒', () => {
      expect(calculateRemainingTime(90, 90)).toBe('约 10 秒');
    });

    test('剩余时间少于 60 分钟时返回分钟', () => {
      expect(calculateRemainingTime(50, 300)).toBe('约 5 分钟');
    });

    test('剩余时间超过 1 小时时返回小时', () => {
      expect(calculateRemainingTime(10, 3600)).toBe('约 1 小时');
    });
  });

  describe('parseTaskStatus', () => {
    const mockStartTime = Date.now() - 60000; // 1 分钟前

    test('空数据时返回默认值', () => {
      const result = parseTaskStatus(null, mockStartTime);
      
      expect(result.status).toBe('unknown');
      expect(result.progress).toBe(0);
      expect(result.stage).toBe('unknown');
      expect(result.is_completed).toBe(false);
    });

    test('init 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'init',
        progress: 5
      }, mockStartTime);
      
      expect(result.stage).toBe('init');
      expect(result.progress).toBe(10);
      expect(result.statusText).toBe('任务初始化中...');
      expect(result.detailText).toContain('准备诊断环境');
    });

    test('ai_fetching 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'ai_fetching',
        progress: 25,
        results: [{}, {}]
      }, mockStartTime);
      
      expect(result.stage).toBe('ai_fetching');
      expect(result.progress).toBe(30);
      expect(result.statusText).toBe('正在连接 AI 大模型...');
      expect(result.detailText).toContain('2 个 AI 平台');
    });

    test('intelligence_analyzing 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'intelligence_analyzing',
        progress: 55,
        detailed_results: [{}, {}, {}]
      }, mockStartTime);
      
      expect(result.stage).toBe('intelligence_analyzing');
      expect(result.progress).toBe(60);
      expect(result.detailText).toContain('3 条数据');
    });

    test('competition_analyzing 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'competition_analyzing',
        progress: 75
      }, mockStartTime);
      
      expect(result.stage).toBe('competition_analyzing');
      expect(result.progress).toBe(80);
      expect(result.detailText).toContain('品牌分析');
    });

    test('completed 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'completed',
        progress: 95,
        results: [{}, {}, {}, {}]
      }, mockStartTime);
      
      expect(result.stage).toBe('completed');
      expect(result.progress).toBe(100);
      expect(result.is_completed).toBe(true);
      expect(result.detailText).toContain('诊断完成');
    });

    test('failed 阶段解析正确', () => {
      const result = parseTaskStatus({
        stage: 'failed',
        error: 'AI 平台调用失败'
      }, mockStartTime);
      
      expect(result.stage).toBe('failed');
      expect(result.progress).toBe(0);
      expect(result.is_completed).toBe(false);
      expect(result.detailText).toBe('AI 平台调用失败');
    });

    test('未知状态时继续轮询', () => {
      const result = parseTaskStatus({
        stage: 'unknown_stage',
        progress: 40
      }, mockStartTime);
      
      expect(result.stage).toBe('processing');
      expect(result.is_completed).toBe(false);
      expect(result.detailText).toContain('unknown_stage');
    });

    test('后端 progress 优先', () => {
      const result = parseTaskStatus({
        stage: 'ai_fetching',
        progress: 35  // 后端提供的值
      }, mockStartTime);
      
      expect(result.progress).toBe(35);  // 使用后端值而非默认的 30
    });

    test('后端 is_completed 优先', () => {
      const result = parseTaskStatus({
        stage: 'completed',
        is_completed: false  // 后端明确设置为 false
      }, mockStartTime);
      
      expect(result.is_completed).toBe(false);  // 使用后端值
    });

    test('包含剩余时间计算', () => {
      const result = parseTaskStatus({
        stage: 'ai_fetching',
        progress: 50
      }, mockStartTime);
      
      expect(result.remainingTime).toBeTruthy();
      expect(typeof result.remainingTime).toBe('string');
    });

    test('包含结果计数', () => {
      const result = parseTaskStatus({
        stage: 'completed',
        results: [{}, {}],
        detailed_results: [{}, {}, {}]
      }, mockStartTime);
      
      expect(result.resultsCount).toBe(5);  // results + detailed_results
    });
  });

  describe('集成测试', () => {
    test('完整的诊断流程状态变化', () => {
      const startTime = Date.now();
      
      // 初始化阶段
      let state = parseTaskStatus({ stage: 'init' }, startTime);
      expect(state.progress).toBe(10);
      
      // AI 连接阶段
      state = parseTaskStatus({ stage: 'ai_fetching', results: [{}] }, startTime);
      expect(state.progress).toBe(30);
      
      // 智能分析阶段
      state = parseTaskStatus({ stage: 'intelligence_analyzing', results: [{}, {}] }, startTime);
      expect(state.progress).toBe(60);
      
      // 竞争分析阶段
      state = parseTaskStatus({ stage: 'competition_analyzing', results: [{}, {}, {}] }, startTime);
      expect(state.progress).toBe(80);
      
      // 完成阶段
      state = parseTaskStatus({ stage: 'completed', results: [{}, {}, {}, {}] }, startTime);
      expect(state.progress).toBe(100);
      expect(state.is_completed).toBe(true);
    });
  });
});
