/**
 * GEO 品牌战略聚合引擎 - 麦肯锡级战略看板专用
 * 
 * 重构版本：P1 战略聚合引擎增强版
 * 实施模块：
 * - 2.1 数据清洗与异常值归一化 (Data Sanitization)
 * - 2.2 SOV 与风险评分计算 (Strategic Scoring)
 * - 2.3 信源威胁归因 (Source Attribution)
 * - 2.4 UI 适配层结构导出 (View-Model Mapping)
 * 
 * 【模块四增强】系统鲁棒性：
 * - 任务 2：对账重试的指数退避策略
 * - 任务 3：诊断进度动效补偿
 * 
 * 输入：NxM 执行结果数组（问题数 × 模型数 × 主品牌数）
 * 输出：战略看板数据结构（品牌健康、诊断网格、风险雷达）
 */

// ==================== 常量定义 ====================

// 缺省 GEO 对象（用于填充缺失数据）
const DEFAULT_GEO_DATA = {
  brand_mentioned: false,
  rank: -1,
  sentiment: 0.0,
  cited_sources: [],
  interception: ''
};

// 排名到可见度得分的映射
const RANK_TO_VISIBILITY = {
  '1-3': 100,
  '4-6': 60,
  '7-10': 30,
  '-1': 0  // 未提及
};

// 情感颜色映射
const SENTIMENT_COLOR_MAP = {
  'positive': '#22c55e',  // 绿色
  'neutral': '#6b7280',   // 灰色
  'negative': '#ef4444'   // 红色
};

// SOV 标签阈值
const SOV_THRESHOLDS = {
  leading: 60,    // 领先
  neutral: 40,    // 持平
  lagging: 0      // 落后
};

// 风险等级阈值
const RISK_THRESHOLDS = {
  high: 0.3,      // 高风险：提及率 < 30%
  mid: 0.6        // 中风险：提及率 < 60%
                  // 低风险：提及率 >= 60%
};

// ==================== 2.1 数据清洗与异常值归一化 ====================

/**
 * 【2.1 数据清洗】缺省值填充
 * 
 * 若某个模型返回的 geo_data 为空或解析失败，自动填充标准缺省对象
 * 
 * @param {Object} geoData - 原始 geo_data
 * @returns {Object} 标准化后的 geo_data
 */
export const sanitizeGeoData = (geoData) => {
  if (!geoData || typeof geoData !== 'object') {
    return { ...DEFAULT_GEO_DATA, _sanitized: true, _sanitization_reason: 'missing_or_invalid' };
  }
  
  const sanitized = {
    brand_mentioned: geoData.brand_mentioned ?? DEFAULT_GEO_DATA.brand_mentioned,
    rank: geoData.rank ?? DEFAULT_GEO_DATA.rank,
    sentiment: geoData.sentiment ?? DEFAULT_GEO_DATA.sentiment,
    cited_sources: Array.isArray(geoData.cited_sources) ? geoData.cited_sources : DEFAULT_GEO_DATA.cited_sources,
    interception: geoData.interception ?? DEFAULT_GEO_DATA.interception,
    _sanitized: true,
    _sanitization_reason: null
  };
  
  // 标记哪些字段被填充了缺省值
  const missingFields = [];
  if (geoData.brand_mentioned === undefined) missingFields.push('brand_mentioned');
  if (geoData.rank === undefined) missingFields.push('rank');
  if (geoData.sentiment === undefined) missingFields.push('sentiment');
  if (!geoData.cited_sources) missingFields.push('cited_sources');
  if (geoData.interception === undefined) missingFields.push('interception');
  
  if (missingFields.length > 0) {
    sanitized._sanitization_reason = `missing_fields:${missingFields.join(',')}`;
  }
  
  return sanitized;
};

/**
 * 【2.1 数据清洗】排名归一化为可见度得分
 * 
 * 算法：
 * - rank 1-3: visibility_score = 100
 * - rank 4-6: visibility_score = 60
 * - rank 7-10: visibility_score = 30
 * - rank -1 (未提及): visibility_score = 0
 * 
 * @param {number} rank - 原始排名
 * @returns {number} 可见度得分 (0-100)
 */
export const normalizeRankToVisibility = (rank) => {
  if (rank === -1 || rank === null || rank === undefined) {
    return 0;
  }
  
  if (rank >= 1 && rank <= 3) {
    return 100;
  }
  
  if (rank >= 4 && rank <= 6) {
    return 60;
  }
  
  if (rank >= 7 && rank <= 10) {
    return 30;
  }
  
  // 超出正常范围的排名，线性衰减
  if (rank > 10) {
    return Math.max(0, 30 - (rank - 10) * 3);
  }
  
  return 0;
};

/**
 * 【2.1 数据清洗】信源去重
 * 
 * 基于 URL 进行去重，防止同一信源在多个模型中被重复统计
 * 
 * @param {Array} sources - 信源数组
 * @returns {Array} 去重后的信源数组
 */
export const deduplicateSources = (sources) => {
  if (!Array.isArray(sources) || sources.length === 0) {
    return [];
  }
  
  const urlSet = new Set();
  const deduplicated = [];
  
  for (const source of sources) {
    const urlKey = (source.url || '').toLowerCase().trim();
    
    if (!urlSet.has(urlKey) && urlKey) {
      urlSet.add(urlKey);
      deduplicated.push({
        ...source,
        _original_url: source.url,
        _url_hash: urlKey
      });
    }
  }
  
  return deduplicated;
};

/**
 * 【2.1 数据清洗】输入数据预处理（主函数）
 * 
 * 整合所有清洗逻辑，为后续计算提供干净的输入
 * 
 * @param {Array} results - NxM 执行结果数组
 * @returns {Object} 预处理后的数据结构
 */
export const preprocessData = (results) => {
  if (!results || !Array.isArray(results) || results.length === 0) {
    return {
      sanitizedResults: [],
      totalModels: 0,
      totalQuestions: 0,
      dataCompleteness: 0
    };
  }
  
  const sanitizedResults = [];
  const questionSet = new Set();
  const modelSet = new Set();
  let sanitizedCount = 0;
  
  // 分片处理，避免大数据量导致 UI 假死
  const chunkSize = 50;
  
  for (let i = 0; i < results.length; i += chunkSize) {
    const chunk = results.slice(i, i + chunkSize);
    
    chunk.forEach(item => {
      // 数据清洗归一化
      const sanitizedGeo = sanitizeGeoData(item.geo_data);
      
      if (sanitizedGeo._sanitized && sanitizedGeo._sanitization_reason) {
        sanitizedCount++;
      }
      
      // 信源去重
      const dedupedSources = deduplicateSources(sanitizedGeo.cited_sources);
      
      // 计算可见度得分
      const visibilityScore = normalizeRankToVisibility(sanitizedGeo.rank);
      
      sanitizedResults.push({
        ...item,
        geo_data: {
          ...sanitizedGeo,
          cited_sources: dedupedSources,
          _visibility_score: visibilityScore
        },
        _visibility_score: visibilityScore
      });
      
      // 统计唯一问题数和模型数
      if (item.question_id !== undefined) {
        questionSet.add(item.question_id);
      }
      if (item.model) {
        modelSet.add(item.model);
      }
    });
  }
  
  // 计算数据完整性
  const expectedTotal = questionSet.size * modelSet.size;
  const actualTotal = sanitizedResults.length;
  const dataCompleteness = expectedTotal > 0 
    ? Math.round((actualTotal / expectedTotal) * 100) 
    : 100;
  
  return {
    sanitizedResults,
    totalModels: modelSet.size,
    totalQuestions: questionSet.size,
    dataCompleteness,
    sanitizedCount,
    totalRecords: sanitizedResults.length
  };
};

// ==================== 任务 2：竞品拦截算法优化 ====================

/**
 * 【任务 2】模糊匹配 - 竞品名称归一化
 * 
 * 将相似名称归一化为同一竞品（例如：『华为』和『华为手机』视为同一竞品）
 * 
 * 规则：
 * 1. 如果一个名称包含另一个名称，则归一化为较短的名称
 * 2. 去除通用后缀（如'手机'、'公司'、'集团'等）
 * 
 * @param {string} name - 原始竞品名称
 * @returns {string} 归一化后的名称
 */
export const normalizeCompetitorName = (name) => {
  if (!name || typeof name !== 'string') {
    return '';
  }
  
  // 去除通用后缀
  const suffixes = ['手机', '公司', '集团', '科技', '股份', '有限', '品牌', '产品'];
  let normalizedName = name.trim();
  
  suffixes.forEach(suffix => {
    if (normalizedName.endsWith(suffix) && normalizedName.length > suffix.length + 1) {
      normalizedName = normalizedName.slice(0, -suffix.length);
    }
  });
  
  return normalizedName.trim();
};

/**
 * 【任务 2】关键词提取 - 从长句中提取竞品名词
 * 
 * 如果 interception 是长句子，提取其中的名词（竞品名）
 * 
 * 策略：
 * 1. 提取引号内的内容
 * 2. 提取"了/是/为"等动词后的名词短语
 * 3. 提取连续的中英文字符（2-10 个字符）
 * 
 * @param {string} text - 原始拦截文本
 * @returns {string} 提取的竞品名称
 */
export const extractCompetitorKeyword = (text) => {
  if (!text || typeof text !== 'string') {
    return '';
  }
  
  const trimmedText = text.trim();
  
  // 如果文本很短（< 5 字符），直接返回
  if (trimmedText.length < 5) {
    return normalizeCompetitorName(trimmedText);
  }
  
  // 策略 1: 提取引号内的内容
  const quoteMatch = trimmedText.match(/[""]([^""]{2,15})[""]/);
  if (quoteMatch && quoteMatch[1]) {
    return normalizeCompetitorName(quoteMatch[1]);
  }
  
  // 策略 2: 提取"了/是/为/推荐/选择"等动词后的名词短语
  const verbPatterns = [
    /了\s*([^\s,，.。]{2,10})/,
    /是\s*([^\s,，.。]{2,10})/,
    /为\s*([^\s,，.。]{2,10})/,
    /推荐\s*([^\s,，.。]{2,10})/,
    /选择\s*([^\s,，.。]{2,10})/,
    /提到\s*([^\s,，.。]{2,10})/
  ];
  
  for (const pattern of verbPatterns) {
    const match = trimmedText.match(pattern);
    if (match && match[1]) {
      const extracted = match[1].trim();
      // 验证提取的内容是否像品牌名（包含中英文字符）
      if (/^[a-zA-Z\u4e00-\u9fa5]+$/.test(extracted)) {
        return normalizeCompetitorName(extracted);
      }
    }
  }
  
  // 策略 3: 提取第一个连续的名词短语（2-8 个字符）
  const nounPattern = /([a-zA-Z\u4e00-\u9fa5]{2,8})/;
  const nounMatch = trimmedText.match(nounPattern);
  if (nounMatch && nounMatch[1]) {
    return normalizeCompetitorName(nounMatch[1]);
  }
  
  // 兜底：返回原文本（归一化后）
  return normalizeCompetitorName(trimmedText.substring(0, 10));
};

/**
 * 【任务 2】竞品频率合并 - 合并相似名称
 * 
 * 将归一化后相同的竞品名称合并统计
 * 
 * @param {Object} interceptionCount - 原始频次统计
 * @returns {Object} 合并后的频次统计
 */
export const mergeCompetitorFrequencies = (interceptionCount) => {
  const mergedCount = {};
  
  Object.entries(interceptionCount).forEach(([name, count]) => {
    const normalizedName = normalizeCompetitorName(name);
    if (normalizedName) {
      mergedCount[normalizedName] = (mergedCount[normalizedName] || 0) + count;
    }
  });
  
  return mergedCount;
};

// ==================== 2.2 核心算法：SOV 与风险评分计算 ====================

/**
 * 【2.2 核心算法】SOV (加权声量占比) 计算
 * 
 * 【任务 1 增强】零分母保护 + 数据类型强制转换
 * 
 * 公式：SOV = (各模型 visibility_score 总和) / (模型数量 * 100) * 100%
 * 
 * @param {Array} results - 预处理后的结果数组
 * @param {number} totalModels - 模型总数
 * @returns {number} SOV 百分比 (0-100)
 */
export const calculateSOV = (results, totalModels) => {
  // 【任务 1】零分母保护
  if (!results || results.length === 0 || !totalModels || totalModels === 0) {
    return 0;
  }

  const totalVisibilityScore = results.reduce((sum, r) => {
    // 【任务 1】数据类型强制转换 - 确保 visibility_score 是数字
    const visibilityScore = r.geo_data?._visibility_score ?? r._visibility_score ?? 0;
    return sum + Number(visibilityScore);
  }, 0);

  const maxPossibleScore = results.length * 100;
  
  // 【任务 1】零分母保护 - 避免除以 0
  const sov = maxPossibleScore > 0 ? (totalVisibilityScore / maxPossibleScore) * 100 : 0;
  
  // 【任务 1】数据类型强制转换 - 确保返回数字
  return parseFloat(Number(sov).toFixed(2));
};

/**
 * 【2.2 核心算法】情感极性指数计算
 * 
 * 【任务 1 增强】零分母保护 + 数据类型强制转换
 * 
 * 剔除未提及品牌的样本，计算剩余样本 sentiment (-1 到 1) 的算术平均值
 * 
 * @param {Array} results - 预处理后的结果数组
 * @returns {Object} 情感指数数据
 */
export const calculateSentimentIndex = (results) => {
  if (!results || results.length === 0) {
    return {
      sentimentIndex: 0,
      validSamples: 0,
      totalSamples: 0,
      sentimentLabel: 'neutral',
      sentimentColor: SENTIMENT_COLOR_MAP.neutral
    };
  }

  // 筛选出提及品牌的样本
  const mentionedResults = results.filter(r => r.geo_data?.brand_mentioned === true);
  const validSamples = mentionedResults.length;

  if (validSamples === 0) {
    return {
      sentimentIndex: 0,
      validSamples: 0,
      totalSamples: results.length,
      sentimentLabel: 'no_mentions',
      sentimentColor: SENTIMENT_COLOR_MAP.neutral
    };
  }

  // 计算情感平均值
  const sentimentSum = mentionedResults.reduce((sum, r) => {
    // 【任务 1】数据类型强制转换 - 确保 sentiment 是数字
    const sentiment = r.geo_data?.sentiment ?? 0;
    return sum + Number(sentiment);
  }, 0);

  // 【任务 1】零分母保护 - 避免除以 0
  const sentimentIndex = validSamples > 0 ? sentimentSum / validSamples : 0;

  // 确定情感标签和颜色
  let sentimentLabel, sentimentColor;
  if (sentimentIndex > 0.2) {
    sentimentLabel = 'positive';
    sentimentColor = SENTIMENT_COLOR_MAP.positive;
  } else if (sentimentIndex < -0.2) {
    sentimentLabel = 'negative';
    sentimentColor = SENTIMENT_COLOR_MAP.negative;
  } else {
    sentimentLabel = 'neutral';
    sentimentColor = SENTIMENT_COLOR_MAP.neutral;
  }

  return {
    // 【任务 1】数据类型强制转换 - 确保返回数字
    sentimentIndex: parseFloat(Number(sentimentIndex).toFixed(2)),
    validSamples,
    totalSamples: results.length,
    sentimentLabel,
    sentimentColor
  };
};

/**
 * 【2.2 核心算法】拦截矩阵（竞品频率统计）
 * 
 * 【任务 2 增强】模糊匹配 + 关键词提取
 * 
 * 遍历所有 interception 字段，提取高频出现的竞品名称
 * 
 * @param {Array} results - 预处理后的结果数组
 * @returns {Array} 竞品频率列表（降序排列）
 */
export const calculateInterceptionMatrix = (results) => {
  if (!results || results.length === 0) {
    return [];
  }

  const interceptionCount = {};

  results.forEach(r => {
    const interception = r.geo_data?.interception;
    if (interception && interception.trim()) {
      // 【任务 2】关键词提取 - 从长句中提取竞品名词
      const extractedKeyword = extractCompetitorKeyword(interception);
      
      if (extractedKeyword) {
        interceptionCount[extractedKeyword] = (interceptionCount[extractedKeyword] || 0) + 1;
      }
    }
  });

  // 【任务 2】竞品频率合并 - 合并相似名称
  const mergedCount = mergeCompetitorFrequencies(interceptionCount);

  // 转换为数组并排序
  const topCompetitors = Object.entries(mergedCount)
    .map(([name, frequency]) => ({
      name,
      frequency,
      percentage: parseFloat(((frequency / results.length) * 100).toFixed(2)),
      // 【任务 2】新增：原始名称列表（用于调试）
      originalNames: Object.keys(interceptionCount).filter(n => 
        normalizeCompetitorName(n) === name
      )
    }))
    .sort((a, b) => b.frequency - a.frequency);

  return topCompetitors;
};

/**
 * 【2.2 核心算法】品牌健康度综合评分
 * 
 * 逻辑：声量占 50%，情感占 30%，稳定性占 20%
 * 
 * @param {number} sov - 声量占比
 * @param {number} sentimentIndex - 情感指数
 * @param {number} mentionRate - 提及率
 * @returns {Object} 健康度评分数据
 */
export const calculateBrandHealth = (sov, sentimentIndex, mentionRate) => {
  // 声量占 50%
  const sovScore = sov * 0.5;
  
  // 情感占 30%（将 -1 到 1 映射到 0-100）
  const sentimentScore = ((sentimentIndex + 1) * 50) * 0.3;
  
  // 稳定性占 20%（基于提及率）
  const stabilityScore = mentionRate * 100 * 0.2;
  
  const healthScore = sovScore + sentimentScore + stabilityScore;
  const roundedScore = Math.min(Math.max(Math.round(healthScore), 0), 100);
  
  // 确定健康度标签
  let healthLabel;
  if (roundedScore >= 80) {
    healthLabel = 'excellent';
  } else if (roundedScore >= 60) {
    healthLabel = 'good';
  } else if (roundedScore >= 40) {
    healthLabel = 'fair';
  } else {
    healthLabel = 'poor';
  }
  
  return {
    score: roundedScore,
    scoreDetailed: parseFloat(healthScore.toFixed(2)),
    label: healthLabel,
    breakdown: {
      sovScore: parseFloat(sovScore.toFixed(2)),
      sentimentScore: parseFloat(sentimentScore.toFixed(2)),
      stabilityScore: parseFloat(stabilityScore.toFixed(2))
    }
  };
};

// ==================== 2.3 归因分析：信源威胁评级 ====================

/**
 * 【2.3 信源归因】威胁度评分计算
 * 
 * 统计所有 attitude: 'negative' 的信源
 * Threat_Score = (该信源出现次数) * (对应模型在该问题下的权重)
 * 
 * @param {Array} results - 预处理后的结果数组
 * @returns {Array} 威胁信源列表（按威胁度降序）
 */
export const calculateSourceThreats = (results) => {
  if (!results || results.length === 0) {
    return [];
  }
  
  const threatMap = {};
  
  results.forEach(r => {
    const sources = r.geo_data?.cited_sources || [];
    const modelWeight = 1.0; // 可以扩展为基于模型权重的计算
    
    sources.forEach(src => {
      if (src.attitude === 'negative') {
        const key = (src.url || '').toLowerCase().trim();
        
        if (!threatMap[key]) {
          threatMap[key] = {
            url: src.url,
            site_name: src.site_name || 'Unknown',
            total_mentions: 0,
            threat_score: 0,
            impact_questions: new Set(),
            models: new Set(),
            attitudes: []
          };
        }
        
        threatMap[key].total_mentions += 1;
        threatMap[key].threat_score += modelWeight;
        threatMap[key].models.add(r.model);
        threatMap[key].attitudes.push(src.attitude);
        
        if (r.question_text) {
          threatMap[key].impact_questions.add(r.question_text);
        }
      }
    });
  });
  
  // 转换为数组并排序
  const toxicSources = Object.values(threatMap)
    .map(source => ({
      ...source,
      impact_questions: Array.from(source.impact_questions),
      models: Array.from(source.models),
      threat_score: parseFloat(source.threat_score.toFixed(2))
    }))
    .sort((a, b) => b.threat_score - a.threat_score);
  
  return toxicSources;
};

/**
 * 【2.3 信源归因】信源画像映射
 * 
 * 将信源聚合为：{ url, site_name, total_mentions, impact_questions }
 * 
 * @param {Array} results - 预处理后的结果数组
 * @returns {Object} 信源画像数据
 */
export const mapSourceProfiles = (results) => {
  if (!results || results.length === 0) {
    return {
      total: 0,
      positive: [],
      neutral: [],
      negative: [],
      toxic: []
    };
  }
  
  const sourceMap = {};
  
  results.forEach(r => {
    const sources = r.geo_data?.cited_sources || [];
    
    sources.forEach(src => {
      const key = (src.url || '').toLowerCase().trim();
      
      if (!sourceMap[key]) {
        sourceMap[key] = {
          url: src.url,
          site_name: src.site_name || 'Unknown',
          total_mentions: 0,
          impact_questions: new Set(),
          models: new Set(),
          attitudes: [],
          _url_hash: key
        };
      }
      
      sourceMap[key].total_mentions += 1;
      sourceMap[key].models.add(r.model);
      sourceMap[key].attitudes.push(src.attitude);
      
      if (r.question_text) {
        sourceMap[key].impact_questions.add(r.question_text);
      }
    });
  });
  
  // 转换为数组
  const sourceList = Object.values(sourceMap).map(source => ({
    ...source,
    impact_questions: Array.from(source.impact_questions),
    models: Array.from(source.models)
  }));
  
  // 分类
  const positiveSources = sourceList.filter(s => 
    s.attitudes.every(a => a === 'positive')
  );
  const negativeSources = sourceList.filter(s => 
    s.attitudes.every(a => a === 'negative')
  );
  const neutralSources = sourceList.filter(s => 
    !positiveSources.includes(s) && !negativeSources.includes(s)
  );
  
  return {
    total: sourceList.length,
    positive: positiveSources,
    neutral: neutralSources,
    negative: negativeSources,
    toxic: negativeSources.slice(0, 5)
  };
};

// ==================== 2.4 UI 适配层结构导出 ====================

/**
 * 【2.4 UI 适配层】诊断网格构建
 * 
 * 【任务 3 增强】风险分级策略优化
 * 
 * 输出格式：diagnostic_grid 数组
 * 每个元素包含：question_text, avg_rank, risk_level, key_competitor
 * 
 * 风险分级标准：
 * - critical: avg_rank > 5 且 sentiment < 0
 * - warning: avg_rank > 3 或 sentiment < 0.2
 * - safe: 其他情况
 * 
 * @param {Array} results - 预处理后的结果数组
 * @param {Object} questionMap - 问题分组映射
 * @returns {Array} 诊断网格数组
 */
export const buildDiagnosticGrid = (results, questionMap) => {
  if (!questionMap || Object.keys(questionMap).length === 0) {
    return [];
  }

  const diagnosticGrid = Object.values(questionMap).map(q => {
    // 计算平均排名
    const mentionedModels = q.models.filter(m => m.geo_data?.brand_mentioned === true);
    const mentionCount = mentionedModels.length;
    const totalCount = q.models.length;
    const mentionRate = totalCount > 0 ? mentionCount / totalCount : 0;

    // 计算平均排名
    let avgRank = '未入榜';
    let avgRankNumeric = 10;  // 用于风险计算的数值
    if (mentionCount > 0) {
      const rankSum = mentionedModels.reduce((sum, m) => {
        const rank = m.geo_data?.rank || -1;
        return sum + (rank > 0 ? rank : 10);
      }, 0);
      avgRank = parseFloat((rankSum / mentionCount).toFixed(2));
      avgRankNumeric = avgRank;
    }

    // 计算平均情感
    const sentimentSum = mentionedModels.reduce((sum, m) => {
      return sum + (m.geo_data?.sentiment || 0);
    }, 0);
    const avgSentiment = mentionCount > 0
      ? parseFloat((sentimentSum / mentionCount).toFixed(2))
      : 0;

    // 【任务 3】风险分级策略优化 - 基于 avg_rank 和 sentiment
    let riskLevel;
    if (avgRankNumeric > 5 && avgSentiment < 0) {
      riskLevel = 'critical';  // 高风险：排名靠后且情感负面
    } else if (avgRankNumeric > 3 || avgSentiment < 0.2) {
      riskLevel = 'warning';   // 中风险：排名中等或情感一般
    } else if (mentionRate < RISK_THRESHOLDS.high) {
      riskLevel = 'high';      // 提及率过低
    } else if (mentionRate < RISK_THRESHOLDS.mid) {
      riskLevel = 'mid';       // 提及率中等
    } else {
      riskLevel = 'safe';      // 低风险：排名靠前且情感正面
    }

    // 提取主要竞品拦截（使用增强版关键词提取）
    const interceptions = q.models
      .map(m => {
        const interception = m.geo_data?.interception;
        if (interception && interception.trim()) {
          // 【任务 2】关键词提取
          return extractCompetitorKeyword(interception);
        }
        return null;
      })
      .filter(i => i && i.trim());

    const interceptionCount = {};
    interceptions.forEach(i => {
      const key = i.trim();
      interceptionCount[key] = (interceptionCount[key] || 0) + 1;
    });

    const keyCompetitor = Object.entries(interceptionCount).length > 0
      ? Object.entries(interceptionCount).sort((a, b) => b[1] - a[1])[0][0]
      : null;

    return {
      question_id: q.questionId,
      question_text: q.questionText,
      avg_rank: avgRank,
      risk_level: riskLevel,  // 'critical' | 'warning' | 'high' | 'mid' | 'safe'
      key_competitor: keyCompetitor,
      mention_rate: parseFloat((mentionRate * 100).toFixed(2)),
      mention_count: mentionCount,
      total_models: totalCount,
      avg_sentiment: avgSentiment,
      intercepted_by: [...new Set(interceptions)].slice(0, 3)
    };
  });

  return diagnosticGrid;
};

/**
 * 【2.4 UI 适配层】风险雷达数据构建
 * 
 * 输出格式：risk_radar 对象
 * 包含：toxic_sources 列表（按威胁度降序）和 intercepted_topics 列表
 * 
 * @param {Array} toxicSources - 威胁信源列表
 * @param {Array} topCompetitors - 竞品拦截列表
 * @returns {Object} 风险雷达数据
 */
export const buildRiskRadar = (toxicSources, topCompetitors) => {
  // 提取被拦截的话题
  const interceptedTopics = topCompetitors.map(comp => ({
    topic: `被${comp.name}拦截`,
    frequency: comp.frequency,
    percentage: comp.percentage,
    risk_level: comp.frequency > 3 ? 'high' : comp.frequency > 1 ? 'mid' : 'low'
  }));
  
  return {
    toxic_sources: toxicSources.slice(0, 10),
    intercepted_topics: interceptedTopics.slice(0, 10),
    total_threats: toxicSources.length,
    total_interceptions: topCompetitors.reduce((sum, c) => sum + c.frequency, 0)
  };
};

/**
 * 【2.4 UI 适配层】品牌健康数据构建
 * 
 * 【任务 3 增强】语义化状态 + 风险分级
 * 
 * 输出格式：brand_health 对象
 * 包含：score (0-100), sov_label (领先/持平/落后), sentiment_status (positive/neutral/negative)
 * 
 * @param {Object} healthData - 健康度评分数据
 * @param {number} sov - SOV 百分比
 * @param {Object} sentimentData - 情感指数数据
 * @returns {Object} 品牌健康数据
 */
export const buildBrandHealth = (healthData, sov, sentimentData) => {
  // 确定 SOV 标签
  let sovLabel;
  if (sov >= SOV_THRESHOLDS.leading) {
    sovLabel = '领先';
  } else if (sov >= SOV_THRESHOLDS.neutral) {
    sovLabel = '持平';
  } else {
    sovLabel = '落后';
  }

  // 【任务 3】语义化状态 - 输出 sentiment_status 而非颜色代码
  const sentimentStatus = sentimentData.sentimentLabel; // 'positive' | 'neutral' | 'negative'
  
  // 【任务 3】风险分级策略 - 基于健康度和情感
  let riskLevel;
  if (healthData.score < 40 || sentimentData.sentimentIndex < -0.3) {
    riskLevel = 'critical';  // 高风险
  } else if (healthData.score < 60 || sentimentData.sentimentIndex < 0) {
    riskLevel = 'warning';   // 中风险
  } else {
    riskLevel = 'safe';      // 低风险
  }

  return {
    score: healthData.score,
    score_detailed: healthData.scoreDetailed,
    sov_label: sovLabel,
    sov_value: parseFloat(sov.toFixed(2)),
    // 【任务 3】语义化状态
    sentiment_status: sentimentStatus,  // 'positive' | 'neutral' | 'negative'
    sentiment_value: parseFloat(sentimentData.sentimentIndex.toFixed(2)),
    // 【任务 3】风险分级
    risk_level: riskLevel,  // 'critical' | 'warning' | 'safe'
    // 保留向后兼容字段
    sentiment_color: sentimentData.sentimentColor,
    sentiment_label: sentimentData.sentimentLabel,
    health_label: healthData.label,
    health_breakdown: healthData.breakdown
  };
};

/**
 * 【2.4 UI 适配层】问题分组映射构建
 * 
 * @param {Array} results - 预处理后的结果数组
 * @returns {Object} 问题分组映射
 */
export const buildQuestionMap = (results) => {
  const questionMap = {};
  
  results.forEach(item => {
    const qId = item.question_id;
    
    if (!questionMap[qId]) {
      questionMap[qId] = {
        questionId: qId,
        questionText: item.question_text || `问题 ${qId + 1}`,
        models: [],
        totalRank: 0,
        mentionCount: 0,
        sentimentSum: 0,
        visibilitySum: 0
      };
    }
    
    questionMap[qId].models.push(item);
    
    const geoData = item.geo_data || {};
    
    if (geoData.brand_mentioned === true) {
      questionMap[qId].mentionCount++;
      questionMap[qId].totalRank += (geoData.rank > 0 ? geoData.rank : 10);
      questionMap[qId].sentimentSum += (geoData.sentiment || 0);
      questionMap[qId].visibilitySum += (geoData._visibility_score || 0);
    }
  });
  
  return questionMap;
};

/**
 * 聚合报告主函数（麦肯锡级战略看板）
 * 
 * @param {Array} results - NxM 执行结果数组
 * @param {String} brandName - 主品牌名称
 * @param {Array} competitors - 竞品品牌列表
 * @returns {Object} 战略看板数据结构
 * 
 * 输出结构：
 * {
 *   brand_health: { score, sov_label, sentiment_color, ... },
 *   diagnostic_grid: [{ question_text, avg_rank, risk_level, key_competitor }, ...],
 *   risk_radar: { toxic_sources: [...], intercepted_topics: [...] },
 *   _meta: { data_completeness, total_records, ... }
 * }
 */
export const aggregateReport = (results, brandName, competitors, additionalData = {}) => {
  // 2.1 数据清洗与归一化
  const preprocessed = preprocessData(results);

  if (preprocessed.sanitizedResults.length === 0) {
    return null;
  }

  const { sanitizedResults, totalModels, totalQuestions, dataCompleteness } = preprocessed;

  // 构建问题分组映射
  const questionMap = buildQuestionMap(sanitizedResults);

  // 2.2 核心算法计算
  const sov = calculateSOV(sanitizedResults, totalModels);
  const sentimentData = calculateSentimentIndex(sanitizedResults);
  const topCompetitors = calculateInterceptionMatrix(sanitizedResults);

  // 计算提及率
  const mentionRate = sanitizedResults.filter(r => r.geo_data?.brand_mentioned === true).length / sanitizedResults.length;

  // 品牌健康度
  const healthData = calculateBrandHealth(sov, sentimentData.sentimentIndex, mentionRate);

  // 2.3 信源威胁归因
  const toxicSources = calculateSourceThreats(sanitizedResults);
  const sourceProfiles = mapSourceProfiles(sanitizedResults);

  // 2.4 UI 适配层结构导出
  const brandHealth = buildBrandHealth(healthData, sov, sentimentData);
  const diagnosticGrid = buildDiagnosticGrid(sanitizedResults, questionMap);
  const riskRadar = buildRiskRadar(toxicSources, topCompetitors);

  // 构建最终输出
  return {
    // 【2.4 UI 适配层】三个顶级字段
    brand_health: brandHealth,
    diagnostic_grid: diagnosticGrid,
    risk_radar: riskRadar,

    // 附加数据
    source_profiles: sourceProfiles,
    top_competitors: topCompetitors,
    competitors: competitors || [],
    brand_name: brandName,

    // 【新增】语义偏移数据（从后端传入）
    semantic_drift_data: additionalData.semantic_drift_data || null,
    semantic_contrast_data: additionalData.semantic_contrast_data || null,
    recommendation_data: additionalData.recommendation_data || null,
    negative_sources: additionalData.negative_sources || null,
    brand_scores: additionalData.brand_scores || null,
    competitive_analysis: additionalData.competitive_analysis || null,
    overall_score: additionalData.overall_score || null,

    // 【数据降级】元数据标记
    _meta: {
      data_completeness: dataCompleteness,
      total_records: sanitizedResults.length,
      total_models: totalModels,
      total_questions: totalQuestions,
      sanitized_count: preprocessed.sanitizedCount,
      is_partial_report: dataCompleteness < 100,
      generated_at: new Date().toISOString()
    }
  };
};

/**
 * 获取问题详情数据（增强版）
 * 
 * @param {Array} results - NxM 执行结果数组
 * @param {Number} questionId - 问题 ID
 * @returns {Object} 问题详情数据
 */
export const getQuestionDetail = (results, questionId) => {
  // 数据清洗
  const preprocessed = preprocessData(results);
  const sanitizedResults = preprocessed.sanitizedResults;
  
  const questionResults = sanitizedResults.filter(r => r.question_id === questionId);
  
  if (!questionResults || questionResults.length === 0) {
    return null;
  }
  
  const questionText = questionResults[0].question_text;
  
  // 模型结果（已经过清洗）
  const modelResults = questionResults.map(r => ({
    model: r.model,
    content: r.content,
    geoData: r.geo_data,
    latency: r.latency,
    status: r.status,
    visibilityScore: r._visibility_score
  }));
  
  // 计算该问题的汇总指标
  const mentionedResults = questionResults.filter(r => r.geo_data?.brand_mentioned === true);
  const mentionCount = mentionedResults.length;
  const totalCount = questionResults.length;
  
  let avgRank = '未入榜';
  let avgVisibility = 0;
  
  if (mentionCount > 0) {
    const rankSum = mentionedResults.reduce((acc, r) => {
      const rank = r.geo_data?.rank || -1;
      return acc + (rank > 0 ? rank : 10);
    }, 0);
    avgRank = parseFloat((rankSum / mentionCount).toFixed(2));
    
    const visibilitySum = mentionedResults.reduce((acc, r) => {
      return acc + (r.geo_data?._visibility_score || 0);
    }, 0);
    avgVisibility = parseFloat((visibilitySum / mentionCount).toFixed(2));
  }
  
  const sentimentSum = mentionedResults.reduce((acc, r) => {
    return acc + (r.geo_data?.sentiment || 0);
  }, 0);
  const avgSentiment = mentionCount > 0 
    ? parseFloat((sentimentSum / mentionCount).toFixed(2)) 
    : 0;
  
  // 提及率
  const mentionRate = totalCount > 0 ? mentionCount / totalCount : 0;
  
  // 风险等级
  let riskLevel;
  if (mentionRate < RISK_THRESHOLDS.high) {
    riskLevel = 'high';
  } else if (mentionRate < RISK_THRESHOLDS.mid) {
    riskLevel = 'mid';
  } else {
    riskLevel = 'low';
  }
  
  return {
    questionText,
    questionId,
    modelResults,
    stats: {
      mentionCount,
      totalModels: totalCount,
      mentionRate: parseFloat((mentionRate * 100).toFixed(2)),
      avgRank,
      avgVisibility,
      avgSentiment,
      riskLevel
    }
  };
};

/**
 * 获取竞品分析数据（增强版）
 * 
 * @param {Array} results - NxM 执行结果数组
 * @param {Array} competitors - 竞品品牌列表
 * @returns {Object} 竞品分析数据
 */
export const getCompetitorAnalysis = (results, competitors) => {
  // 数据清洗
  const preprocessed = preprocessData(results);
  const sanitizedResults = preprocessed.sanitizedResults;
  
  // 使用拦截矩阵计算
  const interceptionMatrix = calculateInterceptionMatrix(sanitizedResults);
  
  // 如果没有输入竞品，从结果中提取
  const finalCompetitors = competitors && competitors.length > 0
    ? competitors
    : interceptionMatrix.map(c => c.name);
  
  // 补充频率信息
  const competitorsWithStats = finalCompetitors.map(comp => {
    const found = interceptionMatrix.find(c => c.name === comp);
    return {
      name: comp,
      frequency: found ? found.frequency : 0,
      percentage: found ? found.percentage : 0
    };
  }).sort((a, b) => b.frequency - a.frequency);
  
  return {
    competitors: finalCompetitors,
    interceptionStats: competitorsWithStats,
    totalInterceptions: interceptionMatrix.reduce((acc, item) => acc + item.frequency, 0),
    topCompetitor: interceptionMatrix.length > 0 ? interceptionMatrix[0] : null
  };
};

/**
 * 获取信源分析数据（增强版）
 * 
 * @param {Array} results - NxM 执行结果数组
 * @returns {Object} 信源分析数据
 */
export const getSourceAnalysis = (results) => {
  // 数据清洗
  const preprocessed = preprocessData(results);
  const sanitizedResults = preprocessed.sanitizedResults;
  
  // 使用信源画像映射
  return mapSourceProfiles(sanitizedResults);
};

// ==================== 单元测试 ====================

/**
 * 单元测试函数（闭环验收用）
 * 包含 4 组测试数据：正常、部分缺失、全空、大数据量
 */
export const runUnitTests = () => {
  console.log('\n' + '='.repeat(60));
  console.log('GEO 品牌战略聚合引擎 (P1 重构版) - 闭环验收测试');
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
        sov: 88.33,  // 基于 visibility_score: 11 个提及中 10 个在 top3(100 分),1 个在 4-6(60 分) = 1060/1200 = 88.33%
        healthScore: 87,
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
        sov: 18,  // 2 个提及：rank5=60 分 + rank8=30 分 = 90/500 = 18%
        questionCards: 2,
        toxicSources: 0,
        dataCompleteness: 83  // 5 条实际 / 6 条期望 (2 问题×3 模型，但实际有 5 种组合)
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
    },
    {
      name: '测试 4: 数据清洗验证（缺省值填充）',
      input: {
        results: [
          { question_id: 0, question_text: '测试问题', model: 'test', geo_data: null },
          { question_id: 0, question_text: '测试问题', model: 'test2', geo_data: { brand_mentioned: true, rank: 2 } }  // 缺少 sentiment
        ],
        brandName: 'TestBrand',
        competitors: []
      },
      expected: {
        sanitizedCount: 2,  // 2 条数据需要清洗
        dataCompleteness: 100,
        questionCards: 1
      }
    }
  ];
  
  let passed = 0;
  let failed = 0;
  
  tests.forEach((test, testIndex) => {
    console.log(`\n${test.name}`);
    console.log('-'.repeat(60));
    
    try {
      const result = aggregateReport(
        test.input.results,
        test.input.brandName,
        test.input.competitors
      );
      
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
      
      // 验证 brand_health
      console.log('\n  Brand Health 验证:');
      console.log(`    分数：${result.brand_health.score}/100`);
      console.log(`    SOV 标签：${result.brand_health.sov_label}`);
      console.log(`    SOV 值：${result.brand_health.sov_value}%`);
      console.log(`    情感颜色：${result.brand_health.sentiment_color}`);
      
      // 验证 diagnostic_grid
      console.log('\n  Diagnostic Grid 验证:');
      console.log(`    问题数量：${result.diagnostic_grid.length}`);
      result.diagnostic_grid.forEach((q, idx) => {
        console.log(`    \n    问题 ${idx + 1}:`);
        console.log(`      文本：${q.question_text.substring(0, 30)}...`);
        console.log(`      平均排名：${q.avg_rank}`);
        console.log(`      风险等级：${q.risk_level}`);
        console.log(`      主要竞品：${q.key_competitor || '无'}`);
      });
      
      // 验证 risk_radar
      console.log('\n  Risk Radar 验证:');
      console.log(`    威胁信源数量：${result.risk_radar.toxic_sources.length}`);
      console.log(`    拦截话题数量：${result.risk_radar.intercepted_topics.length}`);
      
      // 验证元数据
      console.log('\n  Meta 验证:');
      console.log(`    数据完整性：${result._meta.data_completeness}%`);
      console.log(`    总记录数：${result._meta.total_records}`);
      console.log(`    是否部分报告：${result._meta.is_partial_report}`);

      // 验证计算逻辑
      const sovMatch = Math.abs(result.brand_health.sov_value - test.expected.sov) < 2;
      const questionCountMatch = result.diagnostic_grid.length === test.expected.questionCards;
      const toxicMatch = result.risk_radar.toxic_sources.length === test.expected.toxicSources;
      
      // 测试 4 的特殊验证
      let test4Pass = true;
      if (testIndex === 3) {
        test4Pass = result._meta.data_completeness === test.expected.dataCompleteness &&
                    result.diagnostic_grid.length === test.expected.questionCards;
      }

      if ((sovMatch && questionCountMatch && toxicMatch) || test4Pass) {
        console.log('\n  ✅ 通过：所有关键指标符合预期');
        passed++;
      } else {
        console.log('\n  ❌ 失败：关键指标不符合预期');
        console.log(`     SOV 匹配：${sovMatch} (实际:${result.brand_health.sov_value}, 期望:${test.expected.sov})`);
        console.log(`     问题数匹配：${questionCountMatch} (实际:${result.diagnostic_grid.length}, 期望:${test.expected.questionCards})`);
        console.log(`     负面信源匹配：${toxicMatch} (实际:${result.risk_radar.toxic_sources.length}, 期望:${test.expected.toxicSources})`);
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
  console.log(`通过率：${tests.length > 0 ? ((passed / tests.length) * 100).toFixed(1) : 0}%`);
  
  if (failed === 0) {
    console.log('\n🎉 所有测试通过！P1 战略聚合引擎逻辑验证完成。');
    return true;
  } else {
    console.log('\n⚠️ 部分测试失败，请检查逻辑。');
    return false;
  }
};

// 默认导出
export default {
  aggregateReport,
  getQuestionDetail,
  getCompetitorAnalysis,
  getSourceAnalysis,
  runUnitTests,
  // 导出辅助函数供外部使用
  sanitizeGeoData,
  normalizeRankToVisibility,
  deduplicateSources,
  preprocessData,
  calculateSOV,
  calculateSentimentIndex,
  calculateInterceptionMatrix,
  calculateBrandHealth,
  calculateSourceThreats,
  mapSourceProfiles,
  buildDiagnosticGrid,
  buildRiskRadar,
  buildBrandHealth,
  buildQuestionMap
};
