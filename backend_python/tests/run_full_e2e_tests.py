#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试缺口实施执行脚本
按阶段执行所有未完成的测试

对应测试计划：2026-02-23_端到端测试缺口实施计划.md
"""

import requests
import time
import sys
import os

# 配置
BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10
TEST_RESULTS = {
    'total': 0,
    'passed': 0,
    'failed': 0,
    'stages': {}
}

def print_header(text, level=1):
    """打印标题"""
    if level == 1:
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'-'*70}")
        print(f"  {text}")
        print(f"{'-'*70}\n")

def print_result(name, passed, message=""):
    """打印测试结果"""
    status = "✅" if passed else "❌"
    print(f"  {status} {name}: {'通过' if passed else '失败'} {message}")
    TEST_RESULTS['total'] += 1
    if passed:
        TEST_RESULTS['passed'] += 1
    else:
        TEST_RESULTS['failed'] += 1
    return passed

def check_service_status():
    """检查服务状态"""
    print_header("第 0 步：检查后端服务状态")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 后端服务未正常运行 (状态码：{response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到后端服务 ({BASE_URL})")
        print(f"\n请先启动后端服务:")
        print(f"  cd /Users/sgl/PycharmProjects/PythonProject/backend_python")
        print(f"  python run.py")
        return False
    except Exception as e:
        print(f"❌ 检查失败：{e}")
        return False

# =============================================================================
# 第一阶段：后端 API 深度测试
# =============================================================================

def stage1_backend_api_tests():
    """第一阶段：后端 API 深度测试"""
    print_header("第一阶段：后端 API 深度测试")
    
    stage_results = {'total': 0, 'passed': 0}
    TEST_RESULTS['stages']['stage1'] = stage_results
    
    # T1.1: AI 平台列表
    print("\nT1.1: 测试 AI 平台列表 (/api/ai-platforms)...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai-platforms", timeout=TIMEOUT)
        passed = response.status_code == 200
        print_result("AI 平台列表", passed, f"({response.status_code})")
        stage_results['total'] += 1
        if passed:
            stage_results['passed'] += 1
            platforms = response.json()
            print(f"     可用平台：{len(platforms) if platforms else 0} 个")
    except Exception as e:
        print_result("AI 平台列表", False, str(e))
        stage_results['total'] += 1
    
    # T1.2: 平台状态查询
    print("\nT1.2: 测试平台状态查询 (/api/platform-status)...")
    try:
        response = requests.get(f"{BASE_URL}/api/platform-status", timeout=TIMEOUT)
        passed = response.status_code == 200
        print_result("平台状态查询", passed, f"({response.status_code})")
        stage_results['total'] += 1
        if passed:
            stage_results['passed'] += 1
    except Exception as e:
        print_result("平台状态查询", False, str(e))
        stage_results['total'] += 1
    
    # T1.3: 诊断任务提交
    print("\nT1.3: 测试诊断任务提交 (/api/perform-brand-test)...")
    execution_id = None
    try:
        payload = {
            "brand_list": ["测试品牌"],
            "selectedModels": [{"name": "DeepSeek", "checked": True}],
            "custom_question": "介绍一下测试品牌"
        }
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200
        print_result("诊断任务提交", passed, f"({response.status_code})")
        stage_results['total'] += 1
        if passed:
            stage_results['passed'] += 1
            data = response.json()
            execution_id = data.get('execution_id')
            print(f"     执行 ID: {execution_id}")
    except Exception as e:
        print_result("诊断任务提交", False, str(e))
        stage_results['total'] += 1
    
    # T1.4: 任务状态查询
    print("\nT1.4: 测试任务状态查询...")
    if execution_id:
        try:
            response = requests.get(
                f"{BASE_URL}/test/status/{execution_id}",
                timeout=TIMEOUT
            )
            passed = response.status_code == 200
            print_result("任务状态查询", passed, f"({response.status_code})")
            stage_results['total'] += 1
            if passed:
                stage_results['passed'] += 1
                status_data = response.json()
                stage = status_data.get('stage', 'unknown')
                progress = status_data.get('progress', 0)
                print(f"     当前阶段：{stage} ({progress}%)")
        except Exception as e:
            print_result("任务状态查询", False, str(e))
            stage_results['total'] += 1
    else:
        print("     ⏭️  跳过（无 execution_id）")
    
    # T1.5: 任务进度查询
    print("\nT1.5: 测试任务进度查询...")
    if execution_id:
        try:
            response = requests.get(
                f"{BASE_URL}/api/test-progress?executionId={execution_id}",
                timeout=TIMEOUT
            )
            passed = response.status_code == 200
            print_result("任务进度查询", passed, f"({response.status_code})")
            stage_results['total'] += 1
            if passed:
                stage_results['passed'] += 1
        except Exception as e:
            print_result("任务进度查询", False, str(e))
            stage_results['total'] += 1
    else:
        print("     ⏭️  跳过（无 execution_id）")
    
    # T1.6: 诊断结果获取
    print("\nT1.6: 测试诊断结果获取...")
    if execution_id:
        try:
            response = requests.get(
                f"{BASE_URL}/test/result/{execution_id}",
                timeout=TIMEOUT
            )
            passed = response.status_code == 200
            print_result("诊断结果获取", passed, f"({response.status_code})")
            stage_results['total'] += 1
            if passed:
                stage_results['passed'] += 1
                result_data = response.json()
                print(f"     结果数据：{len(str(result_data))} 字节")
        except Exception as e:
            print_result("诊断结果获取", False, str(e))
            stage_results['total'] += 1
    else:
        print("     ⏭️  跳过（无 execution_id）")
    
    # 打印阶段统计
    print_header("第一阶段测试统计")
    print(f"  通过：{stage_results['passed']}/{stage_results['total']} ({stage_results['passed']/stage_results['total']*100:.1f}%)")
    
    return execution_id

# =============================================================================
# 第二阶段：真实 AI 调用测试
# =============================================================================

def stage2_real_ai_tests():
    """第二阶段：真实 AI 调用测试"""
    print_header("第二阶段：真实 AI 调用测试")
    
    stage_results = {'total': 0, 'passed': 0}
    TEST_RESULTS['stages']['stage2'] = stage_results
    
    platforms = [
        ('DeepSeek', 'deepseek'),
        ('通义千问', 'qwen'),
        ('豆包', 'doubao'),
        ('智谱 AI', 'zhipu')
    ]
    
    for platform_name, platform_id in platforms:
        print(f"\nT2.x: 测试 {platform_name} ({platform_id})...")
        
        try:
            payload = {
                "brand_list": ["测试品牌"],
                "selectedModels": [{"name": platform_id, "checked": True}],
                "custom_question": "介绍一下测试品牌"
            }
            
            # 提交任务
            response = requests.post(
                f"{BASE_URL}/api/perform-brand-test",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print_result(f"{platform_name} 任务提交", False, f"({response.status_code})")
                stage_results['total'] += 1
                continue
            
            execution_id = response.json().get('execution_id')
            print(f"     ✅ 任务提交成功，执行 ID: {execution_id}")
            
            # 轮询进度（最多 30 秒）
            max_retries = 15
            completed = False
            for i in range(max_retries):
                time.sleep(2)
                
                status_response = requests.get(
                    f"{BASE_URL}/test/status/{execution_id}",
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    stage = status_data.get('stage', 'unknown')
                    progress = status_data.get('progress', 0)
                    
                    if stage == 'completed':
                        print(f"     ✅ {platform_name} 调用完成")
                        completed = True
                        break
                    elif stage == 'failed':
                        print(f"     ❌ {platform_name} 调用失败")
                        break
                    else:
                        print(f"     进度：{progress}% - {stage}")
            
            passed = completed
            print_result(f"{platform_name} AI 调用", passed)
            stage_results['total'] += 1
            if passed:
                stage_results['passed'] += 1
                
        except Exception as e:
            print_result(f"{platform_name} AI 调用", False, str(e))
            stage_results['total'] += 1
    
    # 打印阶段统计
    print_header("第二阶段测试统计")
    print(f"  通过：{stage_results['passed']}/{stage_results['total']} ({stage_results['passed']/stage_results['total']*100:.1f}%)")

# =============================================================================
# 第三阶段：端到端完整流程测试
# =============================================================================

def stage3_e2e_full_flow_test():
    """第三阶段：端到端完整流程测试"""
    print_header("第三阶段：端到端完整流程测试")
    
    stage_results = {'total': 0, 'passed': 0}
    TEST_RESULTS['stages']['stage3'] = stage_results
    
    print("\nT3.1: 单品牌单模型完整流程测试...")
    
    try:
        # 1. 提交诊断
        payload = {
            "brand_list": ["华为"],
            "selectedModels": [{"name": "deepseek", "checked": True}],
            "custom_question": "介绍一下华为公司"
        }
        
        print("     1. 提交诊断任务...")
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print_result("单品牌单模型流程", False, f"提交失败 ({response.status_code})")
            stage_results['total'] += 1
            return
        
        execution_id = response.json().get('execution_id')
        print(f"     ✅ 提交成功，执行 ID: {execution_id}")
        
        # 2. 轮询进度
        print("     2. 轮询进度...")
        max_retries = 30
        for i in range(max_retries):
            time.sleep(2)
            
            status_response = requests.get(
                f"{BASE_URL}/test/status/{execution_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                stage = status_data.get('stage', 'unknown')
                progress = status_data.get('progress', 0)
                
                if stage == 'completed':
                    print(f"     ✅ 诊断完成")
                    break
                elif stage == 'failed':
                    print(f"     ❌ 诊断失败")
                    break
                else:
                    print(f"       进度：{progress}% - {stage}")
        
        # 3. 获取结果
        print("     3. 获取诊断结果...")
        result_response = requests.get(
            f"{BASE_URL}/test/result/{execution_id}",
            timeout=30
        )
        
        if result_response.status_code == 200:
            result_data = result_response.json()
            has_results = 'results' in result_data and len(result_data['results']) > 0
            print_result("单品牌单模型流程", has_results, 
                        f"({len(result_data.get('results', []))} 条结果)")
            stage_results['total'] += 1
            if has_results:
                stage_results['passed'] += 1
        else:
            print_result("单品牌单模型流程", False, f"({result_response.status_code})")
            stage_results['total'] += 1
            
    except Exception as e:
        print_result("单品牌单模型流程", False, str(e))
        stage_results['total'] += 1
    
    # 打印阶段统计
    print_header("第三阶段测试统计")
    print(f"  通过：{stage_results['passed']}/{stage_results['total']} ({stage_results['passed']/stage_results['total']*100:.1f}%)")

# =============================================================================
# 第四阶段：前端页面联调测试
# =============================================================================

def stage4_frontend_integration():
    """第四阶段：前端页面联调测试"""
    print_header("第四阶段：前端页面联调测试")
    print("\n⚠️  注意：前端页面测试需要在微信开发者工具中手动执行")
    print("\n测试清单:")
    print("  [ ] 首页输入（品牌名称、竞品、AI 模型选择）")
    print("  [ ] 启动诊断按钮")
    print("  [ ] 加载进度显示 (0-100%)")
    print("  [ ] 阶段提示文字")
    print("  [ ] 错误提示弹窗")
    print("  [ ] 结果页面展示")
    print("  [ ] 缓存命中提示")
    print("\n请在微信开发者工具中执行以上测试并记录结果。")
    
    stage_results = {'total': 7, 'passed': 0}
    TEST_RESULTS['stages']['stage4'] = stage_results
    # 这些测试需要手动执行，暂时标记为未执行
    print(f"\n  待手动执行：7/7")

# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    print_header("端到端测试缺口实施执行")
    print(f"目标地址：{BASE_URL}")
    print(f"超时设置：{TIMEOUT}秒")
    
    # 检查服务状态
    if not check_service_status():
        return 1
    
    # 执行各阶段测试
    execution_id = stage1_backend_api_tests()
    stage2_real_ai_tests()
    stage3_e2e_full_flow_test()
    stage4_frontend_integration()
    
    # 打印总统计
    print_header("测试总结")
    total = TEST_RESULTS['total']
    passed = TEST_RESULTS['passed']
    failed = TEST_RESULTS['failed']
    
    print(f"  总测试数：{total}")
    print(f"  通过：{passed}")
    print(f"  失败：{failed}")
    if total > 0:
        print(f"  通过率：{(passed/total*100):.1f}%")
    
    # 保存测试结果
    test_report_file = os.path.join(os.path.dirname(__file__), 'test_execution_report.json')
    import json
    with open(test_report_file, 'w', encoding='utf-8') as f:
        json.dump(TEST_RESULTS, f, ensure_ascii=False, indent=2)
    print(f"\n  📄 测试报告已保存：{test_report_file}")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
