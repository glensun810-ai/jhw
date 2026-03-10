#!/usr/bin/env python3
"""
查看AI响应记录的工具脚本
用于查看和分析保存的AI训练数据
"""

import json
import sys
from pathlib import Path
from utils.ai_response_logger import get_logger


def view_responses(limit=10, platform=None, brand=None):
    """查看最近的AI响应记录"""
    logger = get_logger()
    responses = logger.get_recent_responses(limit=limit, platform=platform, brand=brand)
    
    print("=" * 80)
    print(f"最近的 {len(responses)} 条AI响应记录")
    print("=" * 80)
    
    for idx, record in enumerate(responses, 1):
        print(f"\n【记录 {idx}】")
        print(f"  时间: {record.get('timestamp', 'N/A')}")
        print(f"  品牌: {record.get('brand', 'N/A')}")
        print(f"  平台: {record.get('platform', 'N/A')}")
        print(f"  模型: {record.get('model', 'N/A')}")
        print(f"  状态: {'✅ 成功' if record.get('success') else '❌ 失败'}")
        print(f"  延迟: {record.get('latency_ms', 'N/A')} ms")
        if record.get('tokens_used'):
            print(f"  Token: {record['tokens_used']}")
        print(f"  问题: {record.get('question', 'N/A')[:80]}...")
        print(f"  答案: {record.get('response', 'N/A')[:150]}...")
        print("-" * 80)


def view_statistics():
    """查看统计信息"""
    logger = get_logger()
    stats = logger.get_statistics()
    
    print("=" * 80)
    print("AI响应记录统计")
    print("=" * 80)
    print(f"\n总记录数: {stats['total_records']}")
    print(f"成功记录: {stats['successful_records']}")
    print(f"失败记录: {stats['failed_records']}")
    print(f"\n平台分布:")
    for platform, count in stats['platforms'].items():
        print(f"  - {platform}: {count} 条")
    print(f"\n涉及品牌 ({len(stats['brands'])} 个):")
    for brand in stats['brands'][:20]:  # 最多显示20个
        print(f"  - {brand}")
    if len(stats['brands']) > 20:
        print(f"  ... 还有 {len(stats['brands']) - 20} 个品牌")
    print(f"\n日志文件: {stats['log_file']}")
    print("=" * 80)


def export_to_json(output_file='ai_responses_export.json'):
    """导出所有记录到JSON文件"""
    logger = get_logger()
    responses = logger.get_recent_responses(limit=10000)  # 获取大量记录
    
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已导出 {len(responses)} 条记录到: {output_path.absolute()}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} view [数量] [平台] [品牌]  - 查看记录")
        print(f"  python {sys.argv[0]} stats                      - 查看统计")
        print(f"  python {sys.argv[0]} export [文件名]            - 导出到JSON")
        print(f"\n示例:")
        print(f"  python {sys.argv[0]} view 5")
        print(f"  python {sys.argv[0]} view 10 豆包")
        print(f"  python {sys.argv[0]} stats")
        print(f"  python {sys.argv[0]} export training_data.json")
        return
    
    command = sys.argv[1]
    
    if command == 'view':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        platform = sys.argv[3] if len(sys.argv) > 3 else None
        brand = sys.argv[4] if len(sys.argv) > 4 else None
        view_responses(limit, platform, brand)
    
    elif command == 'stats':
        view_statistics()
    
    elif command == 'export':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'ai_responses_export.json'
        export_to_json(output_file)
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: view, stats, export")


if __name__ == "__main__":
    main()
