#!/usr/bin/env python3
"""
查看AI响应记录的工具脚本 V2 - 支持增强版格式
用于查看和分析保存的AI训练数据
"""

import json
import sys
from pathlib import Path
from utils.ai_response_logger_v2 import get_logger


def view_responses(limit=10, platform=None, brand=None, success_only=False):
    """查看最近的AI响应记录（V2格式）"""
    logger = get_logger()
    responses = logger.get_recent_responses(
        limit=limit, 
        platform=platform, 
        brand=brand,
        success_only=success_only
    )
    
    print("=" * 100)
    print(f"最近的 {len(responses)} 条AI响应记录（V2增强版）")
    print("=" * 100)
    
    for idx, record in enumerate(responses, 1):
        print(f"\n【记录 {idx}】")
        print(f"  记录ID: {record.get('record_id', 'N/A')}")
        print(f"  时间: {record.get('timestamp', 'N/A')}")
        
        # 业务信息
        business = record.get('business', {})
        print(f"  品牌: {business.get('brand', 'N/A')}")
        if business.get('competitor'):
            print(f"  竞品: {business.get('competitor')}")
        if business.get('industry'):
            print(f"  行业: {business.get('industry')}")
        if business.get('question_category'):
            print(f"  问题分类: {business.get('question_category')}")
        
        # 平台信息
        platform_info = record.get('platform', {})
        print(f"  平台: {platform_info.get('name', 'N/A')}")
        print(f"  模型: {platform_info.get('model', 'N/A')}")
        
        # 状态
        status = record.get('status', {})
        print(f"  状态: {'✅ 成功' if status.get('success') else '❌ 失败'}")
        if status.get('error_message'):
            print(f"  错误: {status.get('error_message')[:100]}")
        
        # 性能指标
        perf = record.get('performance', {})
        if perf.get('latency_ms'):
            print(f"  延迟: {perf.get('latency_ms')} ms")
        tokens = perf.get('tokens', {})
        if tokens.get('total'):
            print(f"  Token: {tokens.get('total')} (提示: {tokens.get('prompt', 'N/A')}, 生成: {tokens.get('completion', 'N/A')})")
        if perf.get('throughput'):
            print(f"  吞吐量: {perf.get('throughput')} tokens/s")
        
        # 文本统计
        question_stats = record.get('question', {}).get('stats', {})
        response_stats = record.get('response', {}).get('stats', {})
        print(f"  问题长度: {question_stats.get('length', 0)} 字符")
        print(f"  答案长度: {response_stats.get('length', 0)} 字符 ({response_stats.get('chinese_chars', 0)} 中文)")
        
        # 质量评估
        quality = record.get('quality', {})
        if quality.get('score') is not None:
            print(f"  完整性评分: {quality.get('score')}/1.0")
        if quality.get('has_structured_data'):
            print(f"  结构化数据: ✅")
        
        # 内容预览
        question_text = record.get('question', {}).get('text', 'N/A')
        response_text = record.get('response', {}).get('text', 'N/A')
        print(f"\n  问题: {question_text[:100]}...")
        print(f"  答案: {response_text[:200]}...")
        print("-" * 100)


def view_statistics(days=7):
    """查看统计信息（V2格式）"""
    logger = get_logger()
    stats = logger.get_statistics(days=days)
    
    print("=" * 100)
    print(f"AI响应记录统计（最近 {days} 天）")
    print("=" * 100)
    
    print(f"\n📊 总体统计:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  成功记录: {stats['successful_records']}")
    print(f"  失败记录: {stats['failed_records']}")
    if stats['total_records'] > 0:
        success_rate = stats['successful_records'] / stats['total_records'] * 100
        print(f"  成功率: {success_rate:.1f}%")
    
    print(f"\n🔧 平台分布:")
    for platform, count in sorted(stats['platforms'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {platform}: {count} 条")
    
    print(f"\n🤖 使用模型 ({len(stats['models'])} 个):")
    for model in stats['models'][:10]:
        print(f"  - {model}")
    
    print(f"\n🏢 涉及品牌 ({len(stats['brands'])} 个):")
    for brand in sorted(stats['brands'])[:20]:
        print(f"  - {brand}")
    if len(stats['brands']) > 20:
        print(f"  ... 还有 {len(stats['brands']) - 20} 个品牌")
    
    print(f"\n⚡ 性能指标:")
    perf = stats.get('performance', {})
    if perf.get('avg_latency_ms'):
        print(f"  平均延迟: {perf['avg_latency_ms']} ms")
    if perf.get('total_tokens'):
        print(f"  总Token消耗: {perf['total_tokens']}")
    
    if stats.get('errors'):
        print(f"\n❌ 错误类型分布:")
        for error_type, count in stats['errors'].items():
            print(f"  - {error_type}: {count} 次")
    
    if stats.get('question_categories'):
        print(f"\n📋 问题分类分布:")
        for category, count in stats['question_categories'].items():
            print(f"  - {category}: {count} 条")
    
    print(f"\n📁 日志文件: {stats['log_file']}")
    print("=" * 100)


def export_to_json(output_file='ai_responses_v2_export.json', limit=10000):
    """导出记录到JSON文件（V2格式）"""
    logger = get_logger()
    responses = logger.get_recent_responses(limit=limit)
    
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已导出 {len(responses)} 条记录到: {output_path.absolute()}")


def export_for_training(output_file='training_data.jsonl'):
    """导出为训练数据格式（question-answer对）"""
    logger = get_logger()
    responses = logger.get_recent_responses(limit=10000, success_only=True)
    
    output_path = Path(output_file)
    training_data = []
    
    for record in responses:
        qa_pair = {
            "instruction": record.get('question', {}).get('text', ''),
            "input": "",
            "output": record.get('response', {}).get('text', ''),
            "metadata": {
                "platform": record.get('platform', {}).get('name'),
                "model": record.get('platform', {}).get('model'),
                "brand": record.get('business', {}).get('brand'),
                "category": record.get('business', {}).get('question_category'),
                "timestamp": record.get('timestamp'),
                "quality_score": record.get('quality', {}).get('score')
            }
        }
        training_data.append(qa_pair)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ 已导出 {len(training_data)} 条训练数据到: {output_path.absolute()}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("AI响应记录查看工具 V2（增强版）")
        print("=" * 60)
        print("用法:")
        print(f"  python {sys.argv[0]} view [数量] [平台] [品牌] [--success-only]  - 查看记录")
        print(f"  python {sys.argv[0]} stats [天数]                                       - 查看统计")
        print(f"  python {sys.argv[0]} export [文件名] [数量]                           - 导出完整数据")
        print(f"  python {sys.argv[0]} training [文件名]                                - 导出训练数据")
        print(f"\n示例:")
        print(f"  python {sys.argv[0]} view 5")
        print(f"  python {sys.argv[0]} view 10 豆包")
        print(f"  python {sys.argv[0]} stats 7")
        print(f"  python {sys.argv[0]} export backup.json 1000")
        print(f"  python {sys.argv[0]} training qa_data.jsonl")
        return
    
    command = sys.argv[1]
    
    if command == 'view':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
        platform = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        brand = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else None
        success_only = '--success-only' in sys.argv
        view_responses(limit, platform, brand, success_only)
    
    elif command == 'stats':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        view_statistics(days)
    
    elif command == 'export':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'ai_responses_v2_export.json'
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
        export_to_json(output_file, limit)
    
    elif command == 'training':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'training_data.jsonl'
        export_for_training(output_file)
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: view, stats, export, training")


if __name__ == "__main__":
    main()
