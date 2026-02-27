#!/usr/bin/env python3
"""
修复 fetchTaskStatus 函数，添加 404 处理逻辑
"""
import re

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换 fetchTaskStatus 函数
old_func = '''  /**
   * 获取任务状态
   */
  fetchTaskStatus: async function(executionId) {
    try {
      const response = await getTaskStatusApi(executionId);

      // 检查是否为完成状态
      if (response && (response.is_completed || response.status === 'completed' || response.progress >= 100)) {
        // 确保进度为 100
        response.progress = 100;
        response.is_completed = true;

        // 立即触发数据格式化逻辑
        this.processCompletedResults(response);
      } else if (response && response.results && Array.isArray(response.results) && response.results.length > 0) {
        // 即使任务未完成，但如果已有结果数据，也可以进行部分处理
        // 这有助于在长时间运行的任务中提供更好的用户体验
        logger.debug('检测到部分结果数据，但任务尚未完成');
      }

      return response;
    } catch (error) {
      logger.error('获取任务状态失败:', error);
      throw error; // 重新抛出错误，让调用方处理
    }
  },'''

new_func = '''  /**
   * 获取任务状态
   */
  fetchTaskStatus: async function(executionId) {
    try {
      const response = await getTaskStatusApi(executionId);

      // 【P0 修复】检查 404 响应
      if (!response || (response.error && response.error.includes('not found'))) {
        // 增加 404 计数器
        this.notFoundCount = (this.notFoundCount || 0) + 1;
        logger.warn(`[404] Task not found (count: ${this.notFoundCount})`);
        
        // 如果连续 5 次 404，停止轮询并提示用户
        if (this.notFoundCount >= 5) {
          clearInterval(this.pollInterval);
          this.pollInterval = null;
          this.setData({
            statusText: '任务不存在或已完成',
            isLoading: false
          });
          wx.showToast({
            title: '诊断任务不存在，请查看历史记录',
            icon: 'none',
            duration: 3000
          });
          // 延迟跳转到历史记录页
          setTimeout(() => {
            wx.navigateTo({ url: '/pages/history/history' });
          }, 3000);
        }
        return null;
      }
      
      // 重置 404 计数器
      this.notFoundCount = 0;

      // 检查是否为完成状态
      if (response && (response.is_completed || response.status === 'completed' || response.progress >= 100)) {
        // 确保进度为 100
        response.progress = 100;
        response.is_completed = true;

        // 立即触发数据格式化逻辑
        this.processCompletedResults(response);
      } else if (response && response.results && Array.isArray(response.results) && response.results.length > 0) {
        // 即使任务未完成，但如果已有结果数据，也可以进行部分处理
        // 这有助于在长时间运行的任务中提供更好的用户体验
        logger.debug('检测到部分结果数据，但任务尚未完成');
      }

      return response;
    } catch (error) {
      logger.error('获取任务状态失败:', error);
      throw error; // 重新抛出错误，让调用方处理
    }
  },'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 文件修改成功')
else:
    print('❌ 未找到匹配的内容')
