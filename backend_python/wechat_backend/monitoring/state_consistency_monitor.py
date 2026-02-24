from wechat_backend.log_config import get_logger

#!/usr/bin/env python3
"""
状态一致性监控模块

功能:
1. 实时监控任务状态同步
2. 检测 status/stage 不一致
3. 自动告警和日志记录
4. 生成监控报告

使用示例:
    from state_consistency_monitor import StateConsistencyMonitor
    
    monitor = StateConsistencyMonitor(
    monitor.check_and_log(task_status_dict
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/state_monitor.log', encoding='utf-8'
    ]

logger = logging.getLogger('state_monitor'


class ConsistencyLevel(Enum):
    """一致性级别"""
    CONSISTENT = "consistent"           # 完全一致
    MINOR_ISSUE = "minor_issue"         # 小问题
    MAJOR_ISSUE = "major_issue"         # 严重问题
    CRITICAL = "critical"               # 严重错误


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    task_id: str
    timestamp: str
    level: ConsistencyLevel
    status: str
    stage: str
    is_completed: bool
    progress: int
    issues: List[str]
    auto_fixed: bool
    details: Dict[str, Any]


class StateConsistencyMonitor:
    """状态一致性监控器"""
    
    def __init__(self, auto_fix: bool = True):
        """
        初始化监控器
        
        Args:
            auto_fix: 是否自动修复可修复的问题
        """
        self.auto_fix = auto_fix
        self.check_count = 0
        self.issue_count = 0
        self.critical_count = 0
        self._lock = threading.Lock(
        
        # 统计信息
        self.stats = defaultdict(int
        self.recent_issues: List[ConsistencyCheckResult] = []
        
        logger.info("状态一致性监控器已初始化"
    
    def check_and_log(self, task_data: Dict[str, Any]) -> ConsistencyCheckResult:
        """
        检查任务状态一致性并记录
        
        Args:
            task_data: 任务状态数据
        
        Returns:
            一致性检查结果
        """
        task_id = task_data.get('task_id', 'unknown'
        
        # 执行检查
        result = self._check_consistency(task_data
        
        # 记录统计
        with self._lock:
            self.check_count += 1
            self.stats[result.level.value] += 1
            
            if result.level != ConsistencyLevel.CONSISTENT:
                self.issue_count += 1
                self.recent_issues.append(result
                
                # 只保留最近 100 个问题
                if len(self.recent_issues) > 100:
                    self.recent_issues = self.recent_issues[-100:]
            
            if result.level == ConsistencyLevel.CRITICAL:
                self.critical_count += 1
        
        # 日志记录
        self._log_result(result
        
        # 自动修复
        if self.auto_fix and result.auto_fixed:
            logger.info(f"[自动修复] task_id={task_id}, issues={result.issues}"
        
        return result
    
    def _check_consistency(self, task_data: Dict[str, Any]) -> ConsistencyCheckResult:
        """
        执行一致性检查
        
        检查规则:
        1. status='completed' 时，stage 必须为 'completed'
        2. status='failed' 时，stage 必须为 'failed'
        3. is_completed=true 时，progress 必须为 100 (成功) 或 0 (失败
        4. stage 和 status 必须匹配
        """
        task_id = task_data.get('task_id', 'unknown'
        status = task_data.get('status', 'unknown'
        stage = task_data.get('stage', 'unknown'
        is_completed = task_data.get('is_completed', False
        progress = task_data.get('progress', 0
        
        issues = []
        auto_fixed = False
        level = ConsistencyLevel.CONSISTENT
        
        # 规则 1: status='completed' 时，stage 必须为 'completed'
        if status == 'completed' and stage != 'completed':
            issues.append(f"status=completed 但 stage={stage}"
            level = ConsistencyLevel.MAJOR_ISSUE
            
            # 自动修复
            if self.auto_fix:
                task_data['stage'] = 'completed'
                auto_fixed = True
        
        # 规则 2: status='failed' 时，stage 必须为 'failed'
        if status == 'failed' and stage != 'failed':
            issues.append(f"status=failed 但 stage={stage}"
            level = ConsistencyLevel.MAJOR_ISSUE
            
            # 自动修复
            if self.auto_fix:
                task_data['stage'] = 'failed'
                auto_fixed = True
        
        # 规则 3: is_completed=true 时，检查 progress
        if is_completed:
            if status == 'completed' and progress != 100:
                issues.append(f"is_completed=true, status=completed 但 progress={progress}"
                level = ConsistencyLevel.MINOR_ISSUE
            
            if status == 'failed' and progress != 0:
                issues.append(f"is_completed=true, status=failed 但 progress={progress}"
                level = ConsistencyLevel.MINOR_ISSUE
        
        # 规则 4: stage 和 status 必须匹配
        valid_combinations = [
            ('initializing', 'init'),
            ('processing', 'ai_fetching'),
            ('processing', 'ranking_analysis'),
            ('processing', 'source_tracing'),
            ('completed', 'completed'),
            ('failed', 'failed'),
        ]
        
        if (status, stage) not in valid_combinations:
            if not issues:  # 避免重复报告
                issues.append(f"无效的 status/stage 组合：status={status}, stage={stage}"
                level = ConsistencyLevel.MINOR_ISSUE
        
        # 确定最终级别
        if len(issues) >= 3:
            level = ConsistencyLevel.CRITICAL
        elif len(issues) >= 2:
            level = ConsistencyLevel.MAJOR_ISSUE
        elif len(issues) >= 1:
            level = ConsistencyLevel.MINOR_ISSUE
        
        return ConsistencyCheckResult(
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            level=level,
            status=status,
            stage=stage,
            is_completed=is_completed,
            progress=progress,
            issues=issues,
            auto_fixed=auto_fixed,
            details=task_data
        
    
    def _log_result(self, result: ConsistencyCheckResult):
        """记录检查结果"""
        if result.level == ConsistencyLevel.CONSISTENT:
            logger.debug(f"[一致] task_id={result.task_id}, status={result.status}, stage={result.stage}"
        
        elif result.level == ConsistencyLevel.MINOR_ISSUE:
            logger.warning(f"[小问题] task_id={result.task_id}: {', '.join(result.issues)}"
        
        elif result.level == ConsistencyLevel.MAJOR_ISSUE:
            logger.error(f"[严重问题] task_id={result.task_id}: {', '.join(result.issues)}"
        
        elif result.level == ConsistencyLevel.CRITICAL:
            logger.critical(f"[严重错误] task_id={result.task_id}: {', '.join(result.issues)}"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'total_checks': self.check_count,
                'total_issues': self.issue_count,
                'critical_issues': self.critical_count,
                'consistency_rate': (
                    (self.check_count - self.issue_count) / self.check_count * 100
                    if self.check_count > 0 else 100
                ),
                'by_level': dict(self.stats),
                'recent_issues_count': len(self.recent_issues
            }
    
    def get_recent_issues(self, limit: int = 10) -> List[Dict]:
        """获取最近的问题"""
        with self._lock:
            issues = self.recent_issues[-limit:]
            return [asdict(issue) for issue in issues]
    
    def generate_report(self) -> str:
        """生成监控报告"""
        stats = self.get_stats(
        
        report = []
        report.append("=" * 60
        report.append("状态一致性监控报告"
        report.append("=" * 60
        report.append(f"生成时间：{datetime.now().isoformat()}"
        report.append(""
        report.append("统计信息:"
        report.append(f"  总检查次数：{stats['total_checks']}"
        report.append(f"  发现问题数：{stats['total_issues']}"
        report.append(f"  严重问题数：{stats['critical_issues']}"
        report.append(f"  一致性比率：{stats['consistency_rate']:.2f}%"
        report.append(""
        report.append("问题级别分布:"
        for level, count in stats['by_level'].items():
            report.append(f"  {level}: {count}"
        report.append(""
        
        if stats['recent_issues_count'] > 0:
            report.append(f"最近问题 (最多 10 个):"
            for issue in self.get_recent_issues(10):
                report.append(f"  - [{issue['level']}] task_id={issue['task_id']}: {', '.join(issue['issues'])}"
        else:
            report.append("最近无问题"
        
        report.append(""
        report.append("=" * 60
        
        return "\n".join(report


# 装饰器：自动监控 API 响应
def monitor_state_consistency(monitor: StateConsistencyMonitor):
    """
    装饰器：监控函数返回的状态数据一致性
    
    使用示例:
        monitor = StateConsistencyMonitor(
        
        @monitor_state_consistency(monitor
        def get_task_status_api(task_id):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs
            
            # 如果返回的是字典，执行一致性检查
            if isinstance(result, dict):
                monitor.check_and_log(result
            elif isinstance(result, tuple) and len(result) > 0:
                # Flask 响应可能是 (data, status_code) 格式
                data = result[0]
                if isinstance(data, dict):
                    monitor.check_and_log(data
            
            return result
        return wrapper
    return decorator


# 全局监控实例
_global_monitor: Optional[StateConsistencyMonitor] = None


def get_monitor() -> StateConsistencyMonitor:
    """获取全局监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = StateConsistencyMonitor(auto_fix=True
    return _global_monitor


# CLI 接口
if __name__ == '__main__':
    import sys
    
    print_header = lambda text: print(f"\n{'='*60}\n{text.center(60)}\n{'='*60}\n"
    
    print_header("状态一致性监控器 - 测试模式"
    
    # 创建监控器
    monitor = StateConsistencyMonitor(auto_fix=True
    
    # 测试用例
    test_cases = [
        {
            'name': '正常完成状态',
            'data': {
                'task_id': 'test_001',
                'status': 'completed',
                'stage': 'completed',
                'is_completed': True,
                'progress': 100
            },
            'expected': ConsistencyLevel.CONSISTENT
        },
        {
            'name': 'status/stage 不同步',
            'data': {
                'task_id': 'test_002',
                'status': 'completed',
                'stage': 'ai_fetching',  # 不同步
                'is_completed': True,
                'progress': 100
            },
            'expected': ConsistencyLevel.MAJOR_ISSUE
        },
        {
            'name': '失败状态',
            'data': {
                'task_id': 'test_003',
                'status': 'failed',
                'stage': 'failed',
                'is_completed': True,
                'progress': 0
            },
            'expected': ConsistencyLevel.CONSISTENT
        },
        {
            'name': '处理中状态',
            'data': {
                'task_id': 'test_004',
                'status': 'processing',
                'stage': 'ai_fetching',
                'is_completed': False,
                'progress': 30
            },
            'expected': ConsistencyLevel.CONSISTENT
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = monitor.check_and_log(test['data']
        
        if result.level == test['expected']:
            f"✅ {test['name']}: 通过"
            passed += 1
        else:
            f"❌ {test['name']}: 失败 (期望 {test['expected'].value}, 得到 {result.level.value})"
            failed += 1
    
    # 打印统计
    print("\n" + "=" * 60
    print("测试总结"
    print("=" * 60
    print(f"通过：{passed}"
    print(f"失败：{failed}"
    print(f"通过率：{passed/(passed+failed)*100:.1f}%"
    
    # 打印报告
    print("\n" + monitor.generate_report()
    
    sys.exit(0 if failed == 0 else 1
