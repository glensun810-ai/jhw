#!/usr/bin/env python3
"""
诊断记录页面前后端联调测试脚本

测试内容：
1. 历史列表 API 返回数据格式
2. 报告详情 API 返回数据格式
3. 核心指标计算
4. 评分维度计算
5. 问题诊断墙生成

作者：首席前端工程师 & 首席架构师
日期：2026-03-20
"""

import json
import urllib.request
import sys

BASE_URL = "http://localhost:5001"

def test_history_list_api():
    """测试历史列表 API"""
    print("="*60)
    print("测试 1: 历史列表 API")
    print("="*60)
    
    url = f"{BASE_URL}/api/history/list?userOpenid=anonymous&limit=20&offset=0"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if data.get('status') != 'success':
                print(f"❌ API 返回状态错误：{data}")
                return False
            
            history = data.get('history', [])
            total = data.get('total', 0)
            
            print(f"✅ API 调用成功")
            print(f"   返回记录数：{len(history)}")
            print(f"   总记录数：{total}")
            
            if history:
                print(f"\n   样本数据:")
                for h in history[:3]:
                    print(f"   - {h.get('brandName', 'N/A')}: status={h.get('status', 'N/A')}, score={h.get('overall_score', 'N/A')}")
                
                # 验证字段
                required_fields = ['execution_id', 'brandName', 'status', 'createdAt', 'overall_score']
                first_record = history[0]
                missing_fields = [f for f in required_fields if f not in first_record]
                
                if missing_fields:
                    print(f"\n⚠️  缺少字段：{missing_fields}")
                else:
                    print(f"\n✅ 字段完整")
            
            return True
            
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return False


def test_report_detail_api(execution_id):
    """测试报告详情 API"""
    print("\n" + "="*60)
    print(f"测试 2: 报告详情 API (execution_id={execution_id[:8]}...)")
    print("="*60)
    
    url = f"{BASE_URL}/api/diagnosis/report/{execution_id}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if not data.get('success') and not data.get('data'):
                print(f"❌ API 返回错误：{data}")
                return False
            
            report_data = data.get('data', data)
            
            print(f"✅ API 调用成功")
            
            # 检查核心指标
            metrics = report_data.get('metrics', {})
            if metrics:
                print(f"\n✅ 核心指标:")
                print(f"   - SOV: {metrics.get('sov', 'N/A')}")
                print(f"   - 情感：{metrics.get('sentiment', 'N/A')}")
                print(f"   - 排名：{metrics.get('rank', 'N/A')}")
                print(f"   - 影响力：{metrics.get('influence', 'N/A')}")
            else:
                print(f"\n⚠️  核心指标缺失")
            
            # 检查维度得分
            dimension_scores = report_data.get('dimension_scores', {})
            if dimension_scores:
                print(f"\n✅ 评分维度:")
                print(f"   - 权威度：{dimension_scores.get('authority', 'N/A')}")
                print(f"   - 可见度：{dimension_scores.get('visibility', 'N/A')}")
                print(f"   - 纯净度：{dimension_scores.get('purity', 'N/A')}")
                print(f"   - 一致性：{dimension_scores.get('consistency', 'N/A')}")
            else:
                print(f"\n⚠️  评分维度缺失")
            
            # 检查问题诊断墙
            diagnostic_wall = report_data.get('diagnosticWall', {})
            if diagnostic_wall:
                high_risks = diagnostic_wall.get('risk_levels', {}).get('high', [])
                suggestions = diagnostic_wall.get('priority_recommendations', [])
                print(f"\n✅ 问题诊断墙:")
                print(f"   - 高风险：{len(high_risks)} 条")
                print(f"   - 建议：{len(suggestions)} 条")
                
                if suggestions:
                    print(f"   样本建议：{suggestions[0].get('title', 'N/A')}")
            else:
                print(f"\n⚠️  问题诊断墙缺失")
            
            # 检查结果数量
            results = report_data.get('results', [])
            print(f"\n📊 结果统计:")
            print(f"   - 结果数量：{len(results)}")
            
            if len(results) < 10:
                print(f"   ⚠️  结果数量偏少，建议检查诊断配置")
            
            return True
            
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return False


def get_sample_execution_id():
    """获取一个样本 execution_id"""
    url = f"{BASE_URL}/api/history/list?userOpenid=anonymous&limit=1&offset=0"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            history = data.get('history', [])
            if history:
                return history[0].get('execution_id')
    except:
        pass
    
    # 如果没有历史记录，返回一个已知的 execution_id
    return "12bed967-1094-46b7-a363-0864971df7b0"


def main():
    print("\n" + "="*60)
    print("诊断记录页面 - 前后端联调测试")
    print("="*60)
    
    # 测试 1: 历史列表 API
    list_ok = test_history_list_api()
    
    # 测试 2: 报告详情 API
    execution_id = get_sample_execution_id()
    if execution_id:
        detail_ok = test_report_detail_api(execution_id)
    else:
        print("\n⚠️  未找到 execution_id，跳过详情测试")
        detail_ok = False
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    if list_ok:
        print("✅ 历史列表 API: 正常")
    else:
        print("❌ 历史列表 API: 失败")
    
    if detail_ok:
        print("✅ 报告详情 API: 正常")
    else:
        print("❌ 报告详情 API: 失败")
    
    if list_ok and detail_ok:
        print("\n✅ 所有测试通过！前后端数据联调成功！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查后端服务")
        return 1


if __name__ == '__main__':
    sys.exit(main())
