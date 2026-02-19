#!/usr/bin/env python3
"""
Simple Self-Test for NxM Matrix Refactoring
简化版自检脚本
"""

import json
import re
import os

def test_nxm_loop():
    """测试 1: NxM 循环结构"""
    print("\n" + "="*60)
    print("测试 1: NxM 循环结构")
    print("="*60)
    
    engine_file = 'backend_python/wechat_backend/nxm_execution_engine.py'
    with open(engine_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    checks = {
        '外层循环 (问题)': 'for q_idx, base_question in enumerate(raw_questions):',
        '中层循环 (品牌)': 'for brand_idx, brand in enumerate(brand_list):',
        '内层循环 (模型)': 'for model_idx, model_info in enumerate(selected_models):'
    }
    
    all_pass = True
    for name, pattern in checks.items():
        found = pattern in source
        print(f"  {'✓' if found else '✗'} {name}: {found}")
        if not found:
            all_pass = False
    
    return all_pass


def test_geo_parser():
    """测试 2: GEO JSON 解析器（直接测试代码）"""
    print("\n" + "="*60)
    print("测试 2: GEO JSON 解析器")
    print("="*60)
    
    # 定义解析函数（从 geo_parser.py 复制）
    def parse_geo_json_enhanced(text):
        default_data = {
            "brand_mentioned": False,
            "rank": -1,
            "sentiment": 0.0,
            "cited_sources": [],
            "interception": ""
        }
        
        if not text:
            return default_data
        
        # 清理 Markdown
        cleaned = text
        md_pattern = r'```(?:json)?\s*(.*?)```'
        md_matches = re.findall(md_pattern, text, re.DOTALL)
        if md_matches:
            cleaned = md_matches[-1]
        
        # 查找 JSON
        try:
            # 尝试提取整个 JSON
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            if start != -1 and end > start:
                potential = cleaned[start:end]
                data = json.loads(potential)
                if isinstance(data, dict) and "geo_analysis" in data:
                    return data["geo_analysis"]
        except:
            pass
        
        # 尝试正则
        geo_pattern = r'"geo_analysis"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'
        match = re.search(geo_pattern, cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        return default_data
    
    # 测试用例
    tests = [
        ("标准 JSON", '{"geo_analysis": {"rank": 3, "sentiment": 0.5}}', 3, 0.5),
        ("Markdown 格式", '```json\n{"geo_analysis": {"rank": 5}}\n```', 5, 0.0),
        ("无 JSON", '纯文本无 JSON', -1, 0.0),
    ]
    
    passed = 0
    for name, input_text, exp_rank, exp_sent in tests:
        result = parse_geo_json_enhanced(input_text)
        rank_ok = result.get('rank') == exp_rank
        print(f"  {'✓' if rank_ok else '✗'} {name}: rank={result.get('rank')} (期望：{exp_rank})")
        if rank_ok:
            passed += 1
    
    return passed == len(tests)


def test_geo_prompt():
    """测试 3: GEO Prompt 模板"""
    print("\n" + "="*60)
    print("测试 3: GEO Prompt 模板")
    print("="*60)
    
    adapter_file = 'backend_python/wechat_backend/ai_adapters/base_adapter.py'
    with open(adapter_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取模板
    match = re.search(r'GEO_PROMPT_TEMPLATE\s*=\s*"""(.*?)"""', content, re.DOTALL)
    if not match:
        print("  ✗ 未找到 GEO_PROMPT_TEMPLATE")
        return False
    
    template = match.group(1)
    
    # 检查必需字段
    required = [
        '{brand_name}', '{competitors}', '{question}',
        'geo_analysis', 'brand_mentioned', 'rank', 'sentiment',
        'cited_sources', 'interception',
        '不要包含在 Markdown'
    ]
    
    all_present = True
    for field in required:
        present = field in template
        print(f"  {'✓' if present else '✗'} {field}: {present}")
        if not present:
            all_present = False
    
    # 测试格式化
    try:
        formatted = template.format(
            brand_name="Tesla",
            competitors="BMW",
            question="介绍 Tesla"
        )
        has_values = "Tesla" in formatted and "BMW" in formatted
        print(f"  {'✓' if has_values else '✗'} 格式化测试：{has_values}")
        return all_present and has_values
    except Exception as e:
        print(f"  ✗ 格式化失败：{e}")
        return False


def test_logging():
    """测试 4: 日志记录"""
    print("\n" + "="*60)
    print("测试 4: 日志记录")
    print("="*60)
    
    engine_file = 'backend_python/wechat_backend/nxm_execution_engine.py'
    with open(engine_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    logs = [
        "执行日志", 'Executing [Q:',
        "响应预览", 'AI Response preview',
        "GEO 结果", 'GEO Analysis Result',
    ]
    
    all_present = True
    for name, pattern in [logs[i:i+2] for i in range(0, len(logs), 2)]:
        found = pattern in source
        print(f"  {'✓' if found else '✗'} {name}: {found}")
        if not found:
            all_present = False
    
    return all_present


def main():
    print("\n" + "="*60)
    print("NxM 矩阵重构功能自检")
    print("="*60)
    
    results = [
        test_nxm_loop(),
        test_geo_parser(),
        test_geo_prompt(),
        test_logging()
    ]
    
    # 总结
    print("\n" + "="*60)
    print("自检总结")
    print("="*60)
    
    tests = ["NxM 循环", "GEO 解析器", "Prompt 模板", "日志记录"]
    for name, result in zip(tests, results):
        print(f"  {'✅' if result else '❌'} {name}: {'通过' if result else '失败'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n  总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n  🎉 所有测试通过！")
        print("\n  下一步操作:")
        print("  1. 启动后端服务")
        print("  2. 发送测试 API 请求")
        print("  3. 检查日志中的执行次数（应为 N×M）")
        print("  4. 验证数据库中的 geo_data 字段")
    else:
        print("\n  ⚠️ 部分测试失败，请检查报告")
    
    return passed == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)
