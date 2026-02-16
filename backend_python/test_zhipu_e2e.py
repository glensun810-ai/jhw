import requests
import time
import json
import sys

# 配置
BASE_URL = 'http://127.0.0.1:5000'
BRAND_NAME = "清华大学"
PLATFORM_NAME = "智谱AI"

def test_zhipu_e2e():
    print(f"=== 开始测试 {PLATFORM_NAME} 端到端流程 ===")
    
    # 1. 发起诊断请求
    print(f"\n[1] 发起诊断请求: 品牌={BRAND_NAME}, 平台={PLATFORM_NAME}")
    payload = {
        "brand_list": [BRAND_NAME],
        "selectedModels": [{"name": PLATFORM_NAME, "checked": True}],
        "customQuestions": ["介绍一下{brandName}"],
        "userOpenid": "test_user_001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/perform-brand-test", json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            execution_id = data.get('executionId')
            print(f"SUCCESS: 请求已提交，Execution ID: {execution_id}")
        else:
            print(f"FAILURE: 请求提交失败: {data}")
            return
            
    except Exception as e:
        print(f"FAILURE: 网络请求错误: {e}")
        return

    # 2. 轮询进度
    print(f"\n[2] 开始轮询进度...")
    max_retries = 60
    for i in range(max_retries):
        try:
            progress_response = requests.get(f"{BASE_URL}/api/test-progress?executionId={execution_id}")
            progress_data = progress_response.json()
            
            status = progress_data.get('status')
            progress = progress_data.get('progress')
            
            sys.stdout.write(f"\r进度: {progress}% ({status})")
            sys.stdout.flush()
            
            if status == 'completed':
                print("\nSUCCESS: 诊断完成！")
                verify_results(progress_data)
                return
            elif status == 'failed':
                print(f"\nFAILURE: 诊断失败: {progress_data.get('error')}")
                return
            
            time.sleep(1)
            
        except Exception as e:
            print(f"\nFAILURE: 轮询请求错误: {e}")
            return
            
    print("\nFAILURE: 测试超时")

def verify_results(data):
    print(f"\n[3] 验证结果数据...")
    
    results = data.get('results', [])
    if not results:
        print("FAILURE: 结果列表为空")
        return

    zhipu_result = None
    for res in results:
        # 检查是否包含智谱AI的结果 (注意：后端返回的 aiModel 可能是 'GLM-4' 或 '智谱AI'，取决于适配器实现)
        if 'GLM' in res.get('aiModel', '') or '智谱' in res.get('aiModel', ''):
            zhipu_result = res
            break
    
    if zhipu_result:
        print(f"SUCCESS: 找到 {PLATFORM_NAME} 的诊断结果")
        print(f"  - 模型: {zhipu_result.get('aiModel')}")
        print(f"  - 评分: {zhipu_result.get('score')}")
        print(f"  - 回复长度: {len(zhipu_result.get('response', ''))}")
        print(f"  - 回复预览: {zhipu_result.get('response', '')[:50]}...")
        
        if zhipu_result.get('success'):
             print("SUCCESS: 诊断状态为成功")
        else:
             print(f"FAILURE: 诊断状态为失败: {zhipu_result.get('error_message')}")

    else:
        print(f"FAILURE: 未找到 {PLATFORM_NAME} 的诊断结果")
        print(f"实际返回的模型列表: {[r.get('aiModel') for r in results]}")

if __name__ == "__main__":
    test_zhipu_e2e()
