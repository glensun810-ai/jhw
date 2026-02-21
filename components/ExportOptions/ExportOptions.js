/**
 * 导出选项组件
 * 支持选择导出格式、报告级别、章节等
 * 
 * 版本：v2.0
 * 日期：2026-02-21
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  /**
   * 组件属性
   */
  properties: {
    // 执行 ID
    executionId: {
      type: String,
      value: ''
    },
    // 是否显示
    visible: {
      type: Boolean,
      value: false
    },
    // 品牌名称
    brandName: {
      type: String,
      value: ''
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 导出格式
    format: 'pdf',  // pdf, html, excel
    
    // 报告级别
    level: 'full',  // basic, detailed, full
    levelOptions: [
      { value: 'basic', label: '基础版', desc: '执行摘要 + 健康度', icon: '📄' },
      { value: 'detailed', label: '详细版', desc: '基础版 + 平台 + 竞品', icon: '📊' },
      { value: 'full', label: '完整版', desc: '全部内容 + 行动计划', icon: '📑' }
    ],
    
    // 可选章节
    sections: {
      executiveSummary: true,
      brandHealth: true,
      platformAnalysis: true,
      competitiveAnalysis: true,
      negativeSources: true,
      roiAnalysis: true,
      actionPlan: true
    },
    sectionOptions: [
      { key: 'executiveSummary', label: '执行摘要', icon: '📊', required: true },
      { key: 'brandHealth', label: '品牌健康度', icon: '💚', required: true },
      { key: 'platformAnalysis', label: '平台表现', icon: '🤖', required: false },
      { key: 'competitiveAnalysis', label: '竞品对比', icon: '⚔️', required: false },
      { key: 'negativeSources', label: '负面信源', icon: '⚠️', required: false },
      { key: 'roiAnalysis', label: 'ROI 指标', icon: '💰', required: false },
      { key: 'actionPlan', label: '行动计划', icon: '📋', required: false }
    ],
    
    // 是否异步生成
    isAsync: false,
    
    // 生成状态
    generating: false,
    progress: 0,
    statusMessage: '',
    
    // 任务 ID
    taskId: ''
  },

  /**
   * 生命周期
   */
  lifetimes: {
    attached() {
      console.log('[ExportOptions] Component attached');
    },
    detached() {
      // 清理定时器
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
      }
    }
  },

  /**
   * 数据监听器
   */
  observers: {
    visible: function(newVisible) {
      if (newVisible) {
        this._initOptions();
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 初始化选项
     */
    _initOptions() {
      const { level } = this.data;
      this._updateSectionsByLevel(level);
    },

    /**
     * 根据级别更新章节
     */
    _updateSectionsByLevel(level) {
      const sections = {
        executiveSummary: true,
        brandHealth: true,
        platformAnalysis: level !== 'basic',
        competitiveAnalysis: level === 'full',
        negativeSources: level === 'full',
        roiAnalysis: level === 'full',
        actionPlan: level === 'full'
      };

      this.setData({ sections });
    },

    /**
     * 切换格式
     */
    onFormatChange(e) {
      const { format } = e.currentTarget.dataset;
      this.setData({ format });
    },

    /**
     * 切换级别
     */
    onLevelChange(e) {
      const { level } = e.currentTarget.dataset;
      this.setData({ level });
      this._updateSectionsByLevel(level);
    },

    /**
     * 切换章节
     */
    onSectionChange(e) {
      const { key } = e.currentTarget.dataset;
      const { sections } = this.data;
      
      // 必选章节不能取消
      const requiredSections = ['executiveSummary', 'brandHealth'];
      if (requiredSections.includes(key) && !sections[key]) {
        wx.showToast({
          title: '此章节为必选项',
          icon: 'none'
        });
        return;
      }

      this.setData({
        [`sections.${key}`]: !sections[key]
      });
    },

    /**
     * 开始导出
     */
    async onExport() {
      const { executionId, format, level, sections, isAsync } = this.data;

      if (!executionId) {
        wx.showToast({
          title: '缺少执行 ID',
          icon: 'none'
        });
        return;
      }

      // 验证章节选择
      const selectedSections = Object.keys(sections).filter(k => sections[k]);
      if (selectedSections.length < 2) {
        wx.showToast({
          title: '请至少选择 2 个章节',
          icon: 'none'
        });
        return;
      }

      this.setData({ 
        generating: true, 
        progress: 0,
        statusMessage: '正在准备导出...'
      });

      try {
        if (format === 'pdf') {
          await this._exportPDF(executionId, level, selectedSections, isAsync);
        } else if (format === 'html') {
          await this._exportHTML(executionId, level);
        } else if (format === 'excel') {
          await this._exportExcel(executionId);
        }

        wx.showToast({
          title: '导出成功',
          icon: 'success'
        });

        this.triggerEvent('success', {
          format,
          level,
          sections: selectedSections
        });

        // 延迟关闭
        setTimeout(() => {
          this._close();
        }, 1500);

      } catch (error) {
        console.error('[ExportOptions] Export failed:', error);
        
        wx.showToast({
          title: error.message || '导出失败',
          icon: 'none'
        });

        this.triggerEvent('error', { error });
      } finally {
        if (!isAsync) {
          this.setData({ generating: false, progress: 0 });
        }
      }
    },

    /**
     * 导出 PDF
     */
    async _exportPDF(executionId, level, sections, isAsync) {
      const app = getApp();
      const baseUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';

      if (isAsync) {
        // 异步导出
        return await this._asyncExportPDF(baseUrl, executionId, level, sections);
      } else {
        // 同步导出
        return await this._syncExportPDF(baseUrl, executionId, level, sections);
      }
    },

    /**
     * 同步导出 PDF
     */
    async _syncExportPDF(baseUrl, executionId, level, sections) {
      this.setData({ 
        progress: 20,
        statusMessage: '正在生成 PDF...'
      });

      return new Promise((resolve, reject) => {
        wx.request({
          url: `${baseUrl}/api/export/pdf`,
          method: 'GET',
          data: {
            executionId,
            level,
            sections: sections.join(','),
            async: 'false'
          },
          responseType: 'arraybuffer',
          timeout: 60000,
          success: (res) => {
            this.setData({ progress: 100, statusMessage: '生成完成' });

            // 保存文件
            const fileName = `report_${executionId}_${Date.now()}.pdf`;
            const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;

            const fs = wx.getFileSystemManager();
            fs.writeFile({
              filePath,
              data: res.data,
              encoding: 'binary',
              success: () => {
                // 打开文件
                wx.openDocument({
                  filePath,
                  showMenu: true,
                  success: () => {
                    console.log('[ExportOptions] Document opened');
                  }
                });
              },
              fail: (err) => {
                console.error('[ExportOptions] Save failed:', err);
                reject(new Error('保存文件失败'));
              }
            });

            resolve(filePath);
          },
          fail: (err) => {
            console.error('[ExportOptions] PDF export failed:', err);
            reject(new Error(err.errMsg || 'PDF 生成失败'));
          }
        });
      });
    },

    /**
     * 异步导出 PDF
     */
    async _asyncExportPDF(baseUrl, executionId, level, sections) {
      this.setData({ 
        progress: 10,
        statusMessage: '提交任务...'
      });

      // 提交任务
      const submitResult = await new Promise((resolve, reject) => {
        wx.request({
          url: `${baseUrl}/api/export/pdf`,
          method: 'GET',
          data: {
            executionId,
            level,
            sections: sections.join(','),
            async: 'true'
          },
          success: resolve,
          fail: reject
        });
      });

      if (submitResult.statusCode !== 202) {
        throw new Error('任务提交失败');
      }

      const taskId = submitResult.data.task_id;
      this.setData({ taskId, progress: 20, statusMessage: '任务已提交' });

      // 轮询任务状态
      return await this._pollTaskStatus(baseUrl, taskId);
    },

    /**
     * 轮询任务状态
     */
    _pollTaskStatus(baseUrl, taskId) {
      return new Promise((resolve, reject) => {
        let pollCount = 0;
        const maxPolls = 60;  // 最多轮询 60 次（2 分钟）

        const poll = () => {
          if (pollCount >= maxPolls) {
            reject(new Error('任务超时，请稍后重试'));
            return;
          }

          wx.request({
            url: `${baseUrl}/api/export/status/${taskId}`,
            method: 'GET',
            success: (res) => {
              const { status, progress, message } = res.data;
              
              this.setData({
                progress: progress || 0,
                statusMessage: message || status
              });

              if (status === 'completed') {
                // 下载文件
                this._downloadFile(baseUrl, taskId)
                  .then(resolve)
                  .catch(reject);
              } else if (status === 'failed') {
                reject(new Error(res.data.error || '生成失败'));
              } else {
                // 继续轮询
                pollCount++;
                setTimeout(poll, 2000);  // 每 2 秒轮询一次
              }
            },
            fail: (err) => {
              reject(new Error('查询任务状态失败'));
            }
          });
        };

        poll();
      });
    },

    /**
     * 下载文件
     */
    _downloadFile(baseUrl, taskId) {
      return new Promise((resolve, reject) => {
        wx.downloadFile({
          url: `${baseUrl}/api/export/download/${taskId}`,
          success: (res) => {
            if (res.statusCode === 200) {
              // 打开文件
              wx.openDocument({
                filePath: res.tempFilePath,
                showMenu: true,
                success: resolve,
                fail: reject
              });
            } else {
              reject(new Error('下载失败'));
            }
          },
          fail: reject
        });
      });
    },

    /**
     * 导出 HTML
     */
    async _exportHTML(executionId, level) {
      const app = getApp();
      const baseUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';

      this.setData({ 
        progress: 50,
        statusMessage: '正在生成 HTML...'
      });

      return new Promise((resolve, reject) => {
        wx.request({
          url: `${baseUrl}/api/export/html`,
          method: 'GET',
          data: {
            executionId,
            level
          },
          success: (res) => {
            this.setData({ progress: 100, statusMessage: '生成完成' });

            // 保存文件
            const fileName = `report_${executionId}_${Date.now()}.html`;
            const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;

            const fs = wx.getFileSystemManager();
            fs.writeFile({
              filePath,
              data: res.data,
              encoding: 'utf8',
              success: () => {
                wx.openDocument({
                  filePath,
                  showMenu: true
                });
                resolve(filePath);
              },
              fail: (err) => {
                reject(new Error('保存文件失败'));
              }
            });
          },
          fail: (err) => {
            reject(new Error(err.errMsg || 'HTML 生成失败'));
          }
        });
      });
    },

    /**
     * 导出 Excel
     */
    async _exportExcel(executionId) {
      // TODO: 实现 Excel 导出
      wx.showToast({
        title: 'Excel 导出功能开发中',
        icon: 'none'
      });
    },

    /**
     * 取消导出
     */
    onCancel() {
      this._close();
    },

    /**
     * 关闭组件
     */
    _close() {
      this.setData({ 
        generating: false,
        progress: 0,
        statusMessage: ''
      });
      this.triggerEvent('close');
    },

    /**
     * 切换异步模式
     */
    onAsyncChange(e) {
      const { value } = e.detail;
      this.setData({ isAsync: value });
    }
  }
});
