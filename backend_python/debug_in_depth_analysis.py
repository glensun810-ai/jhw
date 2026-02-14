#!/usr/bin/env python3
"""
深入分析前端到后端流程的具体问题
"""

import json
import requests
import time
from datetime import datetime
import sys
import os
import threading

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_minimal_workflow():
    """测试最小化工作流程"""
    print("🔍 测试最小化工作流程...")
    
    # 使用最少的数据进行测试
    test_data = {
        "brand_list": ["测试品牌"],
        "selectedModels": [
            {"name": "豆包", "checked": True}
        ],
        "customQuestions": [
            "介绍一下{brandName}"
        ]
    }
    
    print(f"📊 测试数据: 1个品牌, 1个模型, 1个问题")
    
    try:
        print("📡 发送请求...")
        response = requests.post(
            "http://127.0.0.1:5001/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=30
        )
        
        print(f"📈 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"📋 响应数据: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
            
            if response_data.get('status') == 'success':
                execution_id = response_data.get('executionId')
                print(f"✅ 请求成功，执行ID: {execution_id}")
                
                # 立即检查进度
                print("\n🔍 立即检查初始进度...")
                progress_response = requests.get(
                    f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}",
                    timeout=10
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    print(f"📊 初始进度: {progress_data.get('progress', 0)}%")
                    print(f"📍 初始状态: {progress_data.get('status', 'unknown')}")
                    print(f"✅ 初始进度查询成功")
                    
                    # 持续监控直到完成或失败
                    print(f"\n⏳ 持续监控执行ID: {execution_id}")
                    start_time = time.time()
                    max_wait_time = 120  # 最多等待120秒
                    
                    while time.time() - start_time < max_wait_time:
                        progress_response = requests.get(
                            f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}",
                            timeout=10
                        )
                        
                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()
                            current_progress = progress_data.get('progress', 0)
                            current_status = progress_data.get('status', 'unknown')
                            
                            print(f"   📈 进度: {current_progress}%, 状态: {current_status}")
                            
                            if current_status == 'completed':
                                print("   ✅ 测试完成!")
                                
                                # 检查返回的关键数据
                                result_keys = ['overallScore', 'overallGrade', 'results', 'competitiveAnalysis']
                                for key in result_keys:
                                    if key in progress_data:
                                        if isinstance(progress_data[key], (list, dict)):
                                            print(f"   📊 {key}: {len(progress_data[key]) if isinstance(progress_data[key], (list, dict)) else 'N/A'} 项")
                                        else:
                                            print(f"   📊 {key}: {progress_data[key]}")
                                    else:
                                        print(f"   ⚠️  {key}: 缺失")
                                
                                return True
                            elif current_status == 'failed':
                                print(f"   ❌ 测试失败: {progress_data.get('error', '未知错误')}")
                                return False
                        else:
                            print(f"   ⚠️  进度查询失败: {progress_response.status_code}")
                        
                        time.sleep(2)  # 每2秒检查一次
                    
                    print("   ⏰ 监控超时")
                    return False
                else:
                    print(f"❌ 初始进度查询失败: {progress_response.status_code}")
                    return False
            else:
                print(f"❌ 后端处理失败: {response_data}")
                return False
        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"❌ 响应内容: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_backend_logs():
    """检查后端日志"""
    print("\n📋 检查后端日志...")
    
    # 尝试访问后端的健康检查端点
    try:
        health_response = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ 后端服务健康状态正常")
        else:
            print(f"⚠️  后端服务健康状态异常: {health_response.status_code}")
    except Exception as e:
        print(f"❌ 无法访问后端健康检查: {e}")
    
    # 尝试获取配置信息
    try:
        config_response = requests.get("http://127.0.0.1:5001/api/config", timeout=5)
        if config_response.status_code == 200:
            config_data = config_response.json()
            print(f"✅ 后端配置正常，应用ID: {config_data.get('app_id', 'N/A')}")
        else:
            print(f"⚠️  配置获取异常: {config_response.status_code}")
    except Exception as e:
        print(f"❌ 无法获取后端配置: {e}")


def analyze_frontend_request_format():
    """分析前端请求格式"""
    print("\n📱 分析前端请求格式...")
    
    # 模拟前端发送的典型请求
    typical_request = {
        "brand_list": ["蔚来汽车", "理想汽车"],
        "selectedModels": [
            {"name": "豆包", "checked": True, "logo": "DB", "tags": ["综合", "创意"]},
        ],
        "customQuestions": [
            "介绍一下{brandName}",
            "{brandName}的主要产品是什么？"
        ],
        # 前端可能还会发送的字段
        "userOpenid": "test_user_openid",  # 可能从前端会话获取
        "userLevel": "Free"  # 用户等级
    }
    
    print("✅ 前端请求格式分析完成")
    print(f"📊 请求字段: {list(typical_request.keys())}")
    print(f"📝 品牌数量: {len(typical_request['brand_list'])}")
    print(f"🤖 选中模型: {len(typical_request['selectedModels'])}")
    print(f"❓ 自定义问题: {len(typical_request['customQuestions'])}")


def main():
    """主函数"""
    print("🔍 前端到后端流程深入分析")
    print("="*60)
    
    # 分析前端请求格式
    analyze_frontend_request_format()
    
    # 检查后端状态
    check_backend_logs()
    
    # 测试最小化工作流程
    print("\n" + "="*60)
    minimal_success = test_minimal_workflow()
    
    print("\n" + "="*60)
    print("📊 最终分析结果:")
    print(f"   最小化流程测试: {'✅ 通过' if minimal_success else '❌ 失败'}")
    
    if minimal_success:
        print("\n✅ 系统核心功能正常!")
        print("💡 如果前端仍然显示失败，可能的原因:")
        print("   1. 前端超时设置过短")
        print("   2. 前端进度轮询逻辑问题")
        print("   3. 网络连接问题")
        print("   4. 微信小程序特定限制")
    else:
        print("\n❌ 系统核心功能存在问题!")
        print("💡 需要进一步排查后端处理逻辑")
    
    return minimal_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)