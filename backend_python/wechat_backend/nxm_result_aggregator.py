"""
NxM 执行引擎 - 结果聚合模块

功能：
- GEO 数据解析与验证
- 结果聚合与去重
- 数据完整性校验
"""

import hashlib
import json
from typing import List, Dict, Any, Tuple, Optional
from wechat_backend.ai_adapters.base_adapter import parse_geo_json
from wechat_backend.ai_adapters.geo_parser import parse_geo_json_enhanced
from wechat_backend.logging_config import api_logger


def generate_result_hash(result_item: Dict[str, Any]) -> str:
    """生成结果哈希用于去重"""
    content = json.dumps(result_item, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def normalize_brand_mentioned(value: Any) -> bool:
    """标准化 brand_mentioned 字段"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '1']
    if isinstance(value, (int, float)):
        return value > 0
    return False


def extract_interception_fallback(text: str) -> str:
    """从文本中提取拦截信息"""
    if not text:
        return ''

    keywords = ['拦截', 'intercept', '屏蔽', 'block', '隐藏', 'hide']
    text_lower = text.lower()

    for keyword in keywords:
        if keyword in text_lower:
            return f'检测到{keyword}'

    return ''


def parse_geo_with_validation(
    response_text: str,
    execution_id: str,
    q_idx: int,
    model_name: str
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    解析 GEO 数据并验证

    返回：
    - geo_data: 解析后的 GEO 数据
    - error: 错误信息（如果有）
    """
    try:
        # 【P0 修复】处理 AIResponse 对象
        from wechat_backend.ai_adapters.base_adapter import AIResponse
        if isinstance(response_text, AIResponse):
            # 从 AIResponse 对象中提取实际响应文本
            if response_text.success and response_text.content:
                response_text = response_text.content
            else:
                return {
                    'brand_mentioned': False,
                    'rank': -1,
                    'sentiment': 0.0,
                    'cited_sources': [],
                    'interception': '',
                    '_error': f'AI 调用失败：{response_text.error_message}'
                }, response_text.error_message or 'AI 调用失败'
        
        # 修复 1: 传递 execution_id, q_idx, model_name 参数
        geo_data = parse_geo_json_enhanced(response_text, execution_id, q_idx, model_name)

        # 修复 1: 检查是否有错误标记
        if geo_data.get('_error'):
            api_logger.warning(f"[GeoParser] 解析失败（有错误标记）：{execution_id}, Q{q_idx}, {model_name}: {geo_data['_error']}")
            return geo_data, geo_data.get('_error')

        if not geo_data:
            api_logger.warning(f"[GeoParser] 解析失败：{execution_id}, Q{q_idx}, {model_name}")
            return {
                'brand_mentioned': False,
                'rank': -1,
                'sentiment': 0.0,
                'cited_sources': [],
                'interception': '',
                '_error': '解析失败',
                '_raw_response': response_text[:1000]
            }, '解析失败'

        # 验证必填字段
        if 'brand_mentioned' not in geo_data:
            geo_data['brand_mentioned'] = False
        else:
            geo_data['brand_mentioned'] = normalize_brand_mentioned(geo_data['brand_mentioned'])

        if 'rank' not in geo_data:
            geo_data['rank'] = -1

        if 'sentiment' not in geo_data:
            geo_data['sentiment'] = 0.0

        if 'cited_sources' not in geo_data:
            geo_data['cited_sources'] = []

        if 'interception' not in geo_data:
            geo_data['interception'] = extract_interception_fallback(response_text)

        return geo_data, None

    except Exception as e:
        api_logger.error(f"[GeoParser] 解析异常：{execution_id}, Q{q_idx}, {model_name}: {e}")
        return {
            'brand_mentioned': False,
            'rank': -1,
            'sentiment': 0.0,
            'cited_sources': [],
            'interception': '',
            '_error': str(e),
            '_raw_response': response_text[:1000]
        }, str(e)


def verify_completion(
    results: List[Dict[str, Any]],
    expected_total: int
) -> Dict[str, Any]:
    """
    验证执行是否完成
    
    返回：
    - success: 是否成功
    - message: 消息
    - missing_count: 缺失数量
    """
    actual_count = len(results)

    if actual_count == expected_total:
        return {
            'success': True,
            'message': f'执行完成：{actual_count}/{expected_total}',
            'missing_count': 0
        }

    missing_count = expected_total - actual_count
    api_logger.warning(f"[Verify] 结果不完整：{actual_count}/{expected_total}, 缺失：{missing_count}")

    return {
        'success': False,
        'message': f'结果不完整：{actual_count}/{expected_total}',
        'missing_count': missing_count
    }


def calculate_result_quality(geo_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    修复 4: 计算结果质量评分

    评分标准：
    - brand_mentioned: 10 分
    - rank > 0: 20 分
    - sentiment != 0: 20 分
    - cited_sources > 0: 30 分 (每个信源 10 分，最多 30 分)
    - interception 非空：20 分

    返回：
    - quality_score: 0-100 分
    - quality_level: 'high', 'medium', 'low', 'failed'
    - quality_details: 详细评分信息
    
    P0 修复：添加空值保护，防止 geo_data 为 None 时崩溃
    """
    # 【P0 关键修复】空值保护
    if geo_data is None:
        return {
            'quality_score': 0,
            'quality_level': 'failed',
            'quality_details': {
                'error': 'geo_data is None',
                'brand_mentioned': False,
                'rank': '无效',
                'sentiment': '无效',
                'sources': 0,
                'interception': False
            }
        }
    
    score = 0
    details = {}

    # brand_mentioned: 10 分
    if geo_data.get('brand_mentioned'):
        score += 10
        details['brand_mentioned'] = True
    else:
        details['brand_mentioned'] = False

    # rank > 0: 20 分
    rank = geo_data.get('rank', -1)
    if rank > 0:
        score += 20
        details['rank'] = rank
    else:
        details['rank'] = '无效'

    # sentiment != 0: 20 分
    sentiment = geo_data.get('sentiment', 0.0)
    if sentiment != 0.0:
        score += 20
        details['sentiment'] = sentiment
    else:
        details['sentiment'] = '中性/默认'

    # cited_sources > 0: 30 分 (每个信源 10 分，最多 30 分)
    sources = geo_data.get('cited_sources', [])
    if sources and len(sources) > 0:
        source_score = min(len(sources) * 10, 30)
        score += source_score
        details['sources'] = len(sources)
    else:
        details['sources'] = 0

    # interception 非空：20 分
    interception = geo_data.get('interception', '')
    if interception and len(interception.strip()) > 0:
        score += 20
        details['interception'] = True
    else:
        details['interception'] = False

    # 确定质量等级
    # 【修复】使用 'very_low' 而不是 'failed'，避免与任务状态混淆
    if score >= 80:
        quality_level = 'high'
    elif score >= 60:
        quality_level = 'medium'
    elif score >= 30:
        quality_level = 'low'
    else:
        quality_level = 'very_low'  # 【修复】质量低不等于任务失败

    return {
        'quality_score': score,
        'quality_level': quality_level,
        'quality_details': details
    }


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重结果"""
    seen_hashes = set()
    deduplicated = []

    for result in results:
        # 修复 4: 添加质量评分
        if 'geo_data' in result:
            quality_info = calculate_result_quality(result['geo_data'])
            result['quality_score'] = quality_info['quality_score']
            result['quality_level'] = quality_info['quality_level']
            result['quality_details'] = quality_info['quality_details']

        result_hash = generate_result_hash(result)
        if result_hash not in seen_hashes:
            seen_hashes.add(result_hash)
            deduplicated.append(result)

    if len(deduplicated) < len(results):
        api_logger.info(f"[Dedup] 去重：{len(results)} → {len(deduplicated)}")

    return deduplicated


def aggregate_results_by_brand(
    results: List[Dict[str, Any]],
    brand_name: str
) -> Dict[str, Any]:
    """按品牌聚合结果"""
    brand_results = [r for r in results if r.get('brand') == brand_name]

    if not brand_results:
        return {
            'brand': brand_name,
            'mention_count': 0,
            'avg_rank': -1,
            'avg_sentiment': 0.0,
            'positive_count': 0,
            'negative_count': 0,
            'errors': []  # P1-2 新增：错误信息列表
        }

    mention_count = len(brand_results)
    ranks = [r.get('geo_data', {}).get('rank', -1) for r in brand_results]
    sentiments = [r.get('geo_data', {}).get('sentiment', 0.0) for r in brand_results]

    valid_ranks = [r for r in ranks if r > 0]
    avg_rank = sum(valid_ranks) / len(valid_ranks) if valid_ranks else -1

    positive_count = sum(1 for s in sentiments if s > 0.5)
    negative_count = sum(1 for s in sentiments if s < -0.5)

    # P1-2 修复：收集所有错误信息
    errors = []
    for r in brand_results:
        if r.get('error'):
            errors.append({
                'question': r.get('question', 'unknown'),
                'model': r.get('model', 'unknown'),
                'error': r.get('error'),
                'error_type': r.get('error_type', 'unknown')
            })

    return {
        'brand': brand_name,
        'mention_count': mention_count,
        'avg_rank': round(avg_rank, 2) if avg_rank > 0 else -1,
        'avg_sentiment': round(sum(sentiments) / len(sentiments), 2),
        'positive_count': positive_count,
        'negative_count': negative_count,
        'errors': errors  # P1-2 新增：错误信息列表
    }
