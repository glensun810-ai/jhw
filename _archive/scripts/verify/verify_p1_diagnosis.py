#!/usr/bin/env python3
"""
P1 诊断任务验证脚本

功能：
1. 创建测试诊断任务
2. 验证数据持久化日志
3. 检查 brand_test_results 表是否有新记录

注意：此脚本需要后端服务运行
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
db_path = project_root / 'backend_python' / 'database.db'

def check_database_before():
    """检查测试前数据库状态"""
    print("=" * 60)
    print("P1 诊断任务验证 - 测试前检查")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取当前记录数
    cursor.execute('SELECT COUNT(*) FROM task_statuses')
    task_count_before = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM brand_test_results')
    result_count_before = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
    report_count_before = cursor.fetchone()[0]
    
    # 获取最新任务
    cursor.execute('''
        SELECT task_id, stage, progress, is_completed, created_at 
        FROM task_statuses 
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    latest_task = cursor.fetchone()
    
    conn.close()
    
    print(f"""
数据库状态 (测试前):
  task_statuses: {task_count_before} 条
  brand_test_results: {result_count_before} 条
  diagnosis_reports: {report_count_before} 条
  
最新任务:
  task_id: {latest_task[0] if latest_task else '无'}
  stage: {latest_task[1] if latest_task else '无'}
  progress: {latest_task[2] if latest_task else '无'}%
  created: {latest_task[4] if latest_task else '无'}
""")
    
    return {
        'task_count': task_count_before,
        'result_count': result_count_before,
        'report_count': report_count_before,
        'latest_task_id': latest_task[0] if latest_task else None
    }

def check_database_after(before_stats):
    """检查测试后数据库状态"""
    print("\n" + "=" * 60)
    print("P1 诊断任务验证 - 测试后检查")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取当前记录数
    cursor.execute('SELECT COUNT(*) FROM task_statuses')
    task_count_after = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM brand_test_results')
    result_count_after = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM diagnosis_reports')
    report_count_after = cursor.fetchone()[0]
    
    # 检查是否有新任务
    cursor.execute('''
        SELECT task_id, stage, progress, is_completed, created_at 
        FROM task_statuses 
        ORDER BY created_at DESC 
        LIMIT 3
    ''')
    latest_tasks = cursor.fetchall()
    
    # 检查 brand_test_results 表
    cursor.execute('''
        SELECT task_id, brand_name, overall_score, created_at 
        FROM brand_test_results 
        ORDER BY created_at DESC 
        LIMIT 3
    ''')
    latest_results = cursor.fetchall()
    
    conn.close()
    
    new_tasks = task_count_after - before_stats['task_count']
    new_results = result_count_after - before_stats['result_count']
    
    print(f"""
数据库状态 (测试后):
  task_statuses: {task_count_after} 条 (新增：{new_tasks})
  brand_test_results: {result_count_after} 条 (新增：{new_results}) ✅
  diagnosis_reports: {report_count_after} 条 (新增：{report_count_after - before_stats['report_count']})

最新 3 个任务:
""")
    
    for i, task in enumerate(latest_tasks, 1):
        print(f"  {i}. task_id: {task[0]}")
        print(f"     stage: {task[1]}, progress: {task[2]}%, completed: {task[3]}")
        print(f"     created: {task[4]}")
    
    if latest_results:
        print("\n最新品牌测试结果:")
        for i, result in enumerate(latest_results, 1):
            print(f"  {i}. task_id: {result[0]}, brand: {result[1]}, score: {result[2]}")
    
    # 验证结论
    print("\n" + "=" * 60)
    print("验证结论")
    print("=" * 60)
    
    if new_results > 0:
        print("✅ P1 修复验证成功！brand_test_results 表已有新记录")
        print(f"   新增测试结果：{new_results} 条")
        return True
    elif new_tasks > 0:
        print("⚠️  有新任务但无结果")
        print("   可能原因:")
        print("   1. 任务仍在执行中")
        print("   2. AI 调用失败")
        print("   3. 保存逻辑仍有问题")
        print("\n   建议：检查后端日志")
        return False
    else:
        print("❌ 无新任务产生")
        print("   可能原因:")
        print("   1. 后端服务未运行")
        print("   2. 前端请求未发送")
        print("\n   建议：检查后端服务和前端连接")
        return False

def check_logs():
    """检查日志中的 P1 持久化信息"""
    print("\n" + "=" * 60)
    print("P1 日志检查")
    print("=" * 60)
    
    log_path = project_root / 'logs' / 'app.log'
    
    if not log_path.exists():
        print("⚠️  日志文件不存在")
        return
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找最近的 P1 日志
        p1_logs = []
        for line in reversed(lines[-500:]):  # 检查最近 500 行
            if '[P1 数据持久化]' in line:
                p1_logs.append(line.strip())
                if len(p1_logs) >= 10:  # 最多显示 10 条
                    break
        
        if p1_logs:
            print("\n最近 P1 数据持久化日志:")
            for log in reversed(p1_logs):
                # 简化显示
                if '✅' in log or '❌' in log or '开始' in log:
                    print(f"  {log[20:100]}...")
        else:
            print("\n⚠️  未发现 P1 数据持久化日志")
            print("   说明：修复后尚未执行新的诊断任务")
    
    except Exception as e:
        print(f"⚠️  读取日志失败：{e}")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("P1 诊断任务修复验证脚本")
    print("=" * 60)
    print(f"数据库路径：{db_path}")
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查测试前状态
    before_stats = check_database_before()
    
    # 检查日志
    check_logs()
    
    # 用户操作提示
    print("\n" + "=" * 60)
    print("操作指南")
    print("=" * 60)
    print("""
请执行以下步骤:

1. 打开微信开发者工具
2. 在首页输入测试数据:
   - 品牌名称：特斯拉
   - 竞品：比亚迪、蔚来、小鹏
   - AI 模型：豆包、通义千问
3. 点击"开始诊断"
4. 等待诊断完成
5. 重新运行此脚本验证

命令：python3 verify_p1_diagnosis.py
""")
    
    # 询问是否已执行测试
    if len(sys.argv) > 1 and sys.argv[1] == '--after':
        # 直接检查测试后状态
        check_database_after(before_stats)
    else:
        print("\n当前为测试前检查，执行诊断任务后请运行:")
        print("  python3 verify_p1_diagnosis.py --after")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
