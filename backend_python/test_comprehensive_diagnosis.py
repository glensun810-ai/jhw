#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌诊断系统全面测试脚本

测试团队：
- 首席测试专家：测试策略、结果验证
- 首席架构师：架构审查、数据流验证
- 全栈工程师：问题修复

测试目标：确保品牌洞察报告完整、准确输出
"""

import json
import time
import requests
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# 测试配置
BASE_URL = "http://127.0.0.1:5001"
TIMEOUT = 300  # 5 分钟超时
POLL_INTERVAL = 1  # 1 秒轮询一次
MAX_POLLS = 60  # 最多轮询 60 次

# 测试用例
TEST_CASES = [
    {
        "name": "单问题单模型诊断",
        "brand_list": ["趣车良品", "承美车居"],
        "selected_models": ["doubao"],
        "custom_question": "深圳新能源汽车改装门店推荐",
        "expected_results": 1,
        "expected_time": 30  # 秒
    },
    {
        "name": "单问题多模型诊断",
        "brand_list": ["趣车良品"],
        "selected_models": ["doubao", "qwen"],
        "custom_question": "深圳新能源汽车改装门店推荐",
        "expected_results": 2,
        "expected_time": 45
    },
    {
        "name": "多问题单模型诊断",
        "brand_list": ["趣车良品"],
        "selected_models": ["doubao"],
        "custom_question": "深圳新能源汽车改装门店推荐，趣车良品的改装质量怎么样",
        "expected_results": 2,
        "expected_time": 45
    }
]


class TestResult:
    """测试结果记录"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.execution_id = None
        self.status = "pending"
        self.error = None
        self.detailed_results = []
        self.poll_count = 0
        self.total_time = 0
        self.field_completeness = {}
        self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "execution_id": self.execution_id,
            "total_time": self.total_time,
            "poll_count": self.poll_count,
            "result_count": len(self.detailed_results),
            "error": self.error,
            "warnings": self.warnings,
            "field_completeness": self.field_completeness
        }


class BrandDiagnosisTester:
    """品牌诊断系统测试器"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: List[TestResult] = []
    
    def check_health(self) -> bool:
        """检查后端服务健康状态"""
        print("\n" + "="*60)
        print("【步骤 1】后端健康检查")
        print("="*60)
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                print(f"✅ 后端服务正常：{response.json()}")
                return True
            else:
                print(f"❌ 后端服务异常：{response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到后端服务，请确保后端已启动")
            print(f"   地址：{self.base_url}")
            return False
        except Exception as e:
            print(f"❌ 健康检查失败：{e}")
            return False
    
    def start_diagnosis(self, brand_list: List[str], selected_models: List[str], 
                       custom_question: str) -> Optional[str]:
        """启动诊断任务"""
        print("\n" + "="*60)
        print("【步骤 2】启动诊断任务")
        print("="*60)
        
        url = f"{self.base_url}/api/perform-brand-test"
        # 后端需要驼峰命名
        payload = {
            "brand_list": brand_list,
            "selectedModels": selected_models,  # 驼峰命名
            "custom_question": custom_question
        }
        
        print(f"请求 URL: {url}")
        print(f"请求数据：{json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            print(f"响应状态码：{response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ 启动失败：{response.status_code}")
                print(f"响应内容：{response.text[:500]}")
                return None
            
            data = response.json()
            execution_id = data.get("execution_id") or data.get("id") or data.get("task_id")
            
            if not execution_id:
                print(f"❌ 无法从响应中提取 execution_id")
                print(f"响应数据：{json.dumps(data, ensure_ascii=False, indent=2)}")
                return None
            
            print(f"✅ 诊断任务启动成功")
            print(f"   Execution ID: {execution_id}")
            return execution_id
            
        except Exception as e:
            print(f"❌ 启动诊断失败：{e}")
            return None
    
    def poll_status(self, execution_id: str, max_polls: int = MAX_POLLS) -> Optional[Dict[str, Any]]:
        """轮询任务状态"""
        print("\n" + "="*60)
        print("【步骤 3】轮询任务状态")
        print("="*60)
        
        url = f"{self.base_url}/test/status/{execution_id}"
        start_time = time.time()
        
        for i in range(max_polls):
            try:
                response = self.session.get(url, timeout=10)
                poll_time = time.time() - start_time
                
                if response.status_code != 200:
                    print(f"❌ 第 {i+1} 次轮询失败：{response.status_code}")
                    continue
                
                data = response.json()
                stage = data.get("stage", "unknown")
                progress = data.get("progress", 0)
                results_count = len(data.get("detailed_results", []) or data.get("results", []))
                
                print(f"第 {i+1:2d} 次轮询 ({poll_time:5.1f}s) | "
                      f"Stage: {stage:20s} | Progress: {progress:3d}% | "
                      f"Results: {results_count}")
                
                # 检查终止条件
                if stage in ["completed", "finished", "done"]:
                    print(f"\n✅ 任务完成！")
                    return data
                
                if stage == "failed":
                    # 检查是否有结果（质量低但有结果的情况）
                    if progress == 100 and results_count > 0:
                        print(f"\n⚠️  任务标记为 failed 但有结果，视为部分完成")
                        return data
                    else:
                        print(f"\n❌ 任务失败：{data.get('error', '未知错误')}")
                        return data
                
                time.sleep(POLL_INTERVAL)
                
            except Exception as e:
                print(f"❌ 第 {i+1} 次轮询异常：{e}")
                time.sleep(POLL_INTERVAL)
        
        print(f"\n❌ 轮询超时（{max_polls} 次）")
        return None
    
    def validate_result_fields(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """验证结果字段完整性"""
        print("\n" + "="*60)
        print("【步骤 4】验证结果字段完整性")
        print("="*60)
        
        completeness = {}
        
        # 顶层字段
        required_top_fields = ["execution_id", "status", "stage", "progress", "detailed_results"]
        for field in required_top_fields:
            exists = field in data
            completeness[field] = exists
            status = "✅" if exists else "❌"
            print(f"{status} {field}: {data.get(field, 'MISSING') if not isinstance(data.get(field), list) else f'[{len(data.get(field, []))} items]'}")
        
        # detailed_results 数组
        detailed_results = data.get("detailed_results", []) or data.get("results", [])
        if detailed_results:
            print(f"\n📊 detailed_results: {len(detailed_results)} 条")
            
            # 检查第一条结果的字段
            first_result = detailed_results[0]
            print(f"\n   检查结果字段:")
            
            # 结果级别字段
            result_fields = ["brand", "model", "question", "response", "geo_data"]
            for field in result_fields:
                exists = field in first_result
                completeness[f"result.{field}"] = exists
                status = "✅" if exists else "❌"
                print(f"   {status} {field}")
            
            # geo_data 字段
            geo_data = first_result.get("geo_data", {})
            if geo_data:
                print(f"\n   检查 geo_data 字段:")
                geo_fields = ["brand_mentioned", "rank", "sentiment", "cited_sources", "interception"]
                for field in geo_fields:
                    exists = field in geo_data
                    completeness[f"geo_data.{field}"] = exists
                    status = "✅" if exists else "❌"
                    print(f"   {status} {field}: {geo_data.get(field, 'MISSING')}")
            
            # quality_info 字段
            quality_fields = ["quality_score", "quality_level", "quality_details"]
            has_quality = all(field in first_result for field in quality_fields)
            if has_quality:
                print(f"\n   检查 quality_info 字段:")
                for field in quality_fields:
                    exists = field in first_result
                    completeness[f"quality.{field}"] = exists
                    status = "✅" if exists else "❌"
                    value = first_result.get(field)
                    if isinstance(value, dict):
                        value = f"{{...}}"
                    print(f"   {status} {field}: {value}")
            else:
                print(f"\n   ⚠️  quality_info 字段缺失")
                for field in quality_fields:
                    completeness[f"quality.{field}"] = False
        
        # competitive_analysis 字段
        comp_analysis = data.get("competitive_analysis", {})
        if comp_analysis:
            print(f"\n📊 competitive_analysis: 存在")
            completeness["competitive_analysis"] = True
        else:
            print(f"\n⚠️  competitive_analysis: 缺失")
            completeness["competitive_analysis"] = False
        
        # brand_scores 字段
        brand_scores = data.get("brand_scores", {})
        if brand_scores:
            print(f"📊 brand_scores: 存在")
            completeness["brand_scores"] = True
        else:
            print(f"⚠️  brand_scores: 缺失")
            completeness["brand_scores"] = False
        
        # 计算完整率
        total_fields = len(completeness)
        present_fields = sum(1 for v in completeness.values() if v)
        completeness_rate = (present_fields / total_fields * 100) if total_fields > 0 else 0
        print(f"\n📈 字段完整率：{present_fields}/{total_fields} ({completeness_rate:.1f}%)")
        
        return completeness
    
    def validate_geo_data_logic(self, detailed_results: List[Dict]) -> List[str]:
        """验证 GEO 数据逻辑正确性"""
        warnings = []
        
        for i, result in enumerate(detailed_results[:3]):  # 检查前 3 条
            geo_data = result.get("geo_data", {})
            
            # 检查 brand_mentioned 和 rank 的一致性
            if not geo_data.get("brand_mentioned", True) and geo_data.get("rank", -1) > 0:
                warnings.append(f"结果{i+1}: brand_mentioned=false 但 rank>0，逻辑矛盾")
            
            # 检查 rank 有效性
            rank = geo_data.get("rank", -1)
            if rank not in [-1, 0] and rank < 1:
                warnings.append(f"结果{i+1}: 无效的 rank 值：{rank}")
            
            # 检查 sentiment 范围
            sentiment = geo_data.get("sentiment", 0)
            if not (-1 <= sentiment <= 1):
                warnings.append(f"结果{i+1}: sentiment 超出范围：{sentiment}")
            
            # 检查 quality_score 和 quality_level 一致性
            quality_score = result.get("quality_score", 0)
            quality_level = result.get("quality_level", "")
            
            expected_level = "very_low"
            if quality_score >= 80:
                expected_level = "high"
            elif quality_score >= 60:
                expected_level = "medium"
            elif quality_score >= 30:
                expected_level = "low"
            
            if quality_level != expected_level:
                warnings.append(f"结果{i+1}: quality_level={quality_level} 但预期={expected_level} (score={quality_score})")
        
        return warnings
    
    def run_test(self, test_case: Dict[str, Any]) -> TestResult:
        """运行单个测试用例"""
        result = TestResult(test_case["name"])
        result.start_time = datetime.now()
        
        print("\n" + "="*70)
        print(f"🧪 测试用例：{test_case['name']}")
        print("="*70)
        
        # 启动诊断
        execution_id = self.start_diagnosis(
            test_case["brand_list"],
            test_case["selected_models"],
            test_case["custom_question"]
        )
        
        if not execution_id:
            result.status = "failed"
            result.error = "无法启动诊断"
            result.end_time = datetime.now()
            result.total_time = (result.end_time - result.start_time).total_seconds()
            return result
        
        result.execution_id = execution_id
        
        # 轮询状态
        final_data = self.poll_status(execution_id)
        
        if not final_data:
            result.status = "timeout"
            result.error = "轮询超时"
            result.end_time = datetime.now()
            result.total_time = (result.end_time - result.start_time).total_seconds()
            return result
        
        # 验证字段完整性
        completeness = self.validate_result_fields(final_data)
        result.field_completeness = completeness
        
        # 获取详细结果
        result.detailed_results = final_data.get("detailed_results", []) or final_data.get("results", [])
        
        # 验证 GEO 数据逻辑
        warnings = self.validate_geo_data_logic(result.detailed_results)
        result.warnings = warnings
        
        # 确定测试状态
        stage = final_data.get("stage", "unknown")
        progress = final_data.get("progress", 0)
        
        if stage in ["completed", "finished", "done"]:
            result.status = "passed"
        elif stage == "failed" and progress == 100 and len(result.detailed_results) > 0:
            result.status = "passed_with_warnings"
            result.warnings.append("任务标记为 failed 但有结果")
        elif stage == "failed":
            result.status = "failed"
            result.error = final_data.get("error", "任务失败")
        else:
            result.status = "unknown"
        
        result.end_time = datetime.now()
        result.total_time = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def run_all_tests(self) -> List[TestResult]:
        """运行所有测试用例"""
        print("\n" + "="*70)
        print("🚀 品牌诊断系统全面测试")
        print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 健康检查
        if not self.check_health():
            print("\n❌ 后端服务不可用，测试终止")
            return []
        
        # 运行测试用例
        for test_case in TEST_CASES:
            result = self.run_test(test_case)
            self.test_results.append(result)
            
            # 打印测试摘要
            print("\n" + "-"*70)
            print(f"测试：{result.test_name}")
            print(f"状态：{result.status}")
            print(f"耗时：{result.total_time:.1f}秒")
            print(f"轮询：{result.poll_count}次")
            print(f"结果：{len(result.detailed_results)}条")
            if result.error:
                print(f"错误：{result.error}")
            if result.warnings:
                print(f"警告：{len(result.warnings)}条")
            print("-"*70)
        
        return self.test_results
    
    def generate_report(self) -> str:
        """生成测试报告"""
        print("\n" + "="*70)
        print("📊 测试报告")
        print("="*70)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.status in ["passed", "passed_with_warnings"])
        failed = sum(1 for r in self.test_results if r.status in ["failed", "timeout"])
        
        print(f"\n总测试数：{total}")
        print(f"通过：{passed} ({passed/total*100:.1f}%)")
        print(f"失败：{failed} ({failed/total*100:.1f}%)")
        
        print("\n详细结果:")
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result.status in ["passed", "passed_with_warnings"] else "❌"
            print(f"\n{i}. {result.test_name}")
            print(f"   {status_icon} 状态：{result.status}")
            print(f"   ⏱️  耗时：{result.total_time:.1f}秒")
            print(f"   📊 结果数：{len(result.detailed_results)}")
            print(f"   📈 字段完整率：{sum(result.field_completeness.values())}/{len(result.field_completeness)}")
            
            if result.error:
                print(f"   ❌ 错误：{result.error}")
            if result.warnings:
                print(f"   ⚠️  警告:")
                for w in result.warnings[:3]:
                    print(f"      - {w}")
        
        # 生成 Markdown 报告
        report = f"""
# 品牌诊断系统测试报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试摘要

| 指标 | 数值 |
|------|------|
| 总测试数 | {total} |
| 通过 | {passed} ({passed/total*100:.1f}%) |
| 失败 | {failed} ({failed/total*100:.1f}%) |

## 详细结果

"""
        for i, result in enumerate(self.test_results, 1):
            completeness_count = sum(result.field_completeness.values()) if result.field_completeness else 0
            completeness_total = len(result.field_completeness) if result.field_completeness else 0
            completeness_rate = (completeness_count / completeness_total * 100) if completeness_total > 0 else 0
            
            report += f"""
### {i}. {result.test_name}

- **状态**: {result.status}
- **耗时**: {result.total_time:.1f}秒
- **轮询次数**: {result.poll_count}
- **结果数量**: {len(result.detailed_results)}
- **字段完整率**: {completeness_count}/{completeness_total} ({completeness_rate:.1f}%)
"""
            if result.error:
                report += f"- **错误**: {result.error}\n"
            if result.warnings:
                report += f"- **警告**:\n"
                for w in result.warnings:
                    report += f"  - {w}\n"
        
        return report


def main():
    """主函数"""
    tester = BrandDiagnosisTester()
    
    # 运行所有测试
    results = tester.run_all_tests()
    
    if not results:
        print("\n❌ 测试未能执行")
        sys.exit(1)
    
    # 生成报告
    report = tester.generate_report()
    
    # 保存报告
    report_file = "test_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 测试报告已保存到：{report_file}")
    
    # 确定退出码
    all_passed = all(r.status in ["passed", "passed_with_warnings"] for r in results)
    if all_passed:
        print("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请查看报告")
        sys.exit(1)


if __name__ == "__main__":
    main()
