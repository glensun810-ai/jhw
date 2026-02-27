/**
 * 诊断流程集成测试
 * 
 * 测试覆盖场景：
 * 1. 完整诊断流程
 * 2. 任务完成时停止轮询
 * 3. 进度更新显示
 * 4. 网络错误优雅处理
 * 5. 任务恢复机制
 * 6. 失败时显示存根报告
 */

// Mock wx API
global.wx = {
  cloud: {
    callFunction: jest.fn()
  },
  showLoading: jest.fn(),
  hideLoading: jest.fn(),
  showToast: jest.fn(),
  showModal: jest.fn(),
  navigateTo: jest.fn(),
  navigateBack: jest.fn(),
  setNavigationBarTitle: jest.fn(),
  getStorageSync: jest.fn(),
  setStorageSync: jest.fn(),
  removeStorageSync: jest.fn()
};

// Mock timers
global.clearTimeout = jest.fn();
global.clearInterval = jest.fn();
global.setTimeout = jest.fn((cb) => {
  cb();
  return 1;
});
global.setInterval = jest.fn((cb) => {
  cb();
  return 1;
});

// Mock console
global.console = {
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn()
};

// Mock feature flags
jest.mock('../../miniprogram/config/featureFlags', () => ({
  isFeatureEnabled: jest.fn(() => false)
}));

// Mock UI helpers
jest.mock('../../miniprogram/utils/uiHelper', () => ({
  showToast: jest.fn(),
  showModal: jest.fn(() => Promise.resolve(true)),
  showLoading: jest.fn(),
  hideLoading: jest.fn()
}));

// Import services
const diagnosisService = require('../../miniprogram/services/diagnosisService').default;
const pollingManager = require('../../miniprogram/services/pollingManager').default;

describe('Diagnosis Flow Integration', () => {
  let mockCallbacks;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockCallbacks = {
      onStatus: jest.fn(),
      onComplete: jest.fn(),
      onError: jest.fn(),
      onTimeout: jest.fn()
    };
  });

  afterEach(() => {
    diagnosisService.dispose();
  });

  describe('complete diagnosis flow', () => {
    test('should complete full diagnosis flow', async () => {
      const executionId = 'test-exec-1';
      const reportId = 'test-report-1';

      // Mock start diagnosis
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          execution_id: executionId,
          report_id: reportId
        }
      });

      // Mock status polling
      wx.cloud.callFunction
        .mockResolvedValueOnce({
          result: {
            status: 'initializing',
            progress: 10,
            should_stop_polling: false
          }
        })
        .mockResolvedValueOnce({
          result: {
            status: 'ai_fetching',
            progress: 50,
            should_stop_polling: false
          }
        })
        .mockResolvedValueOnce({
          result: {
            status: 'completed',
            progress: 100,
            should_stop_polling: true
          }
        });

      // Start diagnosis
      const taskInfo = await diagnosisService.startDiagnosis({
        brand_name: 'Test Brand'
      });

      expect(taskInfo.execution_id).toBe(executionId);
      expect(taskInfo.report_id).toBe(reportId);

      // Start polling
      diagnosisService.startPolling(mockCallbacks);

      // Wait for polling to complete
      await sleep(100);

      // Verify completion
      expect(mockCallbacks.onComplete).toHaveBeenCalled();
      expect(wx.navigateTo).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining('/pages/report/report')
        })
      );
    });
  });

  describe('polling termination', () => {
    test('should stop polling when task completes', async () => {
      const executionId = 'test-exec-2';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'completed',
          progress: 100,
          should_stop_polling: true
        }
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(50);

      expect(mockCallbacks.onComplete).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });

    test('should stop polling on partial success', async () => {
      const executionId = 'test-exec-3';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'partial_success',
          progress: 80,
          should_stop_polling: true
        }
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(50);

      expect(mockCallbacks.onComplete).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });
  });

  describe('progress updates', () => {
    test('should show progress updates', async () => {
      const executionId = 'test-exec-4';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      const progressStages = [
        { status: 'initializing', progress: 10 },
        { status: 'ai_fetching', progress: 40 },
        { status: 'analyzing', progress: 70 },
        { status: 'completed', progress: 100, should_stop_polling: true }
      ];

      progressStages.forEach(stage => {
        wx.cloud.callFunction.mockResolvedValueOnce({
          result: stage
        });
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(100);

      // Verify all progress updates were received
      expect(mockCallbacks.onStatus).toHaveBeenCalledTimes(4);
      expect(mockCallbacks.onStatus).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({
          status: 'initializing',
          progress: 10
        })
      );
      expect(mockCallbacks.onStatus).toHaveBeenNthCalledWith(
        4,
        expect.objectContaining({
          status: 'completed',
          progress: 100
        })
      );
    });
  });

  describe('error handling', () => {
    test('should handle network errors gracefully', async () => {
      const executionId = 'test-exec-5';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      // Mock network errors followed by success
      wx.cloud.callFunction
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          result: {
            status: 'initializing',
            progress: 10,
            should_stop_polling: false
          }
        });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(100);

      // Should retry and eventually succeed
      expect(mockCallbacks.onError).not.toHaveBeenCalled();
      expect(mockCallbacks.onStatus).toHaveBeenCalled();
    });

    test('should show error after max retries', async () => {
      const executionId = 'test-exec-6';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      // Mock consistent network errors
      wx.cloud.callFunction.mockRejectedValue(new Error('Network error'));

      diagnosisService.startPolling(mockCallbacks);
      await sleep(150);

      expect(mockCallbacks.onError).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });

    test('should handle task not found error', async () => {
      const executionId = 'test-exec-7';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      wx.cloud.callFunction.mockRejectedValue({
        code: 'TASK_NOT_FOUND',
        message: 'Task not found'
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(100);

      // Should not retry for non-retryable errors
      expect(mockCallbacks.onError).toHaveBeenCalled();
    });
  });

  describe('task recovery', () => {
    test('should restore pending task on page reload', async () => {
      const savedTask = {
        executionId: 'test-exec-8',
        reportId: 'test-report-8',
        startTime: Date.now()
      };

      // Mock saved task in storage
      wx.getStorageSync.mockReturnValueOnce(savedTask);

      // Mock status check
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'analyzing',
          progress: 60,
          should_stop_polling: false
        }
      });

      const restored = await diagnosisService.restorePendingTask();

      expect(restored).toBeTruthy();
      expect(restored.executionId).toBe(savedTask.executionId);
      expect(diagnosisService.pendingTask).toBeTruthy();
    });

    test('should not restore expired task', async () => {
      const expiredTask = {
        executionId: 'test-exec-9',
        startTime: Date.now() - 7200000 // 2 hours ago
      };

      wx.getStorageSync.mockReturnValueOnce(expiredTask);

      const restored = await diagnosisService.restorePendingTask();

      expect(restored).toBeNull();
      expect(wx.removeStorageSync).toHaveBeenCalled();
    });

    test('should not restore completed task', async () => {
      const completedTask = {
        executionId: 'test-exec-10',
        startTime: Date.now()
      };

      wx.getStorageSync.mockReturnValueOnce(completedTask);

      // Mock completed status
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'completed',
          progress: 100,
          should_stop_polling: true
        }
      });

      const restored = await diagnosisService.restorePendingTask();

      expect(restored).toBeNull();
      expect(wx.removeStorageSync).toHaveBeenCalled();
    });
  });

  describe('stub report on failure', () => {
    test('should show stub report when task fails', async () => {
      const executionId = 'test-exec-11';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      // Mock failure with partial results
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'failed',
          progress: 100,
          should_stop_polling: true,
          error_message: 'Partial AI failures',
          results_count: 5
        }
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(50);

      // Should call onError with proper info
      expect(mockCallbacks.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Partial AI failures',
          status: 'failed'
        })
      );
    });

    test('should handle timeout with partial results', async () => {
      const executionId = 'test-exec-12';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      // Mock timeout with partial results
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'timeout',
          progress: 70,
          should_stop_polling: true,
          results_count: 3
        }
      });

      diagnosisService.startPolling(mockCallbacks);
      await sleep(50);

      expect(mockCallbacks.onError).toHaveBeenCalled();
    });
  });

  describe('resource management', () => {
    test('should clean up resources on dispose', () => {
      diagnosisService.currentTask = {
        executionId: 'test-exec-13',
        startTime: Date.now()
      };

      diagnosisService.dispose();

      expect(diagnosisService.currentTask).toBeNull();
      expect(diagnosisService.pendingTask).toBeNull();
    });

    test('should prevent multiple polling instances', async () => {
      const executionId = 'test-exec-14';

      diagnosisService.currentTask = {
        executionId,
        startTime: Date.now()
      };

      wx.cloud.callFunction.mockResolvedValue({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      // Start polling twice
      diagnosisService.startPolling(mockCallbacks);
      await sleep(30);
      
      const newCallbacks = {
        onStatus: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn(),
        onTimeout: jest.fn()
      };
      diagnosisService.startPolling(newCallbacks);
      await sleep(30);

      // Only the latest callbacks should be called
      expect(mockCallbacks.onStatus).not.toHaveBeenCalled();
      expect(newCallbacks.onStatus).toHaveBeenCalled();
    });
  });
});

// Helper function
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
