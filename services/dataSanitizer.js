/**
 * 数据清洗服务
 * 负责 GEO 数据的清洗、标准化、缺省值填充
 */

// 缺省 GEO 对象
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
  '-1': 0
};

/**
 * 标准化 GEO 数据
 * @param {Object} geoData - 原始 geo_data
 * @returns {Object} 标准化后的 geo_data
 */
const sanitizeGeoData = (geoData) => {
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

  // 标记缺失字段
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
 * 排名归一化为可见度得分
 * @param {number} rank - 排名
 * @returns {number} 可见度得分
 */
const normalizeRankToVisibility = (rank) => {
  if (rank <= 0) return RANK_TO_VISIBILITY['-1'];
  if (rank <= 3) return RANK_TO_VISIBILITY['1-3'];
  if (rank <= 6) return RANK_TO_VISIBILITY['4-6'];
  return RANK_TO_VISIBILITY['7-10'];
};

/**
 * 清洗结果数组
 * @param {Array} results - 原始结果数组
 * @returns {Array} 清洗后的结果
 */
const sanitizeResults = (results) => {
  if (!Array.isArray(results)) return [];

  return results.map(result => {
    const sanitized = { ...result };

    // 清洗 geo_data
    if (result.geo_data) {
      sanitized.geo_data = sanitizeGeoData(result.geo_data);
    }

    // 清洗 response
    if (typeof result.response !== 'string') {
      sanitized.response = '';
    }

    // 添加清洗标记
    sanitized._sanitized = true;

    return sanitized;
  });
};

/**
 * 填充缺失数据
 * @param {Array} results - 结果数组
 * @param {string} mainBrand - 主品牌
 * @returns {Array} 填充后的结果
 */
const fillMissingData = (results, mainBrand) => {
  return results.map(result => {
    const filled = { ...result };

    // 确保 brand 字段存在
    if (!filled.brand) {
      filled.brand = mainBrand;
    }

    // 确保 score 字段存在
    if (filled.score === undefined || filled.score === null) {
      filled.score = 50; // 默认中等分数
    }

    return filled;
  });
};

module.exports = {
  sanitizeGeoData,
  normalizeRankToVisibility,
  sanitizeResults,
  fillMissingData,
  DEFAULT_GEO_DATA,
  RANK_TO_VISIBILITY
};
