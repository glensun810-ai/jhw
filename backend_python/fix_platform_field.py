#!/usr/bin/env python3
"""
修复脚本：为现有记录回填 platform 字段

问题诊断：
- 历史数据的 diagnosis_results 表中 platform 字段为 NULL
- 原因：nxm_concurrent_engine_v3.py 未返回 platform 字段

修复方案：
- 根据 model 字段推断 platform
- 批量更新现有记录

使用方法：
    python3 fix_platform_field.py
"""

import sqlite3
import json
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / 'database.db'

def infer_platform_from_model(model_name: str) -> str:
    """
    根据模型名称推断平台名称
    
    Args:
        model_name: 模型名称
        
    Returns:
        platform: 平台名称
    """
    if not model_name:
        return ''
    
    model_lower = model_name.lower()
    
    if 'deepseek' in model_lower:
        return 'deepseek'
    elif 'doubao' in model_lower:
        return 'doubao'
    elif 'qwen' in model_lower or '通义' in model_lower or '千问' in model_lower:
        return 'qwen'
    elif 'gemini' in model_lower:
        return 'gemini'
    elif 'chatgpt' in model_lower or 'gpt' in model_lower:
        return 'chatgpt'
    elif 'glm' in model_lower or 'zhipu' in model_lower or '智谱' in model_lower:
        return 'zhipu'
    elif 'ernie' in model_lower or 'wenxin' in model_lower or '百度' in model_lower:
        return 'wenxin'
    elif 'kimi' in model_lower:
        return 'kimi'
    else:
        # 尝试从第一个连字符前的部分推断
        parts = model_name.split('-')
        if parts:
            return parts[0].lower()
        return ''

def fix_platform_field():
    """修复 platform 字段"""
    print("=" * 80)
    print("修复 platform 字段")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 统计需要修复的记录
    print("\n1. 统计需要修复的记录...")
    cursor.execute('''
        SELECT 
            id,
            model,
            platform,
            brand,
            question
        FROM diagnosis_results
        WHERE platform IS NULL OR platform = ''
        ORDER BY created_at DESC
    ''')
    
    null_platform_rows = cursor.fetchall()
    print(f"   发现 {len(null_platform_rows)} 条记录的 platform 字段为空")
    
    if not null_platform_rows:
        print("   ✅ 无需修复，所有记录都有 platform 字段")
        conn.close()
        return
    
    # 2. 展示样本记录
    print("\n2. 样本记录（前 10 条）:")
    for i, row in enumerate(null_platform_rows[:10], 1):
        model = row['model'] or 'unknown'
        brand = row['brand'] or ''
        question = row['question'] or ''
        inferred = infer_platform_from_model(model)
        print(f"   {i}. model={model}, brand={brand}, inferred_platform={inferred}")
    
    # 3. 询问是否继续
    confirm = input(f"\n是否继续修复 {len(null_platform_rows)} 条记录？(y/n): ")
    if confirm.lower() != 'y':
        print("   已取消修复")
        conn.close()
        return
    
    # 4. 执行批量更新
    print("\n3. 执行批量更新...")
    updated_count = 0
    batch_size = 100
    
    for i in range(0, len(null_platform_rows), batch_size):
        batch = null_platform_rows[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(null_platform_rows) + batch_size - 1) // batch_size
        
        for row in batch:
            model = row['model']
            inferred_platform = infer_platform_from_model(model)
            
            cursor.execute('''
                UPDATE diagnosis_results
                SET platform = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (inferred_platform, row['id']))
            
            updated_count += 1
        
        # 每批提交一次
        conn.commit()
        print(f"   批次 {batch_num}/{total_batches}: 已更新 {updated_count}/{len(null_platform_rows)} 条记录")
    
    # 5. 验证修复结果
    print("\n4. 验证修复结果...")
    cursor.execute('''
        SELECT 
            platform,
            COUNT(*) as count
        FROM diagnosis_results
        GROUP BY platform
        ORDER BY count DESC
    ''')
    
    platform_stats = cursor.fetchall()
    print("\n   平台分布统计:")
    for row in platform_stats:
        platform = row['platform'] or 'NULL'
        count = row['count']
        print(f"   - {platform}: {count} 条记录")
    
    # 6. 检查目标数据
    print("\n5. 检查目标数据（趣车良品 + 深圳新能源汽车改装）...")
    cursor.execute('''
        SELECT 
            platform,
            COUNT(*) as count
        FROM diagnosis_results
        WHERE brand = '趣车良品'
          AND (question LIKE '%深圳%' AND question LIKE '%新能源%')
        GROUP BY platform
        ORDER BY platform
    ''')
    
    target_stats = cursor.fetchall()
    required_platforms = ['deepseek', 'doubao', 'qwen']
    platform_counts = {row['platform']: row['count'] for row in target_stats}
    
    print("\n   目标数据平台分布:")
    all_present = True
    for platform in required_platforms:
        count = platform_counts.get(platform, 0)
        status = '✅' if count > 0 else '❌'
        print(f"   {status} {platform}: {count} 条记录")
        if count == 0:
            all_present = False
    
    # 其他平台
    for platform in platform_counts:
        if platform not in required_platforms:
            print(f"   - {platform}: {platform_counts[platform]} 条记录")
    
    conn.close()
    
    # 7. 总结
    print("\n" + "=" * 80)
    print("修复总结")
    print("=" * 80)
    print(f"\n✅ 成功更新 {updated_count} 条记录的 platform 字段")
    
    if all_present:
        print("\n✅ 验证通过：三个 AI 平台（deepseek, 豆包，通义千问）都有数据")
    else:
        print("\n⚠️  注意：部分 AI 平台仍然没有数据")
        print("\n建议:")
        print("  1. 重新运行品牌诊断测试")
        print("  2. 选择 deepseek, 豆包，通义千问三个平台")
        print("  3. 使用问题：深圳新能源汽车改装门店哪家好")
        print("  4. 运行 verify_ai_search_results.py 验证结果")

if __name__ == '__main__':
    fix_platform_field()
