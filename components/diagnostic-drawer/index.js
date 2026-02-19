/**
 * 详情抽屉组件逻辑 - 工业级增强版
 * 
 * 核心功能：
 * - 分片渲染引擎 (Chunked Text Engine)
 * - 语义化高亮
 * - 信源引用关联
 * - 多模型切换
 * - 手势控制
 * - 触感反馈
 * 
 * 【增强特性】
 * - 任务 ID 状态锁（线程安全）
 * - 骨架屏占位（瞬间感知）
 * - 滚动置顶（体验优化）
 * - 闭环交互（信源强化）
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },
  
  properties: {
    showDrawer: {
      type: Boolean,
      value: false,
      observer: 'onShowDrawerChange'
    },
    
    currentQuestionData: {
      type: Object,
      value: null,
      observer: 'onQuestionDataChange'
    },
    
    brandName: {
      type: String,
      value: ''
    },
    
    competitors: {
      type: Array,
      value: []
    }
  },
  
  data: {
    // 渲染状态
    isRendering: false,
    renderedNodes: [],
    renderingText: 'AI 分析中...',
    renderTimer: null,
    renderIndex: 0,
    
    // 【任务 1】状态锁
    renderTicket: '',
    activeTicket: '',
    
    // 【任务 2】骨架屏状态
    showSkeleton: false,
    
    // 文本分片配置
    chunkSize: 400,  // 每片 400 字
    renderInterval: 100,  // 每 100ms 渲染一片
    
    // 当前模型
    currentModelId: '',
    currentModelName: '',
    modelList: [],
    
    // 指标数据
    avgRank: '-',
    sentimentValue: '-',
    sentimentStatus: 'neutral',
    riskLevel: 'safe',
    riskLevelText: '低风险',
    
    // 信源列表
    sourceList: [],
    
    // 图片列表（优雅降级）
    imageList: [],
    
    // 态度文本映射
    attitudeTextMap: {
      'positive': '正面',
      'neutral': '中性',
      'negative': '负面'
    },
    
    // 手势控制
    touchStartY: 0,
    touchCurrentY: 0,
    drawerOffset: 100,
    
    // 滚动位置保持
    lastScrollTop: 0
  },
  
  lifetimes: {
    attached() {
      console.log('[DiagnosticDrawer] Component attached');
    },
    
    detached() {
      // 【任务 1】严格清理：组件销毁时清除所有定时器
      this.stopRendering();
      console.log('[DiagnosticDrawer] Component detached, rendering stopped');
    }
  },
  
  methods: {
    /**
     * 【任务 1】停止渲染并清理定时器
     * 
     * 严格清理机制，确保无内存泄漏
     */
    stopRendering() {
      if (this.data.renderTimer) {
        clearTimeout(this.data.renderTimer);
        this.setData({ renderTimer: null });
      }
      
      this.setData({
        isRendering: false,
        renderTicket: ''
      });
      
      console.log('[DiagnosticDrawer] Rendering stopped');
    },
    
    /**
     * 监听抽屉显示状态变化
     */
    onShowDrawerChange(newVal) {
      if (newVal) {
        // 打开抽屉时触发触感反馈
        this.triggerHapticFeedback();
        
        // 【任务 2】显示骨架屏
        this.setData({
          showSkeleton: true,
          renderedNodes: [],
          renderIndex: 0,
          isRendering: true
        });
        
        // 开始分片渲染
        this.startChunkedRendering();
      } else {
        // 关闭抽屉时停止渲染
        this.stopRendering();
        
        // 隐藏骨架屏
        this.setData({ showSkeleton: false });
      }
    },
    
    /**
     * 监听问题数据变化
     */
    onQuestionDataChange(newVal) {
      if (!newVal) return;
      
      // 提取模型列表
      const modelList = this.extractModelList(newVal);
      
      // 设置默认模型（第一个）
      const defaultModel = modelList[0];
      
      // 提取指标数据
      const metrics = this.calculateMetrics(newVal, modelList);
      
      // 提取信源列表
      const sourceList = this.extractSourceList(newVal);
      
      this.setData({
        modelList,
        currentModelId: defaultModel?.id || '',
        currentModelName: defaultModel?.name || '',
        avgRank: metrics.avgRank,
        sentimentValue: metrics.sentimentValue,
        sentimentStatus: metrics.sentimentStatus,
        riskLevel: metrics.riskLevel,
        riskLevelText: metrics.riskLevelText,
        sourceList
      });
      
      // 重新开始渲染
      if (this.data.showDrawer) {
        this.startChunkedRendering();
      }
    },
    
    /**
     * 从问题数据中提取模型列表
     */
    extractModelList(questionData) {
      const models = questionData?.models || [];
      
      return models.map((model, index) => {
        const rank = model.geo_data?.rank || -1;
        const isAnomaly = this.detectModelAnomaly(model, models);
        
        return {
          id: `model-${index}`,
          name: model.model || `模型${index + 1}`,
          rank: rank > 0 ? rank : null,
          isAnomaly,
          rawData: model
        };
      });
    },
    
    /**
     * 检测异常模型（排名明显低于其他模型）
     */
    detectModelAnomaly(currentModel, allModels) {
      const currentRank = currentModel.geo_data?.rank || -1;
      if (currentRank <= 0) return false;
      
      const validRanks = allModels
        .map(m => m.geo_data?.rank)
        .filter(r => r > 0);
      
      if (validRanks.length < 2) return false;
      
      const avgRank = validRanks.reduce((a, b) => a + b, 0) / validRanks.length;
      
      // 如果当前模型排名比平均排名差 3 位以上，标记为异常
      return currentRank - avgRank > 3;
    },
    
    /**
     * 计算指标数据
     */
    calculateMetrics(questionData, modelList) {
      const models = questionData?.models || [];
      const mentionedModels = models.filter(m => m.geo_data?.brand_mentioned);
      
      // 平均排名
      let avgRank = '-';
      if (mentionedModels.length > 0) {
        const rankSum = mentionedModels.reduce((sum, m) => {
          const rank = m.geo_data?.rank || 10;
          return sum + (rank > 0 ? rank : 10);
        }, 0);
        avgRank = (rankSum / mentionedModels.length).toFixed(1);
      }
      
      // 情感指数
      let sentimentValue = 0;
      let sentimentStatus = 'neutral';
      if (mentionedModels.length > 0) {
        const sentimentSum = mentionedModels.reduce((sum, m) => {
          return sum + (m.geo_data?.sentiment || 0);
        }, 0);
        sentimentValue = (sentimentSum / mentionedModels.length).toFixed(2);
        
        const sentimentNum = parseFloat(sentimentValue);
        if (sentimentNum > 0.2) {
          sentimentStatus = 'positive';
        } else if (sentimentNum < -0.2) {
          sentimentStatus = 'negative';
        }
      }
      
      // 风险等级
      const avgRankNum = parseFloat(avgRank) || 10;
      let riskLevel = 'safe';
      let riskLevelText = '低风险';
      
      if (avgRankNum > 5 && sentimentValue < 0) {
        riskLevel = 'critical';
        riskLevelText = '高风险';
      } else if (avgRankNum > 3 || sentimentValue < 0.2) {
        riskLevel = 'warning';
        riskLevelText = '中风险';
      } else if (mentionedModels.length < models.length * 0.3) {
        riskLevel = 'high';
        riskLevelText = '高风险';
      }
      
      return {
        avgRank,
        sentimentValue,
        sentimentStatus,
        riskLevel,
        riskLevelText
      };
    },
    
    /**
     * 提取信源列表
     */
    extractSourceList(questionData) {
      const models = questionData?.models || [];
      const sourceMap = {};
      
      models.forEach(model => {
        const sources = model.geo_data?.cited_sources || [];
        
        sources.forEach(source => {
          const key = source.url || '';
          if (!key) return;
          
          if (!sourceMap[key]) {
            sourceMap[key] = {
              url: source.url,
              site_name: source.site_name || '未知来源',
              attitude: source.attitude || 'neutral',
              mention_count: 0,
              models: []
            };
          }
          
          sourceMap[key].mention_count += 1;
          if (!sourceMap[key].models.includes(model.model)) {
            sourceMap[key].models.push(model.model);
          }
        });
      });
      
      // 转换为数组并按提及次数排序
      return Object.values(sourceMap)
        .sort((a, b) => b.mention_count - a.mention_count);
    },
    
    /**
     * 【核心】分片渲染引擎 - 工业级增强版
     * 
     * 特性：
     * - 每片 400 字
     * - 每 100ms 渲染一片
     * - 路径增量更新 setData
     * - 闪烁光标反馈
     * 
     * 【任务 1 增强】
     * - 任务 ID 状态锁（线程安全）
     * - 竞态检查
     * - 严格清理
     */
    startChunkedRendering() {
      // 获取当前模型的原始文本
      const currentModel = this.data.modelList.find(
        m => m.id === this.data.currentModelId
      );
      
      if (!currentModel) return;
      
      const rawText = currentModel.rawData?.content || '';
      
      if (!rawText) {
        this.setData({ isRendering: false, showSkeleton: false });
        return;
      }
      
      // 【任务 1】生成唯一任务 ID
      const newTicket = `render-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // 切割文本为分片
      const chunks = this.chunkText(rawText, this.data.chunkSize);
      
      // 重置渲染状态
      this.setData({
        renderedNodes: new Array(chunks.length).fill(null).map(() => ({ html: '' })),
        renderIndex: 0,
        isRendering: true,
        renderTicket: newTicket,
        activeTicket: newTicket
      });
      
      // 开始分片渲染
      this.renderChunk(chunks, 0, newTicket);
    },
    
    /**
     * 文本分片
     */
    chunkText(text, chunkSize) {
      const chunks = [];
      let currentIndex = 0;
      
      while (currentIndex < text.length) {
        let endIndex = currentIndex + chunkSize;
        
        // 尝试在句子边界处切割
        if (endIndex < text.length) {
          const sentenceEnd = text.slice(endIndex - 20, endIndex).search(/[.。!?！？]/);
          if (sentenceEnd !== -1) {
            endIndex = currentIndex + sentenceEnd + 1;
          }
        }
        
        chunks.push(text.slice(currentIndex, endIndex));
        currentIndex = endIndex;
      }
      
      return chunks;
    },
    
    /**
     * 渲染单个分片（路径增量更新）
     * 
     * 【任务 1 增强】竞态检查
     */
    renderChunk(chunks, index, ticket) {
      // 【任务 1】竞态检查：如果当前的 renderTicket 不等于最新的 activeTicket，立即退出
      if (ticket !== this.data.activeTicket) {
        console.log('[DiagnosticDrawer] Race condition detected, stopping render:', ticket, this.data.activeTicket);
        return;
      }
      
      if (index >= chunks.length) {
        // 渲染完成
        this.setData({
          isRendering: false,
          renderingText: '分析完成',
          showSkeleton: false  // 【任务 2】隐藏骨架屏
        });
        return;
      }
      
      // 处理分片内容：语义化高亮 + 信标引用
      const processedHtml = this.processChunkContent(chunks[index]);
      
      // 【关键优化】路径增量更新，避免全量 setData
      const dataKey = `renderedNodes[${index}]`;
      this.setData({
        [dataKey]: {
          index,
          html: processedHtml
        }
      });
      
      // 调度下一片
      const nextIndex = index + 1;
      const timer = setTimeout(() => {
        // 【任务 1】再次检查任务 ID（防止定时器累积）
        if (this.data.activeTicket === ticket) {
          this.renderChunk(chunks, nextIndex, ticket);
        }
      }, this.data.renderInterval);
      
      this.setData({ renderTimer: timer, renderIndex: nextIndex });
    },
    
    /**
     * 处理分片内容：语义化高亮 + 信标引用
     */
    processChunkContent(text) {
      let html = text;
      
      // 1. 转义 HTML 特殊字符
      html = html
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
      
      // 2. 品牌名称高亮
      if (this.data.brandName) {
        const brandRegex = new RegExp(`(${this.data.brandName})`, 'g');
        html = html.replace(brandRegex, '<span class="highlight-brand">$1</span>');
      }
      
      // 3. 竞品名称高亮
      this.data.competitors.forEach(comp => {
        const compRegex = new RegExp(`(${comp})`, 'g');
        html = html.replace(compRegex, '<span class="highlight-competitor">$1</span>');
      });
      
      // 4. 信标引用处理 [1], [2] 等
      html = html.replace(/\[(\d+)\]/g, (match, num) => {
        return `<a href="#source-${num}" class="source-ref" data-index="${num}">${match}</a>`;
      });
      
      // 5. 段落换行处理
      html = html.replace(/\n/g, '<br/>');
      
      return html;
    },
    
    /**
     * 切换模型
     * 
     * 【任务 1 增强】严格清理
     * 【任务 2 增强】滚动置顶
     */
    switchModel(e) {
      const model = e.currentTarget.dataset.model;
      
      if (!model) return;
      
      // 触发触感反馈
      this.triggerHapticFeedback();
      
      // 【任务 1】严格清理：停止当前渲染
      this.stopRendering();
      
      // 【任务 2】滚动置顶
      this.scrollToTop();
      
      this.setData({
        currentModelId: model.id,
        currentModelName: model.name,
        renderedNodes: [],
        renderIndex: 0,
        isRendering: true,
        showSkeleton: true  // 【任务 2】显示骨架屏
      });
      
      // 重新开始分片渲染
      this.startChunkedRendering();
    },
    
    /**
     * 【任务 2】滚动置顶
     * 
     * 使用 createSelectorQuery 实现平滑滚动到顶部
     */
    scrollToTop() {
      wx.createSelectorQuery()
        .in(this)
        .select('.drawer-content')
        .boundingClientRect()
        .exec((res) => {
          if (res && res[0]) {
            wx.pageScrollTo({
              scrollTop: 0,
              duration: 300
            });
          }
        });
    },
    
    /**
     * 关闭抽屉
     */
    closeDrawer() {
      this.triggerHapticFeedback();
      this.setData({ showDrawer: false });
      
      // 触发关闭事件
      this.triggerEvent('close');
    },
    
    /**
     * 手势控制：触摸开始
     */
    onDrawerTouchStart(e) {
      this.setData({
        touchStartY: e.touches[0].clientY
      });
    },
    
    /**
     * 手势控制：触摸移动
     */
    onDrawerTouchMove(e) {
      const deltaY = e.touches[0].clientY - this.data.touchStartY;
      
      // 只允许向下拖动
      if (deltaY > 0) {
        const offset = Math.min(100, Math.max(0, (deltaY / 300) * 100));
        this.setData({ drawerOffset: 100 - offset });
      }
      
      // 防止穿透滚动
      return false;
    },
    
    /**
     * 手势控制：触摸结束
     */
    onDrawerTouchEnd(e) {
      const deltaY = e.changedTouches[0].clientY - this.data.touchStartY;
      
      // 如果向下拖动超过 100px，关闭抽屉
      if (deltaY > 100) {
        this.closeDrawer();
      } else {
        // 恢复原位
        this.setData({ drawerOffset: 100 });
      }
    },
    
    /**
     * 防止默认事件（用于遮罩层）
     */
    preventDefault() {
      // 空函数，用于阻止事件冒泡
    },
    
    /**
     * 内容点击处理（信标引用跳转）
     */
    onContentTap(e) {
      console.log('[DiagnosticDrawer] Content tap:', e);
    },
    
    /**
     * 信源卡片点击
     * 
     * 【任务 3 增强】闭环交互
     */
    onSourceTap(e) {
      const source = e.currentTarget.dataset.source;
      
      if (!source) return;
      
      // 触发触感反馈
      this.triggerHapticFeedback();
      
      // 弹出确认对话框
      wx.showModal({
        title: '查看信源',
        content: `是否复制链接去浏览器查看？\n\n${source.site_name}`,
        confirmText: '复制链接',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            this.copySourceLink(source.url);
          }
        }
      });
    },
    
    /**
     * 复制链接
     * 
     * 【任务 3 增强】显式 Toast 提示
     */
    copySourceLink(url) {
      wx.setClipboardData({
        data: url,
        message: '链接已复制',
        success: () => {
          // 【任务 3】复制成功后再次触感反馈
          this.triggerHapticFeedback();
          
          // 【任务 3】显式 Toast 提示
          wx.showToast({
            title: '证据链接已复制，请在浏览器打开',
            icon: 'success',
            duration: 2500
          });
        }
      });
    },
    
    /**
     * 底部操作：复制链接
     */
    onCopyLink() {
      this.triggerHapticFeedback();
      
      const currentModel = this.data.modelList.find(
        m => m.id === this.data.currentModelId
      );
      
      const textToCopy = currentModel?.rawData?.content || '';
      
      wx.setClipboardData({
        data: textToCopy,
        message: '内容已复制',
        success: () => {
          this.triggerHapticFeedback();
          wx.showToast({
            title: '内容已复制',
            icon: 'success'
          });
        }
      });
    },
    
    /**
     * 底部操作：分享
     */
    onShare() {
      this.triggerHapticFeedback();
      
      wx.showShareMenu({
        withShareTicket: true,
        menus: ['shareAppMessage', 'shareTimeline']
      });
    },
    
    /**
     * 底部操作：保存
     */
    onSave() {
      this.triggerHapticFeedback();
      
      wx.showToast({
        title: '已保存到历史记录',
        icon: 'success'
      });
      
      // 触发保存事件
      this.triggerEvent('save', {
        questionData: this.data.currentQuestionData,
        modelId: this.data.currentModelId
      });
    },
    
    /**
     * 图片加载完成
     */
    onImageLoad(e) {
      const { height } = e.detail;
      console.log('[DiagnosticDrawer] Image loaded:', height);
    },
    
    /**
     * 图片加载失败（优雅降级）
     */
    onImageError(e) {
      console.warn('[DiagnosticDrawer] Image load error:', e);
      
      // 设置默认高度，防止布局跳动
      const index = e.currentTarget.dataset.index;
      this.setData({
        [`imageList[${index}].height`]: 200
      });
    },
    
    /**
     * 触感反馈
     */
    triggerHapticFeedback() {
      wx.vibrateShort({
        type: 'light',
        fail: () => {
          // 如果触感不可用，静默失败
        }
      });
    },
    
    /**
     * 保存滚动位置
     */
    saveScrollPosition() {
      // 可以使用 querySelector 获取滚动位置
      // 这里简化处理
      this.data.lastScrollTop = 0;
    },
    
    /**
     * 恢复滚动位置
     */
    restoreScrollPosition() {
      // 可以使用 pageScrollTo 恢复滚动位置
      if (this.data.lastScrollTop > 0) {
        wx.pageScrollTo({
          scrollTop: this.data.lastScrollTop,
          duration: 0
        });
      }
    }
  }
});
