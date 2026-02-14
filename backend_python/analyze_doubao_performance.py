#!/usr/bin/env python3
"""
豆包API性能分析报告生成器
分析请求/响应时间，为系统参数优化提供数据支持
"""

import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def load_records(log_file: str = None) -> List[Dict]:
    """加载AI响应记录"""
    if log_file is None:
        log_file = Path(__file__).parent / "data" / "ai_responses" / "ai_responses.jsonl"
    else:
        log_file = Path(log_file)
    
    records = []
    if not log_file.exists():
        return records
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # 只分析豆包的成功记录
                if (record.get('platform') == '豆包' or 
                    record.get('platform', {}).get('name') == '豆包') and \
                   (record.get('success') or record.get('status', {}).get('success')):
                    records.append(record)
            except json.JSONDecodeError:
                continue
    
    return records


def analyze_latency(records: List[Dict]) -> Dict[str, Any]:
    """分析延迟数据"""
    # 提取延迟数据（支持V1和V2格式）
    latencies = []
    for r in records:
        latency = r.get('latency_ms')
        if latency is None:
            latency = r.get('performance', {}).get('latency_ms')
        if latency:
            latencies.append(latency)
    
    if not latencies:
        return {}
    
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    return {
        "count": n,
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "stdev_ms": round(statistics.stdev(latencies), 2) if n > 1 else 0,
        "p50_ms": sorted_latencies[int(n * 0.5)],
        "p75_ms": sorted_latencies[int(n * 0.75)],
        "p90_ms": sorted_latencies[int(n * 0.9)],
        "p95_ms": sorted_latencies[int(n * 0.95)],
        "p99_ms": sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1],
    }


def analyze_tokens(records: List[Dict]) -> Dict[str, Any]:
    """分析Token使用情况"""
    tokens_list = []
    for r in records:
        tokens = r.get('tokens_used')
        if tokens is None:
            tokens = r.get('performance', {}).get('tokens', {}).get('total')
        if tokens:
            tokens_list.append(tokens)
    
    if not tokens_list:
        return {}
    
    return {
        "count": len(tokens_list),
        "min": min(tokens_list),
        "max": max(tokens_list),
        "mean": round(statistics.mean(tokens_list), 2),
        "median": round(statistics.median(tokens_list), 2),
        "total": sum(tokens_list)
    }


def analyze_response_length(records: List[Dict]) -> Dict[str, Any]:
    """分析响应文本长度"""
    lengths = []
    for r in records:
        response = r.get('response', '')
        if isinstance(response, dict):
            response = response.get('text', '')
        if response:
            lengths.append(len(response))
    
    if not lengths:
        return {}
    
    return {
        "count": len(lengths),
        "min_chars": min(lengths),
        "max_chars": max(lengths),
        "mean_chars": round(statistics.mean(lengths), 2),
        "median_chars": round(statistics.median(lengths), 2),
    }


def calculate_throughput(latency_stats: Dict, token_stats: Dict) -> Dict[str, float]:
    """计算吞吐量指标"""
    if not latency_stats or not token_stats:
        return {}
    
    mean_latency_sec = latency_stats['mean_ms'] / 1000
    
    return {
        "tokens_per_second": round(token_stats['mean'] / mean_latency_sec, 2),
        "chars_per_second": round(1500 / mean_latency_sec, 2),  # 假设平均1500字符
        "requests_per_minute": round(60 / mean_latency_sec, 2)
    }


def generate_recommendations(latency_stats: Dict, token_stats: Dict) -> List[str]:
    """生成系统参数优化建议"""
    recommendations = []
    
    if not latency_stats:
        return ["暂无足够数据生成建议"]
    
    mean_latency = latency_stats['mean_ms']
    p95_latency = latency_stats['p95_ms']
    max_latency = latency_stats['max_ms']
    
    # 超时设置建议
    recommended_timeout = int(p95_latency * 1.2 / 1000) + 5  # P95的120% + 5秒缓冲
    recommendations.append(
        f"【超时设置】建议将API超时时间设置为 {recommended_timeout} 秒 "
        f"(当前平均延迟: {mean_latency/1000:.1f}s, P95: {p95_latency/1000:.1f}s, 最大值: {max_latency/1000:.1f}s)"
    )
    
    # 健康检查建议
    health_check_timeout = int(latency_stats['p50_ms'] * 2 / 1000)
    recommendations.append(
        f"【健康检查】建议健康检查超时设置为 {health_check_timeout} 秒 "
        f"(基于P50延迟: {latency_stats['p50_ms']/1000:.1f}s)"
    )
    
    # 并发控制建议
    if mean_latency > 30000:  # 平均超过30秒
        recommendations.append(
            f"【并发控制】平均延迟较高({mean_latency/1000:.1f}s)，建议降低并发请求数量，"
            f"或使用队列机制顺序处理"
        )
    
    # 熔断器建议
    circuit_breaker_threshold = int(p95_latency * 1.5)
    recommendations.append(
        f"【熔断器设置】建议熔断器触发阈值设置为 {circuit_breaker_threshold/1000:.1f} 秒 "
        f"(P95的150%)"
    )
    
    # 重试策略建议
    if latency_stats['stdev_ms'] / mean_latency > 0.3:  # 变异系数大于30%
        recommendations.append(
            f"【重试策略】延迟波动较大(CV: {latency_stats['stdev_ms']/mean_latency:.1%})，"
            f"建议启用指数退避重试，初始间隔 5 秒"
        )
    else:
        recommendations.append(
            f"【重试策略】延迟相对稳定，可使用固定间隔重试，间隔 10 秒"
        )
    
    # Token相关建议
    if token_stats:
        mean_tokens = token_stats['mean']
        recommendations.append(
            f"【Token限制】平均消耗 {mean_tokens:.0f} tokens，建议 max_tokens 设置为 "
            f"{int(mean_tokens * 1.5)} (平均值的150%)"
        )
    
    # 用户体验建议
    if mean_latency > 20000:
        recommendations.append(
            f"【用户体验】平均响应时间 {mean_latency/1000:.1f} 秒较长，"
            f"建议前端添加进度提示或改用异步处理+轮询模式"
        )
    
    return recommendations


def print_analysis_report(records: List[Dict]):
    """打印分析报告"""
    print("=" * 80)
    print("豆包API性能分析报告")
    print("=" * 80)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"样本数量: {len(records)} 条成功记录")
    print()
    
    # 延迟分析
    print("-" * 80)
    print("【延迟分析】")
    print("-" * 80)
    latency_stats = analyze_latency(records)
    if latency_stats:
        print(f"  样本数: {latency_stats['count']}")
        print(f"  最小值: {latency_stats['min_ms']/1000:.2f} 秒")
        print(f"  最大值: {latency_stats['max_ms']/1000:.2f} 秒")
        print(f"  平均值: {latency_stats['mean_ms']/1000:.2f} 秒")
        print(f"  中位数: {latency_stats['median_ms']/1000:.2f} 秒")
        print(f"  标准差: {latency_stats['stdev_ms']/1000:.2f} 秒")
        print()
        print(f"  分位数:")
        print(f"    P50 (中位数): {latency_stats['p50_ms']/1000:.2f} 秒")
        print(f"    P75:          {latency_stats['p75_ms']/1000:.2f} 秒")
        print(f"    P90:          {latency_stats['p90_ms']/1000:.2f} 秒")
        print(f"    P95:          {latency_stats['p95_ms']/1000:.2f} 秒")
        print(f"    P99:          {latency_stats['p99_ms']/1000:.2f} 秒")
    else:
        print("  暂无延迟数据")
    print()
    
    # Token分析
    print("-" * 80)
    print("【Token使用分析】")
    print("-" * 80)
    token_stats = analyze_tokens(records)
    if token_stats:
        print(f"  样本数: {token_stats['count']}")
        print(f"  最小值: {token_stats['min']:.0f} tokens")
        print(f"  最大值: {token_stats['max']:.0f} tokens")
        print(f"  平均值: {token_stats['mean']:.0f} tokens")
        print(f"  中位数: {token_stats['median']:.0f} tokens")
        print(f"  总计:   {token_stats['total']:.0f} tokens")
    else:
        print("  暂无Token数据")
    print()
    
    # 响应长度分析
    print("-" * 80)
    print("【响应文本长度分析】")
    print("-" * 80)
    length_stats = analyze_response_length(records)
    if length_stats:
        print(f"  样本数:   {length_stats['count']}")
        print(f"  最短:     {length_stats['min_chars']:.0f} 字符")
        print(f"  最长:     {length_stats['max_chars']:.0f} 字符")
        print(f"  平均:     {length_stats['mean_chars']:.0f} 字符")
        print(f"  中位数:   {length_stats['median_chars']:.0f} 字符")
    else:
        print("  暂无长度数据")
    print()
    
    # 吞吐量分析
    print("-" * 80)
    print("【吞吐量估算】")
    print("-" * 80)
    throughput = calculate_throughput(latency_stats, token_stats)
    if throughput:
        print(f"  平均吞吐: {throughput['tokens_per_second']:.1f} tokens/秒")
        print(f"  字符吞吐: {throughput['chars_per_second']:.1f} 字符/秒")
        print(f"  理论QPS:  {throughput['requests_per_minute']:.1f} 请求/分钟")
    else:
        print("  暂无数据")
    print()
    
    # 优化建议
    print("-" * 80)
    print("【系统参数优化建议】")
    print("-" * 80)
    recommendations = generate_recommendations(latency_stats, token_stats)
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    print()
    
    print("=" * 80)


def main():
    """主函数"""
    import sys
    
    log_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("正在加载数据...")
    records = load_records(log_file)
    
    if not records:
        print("未找到豆包API的成功响应记录")
        print(f"请确保日志文件存在: {log_file or 'data/ai_responses/ai_responses.jsonl'}")
        return
    
    print_analysis_report(records)


if __name__ == "__main__":
    main()
