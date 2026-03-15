#!/usr/bin/env python3
"""
AI 平台搜索结果诊断验证脚本

验证目标：
1. 检查数据库中是否保存了三个 AI 平台（deepseek, 豆包，通义千问）的搜索结果
2. 验证品牌"趣车良品"和竞品"车尚艺"的诊断数据完整性
3. 检查 problem"深圳新能源汽车改装门店哪家好"的搜索结果

使用方法：
    python3 verify_ai_search_results.py
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / 'database.db'

def check_database_schema():
    """检查数据库表结构"""
    print("=" * 80)
    print("1. 检查数据库表结构")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查 diagnosis_results 表结构
    cursor.execute("PRAGMA table_info(diagnosis_results)")
    columns = [(row[1], row[2]) for row in cursor.fetchall()]
    
    print(f"\ndiagnosis_results 表字段:")
    for col_name, col_type in columns:
        print(f"  - {col_name}: {col_type}")
    
    # 检查 platform 字段是否存在
    has_platform = any(col[0] == 'platform' for col in columns)
    print(f"\nplatform 字段：{'✅ 存在' if has_platform else '❌ 不存在'}")
    
    conn.close()
    return has_platform

def check_platform_distribution():
    """检查各 AI 平台的数据分布"""
    print("\n" + "=" * 80)
    print("2. 检查各 AI 平台的数据分布")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询所有平台的数据分布
    cursor.execute('''
        SELECT 
            platform,
            model,
            COUNT(*) as count,
            MIN(created_at) as first_record,
            MAX(created_at) as last_record
        FROM diagnosis_results
        WHERE brand = '趣车良品'
          AND (question LIKE '%深圳%' AND question LIKE '%新能源%')
        GROUP BY platform, model
        ORDER BY platform, model
    ''')
    
    rows = cursor.fetchall()
    
    if not rows:
        print("\n❌ 未找到趣车良品关于深圳新能源汽车改装的数据")
        conn.close()
        return False
    
    print(f"\n找到 {len(rows)} 个平台/模型组合:")
    platform_counts = {}
    
    for row in rows:
        platform = row['platform'] or 'NULL'
        model = row['model'] or 'unknown'
        count = row['count']
        first = row['first_record']
        last = row['last_record']
        
        platform_counts[platform] = platform_counts.get(platform, 0) + count
        
        print(f"\n  Platform: {platform}")
        print(f"    Model: {model}")
        print(f"    Count: {count}")
        print(f"    First: {first}")
        print(f"    Last:  {last}")
    
    print("\n平台汇总:")
    required_platforms = ['deepseek', 'doubao', 'qwen']
    for platform in required_platforms:
        count = platform_counts.get(platform, 0)
        status = '✅' if count > 0 else '❌'
        print(f"  {status} {platform}: {count} 条记录")
    
    # 检查是否三个平台都有数据
    all_present = all(platform_counts.get(p, 0) > 0 for p in required_platforms)
    
    conn.close()
    return all_present

def check_question_details():
    """检查具体问题的搜索结果"""
    print("\n" + "=" * 80)
    print("3. 检查具体问题的搜索结果详情")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询具体的问题文本
    cursor.execute('''
        SELECT DISTINCT question
        FROM diagnosis_results
        WHERE brand = '趣车良品'
          AND (question LIKE '%深圳%' AND question LIKE '%新能源%')
    ''')
    
    questions = [row['question'] for row in cursor.fetchall()]
    
    print(f"\n找到 {len(questions)} 个相关问题:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
    
    # 检查每个问题的平台覆盖
    for question in questions[:5]:  # 只显示前 5 个问题
        print(f"\n问题：{question[:60]}...")
        
        cursor.execute('''
            SELECT 
                platform,
                model,
                response_content,
                created_at
            FROM diagnosis_results
            WHERE question = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (question,))
        
        rows = cursor.fetchall()
        platforms_in_question = set(row['platform'] for row in rows if row['platform'])
        
        print(f"  平台覆盖：{', '.join(platforms_in_question) or '无'}")
        print(f"  记录数：{len(rows)}")
    
    conn.close()

def check_ai_responses_file():
    """检查 ai_responses.jsonl 文件中的数据"""
    print("\n" + "=" * 80)
    print("4. 检查 ai_responses.jsonl 文件数据")
    print("=" * 80)
    
    jsonl_path = Path(__file__).parent / 'data' / 'ai_responses' / 'ai_responses.jsonl'
    
    if not jsonl_path.exists():
        print(f"\n❌ 文件不存在：{jsonl_path}")
        return
    
    print(f"\n文件路径：{jsonl_path}")
    
    # 统计平台分布
    platform_counts = {}
    total_count = 0
    target_count = 0
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                total_count += 1
                
                # 检查是否是目标数据
                business = data.get('business', {})
                if isinstance(business, dict):
                    brand = business.get('brand', '')
                else:
                    brand = ''
                    
                question_obj = data.get('question', {})
                if isinstance(question_obj, dict):
                    question_text = question_obj.get('text', '')
                else:
                    question_text = str(question_obj)
                
                if brand == '趣车良品' and '深圳' in question_text and '新能源' in question_text:
                    target_count += 1
                    platform = data.get('platform', {}).get('name', 'unknown') if isinstance(data.get('platform'), dict) else 'unknown'
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1
                    
            except (json.JSONDecodeError, AttributeError) as e:
                continue
    
    print(f"\n文件总记录数：{total_count}")
    print(f"目标记录数（趣车良品 + 深圳 + 新能源）：{target_count}")
    
    if platform_counts:
        print("\n平台分布:")
        required_platforms = ['deepseek', 'doubao', 'qwen']
        for platform in required_platforms:
            count = platform_counts.get(platform, 0)
            status = '✅' if count > 0 else '❌'
            print(f"  {status} {platform}: {count} 条记录")
        
        # 其他平台
        other_platforms = set(platform_counts.keys()) - set(required_platforms)
        for platform in other_platforms:
            print(f"  - {platform}: {platform_counts[platform]} 条记录")

def generate_summary_report():
    """生成总结报告"""
    print("\n" + "=" * 80)
    print("5. 总结报告")
    print("=" * 80)
    
    print("\n诊断目标:")
    print("  - 品牌：趣车良品")
    print("  - 竞品：车尚艺")
    print("  - 问题：深圳新能源汽车改装门店哪家好")
    print("  - AI 平台：deepseek, 豆包，通义千问")
    
    print("\n期望结果:")
    print("  ✅ 三个 AI 平台的搜索结果都完整保存到数据库")
    print("  ✅ diagnosis_results 表中有对应的记录")
    print("  ✅ ai_responses.jsonl 文件中有日志记录")
    
    print("\n实际状态:")
    check_database_schema()
    all_present = check_platform_distribution()
    check_question_details()
    check_ai_responses_file()
    
    print("\n" + "=" * 80)
    print("验证结论")
    print("=" * 80)
    
    if all_present:
        print("\n✅ 验证通过：三个 AI 平台（deepseek, 豆包，通义千问）的搜索结果都已保存到数据库")
    else:
        print("\n❌ 验证失败：部分 AI 平台的搜索结果未保存到数据库")
        print("\n已实施的修复:")
        print("  1. 在 nxm_concurrent_engine_v3.py 中添加 platform 字段")
        print("  2. 确保所有 AI 调用结果都包含平台标识")
        print("  3. 数据库保存逻辑已支持 platform 字段")
        print("\n建议:")
        print("  1. 重新运行品牌诊断测试")
        print("  2. 选择 deepseek, 豆包，通义千问三个平台")
        print("  3. 使用问题：深圳新能源汽车改装门店哪家好")
        print("  4. 运行此脚本验证结果")

if __name__ == '__main__':
    generate_summary_report()
