#!/usr/bin/env python3
"""
测试SQL注入防护模块的修复
"""

import sys
import os
import sqlite3
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_sql_protection():
    """测试SQL注入防护模块"""
    print("🔍 测试SQL注入防护模块修复...")
    
    from wechat_backend.security.sql_protection import SQLInjectionProtector, SafeDatabaseQuery
    
    protector = SQLInjectionProtector()
    
    # 测试1: 合法的INSERT语句不应该被标记为注入
    print("\n1️⃣ 测试合法的INSERT语句...")
    safe_insert = "INSERT INTO test_records (user_id, brand_name) VALUES (?, ?)"
    try:
        is_safe = not protector.contains_sql_injection(safe_insert)
        print(f"   INSERT语句安全性: {'✅ 通过' if is_safe else '❌ 失败'}")
    except Exception as e:
        print(f"   INSERT语句测试异常: {e}")
        is_safe = False
    
    # 测试2: 真正的SQL注入应该被检测到
    print("\n2️⃣ 测试恶意SQL注入...")
    malicious_sql = "1 OR 1=1; DROP TABLE users; --"
    try:
        is_detected = protector.contains_sql_injection(malicious_sql)
        print(f"   恶意注入检测: {'✅ 通过' if is_detected else '❌ 失败'}")
    except Exception as e:
        print(f"   恶意注入测试异常: {e}")
        is_detected = False
    
    # 测试3: UNION注入应该被检测到
    print("\n3️⃣ 测试UNION注入...")
    union_injection = "SELECT * FROM users WHERE id = 1 UNION SELECT username, password FROM admin"
    try:
        is_union_detected = protector.contains_sql_injection(union_injection)
        print(f"   UNION注入检测: {'✅ 通过' if is_union_detected else '❌ 失败'}")
    except Exception as e:
        print(f"   UNION注入测试异常: {e}")
        is_union_detected = False
    
    # 测试4: DROP注入应该被检测到
    print("\n4️⃣ 测试DROP注入...")
    drop_injection = "'; DROP TABLE users; --"
    try:
        is_drop_detected = protector.contains_sql_injection(drop_injection)
        print(f"   DROP注入检测: {'✅ 通过' if is_drop_detected else '❌ 失败'}")
    except Exception as e:
        print(f"   DROP注入测试异常: {e}")
        is_drop_detected = False
    
    # 测试5: 正常的用户输入应该通过
    print("\n5️⃣ 测试正常用户输入...")
    normal_input = "NIO Auto Company"
    try:
        is_normal_safe = not protector.contains_sql_injection(normal_input)
        print(f"   正常输入安全性: {'✅ 通过' if is_normal_safe else '❌ 失败'}")
    except Exception as e:
        print(f"   正常输入测试异常: {e}")
        is_normal_safe = False
    
    # 汇总结果
    print(f"\n📊 测试结果汇总:")
    print(f"   合法INSERT语句: {'✅ 通过' if is_safe else '❌ 失败'}")
    print(f"   恶意注入检测: {'✅ 通过' if is_detected else '❌ 失败'}")
    print(f"   UNION注入检测: {'✅ 通过' if is_union_detected else '❌ 失败'}")
    print(f"   DROP注入检测: {'✅ 通过' if is_drop_detected else '❌ 失败'}")
    print(f"   正常用户输入: {'✅ 通过' if is_normal_safe else '❌ 失败'}")
    
    all_tests_passed = all([is_safe, is_detected, is_union_detected, is_drop_detected, is_normal_safe])
    print(f"\n🎯 总体结果: {'✅ 全部通过' if all_tests_passed else '❌ 存在问题'}")
    
    return all_tests_passed


def test_database_operations():
    """测试数据库操作"""
    print(f"\n🔧 测试数据库操作...")
    
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    # 创建测试数据库
    test_db_path = Path("test_sql_protection.db")
    
    try:
        # 初始化测试表
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_records (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                brand_name TEXT,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
        # 创建安全查询对象
        safe_query = SafeDatabaseQuery(str(test_db_path))
        
        # 测试安全插入
        print("   1️⃣ 测试安全插入操作...")
        try:
            result = safe_query.execute_query(
                "INSERT INTO test_records (user_id, brand_name) VALUES (?, ?)",
                ("user123", "NIO Auto")
            )
            print("   ✅ 安全插入操作: 通过")
            insert_success = True
        except Exception as e:
            print(f"   ❌ 安全插入操作: 失败 - {e}")
            insert_success = False
        
        # 测试安全查询
        print("   2️⃣ 测试安全查询操作...")
        try:
            result = safe_query.execute_query(
                "SELECT * FROM test_records WHERE user_id = ?",
                ("user123",)
            )
            print(f"   ✅ 安全查询操作: 通过 (返回 {len(result)} 条记录)")
            select_success = True
        except Exception as e:
            print(f"   ❌ 安全查询操作: 失败 - {e}")
            select_success = False
        
        # 测试带条件的安全查询
        print("   3️⃣ 测试带条件的安全查询...")
        try:
            result = safe_query.execute_safe_select(
                "test_records",
                conditions={"user_id": "user123", "brand_name": "NIO Auto"}
            )
            print(f"   ✅ 带条件安全查询: 通过 (返回 {len(result)} 条记录)")
            conditional_select_success = True
        except Exception as e:
            print(f"   ❌ 带条件安全查询: 失败 - {e}")
            conditional_select_success = False
        
        # 清理测试数据库
        if test_db_path.exists():
            test_db_path.unlink()
        
        print(f"\n📊 数据库操作测试结果:")
        print(f"   安全插入: {'✅ 通过' if insert_success else '❌ 失败'}")
        print(f"   安全查询: {'✅ 通过' if select_success else '❌ 失败'}")
        print(f"   条件查询: {'✅ 通过' if conditional_select_success else '❌ 失败'}")
        
        db_tests_passed = all([insert_success, select_success, conditional_select_success])
        print(f"\n🎯 数据库操作总体结果: {'✅ 全部通过' if db_tests_passed else '❌ 存在问题'}")
        
        return db_tests_passed
        
    except Exception as e:
        print(f"   ❌ 数据库测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🛡️  SQL注入防护模块修复验证测试")
    print("="*60)
    
    # 测试SQL防护
    protection_ok = test_sql_protection()
    
    # 测试数据库操作
    database_ok = test_database_operations()
    
    print(f"\n" + "="*60)
    print("📋 最终测试结果:")
    print(f"   SQL防护测试: {'✅ 通过' if protection_ok else '❌ 失败'}")
    print(f"   数据库操作测试: {'✅ 通过' if database_ok else '❌ 失败'}")
    
    overall_success = protection_ok and database_ok
    
    if overall_success:
        print(f"\n🎉 所有测试通过! SQL注入防护模块修复成功!")
        print(f"✅ 合法的数据库操作不会再被误拦截")
        print(f"✅ 恶意SQL注入仍能被有效检测")
    else:
        print(f"\n❌ 部分测试失败，请检查修复实现")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)