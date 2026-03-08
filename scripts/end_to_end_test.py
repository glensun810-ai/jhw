#!/usr/bin/env python3
"""
端到端诊断测试脚本

验证完整诊断链路：
1. 发起诊断请求
2. 等待诊断完成
3. 验证数据库结果
4. 验证报告内容

使用方法:
    cd /Users/sgl/PycharmProjects/PythonProject/backend_python
    python3 scripts/end_to_end_test.py
"""

import requests
import time
import sqlite3
import json
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5000"
DB_PATH = "backend_python/database.db"
TIMEOUT_SECONDS = 120  # 2 分钟超时
POLL_INTERVAL = 2  # 轮询间隔（秒）


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def test_api_health():
    """测试 API 健康状态"""
    print_header("Step 0: API 健康检查")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print_success(f"API 健康检查通过 (status={response.status_code})")
            return True
        else:
            print_warning(f"API 返回非 200 状态码：{response.status_code}")
            return True  # 继续测试
    except requests.exceptions.ConnectionError:
        print_error(f"无法连接到 API 服务器：{BASE_URL}")
        print_info("请确保后端服务正在运行：cd backend_python && python3 run.py")
        return False
    except Exception as e:
        print_error(f"API 健康检查失败：{e}")
        return True  # 继续测试


def start_diagnosis():
    """发起诊断请求"""
    print_header("Step 1: 发起诊断请求")
    
    test_data = {
        "user_id": "test_user_e2e",
        "brand_name": "趣车良品",
        "competitor_brands": ["车尚艺"],
        "selected_models": [{"name": "qwen", "checked": True}],
        "questions": ["深圳新能源汽车改装门店靠谱的推荐？"]
    }
    
    print_info(f"测试参数:")
    print(f"  品牌：{test_data['brand_name']}")
    print(f"  竞品：{test_data['competitor_brands']}")
    print(f"  模型：{test_data['selected_models'][0]['name']}")
    print(f"  问题数：{len(test_data['questions'])}")
    
    try:
        start_time = datetime.now()
        response = requests.post(
            f"{BASE_URL}/api/perform-brand-test",
            json=test_data,
            timeout=30
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print_info(f"请求耗时：{elapsed:.2f}秒")
        
        if response.status_code != 200:
            print_error(f"请求失败：status={response.status_code}")
            print_error(f"响应：{response.text[:500]}")
            return None
        
        data = response.json()
        execution_id = data.get('execution_id')
        
        if not execution_id:
            print_error("响应中缺少 execution_id")
            print_error(f"完整响应：{json.dumps(data, indent=2)}")
            return None
        
        print_success(f"请求成功")
        print_info(f"execution_id: {execution_id}")
        
        # 检查初始状态
        status = data.get('status', 'unknown')
        print_info(f"初始状态：{status}")
        
        return execution_id
        
    except requests.exceptions.Timeout:
        print_error("请求超时（30 秒）")
        return None
    except Exception as e:
        print_error(f"请求异常：{e}")
        return None


def wait_for_completion(execution_id):
    """等待诊断完成"""
    print_header("Step 2: 等待诊断完成")
    print_info(f"最多等待 {TIMEOUT_SECONDS} 秒，轮询间隔 {POLL_INTERVAL}秒")
    
    start_time = datetime.now()
    last_status = None
    last_progress = None
    
    while True:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if elapsed > TIMEOUT_SECONDS:
            print_error(f"诊断超时（{TIMEOUT_SECONDS}秒）")
            return False
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/diagnosis-status/{execution_id}",
                timeout=10
            )
            
            if response.status_code != 200:
                print_warning(f"状态查询失败：status={response.status_code}")
                time.sleep(POLL_INTERVAL)
                continue
            
            status_data = response.json()
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress', 0)
            stage = status_data.get('stage', '')
            
            # 状态变化时打印
            if status != last_status or progress != last_progress:
                time_str = datetime.now().strftime("%H:%M:%S")
                print_info(f"[{time_str}] status={status}, progress={progress}%, stage={stage}")
                last_status = status
                last_progress = progress
            
            # 检查完成状态
            if status == 'completed':
                total_elapsed = (datetime.now() - start_time).total_seconds()
                print_success(f"诊断完成！总耗时：{total_elapsed:.1f}秒")
                
                # 检查是否有错误
                if status_data.get('error'):
                    print_warning(f"完成但有错误：{status_data.get('error')}")
                
                return True
            
            # 检查失败状态
            if status == 'failed':
                error_msg = status_data.get('error_message', '未知错误')
                print_error(f"诊断失败：{error_msg}")
                return False
            
        except requests.exceptions.Timeout:
            print_warning("状态查询超时")
        except Exception as e:
            print_warning(f"状态查询异常：{e}")
        
        time.sleep(POLL_INTERVAL)


def verify_database(execution_id):
    """验证数据库结果"""
    print_header("Step 3: 验证数据库结果")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询诊断结果
        cursor.execute("""
            SELECT 
                execution_id, 
                brand, 
                question, 
                model, 
                tokens_used, 
                prompt_tokens, 
                completion_tokens,
                created_at 
            FROM diagnosis_results 
            WHERE execution_id = ?
            ORDER BY created_at DESC
        """, (execution_id,))
        
        results = cursor.fetchall()
        
        print_info(f"查询到 {len(results)} 条结果")
        
        if len(results) == 0:
            print_error("数据库中没有结果！")
            conn.close()
            return False
        
        # 验证第一条结果
        row = dict(results[0])
        print_info("第一条结果详情:")
        print(f"  brand: {row['brand']}")
        print(f"  model: {row['model']}")
        print(f"  question: {row['question'][:50]}...")
        print(f"  tokens_used: {row['tokens_used']}")
        print(f"  prompt_tokens: {row['prompt_tokens']}")
        print(f"  completion_tokens: {row['completion_tokens']}")
        
        # 验证关键字段
        errors = []
        warnings = []
        
        if not row['brand']:
            errors.append("brand 字段为空")
        else:
            print_success(f"brand 字段有值：{row['brand']}")
        
        if row['tokens_used'] == 0:
            warnings.append("tokens_used=0（可能正常，取决于 AI 响应）")
        else:
            print_success(f"tokens_used > 0: {row['tokens_used']}")
        
        # 验证结果数量（1 问题×1 模型=1 结果）
        expected_count = 1  # MVP 场景
        if len(results) != expected_count:
            warnings.append(f"结果数量异常：期望{expected_count}，实际{len(results)}")
        else:
            print_success(f"结果数量正确：{len(results)}")
        
        # 检查 diagnosis_analysis 表
        cursor.execute("""
            SELECT COUNT(*) as count, analysis_type 
            FROM diagnosis_analysis 
            WHERE execution_id = ?
            GROUP BY analysis_type
        """, (execution_id,))
        
        analysis_results = cursor.fetchall()
        
        if len(analysis_results) == 0:
            print_warning("diagnosis_analysis 表无记录（可能是 P3 问题）")
        else:
            print_success(f"diagnosis_analysis 表有 {len(analysis_results)} 条记录:")
            for ar in analysis_results:
                print(f"  - {ar['analysis_type']}: {ar['count']}条")
        
        # 检查 diagnosis_snapshots 表
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM diagnosis_snapshots 
            WHERE execution_id = ?
        """, (execution_id,))
        
        snapshot_result = cursor.fetchone()
        
        if snapshot_result and snapshot_result['count'] > 0:
            print_success(f"diagnosis_snapshots 表有 {snapshot_result['count']} 条记录")
        else:
            print_warning("diagnosis_snapshots 表无记录（可能是 P3 问题）")
        
        conn.close()
        
        # 输出验证结果
        print("")
        if errors:
            for err in errors:
                print_error(err)
            return False
        
        for warn in warnings:
            print_warning(warn)
        
        print_success("数据库验证通过")
        return True
        
    except Exception as e:
        print_error(f"数据库验证失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def verify_report(execution_id):
    """验证报告内容"""
    print_header("Step 4: 验证报告内容")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/diagnosis-report/{execution_id}",
            timeout=30
        )
        
        if response.status_code != 200:
            print_error(f"报告获取失败：status={response.status_code}")
            return False
        
        report = response.json()
        
        print_info("报告关键信息:")
        
        # 检查分数
        overall_score = report.get('overallScore')
        if overall_score is not None:
            print_info(f"  综合分数：{overall_score}")
            print_success("✅ 分数存在")
        else:
            print_error("❌ 缺少综合分数")
        
        # 检查品牌分析
        brand_analysis = report.get('brandAnalysis')
        if brand_analysis:
            print_success("✅ 品牌分析存在")
            # 打印品牌分析摘要
            if isinstance(brand_analysis, dict):
                print_info(f"  品牌分析内容：{json.dumps(brand_analysis, ensure_ascii=False)[:200]}...")
        else:
            print_warning("⚠️  品牌分析缺失（可能是后台分析未完成）")
        
        # 检查竞争分析
        competitive_analysis = report.get('competitiveAnalysis')
        if competitive_analysis:
            print_success("✅ 竞争分析存在")
        else:
            print_warning("⚠️  竞争分析缺失（可能是后台分析未完成）")
        
        # 检查质量信息
        quality = report.get('quality')
        if quality:
            print_info(f"  报告质量：{quality.get('level', 'unknown')}")
            print_info(f"  完整度评分：{quality.get('completeness_score', 0)}")
        
        print("")
        if overall_score is not None:
            print_success("报告验证通过")
            return True
        else:
            print_error("报告缺少关键字段")
            return False
        
    except requests.exceptions.Timeout:
        print_error("报告获取超时")
        return False
    except Exception as e:
        print_error(f"报告验证失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(success):
    """打印测试摘要"""
    print_header("测试摘要")
    
    if success:
        print_success("🎉 端到端测试全部通过！")
        print("")
        print_info("下一步:")
        print("  1. 在小程序前端发起一次真实诊断请求")
        print("  2. 观察前端是否能正常显示报告")
        print("  3. 如果前端仍有问题，使用前端调试面板追踪")
    else:
        print_error("❌ 端到端测试失败")
        print("")
        print_info("调试建议:")
        print("  1. 查看后端日志：tail -100 logs/app.log")
        print("  2. 检查数据库：sqlite3 backend_python/database.db")
        print("  3. 确认后端服务正常运行：ps aux | grep run.py")
    
    print("")


def main():
    """主函数"""
    print_header("🔍 端到端诊断测试")
    print_info(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"API 地址：{BASE_URL}")
    print_info(f"数据库路径：{DB_PATH}")
    
    # Step 0: API 健康检查
    if not test_api_health():
        print_error("API 不可用，测试终止")
        print_summary(False)
        return 1
    
    # Step 1: 发起诊断
    execution_id = start_diagnosis()
    if not execution_id:
        print_error("无法发起诊断，测试终止")
        print_summary(False)
        return 1
    
    # Step 2: 等待完成
    if not wait_for_completion(execution_id):
        print_error("诊断未完成，测试终止")
        print_summary(False)
        return 1
    
    # Step 3: 数据库验证
    db_ok = verify_database(execution_id)
    
    # Step 4: 报告验证
    report_ok = verify_report(execution_id)
    
    # 总结
    overall_success = db_ok and report_ok
    print_summary(overall_success)
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
