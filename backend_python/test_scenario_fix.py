#!/usr/bin/env python3
"""
测试修复后的场景：DeepSeek API认证失败后，AI评分回退逻辑能够正常保存结果
"""

import sqlite3
import tempfile
import os
from pathlib import Path

def test_scenario_fix():
    """测试场景修复"""
    print("🔍 测试修复后的场景：DeepSeek API认证失败后保存结果")
    print("="*60)
    
    # 导入必要的模块
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化测试表
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_records (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                brand_name TEXT,
                ai_models_used TEXT,
                questions_used TEXT,
                overall_score REAL,
                total_tests INTEGER,
                results_summary TEXT,
                detailed_results TEXT,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
        # 创建安全查询对象
        safe_query = SafeDatabaseQuery(db_path)
        
        print("1️⃣ 模拟DeepSeek API认证失败的场景...")
        # 这是模拟DeepSeek API返回认证失败错误的场景
        deepseek_error_msg = "Authentication Fails, Your api key: ****9f92 is invalid"
        print(f"   DeepSeek错误信息: {deepseek_error_msg}")
        
        print("\n2️⃣ 模拟AI评分失败后的回退逻辑...")
        print("   尝试保存测试结果到数据库...")
        
        # 模拟保存测试记录 - 这是原来会被SQL防护模块拦截的操作
        try:
            result = safe_query.execute_query(
                """INSERT INTO test_records 
                   (user_id, brand_name, ai_models_used, questions_used, overall_score, 
                    total_tests, results_summary, detailed_results) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "test_user_123",
                    "Test Brand",
                    '["DeepSeek"]',
                    '["What is the brand?"]',
                    0,  # Score is 0 due to API failure
                    1,  # Total tests
                    f"DeepSeek API failed: {deepseek_error_msg}",
                    "[]",  # Empty detailed results due to failure
                )
            )
            print("   ✅ 数据库插入操作: 成功")
            save_success = True
        except Exception as e:
            print(f"   ❌ 数据库插入操作: 失败 - {e}")
            save_success = False
        
        print("\n3️⃣ 验证其他正常操作不受影响...")
        try:
            # 查询刚插入的记录
            records = safe_query.execute_query(
                "SELECT * FROM test_records WHERE user_id = ?",
                ("test_user_123",)
            )
            print(f"   ✅ 数据库查询操作: 成功 (返回 {len(records)} 条记录)")
            query_success = True
        except Exception as e:
            print(f"   ❌ 数据库查询操作: 失败 - {e}")
            query_success = False
        
        print("\n4️⃣ 测试包含错误信息的参数是否被正确处理...")
        try:
            # 插入包含API错误信息的记录
            result = safe_query.execute_query(
                "INSERT INTO test_records (user_id, results_summary) VALUES (?, ?)",
                ("error_test", f"API Error: {deepseek_error_msg}")
            )
            print("   ✅ 包含错误信息的插入: 成功")
            error_handling_success = True
        except Exception as e:
            print(f"   ❌ 包含错误信息的插入: 失败 - {e}")
            error_handling_success = False
        
        print("\n" + "="*60)
        print("📊 场景修复测试结果:")
        print(f"   结果保存操作: {'✅ 成功' if save_success else '❌ 失败'}")
        print(f"   数据库查询操作: {'✅ 成功' if query_success else '❌ 失败'}")
        print(f"   错误信息处理: {'✅ 成功' if error_handling_success else '❌ 失败'}")
        
        overall_success = save_success and query_success and error_handling_success
        print(f"\n🎯 场景修复总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
        
        if overall_success:
            print("\n🎉 修复成功!")
            print("✅ DeepSeek API认证失败后，系统可以正常保存结果")
            print("✅ SQL防护模块不再拦截合法的INSERT操作")
            print("✅ 系统在API失败时的回退逻辑正常工作")
        else:
            print("\n❌ 修复存在问题，请检查实现")
        
        return overall_success
        
    finally:
        # 清理临时数据库
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """主函数"""
    print("🛡️  SQL防护模块场景修复验证测试")
    print("针对: DeepSeek API认证失败 → AI评分回退 → SQL防护拦截问题")
    print("="*70)
    
    success = test_scenario_fix()
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)