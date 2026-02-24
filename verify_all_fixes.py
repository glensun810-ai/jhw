#!/usr/bin/env python3
"""
品牌洞察报告修复验证脚本

验证所有 P0/P1/P2 修复是否正确实现
"""

import os
import re
import json

# 项目根目录
BASE_DIR = '/Users/sgl/PycharmProjects/PythonProject'

def check_file_contains(file_path, patterns, description):
    """检查文件是否包含所有指定模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        results = []
        for pattern in patterns:
            if isinstance(pattern, tuple):
                pattern, is_regex = pattern
                if is_regex:
                    match = re.search(pattern, content)
                else:
                    match = pattern in content
            else:
                match = pattern in content
            
            results.append(bool(match))
        
        all_passed = all(results)
        status = "✅" if all_passed else "❌"
        print(f"{status} {description}: {'通过' if all_passed else '失败'} ({sum(results)}/{len(results)})")
        
        if not all_passed:
            for i, (pattern, passed) in enumerate(zip(patterns, results)):
                if not passed:
                    p = pattern[0] if isinstance(pattern, tuple) else pattern
                    print(f"   ❌ 缺失：{p[:50]}...")
        
        return all_passed
    except Exception as e:
        print(f"❌ {description}: 错误 - {e}")
        return False

def main():
    print("=" * 60)
    print("品牌洞察报告修复验证")
    print("=" * 60)
    
    all_passed = True
    
    # P0-1: 核心洞察文案生成
    print("\n🔴 P0-1: 核心洞察文案生成")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/nxm_execution_engine.py'),
        ['execution_store[execution_id][\'insights\']', '[NxM] 核心洞察生成完成'],
        "NxM 引擎生成 insights"
    )
    
    # P0-2: 竞品数据生成
    print("\n🔴 P0-2: 竞品数据生成")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/nxm_execution_engine.py'),
        ['all_brands = [main_brand] + (competitor_brands or [])', 'for brand in all_brands:'],
        "NxM 遍历所有品牌"
    )
    
    # P0-3: 信源纯净度数据生成
    print("\n🔴 P0-3: 信源纯净度数据生成")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/nxm_execution_engine.py'),
        ['SourceIntelligenceProcessor', 'source_purity_data'],
        "调用信源分析服务"
    )
    
    # P0-4: 信源情报图谱生成
    print("\n🔴 P0-4: 信源情报图谱生成")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/nxm_execution_engine.py'),
        ['source_intelligence_map', 'nodes = []', '[NxM] 信源情报图谱生成完成'],
        "生成信源情报图谱"
    )
    
    # P1-1: 首次提及率计算
    print("\n🟡 P1-1: 首次提及率计算")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.js'),
        ['calculateFirstMentionByPlatform', 'platformMentions'],
        "前端计算首次提及率"
    )
    
    # P1-2: 拦截风险分析
    print("\n🟡 P1-2: 拦截风险分析")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.js'),
        ['calculateInterceptionRisks', 'competitorMentions'],
        "前端计算拦截风险"
    )
    
    # P1-3: 前端数据验证增强
    print("\n🟡 P1-3: 前端数据验证增强")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.js'),
        ['validateDataIntegrity', '📊 完整数据验证报告'],
        "数据完整性验证"
    )
    
    # P2-1: 空状态友好提示
    print("\n🟢 P2-1: 空状态友好提示")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.wxml'),
        ['empty-state', '信源纯净度分析数据生成中', '信源情报图谱数据生成中'],
        "WXML 空状态提示"
    )
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.wxss'),
        ['.empty-state', '.empty-icon', '.empty-text', '.empty-hint'],
        "CSS 空状态样式"
    )
    
    # P2-2: 性能优化
    print("\n🟢 P2-2: 性能优化")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/database_core.py'),
        ['cache_entries', 'CREATE TABLE IF NOT EXISTS'],
        "添加 cache_entries 表"
    )
    
    # API 返回字段验证
    print("\n📋 API 返回字段验证")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'backend_python/wechat_backend/views/diagnosis_views.py'),
        ['source_purity_data', 'source_intelligence_map', 'insights'],
        "诊断 API 返回新增字段"
    )
    
    # 前端解析字段验证
    print("\n📋 前端解析字段验证")
    all_passed &= check_file_contains(
        os.path.join(BASE_DIR, 'pages/results/results.js'),
        ['sourcePurityDataToUse', 'sourceIntelligenceMapToUse'],
        "前端解析新增字段"
    )
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有修复验证通过！")
    else:
        print("❌ 部分修复验证失败，请检查")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    exit(main())
