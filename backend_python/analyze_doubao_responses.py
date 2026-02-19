#!/usr/bin/env python3
"""
分析豆包 API 响应是否遗漏
"""

import json
from collections import defaultdict
from pathlib import Path

def analyze_doubao_responses():
    log_file = Path(__file__).parent / 'data' / 'ai_responses' / 'ai_responses.jsonl'
    
    if not log_file.exists():
        print(f"❌ 日志文件不存在：{log_file}")
        return
    
    # 统计数据
    stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'empty_response': 0})
    doubao_empty_records = []
    doubao_success_records = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                
                # 提取平台信息
                platform = record.get('platform', 'Unknown')
                if isinstance(platform, dict):
                    platform = platform.get('name', 'Unknown')
                
                # 统计
                stats[platform]['total'] += 1
                
                success = record.get('status', {}).get('success', False)
                if success:
                    stats[platform]['success'] += 1
                else:
                    stats[platform]['failed'] += 1
                
                # 检查响应内容
                response = record.get('response', '')
                if isinstance(response, dict):
                    response_text = response.get('text', '')
                else:
                    response_text = response
                
                # 豆包记录分析
                if platform in ['豆包', 'doubao']:
                    if success:
                        if not response_text or len(response_text.strip()) == 0:
                            stats[platform]['empty_response'] += 1
                            doubao_empty_records.append({
                                'line': line_num,
                                'question': record.get('question', ''),
                                'response': response_text,
                                'metadata': record.get('metadata', {})
                            })
                        else:
                            doubao_success_records.append({
                                'line': line_num,
                                'question': record.get('question', ''),
                                'response_length': len(response_text),
                                'metadata': record.get('metadata', {})
                            })
                
            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON decode error - {e}")
            except Exception as e:
                print(f"Line {line_num}: Error - {e}")
    
    # 输出统计
    print("=" * 80)
    print("豆包 API 响应分析报告")
    print("=" * 80)
    
    print(f"\n📊 文件：{log_file}")
    print(f"\n所有平台统计:")
    for platform, data in sorted(stats.items()):
        print(f"\n【{platform}】")
        print(f"  总记录：{data['total']}")
        print(f"  成功：{data['success']} (成功率：{data['success']/data['total']*100:.1f}%)")
        print(f"  失败：{data['failed']}")
        print(f"  成功但空响应：{data['empty_response']}")
    
    # 重点分析豆包
    print("\n" + "=" * 80)
    print("豆包详细分析")
    print("=" * 80)
    
    doubao_total = stats.get('豆包', {}).get('total', 0)
    doubao_success = stats.get('豆包', {}).get('success', 0)
    doubao_empty = stats.get('豆包', {}).get('empty_response', 0)
    
    if doubao_total > 0:
        print(f"\n豆包总记录：{doubao_total}")
        print(f"成功：{doubao_success}")
        print(f"成功且有响应：{doubao_success - doubao_empty}")
        print(f"成功但空响应：{doubao_empty}")
        
        if doubao_empty > 0:
            print(f"\n⚠️  发现 {doubao_empty} 条成功但响应为空的记录!")
            print(f"\n空响应率：{doubao_empty/doubao_success*100:.1f}%")
            
            print("\n空响应记录详情:")
            for i, r in enumerate(doubao_empty_records[:10], 1):
                question = r['question']
                if isinstance(question, dict):
                    question = question.get('text', str(question))
                q_short = question[:60] + "..." if len(question) > 60 else question
                print(f"\n  {i}. Line {r['line']}: {q_short}")
                print(f"     Metadata: {r['metadata']}")
        else:
            print("\n✅ 所有成功的豆包记录都有响应内容!")
        
        # 显示成功记录示例
        print(f"\n成功记录示例 (共 {len(doubao_success_records)} 条):")
        for i, r in enumerate(doubao_success_records[:3], 1):
            question = r['question']
            if isinstance(question, dict):
                question = question.get('text', str(question))
            q_short = question[:40] + "..." if len(question) > 40 else question
            print(f"  {i}. Line {r['line']}: {q_short} (响应长度：{r['response_length']})")
    
    else:
        print("\n⚠️  未找到豆包记录!")
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)

if __name__ == '__main__':
    analyze_doubao_responses()
