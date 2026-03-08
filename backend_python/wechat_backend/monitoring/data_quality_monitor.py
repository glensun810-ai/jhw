#!/usr/bin/env python3
"""
数据质量监控模块

功能：
1. 实时监控诊断结果数据质量
2. 统计字段完整性指标
3. 触发告警当质量低于阈值
4. 提供质量报告 API

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from wechat_backend.logging_config import api_logger


class DataQualityMetrics:
    """数据质量指标"""
    
    def __init__(self):
        self.total_results = 0
        self.valid_results = 0
        self.invalid_results = 0
        self.empty_brand_count = 0
        self.zero_tokens_count = 0
        self.validation_errors: List[str] = []
        self.last_updated = datetime.now()
    
    @property
    def valid_ratio(self) -> float:
        """有效率"""
        if self.total_results == 0:
            return 1.0
        return self.valid_results / self.total_results
    
    @property
    def empty_brand_ratio(self) -> float:
        """brand 空值率"""
        if self.total_results == 0:
            return 0.0
        return self.empty_brand_count / self.total_results
    
    @property
    def zero_tokens_ratio(self) -> float:
        """tokens_used 零值率"""
        if self.total_results == 0:
            return 0.0
        return self.zero_tokens_count / self.total_results
    
    @property
    def quality_score(self) -> int:
        """
        质量评分（0-100）
        
        计算规则：
        - 基础分 100 分
        - brand 空值率 > 1%: 扣 20 分
        - tokens_used 零值率 > 50%: 扣 20 分
        - 有效率 < 95%: 扣 10 分
        - 有效率 < 80%: 扣 20 分
        """
        score = 100
        
        if self.empty_brand_ratio > 0.01:
            score -= 20
        
        if self.zero_tokens_ratio > 0.5:
            score -= 20
        
        if self.valid_ratio < 0.95:
            score -= 10
        elif self.valid_ratio < 0.80:
            score -= 20
        
        return max(0, min(100, score))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_results': self.total_results,
            'valid_results': self.valid_results,
            'invalid_results': self.invalid_results,
            'valid_ratio': round(self.valid_ratio, 4),
            'empty_brand_count': self.empty_brand_count,
            'empty_brand_ratio': round(self.empty_brand_ratio, 4),
            'zero_tokens_count': self.zero_tokens_count,
            'zero_tokens_ratio': round(self.zero_tokens_ratio, 4),
            'quality_score': self.quality_score,
            'last_updated': self.last_updated.isoformat()
        }


class DataQualityMonitor:
    """
    数据质量监控器
    
    单例模式，全局唯一实例
    
    用法：
        monitor = get_quality_monitor()
        monitor.record_result(result, execution_id)
        metrics = monitor.get_metrics()
    """
    
    # 告警阈值配置
    ALERT_THRESHOLDS = {
        'empty_brand_ratio': 0.01,      # brand 空值率 > 1% 告警
        'zero_tokens_ratio': 0.50,      # tokens_used 零值率 > 50% 告警
        'valid_ratio': 0.95,            # 有效率 < 95% 告警
        'quality_score': 80,            # 质量评分 < 80 告警
    }
    
    # 告警冷却时间（秒）
    ALERT_COOLDOWN = 300  # 5 分钟
    
    def __init__(self):
        self._metrics = DataQualityMetrics()
        self._execution_metrics: Dict[str, DataQualityMetrics] = defaultdict(DataQualityMetrics)
        self._last_alert_time: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._alert_callbacks: List[callable] = []
        
        api_logger.info("[DataQualityMonitor] 初始化完成")
    
    def record_result(
        self,
        result: Dict[str, Any],
        execution_id: str,
        is_valid: bool = True,
        errors: Optional[List[str]] = None
    ):
        """
        记录单个结果
        
        参数：
            result: 诊断结果
            execution_id: 执行 ID
            is_valid: 是否有效
            errors: 验证错误列表
        """
        with self._lock:
            # 更新全局指标
            self._metrics.total_results += 1
            
            if is_valid:
                self._metrics.valid_results += 1
            else:
                self._metrics.invalid_results += 1
                if errors:
                    self._metrics.validation_errors.extend(errors[:5])  # 只保留最近 5 个错误
            
            # 检查特定字段
            if not result.get('brand'):
                self._metrics.empty_brand_count += 1
            
            if not result.get('tokens_used') or result.get('tokens_used') == 0:
                self._metrics.zero_tokens_count += 1
            
            # 更新执行级别指标
            exec_metrics = self._execution_metrics[execution_id]
            exec_metrics.total_results += 1
            if is_valid:
                exec_metrics.valid_results += 1
            else:
                exec_metrics.invalid_results += 1
            
            if not result.get('brand'):
                exec_metrics.empty_brand_count += 1
            
            if not result.get('tokens_used') or result.get('tokens_used') == 0:
                exec_metrics.zero_tokens_count += 1
            
            exec_metrics.last_updated = datetime.now()
            
            # 更新最后更新时间
            self._metrics.last_updated = datetime.now()
            
            # 检查是否需要告警
            self._check_alerts(execution_id)
    
    def _check_alerts(self, execution_id: str):
        """检查是否需要触发告警"""
        now = datetime.now()
        alerts_to_trigger = []
        
        # 检查全局指标
        if self._metrics.empty_brand_ratio > self.ALERT_THRESHOLDS['empty_brand_ratio']:
            alerts_to_trigger.append(('empty_brand_ratio', self._metrics.empty_brand_ratio))
        
        if self._metrics.zero_tokens_ratio > self.ALERT_THRESHOLDS['zero_tokens_ratio']:
            alerts_to_trigger.append(('zero_tokens_ratio', self._metrics.zero_tokens_ratio))
        
        if self._metrics.valid_ratio < self.ALERT_THRESHOLDS['valid_ratio']:
            alerts_to_trigger.append(('valid_ratio', self._metrics.valid_ratio))
        
        if self._metrics.quality_score < self.ALERT_THRESHOLDS['quality_score']:
            alerts_to_trigger.append(('quality_score', self._metrics.quality_score))
        
        # 触发告警（考虑冷却时间）
        for alert_type, value in alerts_to_trigger:
            last_alert = self._last_alert_time.get(alert_type)
            if not last_alert or (now - last_alert).total_seconds() > self.ALERT_COOLDOWN:
                self._trigger_alert(alert_type, value, execution_id)
                self._last_alert_time[alert_type] = now
    
    def _trigger_alert(
        self,
        alert_type: str,
        value: float,
        execution_id: str
    ):
        """触发告警"""
        alert_message = (
            f"[数据质量告警] {alert_type} = {value:.4f}, "
            f"threshold = {self.ALERT_THRESHOLDS.get(alert_type, 'N/A')}, "
            f"execution_id = {execution_id}"
        )
        
        api_logger.error(alert_message, extra={
            'alert_type': alert_type,
            'alert_value': value,
            'threshold': self.ALERT_THRESHOLDS.get(alert_type),
            'execution_id': execution_id
        })
        
        # 调用告警回调
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, value, self._metrics.to_dict())
            except Exception as e:
                api_logger.error(f"[DataQualityMonitor] 告警回调失败：{e}")
    
    def register_alert_callback(self, callback: callable):
        """注册告警回调函数"""
        self._alert_callbacks.append(callback)
    
    def get_metrics(self, execution_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取质量指标
        
        参数：
            execution_id: 执行 ID（可选，不传则返回全局指标）
        
        返回：
            指标字典
        """
        with self._lock:
            if execution_id:
                metrics = self._execution_metrics.get(execution_id, DataQualityMetrics())
            else:
                metrics = self._metrics
            
            return metrics.to_dict()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取所有执行的汇总"""
        with self._lock:
            summary = {
                'total_executions': len(self._execution_metrics),
                'executions': {}
            }
            
            for exec_id, metrics in self._execution_metrics.items():
                summary['executions'][exec_id] = {
                    'total_results': metrics.total_results,
                    'valid_ratio': round(metrics.valid_ratio, 4),
                    'quality_score': metrics.quality_score,
                    'last_updated': metrics.last_updated.isoformat()
                }
            
            return summary
    
    def reset_metrics(self, execution_id: Optional[str] = None):
        """
        重置指标
        
        参数：
            execution_id: 执行 ID（可选，不传则重置全局指标）
        """
        with self._lock:
            if execution_id:
                if execution_id in self._execution_metrics:
                    del self._execution_metrics[execution_id]
            else:
                self._metrics = DataQualityMetrics()


# 单例实例
_quality_monitor: Optional[DataQualityMonitor] = None
_monitor_lock = threading.Lock()


def get_quality_monitor() -> DataQualityMonitor:
    """获取数据质量监控器单例"""
    global _quality_monitor
    
    if _quality_monitor is None:
        with _monitor_lock:
            if _quality_monitor is None:
                _quality_monitor = DataQualityMonitor()
    
    return _quality_monitor


def reset_quality_monitor():
    """重置监控器（用于测试）"""
    global _quality_monitor
    with _monitor_lock:
        _quality_monitor = None


# 装饰器：自动记录质量指标
def monitor_data_quality(func):
    """
    装饰器：自动记录函数返回结果的数据质量
    
    用法：
        @monitor_data_quality
        def execute_nxm_test(...):
            return {'results': [...]}
    """
    from functools import wraps
    from wechat_backend.validators import ResultValidator
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 提取 execution_id
        execution_id = kwargs.get('execution_id') or kwargs.get('task_id') or 'unknown'
        
        # 获取监控器
        monitor = get_quality_monitor()
        validator = ResultValidator(strict_mode=False)
        
        # 记录结果
        if isinstance(result, dict) and 'results' in result:
            for r in result['results']:
                is_valid, errors, _ = validator.validate(r, execution_id)
                monitor.record_result(r, execution_id, is_valid, errors)
        
        return result
    
    return wrapper


# 导出公共 API
__all__ = [
    'DataQualityMetrics',
    'DataQualityMonitor',
    'get_quality_monitor',
    'reset_quality_monitor',
    'monitor_data_quality'
]
