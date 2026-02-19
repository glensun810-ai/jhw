#!/usr/bin/env python3
"""
AI 响应日志分析工具
分析 N 个问题*M 个平台的对应关系
"""

import json
from collections import defaultdict
from pathlib import Path

def analyze_logs():
    log_file = Path(__file__).parent / 'data' / 'ai_responses' / 'ai_responses.jsonl'
    
    if not log_file.exists():
        print(f"❌ 日志文件不存在：{log_file}")
        return
    
    # 统计数据
    stats = defaultdict(lambda: defaultdict(list))
    execution_questions = defaultdict(set)
    platform_question_pairs = defaultdict(set)
    all_records = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                all_records.append(record)
                
                # 提取关键信息
                platform = record.get('platform', 'Unknown')
                if isinstance(platform, dict):
                    platform = platform.get('name', 'Unknown')
                
                question = record.get('question', 'Unknown')
                if isinstance(question, dict):
                    question = question.get('text', 'Unknown')
                
                brand = record.get('business', {}).get('brand', 'Unknown')
                execution_id = record.get('metadata', {}).get('execution_id', 
                                 record.get('context', {}).get('task_id', 'Unknown'))
                question_index = record.get('metadata', {}).get('question_index', 
                                   record.get('metadata', {}).get('attempt', 'N/A'))
                success = record.get('status', {}).get('success', False)
                
                # 统计
                stats[platform][question].append({
                    'brand': brand,
                    'success': success,
                    'line': line_num,
                    'execution_id': execution_id,
                    'question_index': question_index
                })
                
                execution_questions[execution_id].add(question)
                platform_question_pairs[platform].add(question)
                
            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON decode error - {e}")
            except Exception as e:
                print(f"Line {line_num}: Error - {e}")
    
    # 输出统计结果
    print("=" * 80)
    print("AI 响应日志分析报告")
    print("=" * 80)
    
    print(f"\n📊 文件：{log_file}")
    print(f"📈 总记录数：{len(all_records)}")
    
    print("\n" + "=" * 80)
    print("1. 平台分布统计")
    print("=" * 80)
    for platform, questions in sorted(platform_question_pairs.items()):
        print(f"\n【{platform}】")
        print(f"  问题数量：{len(questions)}")
        total_records = sum(len(stats[platform][q]) for q in questions)
        total_success = sum(
            sum(1 for r in stats[platform][q] if r['success']) 
            for q in questions
        )
        print(f"  总记录数：{total_records} (成功：{total_success})")
        for q in sorted(questions):
            q_short = q[:50] + "..." if len(q) > 50 else q
            records = stats[platform][q]
            success_count = sum(1 for r in records if r['success'])
            print(f"    • {q_short} (成功：{success_count}/{len(records)})")
    
    print("\n" + "=" * 80)
    print("2. Execution ID 分析 (N 个问题)")
    print("=" * 80)
    for exec_id, questions in sorted(execution_questions.items()):
        if exec_id != 'Unknown':
            print(f"\n【Execution: {exec_id[:36]}...】")
            print(f"  问题数量：{len(questions)}")
            for q in sorted(questions):
                q_short = q[:50] + "..." if len(q) > 50 else q
                print(f"    • {q_short}")
    
    print("\n" + "=" * 80)
    print("3. 豆包 (Doubao) 日志详细分析")
    print("=" * 80)
    doubao_records = stats.get('豆包', stats.get('doubao', {}))
    if doubao_records:
        total = sum(len(v) for v in doubao_records.values())
        success_total = sum(
            sum(1 for r in records if r['success']) 
            for records in doubao_records.values()
        )
        print(f"\n✅ 豆包总记录数：{total} (成功：{success_total}, 失败：{total - success_total})")
        print(f"✅ 问题数量：{len(doubao_records)}")
        
        for question, records in doubao_records.items():
            q_short = question[:50] + "..." if len(question) > 50 else question
            print(f"\n  问题：{q_short}")
            print(f"  记录数：{len(records)}")
            success_count = sum(1 for r in records if r['success'])
            print(f"  成功：{success_count}, 失败：{len(records) - success_count}")
            for r in records[:5]:  # 显示前 5 条
                print(f"    - Line {r['line']}: Brand={r['brand']}, Success={r['success']}, Exec={r['execution_id'][:8] if r['execution_id'] != 'Unknown' else 'N/A'}...")
    else:
        print("\n⚠️  未找到豆包日志！")
    
    print("\n" + "=" * 80)
    print("4. N*M 对应关系验证")
    print("=" * 80)
    
    # 按 execution_id 分组
    exec_platform_map = defaultdict(lambda: defaultdict(set))
    for platform, questions in platform_question_pairs.items():
        for question in questions:
            for record in stats[platform][question]:
                exec_id = record['execution_id']
                if exec_id != 'Unknown':
                    exec_platform_map[exec_id][platform].add(question)
    
    for exec_id, platform_questions in exec_platform_map.items():
        print(f"\n【{exec_id[:36]}...】")
        print(f"  涉及平台数：{len(platform_questions)}")
        for platform, questions in platform_questions.items():
            print(f"    {platform}: {len(questions)} 个问题")
            for q in sorted(questions):
                q_short = q[:40] + "..." if len(q) > 40 else q
                print(f"      • {q_short}")
    
    print("\n" + "=" * 80)
    print("5. 问题 - 平台矩阵")
    print("=" * 80)
    
    # 获取所有唯一问题
    all_questions = set()
    for questions in platform_question_pairs.values():
        all_questions.update(questions)
    
    # 打印表头
    platforms = sorted(platform_question_pairs.keys())
    questions = sorted(all_questions)
    
    print("\n平台\\问题 |", end="")
    for i, q in enumerate(questions[:5]):  # 只显示前 5 个问题
        q_short = q[:15] + "..." if len(q) > 15 else q
        print(f" Q{i+1}:{q_short} |", end="")
    print()
    print("-" * 80)
    
    for platform in platforms:
        print(f"{platform[:12]:12} |", end="")
        for q in questions[:5]:
            records = stats[platform].get(q, [])
            success = sum(1 for r in records if r['success'])
            total = len(records)
            if total > 0:
                print(f" {success}/{total:2} ✓ |" if success > 0 else f" {success}/{total:2} ✗ |", end="")
            else:
                print(f" -/-   |", end="")
        print()
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)

if __name__ == '__main__':
    analyze_logs()
