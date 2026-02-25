#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试脚本
验证 P0/P1 优化效果

测试场景:
1. 小型：1 品牌 × 3 问题 × 2 模型 = 6 次 AI 调用
2. 中型：3 品牌 × 3 问题 × 4 模型 = 36 次 AI 调用
3. 大型：5 品牌 × 5 问题 × 6 模型 = 150 次 AI 调用

性能目标（优化后）:
- 小型：从 90 秒降至 25 秒（72% 提升）
- 中型：从 540 秒降至 120 秒（78% 提升）
- 大型：从 2250 秒降至 450 秒（80% 提升）
"""

import time
import json
import requests
from typing import Dict, Any, List
from datetime import datetime

BASE_URL = "http://127.0.0.1:5001"

# 测试配置
TEST_SCENARIOS = [
    {
        "name": "小型测试",
        "brand_list": ["测试品牌"],
        "selected_models": ["doubao", "qwen"],
        "custom_question": "这个品牌怎么样",
        "expected_ai_calls": 6  # 1 品牌 × 3 问题 × 2 模型
    },
    {
        "name": "中型测试",
        "brand_list": ["品牌 A", "品牌 B", "品牌 C"],
        "selected_models": ["doubao", "qwen", "deepseek", "zhipu"],
        "custom_question": "分析这个品牌的特点和竞争优势",
        "expected_ai_calls": 36  # 3 品牌 × 3 问题 × 4 模型
    }
]


class PerformanceBenchmark:
    """性能基准测试器"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: List[Dict[str, Any]] = []
    
    def check_health(self) -> bool:
        """检查后端健康"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ 后端健康检查通过")
                return True
            else:
                print(f"❌ 后端健康检查失败：{response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接后端：{e}")
            return False
    
    def run_benchmark(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个基准测试"""
        print(f"\n{'='*60}")
        print(f"开始测试：{scenario['name']}")
        print(f"{'='*60}")
        print(f"品牌数：{len(scenario['brand_list'])}")
        print(f"模型数：{len(scenario['selected_models'])}")
        print(f"预期 AI 调用次数：{scenario['expected_ai_calls']}")
        
        # 启动诊断
        start_time = time.time()
        
        url = f"{self.base_url}/api/perform-brand-test"
        payload = {
            "brand_list": scenario["brand_list"],
            "selectedModels": scenario["selected_models"],
            "custom_question": scenario["custom_question"]
        }
        
        print(f"\n启动诊断任务...")
        response = self.session.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ 启动失败：{response.status_code}")
            return {
                "name": scenario["name"],
                "success": False,
                "error": f"启动失败：{response.status_code}"
            }
        
        execution_id = response.json().get("execution_id")
        print(f"✅ 任务启动成功：{execution_id}")
        
        # 轮询状态
        print(f"\n开始轮询任务状态...")
        poll_count = 0
        max_polls = 300  # 最多轮询 300 次（5 分钟）
        poll_interval = 1  # 初始间隔 1 秒
        
        last_poll_time = time.time()
        completion_time = None
        
        while poll_count < max_polls:
            poll_start = time.time()
            
            try:
                status_url = f"{self.base_url}/test/status/{execution_id}"
                response = self.session.get(status_url, timeout=10)
                
                if response.status_code != 200:
                    print(f"⚠️  轮询失败：{response.status_code}")
                    poll_count += 1
                    time.sleep(poll_interval)
                    continue
                
                data = response.json()
                stage = data.get("stage", "unknown")
                progress = data.get("progress", 0)
                results_count = len(data.get("detailed_results", []) or data.get("results", []))
                
                poll_time = time.time() - poll_start
                elapsed = time.time() - start_time
                
                print(f"[{elapsed:6.1f}s] 轮询 {poll_count+1:3d} | "
                      f"Stage: {stage:20s} | Progress: {progress:3d}% | "
                      f"Results: {results_count} | RT: {poll_time*1000:.0f}ms")
                
                # 检查完成
                if stage in ["completed", "finished", "done", "partial_completed"]:
                    completion_time = time.time() - start_time
                    print(f"\n✅ 任务完成！总耗时：{completion_time:.1f}秒")
                    break
                
                if stage == "failed":
                    print(f"\n❌ 任务失败：{data.get('error', '未知错误')}")
                    break
                
                # 动态调整轮询间隔
                if progress < 10:
                    poll_interval = 0.8
                elif progress < 30:
                    poll_interval = 0.5
                elif progress < 70:
                    poll_interval = 0.4
                elif progress < 90:
                    poll_interval = 0.3
                else:
                    poll_interval = 0.2
                
                poll_count += 1
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"⚠️  轮询异常：{e}")
                poll_count += 1
                time.sleep(poll_interval)
        
        total_time = time.time() - start_time
        
        # 计算性能指标
        result = {
            "name": scenario["name"],
            "success": completion_time is not None,
            "total_time": total_time,
            "completion_time": completion_time,
            "poll_count": poll_count,
            "expected_ai_calls": scenario["expected_ai_calls"],
            "ai_calls_per_second": scenario["expected_ai_calls"] / completion_time if completion_time else 0
        }
        
        self.results.append(result)
        return result
    
    def print_summary(self):
        """打印性能摘要"""
        print(f"\n{'='*70}")
        print("性能基准测试摘要")
        print(f"{'='*70}")
        
        for result in self.results:
            if not result["success"]:
                print(f"❌ {result['name']}: 失败")
                continue
            
            print(f"\n{result['name']}:")
            print(f"  总耗时：{result['total_time']:.1f}秒")
            print(f"  完成时间：{result['completion_time']:.1f}秒")
            print(f"  轮询次数：{result['poll_count']}")
            print(f"  AI 调用速率：{result['ai_calls_per_second']:.2f} 次/秒")
            
            # 性能对比
            expected_ai_calls = result["expected_ai_calls"]
            
            # 优化前（串行）
            serial_time = expected_ai_calls * 15  # 假设每次 AI 调用 15 秒
            
            # 优化后（并发，5 路）
            concurrent_time = (expected_ai_calls / 5) * 15
            
            # 实际性能
            actual_time = result["completion_time"]
            
            improvement_vs_serial = (1 - actual_time / serial_time) * 100
            improvement_vs_concurrent = (1 - actual_time / concurrent_time) * 100
            
            print(f"\n  性能对比:")
            print(f"    优化前（串行）：{serial_time:.0f}秒")
            print(f"    理论并发（5 路）：{concurrent_time:.0f}秒")
            print(f"    实际：{actual_time:.1f}秒")
            print(f"    提升（vs 串行）：{improvement_vs_serial:.1f}%")
            print(f"    达成率（vs 理论）：{(1-improvement_vs_concurrent)*100:.1f}%")
        
        print(f"\n{'='*70}")


def main():
    print("="*70)
    print("品牌诊断系统 - 性能基准测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    benchmark = PerformanceBenchmark()
    
    # 健康检查
    if not benchmark.check_health():
        print("\n❌ 后端服务未运行，无法进行测试")
        return
    
    # 运行测试
    for scenario in TEST_SCENARIOS:
        result = benchmark.run_benchmark(scenario)
        time.sleep(2)  # 测试间隔
    
    # 打印摘要
    benchmark.print_summary()
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"benchmark_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "results": benchmark.results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试结果已保存到：{output_file}")


if __name__ == '__main__':
    main()
