#!/usr/bin/env python3
"""
AI平台接入计划执行脚本
自动化执行DeepSeek、Qwen、Zhipu三个平台的接入
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class IntegrationExecutor:
    """AI平台接入执行器"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = {}
        self.start_time = None
        
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def run_command(self, cmd, cwd=None, timeout=60):
        """执行命令"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd or self.base_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except Exception as e:
            return False, "", str(e)
    
    def phase1_deepseek(self):
        """第一阶段：DeepSeek平台"""
        self.log("=" * 60)
        self.log("开始第一阶段：DeepSeek平台调通")
        self.log("=" * 60)
        
        phase_results = {
            "name": "DeepSeek",
            "tasks": [],
            "status": "pending"
        }
        
        # 任务1.1：验证适配器基础功能
        self.log("\n【任务1.1】验证适配器基础功能")
        success, stdout, stderr = self.run_command(
            "python test_deepseek_integration.py",
            timeout=120
        )
        phase_results["tasks"].append({
            "name": "适配器基础功能",
            "status": "passed" if success else "failed",
            "output": stdout if success else stderr
        })
        
        if success:
            self.log("✅ 适配器基础功能验证通过")
        else:
            self.log("❌ 适配器基础功能验证失败", "ERROR")
            self.log(f"错误: {stderr}", "ERROR")
        
        # 任务1.2：创建MVP接口（需要手动执行）
        self.log("\n【任务1.2】创建MVP接口")
        self.log("⚠️  需要手动在views.py中添加 /api/mvp/deepseek-test 接口")
        self.log("参考: Phase1_DeepSeek_Implementation.md")
        
        # 任务1.3：前端测试（需要手动执行）
        self.log("\n【任务1.3】前端测试验证")
        self.log("⚠️  需要手动创建前端测试页面并验证")
        
        # 任务1.4：性能测试
        self.log("\n【任务1.4】性能测试")
        self.log("✅ 性能数据已在任务1.1中收集")
        
        # 任务1.5：主程序集成（需要手动执行）
        self.log("\n【任务1.5】主程序集成")
        self.log("⚠️  需要手动修改scheduler.py添加DeepSeek支持")
        
        phase_results["status"] = "completed" if success else "failed"
        self.results["deepseek"] = phase_results
        
        return success
    
    def phase2_qwen(self):
        """第二阶段：通义千问平台"""
        self.log("\n" + "=" * 60)
        self.log("开始第二阶段：通义千问平台调通")
        self.log("=" * 60)
        
        phase_results = {
            "name": "Qwen",
            "tasks": [],
            "status": "pending"
        }
        
        # 任务2.1：验证适配器基础功能
        self.log("\n【任务2.1】验证适配器基础功能")
        success, stdout, stderr = self.run_command(
            "python test_qwen_integration.py",
            timeout=120
        )
        phase_results["tasks"].append({
            "name": "适配器基础功能",
            "status": "passed" if success else "failed",
            "output": stdout if success else stderr
        })
        
        if success:
            self.log("✅ 适配器基础功能验证通过")
        else:
            self.log("❌ 适配器基础功能验证失败", "ERROR")
            self.log(f"错误: {stderr}", "ERROR")
        
        # 其他任务需要手动执行
        self.log("\n【任务2.2-2.5】需要手动执行")
        self.log("参考: Phase2_Qwen_Implementation.md")
        
        phase_results["status"] = "completed" if success else "failed"
        self.results["qwen"] = phase_results
        
        return success
    
    def phase3_zhipu(self):
        """第三阶段：智谱AI平台"""
        self.log("\n" + "=" * 60)
        self.log("开始第三阶段：智谱AI平台调通")
        self.log("=" * 60)
        
        phase_results = {
            "name": "Zhipu",
            "tasks": [],
            "status": "pending"
        }
        
        # 任务3.1：验证适配器基础功能
        self.log("\n【任务3.1】验证适配器基础功能")
        success, stdout, stderr = self.run_command(
            "python test_zhipu_integration.py",
            timeout=120
        )
        phase_results["tasks"].append({
            "name": "适配器基础功能",
            "status": "passed" if success else "failed",
            "output": stdout if success else stderr
        })
        
        if success:
            self.log("✅ 适配器基础功能验证通过")
        else:
            self.log("❌ 适配器基础功能验证失败", "ERROR")
            self.log(f"错误: {stderr}", "ERROR")
        
        # 其他任务需要手动执行
        self.log("\n【任务3.2-3.5】需要手动执行")
        self.log("参考: Phase3_Zhipu_Implementation.md")
        
        phase_results["status"] = "completed" if success else "failed"
        self.results["zhipu"] = phase_results
        
        return success
    
    def generate_report(self):
        """生成执行报告"""
        self.log("\n" + "=" * 60)
        self.log("执行报告")
        self.log("=" * 60)
        
        for platform, result in self.results.items():
            status_icon = "✅" if result["status"] == "completed" else "❌"
            self.log(f"\n{status_icon} {result['name']}: {result['status']}")
            
            for task in result.get("tasks", []):
                task_icon = "✅" if task["status"] == "passed" else "❌"
                self.log(f"   {task_icon} {task['name']}: {task['status']}")
        
        # 统计
        total = len(self.results)
        completed = sum(1 for r in self.results.values() if r["status"] == "completed")
        
        self.log(f"\n总计: {completed}/{total} 平台基础测试通过")
        
        if completed == total:
            self.log("\n🎉 所有平台基础测试通过！")
            self.log("接下来请按照各阶段的Implementation文档完成手动集成任务。")
        else:
            self.log("\n⚠️  部分平台测试失败，请检查错误日志。")
    
    def run(self):
        """执行完整计划"""
        self.start_time = time.time()
        
        self.log("=" * 60)
        self.log("AI平台接入计划自动执行")
        self.log("=" * 60)
        self.log(f"开始时间: {datetime.now().isoformat()}")
        self.log(f"工作目录: {self.base_dir}")
        
        try:
            # 执行三个阶段
            self.phase1_deepseek()
            self.phase2_qwen()
            self.phase3_zhipu()
            
        except KeyboardInterrupt:
            self.log("\n执行被用户中断", "WARNING")
        except Exception as e:
            self.log(f"\n执行出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        finally:
            # 生成报告
            self.generate_report()
            
            elapsed = time.time() - self.start_time
            self.log(f"\n总耗时: {elapsed:.1f}秒")


def main():
    """主函数"""
    executor = IntegrationExecutor()
    executor.run()


if __name__ == "__main__":
    main()
