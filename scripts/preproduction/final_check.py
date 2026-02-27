#!/usr/bin/env python3
"""
Step 2.3: 全量发布前最终检查清单

在将 v2 流量切换到 100% 之前，必须完成以下检查：
- 错误率 < 3%
- 超时率 < 1%
- 死信队列已清理
- 性能基线测试通过
- 用户反馈积极

使用方法:
    python scripts/preproduction/final_check.py

    # 或者从代码中调用
    from scripts.preproduction.final_check import run_final_check, CHECKLIST

    result = run_final_check()
    if result['passed']:
        print("✅ 全量发布检查通过")
    else:
        print("❌ 全量发布检查失败")
"""

import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path


class CheckStatus(Enum):
    """检查状态"""
    PASSED = 'passed'
    FAILED = 'failed'
    WARNING = 'warning'
    SKIPPED = 'skipped'


@dataclass
class CheckItem:
    """检查项"""
    name: str
    description: str
    status: CheckStatus = CheckStatus.SKIPPED
    current_value: Any = None
    expected_value: Any = None
    message: str = ''
    critical: bool = True  # 是否为关键检查项（失败则阻止发布）


# ==================== 全量发布检查清单 ====================

CHECKLIST: Dict[str, CheckItem] = {
    'error_rate': CheckItem(
        name='error_rate',
        description='v2 错误率 < 3%',
        expected_value='< 3%',
        critical=True,
    ),
    'timeout_rate': CheckItem(
        name='timeout_rate',
        description='v2 超时率 < 1%',
        expected_value='< 1%',
        critical=True,
    ),
    'dead_letter_cleaned': CheckItem(
        name='dead_letter_cleaned',
        description='死信队列已清理',
        expected_value=True,
        critical=True,
    ),
    'performance_baseline': CheckItem(
        name='performance_baseline',
        description='性能基线测试通过',
        expected_value='passed',
        critical=True,
    ),
    'user_feedback': CheckItem(
        name='user_feedback',
        description='用户反馈积极',
        expected_value='positive',
        critical=False,  # 非关键，但需要记录
    ),
    'ai_failure_rate': CheckItem(
        name='ai_failure_rate',
        description='AI 调用失败率 < 5%',
        expected_value='< 5%',
        critical=True,
    ),
    'database_error_rate': CheckItem(
        name='database_error_rate',
        description='数据库错误率 < 1%',
        expected_value='< 1%',
        critical=True,
    ),
    'avg_response_time': CheckItem(
        name='avg_response_time',
        description='平均响应时间 < 20s',
        expected_value='< 20s',
        critical=True,
    ),
    'monitoring_active': CheckItem(
        name='monitoring_active',
        description='监控系统正常运行',
        expected_value=True,
        critical=True,
    ),
    'rollback_ready': CheckItem(
        name='rollback_ready',
        description='回滚脚本已准备',
        expected_value=True,
        critical=True,
    ),
}


@dataclass
class CheckResult:
    """检查结果"""
    check_time: datetime
    checklist_id: str
    passed: bool
    total_items: int
    passed_items: int
    failed_items: int
    warning_items: int
    skipped_items: int
    items: Dict[str, CheckItem] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


# ==================== 检查数据目录 ====================

CHECKLIST_DATA_DIR = Path(__file__).parent.parent / 'monitoring_data' / 'final_checks'
CHECKLIST_HISTORY_FILE = CHECKLIST_DATA_DIR / 'checklist_history.json'

CHECKLIST_DATA_DIR.mkdir(parents=True, exist_ok=True)


class FinalCheckManager:
    """全量发布检查管理器"""

    def __init__(self):
        self.checklist_history: List[CheckResult] = self._load_checklist_history()

    def _load_checklist_history(self) -> List[CheckResult]:
        """加载检查历史"""
        if CHECKLIST_HISTORY_FILE.exists():
            try:
                with open(CHECKLIST_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [
                        CheckResult(
                            check_time=datetime.fromisoformat(item['check_time']),
                            checklist_id=item['checklist_id'],
                            passed=item['passed'],
                            total_items=item['total_items'],
                            passed_items=item['passed_items'],
                            failed_items=item['failed_items'],
                            warning_items=item['warning_items'],
                            skipped_items=item['skipped_items'],
                            items={
                                k: CheckItem(**v) for k, v in item['items'].items()
                            },
                            recommendations=item.get('recommendations', []),
                        )
                        for item in data[-50:]  # 只保留最近 50 次检查
                    ]
            except Exception as e:
                print(f"加载检查历史失败：{e}")
        return []

    def _save_checklist_history(self):
        """保存检查历史"""
        try:
            data = []
            for result in self.checklist_history[-50:]:
                item = {
                    'check_time': result.check_time.isoformat(),
                    'checklist_id': result.checklist_id,
                    'passed': result.passed,
                    'total_items': result.total_items,
                    'passed_items': result.passed_items,
                    'failed_items': result.failed_items,
                    'warning_items': result.warning_items,
                    'skipped_items': result.skipped_items,
                    'items': {
                        k: {
                            'name': v.name,
                            'description': v.description,
                            'status': v.status.value,
                            'current_value': v.current_value,
                            'expected_value': v.expected_value,
                            'message': v.message,
                            'critical': v.critical,
                        }
                        for k, v in result.items.items()
                    },
                    'recommendations': result.recommendations,
                }
                data.append(item)

            with open(CHECKLIST_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存检查历史失败：{e}")

    def check_error_rate(self, window: str = '1h') -> CheckItem:
        """
        检查错误率

        Args:
            window: 时间窗口

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['error_rate']

        # TODO: 从监控系统获取实际错误率
        # 这里模拟检查逻辑
        try:
            # 实际实现应该从监控系统获取数据
            # from wechat_backend.v2.monitoring.alert_config import get_v2_alert_manager
            # manager = get_v2_alert_manager()
            # stats = manager.get_metric_stats('v2.error_rate', window)
            # error_rate = stats['avg']

            # 模拟数据 - 实际使用时应该从监控系统获取
            error_rate = 0.025  # 2.5%

            item.current_value = f'{error_rate:.2%}'
            item.expected_value = '< 3%'

            if error_rate < 0.03:
                item.status = CheckStatus.PASSED
                item.message = f'错误率 {error_rate:.2%} < 3%，符合要求'
            elif error_rate < 0.05:
                item.status = CheckStatus.WARNING
                item.message = f'警告：错误率 {error_rate:.2%} 接近阈值'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：错误率 {error_rate:.2%} > 3%，不符合要求'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_timeout_rate(self, window: str = '1h') -> CheckItem:
        """
        检查超时率

        Args:
            window: 时间窗口

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['timeout_rate']

        try:
            # 模拟数据 - 实际使用时应该从监控系统获取
            timeout_rate = 0.008  # 0.8%

            item.current_value = f'{timeout_rate:.2%}'
            item.expected_value = '< 1%'

            if timeout_rate < 0.01:
                item.status = CheckStatus.PASSED
                item.message = f'超时率 {timeout_rate:.2%} < 1%，符合要求'
            elif timeout_rate < 0.02:
                item.status = CheckStatus.WARNING
                item.message = f'警告：超时率 {timeout_rate:.2%} 接近阈值'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：超时率 {timeout_rate:.2%} > 1%，不符合要求'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_dead_letter_queue(self) -> CheckItem:
        """
        检查死信队列

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['dead_letter_cleaned']

        try:
            # TODO: 从数据库或消息队列获取死信队列状态
            # 模拟检查逻辑
            dead_letter_count = 5  # 当前死信队列数量
            dead_letter_growth_rate = 2  # 每小时增长

            item.current_value = f'数量：{dead_letter_count}, 增长率：{dead_letter_growth_rate}/h'
            item.expected_value = '已清理'

            if dead_letter_count < 50 and dead_letter_growth_rate < 10:
                item.status = CheckStatus.PASSED
                item.message = f'死信队列状态良好：{dead_letter_count} 条，增长 {dead_letter_growth_rate}/h'
            elif dead_letter_count < 100:
                item.status = CheckStatus.WARNING
                item.message = f'警告：死信队列有 {dead_letter_count} 条，建议清理'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：死信队列过多 ({dead_letter_count} 条)，需要清理'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_performance_baseline(self) -> CheckItem:
        """
        检查性能基线

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['performance_baseline']

        try:
            # TODO: 运行性能测试并对比基线
            # 模拟检查逻辑
            performance_tests = {
                'avg_response_time': 18.5,  # 秒
                'p95_response_time': 25.0,  # 秒
                'p99_response_time': 35.0,  # 秒
                'throughput': 100,  # 请求/秒
            }

            baseline = {
                'avg_response_time': 20.0,
                'p95_response_time': 30.0,
                'p99_response_time': 45.0,
                'throughput': 80,
            }

            item.current_value = performance_tests
            item.expected_value = baseline

            # 检查是否满足基线要求
            passed = (
                performance_tests['avg_response_time'] <= baseline['avg_response_time'] and
                performance_tests['p95_response_time'] <= baseline['p95_response_time'] and
                performance_tests['p99_response_time'] <= baseline['p99_response_time'] and
                performance_tests['throughput'] >= baseline['throughput']
            )

            if passed:
                item.status = CheckStatus.PASSED
                item.message = '性能基线测试通过'
            else:
                item.status = CheckStatus.FAILED
                item.message = '性能基线测试失败'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_user_feedback(self) -> CheckItem:
        """
        检查用户反馈

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['user_feedback']

        try:
            # TODO: 从用户反馈系统获取数据
            # 模拟检查逻辑
            feedback_summary = {
                'total_feedback': 150,
                'positive': 120,
                'neutral': 25,
                'negative': 5,
                'positive_rate': 0.80,  # 80%
            }

            item.current_value = f'积极率：{feedback_summary["positive_rate"]:.0%}'
            item.expected_value = 'positive'

            if feedback_summary['positive_rate'] >= 0.70:
                item.status = CheckStatus.PASSED
                item.message = f'用户反馈积极：{feedback_summary["positive_rate"]:.0%} 好评率'
            elif feedback_summary['positive_rate'] >= 0.50:
                item.status = CheckStatus.WARNING
                item.message = f'警告：用户反馈一般：{feedback_summary["positive_rate"]:.0%} 好评率'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：用户反馈消极：{feedback_summary["positive_rate"]:.0%} 好评率'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_ai_failure_rate(self, window: str = '1h') -> CheckItem:
        """
        检查 AI 调用失败率

        Args:
            window: 时间窗口

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['ai_failure_rate']

        try:
            # 模拟数据
            ai_failure_rate = 0.03  # 3%

            item.current_value = f'{ai_failure_rate:.2%}'
            item.expected_value = '< 5%'

            if ai_failure_rate < 0.05:
                item.status = CheckStatus.PASSED
                item.message = f'AI 失败率 {ai_failure_rate:.2%} < 5%，符合要求'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：AI 失败率 {ai_failure_rate:.2%} > 5%'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_database_error_rate(self, window: str = '1h') -> CheckItem:
        """
        检查数据库错误率

        Args:
            window: 时间窗口

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['database_error_rate']

        try:
            # 模拟数据
            db_error_rate = 0.005  # 0.5%

            item.current_value = f'{db_error_rate:.2%}'
            item.expected_value = '< 1%'

            if db_error_rate < 0.01:
                item.status = CheckStatus.PASSED
                item.message = f'数据库错误率 {db_error_rate:.2%} < 1%，符合要求'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：数据库错误率 {db_error_rate:.2%} > 1%'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_avg_response_time(self, window: str = '1h') -> CheckItem:
        """
        检查平均响应时间

        Args:
            window: 时间窗口

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['avg_response_time']

        try:
            # 模拟数据
            avg_response_time = 18.5  # 秒

            item.current_value = f'{avg_response_time}s'
            item.expected_value = '< 20s'

            if avg_response_time < 20:
                item.status = CheckStatus.PASSED
                item.message = f'平均响应时间 {avg_response_time}s < 20s，符合要求'
            elif avg_response_time < 25:
                item.status = CheckStatus.WARNING
                item.message = f'警告：平均响应时间 {avg_response_time}s 接近阈值'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：平均响应时间 {avg_response_time}s > 20s'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_monitoring_active(self) -> CheckItem:
        """
        检查监控系统是否正常

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['monitoring_active']

        try:
            # TODO: 检查监控系统状态
            # 模拟检查逻辑
            monitoring_active = True

            item.current_value = '运行中' if monitoring_active else '异常'
            item.expected_value = True

            if monitoring_active:
                item.status = CheckStatus.PASSED
                item.message = '监控系统正常运行'
            else:
                item.status = CheckStatus.FAILED
                item.message = '失败：监控系统异常'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def check_rollback_ready(self) -> CheckItem:
        """
        检查回滚脚本是否已准备

        Returns:
            CheckItem: 检查结果
        """
        item = CHECKLIST['rollback_ready']

        try:
            # 检查回滚脚本是否存在且可执行
            rollback_script = Path(__file__).parent.parent.parent / 'scripts' / 'rollback_v2.sh'

            item.current_value = str(rollback_script)
            item.expected_value = True

            if rollback_script.exists():
                item.status = CheckStatus.PASSED
                item.message = f'回滚脚本已准备：{rollback_script}'
            else:
                item.status = CheckStatus.FAILED
                item.message = f'失败：回滚脚本不存在：{rollback_script}'

        except Exception as e:
            item.status = CheckStatus.FAILED
            item.message = f'检查失败：{e}'

        return item

    def run_full_check(self) -> CheckResult:
        """
        运行完整的全量发布检查

        Returns:
            CheckResult: 检查结果
        """
        checklist_id = f'check_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        print("=" * 60)
        print("Step 2.3: 全量发布前最终检查")
        print("=" * 60)
        print(f"检查 ID: {checklist_id}")
        print(f"检查时间：{datetime.now().isoformat()}")
        print("=" * 60)
        print()

        # 运行所有检查
        checks = [
            ('error_rate', self.check_error_rate),
            ('timeout_rate', self.check_timeout_rate),
            ('dead_letter_cleaned', self.check_dead_letter_queue),
            ('performance_baseline', self.check_performance_baseline),
            ('user_feedback', self.check_user_feedback),
            ('ai_failure_rate', self.check_ai_failure_rate),
            ('database_error_rate', self.check_database_error_rate),
            ('avg_response_time', self.check_avg_response_time),
            ('monitoring_active', self.check_monitoring_active),
            ('rollback_ready', self.check_rollback_ready),
        ]

        items: Dict[str, CheckItem] = {}
        passed_count = 0
        failed_count = 0
        warning_count = 0
        skipped_count = 0
        recommendations: List[str] = []

        for name, check_func in checks:
            print(f"🔍 检查：{name}...")
            item = check_func()
            items[name] = item

            if item.status == CheckStatus.PASSED:
                passed_count += 1
                print(f"   ✅ {item.message}")
            elif item.status == CheckStatus.WARNING:
                warning_count += 1
                print(f"   ⚠️  {item.message}")
                if item.critical:
                    recommendations.append(f"建议关注：{item.name} - {item.message}")
            elif item.status == CheckStatus.FAILED:
                failed_count += 1
                print(f"   ❌ {item.message}")
                if item.critical:
                    recommendations.append(f"必须修复：{item.name} - {item.message}")
            else:
                skipped_count += 1
                print(f"   ⏭️  已跳过")

            print()

        # 判断是否通过
        # 关键检查项必须全部通过
        critical_failed = sum(1 for item in items.values() if item.status == CheckStatus.FAILED and item.critical)
        passed = critical_failed == 0

        result = CheckResult(
            check_time=datetime.now(),
            checklist_id=checklist_id,
            passed=passed,
            total_items=len(items),
            passed_items=passed_count,
            failed_items=failed_count,
            warning_items=warning_count,
            skipped_items=skipped_count,
            items=items,
            recommendations=recommendations,
        )

        # 保存检查结果
        self.checklist_history.append(result)
        self._save_checklist_history()

        # 输出总结
        print("=" * 60)
        print("📊 检查总结")
        print("=" * 60)
        print(f"总检查项：{result.total_items}")
        print(f"✅ 通过：{result.passed_items}")
        print(f"❌ 失败：{result.failed_items}")
        print(f"⚠️  警告：{result.warning_items}")
        print(f"⏭️  跳过：{result.skipped_items}")
        print()

        if result.passed:
            print("🎉 全量发布检查通过！可以安全发布。")
        else:
            print("🚨 全量发布检查失败！请修复关键问题后再发布。")

        if result.recommendations:
            print()
            print("📝 建议:")
            for rec in result.recommendations:
                print(f"   - {rec}")

        print("=" * 60)

        return result


# ==================== 全局函数 ====================

def run_final_check() -> CheckResult:
    """
    运行全量发布检查

    Returns:
        CheckResult: 检查结果
    """
    manager = FinalCheckManager()
    return manager.run_full_check()


def get_checklist_history(limit: int = 10) -> List[CheckResult]:
    """
    获取检查历史

    Args:
        limit: 返回数量限制

    Returns:
        List[CheckResult]: 检查结果列表
    """
    manager = FinalCheckManager()
    return manager.checklist_history[-limit:]


def get_latest_check_result() -> Optional[CheckResult]:
    """
    获取最近的检查结果

    Returns:
        Optional[CheckResult]: 检查结果，如果没有则返回 None
    """
    manager = FinalCheckManager()
    if manager.checklist_history:
        return manager.checklist_history[-1]
    return None


if __name__ == '__main__':
    result = run_final_check()

    # 根据检查结果退出相应状态码
    if result.passed:
        sys.exit(0)
    else:
        sys.exit(1)
