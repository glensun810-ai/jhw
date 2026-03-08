"""
数据质量监控模块

P2-3 优化：数据质量监控和告警

功能特性:
- 质量指标采集
- 质量趋势分析
- 告警阈值配置
- 质量报告生成

使用示例:
    from wechat_backend.quality_monitoring import (
        QualityMetricsCollector,
        QualityAlertManager,
        QualityDashboard
    )
    
    # 采集质量指标
    collector = QualityMetricsCollector()
    collector.record_quality_score('execution_123', 85)
    collector.record_analysis_completeness('execution_123', 0.9)
    
    # 检查告警
    alert_manager = QualityAlertManager()
    alerts = alert_manager.check_alerts()
    
    # 获取质量仪表板数据
    dashboard = QualityDashboard()
    dashboard_data = dashboard.get_summary()
"""

import json
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
from pathlib import Path

from .logging_config import db_logger, api_logger


class QualityMetricsCollector:
    """
    质量指标采集器
    
    采集和存储各种质量相关指标
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化指标采集器
        
        Args:
            db_path: 数据库路径
        """
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / 'data' / 'quality_metrics.db')
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
        
        # 内存缓存
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # 缓存 TTL（秒）
    
    def _init_database(self):
        """初始化数据库表"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建质量指标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    UNIQUE(execution_id, metric_name, timestamp)
                )
            ''')
            
            # 创建质量趋势表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    avg_value REAL,
                    min_value REAL,
                    max_value REAL,
                    count INTEGER,
                    UNIQUE(date, hour, metric_name)
                )
            ''')
            
            # 创建告警记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    metric_value REAL,
                    threshold_value REAL,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_execution ON quality_metrics(execution_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON quality_metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trends_date ON quality_trends(date, hour)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON quality_alerts(status)')
            
            conn.commit()
            conn.close()
    
    def record_quality_score(self, execution_id: str, score: float, tags: Dict[str, str] = None):
        """
        记录质量评分
        
        Args:
            execution_id: 执行 ID
            score: 质量评分 (0-100)
            tags: 标签
        """
        self._record_metric(execution_id, 'quality_score', score, tags)
        
        # 更新缓存
        self._cache[f'quality_score:{execution_id}'] = {
            'value': score,
            'timestamp': datetime.now().isoformat()
        }
    
    def record_analysis_completeness(self, execution_id: str, completeness: float,
                                     tags: Dict[str, str] = None):
        """
        记录分析完整性
        
        Args:
            execution_id: 执行 ID
            completeness: 完整性 (0-1)
            tags: 标签
        """
        self._record_metric(execution_id, 'analysis_completeness', completeness, tags)
    
    def record_result_count(self, execution_id: str, count: int, tags: Dict[str, str] = None):
        """
        记录结果数量
        
        Args:
            execution_id: 执行 ID
            count: 结果数量
            tags: 标签
        """
        self._record_metric(execution_id, 'result_count', count, tags)
    
    def record_low_quality_ratio(self, execution_id: str, ratio: float,
                                 tags: Dict[str, str] = None):
        """
        记录低质量结果比例
        
        Args:
            execution_id: 执行 ID
            ratio: 低质量比例 (0-1)
            tags: 标签
        """
        self._record_metric(execution_id, 'low_quality_ratio', ratio, tags)
    
    def record_empty_analysis_count(self, execution_id: str, count: int,
                                    tags: Dict[str, str] = None):
        """
        记录空分析数量
        
        Args:
            execution_id: 执行 ID
            count: 空分析数量
            tags: 标签
        """
        self._record_metric(execution_id, 'empty_analysis_count', count, tags)
    
    def _record_metric(self, execution_id: str, metric_name: str,
                       metric_value: float, tags: Dict[str, str] = None):
        """记录指标到数据库"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            tags_json = json.dumps(tags) if tags else None
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO quality_metrics
                    (execution_id, metric_name, metric_value, tags, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (execution_id, metric_name, metric_value, tags_json,
                      datetime.now().isoformat()))
                conn.commit()
            except Exception as e:
                db_logger.error(f"记录质量指标失败：{e}")
            finally:
                conn.close()
    
    def get_quality_score(self, execution_id: str) -> Optional[float]:
        """获取指定执行 ID 的质量评分"""
        # 检查缓存
        cache_key = f'quality_score:{execution_id}'
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            timestamp = datetime.fromisoformat(cached['timestamp'])
            if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                return cached['value']
        
        # 从数据库查询
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT metric_value FROM quality_metrics
                WHERE execution_id = ? AND metric_name = 'quality_score'
                ORDER BY timestamp DESC LIMIT 1
            ''', (execution_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
    
    def get_trend(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取指标趋势
        
        Args:
            metric_name: 指标名称
            hours: 小时数
            
        Returns:
            趋势数据列表
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    strftime('%H', timestamp) as hour,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    COUNT(*) as count
                FROM quality_metrics
                WHERE metric_name = ? AND timestamp >= ?
                GROUP BY DATE(timestamp), strftime('%H', timestamp)
                ORDER BY date, hour
            ''', (metric_name, cutoff_time))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'date': row[0],
                    'hour': int(row[1]),
                    'avg_value': row[2],
                    'min_value': row[3],
                    'max_value': row[4],
                    'count': row[5]
                }
                for row in rows
            ]
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取统计数据
        
        Args:
            hours: 小时数
            
        Returns:
            统计数据
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # 质量评分统计
            cursor.execute('''
                SELECT 
                    AVG(metric_value) as avg_score,
                    MIN(metric_value) as min_score,
                    MAX(metric_value) as max_score,
                    COUNT(DISTINCT execution_id) as total_reports
                FROM quality_metrics
                WHERE metric_name = 'quality_score' AND timestamp >= ?
            ''', (cutoff_time,))
            
            score_stats = cursor.fetchone()
            
            # 低质量比例统计
            cursor.execute('''
                SELECT AVG(metric_value) as avg_ratio
                FROM quality_metrics
                WHERE metric_name = 'low_quality_ratio' AND timestamp >= ?
            ''', (cutoff_time,))
            
            ratio_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                'time_range': f'Last {hours} hours',
                'quality_score': {
                    'avg': score_stats[0] if score_stats[0] else 0,
                    'min': score_stats[1] if score_stats[1] else 0,
                    'max': score_stats[2] if score_stats[2] else 0,
                    'total_reports': score_stats[3] if score_stats[3] else 0
                },
                'low_quality_ratio': {
                    'avg': ratio_stats[0] if ratio_stats[0] else 0
                }
            }


class QualityAlertManager:
    """
    质量告警管理器
    
    管理质量相关的告警规则和触发
    """
    
    def __init__(self, metrics_collector: QualityMetricsCollector = None):
        """
        初始化告警管理器
        
        Args:
            metrics_collector: 指标采集器实例
        """
        self.metrics_collector = metrics_collector or QualityMetricsCollector()
        self._alert_rules: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # 注册默认告警规则
        self._register_default_alerts()
    
    def _register_default_alerts(self):
        """注册默认告警规则"""
        # 低质量评分告警
        self.add_alert_rule(
            name='low_quality_score',
            metric='quality_score',
            condition='lt',
            threshold=40,
            severity='warning',
            message='报告质量评分低于阈值'
        )
        
        # 极低质量评分告警
        self.add_alert_rule(
            name='critical_quality_score',
            metric='quality_score',
            condition='lt',
            threshold=20,
            severity='critical',
            message='报告质量评分极低'
        )
        
        # 高空分析比例告警
        self.add_alert_rule(
            name='high_empty_analysis_ratio',
            metric='empty_analysis_count',
            condition='gt',
            threshold=3,
            severity='warning',
            message='空分析数量过多'
        )
        
        # 高错误率告警
        self.add_alert_rule(
            name='high_error_rate',
            metric='error_rate',
            condition='gt',
            threshold=0.05,
            severity='critical',
            message='错误率超过阈值'
        )
    
    def add_alert_rule(self, name: str, metric: str, condition: str,
                       threshold: float, severity: str, message: str):
        """
        添加告警规则
        
        Args:
            name: 告警名称
            metric: 指标名称
            condition: 条件 (gt, lt, eq, gte, lte)
            threshold: 阈值
            severity: 严重程度 (info, warning, critical)
            message: 告警消息
        """
        with self._lock:
            self._alert_rules[name] = {
                'name': name,
                'metric': metric,
                'condition': condition,
                'threshold': threshold,
                'severity': severity,
                'message': message,
                'enabled': True
            }
    
    def remove_alert_rule(self, name: str):
        """移除告警规则"""
        with self._lock:
            if name in self._alert_rules:
                del self._alert_rules[name]
    
    def check_alerts(self, execution_id: str = None) -> List[Dict[str, Any]]:
        """
        检查告警
        
        Args:
            execution_id: 执行 ID（可选，不传则检查所有）
            
        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        
        for rule_name, rule in self._alert_rules.items():
            if not rule.get('enabled', True):
                continue
            
            # 获取当前指标值
            if execution_id:
                metric_value = self.metrics_collector.get_quality_score(execution_id)
            else:
                # 获取最近的平均值
                stats = self.metrics_collector.get_statistics(hours=1)
                if rule['metric'] == 'quality_score':
                    metric_value = stats['quality_score']['avg']
                else:
                    continue
            
            if metric_value is None:
                continue
            
            # 检查条件
            triggered = False
            if rule['condition'] == 'gt' and metric_value > rule['threshold']:
                triggered = True
            elif rule['condition'] == 'lt' and metric_value < rule['threshold']:
                triggered = True
            elif rule['condition'] == 'eq' and metric_value == rule['threshold']:
                triggered = True
            elif rule['condition'] == 'gte' and metric_value >= rule['threshold']:
                triggered = True
            elif rule['condition'] == 'lte' and metric_value <= rule['threshold']:
                triggered = True
            
            if triggered:
                triggered_alerts.append({
                    'rule_name': rule_name,
                    'metric': rule['metric'],
                    'metric_value': metric_value,
                    'threshold': rule['threshold'],
                    'severity': rule['severity'],
                    'message': rule['message'],
                    'execution_id': execution_id,
                    'triggered_at': datetime.now().isoformat()
                })
        
        return triggered_alerts
    
    def get_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """获取所有告警规则"""
        return dict(self._alert_rules)
    
    def enable_alert(self, name: str):
        """启用告警规则"""
        if name in self._alert_rules:
            self._alert_rules[name]['enabled'] = True
    
    def disable_alert(self, name: str):
        """禁用告警规则"""
        if name in self._alert_rules:
            self._alert_rules[name]['enabled'] = False


class QualityDashboard:
    """
    质量仪表板
    
    提供质量相关的可视化数据
    """
    
    def __init__(self, metrics_collector: QualityMetricsCollector = None,
                 alert_manager: QualityAlertManager = None):
        """
        初始化仪表板
        
        Args:
            metrics_collector: 指标采集器实例
            alert_manager: 告警管理器实例
        """
        self.metrics_collector = metrics_collector or QualityMetricsCollector()
        self.alert_manager = alert_manager or QualityAlertManager(self.metrics_collector)
    
    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取质量摘要
        
        Args:
            hours: 小时数
            
        Returns:
            摘要数据
        """
        stats = self.metrics_collector.get_statistics(hours)
        alerts = self.alert_manager.check_alerts()
        
        return {
            'statistics': stats,
            'active_alerts': len([a for a in alerts if a.get('severity') in ['warning', 'critical']]),
            'critical_alerts': len([a for a in alerts if a.get('severity') == 'critical']),
            'health_score': self._calculate_health_score(stats),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_health_score(self, stats: Dict[str, Any]) -> float:
        """
        计算健康评分
        
        Args:
            stats: 统计数据
            
        Returns:
            健康评分 (0-100)
        """
        score = 100
        
        # 根据平均质量评分调整
        avg_score = stats['quality_score']['avg']
        if avg_score < 80:
            score -= (80 - avg_score) * 0.5
        
        # 根据低质量比例调整
        low_ratio = stats['low_quality_ratio']['avg']
        score -= low_ratio * 20
        
        # 根据告警数量调整
        alerts = self.alert_manager.check_alerts()
        critical_count = len([a for a in alerts if a.get('severity') == 'critical'])
        warning_count = len([a for a in alerts if a.get('severity') == 'warning'])
        
        score -= critical_count * 10
        score -= warning_count * 5
        
        return max(0, min(100, score))
    
    def get_trend_data(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """
        获取趋势数据
        
        Args:
            metric_name: 指标名称
            hours: 小时数
            
        Returns:
            趋势数据
        """
        trend = self.metrics_collector.get_trend(metric_name, hours)
        
        if not trend:
            return {'metric': metric_name, 'data': [], 'summary': {}}
        
        # 计算趋势摘要
        values = [d['avg_value'] for d in trend]
        
        return {
            'metric': metric_name,
            'data': trend,
            'summary': {
                'current': values[-1] if values else 0,
                'previous': values[0] if len(values) > 1 else values[0] if values else 0,
                'change': values[-1] - values[0] if len(values) > 1 else 0,
                'change_percent': ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] != 0 else 0,
                'avg': sum(values) / len(values) if values else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0
            }
        }
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        alerts = self.alert_manager.check_alerts()
        rules = self.alert_manager.get_alert_rules()
        
        return {
            'total_rules': len(rules),
            'enabled_rules': len([r for r in rules.values() if r.get('enabled', True)]),
            'triggered_alerts': len(alerts),
            'critical_count': len([a for a in alerts if a.get('severity') == 'critical']),
            'warning_count': len([a for a in alerts if a.get('severity') == 'warning']),
            'alerts': alerts
        }


# 全局实例
_metrics_collector: Optional[QualityMetricsCollector] = None
_alert_manager: Optional[QualityAlertManager] = None
_dashboard: Optional[QualityDashboard] = None


def get_metrics_collector() -> QualityMetricsCollector:
    """获取指标采集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = QualityMetricsCollector()
    return _metrics_collector


def get_alert_manager() -> QualityAlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = QualityAlertManager()
    return _alert_manager


def get_quality_dashboard() -> QualityDashboard:
    """获取质量仪表板实例"""
    global _dashboard
    if _dashboard is None:
        _dashboard = QualityDashboard()
    return _dashboard


# 便捷函数
def record_quality_score(execution_id: str, score: float, tags: Dict[str, str] = None):
    """记录质量评分"""
    get_metrics_collector().record_quality_score(execution_id, score, tags)


def check_quality_alerts(execution_id: str = None) -> List[Dict[str, Any]]:
    """检查质量告警"""
    return get_alert_manager().check_alerts(execution_id)


def get_quality_summary(hours: int = 24) -> Dict[str, Any]:
    """获取质量摘要"""
    return get_quality_dashboard().get_summary(hours)


# 导出所有符号
__all__ = [
    'QualityMetricsCollector',
    'QualityAlertManager',
    'QualityDashboard',
    'get_metrics_collector',
    'get_alert_manager',
    'get_quality_dashboard',
    'record_quality_score',
    'check_quality_alerts',
    'get_quality_summary',
]
