"""
Enhanced GEO JSON Parser with improved error handling and Markdown support
"""
import json
import re
from typing import Dict, Any, List
from ..logging_config import api_logger


def parse_geo_json_enhanced(text: str) -> Dict[str, Any]:
    """
    从 AI 返回的混合文本中提取 geo_analysis JSON（增强版）
    
    改进：
    1. 支持 Markdown 代码块格式
    2. 更好的嵌套 JSON 处理
    3. 详细的日志记录
    4. 多种回退策略
    
    Args:
        text: AI 返回的完整文本
        
    Returns:
        包含 geo_analysis 字段的字典，如果解析失败则返回默认值
    """
    default_data = {
        "brand_mentioned": False,
        "rank": -1,
        "sentiment": 0.0,
        "cited_sources": [],
        "interception": ""
    }
    
    if not text or not isinstance(text, str):
        api_logger.warning("parse_geo_json: Empty or invalid text input")
        return default_data
    
    try:
        # 步骤 1: 清理 Markdown 代码块标记
        cleaned_text = text
        markdown_pattern = r'```(?:json)?\s*(.*?)```'
        markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        if markdown_matches:
            # 如果找到 Markdown 代码块，使用最后一个（通常是 JSON 所在位置）
            cleaned_text = markdown_matches[-1]
            api_logger.info("Found JSON in Markdown code block")
        
        # 步骤 2: 尝试直接查找包含 geo_analysis 的 JSON 对象
        # 使用更强大的正则表达式，可以处理嵌套结构
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            # 尝试提取并解析
            potential_json = cleaned_text[json_start:json_end]
            
            # 尝试解析整个文本为 JSON
            try:
                data = json.loads(potential_json)
                if isinstance(data, dict) and "geo_analysis" in data:
                    result = data.get("geo_analysis", default_data)
                    api_logger.info(f"Successfully parsed geo_analysis: rank={result.get('rank', -1)}, sentiment={result.get('sentiment', 0)}")
                    return result
            except json.JSONDecodeError as e:
                api_logger.debug(f"Direct JSON parse failed: {e}")
        
        # 步骤 3: 使用正则表达式查找 geo_analysis 字段
        # 这个正则表达式可以处理嵌套的 JSON 结构
        geo_pattern = r'"geo_analysis"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'
        match = re.search(geo_pattern, cleaned_text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                geo_data = json.loads(json_str)
                api_logger.info(f"Extracted geo_analysis with regex: rank={geo_data.get('rank', -1)}")
                return geo_data
            except json.JSONDecodeError as e:
                api_logger.warning(f"Failed to parse extracted geo_analysis: {e}")
        
        # 步骤 4: 尝试查找文本中所有的 JSON 对象
        # 使用平衡括号法提取 JSON
        json_objects = extract_json_objects(cleaned_text)
        
        for json_str in json_objects:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    if "geo_analysis" in data:
                        result = data["geo_analysis"]
                        api_logger.info(f"Found geo_analysis in JSON object list")
                        return result
                    elif isinstance(data.get("geo_analysis"), dict):
                        api_logger.info(f"Found nested geo_analysis")
                        return data["geo_analysis"]
            except json.JSONDecodeError:
                continue
        
        # 如果所有方法都失败，记录警告并返回默认值
        api_logger.warning(
            f"parse_geo_json: Could not extract geo_analysis from text. "
            f"Text length: {len(text)}, First 200 chars: {text[:200]}..."
        )
        
    except Exception as e:
        api_logger.error(f"Unexpected error in parse_geo_json_enhanced: {e}", exc_info=True)
    
    return default_data


def extract_json_objects(text: str) -> List[str]:
    """
    从文本中提取所有完整的 JSON 对象（使用平衡括号法）
    
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


# 保持向后兼容的别名
parse_geo_json = parse_geo_json_enhanced
