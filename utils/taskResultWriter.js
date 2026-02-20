/**
 * 任务结果写入器 - 实时写入，避免冲突
 * 
 * 功能:
 * 1. 实时写入每个任务结果
 * 2. 避免重复写入
 * 3. 累加到总结果
 * 4. 并发安全
 */

class TaskResultWriter {
  constructor(pageContext, executionId) {
    this.page = pageContext;
    this.executionId = executionId;
    this.writingTasks = new Set(); // 正在写入的任务
    this.storageKey = 'latestTestResults_' + executionId;
  }

  /**
   * 写入单个任务结果
   */
  writeTask(taskData) {
    const taskKey = this.getTaskKey(taskData);
    
    // 检查是否正在写入
    if (this.writingTasks.has(taskKey)) {
      console.log('⏳ 任务正在写入:', taskKey);
      return false;
    }
    
    // 检查是否已写入
    if (this.isTaskWritten(taskKey)) {
      console.log('✅ 任务已写入:', taskKey);
      return false;
    }
    
    // 标记为正在写入
    this.writingTasks.add(taskKey);
    
    try {
      // 读取现有结果
      const allResults = this.getAllResults();
      
      // 检查是否已存在
      const exists = allResults.some(r => 
        r.question_id === taskData.question_id && 
        r.model === taskData.model
      );
      
      if (exists) {
        console.log('⚠️ 结果已存在:', taskKey);
        this.writingTasks.delete(taskKey);
        return false;
      }
      
      // 添加新结果
      allResults.push({
        question_id: taskData.question_id,
        question_text: taskData.question_text,
        model: taskData.model,
        content: taskData.content,
        geo_data: taskData.geo_data,
        status: taskData.status,
        latency: taskData.latency,
        timestamp: Date.now()
      });
      
      // 写入存储
      wx.setStorageSync(this.storageKey, allResults);
      
      console.log('✅ 任务已写入:', taskKey, '总结果数:', allResults.length);
      
      // 从写入中移除
      this.writingTasks.delete(taskKey);
      
      return true;
    } catch (error) {
      console.error('❌ 写入失败:', taskKey, error);
      this.writingTasks.delete(taskKey);
      return false;
    }
  }

  /**
   * 批量写入任务结果
   */
  writeBatch(taskList) {
    let successCount = 0;
    
    taskList.forEach(task => {
      if (this.writeTask(task)) {
        successCount++;
      }
    });
    
    console.log('📊 批量写入完成:', successCount, '/', taskList.length);
    return successCount;
  }

  /**
   * 获取所有结果
   */
  getAllResults() {
    try {
      return wx.getStorageSync(this.storageKey) || [];
    } catch (error) {
      console.error('读取结果失败:', error);
      return [];
    }
  }

  /**
   * 获取任务键
   */
  getTaskKey(taskData) {
    return taskData.question_id + '_' + taskData.model;
  }

  /**
   * 检查任务是否已写入
   */
  isTaskWritten(taskKey) {
    const writtenKey = 'written_tasks_' + this.executionId;
    const writtenTasks = wx.getStorageSync(writtenKey) || [];
    return writtenTasks.includes(taskKey);
  }

  /**
   * 标记任务为已写入
   */
  markTaskAsWritten(taskKey) {
    const writtenKey = 'written_tasks_' + this.executionId;
    const writtenTasks = wx.getStorageSync(writtenKey) || [];
    
    if (!writtenTasks.includes(taskKey)) {
      writtenTasks.push(taskKey);
      wx.setStorageSync(writtenKey, writtenTasks);
    }
  }

  /**
   * 获取写入统计
   */
  getStats() {
    const allResults = this.getAllResults();
    const writtenKey = 'written_tasks_' + this.executionId;
    const writtenTasks = wx.getStorageSync(writtenKey) || [];
    
    return {
      totalResults: allResults.length,
      writtenTasks: writtenTasks.length,
      writingTasks: this.writingTasks.size
    };
  }

  /**
   * 清空写入记录
   */
  clear() {
    const writtenKey = 'written_tasks_' + this.executionId;
    wx.removeStorageSync(writtenKey);
    wx.removeStorageSync(this.storageKey);
    this.writingTasks.clear();
    console.log('🗑️ 写入记录已清空');
  }
}

module.exports = TaskResultWriter;
