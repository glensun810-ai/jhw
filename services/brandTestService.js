const { debug, info, warn, error } = require('../utils/logger');

/**
 * 品牌诊断执行服务
 * 负责诊断任务的启动、轮询、状态管理
 * 
 * P2 优化：使用统一状态枚举
 * P3 优化：集成 SSE 实时推送
 */

const { startBrandTestApi, getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');
const { aggregateReport } = require('./reportAggregator');

// P2 优化：导入状态枚举
const {
  TaskStatus,
  TaskStage,
  TERMINAL_STATUSES,
  FAILED_STATUSES,
  isTerminalStatus,
  isFailedStatus,
  getDisplayText,
} = require('./taskStatusEnums');

// 【P0 关键修复 - 2026-03-02】导入 WebSocket 客户端单例（替代 SSE）
// 注意：webSocketClient.js 导出的是单例实例，不是类，所以不需要 new
const webSocketClient = require('../miniprogram/services/webSocketClient').default;

// 删除 SSE 导入（已清理）
// const { createPollingController: createSSEController } = require('./sseClient');
// 微信小程序使用 WebSocket 或 HTTP 轮询（降级方案）

/**
 * 【P0 颠覆性修复】智能轮询间隔算法 v2.0
 *
 * 借鉴 AWS Step Functions、Google Cloud Tasks 的自适应轮询策略
 * 核心原则：
 * 1. 初期慢轮询（避免无效请求）- init 阶段 2 秒
 * 2. 中期快轮询（快速响应进度）
 * 3. 后期慢轮询（减少资源浪费）
 * 4. 连接质量感知（根据响应时间调整）
 * 5. 连续无进度退避（防止死循环）
 * 6. report_aggregating 阶段特殊处理（长耗时操作）
 *
 * @param {number} progress - 当前进度 (0-100)
 * @param {string} stage - 当前阶段
 * @param {number} lastResponseTime - 上次响应时间（毫秒）
 * @param {number} consecutiveNoProgress - 连续无进度次数
 * @returns {number} 轮询间隔（毫秒）
 */
const getPollingInterval = (progress, stage, lastResponseTime = 100, consecutiveNoProgress = 0) => {
  // 【P0 关键修复】根据阶段智能调整间隔
  let baseInterval;

  // 阶段优先级：stage > progress
  const stageLower = (stage || '').toLowerCase();

  if (stageLower === 'init' || stageLower === 'initializing' || progress < 10) {
    // ⚠️ 初期：任务刚启动，后端异步线程正在初始化
    // AWS 最佳实践：初始等待 2 秒，避免前 10 秒的无效轮询
    baseInterval = 2000;  // 从 800ms 增加到 2000ms
  } else if (stageLower === 'ai_fetching' || (progress >= 10 && progress < 50)) {
    // 🔄 AI 调用阶段：DeepSeek 等模型需要 20-40 秒
    // 策略：中等间隔，避免过度轮询
    baseInterval = 1500;  // 1.5 秒
  } else if (stageLower === 'analyzing' || stageLower === 'intelligence_analyzing' || (progress >= 50 && progress < 80)) {
    // 📊 分析阶段：数据处理和聚合
    // 策略：快速轮询，及时响应用户
    baseInterval = 1000;  // 1 秒
  } else if (stageLower === 'report_aggregating') {
    // 📄 报告聚合阶段：Markdown 转换、PDF 生成等耗时操作
    // 策略：降低轮询频率，减少服务器压力
    // 【P0 修复】使用更长的间隔，避免高频请求加剧 SQLITE_BUSY
    baseInterval = 2000;  // 2 秒
    
    // 【P0 增强】连续无进度时进一步延长间隔
    if (consecutiveNoProgress > 0) {
      const backoffMultiplier = Math.min(Math.pow(1.3, consecutiveNoProgress), 3);
      baseInterval *= backoffMultiplier;
    }
  } else if (stageLower === 'completed' || stageLower === 'finished' || progress >= 90) {
    // ✅ 完成阶段：最后一次确认
    baseInterval = 500;  // 0.5 秒
  } else {
    // 未知阶段：保守策略
    baseInterval = 2000;
  }
  
  // 【P0 增强】连续无进度退避算法
  // 如果连续 N 次无进度，指数退避
  if (consecutiveNoProgress > 0) {
    const backoffMultiplier = Math.min(Math.pow(1.5, consecutiveNoProgress), 4);
    baseInterval *= backoffMultiplier;
  }
  
  // 【P0 增强】连接质量感知
  // 如果后端响应慢，适当延长间隔
  const responseFactor = lastResponseTime / 100;
  const adjustedInterval = baseInterval * Math.max(0.5, Math.min(1.5, responseFactor));
  
  // 限制范围：500ms - 5000ms
  const finalInterval = Math.max(500, Math.min(5000, adjustedInterval));
  
  console.log(`[智能轮询] 阶段=${stage || 'unknown'}, 进度=${progress}%, 间隔=${Math.round(finalInterval)}ms, 无进度次数=${consecutiveNoProgress}`);
  
  return finalInterval;
};

/**
 * 验证输入数据
 * @param {Object} inputData - 输入数据
 * @returns {Object} 验证结果
 */
const validateInput = (inputData) => {
  const { brandName, selectedModels, customQuestions } = inputData;

  // 类型保护：确保 brandName 是字符串，或从对象中提取
  const nameToTrim = (typeof brandName === 'string') ? brandName : (brandName?.brandName || '');
  if (!nameToTrim || nameToTrim.trim() === '') {
    return { valid: false, message: '品牌名称不能为空' };
  }

  if (!selectedModels || selectedModels.length === 0) {
    return { valid: false, message: '请选择至少一个 AI 模型' };
  }

  return { valid: true };
};

/**
 * 构建请求载荷
 * @param {Object} inputData - 输入数据
 * @returns {Object} 请求载荷
 */
const buildPayload = (inputData) => {
  const { brandName, competitorBrands, selectedModels, customQuestions } = inputData;

  const brand_list = [brandName, ...(competitorBrands || [])];

  // P4 修复：前端逻辑保护 - 只保留后端支持的模型
  // 后端支持的模型列表：deepseek, qwen, doubao, chatgpt, gemini, zhipu, wenxin
  const SUPPORTED_MODELS = ['deepseek', 'qwen', 'doubao', 'chatgpt', 'gemini', 'zhipu', 'wenxin'];

  // P1-3 修复：直接发送字符串数组，简化后端处理
  const modelNames = (selectedModels || [])
    .map(item => {
      // 从对象或字符串中提取模型名称
      let modelName;
      if (typeof item === 'object' && item !== null) {
        modelName = (item.id || item.name || item.value || item.label || '').toLowerCase();
      } else if (typeof item === 'string') {
        modelName = item.toLowerCase();
      } else {
        return null;
      }

      // 验证模型名称
      if (!modelName || modelName.trim() === '') {
        return null;
      }

      return modelName;
    })
    .filter(name => {
      // 过滤掉后端不支持的模型
      const isSupported = SUPPORTED_MODELS.includes(name);
      if (!isSupported) {
        console.warn(`⚠️  过滤掉后端不支持的模型：${name}`);
      }
      return isSupported;
    });

  const custom_question = (customQuestions || []).join(' ');

  return {
    brand_list,
    selectedModels: modelNames,  // P1-3 修复：直接发送字符串数组
    custom_question
  };
};

/**
 * 启动品牌诊断（集成 WebSocket）
 * @param {Object} inputData - 输入数据
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 * @returns {Promise<string>} executionId
 */
const startDiagnosis = async (inputData, onProgress, onComplete, onError) => {
  const validation = validateInput(inputData);
  if (!validation.valid) {
    throw new Error(validation.message);
  }

  const payload = buildPayload(inputData);

  console.log('Sending request to API:', payload);

  try {
    const res = await startBrandTestApi(payload);
    const responseData = res.data || res;
    const executionId = responseData.execution_id || responseData.id || (responseData.data && responseData.data.execution_id);

    if (!executionId) {
      throw new Error('未能从响应中提取有效 ID');
    }

    console.log('✅ 诊断任务创建成功，执行 ID:', executionId);

    // 【P0 关键修复 - 2026-03-02】使用 WebSocket 替代轮询
    // 注意：webSocketClient 是单例实例，不需要 new

    // 保存全局引用，防止被 GC
    if (typeof global !== 'undefined') {
      global.wsClient = webSocketClient;
    }

    // 连接 WebSocket
    console.log('[WebSocket] 开始连接:', executionId);
    webSocketClient.connect(executionId, {
      onConnected: () => {
        console.log('[WebSocket] ✅ 连接成功:', executionId);
      },
      
      onProgress: (data) => {
        // 收到进度更新
        console.log('[WebSocket] 📊 进度更新:', data);
        if (onProgress) onProgress(data);
      },
      
      onResult: (data) => {
        // 收到中间结果
        console.log('[WebSocket] 📦 中间结果:', data);
      },
      
      onComplete: (data) => {
        // 诊断完成
        console.log('[WebSocket] ✅ 诊断完成:', data);

        if (onComplete) onComplete(data);

        // 关闭连接
        webSocketClient.close();
        if (typeof global !== 'undefined') {
          global.wsClient = null;
        }
      },
      
      onError: (error) => {
        // 连接错误，降级到轮询
        console.warn('[WebSocket] ⚠️ 连接失败，降级到轮询:', error);

        // 启动 HTTP 轮询
        const pollingController = createPollingController(
          executionId, onProgress, onComplete, onError
        );
      },

      onFallback: () => {
        console.log('[WebSocket] 降级到轮询模式');
        // 启动轮询
        const pollingController = createPollingController(
          executionId, onProgress, onComplete, onError
        );
      }
    });
    
    return executionId;
  } catch (error) {
    console.error('启动诊断失败:', error);
    throw error;
  }
};

/**
 * 创建轮询控制器（P0 修复：支持 WebSocket 降级）
 * @param {string} executionId - 执行 ID
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 * @returns {Object} 轮询控制器
 */
const createPollingController = (executionId, onProgress, onComplete, onError) => {
  // 【P0 关键修复 - 2026-03-02】检查是否已建立 WebSocket 连接
  const hasWebSocket = (typeof global !== 'undefined' && global.wsClient && global.wsClient.isConnected());
  
  if (hasWebSocket) {
    console.log('[brandTestService] ✅ WebSocket 已连接，跳过轮询');
    return { 
      stop: () => {},
      isStopped: () => true,
      mode: 'websocket'
    };  // 返回空控制器
  }
  
  // 启动 HTTP 轮询（降级方案）
  console.log('[brandTestService] ⚠️ WebSocket 不可用，启动 HTTP 轮询（降级方案）');
  
  // 直接使用传统轮询（立即启动）
  const controller = startLegacyPolling(executionId, onProgress, onComplete, onError);

  console.log('[brandTestService] ✅ 轮询已启动，执行 ID:', executionId);
  console.log('[brandTestService] ========== 轮询流程结束 ==========');

  return controller;
};

/**
 * 传统轮询控制器（降级方案）
 * @param {string} executionId - 执行 ID
 * @param {Function} onProgress - 进度回调
 * @param {Function} onComplete - 完成回调
 * @param {Function} onError - 错误回调
 */
const startLegacyPolling = (executionId, onProgress, onComplete, onError) => {
  console.log('[brandTestService] ========== 启动传统轮询模式 ==========');
  console.log('[brandTestService] 执行 ID:', executionId);
  console.log('[brandTestService] 开始时间:', new Date().toLocaleString());

  // 【P0 关键修复 - 2026-03-04】全局熔断标志，防止多个轮询实例并存
  if (global.isTerminated) {
    console.warn('[brandTestService] ⚠️ 全局熔断已触发，跳过轮询启动');
    return { stop: () => {} };
  }

  let pollInterval = null;
  let isStopped = false;
  const maxDuration = 10 * 60 * 1000; // 10 分钟超时

  // 【P0 修复 - 2026-03-02】最大轮询次数限制（最多 500 次，约 5 分钟）
  const MAX_POLL_COUNT = 500;
  let pollCount = 0;

  const startTime = Date.now();

  // Step 1: 错误计数器，实现熔断机制
  let consecutiveAuthErrors = 0;
  const MAX_AUTH_ERRORS = 5;

  // P0 修复：无进度超时计数器
  let lastProgressTime = Date.now();
  const noProgressTimeout = 8 * 60 * 1000; // 8 分钟无进度更新则超时

  // P0 增强：轮询计数器
  let lastLoggedProgress = -1;

  const controller = {
    stop: () => {
      // 【P0 关键修复 - 2026-03-04】清除定时器，确保不会继续触发
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (pollTimeout) {
        clearTimeout(pollTimeout);
        pollTimeout = null;
      }
      isStopped = true;
      console.log('[brandTestService] 轮询已停止，总轮询次数:', pollCount);
    }
  };

  const start = (interval = 800, immediate = true) => {
    // P2 优化：立即触发第一次轮询
    if (immediate) {
      (async () => {
        try {
          const res = await getTaskStatusApi(executionId);
          if (res && (res.progress !== undefined || res.stage)) {
            const parsedStatus = parseTaskStatus(res);
            if (onProgress) onProgress(parsedStatus);

            if (parsedStatus.stage === 'completed' && onComplete) {
              controller.stop();
              onComplete(parsedStatus);
              return;
            }
          }
        } catch (err) {
          console.error('立即轮询失败:', err);

          // 【P0-002 修复】立即轮询时的认证错误处理
          if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
            consecutiveAuthErrors++;

            // 尝试从 Storage 恢复结果
            try {
              const { loadDiagnosisResult } = require('../utils/storage-manager');
              const cachedResults = loadDiagnosisResult(executionId);

              if (cachedResults && (cachedResults.results || cachedResults.detailed_results)) {
                console.log('[立即轮询] ✅ 认证失败但从 Storage 恢复结果成功');
                if (onComplete) {
                  onComplete(cachedResults);
                }
                return;
              }
            } catch (storageErr) {
              console.warn('[立即轮询] 从 Storage 恢复结果失败:', storageErr);
            }

            controller.stop();
            if (onError) onError(new Error('权限验证失败，请重新登录'));
            return;
          }
        }
      })();
    }

    // 启动定时轮询
    let pollTimeout = null;
    let lastResponseTime = Date.now();
    let isPollingInProgress = false;  // 【P0 关键修复 - 2026-03-02】防止轮询重叠的标志

    // 【P0 新增】连续无进度计数器
    let consecutiveNoProgressCount = 0;
    let lastProgressValue = 0;

    // 【P0 新增】30 秒超时提示标志
    let hasShown30sTimeout = false;

    // 【P0 关键修复 - 2026-03-02】report_aggregating 阶段超时保护
    let reportAggregatingStartTime = null;
    const REPORT_AGGREGATING_TIMEOUT = 90000; // 90 秒超时（报告聚合阶段最大允许时间）
    let hasShownAggregatingTimeout = false;

    const poll = async () => {
      // 【P0 关键修复 - 2026-03-02】防止轮询重叠
      if (isPollingInProgress) {
        console.warn('[轮询跳过] 上次轮询仍在进行中，跳过本次请求');
        return;
      }
      
      const requestStartTime = Date.now();
      pollCount++;
      isPollingInProgress = true;  // 标记轮询开始

      try {
        // 【P0 修复 - 2026-03-02】最大轮询次数检查
        if (pollCount >= MAX_POLL_COUNT) {
          controller.stop();
          console.error(`[轮询终止] 达到最大轮询次数 ${MAX_POLL_COUNT}，强制停止`);
          if (onError) {
            onError(new Error(`轮询超时，已尝试 ${MAX_POLL_COUNT} 次，请检查网络或重试`));
          }
          return;
        }

        // P0 增强：定期记录轮询状态（每 10 次或进度变化时）
        const progressChanged = lastLoggedProgress !== -1 &&
          lastLoggedProgress !== (await getTaskStatusApi(executionId).then(r => r.progress).catch(() => -1));
        if (pollCount % 10 === 1 || progressChanged) {
          console.log(`[轮询状态] 第${pollCount}次轮询，最后进度：${lastLoggedProgress === -1 ? '未知' : lastLoggedProgress + '%'}`);
        }

        // 超时检查
        if (Date.now() - startTime > maxDuration) {
          controller.stop();
          console.error(`[轮询超时] 总超时 (10 分钟)，总轮询次数：${pollCount}`);
          if (onError) onError(new Error('诊断超时，请重试或联系管理员'));
          return;
        }

        // P0 修复：无进度超时检查
        if (Date.now() - lastProgressTime > noProgressTimeout) {
          controller.stop();
          console.error(`[轮询超时] 8 分钟无进度更新，总轮询次数：${pollCount}`);
          if (onError) onError(new Error('诊断超时，长时间无响应，请重试'));
          return;
        }

        // 【P0 新增】30 秒无进度提示
        const timeSinceStart = Date.now() - startTime;
        if (timeSinceStart > 30000 && !hasShown30sTimeout) {
          hasShown30sTimeout = true;
          console.warn('[⏰ 30 秒提示] 诊断已启动 30 秒，正在等待 AI 响应，请耐心等待...');
          // 通过 onProgress 回调通知 UI
          if (onProgress) {
            onProgress({
              stage: 'waiting',
              progress: 0,
              statusText: '⏰ AI 响应中，已等待 30 秒...',
              detailText: '首次诊断需要连接 AI 大模型，通常需要 30-60 秒，请耐心等待',
              is_completed: false,
              is_waiting: true
            });
          }
        }

        if (isStopped) {
          return;
        }

        console.log(`[轮询请求] 第${pollCount}次，执行 ID: ${executionId}`);
        const res = await getTaskStatusApi(executionId);
        const responseTime = Date.now() - requestStartTime;
        lastResponseTime = Date.now();

        console.log(`[轮询响应] 第${pollCount}次，耗时：${responseTime}ms, 状态：${res?.stage || '未知'}, 进度：${res?.progress || 0}%`);

        if (res && (res.progress !== undefined || res.stage)) {
          const parsedStatus = parseTaskStatus(res);
          lastLoggedProgress = parsedStatus.progress;

          // 【P0 新增】跟踪进度变化
          const currentProgress = res.progress || 0;
          const currentStage = res.stage || '';
          
          // 【P0 关键修复 - 2026-03-02】report_aggregating 阶段超时保护
          if (currentStage === 'report_aggregating') {
            if (!reportAggregatingStartTime) {
              reportAggregatingStartTime = Date.now();
              console.log('[⏰ report_aggregating] 阶段开始，启动超时保护计时器');
            }
            
            const aggregatingDuration = Date.now() - reportAggregatingStartTime;
            
            // 检查是否超过 90 秒超时
            if (aggregatingDuration > REPORT_AGGREGATING_TIMEOUT && !hasShownAggregatingTimeout) {
              hasShownAggregatingTimeout = true;
              console.error(`[⏰ report_aggregating] 阶段超时！已耗时 ${Math.round(aggregatingDuration / 1000)} 秒，阈值 ${REPORT_AGGREGATING_TIMEOUT / 1000} 秒`);
              
              // 尝试直接获取现有结果
              const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
              const hasDetailedResults = parsedStatus.detailed_results && parsedStatus.detailed_results.length > 0;
              const hasAnyResults = hasResults || hasDetailedResults;
              
              if (hasAnyResults) {
                console.warn('[⏰ report_aggregating] 超时但有结果，强制停止轮询并展示结果');
                controller.stop();
                
                // 通知用户
                if (onProgress) {
                  onProgress({
                    stage: 'completed',
                    progress: 100,
                    statusText: '诊断完成（报告生成超时）',
                    detailText: `已获取 ${hasResults ? hasResults.length : hasDetailedResults.length} 条结果，报告生成超时，直接展示可用数据`,
                    is_completed: true,
                    has_partial_results: true
                  });
                }
                
                if (onComplete) {
                  onComplete(parsedStatus);
                }
                return;
              } else {
                console.error('[⏰ report_aggregating] 超时且无结果，报错处理');
                controller.stop();
                if (onError) {
                  onError(new Error('报告生成超时，请稍后重试或查看历史记录'));
                }
                return;
              }
            }
            
            // 每 30 秒提示一次
            if (aggregatingDuration > 30000 && aggregatingDuration % 30000 < 2000) {
              console.log(`[⏰ report_aggregating] 已耗时 ${Math.round(aggregatingDuration / 1000)} 秒，正在生成报告，请耐心等待...`);
              if (onProgress) {
                onProgress({
                  stage: 'report_aggregating',
                  progress: 90,
                  statusText: '正在深度汇总分析报告...',
                  detailText: `报告生成中，已耗时 ${Math.round(aggregatingDuration / 1000)} 秒，请耐心等待...`,
                  is_completed: false,
                  is_aggregating: true
                });
              }
            }
          } else {
            // 不在 report_aggregating 阶段，重置计时器
            reportAggregatingStartTime = null;
            hasShownAggregatingTimeout = false;
          }
          
          if (currentProgress > lastProgressValue || (currentStage && currentStage !== 'init' && currentStage !== 'initializing')) {
            consecutiveNoProgressCount = 0;
            lastProgressValue = currentProgress;
            lastProgressTime = Date.now();  // 重置无进度计时器
          } else {
            consecutiveNoProgressCount++;
          }

          // P0 修复：更新最后进度时间
          if (parsedStatus.progress > 0 || parsedStatus.stage !== 'init') {
            lastProgressTime = Date.now();
          }

          // BUG-004 修复：使用动态调整的轮询间隔（传入连续无进度次数）
          const newInterval = getPollingInterval(parsedStatus.progress, parsedStatus.stage, responseTime, consecutiveNoProgressCount);
          if (newInterval !== interval) {
            interval = newInterval;
            console.log(`[性能优化] 调整轮询间隔：${interval}ms (响应时间：${responseTime}ms, 进度：${parsedStatus.progress}%, 无进度次数:${consecutiveNoProgressCount})`);
          }

          if (onProgress) {
            onProgress(parsedStatus);
          }

          // 【P0 关键修复】优先检查 should_stop_polling 字段
          // 这是后端明确标记的终止信号，优先级最高
          if (parsedStatus.should_stop_polling === true) {
            controller.stop();
            console.log(`[轮询终止] ✅ 后端标记 should_stop_polling=true，总轮询次数：${pollCount}`);
            console.log(`[轮询终止] 最终状态：status=${parsedStatus.status || parsedStatus.stage}, is_completed=${parsedStatus.is_completed}`);
            console.log(`[轮询终止] 结果数量：results=${parsedStatus.results?.length || 0}, detailed_results=${parsedStatus.detailed_results?.length || 0}`);

            // 判断是成功完成还是失败
            const status = parsedStatus.status || parsedStatus.stage;

            if (status === 'completed' || parsedStatus.is_completed === true) {
              // 成功完成
              console.log('[轮询终止] ✅ 任务成功完成，调用 onComplete 回调');
              
              // 【P0 关键修复 - 2026-03-04】设置全局熔断标志，防止多个 onComplete 调用
              global.isTerminated = true;
              
              if (onComplete) {
                console.log('[轮询终止] 准备跳转到报告页面...');
                onComplete(parsedStatus);
              }
            } else if (status === 'failed') {
              // 失败
              const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
              const hasDetailedResults = parsedStatus.detailed_results && parsedStatus.detailed_results.length > 0;
              const hasAnyResults = hasResults || hasDetailedResults;

              if (hasAnyResults) {
                // 有结果的部分失败，视为部分完成
                console.warn(`[轮询终止] ⚠️ 部分失败但有结果，结果数量：${hasResults ? hasResults : hasDetailedResults}`);
                if (onComplete) {
                  console.log('[轮询终止] 准备跳转到报告页面（部分结果）...');
                  onComplete(parsedStatus);
                }
              } else {
                // 完全失败
                console.error(`[轮询终止] ❌ 完全失败，错误信息：${parsedStatus.error || '诊断失败'}`);
                if (onError) {
                  onError(new Error(parsedStatus.error || '诊断失败'));
                }
              }
            } else {
              // 其他情况，视为完成
              console.log(`[轮询终止] ⚠️ 未知状态，视为完成：${status}`);
              if (onComplete) {
                onComplete(parsedStatus);
              }
            }
            return;
          }

          // P2 优化：使用统一的状态判断函数（兼容旧逻辑）
          const status = parsedStatus.status || parsedStatus.stage;

          if (isTerminalStatus(status)) {
            // 任务完成（包括部分完成）
            controller.stop();
            console.log('[轮询终止] 任务完成，status:', status);
            
            // 【P0 关键修复 - 2026-03-04】设置全局熔断标志
            global.isTerminated = true;
            
            if (onComplete) {
              onComplete(parsedStatus);
            }
            return;
          }

          if (isFailedStatus(status)) {
            // 任务失败
            controller.stop();
            console.log('[轮询终止] 任务失败，status:', status);

            const hasResults = parsedStatus.results && parsedStatus.results.length > 0;
            const hasDetailedResults = parsedStatus.detailed_results && parsedStatus.detailed_results.length > 0;
            const hasAnyResults = hasResults || hasDetailedResults;

            if (hasAnyResults) {
              // 有结果的部分失败，视为部分完成
              console.warn('[品牌诊断] 部分失败但有结果，继续展示可用数据');
              
              // 【P0 关键修复 - 2026-03-04】设置全局熔断标志
              global.isTerminated = true;
              
              if (onComplete) {
                onComplete(parsedStatus);
              }
            } else if (onError) {
              // 完全失败
              onError(new Error(parsedStatus.error || '诊断失败'));
            }
            return;
          }
        }
      } catch (err) {
        console.error('轮询异常:', err);

        const errorInfo = {
          originalError: err,
          statusCode: err.statusCode,
          isAuthError: err.isAuthError || err.statusCode === 403 || err.statusCode === 401,
          isNetworkError: err.errMsg && err.errMsg.includes('request:fail'),
          isTimeout: err.message && err.message.includes('timeout'),
          timestamp: Date.now()
        };

        if (errorInfo.isAuthError) {
          consecutiveAuthErrors++;
          
          // 【P0-002 修复】计算指数退避延迟
          const authErrorRetryDelay = Math.min(
            1000 * Math.pow(2, consecutiveAuthErrors),
            10000
          );
          
          // 【P0-002 修复】在熔断前尝试刷新 token
          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS - 2) {
            console.log('[认证错误] 尝试刷新 token...');
            try {
              // 尝试清除本地认证缓存
              wx.removeStorageSync('user_token');
              console.log('[认证错误] 已清除本地 token 缓存');
            } catch (refreshErr) {
              console.warn('[认证错误] 刷新 token 失败:', refreshErr);
            }
          }
          
          if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
            // 【P0-002 修复】熔断前尝试从 Storage 恢复结果
            console.log('[认证错误熔断] 尝试从 Storage 恢复结果...');
            try {
              const { loadDiagnosisResult } = require('../utils/storage-manager');
              const cachedResults = loadDiagnosisResult(executionId);
              
              if (cachedResults && (cachedResults.results || cachedResults.detailed_results)) {
                console.log('[认证错误熔断] ✅ 从 Storage 恢复结果成功，结果数:', 
                  (cachedResults.results || []).length + (cachedResults.detailed_results || []).length);
                
                // 显示降级提示
                wx.showModal({
                  title: '网络提示',
                  content: '认证信息已过期，但诊断结果已从本地缓存恢复。建议重新登录后再次诊断以获取完整数据。',
                  showCancel: false,
                  confirmText: '知道了'
                });
                
                // 使用恢复的结果完成轮询
                controller.stop();
                if (onComplete) {
                  onComplete(cachedResults);
                }
                return;
              }
            } catch (storageErr) {
              console.warn('[认证错误熔断] 从 Storage 恢复结果失败:', storageErr);
            }
            
            // 无法恢复结果，停止轮询
            controller.stop();
            console.error('[认证错误熔断] 停止轮询');
            if (onError) {
              onError(new Error('权限验证失败，请重新登录'));
            }
            return;
          }
          
          // 使用指数退避延迟重试
          console.log(`[认证错误] 第 ${consecutiveAuthErrors}/${MAX_AUTH_ERRORS} 次，${authErrorRetryDelay}ms 后重试`);
          if (pollTimeout) {
            clearTimeout(pollTimeout);
          }
          pollTimeout = setTimeout(poll, authErrorRetryDelay);
          return;
        } else {
          consecutiveAuthErrors = 0;
          if (errorInfo.isNetworkError) {
            console.warn('网络连接异常，请检查网络设置');
          } else if (errorInfo.isTimeout) {
            console.warn('请求超时，服务器响应缓慢');
          }
        }

        if (onError) {
          const userFriendlyError = createUserFriendlyError(errorInfo);
          onError(userFriendlyError);
        }
      } finally {
        isPollingInProgress = false;  // 【P0 关键修复】标记轮询结束
        
        if (!isStopped) {
          // 【P0 关键修复】使用动态调整的间隔，确保不会重叠
          const nextInterval = getPollingInterval(
            lastLoggedProgress,
            '',  // stage will be checked in next poll
            Date.now() - requestStartTime,
            consecutiveNoProgressCount
          );
          
          pollTimeout = setTimeout(poll, nextInterval);
        }
      }
    };

    poll();

    controller.stop = () => {
      if (pollTimeout) {
        clearTimeout(pollTimeout);
        pollTimeout = null;
      }
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      isStopped = true;
    };
  };

  // ========== 【P0 根因修复】自动启动轮询 ==========
  console.log('[startLegacyPolling] 准备自动启动轮询');
  // 【P0 修复】使用智能轮询间隔算法，初始间隔 2000ms（避免 init 阶段无效请求）
  start(2000, true);  // 从 800ms 改为 2000ms，与 getPollingInterval 保持一致
  console.log('[startLegacyPolling] ✅ start() 已调用，轮询流程已启动');
  // ===============================================

  return { start, stop: controller.stop, isStopped: () => isStopped };
};

/**
 * P1-006 修复：生成用户友好的错误消息
 */
const createUserFriendlyError = (errorInfo) => {
  const errorMessages = {
    auth: '登录已过期，请重新登录',
    network: '网络连接失败，请检查网络设置',
    timeout: '请求超时，服务器响应缓慢',
    AI_PLATFORM_ERROR: 'AI 平台暂时不可用，请稍后重试',
    VALIDATION_ERROR: '输入数据格式错误，请检查后重试',
    AI_CONFIG_ERROR: 'AI 平台配置错误，请联系管理员',
    TASK_EXECUTION_ERROR: '诊断执行失败，已保存的进度不会丢失',
    TASK_TIMEOUT_ERROR: '诊断超时，请重试或联系管理员',
    RATE_LIMIT_ERROR: '请求过于频繁，请稍后再试',
    DATABASE_ERROR: '数据库错误，请联系技术支持',
    default: '诊断过程中断，已保存的进度不会丢失'
  };

  const suggestions = {
    auth: '\n\n建议：\n1. 重新登录\n2. 清除缓存后重试',
    network: '\n\n建议：\n1. 检查设备网络连接\n2. 确认后端服务已启动',
    timeout: '\n\n建议：\n1. 稍后重试\n2. 检查网络速度',
    AI_PLATFORM_ERROR: '\n\n建议：\n1. 稍后重试\n2. 更换其他 AI 模型',
    VALIDATION_ERROR: '\n\n建议：\n1. 检查品牌名称是否正确\n2. 确认已选择 AI 模型',
    AI_CONFIG_ERROR: '\n\n建议：\n1. 联系技术支持\n2. 检查后端配置',
    TASK_EXECUTION_ERROR: '\n\n建议：\n1. 查看历史记录\n2. 重新发起诊断',
    TASK_TIMEOUT_ERROR: '\n\n建议：\n1. 减少 AI 模型数量\n2. 减少问题数量',
    RATE_LIMIT_ERROR: '\n\n建议：\n1. 等待 1 分钟后重试',
    DATABASE_ERROR: '\n\n建议：\n1. 联系技术支持\n2. 提供错误发生时间',
    default: '\n\n建议：\n1. 查看历史记录\n2. 重新发起诊断'
  };

  let errorCode = 'default';
  if (errorInfo.isAuthError) errorCode = 'auth';
  else if (errorInfo.isNetworkError) errorCode = 'network';
  else if (errorInfo.isTimeout) errorCode = 'timeout';
  else if (errorInfo.statusCode === 400) errorCode = 'VALIDATION_ERROR';
  else if (errorInfo.statusCode === 401) errorCode = 'auth';
  else if (errorInfo.statusCode === 403) errorCode = 'auth';
  else if (errorInfo.statusCode === 408) errorCode = 'TASK_TIMEOUT_ERROR';
  else if (errorInfo.statusCode === 429) errorCode = 'RATE_LIMIT_ERROR';
  else if (errorInfo.statusCode === 503) errorCode = 'AI_PLATFORM_ERROR';
  else if (errorInfo.statusCode === 500) errorCode = 'TASK_EXECUTION_ERROR';

  const message = errorMessages[errorCode] || errorMessages.default;
  const suggestion = suggestions[errorCode] || suggestions.default;

  return new Error(message + suggestion);
};

/**
 * 生成战略看板数据
 */
const generateDashboardData = (processedReportData, pageContext) => {
  try {
    let rawResults = null;

    if (Array.isArray(processedReportData)) {
      rawResults = processedReportData;
    } else if (processedReportData && typeof processedReportData === 'object') {
      rawResults = processedReportData.detailed_results
        || processedReportData.results
        || processedReportData.data?.detailed_results
        || processedReportData.data?.results
        || [];
    }

    if (!rawResults || rawResults.length === 0) {
      console.warn('[generateDashboardData] ⚠️ 没有可用的原始结果数据');
      return {
        _error: 'NO_DATA',
        errorMessage: '没有可用的诊断结果数据',
        brandName: pageContext?.brandName || '',
        competitors: pageContext?.competitorBrands || [],
        brandScores: {},
        sov: {},
        risk: {},
        health: {},
        insights: {},
        attribution: {},
        semanticDriftData: null,
        recommendationData: null,
        overallScore: 0,
        timestamp: new Date().toISOString()
      };
    }

    const brandName = pageContext?.brandName || '';
    const competitors = pageContext?.competitorBrands || [];

    const additionalData = {
      semantic_drift_data: processedReportData?.semantic_drift_data || null,
      recommendation_data: processedReportData?.recommendation_data || null,
      negative_sources: processedReportData?.negative_sources || null,
      competitive_analysis: processedReportData?.competitive_analysis || null
    };

    const dashboardData = aggregateReport(rawResults, brandName, competitors, additionalData);

    console.log('[generateDashboardData] ✅ 看板数据生成成功');

    const app = getApp();
    if (app && app.globalData) {
      app.globalData.lastReport = {
        raw: rawResults,
        dashboard: dashboardData,
        competitors: competitors
      };
    }

    return dashboardData;
  } catch (error) {
    console.error('[generateDashboardData] 生成战略看板数据失败:', error);
    return {
      _error: 'GENERATION_ERROR',
      errorMessage: error.message || '生成看板数据失败',
      brandName: pageContext?.brandName || '',
      competitors: pageContext?.competitorBrands || [],
      brandScores: {},
      sov: {},
      risk: {},
      health: {},
      insights: {},
      attribution: {},
      semanticDriftData: null,
      recommendationData: null,
      overallScore: 0,
      timestamp: new Date().toISOString()
    };
  }
};

module.exports = {
  validateInput,
  buildPayload,
  startDiagnosis,
  createPollingController,
  generateDashboardData,
  // 导出传统轮询（向后兼容）
  startLegacyPolling,
  getPollingInterval,
  createUserFriendlyError
};
