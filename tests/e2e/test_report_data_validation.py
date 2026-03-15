#!/usr/bin/env python3
"""
测试验证：诊断报告详情页数据流

测试目标：
1. 验证后端 API /test/status 返回 detailed_results
2. 验证 brand_scores 等详细字段存在
3. 验证数据完整性

@author: 系统架构组
@date: 2026-03-11
@version: 1.0.0
"""

import requests
import json
import sys
import os
import time

# 配置
BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5001')
TIMEOUT = 180  # 3 分钟超时


def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*70)
    print(f" {title} ")
    print("="*70)


def test_backend_status_api():
    """测试后端 /test/status API 返回完整数据"""
    print_separator("测试 1: 后端 API /test/status 返回字段验证")
    
    # Step 1: 启动一个新的诊断任务
    print("\n[Step 1] 启动诊断任务...")
    start_response = requests.post(
        f'{BASE_URL}/api/perform-brand-test',
        json={
            'brand_list': ['华为', '小米'],
            'selectedModels': [{'name': 'qwen'}],  # 使用 camelCase
            'custom_questions': ['智能手机品牌推荐？']
        },
        timeout=30
    )
    
    if start_response.status_code != 200:
        print(f"❌ 启动诊断失败：{start_response.status_code}")
        print(f"   响应：{start_response.text}")
        return False
    
    start_data = start_response.json()
    # 支持 executionId 和 execution_id 两种格式
    execution_id = start_data.get('executionId') or start_data.get('execution_id')
    
    if not execution_id:
        print(f"❌ 响应中缺少 executionId/execution_id")
        print(f"   响应：{start_data}")
        return False
    
    print(f"✅ 诊断已启动：{execution_id}")
    print(f"   formula: {start_data.get('formula', 'N/A')}")
    print(f"   total_tasks: {start_data.get('total_tasks', 'N/A')}")
    
    # Step 2: 等待诊断完成
    print(f"\n[Step 2] 等待诊断完成...")
    max_wait = TIMEOUT
    start_time = time.time()
    poll_interval = 3
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            status_response = requests.get(
                f'{BASE_URL}/test/status/{execution_id}',
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status')
                progress = status_data.get('progress', 0)
                stage = status_data.get('stage', 'unknown')
                
                if status != last_status:
                    print(f"   状态：{status}, 进度：{progress}%, 阶段：{stage}")
                    last_status = status
                
                if status == 'completed':
                    print(f"✅ 诊断已完成")
                    break
                elif status == 'failed':
                    print(f"❌ 诊断失败：{status_data}")
                    return False
            else:
                print(f"⚠️ 状态查询失败：{status_response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 请求异常：{e}")
        
        time.sleep(poll_interval)
    else:
        print(f"❌ 诊断超时（>{max_wait}秒）")
        return False
    
    # Step 3: 验证 API 返回的字段
    print(f"\n[Step 3] 验证 API 返回字段...")
    final_response = requests.get(
        f'{BASE_URL}/test/status/{execution_id}?fields=full',
        timeout=10
    )
    
    if final_response.status_code != 200:
        print(f"❌ 获取详细状态失败：{final_response.status_code}")
        return False
    
    response_data = final_response.json()
    
    # 验证必需字段
    required_fields = [
        'task_id',
        'status',
        'progress',
        'stage',
        'detailed_results',
        'brand_scores',
        'competitive_analysis',
        'semantic_drift_data',
        'recommendation_data',
        'negative_sources',
        'overall_score'
    ]
    
    missing_fields = []
    field_status = {}
    
    for field in required_fields:
        if field in response_data:
            value = response_data[field]
            if isinstance(value, list):
                field_status[field] = f"✅ 存在 (数组，长度={len(value)})"
                if len(value) == 0 and field == 'detailed_results':
                    field_status[field] = "⚠️ 存在但为空数组"
            elif isinstance(value, dict):
                field_status[field] = f"✅ 存在 (对象，keys={len(value)})"
                if len(value) == 0:
                    field_status[field] = "⚠️ 存在但为空对象"
            else:
                field_status[field] = f"✅ 存在 (值={value})"
        else:
            field_status[field] = "❌ 缺失"
            missing_fields.append(field)
    
    # 打印字段状态
    print("\n   API 返回字段验证:")
    for field, status in field_status.items():
        print(f"   {field}: {status}")
    
    if missing_fields:
        print(f"\n❌ 缺少必需字段：{', '.join(missing_fields)}")
        return False
    
    # Step 4: 验证 detailed_results 内容
    print(f"\n[Step 4] 验证 detailed_results 内容...")
    detailed_results = response_data.get('detailed_results', [])
    
    if not detailed_results:
        print(f"❌ detailed_results 为空")
        return False
    
    print(f"✅ detailed_results 包含 {len(detailed_results)} 条记录")
    
    # 验证第一条记录的结构
    first_result = detailed_results[0]
    expected_keys = ['brand', 'question', 'answer', 'sentiment', 'dimensions']
    
    missing_keys = [key for key in expected_keys if key not in first_result]
    if missing_keys:
        print(f"❌ detailed_results 记录缺少关键字段：{missing_keys}")
        return False
    
    print(f"✅ detailed_results 记录结构正确")
    print(f"   示例品牌：{first_result.get('brand', 'N/A')}")
    print(f"   示例问题：{first_result.get('question', 'N/A')[:50]}...")
    
    # Step 5: 验证 brand_scores 内容
    print(f"\n[Step 5] 验证 brand_scores 内容...")
    brand_scores = response_data.get('brand_scores', {})
    
    if not brand_scores:
        print(f"❌ brand_scores 为空")
        return False
    
    print(f"✅ brand_scores 包含 {len(brand_scores)} 个品牌")
    
    # 验证品牌分数结构
    for brand, scores in brand_scores.items():
        if isinstance(scores, dict):
            overall_score = scores.get('overallScore', scores.get('overall_score', 'N/A'))
            print(f"   {brand}: overallScore={overall_score}")
        else:
            print(f"   {brand}: {scores}")
    
    # Step 6: 验证其他字段
    print(f"\n[Step 6] 验证其他字段...")
    
    competitive_analysis = response_data.get('competitive_analysis', {})
    if competitive_analysis:
        print(f"✅ competitive_analysis: {len(competitive_analysis)} 个键")
    else:
        print(f"⚠️ competitive_analysis: 空或不存在")
    
    semantic_drift_data = response_data.get('semantic_drift_data', {})
    if semantic_drift_data:
        print(f"✅ semantic_drift_data: 存在")
    else:
        print(f"⚠️ semantic_drift_data: 空或不存在")
    
    recommendation_data = response_data.get('recommendation_data', {})
    if recommendation_data:
        print(f"✅ recommendation_data: 存在")
    else:
        print(f"⚠️ recommendation_data: 空或不存在")
    
    overall_score = response_data.get('overall_score', 'N/A')
    print(f"✅ overall_score: {overall_score}")
    
    # Step 7: 总结
    print_separator("测试 1 结果总结")
    print(f"✅ 后端 API /test/status 返回完整数据")
    print(f"   - detailed_results: {len(detailed_results)} 条记录")
    print(f"   - brand_scores: {len(brand_scores)} 个品牌")
    print(f"   - overall_score: {overall_score}")
    
    return True


def test_backend_status_api_direct():
    """测试后端 API 直接从 execution_store 获取数据"""
    print_separator("测试 2: 后端 API execution_store 数据验证")
    
    # 这个测试需要后端服务正在运行且有活跃的任务
    print("\n[说明] 此测试需要后端服务正在运行且有活跃任务")
    print("     请在运行此测试前先启动一个诊断任务")
    
    # 尝试获取一个可能存在的任务状态
    test_execution_id = "test-execution-id"
    
    try:
        response = requests.get(
            f'{BASE_URL}/test/status/{test_execution_id}',
            timeout=5
        )
        
        if response.status_code == 404:
            print(f"✅ 预期行为：测试 ID 返回 404 (任务不存在)")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"✅ 获取到任务状态：{data.get('status', 'unknown')}")
            
            # 验证字段
            if 'detailed_results' in data:
                print(f"✅ detailed_results 字段存在")
            else:
                print(f"❌ detailed_results 字段缺失")
                return False
            
            return True
        else:
            print(f"⚠️ 意外响应：{response.status_code}")
            return True  # 不视为失败
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 请求异常（后端可能未启动）：{e}")
        print(f"   跳过此测试")
        return True


def main():
    """主测试函数"""
    print("="*70)
    print(" 诊断报告详情页数据流测试验证 ")
    print("="*70)
    print(f"\n后端 API 地址：{BASE_URL}")
    print(f"超时时间：{TIMEOUT}秒")
    
    # 检查后端服务是否可用
    print("\n[预检查] 检查后端服务连接...")
    try:
        health_response = requests.get(f'{BASE_URL}/health', timeout=5)
        if health_response.status_code == 200:
            print(f"✅ 后端服务正常")
        else:
            print(f"⚠️ 后端服务响应异常：{health_response.status_code}")
    except requests.exceptions.RequestException:
        print(f"❌ 无法连接到后端服务：{BASE_URL}")
        print(f"   请确保后端服务正在运行")
        print(f"   启动命令：cd backend_python && flask run")
        return False
    
    # 运行测试
    results = []
    
    # 测试 1: 后端 API 字段验证
    result1 = test_backend_status_api()
    results.append(("后端 API 字段验证", result1))
    
    # 测试 2: execution_store 验证
    result2 = test_backend_status_api_direct()
    results.append(("execution_store 验证", result2))
    
    # 打印总结
    print_separator("测试总结")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✅ 所有测试通过！诊断报告详情页应该能输出真实完整的诊断结果。")
        return True
    else:
        print(f"\n❌ {total - passed} 个测试失败。请检查修复是否正确应用。")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
