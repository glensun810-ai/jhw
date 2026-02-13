#!/usr/bin/env python3
"""
监控前端到后端的完整流程
"""

import json
import requests
import time
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

def monitor_test_progress(execution_id, max_duration=120):
    """监控测试进度"""
    print(f"\n📊 开始监控执行ID: {execution_id}")
    print(f"⏱️  最大监控时间: {max_duration}秒")
    
    start_time = time.time()
    last_progress = 0
    last_status = "unknown"
    
    while time.time() - start_time < max_duration:
        try:
            response = requests.get(
                f"http://127.0.0.1:5001/api/test-progress?executionId={execution_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                current_progress = data.get('progress', 0)
                current_status = data.get('status', 'unknown')
                
                # 只显进度变化
                if current_progress != last_progress or current_status != last_status:
                    print(f"   📈 进度: {current_progress}%, 状态: {current_status}")
                    last_progress = current_progress
                    last_status = current_status
                
                # 检查是否完成
                if current_status == 'completed':
                    print("   ✅ 测试完成!")
                    
                    # 打印关键结果
                    print(f"   📊 总体分数: {data.get('overallScore', 'N/A')}")
                    print(f"   🏆 总体等级: {data.get('overallGrade', 'N/A')}")
                    print(f"   📝 结果数量: {len(data.get('results', []))}")
                    print(f"   🏢 品牌分析: {len(data.get('competitiveAnalysis', {}).get('brandScores', {}))}")
                    
                    return True
                elif current_status == 'failed':
                    print(f"   ❌ 测试失败: {data.get('error', '未知错误')}")
                    return False
            
            time.sleep(2)  # 每2秒检查一次
            
        except Exception as e:
            print(f"   ⚠️  进度查询异常: {e}")
            time.sleep(2)
    
    print("   ⏰ 监控超时")
    return False


def run_complete_workflow_test():
    """运行完整的工作流程测试"""
    print("🚀 运行前端到后端完整工作流程测试")
    print("="*60)
    
    # 1. 准备测试数据
    print("\n1️⃣ 准备测试数据...")
    test_data = {
        "brand_list": ["蔚来汽车", "理想汽车"],
        "selectedModels": [
            {"name": "豆包", "checked": True, "logo": "DB", "tags": ["综合", "创意"]}
        ],
        "customQuestions": [
            "介绍一下{brandName}",
            "{brandName}的主要产品是什么？"
        ]
    }
    
    print(f"   📝 品牌: {test_data['brand_list']}")
    print(f"   🤖 模型: {[m['name'] for m in test_data['selectedModels']]}")
    print(f"   ❓ 问题: {len(test_data['customQuestions'])} 个")
    
    # 2. 发送请求
    print("\n2️⃣ 发送品牌测试请求...")
    try:
        response = requests.post(
            "http://127.0.0.1:5001/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status') == 'success':
                execution_id = response_data.get('executionId')
                print(f"   ✅ 请求成功，执行ID: {execution_id}")
                
                # 3. 监控进度
                print("\n3️⃣ 开始监控测试进度...")
                success = monitor_test_progress(execution_id)
                
                if success:
                    print("\n✅ 完整工作流程测试成功!")
                    return True
                else:
                    print("\n❌ 完整工作流程测试失败!")
                    return False
            else:
                print(f"   ❌ 后端处理失败: {response_data}")
                return False
        else:
            print(f"   ❌ API请求失败: {response.status_code}, {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return False


def test_specific_scenario():
    """测试特定场景 - 单一品牌，単一模型"""
    print("\n🎯 测试简化场景 (単一品牌，単一模型)...")
    
    test_data = {
        "brand_list": ["测试品牌"],
        "selectedModels": [
            {"name": "豆包", "checked": True}
        ],
        "customQuestions": [
            "介绍一下{brandName}"
        ]
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:5001/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status') == 'success':
                execution_id = response_data.get('executionId')
                print(f"   ✅ 简化场景请求成功，执行ID: {execution_id}")
                
                # 监控进度
                success = monitor_test_progress(execution_id, max_duration=180)  # 更长时间
                
                return success
            else:
                print(f"   ❌ 简化场景处理失败: {response_data}")
                return False
        else:
            print(f"   ❌ 简化场景API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 简化场景请求异常: {e}")
        return False


def main():
    """主函数"""
    print("🔍 微信小程序前端到后端完整流程监控测试")
    print("="*60)
    
    # 首先测试简化场景
    print("\n📋 首先测试简化场景...")
    simple_success = test_specific_scenario()
    
    if simple_success:
        print("\n✅ 简化场景测试成功，现在测试完整场景...")
        complete_success = run_complete_workflow_test()
    else:
        print("\n❌ 简化场景测试失败，跳过完整场景测试")
        complete_success = False
    
    print("\n" + "="*60)
    print("📊 最终测试结果:")
    print(f"   简化场景: {'✅ 通过' if simple_success else '❌ 失败'}")
    print(f"   完整场景: {'✅ 通过' if complete_success else '❌ 失败'}")
    
    if simple_success:
        print("\n🎉 至少简化场景工作正常，说明核心功能可用!")
        print("💡 如果完整场景失败，可能是由于:")
        print("   - 更多的API调用导致总时间较长")
        print("   - 竞品分析增加了处理时间")
        print("   - 资源限制导致的性能问题")
        return True
    else:
        print("\n❌ 连简化场景都无法正常工作，需要进一步排查!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)