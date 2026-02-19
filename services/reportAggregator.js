/**
 * GEO 品牌战略聚合引擎
 * 
 * 核心逻辑：将 NxM 的原始结果聚合为战略看板 (Dashboard) 数据
 * 
 * 输入：NxM 执行结果数组（问题数 × 模型数 × 主品牌数）
 * 输出：战略看板数据结构（概览评分、问题墙、归因列表）
 */

/**
 * 聚合报告主函数
 * @param {Array} results - NxM 执行结果数组
 * @param {String} brandName - 主品牌名称
 * @param {Array} competitors - 竞品品牌列表
 * @returns {Object} 战略看板数据
 */
export const aggregateReport = (results, brandName, competitors) => {
  if (!results || results.length === 0) return null;

  // 1. 按"问题"进行分组
  const questionMap = {};
  results.forEach(item => {
    const qId = item.question_id;
    if (!questionMap[qId]) {
      questionMap[qId] = {
        questionText: item.question_text,
        models: [],
        totalRank: 0,
        mentionCount: 0,
        sentimentSum: 0,
        competitorInterception: []
      };
    }
    
    const geoData = item.geo_data || {};
    questionMap[qId].models.push(item);
    
    // 统计排名和可见度
    if (geoData.brand_mentioned) {
      questionMap[qId].mentionCount++;
      questionMap[qId].totalRank += (geoData.rank > 0 ? geoData.rank : 10);
      questionMap[qId].sentimentSum += (geoData.sentiment || 0);
    }

    // 统计竞品拦截
    if (geoData.interception && geoData.interception.trim()) {
      questionMap[qId].competitorInterception.push(geoData.interception);
    }
  });

  // 2. 计算全局汇总指标 (Global Metrics)
  const totalQuestions = Object.keys(questionMap).length;
  const totalMentions = results.filter(r => r.geo_data?.brand_mentioned).length;
  const sov = (totalMentions / results.length) * 100; // 声量占比 (Share of Voice)

  // 3. 构建信源黑榜 (Toxic Sources)
  const toxicSources = [];
  results.forEach(r => {
    (r.geo_data?.cited_sources || []).forEach(src => {
      if (src.attitude === 'negative') {
        toxicSources.push({ 
          url: src.url, 
          site: src.site_name, 
          model: r.model,
          attitude: src.attitude 
        });
      }
    });
  });

  // 4. 输出看板专用结构
  return {
    summary: {
      brandName,
      sov: sov.toFixed(1),
      avgSentiment: (results.reduce((acc, r) => acc + (r.geo_data?.sentiment || 0), 0) / results.length).toFixed(2),
      healthScore: calculateHealthScore(sov, results),
      totalTests: results.length,
      totalMentions: totalMentions
    },
    questionCards: Object.values(questionMap).map(q => ({
      text: q.questionText,
      avgRank: q.mentionCount > 0 ? (q.totalRank / q.mentionCount).toFixed(1) : '未入榜',
      status: q.mentionCount > (results.length / totalQuestions / 2) ? 'safe' : 'risk',
      interceptedBy: [...new Set(q.competitorInterception)].slice(0, 2),
      mentionCount: q.mentionCount,
      totalModels: q.models.length,
      avgSentiment: (q.sentimentSum / (q.mentionCount || 1)).toFixed(2)
    })),
    toxicSources: toxicSources.slice(0, 5), // 仅取前 5 个最危险的信源
    competitors: competitors || []
  };
};

/**
 * 内部辅助：健康度算法
 * 
 * 逻辑：声量占 50%，情感占 30%，稳定性占 20%
 * - 声量占比 (SOV): 0-100 分
 * - 情感得分：-1 到 1 映射到 0-100 分
 * - 稳定性：基于提及率的稳定性
 * 
 * @param {Number} sov - 声量占比
 * @param {Array} results - 原始结果
 * @returns {Number} 健康度得分 (0-100)
 */
function calculateHealthScore(sov, results) {
  // 声量占 50%
  const sovScore = sov * 0.5;
  
  // 情感占 30%（将 -1 到 1 映射到 0-100）
  const sentimentBase = results.reduce((acc, r) => acc + (r.geo_data?.sentiment || 0), 0) / results.length;
  const sentimentScore = ((sentimentBase + 1) * 50) * 0.3;
  
  // 稳定性占 20%（基于提及率的稳定性）
  const mentionRate = results.filter(r => r.geo_data?.brand_mentioned).length / results.length;
  const stabilityScore = mentionRate * 100 * 0.2;
  
  const score = sovScore + sentimentScore + stabilityScore;
  return Math.min(Math.max(Math.round(score), 0), 100);
}

/**
 * 获取问题详情数据
 * @param {Array} results - NxM 执行结果数组
 * @param {Number} questionId - 问题 ID
 * @returns {Object} 问题详情数据
 */
export const getQuestionDetail = (results, questionId) => {
  const questionResults = results.filter(r => r.question_id === questionId);
  
  if (!questionResults || questionResults.length === 0) {
    return null;
  }
  
  const questionText = questionResults[0].question_text;
  const modelResults = questionResults.map(r => ({
    model: r.model,
    content: r.content,
    geoData: r.geo_data,
    latency: r.latency,
    status: r.status
  }));
  
  // 计算该问题的汇总指标
  const mentionCount = questionResults.filter(r => r.geo_data?.brand_mentioned).length;
  const avgRank = mentionCount > 0 
    ? (questionResults.reduce((acc, r) => acc + (r.geo_data?.rank > 0 ? r.geo_data.rank : 10), 0) / mentionCount).toFixed(1)
    : '未入榜';
  const avgSentiment = (questionResults.reduce((acc, r) => acc + (r.geo_data?.sentiment || 0), 0) / questionResults.length).toFixed(2);
  
  return {
    questionText,
    modelResults,
    stats: {
      mentionCount,
      totalModels: questionResults.length,
      avgRank,
      avgSentiment
    }
  };
};

/**
 * 获取竞品分析数据
 * @param {Array} results - NxM 执行结果数组
 * @param {Array} competitors - 竞品品牌列表
 * @returns {Object} 竞品分析数据
 */
export const getCompetitorAnalysis = (results, competitors) => {
  if (!competitors || competitors.length === 0) {
    // 如果没有输入竞品，从结果中提取 AI 提及的品牌
    const mentionedBrands = new Set();
    results.forEach(r => {
      if (r.geo_data?.interception && r.geo_data.interception.trim()) {
        mentionedBrands.add(r.geo_data.interception);
      }
    });
    competitors = Array.from(mentionedBrands);
  }
  
  // 统计每个竞品的拦截次数
  const interceptionStats = {};
  competitors.forEach(comp => {
    interceptionStats[comp] = 0;
  });
  
  results.forEach(r => {
    if (r.geo_data?.interception && interceptionStats.hasOwnProperty(r.geo_data.interception)) {
      interceptionStats[r.geo_data.interception]++;
    }
  });
  
  // 转换为数组并排序
  const interceptionList = Object.entries(interceptionStats)
    .map(([brand, count]) => ({ brand, count }))
    .sort((a, b) => b.count - a.count);
  
  return {
    competitors,
    interceptionStats: interceptionList,
    totalInterceptions: interceptionList.reduce((acc, item) => acc + item.count, 0)
  };
};

/**
 * 获取信源分析数据
 * @param {Array} results - NxM 执行结果数组
 * @returns {Object} 信源分析数据
 */
export const getSourceAnalysis = (results) => {
  const sourceMap = {};
  
  results.forEach(r => {
    (r.geo_data?.cited_sources || []).forEach(src => {
      const key = src.url;
      if (!sourceMap[key]) {
        sourceMap[key] = {
          url: src.url,
          site_name: src.site_name,
          attitude: src.attitude,
          mentionCount: 0,
          models: new Set()
        };
      }
      sourceMap[key].mentionCount++;
      sourceMap[key].models.add(r.model);
    });
  });
  
  // 转换为数组
  const sourceList = Object.values(sourceMap).map(s => ({
    ...s,
    models: Array.from(s.models)
  }));
  
  // 分类
  const positiveSources = sourceList.filter(s => s.attitude === 'positive');
  const neutralSources = sourceList.filter(s => s.attitude === 'neutral');
  const negativeSources = sourceList.filter(s => s.attitude === 'negative');
  
  return {
    total: sourceList.length,
    positive: positiveSources,
    neutral: neutralSources,
    negative: negativeSources,
    toxic: negativeSources.slice(0, 5) // 前 5 个负面信源
  };
};

export default {
  aggregateReport,
  getQuestionDetail,
  getCompetitorAnalysis,
  getSourceAnalysis,
  runUnitTests
};

/**
 * 单元测试函数（闭环验收用）
 * 包含 3 组测试数据：正常、部分缺失、全空
 */
export const runUnitTests = () => {
  console.log('\n' + '='.repeat(60));
  console.log('GEO 品牌战略聚合引擎 - 闭环验收测试');
  console.log('='.repeat(60));
  
  const tests = [
    {
      name: '测试 1: 正常数据（3 问题×4 模型×1 主品牌）',
      input: {
        results: [
          // 问题 1 - 4 个模型的回答
          { question_id: 0, question_text: '介绍一下 Tesla', model: 'doubao', geo_data: { brand_mentioned: true, rank: 2, sentiment: 0.7, cited_sources: [{url: 'https://a.com', site_name: 'Site A', attitude: 'positive'}], interception: '' } },
          { question_id: 0, question_text: '介绍一下 Tesla', model: 'qwen', geo_data: { brand_mentioned: true, rank: 3, sentiment: 0.5, cited_sources: [], interception: 'BMW' } },
          { question_id: 0, question_text: '介绍一下 Tesla', model: 'deepseek', geo_data: { brand_mentioned: true, rank: 1, sentiment: 0.8, cited_sources: [{url: 'https://b.com', site_name: 'Site B', attitude: 'negative'}], interception: '' } },
          { question_id: 0, question_text: '介绍一下 Tesla', model: 'zhipu', geo_data: { brand_mentioned: true, rank: 2, sentiment: 0.6, cited_sources: [], interception: '' } },
          // 问题 2 - 4 个模型的回答
          { question_id: 1, question_text: 'Tesla 的主要产品', model: 'doubao', geo_data: { brand_mentioned: true, rank: 3, sentiment: 0.4, cited_sources: [], interception: '' } },
          { question_id: 1, question_text: 'Tesla 的主要产品', model: 'qwen', geo_data: { brand_mentioned: true, rank: 4, sentiment: 0.3, cited_sources: [], interception: 'Mercedes' } },
          { question_id: 1, question_text: 'Tesla 的主要产品', model: 'deepseek', geo_data: { brand_mentioned: false, rank: -1, sentiment: 0, cited_sources: [], interception: '' } },
          { question_id: 1, question_text: 'Tesla 的主要产品', model: 'zhipu', geo_data: { brand_mentioned: true, rank: 2, sentiment: 0.5, cited_sources: [], interception: '' } },
          // 问题 3 - 4 个模型的回答
          { question_id: 2, question_text: 'Tesla 和竞品区别', model: 'doubao', geo_data: { brand_mentioned: true, rank: 1, sentiment: 0.9, cited_sources: [], interception: '' } },
          { question_id: 2, question_text: 'Tesla 和竞品区别', model: 'qwen', geo_data: { brand_mentioned: true, rank: 2, sentiment: 0.7, cited_sources: [], interception: '' } },
          { question_id: 2, question_text: 'Tesla 和竞品区别', model: 'deepseek', geo_data: { brand_mentioned: true, rank: 1, sentiment: 0.8, cited_sources: [], interception: '' } },
          { question_id: 2, question_text: 'Tesla 和竞品区别', model: 'zhipu', geo_data: { brand_mentioned: true, rank: 3, sentiment: 0.6, cited_sources: [], interception: 'BMW' } }
        ],
        brandName: 'Tesla',
        competitors: ['BMW', 'Mercedes', 'Audi']
      },
      expected: {
        sov: 91.7,  // 11/12 = 91.67%
        healthScore: 79, // 近似值
        questionCards: 3,
        toxicSources: 1
      }
    },
    {
      name: '测试 2: 部分数据缺失（某些 geo_data 为空）',
      input: {
        results: [
          { question_id: 0, question_text: '问题 1', model: 'doubao', geo_data: { brand_mentioned: true, rank: 5, sentiment: 0.3, cited_sources: [], interception: '' } },
          { question_id: 0, question_text: '问题 1', model: 'qwen', geo_data: null },
          { question_id: 0, question_text: '问题 1', model: 'deepseek', geo_data: { brand_mentioned: false, rank: -1, sentiment: 0, cited_sources: [], interception: '' } },
          { question_id: 1, question_text: '问题 2', model: 'doubao', geo_data: undefined },
          { question_id: 1, question_text: '问题 2', model: 'qwen', geo_data: { brand_mentioned: true, rank: 8, sentiment: -0.2, cited_sources: [], interception: 'CompetitorA' } }
        ],
        brandName: 'BrandX',
        competitors: ['CompetitorA', 'CompetitorB']
      },
      expected: {
        sov: 40,  // 2/5 = 40%
        questionCards: 2,
        toxicSources: 0
      }
    },
    {
      name: '测试 3: 全空数据',
      input: {
        results: [],
        brandName: 'EmptyBrand',
        competitors: []
      },
      expected: {
        result: null
      }
    }
  ];
  
  let passed = 0;
  let failed = 0;
  
  tests.forEach((test, testIndex) => {
    console.log(`\n${test.name}`);
    console.log('-'.repeat(60));
    
    try {
      const result = aggregateReport(test.input.results, test.input.brandName, test.input.competitors);
      
      if (test.expected.result === null) {
        // 测试 3：期望返回 null
        if (result === null) {
          console.log('  ✅ 通过：返回 null（符合预期）');
          passed++;
        } else {
          console.log(`  ❌ 失败：期望 null，实际返回 ${JSON.stringify(result)}`);
          failed++;
        }
        return;
      }
      
      if (!result) {
        console.log('  ❌ 失败：返回结果为空');
        failed++;
        return;
      }
      
      // 验证 summary
      console.log('\n  Summary 验证:');
      console.log(`    SOV: ${result.summary.sov}% (期望：${test.expected.sov}%)`);
      console.log(`    健康度：${result.summary.healthScore} (期望：~${test.expected.healthScore})`);
      console.log(`    情感均值：${result.summary.avgSentiment}`);
      console.log(`    总提及：${result.summary.totalMentions}/${result.summary.totalTests}`);
      
      // 验证 questionCards
      console.log('\n  QuestionCards 验证:');
      console.log(`    问题数量：${result.questionCards.length} (期望：${test.expected.questionCards})`);
      
      result.questionCards.forEach((q, idx) => {
        console.log(`    \n    问题 ${idx + 1}:`);
        console.log(`      文本：${q.text.substring(0, 20)}...`);
        console.log(`      平均排名：${q.avgRank}`);
        console.log(`      提及率：${q.mentionCount}/${q.totalModels}`);
        console.log(`      情感：${q.avgSentiment}`);
        console.log(`      状态：${q.status}`);
        if (q.interceptedBy.length > 0) {
          console.log(`      ⚠️ 被竞品拦截：${q.interceptedBy}`);
        }
      });
      
      // 验证 toxicSources
      console.log('\n  ToxicSources 验证:');
      console.log(`    负面信源数量：${result.toxicSources.length} (期望：${test.expected.toxicSources})`);
      result.toxicSources.forEach(src => {
        console.log(`      - [${src.site}] ${src.url} (模型：${src.model})`);
      });
      
      // 验证计算逻辑
      const sovMatch = Math.abs(parseFloat(result.summary.sov) - test.expected.sov) < 1;
      const questionCountMatch = result.questionCards.length === test.expected.questionCards;
      const toxicMatch = result.toxicSources.length === test.expected.toxicSources;
      
      if (sovMatch && questionCountMatch && toxicMatch) {
        console.log('\n  ✅ 通过：所有关键指标符合预期');
        passed++;
      } else {
        console.log('\n  ❌ 失败：关键指标不符合预期');
        console.log(`     SOV 匹配：${sovMatch}, 问题数匹配：${questionCountMatch}, 负面信源匹配：${toxicMatch}`);
        failed++;
      }
      
    } catch (error) {
      console.log(`  ❌ 失败：执行异常 - ${error.message}`);
      console.error(error);
      failed++;
    }
  });
  
  // 总结
  console.log('\n' + '='.repeat(60));
  console.log('测试总结');
  console.log('='.repeat(60));
  console.log(`总测试数：${tests.length}`);
  console.log(`通过：${passed}`);
  console.log(`失败：${failed}`);
  console.log(`通过率：${(passed / tests.length * 100).toFixed(1)}%`);
  
  if (failed === 0) {
    console.log('\n🎉 所有测试通过！聚合引擎逻辑验证完成。');
    return true;
  } else {
    console.log('\n⚠️ 部分测试失败，请检查逻辑。');
    return false;
  }
};
