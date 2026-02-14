#!/usr/bin/env python3
"""
验证AI平台集成
"""
import os
import sys
import time
import requests
import json

def test_ai_integration():
    """测试AI平台集成"""
    print("🔍 验证AI平台集成...\n")
    
    # 测试数据
    test_payload = {
        "brand_list": ["苹果"],
        "selectedModels": [
            {"name": "deepseek", "displayName": "DeepSeek"},
            {"name": "qwen", "displayName": "通义千问"}
        ],
        "customQuestions": [
            "介绍一下{brandName}的主要产品",
            "{brandName}的核心竞争力是什么"
        ],
        "apiKey": ""
    }
    
    # 发送测试请求
    url = "http://127.0.0.1:5001/api/perform-brand-test"
    print(f"📤 发送品牌测试请求到: {url}")
    
    try:
        response = requests.post(url, json=test_payload, timeout=120)
        print(f"✅ HTTP响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
            
            if result.get('status') == 'success':
                execution_id = result.get('executionId')
                print(f"🆔 执行ID: {execution_id}")
                
                # 轮询进度
                progress_url = f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}"
                print(f"\n🔄 开始轮询进度: {progress_url}")
                
                for i in range(30):  # 最多轮询30次
                    time.sleep(3)
                    try:
                        progress_response = requests.get(progress_url, timeout=30)
                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()
                            progress = progress_data.get('progress', 0)
                            completed = progress_data.get('completed', 0)
                            total = progress_data.get('total', 0)
                            
                            print(f"📊 进度: {progress}% ({completed}/{total})")
                            
                            if progress >= 100:
                                print("\n🎉 AI平台集成测试完成!")
                                print(f"📈 总体分数: {progress_data.get('overallScore', 'N/A')}")
                                print(f"🏆 总体等级: {progress_data.get('overallGrade', 'N/A')}")
                                
                                results = progress_data.get('results', [])
                                print(f"\n📝 结果详情:")
                                
                                success_count = 0
                                for idx, result in enumerate(results):
                                    print(f"\n  {idx+1}. {result.get('aiModel', 'N/A')} - {result.get('brand', 'N/A')}")
                                    print(f"     成功: {result.get('success', 'N/A')}")
                                    
                                    if result.get('success'):
                                        success_count += 1
                                        print(f"     分数: {result.get('score', 'N/A')}")
                                        print(f"     响应长度: {len(result.get('response', ''))} 字符")
                                    else:
                                        print(f"     错误: {result.get('error_message', 'N/A')[:100]}...")
                                
                                print(f"\n✅ 成功完成 {success_count}/{len(results)} 个AI平台调用")
                                return True
                        else:
                            print(f"❌ 进度查询失败，状态码: {progress_response.status_code}")
                            break
                    except Exception as e:
                        print(f"❌ 进度查询异常: {e}")
                        break
            else:
                print(f"❌ 请求失败: {result}")
        else:
            print(f"❌ HTTP请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        print("💡 提示: 运行 'python3 main.py' 启动服务器")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    return False

def check_api_keys():
    """检查API密钥配置"""
    print("\n🔐 检查API密钥配置...")
    
    required_keys = ['DEEPSEEK_API_KEY', 'QWEN_API_KEY', 'DOUBAO_API_KEY']
    for key in required_keys:
        value = os.getenv(key)
        if value:
            print(f"  ✅ {key}: {value[:8]}...{'*' * (len(value)-8) if len(value) > 8 else ''}")
        else:
            print(f"  ❌ {key}: 未设置")

def main():
    """主函数"""
    print("🚀 开始验证AI平台集成...\n")
    
    # 检查API密钥
    check_api_keys()
    
    # 测试AI集成
    success = test_ai_integration()
    
    if success:
        print("\n✅ AI平台集成验证成功！")
        print("🎉 应用程序现在可以调用真实的AI搜索平台进行品牌诊断")
    else:
        print("\n❌ AI平台集成验证失败")
        print("⚠️  可能需要检查API密钥或服务器配置")

if __name__ == "__main__":
    main()