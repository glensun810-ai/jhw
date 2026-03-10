#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌诊断系统 - 完整验证测试脚本

验证任务:
1. 完整诊断流程
2. 数据库记录验证
3. 前端展示验证

作者：金牌测试工程师
日期：2026-02-25
"""

import sys
import os
import json
import time
import sqlite3
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 测试配置
BASE_URL = 'http://127.0.0.1:5001'
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

# 测试数据
TEST_DATA = {
    'brand_list': ['华为', '小米', '苹果'],
    'selectedModels': ['doubao'],
    'custom_question': '20 万左右的新能源汽车品牌推荐'
}


def print_header(title):
    """打印标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_result(test_name, success, message=""):
    """打印测试结果"""
    status = "✅" if success else "❌"
    print(f"{status} {test_name}: {message}")
    return success


# ==================== 任务 1: 完整诊断流程验证 ====================

def test_diagnosis_flow():
    """验证完整诊断流程"""
    print_header("任务 1: 完整诊断流程验证")
    
    results = []
    
    # 步骤 1: 检查后端服务
    print("步骤 1: 检查后端服务...")
    try:
        import requests
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            results.append(print_result("后端服务", True, "运行正常"))
        else:
            results.append(print_result("后端服务", False, f"状态码：{response.status_code}"))
    except Exception as e:
        results.append(print_result("后端服务", False, str(e)))
        return results  # 服务不可用，后续测试无法执行
    
    # 步骤 2: 启动诊断
    print("\n步骤 2: 启动诊断...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=TEST_DATA,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            execution_id = data.get('execution_id')
            
            if execution_id:
                results.append(print_result("启动诊断", True, f"execution_id: {execution_id}"))
                
                # 步骤 3: 轮询进度
                print("\n步骤 3: 轮询诊断进度...")
                max_polls = 60
                poll_interval = 2  # 秒
                
                for i in range(max_polls):
                    try:
                        response = requests.get(
                            f"{BASE_URL}/test/status/{execution_id}",
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            status_data = response.json()
                            progress = status_data.get('progress', 0)
                            stage = status_data.get('stage', 'unknown')
                            is_completed = status_data.get('is_completed', False)
                            
                            print(f"  轮询 {i+1}/{max_polls}: 进度={progress}%, 阶段={stage}, 完成={is_completed}")
                            
                            if is_completed or stage == 'completed':
                                results.append(print_result(
                                    "诊断完成",
                                    True,
                                    f"轮询次数：{i+1}, 最终进度：{progress}%"
                                ))
                                
                                # 验证返回数据
                                results_count = len(status_data.get('detailed_results', []) or [])
                                results.append(print_result(
                                    "结果数据",
                                    results_count > 0,
                                    f"结果数量：{results_count}"
                                ))
                                
                                break
                            elif stage == 'failed':
                                results.append(print_result(
                                    "诊断完成",
                                    False,
                                    f"诊断失败：{status_data.get('error', '未知错误')}"
                                ))
                                break
                        else:
                            print(f"  轮询 {i+1}/{max_polls}: 状态码={response.status_code}")
                        
                        time.sleep(poll_interval)
                        
                    except Exception as e:
                        print(f"  轮询 {i+1}/{max_polls}: 错误={e}")
                        time.sleep(poll_interval)
                else:
                    results.append(print_result("诊断超时", False, f"超过{max_polls}次轮询"))
            else:
                results.append(print_result("启动诊断", False, "未返回 execution_id"))
        else:
            results.append(print_result("启动诊断", False, f"状态码：{response.status_code}"))
            
    except Exception as e:
        results.append(print_result("启动诊断", False, str(e)))
    
    return results


# ==================== 任务 2: 数据库记录验证 ====================

def test_database_records():
    """验证数据库记录"""
    print_header("任务 2: 数据库记录验证")
    
    results = []
    
    # 步骤 1: 检查数据库文件
    print("步骤 1: 检查数据库文件...")
    if os.path.exists(DB_PATH):
        results.append(print_result("数据库文件", True, f"存在：{DB_PATH}"))
    else:
        results.append(print_result("数据库文件", False, f"不存在：{DB_PATH}"))
        return results
    
    # 步骤 2: 检查表结构
    print("\n步骤 2: 检查表结构...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查 diagnosis_reports 表
        cursor.execute("PRAGMA table_info(diagnosis_reports)")
        reports_columns = [row[1] for row in cursor.fetchall()]
        
        expected_reports_columns = ['id', 'execution_id', 'user_id', 'brand_name', 'status', 'progress']
        missing_reports = [col for col in expected_reports_columns if col not in reports_columns]
        
        if not missing_reports:
            results.append(print_result("diagnosis_reports 表结构", True, f"字段数：{len(reports_columns)}"))
        else:
            results.append(print_result("diagnosis_reports 表结构", False, f"缺少字段：{missing_reports}"))
        
        # 检查 diagnosis_results 表
        cursor.execute("PRAGMA table_info(diagnosis_results)")
        results_columns = [row[1] for row in cursor.fetchall()]
        
        expected_results_columns = ['id', 'report_id', 'execution_id', 'brand', 'question', 'model', 'geo_data', 'quality_score']
        missing_results = [col for col in expected_results_columns if col not in results_columns]
        
        if not missing_results:
            results.append(print_result("diagnosis_results 表结构", True, f"字段数：{len(results_columns)}"))
        else:
            results.append(print_result("diagnosis_results 表结构", False, f"缺少字段：{missing_results}"))
        
        conn.close()
        
    except Exception as e:
        results.append(print_result("表结构检查", False, str(e)))
        return results
    
    # 步骤 3: 检查最新诊断记录
    print("\n步骤 3: 检查最新诊断记录...")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询最新诊断报告
        cursor.execute("""
            SELECT execution_id, brand_name, status, progress, created_at
            FROM diagnosis_reports
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        latest_report = cursor.fetchone()
        
        if latest_report:
            results.append(print_result(
                "最新诊断报告",
                True,
                f"execution_id: {latest_report['execution_id']}, 品牌：{latest_report['brand_name']}, 状态：{latest_report['status']}"
            ))
            
            # 查询对应的结果
            cursor.execute("""
                SELECT COUNT(*) as count, AVG(quality_score) as avg_score
                FROM diagnosis_results
                WHERE execution_id = ?
            """, (latest_report['execution_id'],))
            
            result_stats = cursor.fetchone()
            
            if result_stats['count'] > 0:
                results.append(print_result(
                    "诊断结果",
                    True,
                    f"结果数量：{result_stats['count']}, 平均质量分：{result_stats['avg_score']:.1f}"
                ))
            else:
                results.append(print_result("诊断结果", False, "无结果记录"))
        else:
            results.append(print_result("最新诊断报告", False, "无记录"))
        
        conn.close()
        
    except Exception as e:
        results.append(print_result("记录检查", False, str(e)))
    
    return results


# ==================== 任务 3: 前端展示验证 ====================

def test_frontend_display():
    """验证前端展示"""
    print_header("任务 3: 前端展示验证")
    
    results = []
    
    # 步骤 1: 检查前端文件
    print("步骤 1: 检查前端文件...")
    
    frontend_files = [
        'pages/index/index.js',
        'pages/index/index.wxml',
        'pages/results/results.js',
        'pages/results/results.wxml',
        'services/diagnosisApi.js'
    ]
    
    for file_path in frontend_files:
        full_path = os.path.join(os.path.dirname(__file__), '..', '..', file_path)
        if os.path.exists(full_path):
            results.append(print_result(f"前端文件：{file_path}", True, "存在"))
        else:
            results.append(print_result(f"前端文件：{file_path}", False, "不存在"))
    
    # 步骤 2: 检查前端代码关键逻辑
    print("\n步骤 2: 检查前端代码关键逻辑...")
    
    results_js_path = os.path.join(os.path.dirname(__file__), '..', '..', 'pages/results/results.js')
    
    if os.path.exists(results_js_path):
        try:
            with open(results_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查空结果处理
            if 'showEmptyState' in content:
                results.append(print_result("空结果处理", True, "showEmptyState 函数存在"))
            else:
                results.append(print_result("空结果处理", False, "缺少 showEmptyState 函数"))
            
            # 检查数据加载
            if 'getFullReport' in content:
                results.append(print_result("API 调用", True, "getFullReport 函数存在"))
            else:
                results.append(print_result("API 调用", False, "缺少 getFullReport 函数"))
            
            # 检查缓存处理
            if 'last_diagnostic_results' in content:
                results.append(print_result("缓存处理", True, "缓存逻辑存在"))
            else:
                results.append(print_result("缓存处理", False, "缺少缓存逻辑"))
            
        except Exception as e:
            results.append(print_result("前端代码检查", False, str(e)))
    
    # 步骤 3: 检查 WXML 模板
    print("\n步骤 3: 检查 WXML 模板...")
    
    results_wxml_path = os.path.join(os.path.dirname(__file__), '..', '..', 'pages/results/results.wxml')
    
    if os.path.exists(results_wxml_path):
        try:
            with open(results_wxml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查关键展示元素
            if 'targetBrand' in content:
                results.append(print_result("品牌展示", True, "targetBrand 绑定存在"))
            else:
                results.append(print_result("品牌展示", False, "缺少 targetBrand 绑定"))
            
            if 'competitiveAnalysis' in content:
                results.append(print_result("竞争分析", True, "competitiveAnalysis 绑定存在"))
            else:
                results.append(print_result("竞争分析", False, "缺少 competitiveAnalysis 绑定"))
            
            # 检查 WXML 语法
            if content.count('<block wx:if') == content.count('</block>'):
                results.append(print_result("WXML 语法", True, "block 标签配对正确"))
            else:
                results.append(print_result("WXML 语法", False, "block 标签配对错误"))
            
        except Exception as e:
            results.append(print_result("WXML 检查", False, str(e)))
    
    return results


# ==================== 主函数 ====================

def main():
    """主函数"""
    print("\n" + "="*70)
    print("  品牌诊断系统 - 完整验证测试")
    print("="*70)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"后端地址：{BASE_URL}")
    print(f"数据库路径：{DB_PATH}")
    
    all_results = []
    
    # 任务 1: 完整诊断流程验证
    all_results.extend(test_diagnosis_flow())
    
    # 任务 2: 数据库记录验证
    all_results.extend(test_database_records())
    
    # 任务 3: 前端展示验证
    all_results.extend(test_frontend_display())
    
    # 总结
    print_header("验证总结")
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r)
    failed = total - passed
    
    print(f"总测试数：{total}")
    print(f"通过：{passed} ({passed/total*100:.1f}%)")
    print(f"失败：{failed} ({failed/total*100:.1f}%)")
    
    if failed > 0:
        print("\n失败的测试:")
        for i, result in enumerate(all_results, 1):
            if not result:
                print(f"  {i}. {result}")
    
    print("\n" + "="*70)
    
    if failed == 0:
        print("✅ 所有验证通过！系统可以上线。")
        return 0
    else:
        print(f"⚠️  {failed} 个验证失败，请修复后重新验证。")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
