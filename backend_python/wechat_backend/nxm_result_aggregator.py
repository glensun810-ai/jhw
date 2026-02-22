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
        geo_data, error = parse_geo_json_enhanced(response_text, execution_id, q_idx, model_name)

        if not geo_data:
            api_logger.warning(f"[GeoParser] 解析失败：{execution_id}, Q{q_idx}, {model_name}")
            return {
                'brand_mentioned': False,
                'rank': -1,
                'sentiment': 0.0,
                'cited_sources': [],
                'interception': '',
                '_error': error or '解析失败'
            }, error

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
            '_error': str(e)
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


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重结果"""
    seen_hashes = set()
    deduplicated = []

    for result in results:
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
            'negative_count': 0
        }

    mention_count = len(brand_results)
    ranks = [r.get('geo_data', {}).get('rank', -1) for r in brand_results]
    sentiments = [r.get('geo_data', {}).get('sentiment', 0.0) for r in brand_results]

    valid_ranks = [r for r in ranks if r > 0]
    avg_rank = sum(valid_ranks) / len(valid_ranks) if valid_ranks else -1

    positive_count = sum(1 for s in sentiments if s > 0.5)
    negative_count = sum(1 for s in sentiments if s < -0.5)

    return {
        'brand': brand_name,
        'mention_count': mention_count,
        'avg_rank': round(avg_rank, 2) if avg_rank > 0 else -1,
        'avg_sentiment': round(sum(sentiments) / len(sentiments), 2),
        'positive_count': positive_count,
        'negative_count': negative_count
    }
