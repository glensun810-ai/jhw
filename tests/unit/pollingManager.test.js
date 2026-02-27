/**
 * PollingManager 单元测试
 * 
 * 测试覆盖场景：
 * 1. 开始轮询
 * 2. 停止轮询（基于 should_stop_polling）
 * 3. 指数退避重试
 * 4. 超时处理
 * 5. 资源清理
 * 6. 内存泄漏预防
 * 7. 并发任务处理
 */

// Mock wx.cloud.callFunction
global.wx = {
  cloud: {
    callFunction: jest.fn()
  }
};

// Mock clearTimeout and setTimeout
global.clearTimeout = jest.fn();
global.setTimeout = jest.fn((cb) => {
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

// Import PollingManager
const PollingManager = require('../../miniprogram/services/pollingManager').default;

describe('PollingManager', () => {
  let pollingManager;
  let mockCallbacks;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Create new instance for each test
    pollingManager = new (require('../../miniprogram/services/pollingManager').default.constructor)({
      baseInterval: 100,
      maxInterval: 1000,
      maxRetries: 3,
      timeout: 5000
    });

    // Mock callbacks
    mockCallbacks = {
      onStatus: jest.fn(),
      onComplete: jest.fn(),
      onError: jest.fn(),
      onTimeout: jest.fn()
    };
  });

  afterEach(() => {
    // Clean up all polling tasks
    pollingManager.stopAllPolling();
  });

  describe('startPolling', () => {
    test('should start polling for a task', async () => {
      const executionId = 'test-task-1';
      
      // Mock successful API response
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);

      // Wait for the first poll
      await sleep(50);

      expect(wx.cloud.callFunction).toHaveBeenCalledWith({
        name: 'getDiagnosisStatus',
        data: { executionId }
      });
      expect(mockCallbacks.onStatus).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(true);
    });

    test('should cancel old task if same executionId is already polling', async () => {
      const executionId = 'test-task-2';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      // Start first polling
      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      const oldCallbacks = mockCallbacks;
      const newCallbacks = {
        onStatus: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn(),
        onTimeout: jest.fn()
      };

      // Start second polling with same ID
      pollingManager.startPolling(executionId, newCallbacks);
      await sleep(50);

      // Old callbacks should not be called
      expect(oldCallbacks.onStatus).not.toHaveBeenCalled();
      expect(newCallbacks.onStatus).toHaveBeenCalled();
    });
  });

  describe('stopPolling', () => {
    test('should stop polling when should_stop_polling is true', async () => {
      const executionId = 'test-task-3';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'completed',
          progress: 100,
          should_stop_polling: true
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      expect(mockCallbacks.onComplete).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });

    test('should clean up timers when stopped', async () => {
      const executionId = 'test-task-4';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      const initialTimerCount = clearTimeout.mock.calls.length;
      
      pollingManager.stopPolling(executionId);

      expect(clearTimeout).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });
  });

  describe('exponential backoff', () => {
    test('should implement exponential backoff on errors', async () => {
      const executionId = 'test-task-5';
      
      // Mock API failures
      wx.cloud.callFunction.mockRejectedValueOnce(new Error('Network error'));
      wx.cloud.callFunction.mockRejectedValueOnce(new Error('Network error'));
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      
      // Wait for retries
      await sleep(300);

      // Should retry multiple times
      expect(wx.cloud.callFunction).toHaveBeenCalledTimes(3);
      expect(mockCallbacks.onError).not.toHaveBeenCalled();
    });

    test('should call onError after max retries exceeded', async () => {
      const executionId = 'test-task-6';
      
      // Mock consistent failures
      wx.cloud.callFunction.mockRejectedValue(new Error('Network error'));

      pollingManager.startPolling(executionId, mockCallbacks);
      
      // Wait for all retries
      await sleep(500);

      expect(mockCallbacks.onError).toHaveBeenCalled();
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });
  });

  describe('timeout handling', () => {
    test('should handle timeout correctly', async () => {
      const executionId = 'test-task-7';
      
      // Mock slow response
      wx.cloud.callFunction.mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({
              result: {
                status: 'initializing',
                progress: 10,
                should_stop_polling: false
              }
            });
          }, 10000);
        });
      });

      // Create manager with short timeout
      const shortTimeoutManager = new (require('../../miniprogram/services/pollingManager').default.constructor)({
        baseInterval: 100,
        timeout: 200
      });

      shortTimeoutManager.startPolling(executionId, mockCallbacks);
      
      // Wait for timeout
      await sleep(300);

      expect(mockCallbacks.onTimeout).toHaveBeenCalled();
      expect(shortTimeoutManager.isPolling(executionId)).toBe(false);
      
      shortTimeoutManager.stopAllPolling();
    });
  });

  describe('resource cleanup', () => {
    test('should prevent memory leaks', async () => {
      const executionId = 'test-task-8';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'completed',
          progress: 100,
          should_stop_polling: true
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      // Check that all maps are cleaned up
      expect(pollingManager.pollingTasks.size).toBe(0);
      expect(pollingManager.retryCounts.size).toBe(0);
      expect(pollingManager.startTimes.size).toBe(0);
    });

    test('should clean up all tasks on stopAllPolling', async () => {
      const taskIds = ['task-1', 'task-2', 'task-3'];
      
      wx.cloud.callFunction.mockResolvedValue({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      // Start multiple tasks
      taskIds.forEach(id => {
        pollingManager.startPolling(id, mockCallbacks);
      });

      expect(pollingManager.getActiveTaskCount()).toBe(3);

      pollingManager.stopAllPolling();

      expect(pollingManager.getActiveTaskCount()).toBe(0);
    });
  });

  describe('concurrent tasks', () => {
    test('should handle multiple concurrent tasks', async () => {
      const taskIds = ['task-1', 'task-2', 'task-3'];
      
      wx.cloud.callFunction.mockResolvedValue({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      // Start multiple tasks
      taskIds.forEach(id => {
        pollingManager.startPolling(id, mockCallbacks);
      });

      await sleep(50);

      expect(pollingManager.getActiveTaskCount()).toBe(3);
      
      taskIds.forEach(id => {
        expect(pollingManager.isPolling(id)).toBe(true);
      });

      // Clean up
      pollingManager.stopAllPolling();
    });

    test('should track task status correctly', async () => {
      const executionId = 'test-task-9';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'analyzing',
          progress: 60,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      const taskStatus = pollingManager.getTaskStatus(executionId);
      
      expect(taskStatus).toBeTruthy();
      expect(taskStatus.executionId).toBe(executionId);
      expect(taskStatus.isActive).toBe(true);
    });
  });

  describe('utility methods', () => {
    test('should get elapsed time correctly', async () => {
      const executionId = 'test-task-10';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      const elapsedTime = pollingManager.getElapsedTime(executionId);
      expect(elapsedTime).toBeGreaterThan(0);
    });

    test('should get remaining time correctly', async () => {
      const executionId = 'test-task-11';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      const remainingTime = pollingManager.getRemainingTime(executionId);
      expect(remainingTime).toBeGreaterThan(0);
    });

    test('should cleanup expired tasks', async () => {
      const executionId = 'test-task-12';
      
      wx.cloud.callFunction.mockResolvedValueOnce({
        result: {
          status: 'initializing',
          progress: 10,
          should_stop_polling: false
        }
      });

      pollingManager.startPolling(executionId, mockCallbacks);
      await sleep(50);

      // Cleanup with very short maxAge
      pollingManager.cleanupExpiredTasks(10);
      
      expect(pollingManager.isPolling(executionId)).toBe(false);
    });
  });
});

// Helper function
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
