#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 响应解析调试脚本

用于诊断 AI 返回的响应格式问题
"""

import json
import re
from typing import Dict, Any

# 模拟 AI 响应（从日志中获取）
SAMPLE_AI_RESPONSE = """
作为专业的汽车改装行业顾问，为你整理了深圳几家口碑不错的新能源汽车改装门店...

{"geo_analysis":{"brand_mentioned":false,"rank":-1,"sentiment":0.0,"cited_sources":[],"interception":""}}
"""

def extract_json_objects(text: str) -> list:
    """使用平衡括号法提取 JSON 对象"""
    json_objects = []
    depth = 0
    start_idx = None
    
    for i, char in enumerate(text):
        if char == '{':
            if depth == 0:
                start_idx = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start_idx is not None:
                json_objects.append(text[start_idx:i+1])
                start_idx = None
    
    return json_objects


def parse_geo_debug(text: str) -> Dict[str, Any]:
    """调试版 GEO 解析器"""
    print("="*60)
    print("AI 原始响应:")
    print("="*60)
    print(text[:1000])
    print("\n")
    
    # 步骤 1: 清理 Markdown
    cleaned_text = text
    markdown_pattern = r'```(?:json)?\s*(.*?)```'
    markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
    if markdown_matches:
        print(f"✅ 找到 Markdown 代码块，数量：{len(markdown_matches)}")
        cleaned_text = markdown_matches[-1]
    else:
        print("ℹ️  未找到 Markdown 代码块")
    
    # 步骤 2: 查找 JSON 对象
    json_objects = extract_json_objects(cleaned_text)
    print(f"\n📊 找到 JSON 对象数量：{len(json_objects)}")
    
    for i, json_str in enumerate(json_objects):
        print(f"\n--- JSON 对象 {i+1} ---")
        print(f"长度：{len(json_str)} 字符")
        print(f"内容预览：{json_str[:200]}")
        
        try:
            data = json.loads(json_str)
            print(f"✅ 解析成功")
            print(f"键：{list(data.keys())}")
            
            if "geo_analysis" in data:
                print(f"\n✅ 找到 geo_analysis:")
                print(json.dumps(data["geo_analysis"], indent=2, ensure_ascii=False))
                return data["geo_analysis"]
        except json.JSONDecodeError as e:
            print(f"❌ 解析失败：{e}")
    
    # 步骤 3: 正则表达式查找
    geo_pattern = r'"geo_analysis"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'
    match = re.search(geo_pattern, cleaned_text, re.DOTALL)
    if match:
        print(f"\n✅ 正则表达式找到 geo_analysis")
        json_str = match.group(1)
        try:
            geo_data = json.loads(json_str)
            print(json.dumps(geo_data, indent=2, ensure_ascii=False))
            return geo_data
        except json.JSONDecodeError as e:
            print(f"❌ 解析失败：{e}")
    else:
        print(f"\n❌ 正则表达式未找到 geo_analysis")
    
    # 步骤 4: 查找所有 geo_analysis 相关字段
    print("\n🔍 搜索 geo_analysis 相关字段:")
    for pattern in [r'"brand_mentioned"\s*:\s*(true|false)',
                    r'"rank"\s*:\s*(-?\d+)',
                    r'"sentiment"\s*:\s*([\d.-]+)']:
        match = re.search(pattern, text)
        if match:
            print(f"  ✅ 找到：{match.group(0)}")
        else:
            print(f"  ❌ 未找到：{pattern}")
    
    return {
        "brand_mentioned": False,
        "rank": -1,
        "sentiment": 0.0,
        "cited_sources": [],
        "interception": "",
        "_error": "解析失败",
        "_debug": "请检查 AI 响应格式"
    }


if __name__ == "__main__":
    # 测试示例响应
    result = parse_geo_debug(SAMPLE_AI_RESPONSE)
    
    print("\n" + "="*60)
    print("最终结果:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 测试真实日志中的响应
    print("\n\n")
    print("="*60)
    print("测试真实日志响应:")
    print("="*60)
    
    # 从日志中读取实际响应
    try:
        with open('/Users/sgl/PycharmProjects/PythonProject/backend_python/logs/app.log', 'r', encoding='utf-8') as f:
            log_content = f.read()
            
            # 查找 AI 响应
            response_pattern = r'AI 响应：\n(.*?)(?=\n\d{4}-\d{2}-\d{2}|\n[A-Z]{3} \d{4}-\d{2}-\d{2}|$)'
            matches = re.findall(response_pattern, log_content, re.DOTALL)
            
            if matches:
                print(f"找到 {len(matches)} 个 AI 响应")
                for i, response in enumerate(matches[-3:], 1):  # 最后 3 个
                    print(f"\n--- 响应 {i} ---")
                    parse_geo_debug(response.strip())
            else:
                print("未在日志中找到 AI 响应")
    except Exception as e:
        print(f"读取日志失败：{e}")
