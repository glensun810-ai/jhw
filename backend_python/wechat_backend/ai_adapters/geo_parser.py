"""
Enhanced GEO JSON Parser with Maximum Fault Tolerance

P0-2 修复：AI 响应解析容错性增强

修复内容:
1. 支持多种 JSON 格式（Markdown 代码块、内联 JSON、纯文本）
2. 添加智能 JSON 提取算法（平衡括号法、正则匹配、递归提取）
3. 添加 AI 响应格式自动识别
4. 添加语义分析降级方案（当 JSON 解析失败时）
5. 保留原始响应便于调试
6. 添加详细的错误分类和日志
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from wechat_backend.logging_config import api_logger


# ============== 默认值定义 ==============
DEFAULT_GEO_DATA = {
    "brand_mentioned": False,
    "rank": -1,
    "sentiment": 0.0,
    "cited_sources": [],
    "interception": ""
}

# 情感关键词映射（用于语义分析降级）
SENTIMENT_KEYWORDS = {
    'positive': ['推荐', '优秀', '出色', '好', '专业', '可靠', '领先', '首选', '最佳', '满意', '赞赏'],
    'negative': ['不推荐', '避免', '差', '糟糕', '问题', '投诉', '失望', '谨慎', '风险'],
    'neutral': ['一般', '普通', '中等', '尚可', '还行']
}

# 排名关键词（用于语义分析降级）
RANK_KEYWORDS = ['第一', '首选', 'TOP1', '第 1', '第二', 'TOP2', '第 2', '第三', 'TOP3', '第 3',
                 '第四', '第 4', '第五', '第 5', '前十', '前列']


def parse_geo_json_enhanced(
    text: str,
    execution_id: str = None,
    q_idx: int = None,
    model_name: str = None
) -> Dict[str, Any]:
    """
    从 AI 返回的混合文本中提取 geo_analysis JSON（最大容错版本）
    
    P0-2 修复：增强容错性，支持多种格式和降级方案

    解析策略（按优先级）:
    1. Markdown JSON 代码块
    2. 内联 JSON 对象
    3. 正则提取 geo_analysis 字段
    4. 平衡括号法提取 JSON
    5. 语义分析降级（从纯文本中提取信息）
    6. 返回默认值并标记错误

    Args:
        text: AI 返回的完整文本
        execution_id: 执行 ID（可选，用于日志）
        q_idx: 问题索引（可选，用于日志）
        model_name: 模型名称（可选，用于日志）

    Returns:
        包含 geo_analysis 字段的字典，如果解析失败则返回带错误标记的默认值
    """
    log_context = f"exec={execution_id}, Q={q_idx}, model={model_name}" if execution_id else ""
    
    # 验证输入
    if not text or not isinstance(text, str):
        api_logger.warning(f"[GeoParser] 输入无效：{log_context}")
        return _create_error_result("AI 响应为空或格式无效", text)
    
    try:
        # ========== 策略 1: 清理并提取 Markdown 代码块 ==========
        api_logger.debug(f"[GeoParser] 策略 1: 尝试 Markdown 代码块提取")
        
        # 支持多种 Markdown 格式
        markdown_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json ... ```
            r'```JSON\s*(.*?)\s*```',  # ```JSON ... ```
            r'```\s*(.*?)\s*```',      # ``` ... ```
        ]
        
        for pattern in markdown_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                # 使用最后一个匹配（通常是 JSON 所在位置）
                json_text = matches[-1].strip()
                api_logger.info(f"[GeoParser] 找到 Markdown JSON 代码块")
                
                result = _try_parse_json(json_text, log_context)
                if result:
                    return result
        
        # ========== 策略 2: 直接查找 JSON 对象 ==========
        api_logger.debug(f"[GeoParser] 策略 2: 尝试直接查找 JSON 对象")
        
        # 查找第一个 { 和最后一个 }
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            potential_json = text[json_start:json_end]
            result = _try_parse_json(potential_json, log_context)
            if result:
                api_logger.info(f"[GeoParser] 直接 JSON 提取成功")
                return result
        
        # ========== 策略 3: 正则提取 geo_analysis 字段 ==========
        api_logger.debug(f"[GeoParser] 策略 3: 尝试正则提取 geo_analysis")
        
        # 支持嵌套 JSON 的正则
        geo_patterns = [
            r'"geo_analysis"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})',  # 一层嵌套
            r'"geo_analysis"\s*:\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})',  # 二层嵌套
        ]
        
        for pattern in geo_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_str = match.group(1)
                result = _try_parse_json(json_str, log_context)
                if result:
                    api_logger.info(f"[GeoParser] 正则提取 geo_analysis 成功")
                    return result
        
        # ========== 策略 4: 平衡括号法提取所有 JSON 对象 ==========
        api_logger.debug(f"[GeoParser] 策略 4: 尝试平衡括号法")
        
        json_objects = _extract_json_objects_balanced(text)
        
        for json_str in json_objects:
            result = _try_parse_json(json_str, log_context)
            if result:
                api_logger.info(f"[GeoParser] 平衡括号法提取成功")
                return result
        
        # ========== 策略 5: 语义分析降级（P0-2 新增） ==========
        api_logger.warning(f"[GeoParser] JSON 解析失败，启用语义分析降级：{log_context}")

        semantic_result = _semantic_analysis_fallback(text, log_context)
        if semantic_result:
            api_logger.info(f"[GeoParser] 语义分析降级成功")
            # 合并结果，保留语义分析中的 _raw_response 字段
            result = {
                **semantic_result,
                "_parse_method": "semantic_analysis",
                "_warning": "JSON 解析失败，使用语义分析结果"
            }
            # 确保 _raw_response 不被覆盖
            if '_raw_response' not in result and text:
                result['_raw_response'] = text[:1000]
            return result

        # ========== 策略 6: 所有方法都失败，返回默认值 ==========
        api_logger.error(f"[GeoParser] 所有解析方法均失败：{log_context}")
        return _create_error_result("无法从 AI 响应中提取 geo_analysis 字段", text)
    
    except Exception as e:
        api_logger.error(f"[GeoParser] 未预期的异常：{e}", exc_info=True)
        return _create_error_result(f"解析异常：{str(e)}", text)


def _try_parse_json(json_str: str, log_context: str) -> Optional[Dict[str, Any]]:
    """
    尝试解析 JSON 字符串并提取 geo_analysis
    
    Args:
        json_str: JSON 字符串
        log_context: 日志上下文
    
    Returns:
        解析成功的 geo_analysis 数据，失败返回 None
    """
    try:
        # 清理 JSON 字符串
        json_str = json_str.strip()
        
        # 尝试解析
        data = json.loads(json_str)
        
        if not isinstance(data, dict):
            return None
        
        # 检查是否包含 geo_analysis
        if "geo_analysis" in data:
            geo_data = data["geo_analysis"]
            if isinstance(geo_data, dict):
                api_logger.info(f"[GeoParser] 解析成功：rank={geo_data.get('rank', -1)}, sentiment={geo_data.get('sentiment', 0)}")
                return {**DEFAULT_GEO_DATA, **geo_data}
        
        # 检查 data 本身就是 geo_analysis
        if _is_geo_analysis_structure(data):
            api_logger.info(f"[GeoParser] 数据本身就是 geo_analysis 格式")
            return {**DEFAULT_GEO_DATA, **data}
        
        return None
    
    except json.JSONDecodeError as e:
        api_logger.debug(f"[GeoParser] JSON 解析失败：{e}")
        return None
    except Exception as e:
        api_logger.debug(f"[GeoParser] 解析异常：{e}")
        return None


def _is_geo_analysis_structure(data: Dict) -> bool:
    """
    检查字典是否是 geo_analysis 结构
    
    Args:
        data: 字典
    
    Returns:
        是否是 geo_analysis 结构
    """
    required_fields = ['brand_mentioned', 'rank', 'sentiment']
    return all(field in data for field in required_fields)


def _extract_json_objects_balanced(text: str) -> List[str]:
    """
    从文本中提取所有完整的 JSON 对象（平衡括号法）
    
    Args:
        text: 输入文本
    
    Returns:
        JSON 字符串列表
    """
    json_objects = []
    stack = []
    start_idx = -1
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                if not stack:
                    start_idx = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack and start_idx != -1:
                        json_objects.append(text[start_idx:i+1])
                        start_idx = -1
    
    return json_objects


def _semantic_analysis_fallback(text: str, log_context: str) -> Optional[Dict[str, Any]]:
    """
    语义分析降级方案（P0-2 新增）

    当 JSON 解析失败时，从纯文本中提取品牌提及、排名、情感等信息

    Args:
        text: AI 响应文本
        log_context: 日志上下文

    Returns:
        提取的 geo 数据，失败返回 None
    """
    try:
        text_lower = text.lower()

        # 1. 品牌提及分析
        brand_mentioned = False
        rank = -1
        sentiment = 0.0

        # 检测品牌提及（通过常见品牌关键词）
        brand_keywords = ['品牌', '门店', '推荐', '选择', '产品']
        for keyword in brand_keywords:
            if keyword in text_lower:
                brand_mentioned = True
                break

        # 2. 排名提取（增强版）
        rank_patterns = [
            # 明确排名：第一名、第 1 名等
            (r'第 ([一二三四五六七八九十\d]+) 名', 1),
            # TOP 排名：TOP1、TOP2 等
            (r'TOP(\d+)', 1),
            # 排名关键词：排名第 1、第 2 等
            (r'排名 [第]?(\d+)', 1),
            # 第一/首选（无捕获组改为捕获组）
            (r'(第一 | 首选)', 0),
            # 第二
            (r'(第二)', 0),
            # 第三
            (r'(第三)', 0),
            # 推荐顺序：第一推荐、第二推荐等
            (r'第 ([一二三四五六七八九十\d]+) 推荐', 1),
            # 最推荐、强烈推荐等（暗示排名靠前）
            (r'(?:最 | 强烈 | 优先 | 重点) 推荐', 0),
        ]

        chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                       '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}

        for pattern, group_idx in rank_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if group_idx > 0:
                    rank_str = match.group(group_idx)
                    if rank_str in chinese_nums:
                        rank = chinese_nums[rank_str]
                        break
                    else:
                        try:
                            rank = int(rank_str)
                            break
                        except:
                            continue
                else:
                    # 无捕获组，根据匹配内容判断排名
                    matched_text = match.group(0).lower()
                    if '第一' in matched_text or '首选' in matched_text or '最推荐' in matched_text:
                        rank = 1
                        break
                    elif '第二' in matched_text:
                        rank = 2
                        break
                    elif '第三' in matched_text:
                        rank = 3
                        break

        # 如果仍未提取到排名，但有推荐关键词，给一个默认排名
        if rank == -1 and brand_mentioned:
            # 检查是否有 TOP3 相关表述
            if any(kw in text_lower for kw in ['top3', 'top 3', '前三', '前列', '推荐']):
                rank = 3  # 默认给一个中间排名

        # 3. 情感分析
        positive_count = sum(1 for kw in SENTIMENT_KEYWORDS['positive'] if kw in text_lower)
        negative_count = sum(1 for kw in SENTIMENT_KEYWORDS['negative'] if kw in text_lower)

        if positive_count > negative_count:
            sentiment = min(0.5 + (positive_count - negative_count) * 0.1, 1.0)
        elif negative_count > positive_count:
            sentiment = max(-0.5 - (negative_count - positive_count) * 0.1, -1.0)
        else:
            sentiment = 0.0

        # 4. 信源提取（简单 URL 提取）
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        cited_sources = [{'url': url, 'site_name': _extract_site_name(url), 'attitude': 'neutral'} for url in urls[:5]]

        # 5. 拦截信息提取
        interception = ''
        if any(kw in text_lower for kw in ['拦截', '屏蔽', 'block', 'intercept']):
            interception = '检测到内容拦截'

        api_logger.info(
            f"[GeoParser] 语义分析成功：mentioned={brand_mentioned}, rank={rank}, sentiment={sentiment:.2f}"
        )

        return {
            'brand_mentioned': brand_mentioned,
            'rank': rank,
            'sentiment': sentiment,
            'cited_sources': cited_sources,
            'interception': interception,
            '_raw_response': text[:1000] if text else None,  # 保留原始响应便于调试
            '_parse_method': 'semantic_analysis'
        }

    except Exception as e:
        api_logger.warning(f"[GeoParser] 语义分析失败：{e}")
        return None


def _extract_site_name(url: str) -> str:
    """从 URL 中提取网站名称"""
    try:
        # 简单提取域名
        if 'zhihu' in url:
            return '知乎'
        elif 'xiaohongshu' in url:
            return '小红书'
        elif 'zol' in url:
            return '中关村在线'
        elif 'pconline' in url:
            return '太平洋电脑网'
        elif 'smzdm' in url:
            return '什么值得买'
        else:
            # 通用提取
            match = re.search(r'://(?:www\.)?([^/]+)', url)
            if match:
                return match.group(1).split('.')[0]
    except:
        pass
    return '未知信源'


def _create_error_result(error_message: str, raw_text: str = None) -> Dict[str, Any]:
    """
    创建错误结果
    
    Args:
        error_message: 错误信息
        raw_text: 原始响应文本
    
    Returns:
        带错误标记的默认数据
    """
    return {
        **DEFAULT_GEO_DATA,
        "_error": error_message,
        "_raw_response": raw_text[:1000] if raw_text else None,
        "_parse_method": "failed"
    }


# 保持向后兼容的别名
parse_geo_json = parse_geo_json_enhanced
