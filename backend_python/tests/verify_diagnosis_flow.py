#!/usr/bin/env python3
"""
诊断数据流自动化验证脚本 v2

验证点：
1. AI 品牌提取代码是否存在
2. 数据库 schema 是否正确
3. 数据质量是否合格
4. API 端点是否可访问
"""

import sqlite3
import sys
import os

DB_PATH = 'backend_python/database.db'
CODE_PATH = 'backend_python/wechat_backend/nxm_concurrent_engine_v3.py'

def check_brand_extraction_code():
    """检查品牌提取代码是否存在"""
    print("🔍 检查品牌提取代码...")
    try:
        with open(CODE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            if '_extract_recommended_brand' in content:
                print("✅ 品牌提取代码存在")
                return True
            else:
                print("❌ 品牌提取代码不存在")
                return False
    except Exception as e:
        print(f"❌ 读取代码文件失败：{e}")
        return False

def check_database_schema():
    """检查数据库 schema"""
    print("🔍 检查数据库 schema...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(diagnosis_results)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['extracted_brand', 'raw_response', 'extraction_method', 'platform']
        missing = [col for col in required_columns if col not in columns]
        
        if not missing:
            print("✅ 数据库 schema 正确 (所有必需字段存在)")
            return True
        else:
            print(f"❌ 缺少字段：{missing}")
            return False
    except Exception as e:
        print(f"❌ 检查数据库失败：{e}")
        return False

def check_data_quality():
    """检查数据质量"""
    print("🔍 检查数据质量...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查最新 10 条记录
        cursor.execute("""
            SELECT execution_id, brand, extracted_brand 
            FROM diagnosis_results 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️  数据库中没有记录（这是正常的，执行一次诊断后再检查）")
            return True
        
        total = len(rows)
        has_extracted = sum(1 for row in rows if row[2] is not None)
        extraction_rate = has_extracted / total if total > 0 else 0
        
        print(f"   检查了 {total} 条记录")
        print(f"   有 extracted_brand 的：{has_extracted}/{total} ({extraction_rate:.2%})")
        
        if extraction_rate == 0:
            print("⚠️  extracted_brand 全部为 NULL")
            print("   可能原因：")
            print("   1. 后端服务未重启（代码未生效）")
            print("   2. AI 调用使用的是旧代码路径")
            print("   3. 品牌提取逻辑未执行")
            return False
        elif extraction_rate < 0.5:
            print(f"⚠️  提取率偏低 ({extraction_rate:.2%})，建议检查")
            return True  # 至少有一些数据
        else:
            print(f"✅ 数据质量良好 (提取率 {extraction_rate:.2%})")
            return True
    except Exception as e:
        print(f"❌ 检查数据质量失败：{e}")
        return False

def check_api_endpoint():
    """检查 API 端点"""
    print("🔍 检查 API 端点配置...")
    try:
        import requests
        # 使用根端点检查（返回版本号）
        response = requests.get('http://localhost:5001/', timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务可访问")
            return True
        else:
            print(f"❌ 后端服务返回错误状态码：{response.status_code}")
            return False
    except ImportError:
        print("⚠️  requests 库未安装，跳过 API 检查")
        return True
    except Exception as e:
        print(f"❌ 后端服务不可访问：{e}")
        print("   请确保后端服务已启动：cd backend_python && ./stop_server.sh && ./start_server.sh")
        return False

def main():
    print("=" * 70)
    print("诊断数据流自动化验证 v2")
    print("=" * 70)
    print()
    
    checks = [
        ("代码检查", check_brand_extraction_code),
        ("数据库 schema", check_database_schema),
        ("数据质量", check_data_quality),
        ("API 端点", check_api_endpoint),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查异常：{e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(checks):
        status = "✅" if results[i] else "❌"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！")
        print("\n下一步:")
        print("1. 在小程序中执行一次完整诊断")
        print("2. 再次运行此脚本验证数据质量")
        print("3. 检查前端是否能查看完整报告")
        return 0
    else:
        print("\n❌ 有检查未通过，请修复后重试")
        print("\n修复建议:")
        if not results[0]:
            print("- 检查品牌提取代码是否正确添加")
        if not results[1]:
            print("- 执行数据库迁移：sqlite3 backend_python/database.db < backend_python/database/migrations/005_add_raw_response_fields.sql")
        if not results[3]:
            print("- 重启后端服务：cd backend_python && python3 run.py &")
        return 1

if __name__ == '__main__':
    sys.exit(main())
