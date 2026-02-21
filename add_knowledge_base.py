#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加知识库数据
old_data = '''    //【P0 新增】进度详情
    remainingTime: 0,
    completedTasks: 0,
    totalTasks: 0,
    currentTask: '',
    pendingTasks: 0,
    taskStartTime: 0
  },'''

new_data = '''    //【P0 新增】进度详情
    remainingTime: 0,
    completedTasks: 0,
    totalTasks: 0,
    currentTask: '',
    pendingTasks: 0,
    taskStartTime: 0,
    //【P0 新增】诊断知识
    knowledgeTip: '',
    knowledgeIndex: 0
  },

  //【P0 新增】诊断知识库
  knowledgeTips: [
    'GEO（Generative Engine Optimization）类似于 SEO，但针对的是 AI 模型而非搜索引擎。',
    '品牌在 AI 模型中的提及率直接影响消费者的购买决策。',
    '情感分析得分>0.2 表示正面评价，<-0.2 表示负面评价。',
    'SOV（Share of Voice）>60% 表示市场领先地位。',
    '被竞品拦截意味着 AI 模型更推荐竞品而非您的品牌。',
    '负面信源的影响力是正面信源的 3 倍，需要及时处理。',
    '多模型诊断可以避免单一 AI 模型的偏见。',
    '排名 1-3 位可见度为 100%，4-6 位为 60%，7-10 位为 30%。'
  ],'''

content = content.replace(old_data, new_data)

# 2. 在 onLoad 中添加知识库初始化
old_onload = '''      // 启动进度条动画（10 秒内平滑滑到 80%）
      this.startProgressAnimation(estimatedTime);

      // 启动轮询
      this.startPolling();'''

new_onload = '''      // 启动进度条动画（10 秒内平滑滑到 80%）
      this.startProgressAnimation(estimatedTime);

      //【P0 新增】启动知识科普
      this.startKnowledgeRotation();

      // 启动轮询
      this.startPolling();'''

content = content.replace(old_onload, new_onload)

# 3. 添加知识轮换方法
old_method = '''  /**
   * 【P0 新增】后台运行功能
   */
  runInBackground: function() {'''

new_method = '''  /**
   * 【P0 新增】启动知识轮换
   */
  startKnowledgeRotation: function() {
    // 显示第一条知识
    this.updateKnowledgeTip();
    
    // 每 10 秒切换一次
    this.knowledgeInterval = setInterval(() => {
      this.updateKnowledgeTip();
    }, 10000);
  },

  /**
   * 【P0 新增】更新知识提示
   */
  updateKnowledgeTip: function() {
    const index = this.data.knowledgeIndex % this.knowledgeTips.length;
    this.setData({
      knowledgeTip: this.knowledgeTips[index],
      knowledgeIndex: index + 1
    });
  },

  /**
   * 【P0 新增】后台运行功能
   */
  runInBackground: function() {'''

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已添加知识库和轮换逻辑')
