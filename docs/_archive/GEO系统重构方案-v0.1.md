🚀 GEO 品牌战略仪表盘：全栈重构与实施方案
0. 核心设计理念 (Architecture Philosophy)
One Source, Multiple Views: 后端返回的同一套数据（API 结果），在前端分裂为两个视图：

Dashboard (决策层)：给老板看。展示分数、雷达图、共识关键词、红黑榜。

Detail (执行层)：给执行层看。展示原始对话、具体信源链接、逐字稿。

Frontend Aggregation: 鉴于目前 API 主要返回文本（见 JSONL 附件），前端必须承担“清洗者”角色，将非结构化文本转化为图表数据。

第一部分：数据层重构 (Data Layer Refactoring)
目标：将 index.js 中原本零散的数据处理逻辑（如 generateTrendChartData）剥离，建立统一的数据聚合引擎。

1. 新增 services/reportAggregator.js (核心引擎)
请 AI Coding 创建此文件，实现以下四个核心转换器：

A. 综合评分计算器 (Score Calculator)

输入：所有模型的 response 文本。

逻辑：如果后端未返回 scores 字段，则基于 NLP 规则（如出现“推荐”、“好”、“强”加分，出现“差”、“贵”、“坑”减分）进行本地模拟打分。

输出：{ totalScore: 85, dimensions: { popularity: 80, sentiment: 90, innovation: 75 } }。

借鉴竞品：引入“加权逻辑”，DeepSeek 和 ChatGPT 的权重设为 1.2（更权威），其他为 1.0。

B. 语义共识提取器 (Consensus Extractor) - ⭐️ 核心竞争力

逻辑：对比 4 个模型的回答。

如果 DeepSeek 和 豆包 都提到了“售后服务差”，则标记为 [高风险共识]。

如果 智谱AI 提到了“性价比高”而 千问 没提，标记为 [独家洞察]。

输出：consensus_list: [{ text: "售后响应慢", count: 3, sentiment: "negative" }]。

C. 信源权重透视 (Source Authority Radar)

逻辑：正则匹配回答中的 URL 或网站名（如 zhihu.com, toutiao.com）。

输出：source_distribution: { "UGC社区": 30%, "官方媒体": 50%, "垂类网站": 20% }。

借鉴竞品：不仅列出网站，还要计算“信源多样性得分”。

D. 竞品拦截分析 (Competitor Interception)

逻辑：检测 AI 回答中是否提及了 competitorBrands 数组中的品牌。

输出：interception_rate: "在 4 个模型中，有 2 个在回答您的品牌时推荐了竞品 X"。

第二部分：界面层重构 (UI Layer Refactoring)
目标：由“长列表”改为“1+1”双页模式。

1. 新建 pages/report/dashboard (麦肯锡看板)
这是用户完成测试后看到的第一屏。

WXML 结构建议：

Header 区：品牌总分（大数字） + 击败了全国 XX% 的品牌。

Chart 区（引入 ECharts）：

雷达图：展示 5 维能力（知名度、美誉度、服务、产品力、创新）。

饼图：情感倾向分析（正面 vs 负面 vs 中立）。

Insight 区（卡片式布局）：

“AI 核心印象”：展示 Top 5 关键词云（Tag Cloud）。

“竞品警报”：显示竞品拦截率。

Action 区：

“GEO 优化建议”：基于短板生成的一句话建议（例如：“建议增加知乎平台的正面案例铺设”）。

主按钮：“查看详细原始报告” -> 跳转至 Detail 页。

2. 重构 pages/report/detail (原始档案)
这是原来的详情页，但需做性能降级处理。

逻辑优化：

分包加载：由于 4 个模型可能返回上万字，必须使用 Chunked Rendering（分片渲染）。

代码实现：复用你之前规划的 setInterval 渲染逻辑，每 50ms 渲染 500 字，避免安卓机卡死。

Tabs 切换：顶部设置 Tab [DeepSeek | 豆包 | 通义 | 智谱]，默认展示内容最丰富的那一个。

第三部分：现有 index.js 的外科手术 (Migration)
现状分析：目前的 index.js 包含大量图表生成逻辑（如 generateTrendChartData）和直接跳转逻辑。

修改计划：

数据存储方式变更：

放弃：URL 传参（wx.navigateTo({ url: '...?results=' + JSON.stringify(...) })）。这会导致数据截断。

采用：全局存储或本地缓存。

JavaScript
// 在 index.js 的 pollTestProgress 完成后：
const reportData = ...; // 获取完整数据
const app = getApp();
app.globalData.currentReport = reportData; // 存入全局

// 调用聚合引擎（新逻辑）
const dashboardData = require('../../services/reportAggregator').aggregate(reportData);
app.globalData.dashboardData = dashboardData;

// 跳转
wx.navigateTo({ url: '/pages/report/dashboard/index' }); // 不带参数
删除冗余代码：

删除 index.js 中的 generateTrendChartData、extractScoreData 等函数，将它们全部迁移并升级到 services/reportAggregator.js 中。

第四部分：给 AI Coding 的分步执行 Prompt (可直接复制)
请按照以下顺序发给 AI Coding，确保它理解上下文：

Step 1: 创建聚合引擎 (The Brain)
"你现在是高级后端工程师。请创建 services/reportAggregator.js。
任务：编写一个 aggregate(rawReportData) 函数，处理来自 DeepSeek、豆包、千问、智谱的原始 API 响应。

评分逻辑：遍历所有 results，如果 API 返回了 scores 字段则使用，否则编写一个基于正则的 fallbackScore 函数，根据文本中的正向/负向词汇计算 0-100 的分数。

共识提取：分析所有模型的 response 文本，找出出现频率超过 2 次的形容词，存入 consensus_keywords。

竞品分析：检查文本中是否提及了 competitorBrands（从全局配置获取），计算 interception_rate。

输出规范：返回一个标准对象 { totalScore, radarData, keywords, advice }，供前端看板使用。"

Step 2: 构建麦肯锡看板 (The Face)
"你现在是资深前端开发。请新建页面 pages/report/dashboard。

布局：采用 'Bento Box' 风格。顶部展示 '品牌健康度总分'。中部使用 ec-canvas 绘制雷达图（维度：知名度、情感、内容量、竞品防御、搜索关联）。

数据源：在 onLoad 中从 app.globalData.dashboardData 读取 Step 1 生成的数据。

交互：底部添加固定按钮 '查看 AI 原始对话'，点击跳转至 pages/report/detail。
请给出 WXML 和 JS 代码，注意 ECharts 的懒加载配置。"

Step 3: 优化详情页与路由 (The Link)
"最后，请修改现有的 index.js 和重构 pages/report/detail。

index.js：在任务完成后，不再通过 URL 传递巨型 JSON。改为将数据存入 app.globalData，并调用 reportAggregator 处理数据，最后跳转到 dashboard 页。

detail 页：实现分片渲染 (Chunked Rendering)。因为 AI 回答可能很长，请使用 setInterval 每 50ms 渲染 500 个字符，防止页面卡顿。添加 Tab 栏以切换不同模型的回答。"

🌟 方案亮点总结
解决了“数据不可读”：通过聚合引擎，将枯燥的文本转为了老板爱看的图表。

解决了“URL 溢出”：放弃 URL 传参，改用内存/缓存，稳定性提升。

解决了“页面卡顿”：看板页轻量化，详情页分片加载，体验丝滑。

复用了现有接口：不需要后端重写 API，完全在前端做数据清洗和增强。