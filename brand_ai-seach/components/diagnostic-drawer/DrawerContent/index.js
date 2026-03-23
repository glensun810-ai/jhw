/**
 * 诊断抽屉内容组件
 * 
 * 职责：
 * - 文本分片渲染
 * - 语义化高亮
 * - 内容展示
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    responseText: {
      type: String,
      value: '',
      observer: 'onResponseTextChange'
    },
    chunkSize: {
      type: Number,
      value: 400
    },
    renderInterval: {
      type: Number,
      value: 100
    }
  },

  data: {
    // 渲染状态
    isRendering: false,
    renderedNodes: [],
    renderingText: 'AI 分析中...',

    // 文本分片
    chunks: [],
    currentChunkIndex: 0,

    // 高亮关键词
    highlightKeywords: []
  },

  lifetimes: {
    attached() {
      console.log('[DrawerContent] 组件已挂载');
    },
    detached() {
      this.clearRenderTimer();
    }
  },

  methods: {
    /**
     * 响应文本变化监听
     */
    onResponseTextChange(newVal) {
      if (newVal) {
        this.startChunkedRender(newVal);
      }
    },

    /**
     * 开始分片渲染
     */
    startChunkedRender(text) {
      // 分割文本为块
      const chunks = this.splitTextIntoChunks(text, this.data.chunkSize);
      
      this.setData({
        chunks,
        currentChunkIndex: 0,
        renderedNodes: [],
        isRendering: true,
        renderingText: 'AI 分析中...'
      });

      // 启动渲染定时器
      this.clearRenderTimer();
      this.renderTimer = setInterval(() => {
        this.renderNextChunk();
      }, this.data.renderInterval);
    },

    /**
     * 分割文本为块
     */
    splitTextIntoChunks(text, chunkSize) {
      const chunks = [];
      let start = 0;
      
      while (start < text.length) {
        let end = start + chunkSize;
        
        // 尝试在句子边界分割
        if (end < text.length) {
          const lastPeriod = text.lastIndexOf('。', end);
          const lastNewline = text.lastIndexOf('\n', end);
          const splitPoint = Math.max(lastPeriod, lastNewline);
          
          if (splitPoint > start) {
            end = splitPoint + 1;
          }
        }
        
        chunks.push(text.slice(start, end));
        start = end;
      }
      
      return chunks;
    },

    /**
     * 渲染下一块
     */
    renderNextChunk() {
      const { chunks, currentChunkIndex, renderedNodes } = this.data;
      
      if (currentChunkIndex >= chunks.length) {
        this.clearRenderTimer();
        this.setData({
          isRendering: false,
          renderingText: ''
        });
        this.triggerEvent('rendercomplete');
        return;
      }

      const newChunk = chunks[currentChunkIndex];
      const newNodes = this.parseChunkToNodes(newChunk);

      this.setData({
        renderedNodes: [...renderedNodes, ...newNodes],
        currentChunkIndex: currentChunkIndex + 1
      });

      // 触发滚动到底部
      this.triggerEvent('scrolltobottom');
    },

    /**
     * 解析块为节点
     */
    parseChunkToNodes(chunk) {
      const nodes = [];
      
      // 简单解析：按换行分割
      const lines = chunk.split('\n');
      
      lines.forEach(line => {
        if (line.trim()) {
          nodes.push({
            type: 'text',
            content: line.trim()
          });
        }
      });
      
      return nodes;
    },

    /**
     * 清除渲染定时器
     */
    clearRenderTimer() {
      if (this.renderTimer) {
        clearInterval(this.renderTimer);
        this.renderTimer = null;
      }
    },

    /**
     * 滚动到顶部
     */
    scrollToTop() {
      this.triggerEvent('scrolltotop');
    }
  }
});
