#!/usr/bin/env python3
"""
深度分析豆包 API 失败原因
"""

import json
from collections import defaultdict, Counter
from pathlib import Path

def analyze_doubao_failures():
    log_file = Path(__file__).parent / 'data' / 'ai_responses' / 'ai_responses.jsonl'
    
    if not log_file.exists():
        print(f"❌ 日志文件不存在：{log_file}")
        return
    
    # 失败原因统计
    failure_reasons = Counter()
    doubao_failures = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                
                # 提取平台信息
                platform = record.get('platform', 'Unknown')
                if isinstance(platform, dict):
                    platform = platform.get('name', 'Unknown')
                
                # 只分析豆包失败记录
                if platform in ['豆包', 'doubao']:
                    success = record.get('status', {}).get('success', False)
                    
                    if not success:
                        error_msg = record.get('status', {}).get('error_message', 'Unknown error')
                        failure_reasons[error_msg[:50]] += 1
                        
                        doubao_failures.append({
                            'line': line_num,
                            'question': record.get('question', ''),
                            'error': error_msg,
                            'metadata': record.get('metadata', {}),
                            'source': record.get('metadata', {}).get('source', 'unknown')
                        })
                
            except Exception as e:
                print(f"Line {line_num}: Error - {e}")
    
    # 输出分析
    print("=" * 80)
    print("豆包 API 失败原因分析")
    print("=" * 80)
    
    print(f"\n📊 文件：{log_file}")
    print(f"\n豆包失败记录总数：{len(doubao_failures)}")
    
    print("\n失败原因分布:")
    for reason, count in failure_reasons.most_common(10):
        pct = count / len(doubao_failures) * 100 if doubao_failures else 0
        print(f"  {count:3d} ({pct:5.1f}%) - {reason}")
    
    # 按来源分析
    print("\n按执行来源分析:")
    by_source = Counter(f['source'] for f in doubao_failures)
    for source, count in by_source.most_common():
        pct = count / len(doubao_failures) * 100 if doubao_failures else 0
        print(f"  {source}: {count} ({pct:.1f}%)")
    
    # 显示失败记录示例
    print("\n失败记录示例 (前 10 条):")
    for i, f in enumerate(doubao_failures[:10], 1):
        question = f['question']
        if isinstance(question, dict):
            question = question.get('text', str(question))
        q_short = question[:50] + "..." if len(question) > 50 else question
        print(f"\n  {i}. Line {f['line']}")
        print(f"     问题：{q_short}")
        print(f"     错误：{f['error']}")
        print(f"     来源：{f['source']}")
        print(f"     Metadata: {f['metadata']}")
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)

if __name__ == '__main__':
    analyze_doubao_failures()
